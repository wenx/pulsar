#!/usr/bin/env python3
"""
Sync Links.md → links.json (incremental).
- New URLs: added with basic metadata, enriched by pipeline later
- Existing URLs: syncs done/notes from Obsidian, preserves enrichment data
- Removed URLs: kept in links.json (no deletion)
"""

import importlib.util
import json
import sys
from pathlib import Path

from config import VAULT_PATH

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
LINKS_MD = VAULT_PATH / "Links.md"

# Import parse_links_md from parse-links.py (hyphen prevents normal import)
_spec = importlib.util.spec_from_file_location("parse_links", ROOT / "parse-links.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_links_md = _mod.parse_links_md


def sync() -> int:
    """Returns number of new links added."""
    if not LINKS_MD.exists():
        print(f"✗ Not found: {LINKS_MD}")
        sys.exit(1)

    md_links = [l for l in parse_links_md(LINKS_MD.read_text("utf-8")) if l.get("url")]

    existing = json.loads(LINKS_FILE.read_text("utf-8")) if LINKS_FILE.exists() else []
    existing_by_url = {l["url"].rstrip("/"): l for l in existing}

    added = 0
    updated = 0

    for md_link in md_links:
        key = md_link["url"].rstrip("/")

        if key in existing_by_url:
            link = existing_by_url[key]
            changed = False
            for field in ("done", "notes"):
                if link.get(field) != md_link.get(field):
                    link[field] = md_link.get(field)
                    changed = True
            if changed:
                updated += 1
        else:
            existing.insert(0, md_link)
            existing_by_url[key] = md_link
            added += 1

    LINKS_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
    print(f"Sync: +{added} new, {updated} updated, {len(existing)} total")
    return added


if __name__ == "__main__":
    sync()
