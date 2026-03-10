#!/usr/bin/env python3
"""
Generate RSS feed (feed.xml) from links.json.
Run after generate-ai.py or download-thumbs.py in the pipeline.
"""

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

INPUT = Path(__file__).parent / "links.json"
OUTPUT = Path(__file__).parent / "feed.xml"

SITE_URL = "https://pulsar.wenxin.io"
FEED_TITLE = "Pulsar"
FEED_DESC = "Curated links from SOLARIS"


def build_rss(links: list) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for link in links:
        if link.get("done"):
            continue

        title = escape(link.get("title", ""))
        url = escape(link.get("url", ""))
        desc = escape(link.get("desc", ""))
        category = link.get("category", "")
        fmt = link.get("format", "")
        tags = link.get("tags", [])

        categories = ""
        if fmt:
            categories += f"      <category>{escape(fmt)}</category>\n"
        if category:
            categories += f"      <category>{escape(category)}</category>\n"
        for tag in tags:
            categories += f"      <category>{escape(tag)}</category>\n"

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <description>{desc}</description>
{categories}    </item>""")

    items_xml = "\n".join(items)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{FEED_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>{FEED_DESC}</description>
    <language>zh-cn</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>
"""


def main():
    links = json.loads(INPUT.read_text("utf-8"))
    xml = build_rss(links)
    OUTPUT.write_text(xml, "utf-8")
    active = sum(1 for l in links if not l.get("done"))
    print(f"Generated feed.xml — {active} items")


if __name__ == "__main__":
    main()
