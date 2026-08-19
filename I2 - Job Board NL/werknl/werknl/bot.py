"""WerkNL — Telegram bot.

Worker side: subscribe to sectors, get job alerts.
Employer side: /post to submit a job.
Admin side: /approve, /reject, /fill, /stats, /grant, /setpremium, /broadcast.
"""
import logging
from datetime import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)

from werknl import config, db
from werknl.constants import SECTORS, PRICING
from werknl.formatting import job_post_text, pricing_text, job_dm_text, contact_url, respond_label
from werknl.digest import post_job_to_channel, notify_premium_workers, daily_digest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("werknl")

# Conversation states for /post
(TITLE, SECTOR, AREA, PAY, HOURS, DESCRIPTION, CONTACT, CONFIRM) = range(8)


# ── helpers ──

def sector_keyboard(selected):
    rows = []
    for key, meta in SECTORS.items():
        mark = "✅ " if key in selected else ""
        rows.append([InlineKeyboardButton(
            f"{mark}{meta['emoji']} {meta['label']}", callback_data=f"sector:{key}")])
    rows.append([
        InlineKeyboardButton("➕ All three", callback_data="sector:all"),
        InlineKeyboardButton("🗑 Clear", callback_data="sector:clear"),
    ])
    rows.append([InlineKeyboardButton("✅ Done", callback_data="sector:done")])
    return InlineKeyboardMarkup(rows)


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👷 I'm looking for work", callback_data="menu:sectors")],
        [InlineKeyboardButton("🏢 I'm an employer", callback_data="menu:employer")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="menu:help")],
    ])


def is_admin(update: Update) -> bool:
    uid = update.effective_user.id if update.effective_user else 0
    return uid == config.ADMIN_ID


def ensure_worker(update):
    u = update.effective_user
    db.upsert_worker(config.DB_PATH, u.id, u.username, u.first_name)
    return u


# ── worker commands ──

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_worker(update)
    await update.message.reply_text(
        "👋 <b>Welcome to WerkNL</b> — Amsterdam jobs for international workers.\n\n"
        "We post real jobs in <b>moving</b>, <b>horeca</b>, and <b>cleaning</b> — "
        "every day, straight to your phone.\n\n"
        "Pick an option below.",
        parse_mode=ParseMode.HTML, reply_markup=main_menu_kb(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠️ <b>WerkNL — commands</b>\n\n"
        "<b>For workers:</b>\n"
        "/start — main menu\n"
        "/jobs — today's jobs in your sectors\n"
        "/sectors — choose your sectors\n"
        "/premium — instant job alerts (€1.99/mo)\n\n"
        "<b>For employers:</b>\n"
        "/post — submit a job\n"
        "/pricing — see prices\n"
        "/myjobs — your job posts\n\n"
        "More jobs every day on the channel."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_worker(update)
    uid = update.effective_user.id
    sectors = db.get_worker_sectors(config.DB_PATH, uid)
    if not sectors:
        await update.message.reply_text("You haven't picked sectors yet. Use /sectors.")
        return
    jobs = db.jobs_active_by_sectors(config.DB_PATH, sectors)
    if not jobs:
        await update.message.reply_text(
            "No active jobs in your sectors right now — check the channel, more go up all day.")
        return
    jobs = jobs[:20]
    parts = ["🗞️ <b>Jobs for you</b>\n"]
    for j in jobs:
        parts.append("• " + job_dm_text(j))
    keyboard = []
    for j in jobs:
        url = contact_url(j.get("contact"))
        if url:
            keyboard.append([InlineKeyboardButton(
                respond_label(url) + " — " + (j.get("title") or "")[:20], url=url)])
    await update.message.reply_text(
        "\n".join(parts), parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


async def cmd_sectors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_worker(update)
    uid = update.effective_user.id
    selected = db.get_worker_sectors(config.DB_PATH, uid)
    await update.message.reply_text(
        "Pick the sectors you want job alerts for (tap to toggle):",
        reply_markup=sector_keyboard(selected),
    )


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_worker(update)
    w = db.get_worker(config.DB_PATH, update.effective_user.id)
    status = "✅ active" if w["premium"] else "❌ not active"
    await update.message.reply_text(
        f"⚡ <b>Premium worker — instant alerts</b>\n\n"
        f"€{PRICING['premium_worker_monthly']}/month, you get every new job in your sector "
        f"the moment it's posted — before the daily digest.\n\n"
        f"Your status: {status}\n\n"
        "To subscribe, message the admin.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(pricing_text(), parse_mode=ParseMode.HTML)


async def cmd_myjobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    jobs = [j for j in db.list_jobs(config.DB_PATH, limit=200) if j.get("employer_id") == uid]
    if not jobs:
        await update.message.reply_text("You haven't posted any jobs yet. Use /post.")
        return
    parts = ["🗂️ <b>Your jobs</b>\n"]
    for j in jobs[:15]:
        parts.append(f"#{j['id']} [{j['status']}] {j['title']}")
    await update.message.reply_text("\n".join(parts), parse_mode=ParseMode.HTML)


# ── /post conversation ──

async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.upsert_employer(config.DB_PATH, u.id, u.username)
    await update.message.reply_text(
        "📝 <b>Post a job</b>\n\nWhat's the job title? (e.g. \"Mover needed — today\")",
        parse_mode=ParseMode.HTML,
    )
    return TITLE


async def post_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"] = {"title": update.message.text.strip()}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{m['emoji']} {m['label']}", callback_data=f"postsector:{k}")]
        for k, m in SECTORS.items()
    ])
    await update.message.reply_text("Pick the sector:", reply_markup=kb)
    return SECTOR


async def post_sector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    context.user_data["job"]["sector"] = key
    await q.edit_message_text("📍 Which area? (e.g. \"Amsterdam West\", \"anywhere in Amsterdam\")")
    return AREA


async def post_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"]["area"] = update.message.text.strip()
    await update.message.reply_text("💰 Pay? (e.g. \"€14/hr\", \"€130/day\", \"negotiable\")")
    return PAY


async def post_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"]["pay"] = update.message.text.strip()
    await update.message.reply_text("⏰ Hours / shift? (e.g. \"9:00–17:00\", \"2 shifts today\")")
    return HOURS


async def post_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"]["hours"] = update.message.text.strip()
    await update.message.reply_text("📄 Short description of the work (2–3 lines):")
    return DESCRIPTION


async def post_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["job"]["description"] = update.message.text.strip()
    await update.message.reply_text("📩 How should workers contact you? (phone number or @telegram)")
    return CONTACT


async def post_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.text.strip()
    if not contact_url(contact):
        await update.message.reply_text(
            "⚠️ That doesn't look like a @username, phone number, or link — "
            "workers won't be able to tap it. Type a real contact "
            "(e.g. @employer_name or +31612345678):")
        return CONTACT
    context.user_data["job"]["contact"] = contact
    job = context.user_data["job"]
    u = update.effective_user
    job["employer"] = u.first_name or u.username or "Employer"
    job["employer_id"] = u.id
    preview = (
        "✅ <b>Confirm your job</b>\n\n" + job_post_text(job) +
        "\n\nFree posts go into review and appear in the next digest. "
        "Paid posts (€7) go live instantly — /pricing for details."
    )
    await update.message.reply_text(
        preview, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Submit", callback_data="post:submit"),
            InlineKeyboardButton("❌ Cancel", callback_data="post:cancel"),
        ]]),
    )
    return CONFIRM


async def post_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "post:cancel":
        context.user_data.pop("job", None)
        await q.edit_message_text("Cancelled.")
        return ConversationHandler.END
    job = context.user_data.get("job")
    if not job:
        await q.edit_message_text("Something went wrong — start again with /post.")
        return ConversationHandler.END
    job_id = db.add_job(config.DB_PATH, **job)
    await q.edit_message_text(f"✅ Submitted! Job #{job_id} is in review and will appear once approved.")
    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"📥 <b>New job #{job_id}</b> — /approve {job_id} or /reject {job_id}\n\n"
                 + job_post_text(job),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    context.user_data.pop("job", None)
    return ConversationHandler.END


async def post_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("job", None)
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── admin commands ──

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    pending = db.list_jobs(config.DB_PATH, status="pending", limit=10)
    lines = ["🛠️ <b>Admin</b>\n\n<b>Pending jobs:</b>"]
    if not pending:
        lines.append("(none)")
    for j in pending:
        lines.append(f"#{j['id']} [{j['sector']}] {j['title']} — /approve {j['id']}")
    lines.append("\n/approve &lt;id&gt; · /reject &lt;id&gt; · /fill &lt;id&gt; · /stats · /grant · /setpremium · /broadcast")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /approve <job_id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Bad id.")
        return
    job = db.get_job(config.DB_PATH, job_id)
    if not job:
        await update.message.reply_text("Job not found.")
        return
    mid = await post_job_to_channel(context, job)
    db.set_job_status(config.DB_PATH, job_id, "active", channel_message_id=mid)
    await notify_premium_workers(context, job)
    await update.message.reply_text(f"✅ Approved & posted job #{job_id}.")
    if job.get("employer_id"):
        try:
            await context.bot.send_message(
                chat_id=job["employer_id"],
                text=f"✅ Your job \"{job['title']}\" is now live on WerkNL.",
            )
        except Exception:
            pass


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /reject <job_id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Bad id.")
        return
    job = db.get_job(config.DB_PATH, job_id)
    if not job:
        await update.message.reply_text("Job not found.")
        return
    db.set_job_status(config.DB_PATH, job_id, "rejected")
    await update.message.reply_text(f"❌ Rejected job #{job_id}.")
    if job.get("employer_id"):
        try:
            await context.bot.send_message(
                chat_id=job["employer_id"],
                text=f"Your job \"{job['title']}\" was not approved. Message the admin with questions.",
            )
        except Exception:
            pass


async def cmd_fill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /fill <job_id>")
        return
    try:
        job_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Bad id.")
        return
    db.set_job_status(config.DB_PATH, job_id, "filled")
    await update.message.reply_text(f"✅ Job #{job_id} marked filled.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    s = db.stats(config.DB_PATH)
    text = (
        "📊 <b>WerkNL stats</b>\n\n"
        f"Workers: {s['workers']} (premium: {s['premium_workers']})\n"
        f"Employers: {s['employers']}\n"
        f"Active jobs: {s['active_jobs']}\n"
        f"Pending: {s['pending_jobs']}\n"
        f"Filled: {s['filled_jobs']}\n"
        f"Fill rate: {s['fill_rate']}%"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /grant <employer_id> <credits>")
        return
    try:
        eid, n = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("Bad numbers.")
        return
    db.upsert_employer(config.DB_PATH, eid)
    db.grant_credits(config.DB_PATH, eid, n)
    await update.message.reply_text(f"✅ Granted {n} credits to employer {eid}.")


async def cmd_setpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setpremium <worker_id>")
        return
    try:
        wid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Bad id.")
        return
    w = db.get_worker(config.DB_PATH, wid)
    if not w:
        await update.message.reply_text("Worker not found (have they used /start yet?).")
        return
    new = not w["premium"]
    db.set_worker_premium(config.DB_PATH, wid, new)
    await update.message.reply_text(f"✅ Worker {wid} premium={'on' if new else 'off'}.")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /broadcast <sector|all> <message>")
        return
    sector = context.args[0].lower()
    text = " ".join(context.args[1:])
    ids = db.all_worker_ids(config.DB_PATH) if sector == "all" else db.worker_ids_by_sector(config.DB_PATH, sector)
    sent = 0
    for wid in ids:
        try:
            await context.bot.send_message(chat_id=wid, text=text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception:
            continue
    await update.message.reply_text(f"📣 Broadcast sent to {sent}/{len(ids)} workers.")


# ── callback handlers ──

async def on_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split(":", 1)[1]
    uid = update.effective_user.id
    if data == "sectors":
        selected = db.get_worker_sectors(config.DB_PATH, uid)
        await q.edit_message_text("Pick sectors (tap to toggle):", reply_markup=sector_keyboard(selected))
    elif data == "employer":
        await q.edit_message_text(
            "🏢 <b>For employers</b>\n\nUse /post to submit a job, /pricing for rates, /myjobs to see your posts.",
            parse_mode=ParseMode.HTML)
    elif data == "help":
        await q.edit_message_text("🛠️ Use /help for all commands.", parse_mode=ParseMode.HTML)


async def on_sector_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    data = q.data.split(":", 1)[1]
    selected = db.get_worker_sectors(config.DB_PATH, uid)
    if data == "all":
        selected = list(SECTORS.keys())
    elif data == "clear":
        selected = []
    elif data == "done":
        if selected:
            labels = ", ".join(SECTORS[s]["label"] for s in selected)
            summary = (
                f"✅ Sectors saved: {labels}\n\n"
                "You'll get new jobs here — daily digest at 8:00, and every post has "
                "a button to respond (💬 Chat / 🔗 Open ad).\n\n"
                "📣 Also follow the job channel for everything: @werknl_ams"
            )
        else:
            summary = "No sectors selected — you won't get alerts until you pick some. Use /sectors anytime."
        await q.edit_message_text(summary, parse_mode=ParseMode.HTML)
        return
    else:
        if data in selected:
            selected.remove(data)
        else:
            selected.append(data)
    db.set_worker_sectors(config.DB_PATH, uid, selected)
    await q.edit_message_text("Pick sectors (tap to toggle):", reply_markup=sector_keyboard(selected))


# ── main ──

def build_application() -> Application:
    app = Application.builder().token(config.BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("post", post_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_title)],
            SECTOR: [CallbackQueryHandler(post_sector, pattern="^postsector:")],
            AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_area)],
            PAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_pay)],
            HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_hours)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_description)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_contact)],
            CONFIRM: [CallbackQueryHandler(post_confirm, pattern="^post:")],
        },
        fallbacks=[CommandHandler("cancel", post_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("sectors", cmd_sectors))
    app.add_handler(CommandHandler("premium", cmd_premium))
    app.add_handler(CommandHandler("pricing", cmd_pricing))
    app.add_handler(CommandHandler("myjobs", cmd_myjobs))
    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("fill", cmd_fill))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("grant", cmd_grant))
    app.add_handler(CommandHandler("setpremium", cmd_setpremium))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(on_sector_cb, pattern="^sector:"))
    app.add_handler(CallbackQueryHandler(on_menu_cb, pattern="^menu:"))

    app.job_queue.run_daily(daily_digest, time=time(hour=config.DIGEST_HOUR, minute=0))

    return app


def main():
    if not config.ready():
        print("Missing config. Set WERKNL_BOT_TOKEN, WERKNL_CHANNEL_ID, WERKNL_ADMIN_ID in .env")
        return
    db.init_db(config.DB_PATH)
    app = build_application()
    logger.info("WerkNL bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
