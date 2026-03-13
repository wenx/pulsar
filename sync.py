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
from pathlib import Path

from config import VAULT_PATH

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
LINKS_MD = VAULT_PATH / "Links.md"
TELEGRAM_FILE = ROOT / "pulsar-links-telegram.json"

# Import parse_links_md from parse-links.py (hyphen prevents normal import)
_spec = importlib.util.spec_from_file_location("parse_links", ROOT / "parse-links.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_links_md = _mod.parse_links_md


def _merge(sources: list[dict], existing: list[dict]) -> tuple[int, int]:
    """Merge source links into existing list. Returns (added, updated)."""
    existing_by_url = {l["url"].rstrip("/"): l for l in existing}
    added = updated = 0

    for link in sources:
        key = link["url"].rstrip("/")
        if key in existing_by_url:
            cur = existing_by_url[key]
            changed = False
            for field in ("done", "notes"):
                if cur.get(field) != link.get(field):
                    cur[field] = link.get(field)
                    changed = True
            if changed:
                updated += 1
        else:
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

    # Sync from Links.md
    md_links = [l for l in parse_links_md(LINKS_MD.read_text("utf-8")) if l.get("url")]
    added, updated = _merge(md_links, existing)

    # Sync from Telegram
    tg_added = tg_updated = 0
    if TELEGRAM_FILE.exists():
        tg_data = json.loads(TELEGRAM_FILE.read_text("utf-8"))
        tg_links = [l for l in tg_data.get("links", []) if l.get("url")]
        tg_added, tg_updated = _merge(tg_links, existing)

    total_added = added + tg_added
    total_updated = updated + tg_updated
    LINKS_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
    print(f"Sync: +{total_added} new ({added} Obsidian, {tg_added} Telegram), {total_updated} updated, {len(existing)} total")
    return total_added


if __name__ == "__main__":
    sync()
