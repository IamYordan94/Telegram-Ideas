"""StaffQuiz — Telegram bot (group delivery adapter).

One bot, many company groups. Each tenant (a company) gets:
- a daily question OR flashcard posted to their group (branded with their name)
- questions carry A/B/C/D tap-to-answer buttons → toast + DM with result/explanation
- flashcards hide the answer behind a Telegram spoiler (tap to reveal)
- a weekly leaderboard (overall top 10 + department champions)
Employees register with /start (name → department → language).
The owner (STAFFQUIZ_OWNER_ADMIN_ID) manages companies from the bot chat.

CORE CONTRACT (consumed from `staffquiz.core`, built in parallel):
  bank.load_bank(banks_dir, filename)  -> list of items, each:
      {"type": "question",  "q","options"(4),"answer"(0-3),"explain"?,"topic"?}
      {"type": "flashcard", "front","back","explain"?,"topic"?}
  bank.next_item(bank, q_index)        -> (item, position)  (cycles the bank)
  schedule.pick_bank(tenant, weekday)  -> bank filename (fun override or default_bank)
  schedule.parse_fun_config("fri:a.json") -> {"friday":"a.json"}
  db.add_tenant(db_path, slug, name, group_id=, default_bank=, fun_banks=, quiz_time=)
  db.get_tenant / get_tenant_by_id / list_tenants   (fun_banks returned as dict)
  db.set_q_index / db.set_active
  db.upsert_employee(db_path, tenant_id, uid, name, department, language) -> employee id
  db.get_employee(db_path, tenant_id, uid)
  db.record_answer(db_path, tenant_id, employee_id, item_index, correct, topic=) -> bool
  db.week_leaderboard(db_path, tenant_id, days=7, limit=10)  (rows: correct/answered)
  db.department_board(db_path, tenant_id, days=7)
  db.streak_days(db_path, employee_id) -> int
  db.aggregate_report(db_path, tenant_id) -> {per_topic, participation_pct,
                                               weakest_topics, active_employees}

Things the core does NOT provide (kept here, in the adapter):
  - `paid_until` subscription handling (/paid) — added as an extra column on the
    shared tenants table plus a `tenant_paid_ok`-style helper.
  - tenant lookup by group id (registration/`/me` resolve the company).
  - a `telegram_posts` table recording which item was posted at each q_index,
    so answers can be graded without re-loading the (possibly fun-overridden) bank.
"""
import html
import json
import logging
import sqlite3
import sys
from datetime import date, timedelta
from datetime import time as dtime
from pathlib import Path

# ── import plumbing ─────────────────────────────────────────────────────────
# Our adapter folder is literally named `telegram/`, which collides with
# python-telegram-bot's own `telegram` package. So we must NOT put the
# staffquiz repo root on sys.path (it contains a `telegram/` subfolder that
# would shadow PTB). We add only the two dirs we actually need:
_THIS_DIR = Path(__file__).resolve().parent          # .../staffquiz/telegram
_REPO_ROOT = _THIS_DIR.parent                          # .../staffquiz
_PRODUCTS_DIR = _REPO_ROOT.parent                      # .../E2 - SaaS Bots
for _p in (_THIS_DIR, _PRODUCTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters,
)

import config
from staffquiz.core import bank, db, schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staffquiz")

LETTERS = ["A", "B", "C", "D"]
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
LANGUAGE_LABELS = {
    "nl": "🇳🇱 Nederlands", "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский", "ua": "🇺🇦 Українська",
}
LEADERBOARD_DAY = WEEKDAYS["sunday"]   # weekly leaderboard posts on Sunday
LEADERBOARD_TIME = "18:00"

# ConversationHandler states
NAME, DEPARTMENT, LANGUAGE, PICK = range(4)


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def parse_hm(s: str):
    """'HH:MM' -> (hour, minute). Raises ValueError on bad input."""
    try:
        h, m = s.strip().split(":")
        h, m = int(h), int(m)
    except (ValueError, AttributeError):
        raise ValueError(f"bad time '{s}' — use HH:MM")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"bad time '{s}' — use HH:MM")
    return h, m


def item_kind(item) -> str:
    """'flashcard' when the item's type is flashcard, otherwise 'question'."""
    if item.get("type") == "flashcard":
        return "flashcard"
    return "question"


# ── owner gate ──

def owner_only(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    return uid == config.OWNER_ADMIN_ID


# ── callback data (pure encode/decode — colon-separated, 4 parts) ───────────

def encode_answer_callback(tenant_id, q_index, letter_index) -> str:
    return f"ans:{tenant_id}:{q_index}:{letter_index}"


def decode_answer_callback(data: str):
    """Return (tenant_id, q_index, letter) or None when malformed."""
    if not data:
        return None
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "ans":
        return None
    try:
        return int(parts[1]), int(parts[2]), int(parts[3])
    except ValueError:
        return None


# ── message builders (pure functions) ───────────────────────────────────────

def build_question_text(tenant, item, q_index) -> str:
    lines = [
        f"🎯 <b>{esc(tenant['name'])}</b> — question #{q_index + 1}",
        "",
        esc(item["q"]),
        "",
    ]
    for i, opt in enumerate(item["options"]):
        lines.append(f"{LETTERS[i]}. {esc(opt)}")
    lines.append("")
    lines.append("Tap your answer 👇")
    return "\n".join(lines)


def build_flashcard_text(tenant, item, q_index) -> str:
    lines = [
        f"🃏 <b>{esc(tenant['name'])}</b> — Flashcard #{q_index + 1}",
        "",
        f"<b>Front:</b> {esc(item['front'])}",
        "",
        f"<b>Back:</b> <tg-spoiler>{esc(item['back'])}</tg-spoiler>",
        "",
        "👆 Tap to reveal",
    ]
    return "\n".join(lines)


def build_leaderboard_text(tenant, top, departments) -> str:
    lines = [f"🏆 <b>{esc(tenant['name'])}</b> — weekly leaderboard", ""]
    if not top:
        lines.append("No answers yet this week — be first today! 😉")
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines.append("<b>Top 10</b>")
        for i, row in enumerate(top):
            mark = medals[i] if i < 3 else f"{i + 1}."
            who = esc(row.get("name") or row.get("uid") or "?")
            lines.append(f"{mark} {who} — {row['correct']} ✅")
    if departments:
        lines.append("")
        lines.append("<b>Department champions</b>")
        for d in departments:
            who = esc(d.get("name") or d.get("uid") or "?")
            lines.append(f"🏢 {esc(d.get('department') or '—')} — {who} ({d['correct']} ✅)")
    lines.append("")
    lines.append("New question every day — tap to keep your spot.")
    return "\n".join(lines)


def build_report_text(tenant, report) -> str:
    """Aggregate + anonymous manager report. Deliberately has NO per-employee
    lines — that is a privacy design decision, not an omission (see README)."""
    lines = [f"📊 <b>{esc(tenant['name'])}</b> — staff report (aggregate, anonymous)", ""]
    lines.append(f"Active employees: <b>{report.get('active_employees', 0)}</b>")
    lines.append(f"Participation: <b>{report.get('participation_pct', 0.0):.0f}%</b>")
    per_topic = report.get("per_topic") or {}
    if per_topic:
        lines.append("")
        lines.append("<b>By topic</b>")
        for topic in sorted(per_topic):
            t = per_topic[topic]
            lines.append(f"• {esc(topic)} — {t['correct']}/{t['answered']} ({t['correct_pct']:.0f}%)")
    weakest = report.get("weakest_topics") or []
    if weakest:
        lines.append("")
        lines.append(f"<b>Weakest topics:</b> {esc(', '.join(weakest))}")
    return "\n".join(lines)


def answer_keyboard(tenant_id, q_index):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(LETTERS[i], callback_data=encode_answer_callback(tenant_id, q_index, i))
        for i in range(4)
    ]])


# ── adapter-local persistence helpers (sqlite, same file as the core db) ────

def _raw_conn():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_paid_column():
    """Add the `paid_until` column the core tenants table doesn't have (yet)."""
    conn = _raw_conn()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tenants)")}
        if "paid_until" not in cols:
            conn.execute("ALTER TABLE tenants ADD COLUMN paid_until TEXT")
            conn.commit()
    finally:
        conn.close()


def _tenant_paid_ok(tenant) -> bool:
    """paid_until NULL = unlimited (demo). Otherwise must be today or later."""
    until = tenant.get("paid_until")
    if not until:
        return True
    try:
        return date.fromisoformat(until) >= date.today()
    except ValueError:
        return False


def _extend_paid(tenant_id, days) -> str:
    """Extend paid_until by `days` from today (or from current expiry if later)."""
    _ensure_paid_column()
    conn = _raw_conn()
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


def _set_fun_banks(tenant_id, fun_map) -> None:
    """Store a fun-bank override map as JSON (the core reads it back as a dict)."""
    conn = _raw_conn()
    conn.execute("UPDATE tenants SET fun_banks=? WHERE id=?", (json.dumps(fun_map), tenant_id))
    conn.commit()
    conn.close()


_POSTS_SCHEMA = """CREATE TABLE IF NOT EXISTS telegram_posts (
    tenant_id INTEGER NOT NULL,
    q_index INTEGER NOT NULL,
    item_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, q_index)
);"""


def _ensure_posts_table():
    conn = _raw_conn()
    conn.execute(_POSTS_SCHEMA)
    conn.commit()
    conn.close()


def _store_post(tenant_id, q_index, item):
    """Remember which item was posted at this q_index so answers grade offline
    (the post may have come from a fun-override bank, not the default one)."""
    _ensure_posts_table()
    conn = _raw_conn()
    conn.execute(
        "INSERT OR REPLACE INTO telegram_posts (tenant_id, q_index, item_json) VALUES (?, ?, ?)",
        (tenant_id, q_index, json.dumps(item)),
    )
    conn.commit()
    conn.close()


def _get_post(tenant_id, q_index):
    _ensure_posts_table()
    conn = _raw_conn()
    row = conn.execute(
        "SELECT item_json FROM telegram_posts WHERE tenant_id=? AND q_index=?",
        (tenant_id, q_index),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["item_json"])
    except (ValueError, TypeError):
        return None


def _find_tenant_by_group(group_id):
    g = str(group_id)
    for t in db.list_tenants(config.DB_PATH):
        if (t.get("group_id") or "") == g:
            return t
    return None


def _employee_week_correct(tenant_id, employee_id, days=7) -> int:
    for row in db.week_leaderboard(config.DB_PATH, tenant_id, days=days, limit=10 ** 6):
        if row["employee_id"] == employee_id:
            return row["correct"]
    return 0


# ── scheduled posting ──

async def post_daily_item(context, tenant_id):
    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t or not t["active"]:
        return
    if not _tenant_paid_ok(t):
        logger.info("tenant %s unpaid — skipping daily item", t["slug"])
        return
    weekday = _today_weekday()
    bank_file = schedule.pick_bank(t, weekday)
    try:
        b = bank.load_bank(config.BANKS_DIR, bank_file)
    except Exception as e:
        logger.error("tenant %s bank %s failed to load: %s", t["slug"], bank_file, e)
        return
    item, _ = bank.next_item(b, t["q_index"])

    if item_kind(item) == "flashcard":
        msg = await context.bot.send_message(
            chat_id=t["group_id"],
            text=build_flashcard_text(t, item, t["q_index"]),
            parse_mode=ParseMode.HTML,
        )
    else:
        msg = await context.bot.send_message(
            chat_id=t["group_id"],
            text=build_question_text(t, item, t["q_index"]),
            parse_mode=ParseMode.HTML,
            reply_markup=answer_keyboard(t["id"], t["q_index"]),
        )
    _store_post(t["id"], t["q_index"], item)
    # advance the rotation only after the post actually landed
    db.set_q_index(config.DB_PATH, t["id"], t["q_index"] + 1)
    logger.info("tenant %s: posted %s #%s (mid %s)",
                t["slug"], item_kind(item), t["q_index"] + 1, msg.message_id)
    return msg


async def post_leaderboard(context, tenant_id):
    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t or not t["active"]:
        return
    top = db.week_leaderboard(config.DB_PATH, t["id"], days=7, limit=10)
    departments = db.department_board(config.DB_PATH, t["id"], days=7)
    await context.bot.send_message(
        chat_id=t["group_id"],
        text=build_leaderboard_text(t, top, departments),
        parse_mode=ParseMode.HTML,
    )
    logger.info("tenant %s: leaderboard posted", t["slug"])


def _today_weekday() -> str:
    return date.today().strftime("%A").lower()


# ── jobs → handlers ──

async def job_post_item(context):
    await post_daily_item(context, context.job.data["tenant_id"])


async def job_post_leaderboard(context):
    await post_leaderboard(context, context.job.data["tenant_id"])


# ── answering ──

async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parsed = decode_answer_callback(q.data)
    if parsed is None:
        await q.answer()
        return
    tenant_id, q_index, letter = parsed
    uid = update.effective_user.id

    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t:
        await q.answer("Quiz not found.")
        return
    # Employees must register first so answers attribute to a named person.
    emp = db.get_employee(config.DB_PATH, tenant_id, str(uid))
    if not emp:
        await q.answer("Register with /start first")
        return
    item = _get_post(tenant_id, q_index)
    if not item or item_kind(item) != "question":
        await q.answer()
        return

    correct = letter == item["answer"]
    # topic for the aggregate report: item's own tag, else the default bank name
    topic = item.get("topic") or t.get("default_bank")
    recorded = db.record_answer(config.DB_PATH, tenant_id, emp["id"], q_index, correct, topic=topic)
    week = _employee_week_correct(tenant_id, emp["id"])

    if correct:
        await q.answer(f"✅ Correct! (+1 — {week} this week)")
    else:
        await q.answer(f"❌ Wrong — it was {LETTERS[item['answer']]}")

    if not recorded:
        return  # already answered this question earlier — no double points

    # DM the employee the full result (name/explanation/streak/week score).
    streak = db.streak_days(config.DB_PATH, emp["id"])
    if correct:
        verdict = "✅ <b>Correct!</b>"
    else:
        right = item["options"][item["answer"]]
        verdict = f"❌ <b>Wrong</b> — it was {LETTERS[item['answer']]}: {esc(right)}"
    lines = [
        f"🎯 <b>{esc(t['name'])}</b> — question #{q_index + 1}",
        "",
        verdict,
    ]
    if item.get("explain"):
        lines.append("")
        lines.append(f"💡 {esc(item['explain'])}")
    lines.append("")
    lines.append(f"📊 Your week: <b>{week}</b> correct")
    lines.append(f"🔥 Streak: <b>{streak}</b>")
    try:
        await context.bot.send_message(chat_id=uid, text="\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception:
        pass  # user blocked the bot — fine


# ── employee registration (/start → name → department → language) ───────────

def company_keyboard(tenants):
    """Pick-a-company inline keyboard. None when 0 or 1 company (single auto-assigns)."""
    if len(tenants) <= 1:
        return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["name"], callback_data=f"pick:{t['id']}")]
        for t in tenants
    ])


async def reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    tenant = _find_tenant_by_group(chat.id)
    if tenant:
        context.user_data["tenant_id"] = tenant["id"]
        context.user_data["tenant_name"] = tenant["name"]
        await update.effective_message.reply_text(
            f"👋 Welcome to <b>{esc(tenant['name'])}</b> staff training!\nWhat's your name?",
            parse_mode=ParseMode.HTML,
        )
        return NAME
    if chat.type == "private":
        tenants = [t for t in db.list_tenants(config.DB_PATH) if t["active"]]
        if not tenants:
            await update.effective_message.reply_text(
                "No company is set up yet.\n"
                "The owner adds one by running /addcompany INSIDE the company group."
            )
            return ConversationHandler.END
        if len(tenants) == 1:
            context.user_data["tenant_id"] = tenants[0]["id"]
            context.user_data["tenant_name"] = tenants[0]["name"]
            await update.effective_message.reply_text(
                f"👋 Welcome to <b>{esc(tenants[0]['name'])}</b> staff training!\nWhat's your name?",
                parse_mode=ParseMode.HTML,
            )
            return NAME
        await update.effective_message.reply_text(
            "Which company are you with?", reply_markup=company_keyboard(tenants),
        )
        return PICK
    await update.effective_message.reply_text(
        "Run /start inside your company's group chat, or in a private chat with me."
    )
    return ConversationHandler.END


async def reg_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tid = int(q.data.split(":", 1)[1])
    t = db.get_tenant_by_id(config.DB_PATH, tid)
    if not t:
        await q.edit_message_text("Unknown company — /start again.")
        return ConversationHandler.END
    context.user_data["tenant_id"] = t["id"]
    context.user_data["tenant_name"] = t["name"]
    await q.edit_message_text(
        f"👋 Welcome to <b>{esc(t['name'])}</b> staff training!\nWhat's your name?",
        parse_mode=ParseMode.HTML,
    )
    return NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("Please type your name.")
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text(f"Thanks, {esc(name)}! Which department are you in?")
    return DEPARTMENT


async def reg_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dept = (update.message.text or "").strip()
    if not dept:
        await update.message.reply_text("Please type your department.")
        return DEPARTMENT
    context.user_data["department"] = dept
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(label, callback_data=f"lang:{code}")
        for code, label in LANGUAGE_LABELS.items()
    ]])
    await update.message.reply_text("Choose your language:", reply_markup=kb)
    return LANGUAGE


async def reg_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    code = q.data.split(":", 1)[1]
    if code not in LANGUAGE_LABELS:
        await q.edit_message_text("Unknown language — /start again.")
        return ConversationHandler.END
    context.user_data["language"] = code
    tid = context.user_data["tenant_id"]
    uid = update.effective_user.id
    db.upsert_employee(
        config.DB_PATH, tid, str(uid),
        context.user_data["name"], context.user_data["department"], code,
    )
    await q.edit_message_text(
        f"✅ Registered, <b>{esc(context.user_data['name'])}</b>!\n"
        f"Department: {esc(context.user_data['department'])}\n"
        f"Language: {LANGUAGE_LABELS[code]}\n\n"
        f"A quiz question or flashcard drops every day — tap your answer!\n"
        f"Check yourself anytime with /me.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled. /start anytime to try again.")
    return ConversationHandler.END


# ── employee command ──

async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    uid = update.effective_user.id
    tenant = _find_tenant_by_group(chat_id)
    if not tenant:
        await update.message.reply_text("Run /me inside your company's group chat.")
        return
    emp = db.get_employee(config.DB_PATH, tenant["id"], str(uid))
    if not emp:
        await update.message.reply_text("Not registered yet — /start first.")
        return
    week = _employee_week_correct(tenant["id"], emp["id"])
    streak = db.streak_days(config.DB_PATH, emp["id"])
    await update.message.reply_text(
        f"👤 <b>{esc(emp['name'])}</b>\n"
        f"🏢 {esc(tenant['name'])}\n"
        f"🗂 {esc(emp['department'])}\n"
        f"🌐 {esc(emp['language'])}\n"
        f"🔥 Streak: <b>{streak}</b>\n"
        f"✅ This week: <b>{week}</b> correct",
        parse_mode=ParseMode.HTML,
    )


# ── owner commands ──

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if owner_only(update):
        await update.message.reply_text(
            "🧠 <b>StaffQuiz owner console</b>\n\n"
            "/addcompany slug|Name|group_id|bank|HH:MM\n"
            "/fun slug friday:scifi.json,saturday:general.json\n"
            "/report slug — aggregate staff report (DM, anonymous)\n"
            "/quiznow slug · /leaderboard slug\n"
            "/tenants · /paid slug N · /suspend slug · /activate slug\n"
            "/me — your own stats",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "👋 I'm your company's daily training bot.\n"
            "/start — register\n"
            "/me — your stats",
            parse_mode=ParseMode.HTML,
        )


async def cmd_tenants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    rows = db.list_tenants(config.DB_PATH)
    if not rows:
        await update.message.reply_text("No companies yet — /addcompany to create one.")
        return
    lines = ["📋 <b>Companies</b>", ""]
    for t in rows:
        paid = t.get("paid_until") or "free"
        status = "🟢" if (t["active"] and _tenant_paid_ok(t)) else "🔴"
        lines.append(
            f"{status} <b>{esc(t['slug'])}</b> — {esc(t['name'])} · bank {esc(t['default_bank'])} · "
            f"{esc(t['quiz_time'])} · q#{t['q_index']} · paid: {esc(paid)}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


def parse_addcompany_args(text, chat_type, chat_id):
    """Parse an /addcompany message into [slug, name, group, bank, qtime].

    Two accepted forms:
      5 parts: slug|Name|group_id|bank|HH:MM   (group id or @username; remote setup)
      4 parts: slug|Name|bank|HH:MM            (sent FROM the company group — that group is used)
    Returns (parts_list_or_empty, error_message_or_empty).
    """
    arg = text.split(" ", 1)[1] if " " in text else ""
    parts = [p.strip() for p in arg.split("|")] if arg else []
    if len(parts) == 5:
        return parts, ""
    if len(parts) == 4 and chat_type in ("group", "supergroup"):
        return [parts[0], parts[1], str(chat_id), parts[2], parts[3]], ""
    return [], (
        "Format: /addcompany slug|Name|group_id|bank|HH:MM\n"
        "or — much easier — run it INSIDE the company group as:\n"
        "/addcompany slug|Name|bank|HH:MM"
    )


async def cmd_addcompany(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    parts, err = parse_addcompany_args(
        update.message.text, update.effective_chat.type, update.effective_chat.id,
    )
    if err:
        await update.message.reply_text(err)
        return
    slug, name, group, bankname, qtime = parts
    if not slug or not name or not group or not bankname:
        await update.message.reply_text("Every field must be filled — no empty slots.")
        return
    if db.get_tenant(config.DB_PATH, slug):
        await update.message.reply_text(f"Slug '{slug}' already exists.")
        return
    try:
        bank.load_bank(config.BANKS_DIR, bankname)
    except Exception as e:
        await update.message.reply_text(f"Bank '{bankname}' failed to load: {e}")
        return
    try:
        parse_hm(qtime)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return
    try:
        chat = await context.bot.get_chat(group)
    except Exception as e:
        await update.message.reply_text(
            f"Group '{group}' not reachable: {e}\n"
            "The bot must already be an admin of the group."
        )
        return
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            f"'{group}' is not a group — StaffQuiz posts into groups/supergroups only."
        )
        return
    tid = db.add_tenant(config.DB_PATH, slug, name, str(chat.id), bankname, quiz_time=qtime)
    t = db.get_tenant_by_id(config.DB_PATH, tid)
    _schedule_tenant(context.application, t)
    await update.message.reply_text(
        f"✅ Company <b>{esc(name)}</b> live.\n"
        f"Daily quiz at {esc(qtime)} in {esc(group)}.\n"
        f"Subscription: run /paid {esc(slug)} N (free month to start if you want).",
        parse_mode=ParseMode.HTML,
    )
    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                f"👋 <b>{esc(name)}</b> staff training is live!\n"
                f"A question or flashcard drops every day at <b>{esc(qtime)}</b>.\n"
                f"Register with /start in a private chat with me, "
                f"then tap your answers right here."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass  # group welcome is best-effort


async def cmd_fun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    parts = update.message.text.split(" ", 2)
    if len(parts) != 3:
        await update.message.reply_text("Usage: /fun slug friday:scifi.json,saturday:general.json")
        return
    slug, config_str = parts[1], parts[2]
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    try:
        fun = schedule.parse_fun_config(config_str)
    except ValueError as e:
        await update.message.reply_text(f"Bad fun config: {e}")
        return
    _set_fun_banks(t["id"], fun)
    lines = [f"✅ Fun banks for '{slug}':", ""]
    for day in sorted(fun):
        lines.append(f"{day.capitalize()}: {esc(fun[day])}")
    lines.append("")
    lines.append("All other days keep the default bank.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    report = db.aggregate_report(config.DB_PATH, t["id"])
    # PRIVACY: this report is deliberately aggregate + anonymous. There are no
    # per-employee lines here and there never will be — managers see gaps, not
    # people (that's both the pitch and the legal-safe design, see README).
    await update.message.reply_text(build_report_text(t, report), parse_mode=ParseMode.HTML)


async def cmd_quiznow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    try:
        await post_daily_item(context, t["id"])
        await update.message.reply_text(f"✅ Item posted to {t['group_id']}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Post failed: {e}")


async def cmd_leaderboard_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    try:
        await post_leaderboard(context, t["id"])
        await update.message.reply_text(f"✅ Leaderboard posted to {t['group_id']}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Post failed: {e}")


async def cmd_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    parts = update.message.text.split()
    if len(parts) != 3:
        await update.message.reply_text("Usage: /paid slug 30")
        return
    slug, days_s = parts[1], parts[2]
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    try:
        days = int(days_s)
    except ValueError:
        await update.message.reply_text("Days must be a number.")
        return
    until = _extend_paid(t["id"], days)
    await update.message.reply_text(f"✅ '{slug}' paid until {until}.")


async def cmd_suspend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    db.set_active(config.DB_PATH, t["id"], False)
    await update.message.reply_text(f"⏸️ '{slug}' suspended (no more questions posted).")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No company '{slug}'.")
        return
    db.set_active(config.DB_PATH, t["id"], True)
    await update.message.reply_text(f"▶️ '{slug}' active again.")


# ── application ──

def _schedule_tenant(app: Application, t):
    h, m = parse_hm(t["quiz_time"])
    app.job_queue.run_daily(
        job_post_item, time=dtime(hour=h, minute=m),
        data={"tenant_id": t["id"]}, name=f"quiz:{t['id']}",
    )
    h2, m2 = parse_hm(LEADERBOARD_TIME)
    app.job_queue.run_daily(
        job_post_leaderboard, time=dtime(hour=h2, minute=m2), days=(LEADERBOARD_DAY,),
        data={"tenant_id": t["id"]}, name=f"lb:{t['id']}",
    )


def build_application() -> Application:
    db.init_db(config.DB_PATH)
    _ensure_paid_column()
    _ensure_posts_table()
    app = Application.builder().token(config.BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", reg_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_department)],
            LANGUAGE: [CallbackQueryHandler(reg_language, pattern="^lang:")],
            PICK: [CallbackQueryHandler(reg_pick, pattern="^pick:")],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("addcompany", cmd_addcompany))
    app.add_handler(CommandHandler("fun", cmd_fun))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("quiznow", cmd_quiznow))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard_now))
    app.add_handler(CommandHandler("tenants", cmd_tenants))
    app.add_handler(CommandHandler("paid", cmd_paid))
    app.add_handler(CommandHandler("suspend", cmd_suspend))
    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CallbackQueryHandler(on_answer, pattern="^ans:"))

    for t in db.list_tenants(config.DB_PATH):
        _schedule_tenant(app, t)

    return app


def main():
    if not config.ready():
        print("Missing config. Set STAFFQUIZ_BOT_TOKEN and STAFFQUIZ_OWNER_ADMIN_ID in .env")
        return
    app = build_application()
    logger.info("StaffQuiz starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
