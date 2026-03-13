#!/usr/bin/env python3
"""
Step 2: Analyze links — classify category, extract tags, generate summary.
One Claude API call per link, results written directly to links.json.
"""

import argparse
import json
import os
import time
from pathlib import Path

from config import (
    AI_MODEL, AI_MAX_TOKENS, AI_BODY_LIMIT, AI_DESC_LIMIT,
    AI_DELAY, AI_CATEGORIES, AI_ANALYZE_PROMPT,
)

ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"


def get_ai_client():
    """Initialize Anthropic client."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from anthropic import Anthropic
        return Anthropic()
    except ImportError:
        print("  ✗ anthropic SDK not installed. Run: pip install anthropic")
        return None
    except Exception as e:
        print(f"  ✗ Failed to init client: {e}")
        return None


def build_context(link: dict) -> str:
    """Build context string from link data."""
    parts = [f"Title: {link.get('title', '')}"]
    parts.append(f"URL: {link.get('url', '')}")
    parts.append(f"Domain: {link.get('domain', '')}")
    desc = link.get("desc", "")
    if desc:
        parts.append(f"Description: {desc[:AI_DESC_LIMIT]}")
    body = link.get("body_text", "")
    if body:
        parts.append(f"\nArticle content:\n{body[:AI_BODY_LIMIT]}")
    return "\n".join(parts)


def analyze_link(client, link: dict) -> dict | None:
    """Call Claude to get category, tags, and summary in one shot."""
    context = build_context(link)
    prompt = AI_ANALYZE_PROMPT.format(
        categories=", ".join(AI_CATEGORIES),
        context=context,
    )

    try:
        msg = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        # Strip markdown code fence if present (handles ```json, ```\n, etc.)
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            # Strip language identifier line (e.g. "json\n{...")
            if text and not text.startswith("{"):
                text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.strip()
        # Extract JSON object even if surrounded by extra text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    ✗ Parse error: {e}")
        return None
    except Exception as e:
        print(f"    ✗ API error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-analyze all links (clear existing ai_summary/category/tags)")
    args = parser.parse_args()

    links = json.loads(LINKS_FILE.read_text("utf-8"))

    if args.force:
        cleared = 0
        for l in links:
            for key in ("ai_summary", "category", "tags"):
                if l.pop(key, None) is not None:
                    cleared += 1
        print(f"Force mode: cleared {cleared} fields")

    client = get_ai_client()
    if not client:
        print("No API key or SDK — skipping analysis")
        return

    to_analyze = [
        l for l in links
        if l.get("url") and not l.get("ai_summary")
    ]

    if not to_analyze:
        print("No links need analysis")
        return

    print(f"Analyzing {len(to_analyze)} links...")
    success = 0
    errors = 0

    for i, link in enumerate(to_analyze):
        print(f"  [{i+1}/{len(to_analyze)}] {link.get('title', '')[:50]}...")

        result = analyze_link(client, link)
        if result:
            if result.get("category") and result["category"] in AI_CATEGORIES:
                link["category"] = result["category"]
            if result.get("tags") and isinstance(result["tags"], list):
                link["tags"] = result["tags"][:5]
            if result.get("summary"):
                link["ai_summary"] = result["summary"]
            success += 1
        else:
            errors += 1

        time.sleep(AI_DELAY)

    # Save
    LINKS_FILE.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nDone: {success} analyzed, {errors} errors")


if __name__ == "__main__":
    main()
