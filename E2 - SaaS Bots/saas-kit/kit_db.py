"""BoardKit — registry of job-board tenants (each runs the WerkNL machine)."""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL,
    city TEXT NOT NULL,
    bot_token TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_username TEXT DEFAULT '',
    admin_id INTEGER NOT NULL,
    digest_hour INTEGER NOT NULL DEFAULT 8,
    paid_until TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT
);
"""


def init_db(db_path):
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def add_board(db_path, slug, brand, city, bot_token, channel_id,
              channel_username="", admin_id=0, digest_hour=8) -> int:
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO boards (slug, brand, city, bot_token, channel_id, "
            "channel_username, admin_id, digest_hour, paid_until, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 1, ?)",
            (slug, brand, city, bot_token, channel_id, channel_username, admin_id,
             digest_hour, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_board(db_path, slug):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM boards WHERE slug=?", (slug,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_boards(db_path):
    conn = get_conn(db_path)
    rows = conn.execute("SELECT * FROM boards ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_active(db_path, slug, active: bool):
    conn = get_conn(db_path)
    conn.execute("UPDATE boards SET active=? WHERE slug=?", (1 if active else 0, slug))
    conn.commit()
    conn.close()


def extend_paid(db_path, slug, days) -> str:
    conn = get_conn(db_path)
    row = conn.execute("SELECT paid_until FROM boards WHERE slug=?", (slug,)).fetchone()
    base = date.today()
    if row and row["paid_until"]:
        try:
            cur = date.fromisoformat(row["paid_until"])
            if cur > base:
                base = cur
        except ValueError:
            pass
    new = base + timedelta(days=days)
    conn.execute("UPDATE boards SET paid_until=? WHERE slug=?", (new.isoformat(), slug))
    conn.commit()
    conn.close()
    return new.isoformat()


def remove_board(db_path, slug):
    conn = get_conn(db_path)
    conn.execute("DELETE FROM boards WHERE slug=?", (slug,))
    conn.commit()
    conn.close()


def paid_ok(board) -> bool:
    if not board["paid_until"]:
        return True
    try:
        return date.fromisoformat(board["paid_until"]) >= date.today()
    except ValueError:
        return False
