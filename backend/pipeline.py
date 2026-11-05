import storage
import re
from collector import crawl
from extractor import extract_knowledge, normalize_ids
from shopify import fetch_products, products_to_items
from schemas import OpeningHours


def run_collection(bid: str) -> None:
    def setjob(**kw):
        data = storage.get_sources(bid)
        data["job"] = {**data.get("job", {}), **kw}
        storage.save_sources(bid, data)

    try:
        setjob(status="collecting", error=None, errors=[], pages=0, started_at=storage.now())
        docs, errors = [], []
        shop_items, shop_incomplete, shop_hidden = [], False, 0
        for s in storage.get_sources(bid)["sources"]:
            if s["type"] in ("website", "url"):
                products, complete = fetch_products(s["url"])
                if products:
                    items, hidden = products_to_items(products, s["id"])
                    shop_items += items
                    shop_hidden += hidden
                    shop_incomplete = shop_incomplete or not complete
                pages, errs = crawl(s["url"])
                errors += errs
                storage.write_json(storage.path(bid, "documents", f"{s['id']}.json"), pages)
                docs += [{"source_id": s["id"], "origin": p["url"], "text": p["text"], "kind": "web"} for p in pages]
            else:
                text = storage.path(bid, "documents", f"{s['id']}.txt").read_text("utf-8")
                docs.append({
                    "source_id": s["id"],
                    "origin": s.get("label") or s.get("filename") or "texte fourni",
                    "text": text,
                    "kind": "merchant",
                })
        if not docs:
            raise RuntimeError("Aucun contenu exploitable. " + "; ".join(errors[:3]))

        setjob(status="extracting", pages=len(docs), errors=errors)
        business = storage.get_business(bid)
        google = business.get("google_hours")
        kn = extract_knowledge(
            business, docs, need_hours=google is None, catalog_known=bool(shop_items)
        )
        if google:
            try:
                kn.opening_hours = OpeningHours.model_validate(google)
            except ValueError:
                kn.notes.append("Horaires Google illisibles : à saisir manuellement.")

        if shop_items:
            by_name = {i.name.strip().lower(): i for i in shop_items}
            for it in kn.items:  # produits extraits des PDF / textes du commerçant
                by_name[it.name.strip().lower()] = it
            kn.items = list(by_name.values())
            normalize_ids(kn)
            kn.notes = [n for n in kn.notes if not re.search(r"prix|catalogue|pages|produit", n, re.I)]
            kn.notes.append(
                f"{len(shop_items)} produits importés du catalogue du site (prix et disponibilités exacts)"
                + (f" ; {shop_hidden} produits épuisés ignorés." if shop_hidden else ".")
            )
            if shop_incomplete:
                kn.notes.append("Le catalogue du site n'a pas pu être lu en entier : la liste peut être incomplète.")
        storage.write_knowledge(bid, "draft", kn.model_dump())
        setjob(status="ready_for_review")
    except Exception as exc:
        setjob(status="failed", error=str(exc))