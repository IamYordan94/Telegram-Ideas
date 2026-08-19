"""QuizDay — Telegram bot.

One bot, many customer channels. Each tenant gets:
- a daily question posted to their channel (branded with their name)
- tap-to-answer buttons (A/B/C/D) — feedback via toast + DM
- a weekly leaderboard post
Owner (QUIZ_OWNER_ADMIN_ID) manages tenants from the bot chat.
"""
import html
import logging
from datetime import time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)

from quiz import config, db, bank

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("quizday")

LETTERS = ["A", "B", "C", "D"]
WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


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


# ── owner gate ──

def owner_only(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    return uid == config.OWNER_ADMIN_ID


# ── message builders ──

def question_text(tenant, q, q_index) -> str:
    lines = [
        f"🎯 <b>{esc(tenant['name'])}</b> — question #{q_index + 1}",
        "",
        esc(q["q"]),
        "",
    ]
    for i, opt in enumerate(q["options"]):
        lines.append(f"{LETTERS[i]}. {esc(opt)}")
    lines.append("")
    lines.append("Tap your answer 👇")
    return "\n".join(lines)


def answer_keyboard(tenant_id, q_index):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(LETTERS[i], callback_data=f"ans:{tenant_id}:{q_index}:{i}")
        for i in range(4)
    ]])


# ── scheduled posting ──

async def post_question(context, tenant_id):
    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t or not t["active"]:
        return
    if not db.tenant_paid_ok(t):
        logger.info("tenant %s unpaid — skipping daily question", t["slug"])
        return
    try:
        b = bank.load_bank(config.BANKS_DIR, t["bank"])
    except Exception as e:
        logger.error("tenant %s bank failed to load: %s", t["slug"], e)
        return
    q, _ = bank.next_question(b, t["q_index"])
    msg = await context.bot.send_message(
        chat_id=t["channel_id"],
        text=question_text(t, q, t["q_index"]),
        parse_mode=ParseMode.HTML,
        reply_markup=answer_keyboard(t["id"], t["q_index"]),
    )
    db.set_tenant_q_index(config.DB_PATH, t["id"], t["q_index"] + 1)
    logger.info("tenant %s: posted question #%s (mid %s)", t["slug"], t["q_index"] + 1, msg.message_id)
    return msg


async def post_leaderboard(context, tenant_id):
    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t or not t["active"]:
        return
    top = db.week_top(config.DB_PATH, t["id"], days=7, limit=10)
    lines = [f"🏆 <b>{esc(t['name'])}</b> — weekly leaderboard", ""]
    if not top:
        lines.append("No answers yet this week — be first tomorrow! 😉")
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(top):
            mark = medals[i] if i < 3 else f"{i + 1}."
            who = esc(row["username"] or f"player {row['user_id']}")
            lines.append(f"{mark} {who} — {row['n']} ✅")
        lines.append("")
        lines.append("New question every day — tap to keep your spot.")
    await context.bot.send_message(
        chat_id=t["channel_id"],
        text="\n".join(lines),
        parse_mode=ParseMode.HTML,
    )
    logger.info("tenant %s: leaderboard posted", t["slug"])


# ── jobs → handlers ──

async def job_post_question(context):
    await post_question(context, context.job.data["tenant_id"])


async def job_post_leaderboard(context):
    await post_leaderboard(context, context.job.data["tenant_id"])


# ── answering ──

async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) != 4:
        await q.answer()
        return
    _, tenant_id_s, q_index_s, letter_s = parts
    try:
        tenant_id, q_index, letter = int(tenant_id_s), int(q_index_s), int(letter_s)
    except ValueError:
        await q.answer()
        return
    uid = update.effective_user.id
    uname = update.effective_user.username or update.effective_user.first_name or str(uid)

    t = db.get_tenant_by_id(config.DB_PATH, tenant_id)
    if not t:
        await q.answer("Quiz not found.")
        return
    try:
        b = bank.load_bank(config.BANKS_DIR, t["bank"])
    except Exception:
        await q.answer("This question is no longer available.")
        return
    question, _ = bank.next_question(b, q_index)

    correct = letter == question["answer"]
    recorded = db.record_answer(config.DB_PATH, tenant_id, uid, uname, q_index, correct)
    week = db.user_week_correct(config.DB_PATH, tenant_id, uid)

    if correct:
        await q.answer(f"✅ Correct! (+1 — {week} this week)")
    else:
        await q.answer(f"❌ Wrong — it was {LETTERS[question['answer']]}")

    if not recorded:
        return  # already answered this question earlier — no double points

    if correct:
        verdict = "✅ <b>Correct!</b>"
    else:
        right = question["options"][question["answer"]]
        verdict = f"❌ <b>Wrong</b> — it was {LETTERS[question['answer']]}: {esc(right)}"
    lines = [
        f"🎯 <b>{esc(t['name'])}</b> — question #{q_index + 1}",
        "",
        verdict,
    ]
    if question.get("explain"):
        lines.append("")
        lines.append(f"💡 {esc(question['explain'])}")
    lines.append("")
    lines.append(f"📊 Your week: <b>{week}</b> correct")
    try:
        await context.bot.send_message(
            chat_id=uid,
            text="\n".join(lines),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass  # user blocked the bot — fine


# ── owner commands ──

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if owner_only(update):
        await update.message.reply_text(
            "🧠 <b>QuizDay owner console</b>\n\n"
            "/tenants — all customers\n"
            "/addquiz slug|Name|channel_id|bank|HH:MM — add a customer\n"
            "/quiznow slug — post today's question now (test)\n"
            "/leaderboard slug — post the leaderboard now (test)\n"
            "/paid slug 30 — extend subscription by N days\n"
            "/suspend slug · /activate slug\n"
            "/banks — available question banks",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            "🎯 I post a daily quiz into channels. Ask the channel owner about their quiz!"
        )


async def cmd_tenants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    rows = db.list_tenants(config.DB_PATH)
    if not rows:
        await update.message.reply_text("No customers yet — /addquiz to create one.")
        return
    lines = ["📋 <b>Customers</b>", ""]
    for t in rows:
        paid = t["paid_until"] or "free"
        if t["active"] and db.tenant_paid_ok(t):
            status = "🟢"
        else:
            status = "🔴"
        lines.append(
            f"{status} <b>{esc(t['slug'])}</b> — {esc(t['name'])} · bank {esc(t['bank'])} · "
            f"{esc(t['quiz_time'])} · q#{t['q_index']} · paid: {esc(paid)}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_addquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    arg = update.message.text.split(" ", 1)[1] if " " in update.message.text else ""
    parts = arg.split("|")
    if len(parts) != 5:
        await update.message.reply_text(
            "Format: /addquiz slug|Name|channel_id|bank|HH:MM\n"
            "channel_id can be numeric (-100...) or @username. Use /banks for bank names."
        )
        return
    slug, name, channel, bankname, qtime = (p.strip() for p in parts)
    if not slug or not name or not channel or not bankname:
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
        chat = await context.bot.get_chat(channel)
    except Exception as e:
        await update.message.reply_text(
            f"Channel '{channel}' not reachable: {e}\n"
            "The bot must already be an admin of the channel."
        )
        return
    if chat.type != "channel":
        await update.message.reply_text(f"'{channel}' is not a channel — QuizDay posts into channels only.")
        return
    tid = db.add_tenant(config.DB_PATH, slug, name, str(chat.id), bankname, quiz_time=qtime)
    t = db.get_tenant_by_id(config.DB_PATH, tid)
    _schedule_tenant(context.application, t)
    await update.message.reply_text(
        f"✅ Customer <b>{esc(name)}</b> live.\n"
        f"Daily question at {esc(qtime)} in {esc(channel)}.\n"
        "Subscription: run /paid slug N (they get a free month to start if you want).",
        parse_mode=ParseMode.HTML,
    )


async def cmd_quiznow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No customer '{slug}'.")
        return
    try:
        await post_question(context, t["id"])
        await update.message.reply_text(f"✅ Question posted to {t['channel_id']}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Post failed: {e}")


async def cmd_leaderboard_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No customer '{slug}'.")
        return
    try:
        await post_leaderboard(context, t["id"])
        await update.message.reply_text(f"✅ Leaderboard posted to {t['channel_id']}.")
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
        await update.message.reply_text(f"No customer '{slug}'.")
        return
    try:
        days = int(days_s)
    except ValueError:
        await update.message.reply_text("Days must be a number.")
        return
    until = db.extend_paid(config.DB_PATH, t["id"], days)
    await update.message.reply_text(f"✅ '{slug}' paid until {until}.")


async def cmd_suspend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No customer '{slug}'.")
        return
    db.set_tenant_active(config.DB_PATH, t["id"], False)
    await update.message.reply_text(f"⏸️ '{slug}' suspended (no more questions posted).")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    slug = update.message.text.split(" ", 1)[1].strip() if " " in update.message.text else ""
    t = db.get_tenant(config.DB_PATH, slug)
    if not t:
        await update.message.reply_text(f"No customer '{slug}'.")
        return
    db.set_tenant_active(config.DB_PATH, t["id"], True)
    await update.message.reply_text(f"▶️ '{slug}' active again.")


async def cmd_banks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return
    from pathlib import Path
    files = sorted(p.name for p in Path(config.BANKS_DIR).glob("*.json"))
    await update.message.reply_text("📚 Banks: " + (", ".join(files) if files else "none yet"))


# ── application ──

def _schedule_tenant(app: Application, t):
    h, m = parse_hm(t["quiz_time"])
    app.job_queue.run_daily(
        job_post_question, time=dtime(hour=h, minute=m),
        data={"tenant_id": t["id"]}, name=f"quiz:{t['id']}",
    )
    day = WEEKDAYS.get((t["leaderboard_day"] or "sunday").lower(), 6)
    h2, m2 = parse_hm(t["leaderboard_time"])
    app.job_queue.run_daily(
        job_post_leaderboard, time=dtime(hour=h2, minute=m2), days=(day,),
        data={"tenant_id": t["id"]}, name=f"lb:{t['id']}",
    )


def build_application() -> Application:
    db.init_db(config.DB_PATH)
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("tenants", cmd_tenants))
    app.add_handler(CommandHandler("addquiz", cmd_addquiz))
    app.add_handler(CommandHandler("quiznow", cmd_quiznow))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard_now))
    app.add_handler(CommandHandler("paid", cmd_paid))
    app.add_handler(CommandHandler("suspend", cmd_suspend))
    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CommandHandler("banks", cmd_banks))
    app.add_handler(CallbackQueryHandler(on_answer, pattern="^ans:"))

    for t in db.list_tenants(config.DB_PATH):
        _schedule_tenant(app, t)

    return app


def main():
    if not config.ready():
        print("Missing config. Set QUIZ_BOT_TOKEN and QUIZ_OWNER_ADMIN_ID in .env")
        return
    app = build_application()
    logger.info("QuizDay starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
