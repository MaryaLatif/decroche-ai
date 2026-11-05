import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR

_ID = re.compile(r"^[A-Za-z0-9_\-]{3,200}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_id(value: str) -> str:
    if not _ID.match(value or ""):
        raise ValueError("Identifiant invalide")
    return value


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def path(bid: str, *parts: str) -> Path:
    check_id(bid)
    return DATA_DIR.joinpath(bid, *parts)


def read_json(p: Path, default=None):
    if not p.exists():
        if default is not None:
            return default
        raise FileNotFoundError(p.name)
    return json.loads(p.read_text("utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, p)


# --- commerce ---
def create_business(data: dict) -> dict:
    bid = check_id(data["place_id"])
    p = path(bid, "business.json")
    existing = read_json(p, default={})
    business = {**data, "id": bid, "created_at": existing.get("created_at", now())}
    write_json(p, business)
    return business


def get_business(bid: str) -> dict:
    return read_json(path(bid, "business.json"))


def get_sources(bid: str) -> dict:
    return read_json(path(bid, "sources.json"), default={"sources": [], "job": {"status": "idle"}})


def save_sources(bid: str, data: dict) -> None:
    write_json(path(bid, "sources.json"), data)


def add_source(bid: str, source: dict) -> dict:
    data = get_sources(bid)
    source = {"id": new_id("src"), "added_at": now(), **source}
    data["sources"].append(source)
    save_sources(bid, data)
    return source


# --- connaissances ---
def read_knowledge(bid: str, version: str) -> dict:
    return read_json(path(bid, f"knowledge.{version}.json"))


def write_knowledge(bid: str, version: str, data: dict) -> None:
    write_json(path(bid, f"knowledge.{version}.json"), data)


# --- conversations ---
def get_conversation(bid: str, cid: str) -> dict:
    return read_json(path(bid, "conversations", f"{check_id(cid)}.json"))


def save_conversation(bid: str, conv: dict) -> None:
    write_json(path(bid, "conversations", f"{check_id(conv['id'])}.json"), conv)


def save_order(bid: str, order: dict) -> None:
    write_json(path(bid, "orders", f"{check_id(order['id'])}.json"), order)