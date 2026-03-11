#!/usr/bin/env python3
"""
Step 1: Fetch web pages and extract metadata via Jina Reader (JSON mode).
One API call per URL returns title, description, content, and images.
"""

import hashlib
import json
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

from config import (
    FETCH_DELAY, JINA_BASE_URL, JINA_TIMEOUT, JINA_API_KEY,
    BODY_TEXT_LIMIT, USER_AGENT,
)

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
CACHE_FILE = ROOT / "meta-cache.json"
CONTENT_DIR = ROOT / "content"


def fetch_via_jina(url: str) -> dict:
    """Fetch URL via Jina Reader JSON mode. Returns structured data."""
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "X-With-Images-Summary": "true",
    }
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"

    try:
        req = urllib.request.Request(
            f"{JINA_BASE_URL}{url}",
            headers=headers,
        )
        resp = urllib.request.urlopen(req, timeout=JINA_TIMEOUT)
        result = json.loads(resp.read().decode("utf-8", errors="ignore"))
        if result.get("code") == 200 and result.get("data"):
            return result["data"]
        return {"_error": result.get("message", "Jina returned no data")}
    except Exception as e:
        return {"_error": str(e)[:100]}


def extract_video_id(url: str) -> tuple[str, str]:
    """Extract video ID and platform from YouTube/Bilibili URL."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")

    if host in ("youtube.com", "m.youtube.com"):
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [""])[0]
        if vid:
            return ("youtube", vid)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("shorts", "embed"):
            return ("youtube", parts[1])
    elif host == "youtu.be":
        vid = parsed.path.strip("/").split("/")[0]
        if vid:
            return ("youtube", vid)

    if host == "bilibili.com" or host.endswith(".bilibili.com"):
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "video":
            return ("bilibili", parts[1])

    return ("", "")


def get_thumbnail(jina_data: dict, url: str) -> str:
    """Pick best thumbnail: video platform > Jina images > og:image > mshots."""
    # YouTube direct thumbnail
    platform, vid = extract_video_id(url)
    if platform == "youtube":
        return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"

    # Jina images (pick first meaningful one)
    images = jina_data.get("images", {})
    if images:
        for name, img_url in images.items():
            # Skip tiny tracking pixels and icons
            if "1x1" in img_url or "favicon" in img_url.lower():
                continue
            return img_url

    # mshots fallback
    if url:
        return f"https://s0.wp.com/mshots/v1/{quote(url, safe='')}?w=480&h=270"
    return ""


def url_hash(url: str) -> str:
    """Short hash of URL for filename."""
    return hashlib.md5(url.encode()).hexdigest()[:10]


def save_content_md(url: str, title: str, content: str) -> str:
    """Save Jina markdown content to content/ directory. Returns filename."""
    CONTENT_DIR.mkdir(exist_ok=True)
    filename = f"{url_hash(url)}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        return filename

    safe_title = title.replace('"', '\\"')
    frontmatter = f"""---
title: "{safe_title}"
source: "{url}"
saved: {date.today().isoformat()}
---

"""
    filepath.write_text(frontmatter + content, "utf-8")
    return filename


def get_favicon_url(domain: str) -> str:
    """Get favicon URL via Google S2."""
    if domain:
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
    return ""


def main():
    links = json.loads(LINKS_FILE.read_text("utf-8"))

    # Load cache
    cache = json.loads(CACHE_FILE.read_text("utf-8")) if CACHE_FILE.exists() else {}

    enriched = 0
    skipped = 0
    errors = 0

    for i, link in enumerate(links):
        url = link.get("url", "")
        if not url:
            continue

        # Skip if fully enriched (metadata + content)
        if link.get("thumbnail") and link.get("desc") and link.get("content_file"):
            skipped += 1
            continue

        # Check cache (skip error entries so they get retried)
        cached = cache.get(url)
        if cached and "_error" not in cached:
            data = cached
        else:
            print(f"[{i+1}/{len(links)}] Fetching: {link['title'][:50]}...")
            data = fetch_via_jina(url)
            if "_error" not in data:
                cache[url] = data
            time.sleep(FETCH_DELAY)

        if "_error" in data:
            errors += 1
            print(f"  ✗ {data['_error'][:60]}")
            continue

        # Apply metadata
        title = data.get("title", "")
        desc = data.get("description", "")
        content = data.get("content", "")
        domain = link.get("domain", "")

        # Title: use Jina title if current title is bare domain/URL
        if title and (link["title"].startswith("http") or link["title"] == domain):
            link["title"] = title

        # Description
        if desc and not link.get("desc"):
            link["desc"] = desc

        # Save full content as Markdown
        if content:
            cf = save_content_md(url, link.get("title", title), content)
            link["content_file"] = cf

        # Body text for AI analysis
        if content and not link.get("body_text"):
            link["body_text"] = content[:BODY_TEXT_LIMIT]

        # Thumbnail
        thumb = get_thumbnail(data, url)
        if thumb:
            link["thumbnail"] = thumb

        # Favicon
        favicon = get_favicon_url(domain)
        if favicon:
            link["favicon"] = favicon

        enriched += 1

    # Save cache
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")

    # Save enriched links
    LINKS_FILE.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")

    print(f"\nDone: {enriched} enriched, {skipped} skipped, {errors} errors")
    with_thumb = sum(1 for l in links if l.get("thumbnail"))
    with_desc = sum(1 for l in links if l.get("desc"))
    with_content = sum(1 for l in links if l.get("content_file"))
    print(f"Thumbnails: {with_thumb}/{len(links)}")
    print(f"Descriptions: {with_desc}/{len(links)}")
    print(f"Content saved: {with_content}/{len(links)}")


if __name__ == "__main__":
    main()
