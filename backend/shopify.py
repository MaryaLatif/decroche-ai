import json
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from collector import UA, safe_get
from schemas import Item

PAGE_SIZE = 100
MAX_PAGES = 8
_NOISE_TAGS = {"new", "nouveau", "nouveauté", "promo", "sale", "soldes", "best seller", "bestseller", "featured", "home", "homepage"}


def _tags(p: dict) -> list[str]:
    raw = p.get("tags") or []
    if isinstance(raw, str):
        raw = raw.split(",")
    out: list[str] = []
    for tag in raw:
        tag = tag.strip()
        if not tag or tag.startswith(("_", ":")) or ":" in tag or len(tag) > 40 or tag.lower() in _NOISE_TAGS:
            continue
        if tag.lower() not in {t.lower() for t in out}:
            out.append(tag)
    return out[:8]

def fetch_products(site_url: str) -> tuple[list[dict], bool]:
    """Retourne (produits, complet). Liste vide si le site n'expose pas le catalogue."""
    p = urlparse(site_url)
    origin = f"{p.scheme}://{p.netloc}"
    products: list[dict] = []
    with httpx.Client(timeout=20, headers={"User-Agent": UA, "Accept": "application/json"}) as client:
        for page in range(1, MAX_PAGES + 1):
            try:
                _, _, body = safe_get(client, f"{origin}/products.json?limit={PAGE_SIZE}&page={page}")
                batch = json.loads(body).get("products")
            except Exception:
                return products, False if products else False
            if not batch:
                break
            products += batch
            if len(batch) < PAGE_SIZE:
                return products, True
            time.sleep(2)
    return products, len(products) > 0 and len(products) % PAGE_SIZE != 0


def _cents(price) -> int:
    return round(float(price) * 100)


def _text(html: str | None, limit: int = 400) -> str | None:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    return text[:limit] or None


def products_to_items(
    products: list[dict], source_id: str, include_unavailable: bool = False
) -> tuple[list[Item], int]:
    """Retourne (items, nombre de produits ignorés car épuisés)."""
    items: list[Item] = []
    hidden = 0
    for p in products:
        variants = p.get("variants") or []
        if not include_unavailable:
            variants = [v for v in variants if v.get("available")]
        if not variants:
            hidden += 1
            continue

        title = (p.get("title") or "").strip()
        tags = _tags(p)
        category = (p.get("product_type") or "").strip() or (tags[0] if tags else None)
        base_desc = _text(p.get("body_html"))
        prices = {_cents(v["price"]) for v in variants}

        split = None  # option dont dépend le prix (ex. la taille)
        if len(prices) > 1:
            for k in (1, 2, 3):
                key = f"option{k}"
                values = {v.get(key) for v in variants}
                if None in values or len(values) < 2:
                    continue
                if all(len({_cents(v["price"]) for v in variants if v.get(key) == val}) == 1 for val in values):
                    split = k
                    break

        if len(prices) == 1:
            groups = [(None, prices.pop(), any(v.get("available") for v in variants))]
        elif split:
            by_value: dict[str, list[dict]] = {}
            for v in variants:
                by_value.setdefault(v[f"option{split}"], []).append(v)
            groups = [
                (val, _cents(vs[0]["price"]), any(x.get("available") for x in vs))
                for val, vs in by_value.items()
            ]
        else:
            groups = [(v.get("title"), _cents(v["price"]), bool(v.get("available"))) for v in variants]

        extras = []
        if len(prices) == 1 or split:
            for opt in p.get("options") or []:
                pos = opt.get("position")
                if pos == split or opt.get("name") == "Title":
                    continue
                vals = list(dict.fromkeys(v.get(f"option{pos}") for v in variants if v.get(f"option{pos}")))
                if len(vals) > 1:
                    extras.append(f"{opt['name']} au choix : {', '.join(vals)}")
        description = " ".join(x for x in [base_desc, ". ".join(extras) or None] if x) or None

        for label, price, available in groups:
            name = title if label in (None, "Default Title") else f"{title} - {label}"
            items.append(Item(
                name=name, category=category, description=description, price_cents=price,
                availability="available" if available else "unavailable",
                source_ids=[source_id], tags=tags,
            ))
    return items, hidden