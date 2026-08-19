"""WerkNL — seed jobs CLI.

Usage:
    python -m werknl.seed                       # fetch RSS feeds -> pending jobs
    python -m werknl.seed --dry-run             # preview RSS inserts
    python -m werknl.seed --json FILE           # insert jobs from a JSON file
    python -m werknl.seed --json FILE --dry-run # preview JSON inserts
"""
import argparse
import json
from pathlib import Path

from werknl import config, db
from werknl.scraper import fetch_feed, parse_rss, normalize

SOURCES_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_sources.json"


def load_sources():
    if not SOURCES_PATH.exists():
        return []
    return json.loads(SOURCES_PATH.read_text())


def seed_exists(title, contact):
    conn = db.get_conn(config.DB_PATH)
    try:
        return conn.execute(
            "SELECT 1 FROM jobs WHERE title=? AND contact=? AND source='seed'",
            (title, contact),
        ).fetchone() is not None
    finally:
        conn.close()


def _insert(title, sector, contact, area=None, pay=None, hours=None,
            description=None, dry_run=False):
    title = (title or "").strip()
    contact = (contact or "").strip()
    if not title:
        return False
    if seed_exists(title, contact):
        return False
    if dry_run:
        print(f"[dry] {sector}: {title}")
        return False
    db.add_job(config.DB_PATH, title=title, sector=sector, area=area, pay=pay,
               hours=hours, description=description, contact=contact, source="seed")
    return True


def run(dry_run=False, json_path=None):
    db.init_db(config.DB_PATH)
    inserted = 0

    if json_path:
        jobs = json.loads(Path(json_path).read_text())
        for job in jobs:
            if _insert(job.get("title"), job.get("sector", "moving"),
                       job.get("contact", ""), job.get("area"), job.get("pay"),
                       job.get("hours"), job.get("description"), dry_run=dry_run):
                inserted += 1
        print("Dry run complete." if dry_run else f"Inserted {inserted} pending seed jobs.")
        return

    sources = load_sources()
    if not sources:
        print("No sources configured. Add feeds to data/seed_sources.json")
        return
    for src in sources:
        try:
            xml = fetch_feed(src["url"])
            items = parse_rss(xml)
        except Exception as e:
            print(f"[skip] {src.get('name', src['url'])}: {e}")
            continue
        for item in items:
            job = normalize(item, src["sector"])
            if not job["title"]:
                continue
            if _insert(job["title"], job["sector"], job["contact"],
                       job.get("area"), job.get("pay"), job.get("hours"),
                       job["description"], dry_run=dry_run):
                inserted += 1
    print("Dry run complete." if dry_run else f"Inserted {inserted} pending seed jobs.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", default=None, help="Path to a JSON file of jobs to insert")
    args = ap.parse_args()
    run(dry_run=args.dry_run, json_path=args.json)
