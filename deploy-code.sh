#!/bin/bash
# Deploy code changes to server
set -e

echo "▶ Pushing to GitHub..."
git push

echo "▶ Pulling on server..."
ssh dmit "cd /opt/pulsar && git pull && systemctl restart pulsar"

echo "✓ Done"
