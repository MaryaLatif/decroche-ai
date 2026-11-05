from datetime import datetime
from zoneinfo import ZoneInfo

DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def format_hours(oh: dict | None, fallback: str | None = None) -> str:
    if not oh or not oh.get("days"):
        return fallback or "non renseignés"
    lines = []
    for d in sorted(oh["days"], key=lambda x: x["day"]):
        slots = " et ".join(f"{s['open']}-{s['close']}" for s in d["slots"]) or "fermé"
        lines.append(f"{DAYS[d['day']]} : {slots}")
    if oh.get("note"):
        lines.append(f"Remarque : {oh['note']}")
    return "\n".join(lines)


def is_open(oh: dict | None, now: datetime) -> bool | None:
    if not oh or not oh.get("days"):
        return None
    by_day = {d["day"]: d["slots"] for d in oh["days"]}
    wd, cur = now.weekday(), now.hour * 60 + now.minute
    for s in by_day.get(wd, []):
        o, c = _minutes(s["open"]), _minutes(s["close"])
        if (o < c and o <= cur < c) or (c < o and cur >= o):
            return True
    for s in by_day.get((wd - 1) % 7, []):
        o, c = _minutes(s["open"]), _minutes(s["close"])
        if c < o and cur < c:
            return True
    return False


def opening_status(oh: dict | None, tz: str | None) -> dict:
    try:
        now = datetime.now(ZoneInfo(tz or "Europe/Paris"))
    except Exception:
        now = datetime.now(ZoneInfo("Europe/Paris"))
    return {
        "maintenant": f"{DAYS[now.weekday()]} {now.strftime('%H:%M')} (heure locale du commerce)",
        "ouvert_maintenant": is_open(oh, now),  # null = horaires inconnus
        "horaires": format_hours(oh),
    }