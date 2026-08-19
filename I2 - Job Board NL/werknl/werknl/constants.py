"""WerkNL — constants: sectors, pricing, labels."""

SECTORS = {
    "moving": {"label": "Moving / Verhuizing", "emoji": "📦"},
    "horeca": {"label": "Horeca", "emoji": "🍽️"},
    "cleaning": {"label": "Cleaning / Schoonmaak", "emoji": "🧹"},
}

PRICING = {
    "per_post": 7,
    "pack_10": 49,
    "monthly": 79,
    "featured": 5,
    "premium_worker_monthly": 1.99,
}


def sector_label(key: str) -> str:
    s = SECTORS.get(key)
    return f"{s['emoji']} {s['label']}" if s else key


def valid_sector(key: str) -> bool:
    return key in SECTORS
