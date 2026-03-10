#!/usr/bin/env python3
"""
Download all remote thumbnail images to local thumbs/ directory.
Run once to cache all thumbnails locally for faster loading.
"""

import hashlib
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse


def url_hash(url: str) -> str:
    """Short hash of URL for stable file naming."""
    return hashlib.md5(url.encode()).hexdigest()[:10]

INPUT = Path(__file__).parent / "links.json"
OUTPUT = Path(__file__).parent / "links.json"
THUMBS = Path(__file__).parent / "thumbs"

DELAY = 0.3
TIMEOUT = 15

# User-Agent to avoid blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def guess_ext(url: str, content_type: str = "") -> str:
    """Guess file extension from URL or content-type."""
    if "png" in content_type or url.endswith(".png"):
        return ".png"
    if "svg" in content_type or url.endswith(".svg"):
        return ".svg"
    if "webp" in content_type or url.endswith(".webp"):
        return ".webp"
    if "gif" in content_type or url.endswith(".gif"):
        return ".gif"
    return ".jpg"


def download_thumbnail(url: str, dest: Path) -> bool:
    """Download a thumbnail image. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        content_type = resp.headers.get("Content-Type", "")

        # mshots returns a 1x1 placeholder if not ready yet — retry once
        data = resp.read()
        if len(data) < 1000 and "mshots" in url:
            print(f"    ↻ mshots not ready, retrying in 3s...")
            time.sleep(3)
            resp = urllib.request.urlopen(req, timeout=TIMEOUT)
            data = resp.read()
            if len(data) < 1000:
                print(f"    ✗ mshots still not ready, skipping")
                return False

        ext = guess_ext(url, content_type)
        final = dest.with_suffix(ext)
        final.write_bytes(data)
        return True
    except Exception as e:
        # YouTube maxresdefault may not exist — try hqdefault
        if "img.youtube.com" in url and "maxresdefault" in url:
            fallback = url.replace("maxresdefault", "hqdefault")
            print(f"    ↻ maxres unavailable, trying hqdefault...")
            try:
                req2 = urllib.request.Request(fallback, headers=HEADERS)
                resp2 = urllib.request.urlopen(req2, timeout=TIMEOUT)
                data2 = resp2.read()
                ext = guess_ext(fallback, resp2.headers.get("Content-Type", ""))
                dest.with_suffix(ext).write_bytes(data2)
                return True
            except Exception as e2:
                print(f"    ✗ {str(e2)[:60]}")
                return False
        print(f"    ✗ {str(e)[:60]}")
        return False


def main():
    THUMBS.mkdir(exist_ok=True)
    links = json.loads(INPUT.read_text("utf-8"))

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

        # Check if already downloaded (by hash)
        existing = list(THUMBS.glob(f"{h}.*"))
        if existing:
            link["thumbnail"] = str(existing[0].relative_to(Path(__file__).parent))
            skipped += 1
            continue

        print(f"[{i+1}/{len(links)}] Downloading: {link['title'][:40]}...")

        ext = guess_ext(thumb_url)
        dest = (THUMBS / h).with_suffix(ext)

        if download_thumbnail(thumb_url, dest):
            final = list(THUMBS.glob(f"{h}.*"))
            if final:
                link["thumbnail"] = str(final[0].relative_to(Path(__file__).parent))
            downloaded += 1
        else:
            failed += 1

        time.sleep(DELAY)

    # Save updated links.json with local paths
    OUTPUT.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    local = sum(1 for l in links if l.get("thumbnail") and not l["thumbnail"].startswith("http"))
    print(f"Local thumbnails: {local}/{len(links)}")


if __name__ == "__main__":
    main()
