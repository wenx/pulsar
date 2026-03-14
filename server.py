#!/usr/bin/env python3
"""
Pulsar dev server — static files + API endpoints.
Replaces `python3 -m http.server 3460`.
"""

import json
import subprocess
import sys
import threading
from datetime import date
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from config import PORT, PIPELINE_TIMEOUT, classify_format, normalize_url, read_links, write_links

ROOT = Path(__file__).parent
DELETED_FILE = ROOT / "deleted.json"
MAX_BODY = 65536  # 64KB max request body

PIPELINE = [
    "sync.py",
    "fetch.py",
    "analyze.py",
    "assets.py",
]

# Pipeline status tracking
pipeline_status = {"running": False, "step": "", "done": True}
_pipeline_rerun = False  # Flag: new link added while pipeline running, need re-run


def _run_pipeline_once():
    """Run all pipeline steps once."""
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


def run_pipeline():
    """Run enrichment pipeline in background. Re-runs if new links added during execution."""
    global _pipeline_rerun
    pipeline_status.update({"running": True, "step": "starting", "done": False})
    while True:
        _pipeline_rerun = False
        print("  ▶ Running pipeline...")
        _run_pipeline_once()
        if _pipeline_rerun:
            print("  ↻ New links added during pipeline, re-running...")
            continue
        break
    pipeline_status.update({"running": False, "step": "", "done": True})
    print("  ✓ Pipeline complete")


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
        elif self.path == "/api/sync":
            self.handle_sync()
        else:
            self.send_error(404)

    def handle_add_link(self):
        try:
            length = min(int(self.headers.get("Content-Length", 0)), MAX_BODY)
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
            links = read_links()
            url_norm = normalize_url(url)
            if any(normalize_url(l.get("url", "")) == url_norm for l in links):
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
                "done": False,
                "date": date.today().isoformat(),
            }

            links.insert(0, new_link)
            write_links(links)

            self.send_json(200, {"ok": True, "title": title, "count": len(links)})
            print(f"  + Added: {title[:40]} ({url})")

            global _pipeline_rerun
            if pipeline_status.get("running"):
                # Pipeline already running — flag for re-run so new link gets processed
                _pipeline_rerun = True
                print("    (pipeline running, queued for re-run)")
            else:
                threading.Thread(target=run_pipeline, daemon=True).start()

        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def handle_sync(self):
        global _pipeline_rerun
        if pipeline_status.get("running"):
            _pipeline_rerun = True
            self.send_json(200, {"ok": True, "rerun": True})
            print("  ↻ Manual sync — pipeline running, queued for re-run")
            return
        self.send_json(200, {"ok": True})
        print("  ↻ Manual sync triggered")
        threading.Thread(target=run_pipeline, daemon=True).start()

    def handle_delete_link(self):
        try:
            length = min(int(self.headers.get("Content-Length", 0)), MAX_BODY)
            body = json.loads(self.rfile.read(length))
            url = body.get("url", "").strip()

            if not url:
                self.send_json(400, {"error": "URL is required"})
                return

            links = read_links()
            original_len = len(links)
            links = [l for l in links if normalize_url(l.get("url", "")) != normalize_url(url)]

            if len(links) == original_len:
                self.send_json(404, {"error": "Link not found"})
                return

            write_links(links)

            # Record deleted URL so sync.py won't re-add it
            deleted = json.loads(DELETED_FILE.read_text("utf-8")) if DELETED_FILE.exists() else []
            norm = normalize_url(url)
            if norm not in deleted:
                deleted.append(norm)
                DELETED_FILE.write_text(json.dumps(deleted, ensure_ascii=False, indent=2), "utf-8")

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
