"""WerkNL — configuration loaded from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ.get("WERKNL_BOT_TOKEN", "").strip()
CHANNEL_ID = os.environ.get("WERKNL_CHANNEL_ID", "").strip()
ADMIN_ID = int(os.environ.get("WERKNL_ADMIN_ID", "0") or 0)
DB_PATH = os.environ.get("WERKNL_DB_PATH", str(BASE_DIR / "data" / "werknl.db"))
DIGEST_HOUR = int(os.environ.get("WERKNL_DIGEST_HOUR", "8") or 8)


def ready() -> bool:
    return bool(BOT_TOKEN and CHANNEL_ID and ADMIN_ID)
