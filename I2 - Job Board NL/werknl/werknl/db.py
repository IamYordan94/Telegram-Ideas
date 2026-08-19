"""WerkNL — SQLite persistence layer."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS workers (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    sectors TEXT DEFAULT '[]',
    premium INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS employers (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    company TEXT,
    credits INTEGER DEFAULT 0,
    plan TEXT DEFAULT 'free',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    employer TEXT,
    employer_id INTEGER,
    sector TEXT NOT NULL,
    area TEXT,
    pay TEXT,
    hours TEXT,
    description TEXT,
    contact TEXT,
    status TEXT DEFAULT 'pending',
    is_paid INTEGER DEFAULT 0,
    is_featured INTEGER DEFAULT 0,
    source TEXT DEFAULT 'employer',
    created_at TEXT,
    posted_at TEXT,
    channel_message_id INTEGER
);
"""


def init_db(db_path: str):
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ── workers ──

def upsert_worker(db_path, telegram_id, username=None, first_name=None):
    conn = get_conn(db_path)
    conn.execute(
        "INSERT INTO workers (telegram_id, username, first_name, sectors, premium, created_at) "
        "VALUES (?, ?, ?, '[]', 0, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name",
        (telegram_id, username, first_name, now_iso()),
    )
    conn.commit()
    conn.close()


def get_worker(db_path, telegram_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM workers WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_worker_sectors(db_path, telegram_id, sectors):
    conn = get_conn(db_path)
    conn.execute("UPDATE workers SET sectors=? WHERE telegram_id=?", (json.dumps(sectors), telegram_id))
    conn.commit()
    conn.close()


def get_worker_sectors(db_path, telegram_id):
    w = get_worker(db_path, telegram_id)
    if not w:
        return []
    try:
        return json.loads(w["sectors"])
    except (json.JSONDecodeError, TypeError):
        return []


def set_worker_premium(db_path, telegram_id, premium: bool):
    conn = get_conn(db_path)
    conn.execute("UPDATE workers SET premium=? WHERE telegram_id=?", (1 if premium else 0, telegram_id))
    conn.commit()
    conn.close()


def worker_ids_by_sector(db_path, sector, premium_only=False):
    conn = get_conn(db_path)
    rows = conn.execute("SELECT telegram_id, sectors, premium FROM workers").fetchall()
    conn.close()
    ids = []
    for r in rows:
        try:
            s = json.loads(r["sectors"])
        except (json.JSONDecodeError, TypeError):
            s = []
        if sector in s:
            if premium_only and not r["premium"]:
                continue
            ids.append(r["telegram_id"])
    return ids


def all_worker_ids(db_path):
    conn = get_conn(db_path)
    rows = conn.execute("SELECT telegram_id FROM workers").fetchall()
    conn.close()
    return [r["telegram_id"] for r in rows]


# ── employers ──

def upsert_employer(db_path, telegram_id, username=None, company=None):
    conn = get_conn(db_path)
    conn.execute(
        "INSERT INTO employers (telegram_id, username, company, credits, plan, created_at) "
        "VALUES (?, ?, ?, 0, 'free', ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username",
        (telegram_id, username, company, now_iso()),
    )
    conn.commit()
    conn.close()


def get_employer(db_path, telegram_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM employers WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_employer_credits(db_path, telegram_id):
    e = get_employer(db_path, telegram_id)
    return e["credits"] if e else 0


def grant_credits(db_path, telegram_id, n):
    conn = get_conn(db_path)
    conn.execute("UPDATE employers SET credits=credits+? WHERE telegram_id=?", (n, telegram_id))
    conn.commit()
    conn.close()


def spend_credit(db_path, telegram_id) -> bool:
    conn = get_conn(db_path)
    row = conn.execute("SELECT credits FROM employers WHERE telegram_id=?", (telegram_id,)).fetchone()
    if not row or row["credits"] <= 0:
        conn.close()
        return False
    conn.execute("UPDATE employers SET credits=credits-1 WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    conn.close()
    return True


# ── jobs ──

def add_job(db_path, **fields):
    cols = ["title", "employer", "employer_id", "sector", "area", "pay", "hours",
            "description", "contact", "status", "is_paid", "is_featured", "source", "created_at"]
    vals = {
        "status": "pending", "is_paid": 0, "is_featured": 0,
        "source": "employer", "created_at": now_iso(),
    }
    vals.update({k: v for k, v in fields.items() if v is not None})
    conn = get_conn(db_path)
    keys = [c for c in cols if c in vals]
    sql = f"INSERT INTO jobs ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
    cur = conn.execute(sql, [vals[k] for k in keys])
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return job_id


def get_job(db_path, job_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_jobs(db_path, status=None, sector=None, limit=50):
    conn = get_conn(db_path)
    q = "SELECT * FROM jobs"
    conds, params = [], []
    if status:
        conds.append("status=?")
        params.append(status)
    if sector:
        conds.append("sector=?")
        params.append(sector)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_job_status(db_path, job_id, status, channel_message_id=None):
    conn = get_conn(db_path)
    posted_at = now_iso() if status == "active" else None
    conn.execute(
        "UPDATE jobs SET status=?, posted_at=COALESCE(?, posted_at), "
        "channel_message_id=COALESCE(?, channel_message_id) WHERE id=?",
        (status, posted_at, channel_message_id, job_id),
    )
    conn.commit()
    conn.close()


def jobs_active_by_sectors(db_path, sectors):
    if not sectors:
        return []
    conn = get_conn(db_path)
    ph = ",".join("?" for _ in sectors)
    q = f"SELECT * FROM jobs WHERE status='active' AND sector IN ({ph}) ORDER BY id DESC"
    rows = conn.execute(q, sectors).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats(db_path):
    conn = get_conn(db_path)
    workers = conn.execute("SELECT COUNT(*) c FROM workers").fetchone()["c"]
    premium = conn.execute("SELECT COUNT(*) c FROM workers WHERE premium=1").fetchone()["c"]
    employers = conn.execute("SELECT COUNT(*) c FROM employers").fetchone()["c"]
    active = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='active'").fetchone()["c"]
    filled = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='filled'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) c FROM jobs WHERE status='pending'").fetchone()["c"]
    conn.close()
    total = active + filled
    fill_rate = round(filled / total * 100, 1) if total else 0
    return {
        "workers": workers, "premium_workers": premium, "employers": employers,
        "active_jobs": active, "filled_jobs": filled, "pending_jobs": pending,
        "fill_rate": fill_rate,
    }
