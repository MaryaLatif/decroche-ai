import json
import re
import config
from extractor import get_client
from orders import cart_view, execute_tool
from hours import format_hours, opening_status

MAX_MESSAGES = 60

TOOLS = [
    {
        "name": "add_to_cart",
        "description": "Ajoute un produit du catalogue au panier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 20},
                "note": {"type": "string", "description": "Précision du client (optionnel)"},
            },
            "required": ["item_id", "quantity"],
        },
    },
    {
        "name": "remove_from_cart",
        "description": "Retire un produit (ou une quantité) du panier.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}, "quantity": {"type": "integer"}},
            "required": ["item_id"],
        },
    },
    {"name": "get_cart", "description": "Retourne le panier actuel.", "input_schema": {"type": "object", "properties": {}}},
    {
        "name": "get_opening_status",
        "description": "Donne le jour et l'heure locaux et indique si le commerce est ouvert maintenant. "
                       "À utiliser pour toute question du type « êtes-vous ouverts ? ».",
        "input_schema": {"type": "object", "properties": {}},
    },
]

_HOURS_WORDS = re.compile(r"horaire|ouvert|ouvre|ouvrir|ferm|heures? d", re.I)


def _faq_for_prompt(knowledge: dict) -> list:
    faq = knowledge.get("faq", [])
    if not (knowledge.get("opening_hours") or {}).get("days"):
        return faq
    return [f for f in faq if not _HOURS_WORDS.search(f["question"] + " " + f["answer"])]


def _eur(cents):
    return "prix non renseigné" if cents is None else f"{cents / 100:.2f} €".replace(".", ",")


def build_system(business: dict, knowledge: dict) -> str:
    catalog = [
        {
            "item_id": i["id"], "nom": i["name"], "categorie": i.get("category"),
            "description": i.get("description"), "prix": _eur(i.get("price_cents")),
            "disponibilite": i.get("availability"), "allergenes": i.get("allergens"),
            "tags": i.get("tags") or None,
        }
        for i in knowledge["items"]
    ]
    hours = format_hours(knowledge.get("opening_hours"), knowledge.get("opening_hours_text"))
    info = {
        "nom": knowledge.get("business_name") or business.get("name"),
        "adresse": business.get("address"),
        "telephone": business.get("phone"),
        "horaires": hours,
        "description": knowledge.get("description"),
        "commande_activee": knowledge.get("ordering_enabled", True),
        "modes": knowledge.get("fulfillment_modes"),
    }
    return (
        "Tu es l'assistant du commerce décrit ci-dessous. Tu réponds aux clients de façon brève et chaleureuse, "
        "dans leur langue (français par défaut).\n\n"
        "RÈGLES :\n"
        "- Pour toute question sur les horaires ou l'ouverture, appelle get_opening_status et utilise uniquement sa réponse. "
        "Ignore toute autre mention d'horaires dans la description ou la FAQ.\n"
        "- Les informations de ce message sont les plus récentes : elles priment sur tout ce qui a été dit plus tôt dans la conversation.\n"
        "- Ne mentionne jamais tes sources ni d'éventuelles contradictions : donne directement l'information du bloc COMMERCE.\n"
        "- Réponds en 4 phrases maximum, sans emoji.\n"
        f"COMMERCE :\n{json.dumps(info, ensure_ascii=False)}\n\n"
        f"CATALOGUE :\n{json.dumps(catalog, ensure_ascii=False)}\n\n"
        f"FAQ :\n{json.dumps(_faq_for_prompt(knowledge), ensure_ascii=False)}"
    )


def _clean(block) -> dict | None:
    if block.type == "text" and block.text.strip():
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return None


def run_turn(business: dict, knowledge: dict, conv: dict, user_text: str) -> str:
    if len(conv["messages"]) >= MAX_MESSAGES:
        raise ValueError("Conversation trop longue : démarre une nouvelle conversation.")
    messages = conv["messages"] + [{"role": "user", "content": user_text}]
    system = build_system(business, knowledge)
    reply = ""

    for _ in range(6):
        resp = get_client().messages.create(
            model=config.require_model(), max_tokens=1024,
            system=system, tools=TOOLS, messages=messages,
        )
        blocks = [b for b in map(_clean, resp.content) if b]
        messages.append({"role": "assistant", "content": blocks})
        reply = "\n".join(b["text"] for b in blocks if b["type"] == "text")
        if resp.stop_reason != "tool_use":
            break
        results = []
        for b in blocks:
            if b["type"] == "tool_use":
                if b["name"] == "get_opening_status":
                    out = opening_status(knowledge.get("opening_hours"), business.get("timezone"))
                else:
                    out = execute_tool(b["name"], b["input"], knowledge, conv["cart"])
                results.append({
                    "type": "tool_result", "tool_use_id": b["id"],
                    "content": json.dumps(out, ensure_ascii=False),
                })
        messages.append({"role": "user", "content": results})

    conv["messages"] = messages
    return reply or "Je n'ai pas pu répondre, pouvez-vous reformuler ?"