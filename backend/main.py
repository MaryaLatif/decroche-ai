import anthropic
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import chat
import config
import storage
from business_lookup import BusinessLookupError, clean_phone, get_business_details, search_businesses
from collector import assert_public_url, extract_upload
from extractor import normalize_ids
from orders import cart_view, confirm_order
from pipeline import run_collection
from schemas import Knowledge

app = FastAPI(title="Business Onboarding API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _value_error(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(FileNotFoundError)
async def _not_found(_, exc):
    return JSONResponse({"detail": "Ressource introuvable (étape précédente non terminée ?)"}, status_code=404)


# ---------- recherche ----------
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    max_results: int = Field(default=20, ge=1, le=20)


class SelectRequest(BaseModel):
    place_id: str


@app.post("/businesses/search")
def search(req: SearchRequest):
    try:
        return {"results": search_businesses(req.query, max_results=req.max_results)}
    except BusinessLookupError as e:
        raise HTTPException(400, str(e))


@app.post("/businesses/select")
def select(req: SelectRequest):
    try:
        business = get_business_details(req.place_id)
    except BusinessLookupError as e:
        raise HTTPException(400, str(e))
    business["phone_normalized"] = clean_phone(business.get("phone"))
    return {"business": business}


# ---------- onboarding ----------
@app.post("/onboarding/confirm")
def onboarding_confirm(req: SelectRequest):
    try:
        details = get_business_details(req.place_id)
    except BusinessLookupError as e:
        raise HTTPException(400, str(e))
    business = storage.create_business(details)
    data = storage.get_sources(business["id"])
    if business.get("website") and not any(s["type"] == "website" for s in data["sources"]):
        storage.add_source(business["id"], {"type": "website", "url": business["website"], "label": "Site officiel"})
    return {"business_id": business["id"], "business": business}


@app.get("/businesses/{bid}")
def get_business(bid: str):
    data = storage.get_sources(bid)
    return {"business": storage.get_business(bid), "sources": data["sources"], "job": data["job"]}


class UrlSource(BaseModel):
    url: str
    label: str | None = None


class TextSource(BaseModel):
    text: str = Field(..., min_length=3, max_length=100_000)
    label: str | None = "Texte collé"


@app.post("/businesses/{bid}/sources")
def add_url(bid: str, req: UrlSource):
    storage.get_business(bid)
    assert_public_url(req.url)
    return storage.add_source(bid, {"type": "url", "url": req.url, "label": req.label})


@app.post("/businesses/{bid}/sources/text")
def add_text(bid: str, req: TextSource):
    storage.get_business(bid)
    src = storage.add_source(bid, {"type": "text", "label": req.label})
    storage.path(bid, "documents", f"{src['id']}.txt").parent.mkdir(parents=True, exist_ok=True)
    storage.path(bid, "documents", f"{src['id']}.txt").write_text(req.text, "utf-8")
    return src


@app.post("/businesses/{bid}/documents")
def upload_document(bid: str, file: UploadFile = File(...)):
    storage.get_business(bid)
    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValueError("Fichier trop volumineux (10 Mo max)")
    text = extract_upload(file.filename or "", data)
    src = storage.add_source(bid, {"type": "upload", "filename": file.filename})
    p = storage.path(bid, "documents", f"{src['id']}.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, "utf-8")
    return src


@app.post("/businesses/{bid}/collect")
def start_collect(bid: str, background: BackgroundTasks):
    data = storage.get_sources(bid)
    if not data["sources"]:
        raise ValueError("Ajoute au moins une source.")
    if data["job"].get("status") in ("collecting", "extracting"):
        raise ValueError("Une collecte est déjà en cours.")
    data["job"] = {"status": "collecting"}
    storage.save_sources(bid, data)
    background.add_task(run_collection, bid)
    return data["job"]


@app.get("/businesses/{bid}/collect/status")
def collect_status(bid: str):
    return storage.get_sources(bid)["job"]


# ---------- connaissances ----------
@app.get("/businesses/{bid}/knowledge/{version}")
def get_knowledge(bid: str, version: str):
    if version not in ("draft", "approved"):
        raise ValueError("Version invalide")
    return storage.read_knowledge(bid, version)


@app.put("/businesses/{bid}/knowledge")
def put_knowledge(bid: str, kn: Knowledge):
    storage.get_business(bid)
    storage.write_knowledge(bid, "draft", normalize_ids(kn).model_dump())
    return {"ok": True}


@app.post("/businesses/{bid}/knowledge/approve")
def approve(bid: str):
    draft = Knowledge.model_validate(storage.read_knowledge(bid, "draft"))
    if not draft.items:
        raise ValueError("Le catalogue est vide.")
    try:
        version = storage.read_knowledge(bid, "approved").get("version", 0) + 1
    except FileNotFoundError:
        version = 1
    data = {**draft.model_dump(), "version": version, "approved_at": storage.now()}
    storage.write_knowledge(bid, "approved", data)
    return {"version": version}


# ---------- chat ----------
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=80)
    customer_phone: str = Field(..., min_length=6, max_length=20)
    fulfillment: str = "pickup"


@app.post("/businesses/{bid}/conversations")
def new_conversation(bid: str):
    business = storage.get_business(bid)
    knowledge = storage.read_knowledge(bid, "approved")
    conv = {
        "id": storage.new_id("conv"), "created_at": storage.now(),
        "messages": [], "cart": {}, "knowledge_version": knowledge.get("version"),
    }
    storage.save_conversation(bid, conv)
    name = knowledge.get("business_name") or business.get("name")
    return {
        "conversation_id": conv["id"],
        "greeting": f"Bonjour ! Je suis l'assistant de {name}. Je peux vous renseigner sur notre carte et préparer une commande.",
    }


@app.post("/businesses/{bid}/conversations/{cid}/messages")
def send_message(bid: str, cid: str, req: MessageRequest):
    business = storage.get_business(bid)
    knowledge = storage.read_knowledge(bid, "approved")
    conv = storage.get_conversation(bid, cid)
    if conv.get("knowledge_version") != knowledge.get("version"):
        conv["messages"] = []  # la base a changé : on repart de l'historique vide
        conv["knowledge_version"] = knowledge.get("version")
    try:
        reply = chat.run_turn(business, knowledge, conv, req.message)
    except anthropic.APIError as e:
        raise HTTPException(502, f"Erreur du modèle : {e}")
    storage.save_conversation(bid, conv)
    return {"reply": reply, "cart": cart_view(conv["cart"], knowledge)}


@app.post("/businesses/{bid}/conversations/{cid}/orders/confirm")
def confirm(bid: str, cid: str, req: OrderRequest):
    knowledge = storage.read_knowledge(bid, "approved")
    conv = storage.get_conversation(bid, cid)
    order = confirm_order(bid, conv, knowledge, req.customer_name, req.customer_phone, req.fulfillment)
    return {"order": order}


@app.get("/health")
def health():
    return {"status": "ok"}