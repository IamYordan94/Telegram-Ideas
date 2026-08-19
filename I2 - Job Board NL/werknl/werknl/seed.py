"""WerkNL — seed jobs CLI.

Usage:
    python -m werknl.seed            # fetch all configured feeds -> pending jobs
    python -m werknl.seed --dry-run  # show what would be inserted, don't insert
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


def run(dry_run=False):
    db.init_db(config.DB_PATH)
    sources = load_sources()
    if not sources:
        print("No sources configured. Add feeds to data/seed_sources.json")
        return
    inserted = 0
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
            if dry_run:
                print(f"[dry] {src['sector']}: {job['title']}")
            else:
                db.add_job(config.DB_PATH, **job)
                inserted += 1
    if dry_run:
        print("Dry run complete.")
    else:
        print(f"Inserted {inserted} pending seed jobs.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(dry_run=args.dry_run)
