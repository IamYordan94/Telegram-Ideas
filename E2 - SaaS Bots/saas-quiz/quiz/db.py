"""QuizDay — SQLite persistence: tenants, scores, rotation."""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    return date.today().isoformat()


def get_conn(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    bank TEXT NOT NULL,
    quiz_time TEXT NOT NULL DEFAULT '09:00',
    leaderboard_day TEXT NOT NULL DEFAULT 'sunday',
    leaderboard_time TEXT NOT NULL DEFAULT '18:00',
    q_index INTEGER NOT NULL DEFAULT 0,
    paid_until TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    q_index INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    answered_at TEXT,
    UNIQUE(tenant_id, user_id, q_index)
);
"""


def init_db(db_path: str):
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ── tenants ──

def add_tenant(db_path, slug, name, channel_id, bank,
               quiz_time="09:00", leaderboard_day="sunday", leaderboard_time="18:00") -> int:
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO tenants (slug, name, channel_id, bank, quiz_time, "
            "leaderboard_day, leaderboard_time, q_index, paid_until, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, 1, ?)",
            (slug, name, channel_id, bank, quiz_time, leaderboard_day, leaderboard_time, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_tenant(db_path, slug):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_tenant_by_id(db_path, tenant_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_tenants(db_path):
    conn = get_conn(db_path)
    rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_tenant_q_index(db_path, tenant_id, q_index):
    conn = get_conn(db_path)
    conn.execute("UPDATE tenants SET q_index=? WHERE id=?", (q_index, tenant_id))
    conn.commit()
    conn.close()


def set_tenant_active(db_path, tenant_id, active: bool):
    conn = get_conn(db_path)
    conn.execute("UPDATE tenants SET active=? WHERE id=?", (1 if active else 0, tenant_id))
    conn.commit()
    conn.close()


def extend_paid(db_path, tenant_id, days) -> str:
    """Extend paid_until by `days` from today (or from the current expiry if later)."""
    conn = get_conn(db_path)
    row = conn.execute("SELECT paid_until FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    base = date.today()
    if row and row["paid_until"]:
        try:
            cur = date.fromisoformat(row["paid_until"])
            if cur > base:
                base = cur
        except ValueError:
            pass
    new = base + timedelta(days=days)
    conn.execute("UPDATE tenants SET paid_until=? WHERE id=?", (new.isoformat(), tenant_id))
    conn.commit()
    conn.close()
    return new.isoformat()


def tenant_paid_ok(tenant) -> bool:
    """paid_until NULL = unlimited (our own demo channels). Otherwise must be today or later."""
    if not tenant["paid_until"]:
        return True
    try:
        return date.fromisoformat(tenant["paid_until"]) >= date.today()
    except ValueError:
        return False


# ── scores ──

def record_answer(db_path, tenant_id, user_id, username, q_index, correct) -> bool:
    """First answer counts; later answers on the same question are ignored. Returns True if recorded."""
    conn = get_conn(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO scores (tenant_id, user_id, username, q_index, correct, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tenant_id, user_id, username, q_index, 1 if correct else 0, now_iso()),
    )
    conn.commit()
    recorded = cur.rowcount > 0
    conn.close()
    return recorded


def user_week_correct(db_path, tenant_id, user_id, days=7) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn(db_path)
    row = conn.execute(
        "SELECT COALESCE(SUM(correct), 0) AS n FROM scores "
        "WHERE tenant_id=? AND user_id=? AND answered_at>=?",
        (tenant_id, user_id, since),
    ).fetchone()
    conn.close()
    return row["n"]


def week_top(db_path, tenant_id, days=7, limit=10):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT user_id, username, SUM(correct) AS n, COUNT(*) AS answered "
        "FROM scores WHERE tenant_id=? AND answered_at>=? "
        "GROUP BY user_id ORDER BY n DESC, answered ASC LIMIT ?",
        (tenant_id, since, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
