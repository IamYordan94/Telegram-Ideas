"""WerkNL — formatting job posts and digests."""
import html

from werknl.constants import SECTORS, PRICING


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def job_post_text(job, include_contact=True) -> str:
    sec = SECTORS.get(job.get("sector"), {})
    emoji = sec.get("emoji", "💼")
    label = sec.get("label", job.get("sector", ""))
    lines = [
        f"{emoji} <b>{esc(job.get('title', ''))}</b>",
        f"🏷️ {esc(label)}",
    ]
    if job.get("area"):
        lines.append(f"📍 {esc(job['area'])}")
    if job.get("pay"):
        lines.append(f"💰 {esc(job['pay'])}")
    if job.get("hours"):
        lines.append(f"⏰ {esc(job['hours'])}")
    if job.get("description"):
        lines.append(f"\n{esc(job['description'])}")
    if include_contact and job.get("contact"):
        lines.append(f"\n📩 <b>Respond:</b> {esc(job['contact'])}")
    if job.get("is_featured"):
        lines.append("\n⭐ <i>Featured</i>")
    return "\n".join(lines)


def job_dm_text(job) -> str:
    """Single-line DM version for alerts and digest bullets."""
    sec = SECTORS.get(job.get("sector"), {})
    bits = [f"{sec.get('emoji', '💼')} <b>{esc(job.get('title', ''))}</b>"]
    if job.get("area"):
        bits.append(f"📍{esc(job['area'])}")
    if job.get("pay"):
        bits.append(f"💰{esc(job['pay'])}")
    if job.get("contact"):
        bits.append(f"📩{esc(job['contact'])}")
    return " — ".join(bits)


def pricing_text() -> str:
    p = PRICING
    return (
        "💶 <b>WerkNL — Employer pricing</b>\n\n"
        f"• Single job post — <b>€{p['per_post']}</b>\n"
        f"• 10-post pack — <b>€{p['pack_10']}</b> (≈€{p['pack_10'] / 10:.2f}/post)\n"
        f"• Monthly unlimited — <b>€{p['monthly']}</b> (best value)\n"
        f"• Featured/pinned boost — <b>+€{p['featured']}</b>\n\n"
        "Workers stay free. A paid post goes live instantly; a free post goes into review.\n\n"
        "To pay or buy credits, message the admin."
    )
