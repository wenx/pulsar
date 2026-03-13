#!/usr/bin/env python3
"""
Step 3: Download thumbnails + generate SVG fallbacks + generate RSS feed.
"""

import hashlib
import json
import random
import time
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from config import (
    USER_AGENT, THUMB_DOWNLOAD_DELAY, THUMB_DOWNLOAD_TIMEOUT,
    SITE_URL, FEED_TITLE, FEED_DESC, url_hash,
)

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
THUMBS_DIR = ROOT / "thumbs"
FEED_FILE = ROOT / "feed.xml"

HEADERS = {"User-Agent": USER_AGENT}

# ── SVG thumbnail config ──
ACCENT_COLORS = [
    "#c4a44a", "#4ac4a4", "#a44ac4", "#c44a4a",
    "#4a8ec4", "#4ac44a", "#c4884a",
]

CATEGORY_GLYPHS = {
    "Article": "//", "Video": "▶", "WeChat": "◈", "News": "◆",
    "GitHub": ">_", "Podcast": "♪", "Book": "□", "Notion": "≡",
    "Social": "@", "Reference": "※",
}


# ── Thumbnail download ──

def guess_ext(url: str, content_type: str = "") -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct == "image/png" or url.endswith(".png"):
        return ".png"
    if ct == "image/svg+xml" or url.endswith(".svg"):
        return ".svg"
    if ct == "image/webp" or url.endswith(".webp"):
        return ".webp"
    if ct == "image/gif" or url.endswith(".gif"):
        return ".gif"
    return ".jpg"


def download_thumbnail(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=THUMB_DOWNLOAD_TIMEOUT)
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()

        # Microlink may return JSON error instead of image
        if "microlink" in url and not content_type.startswith("image/"):
            print(f"    ✗ Microlink screenshot failed (Content-Type: {content_type}), skipping")
            return False

        ext = guess_ext(url, content_type)
        dest.with_suffix(ext).write_bytes(data)
        return True
    except Exception as e:
        # YouTube maxresdefault may not exist — try hqdefault
        if "img.youtube.com" in url and "maxresdefault" in url:
            fallback = url.replace("maxresdefault", "hqdefault")
            print(f"    ↻ maxres unavailable, trying hqdefault...")
            try:
                req2 = urllib.request.Request(fallback, headers=HEADERS)
                resp2 = urllib.request.urlopen(req2, timeout=THUMB_DOWNLOAD_TIMEOUT)
                data2 = resp2.read()
                ext = guess_ext(fallback, resp2.headers.get("Content-Type", ""))
                dest.with_suffix(ext).write_bytes(data2)
                return True
            except Exception:
                pass
        print(f"    ✗ {str(e)[:60]}")
        return False


def download_all_thumbnails(links: list):
    """Download remote thumbnails to local thumbs/ directory."""
    THUMBS_DIR.mkdir(exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0

    for i, link in enumerate(links):
        thumb_url = link.get("thumbnail", "")
        if not thumb_url:
            continue

        # Already local
        if not thumb_url.startswith("http"):
            skipped += 1
            continue

        link_url = link.get("url", "")
        h = url_hash(link_url) if link_url else f"thumb-{i:03d}"

        # Check if already downloaded (ignore SVG fallbacks)
        existing = [f for f in THUMBS_DIR.glob(f"{h}.*") if f.suffix != ".svg"]
        if existing:
            link["thumbnail"] = str(existing[0].relative_to(ROOT))
            skipped += 1
            continue

        # Remove old SVG fallback before downloading real thumbnail
        for old_svg in THUMBS_DIR.glob(f"{h}.svg"):
            old_svg.unlink()

        print(f"  [{i+1}/{len(links)}] Downloading: {link['title'][:40]}...")

        ext = guess_ext(thumb_url)
        dest = (THUMBS_DIR / h).with_suffix(ext)

        if download_thumbnail(thumb_url, dest):
            final = list(THUMBS_DIR.glob(f"{h}.*"))
            if final:
                link["thumbnail"] = str(final[0].relative_to(ROOT))
            downloaded += 1
        else:
            failed += 1

        time.sleep(THUMB_DOWNLOAD_DELAY)

    print(f"Thumbnails: {downloaded} downloaded, {skipped} skipped, {failed} failed")


# ── SVG fallback thumbnails ──

def make_svg_thumbnail(title: str, category: str, domain: str, index: int) -> str:
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    accent = ACCENT_COLORS[h % len(ACCENT_COLORS)]
    glyph = CATEGORY_GLYPHS.get(category, "//")

    display_title = title[:40] + ("..." if len(title) > 40 else "")
    display_title = display_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    domain_esc = domain.replace("&", "&amp;")

    random.seed(h)
    scan_lines = "".join(
        f'<line x1="0" y1="{y}" x2="480" y2="{y}" stroke="{accent}" stroke-opacity="0.03"/>'
        for y in range(0, 270, random.randint(4, 8))
    )
    dots = ""
    for x in range(20, 460, 40):
        for y in range(20, 250, 40):
            opacity = random.uniform(0.02, 0.08)
            dots += f'<circle cx="{x}" cy="{y}" r="1" fill="{accent}" opacity="{opacity}"/>'

    corner_size = 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0a0a"/>
      <stop offset="100%" stop-color="#111"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg{index})"/>
  {scan_lines}
  {dots}
  <rect x="1" y="1" width="478" height="268" fill="none" stroke="{accent}" stroke-opacity="0.15" rx="2"/>
  <path d="M{corner_size},1 L1,1 L1,{corner_size}" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M{480-corner_size},1 L479,1 L479,{corner_size}" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M1,{270-corner_size} L1,269 L{corner_size},269" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M479,{270-corner_size} L479,269 L{480-corner_size},269" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <text x="24" y="44" font-family="'SF Mono','Cascadia Code',monospace" font-size="18" fill="{accent}" opacity="0.6">{glyph}</text>
  <line x1="24" y1="60" x2="120" y2="60" stroke="{accent}" stroke-opacity="0.3" stroke-width="1"/>
  <text x="24" y="120" font-family="'SF Mono','Cascadia Code',monospace" font-size="16" fill="#e8e4de" opacity="0.9">
    <tspan x="24" dy="0">{display_title}</tspan>
  </text>
  <text x="24" y="245" font-family="'SF Mono','Cascadia Code',monospace" font-size="11" fill="{accent}" opacity="0.4">{domain_esc}</text>
  <circle cx="456" cy="245" r="3" fill="{accent}" opacity="0.5">
    <animate attributeName="opacity" values="0.2;0.7;0.2" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>'''


def generate_svg_fallbacks(links: list):
    """Generate SVG thumbnails for links without one."""
    THUMBS_DIR.mkdir(exist_ok=True)
    generated = 0
    for i, link in enumerate(links):
        if link.get("thumbnail"):
            continue
        h = url_hash(link.get("url", str(i)))
        svg = make_svg_thumbnail(
            link["title"],
            link.get("category", "Article"),
            link.get("domain", ""),
            i,
        )
        filename = f"{h}.svg"
        (THUMBS_DIR / filename).write_text(svg, encoding="utf-8")
        link["thumbnail"] = f"thumbs/{filename}"
        generated += 1
    if generated:
        print(f"Generated {generated} SVG fallback thumbnails")


# ── RSS feed ──

def generate_feed(links: list):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for link in links:
        if link.get("done"):
            continue
        title = escape(link.get("title", ""))
        url = escape(link.get("url", ""))
        desc = escape(link.get("ai_summary") or link.get("desc", ""))
        category = link.get("category", "")
        fmt = link.get("format", "")
        tags = link.get("tags", [])

        categories = ""
        if fmt:
            categories += f"      <category>{escape(fmt)}</category>\n"
        if category:
            categories += f"      <category>{escape(category)}</category>\n"
        for tag in tags:
            categories += f"      <category>{escape(tag)}</category>\n"

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <description>{desc}</description>
{categories}    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{FEED_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>{FEED_DESC}</description>
    <language>zh-cn</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""
    FEED_FILE.write_text(xml, "utf-8")
    active = sum(1 for l in links if not l.get("done"))
    print(f"Generated feed.xml — {active} items")


def main():
    links = json.loads(LINKS_FILE.read_text("utf-8"))

    # 1. Download remote thumbnails
    download_all_thumbnails(links)

    # 2. Generate SVG fallbacks for any remaining without thumbnails
    generate_svg_fallbacks(links)

    # 3. Save updated links
    LINKS_FILE.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")

    # 4. Generate RSS feed
    generate_feed(links)

    local = sum(1 for l in links if l.get("thumbnail") and not l["thumbnail"].startswith("http"))
    print(f"Local thumbnails: {local}/{len(links)}")


if __name__ == "__main__":
    main()
