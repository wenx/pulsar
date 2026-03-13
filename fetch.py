#!/usr/bin/env python3
"""
Step 1: Fetch web pages and extract metadata via Jina Reader (JSON mode).
One API call per URL returns title, description, content, and images.
"""

import json
import time
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

from config import (
    FETCH_DELAY, JINA_BASE_URL, JINA_TIMEOUT, JINA_API_KEY,
    BODY_TEXT_LIMIT, USER_AGENT, MICROLINK_SCREENSHOT_URL, url_hash,
    CACHE_TTL_DAYS,
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


def _api_get(url: str, headers: dict = None, timeout: int = 10) -> dict:
    """Helper: GET JSON from API endpoint."""
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _make_result(title: str = "", description: str = "", content: str = "",
                 og_image: str = "") -> dict:
    """Build a Jina-compatible result dict."""
    result = {"title": title, "description": description, "content": content, "metadata": {}}
    if og_image:
        result["metadata"]["og:image"] = og_image
    return result


# ── Platform-specific fetchers ──

def fetch_bilibili(bvid: str) -> dict:
    """Fetch Bilibili video metadata via API."""
    try:
        data = _api_get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
        d = data.get("data", {})
        if not d:
            return {"_error": "Bilibili API returned no data"}
        pic = d.get("pic", "")
        if pic.startswith("http://"):
            pic = "https://" + pic[7:]
        owner = d.get("owner", {}).get("name", "")
        title = d.get("title", "")
        desc = d.get("desc", "")
        return _make_result(
            title=title,
            description=f"{title} — {owner}" if owner else desc,
            content=desc,
            og_image=pic,
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_youtube(vid: str) -> dict:
    """Fetch YouTube video metadata via oEmbed."""
    try:
        watch_url = f"https://www.youtube.com/watch?v={vid}"
        data = _api_get(
            f"https://www.youtube.com/oembed?url={quote(watch_url, safe='')}&format=json"
        )
        title = data.get("title", "")
        author = data.get("author_name", "")
        return _make_result(
            title=title,
            description=f"{title} — {author}" if author else title,
            og_image=data.get("thumbnail_url", ""),
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_vimeo(url: str) -> dict:
    """Fetch Vimeo video metadata via oEmbed."""
    try:
        data = _api_get(
            f"https://vimeo.com/api/oembed.json?url={quote(url, safe='')}"
        )
        title = data.get("title", "")
        author = data.get("author_name", "")
        return _make_result(
            title=title,
            description=f"{title} — {author}" if author else title,
            og_image=data.get("thumbnail_url", ""),
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_spotify(url: str) -> dict:
    """Fetch Spotify metadata via oEmbed."""
    try:
        data = _api_get(
            f"https://open.spotify.com/oembed?url={quote(url, safe='')}"
        )
        return _make_result(
            title=data.get("title", ""),
            description=data.get("title", ""),
            og_image=data.get("thumbnail_url", ""),
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_github(url: str) -> dict:
    """Fetch GitHub repo metadata via REST API."""
    try:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            return {"_error": "Not a GitHub repo URL"}
        owner, repo = parts[0], parts[1]
        data = _api_get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        title = data.get("full_name", "")
        desc = data.get("description", "") or ""
        lang = data.get("language", "")
        stars = data.get("stargazers_count", 0)
        extras = []
        if lang:
            extras.append(lang)
        if stars:
            extras.append(f"{stars:,}★")
        description = f"{desc} ({', '.join(extras)})" if desc and extras else desc
        return _make_result(
            title=title,
            description=description,
            content=desc,
            og_image=data.get("owner", {}).get("avatar_url", ""),
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_reddit(url: str) -> dict:
    """Fetch Reddit post metadata via oEmbed."""
    try:
        data = _api_get(
            f"https://www.reddit.com/oembed?url={quote(url, safe='')}"
        )
        title = data.get("title", "")
        author = data.get("author_name", "")
        return _make_result(
            title=title,
            description=f"{title} — {author}" if author else title,
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


def fetch_wechat(url: str) -> dict:
    """WeChat articles are anti-scraping. Return error to skip Jina without caching."""
    return {"_error": "wechat_skip"}


def fetch_wikipedia(url: str) -> dict:
    """Fetch Wikipedia article summary via REST API."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        lang = host.split(".")[0] if "." in host else "en"
        title_path = parsed.path.split("/wiki/")[-1] if "/wiki/" in parsed.path else ""
        if not title_path:
            return {"_error": "Not a Wikipedia article URL"}
        data = _api_get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title_path}"
        )
        return _make_result(
            title=data.get("title", ""),
            description=data.get("description", ""),
            content=data.get("extract", ""),
            og_image=data.get("thumbnail", {}).get("source", ""),
        )
    except Exception as e:
        return {"_error": str(e)[:100]}


# ── Platform routing ──

def get_platform_fetcher(url: str):
    """Return (fetch_func, arg) for known platforms, or None to use Jina."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")

    # Video platforms
    platform, vid = extract_video_id(url)
    if platform == "bilibili":
        return (fetch_bilibili, vid)
    if platform == "youtube":
        return (fetch_youtube, vid)
    if host in ("vimeo.com", "player.vimeo.com"):
        return (fetch_vimeo, url)

    # WeChat (anti-scraping, skip Jina)
    if host == "mp.weixin.qq.com":
        return (fetch_wechat, url)

    # Code hosting
    if host == "github.com":
        return (fetch_github, url)

    # Music/Podcast
    if host == "open.spotify.com":
        return (fetch_spotify, url)

    # Social/Forum
    if host in ("reddit.com", "old.reddit.com"):
        return (fetch_reddit, url)

    # Wiki
    if host.endswith("wikipedia.org"):
        return (fetch_wikipedia, url)

    return None


def get_thumbnail(jina_data: dict, url: str) -> str:
    """Pick best thumbnail: og:image > twitter:image > video platform > Jina images > Microlink screenshot."""
    meta = jina_data.get("metadata", {})

    # Known platform placeholder images (useless as thumbnails)
    placeholder_images = {
        "https://www.notion.so/images/meta/default.png",
    }

    # 1. og:image — publisher's chosen social sharing image
    og = meta.get("og:image", "")
    if og:
        # Fix protocol-relative URLs
        if og.startswith("//"):
            og = "https:" + og
        # Bilibili: strip thumbnail resize suffix to get full image
        if "hdslb.com" in og and "@" in og:
            og = og.split("@")[0]
        if og not in placeholder_images:
            return og

    # 2. twitter:image — fallback social image
    tw = meta.get("twitter:image", "")
    if tw:
        if tw.startswith("//"):
            tw = "https:" + tw
        if tw not in placeholder_images:
            return tw

    # 3. Video platform direct thumbnail
    platform, vid = extract_video_id(url)
    if platform == "youtube":
        return f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"

    # 4. Jina images (pick first meaningful one)
    images = jina_data.get("images", {})
    if images:
        for name, img_url in images.items():
            if "1x1" in img_url or "favicon" in img_url.lower():
                continue
            if img_url.lower().endswith(".svg"):
                continue
            if "logo" in img_url.lower():
                continue
            return img_url

    # 5. Microlink screenshot fallback
    if url:
        return MICROLINK_SCREENSHOT_URL.format(url=quote(url, safe=''))
    return ""


def save_content_md(url: str, title: str, content: str) -> str:
    """Save Jina markdown content to content/ directory. Returns filename."""
    CONTENT_DIR.mkdir(exist_ok=True)
    filename = f"{url_hash(url)}.md"
    filepath = CONTENT_DIR / filename

    if filepath.exists():
        return filename

    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_url = url.replace("\\", "\\\\").replace('"', '\\"')
    frontmatter = f"""---
title: "{safe_title}"
source: "{safe_url}"
saved: {date.today().isoformat()}
---

"""
    filepath.write_text(frontmatter + content, "utf-8")
    return filename


def get_favicon_url(domain: str) -> str:
    """Get favicon URL via Google S2. Skip domains without a valid TLD."""
    if domain and '.' in domain:
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

        # Check cache (skip error entries and stale entries so they get retried)
        cached = cache.get(url)
        cache_age = (time.time() - cached.get("_cached_at", 0)) / 86400 if cached else None
        if cached and "_error" not in cached and (cache_age is None or cache_age < CACHE_TTL_DAYS):
            data = cached
        else:
            print(f"[{i+1}/{len(links)}] Fetching: {link['title'][:50]}...")
            pf = get_platform_fetcher(url)
            if pf:
                func, arg = pf
                data = func(arg)
            else:
                data = fetch_via_jina(url)
            if "_error" not in data:
                data["_cached_at"] = time.time()
                cache[url] = data
            time.sleep(FETCH_DELAY)

        if "_error" in data:
            if data["_error"] != "wechat_skip":
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
