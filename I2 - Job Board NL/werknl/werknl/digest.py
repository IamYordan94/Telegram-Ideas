"""WerkNL — channel posting, instant alerts, and daily digest."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from werknl import config, db
from werknl.formatting import job_post_text, job_dm_text


def _respond_button(job):
    contact = job.get("contact") or ""
    url = None
    if contact.startswith("@"):
        url = f"https://t.me/{contact[1:]}"
    elif contact.startswith("http"):
        url = contact
    if not url:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("📩 Respond", url=url)]])


async def post_job_to_channel(context, job):
    """Post an approved job to the channel. Returns the message id (or None)."""
    msg = await context.bot.send_message(
        chat_id=config.CHANNEL_ID,
        text=job_post_text(job),
        parse_mode=ParseMode.HTML,
        reply_markup=_respond_button(job),
    )
    return msg.message_id


async def notify_premium_workers(context, job):
    """Instant DM to premium workers subscribed to this job's sector."""
    ids = db.worker_ids_by_sector(config.DB_PATH, job["sector"], premium_only=True)
    text = "⚡ <b>New job — instant alert</b>\n\n" + job_dm_text(job)
    for wid in ids:
        try:
            await context.bot.send_message(chat_id=wid, text=text, parse_mode=ParseMode.HTML)
        except Exception:
            continue


async def daily_digest(context):
    """Once a day: DM every worker a digest of active jobs in their sectors."""
    for wid in db.all_worker_ids(config.DB_PATH):
        sectors = db.get_worker_sectors(config.DB_PATH, wid)
        jobs = db.jobs_active_by_sectors(config.DB_PATH, sectors)
        if not jobs:
            continue
        parts = ["🗞️ <b>WerkNL — jobs for you today</b>\n"]
        for j in jobs:
            parts.append("• " + job_dm_text(j))
        parts.append("\nMore jobs on the channel — every approved job is posted there first.")
        try:
            await context.bot.send_message(
                chat_id=wid, text="\n".join(parts), parse_mode=ParseMode.HTML,
            )
        except Exception:
            continue
