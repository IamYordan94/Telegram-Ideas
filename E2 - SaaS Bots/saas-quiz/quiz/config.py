"""QuizDay — configuration loaded from .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ.get("QUIZ_BOT_TOKEN", "").strip()
OWNER_ADMIN_ID = int(os.environ.get("QUIZ_OWNER_ADMIN_ID", "0") or 0)
DB_PATH = os.environ.get("QUIZ_DB_PATH", str(BASE_DIR / "data" / "quiz.db"))
BANKS_DIR = os.environ.get("QUIZ_BANKS_DIR", str(BASE_DIR / "data" / "banks"))


def ready() -> bool:
    return bool(BOT_TOKEN and OWNER_ADMIN_ID)
