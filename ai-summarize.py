#!/usr/bin/env python3
"""
Generate AI descriptions for links missing them using Claude Haiku.
Reads links.json, calls Claude API, writes ai-descriptions.json.
"""

import json
import os
import time
from pathlib import Path

from config import (
    AI_MODEL, AI_MAX_TOKENS, AI_BODY_LIMIT, AI_DESC_LIMIT,
    AI_DELAY, AI_SKIP_DESC_THRESHOLD, AI_SUMMARY_PROMPT,
)

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
DESCS_FILE = ROOT / "ai-descriptions.json"


def get_client():
    """Initialize Anthropic client."""
    try:
        from anthropic import Anthropic
        return Anthropic()
    except ImportError:
        print("✗ anthropic SDK not installed. Run: pip install anthropic")
        return None
    except Exception as e:
        print(f"✗ Failed to init client: {e}")
        return None


def summarize_link(client, title: str, url: str, desc: str, domain: str, body_text: str = "") -> str:
    """Generate a one-line summary for a link using Claude."""
    context = f"Title: {title}\nURL: {url}\nDomain: {domain}"
    if desc:
        context += f"\nDescription: {desc[:AI_DESC_LIMIT]}"
    if body_text:
        context += f"\n\nArticle content:\n{body_text[:AI_BODY_LIMIT]}"

    try:
        msg = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": AI_SUMMARY_PROMPT.format(context=context),
            }],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"  ✗ API error: {e}")
        return ""


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("✗ ANTHROPIC_API_KEY not set")
        return

    client = get_client()
    if not client:
        return

    links = json.loads(LINKS_FILE.read_text("utf-8"))
    descs = json.loads(DESCS_FILE.read_text("utf-8")) if DESCS_FILE.exists() else {}

    # Find links needing summaries
    to_summarize = []
    for link in links:
        url = link.get("url", "")
        if not url:
            continue
        if url in descs:
            continue
        if link.get("desc") and len(link["desc"]) > AI_SKIP_DESC_THRESHOLD:
            continue
        to_summarize.append(link)

    if not to_summarize:
        print("No links need AI summaries")
        return

    print(f"Generating summaries for {len(to_summarize)} links...")
    generated = 0
    errors = 0

    for i, link in enumerate(to_summarize):
        url = link.get("url", "")
        title = link.get("title", "")
        desc = link.get("desc", "")
        domain = link.get("domain", "")
        body_text = link.get("body_text", "")

        print(f"  [{i+1}/{len(to_summarize)}] {title[:50]}...")

        summary = summarize_link(client, title, url, desc, domain, body_text)
        if summary:
            descs[url] = summary
            generated += 1
        else:
            errors += 1

        time.sleep(AI_DELAY)

    # Save
    DESCS_FILE.write_text(json.dumps(descs, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nDone: {generated} generated, {errors} errors")


if __name__ == "__main__":
    main()
