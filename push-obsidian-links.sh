#!/bin/bash
# Push Obsidian Links.md to server, then trigger pipeline
set -e

VAULT_PATH="${VAULT_PATH:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/SOLARIS}"

echo "▶ Pushing Links.md to server..."
rsync -az "$VAULT_PATH/Links.md" dmit:/opt/pulsar/Links.md

echo "▶ Running pipeline on server..."
ssh dmit "cd /opt/pulsar && python3 sync.py && python3 fetch.py && python3 analyze.py && python3 assets.py"

echo "✓ Done"
