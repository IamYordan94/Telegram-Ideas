"""WerkNL — seed job scraper.

Pulls real public vacancies from RSS feeds. Feeds are configurable in
data/seed_sources.json. Jobs always land as 'pending' so an admin reviews
before anything goes live (no fake jobs, no junk).
"""
import xml.etree.ElementTree as ET

import httpx


def fetch_feed(url, timeout=15) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def parse_rss(xml_text):
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        def txt(tag):
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        items.append({
            "title": txt("title"),
            "description": txt("description"),
            "link": txt("link"),
        })
    return items


def normalize(item, sector):
    """Map a feed item to a WerkNL seed job dict."""
    return {
        "title": (item.get("title") or "").strip(),
        "description": (item.get("description") or "")[:300],
        "contact": (item.get("link") or "").strip(),
        "sector": sector,
        "source": "seed",
    }
