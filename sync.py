#!/usr/bin/env python3
"""
Sync Links.md + pulsar-links-telegram.json → links.json (incremental).
- New URLs: added with metadata, enriched by pipeline later
- Existing URLs: syncs done/notes from Obsidian, preserves enrichment data
- Removed URLs: kept in links.json (no deletion)
- Telegram links: already have ai_summary/tags/category from Marvin bot
"""

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

from config import VAULT_PATH, normalize_url

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
DELETED_FILE = ROOT / "deleted.json"
LINKS_MD = VAULT_PATH / "Links.md"
TELEGRAM_FILE = ROOT / "pulsar-links-telegram.json"

# Import parse_links_md from parse-links.py (hyphen prevents normal import)
_spec = importlib.util.spec_from_file_location("parse_links", ROOT / "parse-links.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_links_md = _mod.parse_links_md


OBSIDIAN_SYNC_FIELDS = ("done", "notes")
TELEGRAM_SYNC_FIELDS = ("done", "notes", "ai_summary", "tags", "category", "desc")


def _load_deleted() -> set:
    """Load deleted URLs set."""
    if DELETED_FILE.exists():
        return set(json.loads(DELETED_FILE.read_text("utf-8")))
    return set()


def _merge(sources: list[dict], existing: list[dict],
           sync_fields: tuple = OBSIDIAN_SYNC_FIELDS,
           deleted: set = None) -> tuple[int, int]:
    """Merge source links into existing list. Returns (added, updated)."""
    existing_by_url = {normalize_url(l["url"]): l for l in existing}
    added = updated = 0

    for link in sources:
        key = normalize_url(link["url"])
        if deleted and key in deleted:
            continue
        if key in existing_by_url:
            cur = existing_by_url[key]
            changed = False
            for field in sync_fields:
                if link.get(field) and cur.get(field) != link.get(field):
                    cur[field] = link.get(field)
                    changed = True
            if changed:
                updated += 1
        else:
            if not link.get("date"):
                link["date"] = date.today().isoformat()
            existing.insert(0, link)
            existing_by_url[key] = link
            added += 1

    return added, updated


def sync() -> int:
    """Returns number of new links added."""
    if not LINKS_MD.exists():
        print(f"✗ Not found: {LINKS_MD}")
        sys.exit(1)

    existing = json.loads(LINKS_FILE.read_text("utf-8")) if LINKS_FILE.exists() else []
    deleted = _load_deleted()

    # Sync from Links.md
    md_links = [l for l in parse_links_md(LINKS_MD.read_text("utf-8")) if l.get("url")]
    added, updated = _merge(md_links, existing, deleted=deleted)

    # Sync from Telegram
    tg_added = tg_updated = 0
    if TELEGRAM_FILE.exists():
        tg_data = json.loads(TELEGRAM_FILE.read_text("utf-8"))
        tg_links = [l for l in tg_data.get("links", []) if l.get("url")]
        tg_added, tg_updated = _merge(tg_links, existing, TELEGRAM_SYNC_FIELDS, deleted=deleted)

    total_added = added + tg_added
    total_updated = updated + tg_updated
    LINKS_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
    print(f"Sync: +{total_added} new ({added} Obsidian, {tg_added} Telegram), {total_updated} updated, {len(existing)} total")
    return total_added


if __name__ == "__main__":
    sync()
