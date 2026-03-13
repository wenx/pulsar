#!/bin/bash
# Pulsar deploy: sync Obsidian locally, then push data + run pipeline on server
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
REMOTE="dmit:/opt/pulsar"

echo "▶ Step 1/4: sync Obsidian → links.json (local)"
python3 "$ROOT/sync.py"

echo "▶ Step 2/4: rsync data to server"
rsync -az "$ROOT/links.json" "$ROOT/pulsar-links-telegram.json" dmit:/opt/pulsar/

echo "▶ Step 3/4: run pipeline on server (fetch + analyze + assets)"
ssh dmit "cd /opt/pulsar && python3 fetch.py && python3 analyze.py && python3 assets.py"

echo "▶ Step 4/4: rsync generated data back (thumbs + content + links.json)"
rsync -az dmit:/opt/pulsar/links.json "$ROOT/links.json"
rsync -az dmit:/opt/pulsar/thumbs/ "$ROOT/thumbs/"
rsync -az dmit:/opt/pulsar/content/ "$ROOT/content/"

echo "✓ Done"
