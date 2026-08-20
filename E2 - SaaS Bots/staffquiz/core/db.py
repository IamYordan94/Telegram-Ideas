"""StaffQuiz — SQLite persistence: tenants, employees, answers, aggregates.

Privacy design (IMPORTANT)
--------------------------
This module deliberately has NO function that exports per-employee answer
rows (there is no ``get_employee_scores_export``). The analytics entry point
is :func:`aggregate_report`, which is aggregate-only: it returns topic-level
correct percentages and answered counts summed across a whole tenant, so an
individual employee's answer history cannot be reconstructed from it. The
week/department leaderboards rank employees for the game — the intended
product feature — but they are ranking summaries, not raw per-answer exports.

The ``answers.topic`` column (a small, deliberate extension of the answer row)
carries the topic of the answered item so :func:`aggregate_report` can compute
per-topic percentages without needing the bank file at read time.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def get_conn(db_path: str) -> sqlite3.Connection:
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
    group_id TEXT,
    default_bank TEXT,
    fun_banks TEXT,
    quiz_time TEXT NOT NULL DEFAULT '09:00',
    q_index INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    name TEXT,
    department TEXT,
    language TEXT,
    tenant_id INTEGER NOT NULL,
    created_at TEXT,
    UNIQUE(tenant_id, uid)
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    item_index INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    topic TEXT,
    answered_at TEXT,
    UNIQUE(tenant_id, employee_id, item_index)
);
CREATE INDEX IF NOT EXISTS idx_answers_tenant_time ON answers(tenant_id, answered_at);
CREATE INDEX IF NOT EXISTS idx_answers_employee ON answers(employee_id);
"""


def init_db(db_path: str) -> None:
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ── tenants ──

def add_tenant(db_path, slug, name, group_id=None, default_bank=None,
               fun_banks=None, quiz_time="09:00") -> int:
    """Insert a tenant and return its id. ``fun_banks`` may be a dict or JSON str."""
    if fun_banks is not None and not isinstance(fun_banks, str):
        fun_banks = json.dumps(fun_banks)
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO tenants (slug, name, group_id, default_bank, fun_banks, "
            "quiz_time, q_index, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?)",
            (slug, name, group_id, default_bank, fun_banks, quiz_time, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _parse_fun_banks(raw):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _tenant_dict(row):
    d = dict(row)
    d["fun_banks"] = _parse_fun_banks(d.get("fun_banks"))
    return d


def get_tenant(db_path, slug):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM tenants WHERE slug=?", (slug,)).fetchone()
    conn.close()
    return _tenant_dict(row) if row else None


def get_tenant_by_id(db_path, tenant_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()
    conn.close()
    return _tenant_dict(row) if row else None


def list_tenants(db_path):
    conn = get_conn(db_path)
    rows = conn.execute("SELECT * FROM tenants ORDER BY id").fetchall()
    conn.close()
    return [_tenant_dict(r) for r in rows]


def set_q_index(db_path, tenant_id, q_index):
    conn = get_conn(db_path)
    conn.execute("UPDATE tenants SET q_index=? WHERE id=?", (int(q_index), tenant_id))
    conn.commit()
    conn.close()


def set_active(db_path, tenant_id, active: bool):
    conn = get_conn(db_path)
    conn.execute("UPDATE tenants SET active=? WHERE id=?", (1 if active else 0, tenant_id))
    conn.commit()
    conn.close()


# ── employees ──

def upsert_employee(db_path, tenant_id, uid, name=None, department=None,
                    language=None) -> int:
    """Insert an employee, or update name/department/language on an existing
    (tenant_id, uid) pair. Returns the employee id (stable across upserts)."""
    conn = get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO employees (uid, name, department, language, tenant_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(tenant_id, uid) DO UPDATE SET "
            "name=excluded.name, department=excluded.department, language=excluded.language",
            (uid, name, department, language, tenant_id, now_iso()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM employees WHERE tenant_id=? AND uid=?", (tenant_id, uid)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


def get_employee(db_path, tenant_id, uid):
    conn = get_conn(db_path)
    row = conn.execute(
        "SELECT * FROM employees WHERE tenant_id=? AND uid=?", (tenant_id, uid)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_employee_by_id(db_path, employee_id):
    conn = get_conn(db_path)
    row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_employees(db_path, tenant_id):
    """All registered employees of a tenant, in registration order."""
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM employees WHERE tenant_id=? ORDER BY id", (tenant_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_tenant_admin(db_path, tenant_id, admin_id):
    """Store the buyer's Telegram id on the tenant (their 'mini-key').

    Adds the admin_id column on first use (sqlite has no ADD COLUMN IF NOT EXISTS).
    """
    conn = get_conn(db_path)
    try:
        try:
            conn.execute("ALTER TABLE tenants ADD COLUMN admin_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.execute("UPDATE tenants SET admin_id=? WHERE id=?", (admin_id, tenant_id))
        conn.commit()
    finally:
        conn.close()


# ── answers ──

def record_answer(db_path, tenant_id, employee_id, item_index, correct,
                  topic=None, answered_at=None) -> bool:
    """Record one answer. First answer on (tenant, employee, item) wins.

    Returns True if recorded, False if it was a duplicate and ignored.
    ``topic`` is optional but needed for meaningful aggregate_report output;
    ``answered_at`` defaults to now (UTC) and is overridable for testing.
    """
    conn = get_conn(db_path)
    cur = conn.execute(
        "INSERT OR IGNORE INTO answers (tenant_id, employee_id, item_index, correct, topic, answered_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tenant_id, employee_id, item_index, 1 if correct else 0, topic,
         answered_at or now_iso()),
    )
    conn.commit()
    recorded = cur.rowcount > 0
    conn.close()
    return recorded


def _since_iso(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _employee_aggregates(db_path, tenant_id, days):
    """Per-employee correct/answered totals over the last `days`, ordered
    correct DESC then answered ASC (fewest-answered breaks ties)."""
    since = _since_iso(days)
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT e.id AS employee_id, e.uid AS uid, e.name AS name, "
        "COALESCE(e.department, '') AS department, "
        "COALESCE(SUM(a.correct), 0) AS correct, COUNT(a.id) AS answered "
        "FROM answers a JOIN employees e ON e.id = a.employee_id "
        "WHERE a.tenant_id = ? AND a.answered_at >= ? "
        "GROUP BY e.id "
        "ORDER BY correct DESC, answered ASC, e.id ASC",
        (tenant_id, since),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def week_leaderboard(db_path, tenant_id, days=7, limit=10):
    """Top employees by correct answers in the last `days`, fewest-answered first on ties."""
    return _employee_aggregates(db_path, tenant_id, days)[:limit]


def department_board(db_path, tenant_id, days=7):
    """One row per department: its top employee, sorted best-first."""
    rows = _employee_aggregates(db_path, tenant_id, days)
    best = {}
    order = []
    for r in rows:
        dept = r["department"]
        if dept not in best:
            best[dept] = r
            order.append(dept)
    result = [best[d] for d in order]
    result.sort(key=lambda r: (-r["correct"], r["answered"]))
    return result


def streak_days(db_path, employee_id) -> int:
    """Consecutive UTC calendar days with >=1 answer, ending today.

    Returns 0 when today has no answer yet (a streak only counts if it reaches
    today), and 0 for an employee with no answers at all.
    """
    conn = get_conn(db_path)
    rows = conn.execute(
        "SELECT DISTINCT substr(answered_at, 1, 10) AS d FROM answers WHERE employee_id=?",
        (employee_id,),
    ).fetchall()
    conn.close()
    days = {r["d"] for r in rows if r["d"]}
    today = datetime.now(timezone.utc).date()
    if today.isoformat() not in days:
        return 0
    streak = 0
    d = today
    while d.isoformat() in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


def participation_pct(db_path, tenant_id) -> float:
    """Percentage (0-100) of registered employees who answered at least once."""
    conn = get_conn(db_path)
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM employees WHERE tenant_id=?", (tenant_id,)
    ).fetchone()["n"]
    active = conn.execute(
        "SELECT COUNT(DISTINCT employee_id) AS n FROM answers WHERE tenant_id=?", (tenant_id,)
    ).fetchone()["n"]
    conn.close()
    if total == 0:
        return 0.0
    return (active / total) * 100.0


def aggregate_report(db_path, tenant_id) -> dict:
    """Aggregate-only analytics for a tenant (see module privacy note).

    Returns a dict with:
      per_topic          {topic: {"correct_pct": float, "answered": int, "correct": int}}
      participation_pct  float (0-100)
      weakest_topics     topic names sorted lowest correct_pct first
      active_employees   count of distinct employees with >=1 answer
    Answers without a topic are excluded from ``per_topic`` (but still count
    toward participation and active_employees).
    """
    conn = get_conn(db_path)
    topic_rows = conn.execute(
        "SELECT topic, COALESCE(SUM(correct), 0) AS correct, COUNT(*) AS answered "
        "FROM answers WHERE tenant_id=? AND topic IS NOT NULL AND topic != '' "
        "GROUP BY topic",
        (tenant_id,),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM employees WHERE tenant_id=?", (tenant_id,)
    ).fetchone()["n"]
    active = conn.execute(
        "SELECT COUNT(DISTINCT employee_id) AS n FROM answers WHERE tenant_id=?", (tenant_id,)
    ).fetchone()["n"]
    conn.close()

    per_topic = {}
    for r in topic_rows:
        answered = r["answered"]
        correct = r["correct"]
        pct = (correct / answered) * 100.0 if answered else 0.0
        per_topic[r["topic"]] = {
            "correct_pct": round(pct, 2),
            "answered": answered,
            "correct": correct,
        }
    weakest = sorted(per_topic, key=lambda t: (per_topic[t]["correct_pct"], t))
    participation = (active / total) * 100.0 if total else 0.0
    return {
        "per_topic": per_topic,
        "participation_pct": participation,
        "weakest_topics": weakest,
        "active_employees": active,
    }
