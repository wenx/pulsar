#!/usr/bin/env python3
"""
Pulsar dev server — static files + API endpoints.
Replaces `python3 -m http.server 3460`.
"""

import json
import os
import subprocess
import sys
import threading
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from config import (
    PORT, USER_AGENT, PIPELINE_TIMEOUT,
)

ROOT = Path(__file__).parent

# Load .env if present
_env_file = ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
LINKS_FILE = ROOT / "links.json"

PIPELINE = [
    "enrich-links.py",
    "ai-enrich.py",
    "ai-summarize.py",
    "generate-ai.py",
    "download-thumbs.py",
    "generate-feed.py",
]

HEADERS = {"User-Agent": USER_AGENT}

# Pipeline status tracking
pipeline_status = {"running": False, "step": "", "done": True}


def run_pipeline():
    """Run enrichment pipeline in background."""
    global pipeline_status
    pipeline_status = {"running": True, "step": "starting", "done": False}
    print("  ▶ Running pipeline...")
    for script in PIPELINE:
        path = ROOT / script
        if not path.exists():
            continue
        step_name = script.replace(".py", "")
        pipeline_status["step"] = step_name
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=PIPELINE_TIMEOUT,
            )
            lines = result.stdout.strip().splitlines()
            if lines:
                print(f"    {script}: {lines[-1]}")
            if result.returncode != 0 and result.stderr:
                print(f"    ✗ {script}: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            print(f"    ✗ {script}: timeout")
    pipeline_status = {"running": False, "step": "", "done": True}
    print("  ✓ Pipeline complete")



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
    def do_GET(self):
        if self.path == "/api/status":
            self.send_json(200, pipeline_status)
        else:
            super().do_GET()

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

            # --- Use domain as temporary title, pipeline will enrich later ---
            title = domain or url

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

            pipeline_status.update({"running": True, "step": "queued", "done": False})
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
