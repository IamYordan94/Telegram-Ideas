"""StaffQuiz (Telegram) — configuration loaded from the telegram folder's .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

# telegram/ is this file's folder; staffquiz root is one level up.
BASE_DIR = Path(__file__).resolve().parent          # .../staffquiz/telegram
ROOT_DIR = BASE_DIR.parent                           # .../staffquiz

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ.get("STAFFQUIZ_BOT_TOKEN", "").strip()
OWNER_ADMIN_ID = int(os.environ.get("STAFFQUIZ_OWNER_ADMIN_ID", "0") or 0)
DB_PATH = os.environ.get("STAFFQUIZ_DB_PATH", str(BASE_DIR / "data" / "staffquiz.db"))
BANKS_DIR = os.environ.get("STAFFQUIZ_BANKS_DIR", str(ROOT_DIR / "data" / "banks"))


def ready() -> bool:
    return bool(BOT_TOKEN and OWNER_ADMIN_ID)
