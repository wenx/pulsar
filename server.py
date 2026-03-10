#!/usr/bin/env python3
"""
Pulsar dev server — static files + API endpoints.
Replaces `python3 -m http.server 3460`.
"""

import json
import re
import subprocess
import sys
import threading
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

PORT = 3460
ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"

# Pipeline scripts to run after adding a link
PIPELINE = [
    "enrich-links.py",    # Fetch og metadata, thumbnail, favicon
    "ai-enrich.py",       # Auto-classify category + extract tags (rule-based)
    "ai-summarize.py",    # Generate AI descriptions via Claude API
    "generate-ai.py",     # Apply AI categories, tags, descriptions + SVG thumbs
    "download-thumbs.py", # Download thumbnails locally
    "generate-feed.py",   # Regenerate RSS feed
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def run_pipeline():
    """Run enrichment pipeline in background."""
    print("  ▶ Running pipeline...")
    for script in PIPELINE:
        path = ROOT / script
        if not path.exists():
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            lines = result.stdout.strip().splitlines()
            if lines:
                print(f"    {script}: {lines[-1]}")
            if result.returncode != 0 and result.stderr:
                print(f"    ✗ {script}: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"    ✗ {script}: timeout")
    print("  ✓ Pipeline complete")


def fetch_title(url: str) -> str:
    """Quick fetch of page <title>. Returns '' on failure."""
    # YouTube oEmbed (more reliable than scraping)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().replace("www.", "")
    if host in ("youtube.com", "m.youtube.com", "youtu.be"):
        try:
            from urllib.parse import parse_qs, quote
            oembed_url = f"https://www.youtube.com/oembed?url={quote(url, safe='')}&format=json"
            req = urllib.request.Request(oembed_url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("title", "")
        except Exception:
            pass

    # Generic: scrape <title>
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=5)
        html = resp.read(20_000).decode("utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return ""


def classify_format(domain: str) -> str:
    """Auto-detect link format from domain."""
    d = domain.lower()
    video_domains = {"youtube.com", "youtu.be", "bilibili.com", "b23.tv", "vimeo.com"}
    podcast_kw = {"podcast", "joincolossus", "whatbitcoindid"}
    if any(d.endswith(v) or d == v for v in video_domains):
        return "Video"
    if any(kw in d for kw in podcast_kw):
        return "Podcast"
    if "github.com" in d or "gitlab.com" in d:
        return "GitHub"
    return "Article"


class PulsarHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/add":
            self.handle_add_link()
        elif self.path == "/api/delete":
            self.handle_delete_link()
        else:
            self.send_error(404)

    def handle_add_link(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            url = body.get("url", "").strip()

            # --- Validation ---
            if not url:
                self.send_json(400, {"error": "URL is required"})
                return

            # Basic URL format check
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                self.send_json(400, {"error": "Invalid URL — must start with http:// or https://"})
                return

            domain = parsed.hostname.replace("www.", "")

            # --- Duplicate check ---
            links = json.loads(LINKS_FILE.read_text("utf-8"))
            existing_urls = {l.get("url", "") for l in links}
            # Normalize: strip trailing slash for comparison
            url_norm = url.rstrip("/")
            if any(u.rstrip("/") == url_norm for u in existing_urls):
                self.send_json(409, {"error": "Link already exists"})
                return

            # --- Auto-fetch title ---
            title = fetch_title(url) or domain or url

            # --- Build link entry ---
            new_link = {
                "title": title,
                "url": url,
                "domain": domain,
                "author": "",
                "category": "",
                "format": classify_format(domain),
                "notes": "",
                "done": False,
            }

            links.insert(0, new_link)
            LINKS_FILE.write_text(
                json.dumps(links, ensure_ascii=False, indent=2), "utf-8"
            )

            self.send_json(200, {"ok": True, "title": title, "count": len(links)})
            print(f"  + Added: {title[:40]} ({url})")

            threading.Thread(target=run_pipeline, daemon=True).start()

        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def handle_delete_link(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            url = body.get("url", "").strip()

            if not url:
                self.send_json(400, {"error": "URL is required"})
                return

            links = json.loads(LINKS_FILE.read_text("utf-8"))
            original_len = len(links)
            links = [l for l in links if l.get("url", "").rstrip("/") != url.rstrip("/")]

            if len(links) == original_len:
                self.send_json(404, {"error": "Link not found"})
                return

            LINKS_FILE.write_text(
                json.dumps(links, ensure_ascii=False, indent=2), "utf-8"
            )

            self.send_json(200, {"ok": True, "count": len(links)})
            print(f"  - Deleted: {url}")

        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def send_json(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        msg = str(args[0]) if args else ""
        if "/api/" in msg or "200" not in " ".join(str(a) for a in args):
            super().log_message(format, *args)


def main():
    server = HTTPServer(("", PORT), PulsarHandler)
    print(f"Pulsar server running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
