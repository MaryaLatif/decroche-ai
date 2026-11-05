import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data/businesses"))
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
MAX_PAGES = 6
MAX_CONTEXT_CHARS = 90_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def require_model() -> str:
    if not ANTHROPIC_MODEL:
        raise RuntimeError("ANTHROPIC_MODEL manquant dans .env")
    return ANTHROPIC_MODEL