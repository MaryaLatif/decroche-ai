import re

import storage


def cart_view(cart: dict, knowledge: dict) -> dict:
    items = {i["id"]: i for i in knowledge["items"]}
    lines, total = [], 0
    for item_id, line in cart.items():
        item = items.get(item_id)
        if not item or item.get("price_cents") is None:
            continue
        line_total = item["price_cents"] * line["quantity"]
        total += line_total
        lines.append({
            "item_id": item_id,
            "name": item["name"],
            "quantity": line["quantity"],
            "unit_price_cents": item["price_cents"],
            "line_total_cents": line_total,
            "note": line.get("note"),
        })
    return {"lines": lines, "total_cents": total, "currency": knowledge.get("currency", "EUR")}


def execute_tool(name: str, args: dict, knowledge: dict, cart: dict) -> dict:
    items = {i["id"]: i for i in knowledge["items"]}
    try:
        if name == "add_to_cart":
            item = items.get(args.get("item_id"))
            if not item:
                return {"error": "Produit inconnu. Utilise un item_id du catalogue."}
            if item.get("price_cents") is None:
                return {"error": "Prix non renseigné : produit non commandable."}
            if item.get("availability") == "unavailable":
                return {"error": "Produit indisponible."}
            qty = int(args.get("quantity", 1))
            line = cart.setdefault(item["id"], {"quantity": 0, "note": None})
            if not 1 <= qty <= 20 or line["quantity"] + qty > 50:
                return {"error": "Quantité invalide (1 à 20 par ajout, 50 max par produit)."}
            line["quantity"] += qty
            if args.get("note"):
                line["note"] = str(args["note"])[:200]
        elif name == "remove_from_cart":
            item_id = args.get("item_id")
            if item_id not in cart:
                return {"error": "Ce produit n'est pas dans le panier."}
            qty = args.get("quantity")
            if qty is None or int(qty) >= cart[item_id]["quantity"]:
                del cart[item_id]
            else:
                cart[item_id]["quantity"] -= int(qty)
        elif name != "get_cart":
            return {"error": "Outil inconnu."}
    except (TypeError, ValueError):
        return {"error": "Arguments invalides."}
    return {"ok": True, "cart": cart_view(cart, knowledge)}


def confirm_order(bid: str, conv: dict, knowledge: dict, name: str, phone: str, fulfillment: str) -> dict:
    if not knowledge.get("ordering_enabled", True):
        raise ValueError("Les commandes ne sont pas activées pour ce commerce.")
    if fulfillment not in knowledge.get("fulfillment_modes", ["pickup"]):
        raise ValueError("Mode de retrait non proposé.")
    if not name.strip() or not re.fullmatch(r"[+\d\s().-]{6,20}", phone):
        raise ValueError("Nom ou téléphone invalide.")
    view = cart_view(conv["cart"], knowledge)
    if not view["lines"]:
        raise ValueError("Le panier est vide.")
    order = {
        "id": storage.new_id("cmd"),
        "number": "CMD-" + storage.new_id("x")[-6:].upper(),
        "status": "pending_merchant_acceptance",
        "created_at": storage.now(),
        "conversation_id": conv["id"],
        "customer": {"name": name.strip(), "phone": phone.strip()},
        "fulfillment": fulfillment,
        **view,
    }
    storage.save_order(bid, order)
    conv["cart"] = {}
    storage.save_conversation(bid, conv)
    return order