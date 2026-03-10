#!/usr/bin/env python3
"""
Enrich links.json with metadata: og:image, og:description, favicon.
Then optionally generate AI summaries via Claude API.
"""

import json
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin

from config import (
    FETCH_TIMEOUT, FETCH_DELAY, JINA_BASE_URL, JINA_TIMEOUT, USER_AGENT,
    HTML_READ_LIMIT, BODY_TEXT_LIMIT, BODY_TEXT_MIN,
)

ROOT = Path(__file__).parent
INPUT = ROOT / "links.json"
OUTPUT = ROOT / "links.json"
CACHE = ROOT / "meta-cache.json"


class MetaParser(HTMLParser):
    """Extract og:image, og:description, twitter:image, description, title, favicon."""

    def __init__(self):
        super().__init__()
        self.meta = {}
        self._in_title = False
        self._title_text = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta":
            prop = d.get("property", d.get("name", "")).lower()
            content = d.get("content", "")
            if prop in (
                "og:image", "og:description", "og:title", "og:site_name",
                "twitter:image", "twitter:description",
                "description",
            ):
                self.meta[prop] = content
        elif tag == "title":
            self._in_title = True
        elif tag == "link":
            rel = d.get("rel", "")
            href = d.get("href", "")
            if "icon" in rel and href:
                self.meta["favicon"] = href

    def handle_data(self, data):
        if self._in_title:
            self._title_text += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            if self._title_text.strip():
                self.meta["title"] = self._title_text.strip()


def extract_body_text(url: str) -> str:
    """Extract body text via Jina Reader."""
    if not url:
        return ""
    try:
        req = urllib.request.Request(
            f"{JINA_BASE_URL}{url}",
            headers={"Accept": "text/plain", "User-Agent": USER_AGENT},
        )
        resp = urllib.request.urlopen(req, timeout=JINA_TIMEOUT)
        text = resp.read().decode("utf-8", errors="ignore")
        return text[:BODY_TEXT_LIMIT] if text else ""
    except Exception:
        return ""


def fetch_meta(url: str) -> dict:
    """Fetch URL and extract metadata. Falls back to Jina Reader."""
    meta = {}
    html = ""

    # Try direct scrape
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        })
        resp = urllib.request.urlopen(req, timeout=FETCH_TIMEOUT)
        html = resp.read(HTML_READ_LIMIT).decode("utf-8", errors="ignore")
        parser = MetaParser()
        parser.feed(html)
        meta = parser.meta
    except Exception:
        pass

    # Extract body text: from HTML if available, Jina Reader as fallback
    if html:
        from html.parser import HTMLParser as _HP
        class _TextExtractor(_HP):
            def __init__(self):
                super().__init__()
                self.parts = []
                self._skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style', 'nav', 'header', 'footer'):
                    self._skip = True
            def handle_endtag(self, tag):
                if tag in ('script', 'style', 'nav', 'header', 'footer'):
                    self._skip = False
            def handle_data(self, data):
                if not self._skip:
                    t = data.strip()
                    if t:
                        self.parts.append(t)
        ext = _TextExtractor()
        ext.feed(html)
        body = "\n".join(ext.parts)
        if len(body) < BODY_TEXT_MIN or "javascript" in body[:500].lower():
            body = extract_body_text(url)
    else:
        body = extract_body_text(url)
    if body:
        meta["_body_text"] = body[:BODY_TEXT_LIMIT]

    # If direct scrape got no title, parse it from Jina body text
    if not meta.get("title") and not meta.get("og:title") and "_body_text" in meta:
        for line in meta["_body_text"].splitlines():
            if line.startswith("Title: "):
                meta["title"] = line[7:].strip()
                break

    # Resolve relative favicon/image URLs
    for key in ("og:image", "twitter:image", "favicon"):
        if key in meta and meta[key] and not meta[key].startswith("http"):
            meta[key] = urljoin(url, meta[key])

    if not meta:
        return {"_error": "No metadata found"}
    return meta


def extract_video_id(url: str) -> tuple[str, str]:
    """Extract video ID and platform from YouTube/Bilibili URL.
    Returns (platform, video_id) or ('', '')."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")

    # YouTube: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID
    if host in ("youtube.com", "m.youtube.com"):
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [""])[0]
        if vid:
            return ("youtube", vid)
        # /shorts/ID or /embed/ID
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("shorts", "embed"):
            return ("youtube", parts[1])
    elif host == "youtu.be":
        vid = parsed.path.strip("/").split("/")[0]
        if vid:
            return ("youtube", vid)

    # Bilibili: bilibili.com/video/BV... or b23.tv redirect
    if host == "bilibili.com" or host.endswith(".bilibili.com"):
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "video":
            return ("bilibili", parts[1])

    return ("", "")


def fetch_youtube_oembed(url: str) -> dict:
    """Fetch YouTube video metadata via oEmbed API (no key needed)."""
    platform, vid = extract_video_id(url)
    if platform != "youtube":
        return {}
    try:
        from urllib.parse import quote
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
        req = urllib.request.Request(oembed_url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        import json as _json
        return _json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def get_video_thumbnail(url: str) -> str:
    """Get high-quality thumbnail directly from video platform."""
    platform, vid = extract_video_id(url)
    if platform == "youtube":
        # maxresdefault (1280x720) > sddefault (640x480) > hqdefault (480x360)
        return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
    if platform == "bilibili":
        # Bilibili doesn't have a direct thumbnail URL pattern,
        # fall through to og:image
        pass
    return ""


def get_thumbnail(meta: dict, url: str = "") -> str:
    """Pick best thumbnail: video platform > og:image > twitter:image > mshots."""
    # Try direct video platform thumbnail first
    thumb = get_video_thumbnail(url) if url else ""

    if not thumb:
        thumb = (
            meta.get("og:image")
            or meta.get("twitter:image")
            or ""
        )
    if not thumb and url:
        # Use WordPress mshots as fallback screenshot
        from urllib.parse import quote
        thumb = f"https://s0.wp.com/mshots/v1/{quote(url, safe='')}?w=480&h=270"
    return thumb


def get_description(meta: dict) -> str:
    """Pick best description from metadata."""
    return (
        meta.get("og:description")
        or meta.get("twitter:description")
        or meta.get("description")
        or ""
    )


def get_favicon_url(domain: str, meta: dict) -> str:
    """Get favicon URL."""
    if meta.get("favicon"):
        return meta["favicon"]
    if domain:
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
    return ""


def main():
    links = json.loads(INPUT.read_text("utf-8"))

    # Load cache
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text("utf-8"))

    enriched = 0
    skipped = 0
    errors = 0

    for i, link in enumerate(links):
        url = link.get("url", "")
        if not url:
            continue

        # Skip if already enriched
        if link.get("thumbnail") and link.get("desc"):
            skipped += 1
            continue

        # Check cache
        if url in cache:
            meta = cache[url]
        else:
            print(f"[{i+1}/{len(links)}] Fetching: {link['title'][:50]}...")
            meta = fetch_meta(url)
            cache[url] = meta
            time.sleep(FETCH_DELAY)

        if "_error" in meta:
            errors += 1
            print(f"  ✗ {meta['_error'][:60]}")
            continue

        # YouTube oEmbed fallback for title/desc
        platform, _ = extract_video_id(url)
        if platform == "youtube" and (not meta.get("og:title") or not get_description(meta)):
            oembed = fetch_youtube_oembed(url)
            if oembed:
                if not meta.get("og:title") and oembed.get("title"):
                    meta["og:title"] = oembed["title"]
                if not get_description(meta) and oembed.get("author_name"):
                    meta["description"] = f"{oembed['title']} — {oembed['author_name']}"
                cache[url] = meta

        # Apply metadata
        thumb = get_thumbnail(meta, url)
        desc = get_description(meta)
        favicon = get_favicon_url(link.get("domain", ""), meta)

        if thumb:
            link["thumbnail"] = thumb
        if desc and not link.get("desc"):
            link["desc"] = desc
        if favicon:
            link["favicon"] = favicon
        if meta.get("_body_text") and not link.get("body_text"):
            link["body_text"] = meta["_body_text"]
        # Use og:title or parsed title if our title looks like a bare URL or bare domain
        best_title = meta.get("og:title") or meta.get("title")
        if best_title and (link["title"].startswith("http") or link["title"] == link.get("domain", "")):
            link["title"] = best_title
        if meta.get("_author") and not link.get("author"):
            link["author"] = meta["_author"]

        enriched += 1

    # Save cache
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")

    # Save enriched links
    OUTPUT.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")

    print(f"\nDone: {enriched} enriched, {skipped} skipped, {errors} errors")
    # Stats
    with_thumb = sum(1 for l in links if l.get("thumbnail"))
    with_desc = sum(1 for l in links if l.get("desc"))
    print(f"Thumbnails: {with_thumb}/{len(links)}")
    print(f"Descriptions: {with_desc}/{len(links)}")


if __name__ == "__main__":
    main()
