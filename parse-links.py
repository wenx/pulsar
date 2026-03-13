#!/usr/bin/env python3
"""
Parse SOLARIS/Links.md into JSON for Pulsar.
Reads Obsidian markdown link list → outputs links.json
"""

import re
import json
from pathlib import Path
from urllib.parse import urlparse

from config import classify_format, VAULT_PATH

LINKS_MD = VAULT_PATH / "Links.md"
OUTPUT = Path(__file__).parent / "links.json"


def parse_links_md(text: str) -> list[dict]:
    links = []
    lines = text.split("\n")
    current_section = ""
    current_link = None

    for line in lines:
        stripped = line.strip()

        # Section headers
        m = re.match(r"^##\s+(.+)", stripped)
        if m:
            current_section = m.group(1).strip()
            continue

        # Skip frontmatter, empty lines, checkboxes that are done
        if stripped.startswith("---") or not stripped:
            continue

        # Main link line: - [title](url) or - [[wikilink]] with optional tags
        # Handle checkbox format: - [ ] or - [x]
        link_line = stripped
        is_done = False
        if re.match(r"^-\s*\[x\]", link_line):
            is_done = True
            link_line = re.sub(r"^-\s*\[x\]\s*", "", link_line)
        elif re.match(r"^-\s*\[\s\]", link_line):
            link_line = re.sub(r"^-\s*\[\s\]\s*", "", link_line)
        elif re.match(r"^-\s+", link_line):
            link_line = re.sub(r"^-\s+", "", link_line)
        elif line.startswith("\t") or line.startswith("  "):
            # Indented line = annotation for previous link
            if current_link and stripped:
                note = re.sub(r"^-\s*", "", stripped)
                # Clean wikilinks in notes
                note = re.sub(r"\[\[([^\]]+)\]\]", r"\1", note)
                if current_link.get("notes"):
                    current_link["notes"] += " " + note
                else:
                    current_link["notes"] = note
            continue
        else:
            # Bare URL line
            url_match = re.match(r"^(https?://\S+)", stripped)
            if url_match:
                link_line = stripped
            else:
                continue

        # Extract tags
        tags = re.findall(r"#(\w+[\w/-]*)", link_line)
        link_line = re.sub(r"\s*#\w+[\w/-]*", "", link_line).strip()

        # Extract markdown link [title](url)
        md_match = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", link_line)
        # Extract wikilink [[title]]
        wiki_match = re.search(r"\[\[([^\]]+)\]\]", link_line)
        # Bare URL
        bare_match = re.match(r"^(https?://\S+)", link_line)

        title = ""
        url = ""

        if md_match:
            title = md_match.group(1).strip()
            url = md_match.group(2).strip()
        elif wiki_match:
            title = wiki_match.group(1).strip()
            url = ""  # Internal wikilink, no URL
        elif bare_match:
            url = bare_match.group(1).strip()
            title = url

        if not title and not url:
            continue

        # Extract "by [[Author]]" or "by Author"
        author = ""
        by_match = re.search(r"by\s+\[\[([^\]]+)\]\]", link_line)
        if not by_match:
            by_match = re.search(r"by\s+(\S+(?:\s+\S+)?)\s*$", link_line)
        if by_match:
            author = by_match.group(1).strip()

        # Clean title
        title = re.sub(r"\[\[([^\]]+)\]\]", r"\1", title)
        # Remove domain suffixes commonly left in titles
        title = re.sub(r"\s*[-–—|]\s*(YouTube|bilibili|哔哩哔哩|豆瓣|www\.\S+)\s*$", "", title, flags=re.IGNORECASE)

        # Get domain
        domain = ""
        if url:
            try:
                domain = urlparse(url).hostname or ""
                domain = re.sub(r"^www\.", "", domain)
            except:
                pass

        link_obj = {
            "title": title,
            "url": url,
            "domain": domain,
            "author": author,
            "section": current_section,
            "category": classify_link(domain, url, title),
            "format": classify_format(domain),
            "notes": "",
            "done": is_done,
        }

        current_link = link_obj
        links.append(link_obj)

    return links


def classify_link(domain: str, url: str, title: str) -> str:
    """Auto-classify link by domain/URL pattern into content type."""
    d = domain.lower()
    u = url.lower()

    # Video
    video_domains = {
        "youtube.com", "youtu.be", "bilibili.com", "b23.tv",
        "vimeo.com", "netflix.com",
    }
    if any(d.endswith(v) or d == v for v in video_domains):
        return "Video"

    # Podcast
    if any(kw in d for kw in ["podcast", "joincolossus", "whatbitcoindid"]):
        return "Podcast"

    # Social / Microblog
    social_domains = {
        "twitter.com", "x.com", "threads.net", "mastodon.social",
        "reddit.com", "v2ex.com",
    }
    if any(d.endswith(v) or d == v for v in social_domains):
        return "Social"

    # GitHub / Code
    if "github.com" in d or "gitlab.com" in d:
        return "GitHub"

    # WeChat articles
    if "mp.weixin.qq.com" in d:
        return "WeChat"

    # Books
    book_domains = {"book.douban.com", "douban.com", "goodreads.com"}
    if any(d.endswith(v) or d == v for v in book_domains):
        return "Book"

    # Notion
    if "notion.site" in d or "notion.so" in d:
        return "Notion"

    # Wiki / Reference
    if "wikipedia.org" in d or "wikihow.com" in d:
        return "Reference"

    # News / Media
    news_domains = {
        "nytimes.com", "bbc.com", "wired.com", "techcrunch.com",
        "anandtech.com", "huxiu.com", "36kr.com", "thepaper.cn",
    }
    if any(d.endswith(v) or d == v for v in news_domains):
        return "News"

    # Archive
    if "archive.is" in d or "archive.org" in d:
        return "Article"

    # Default: Article (blogs, personal sites, etc.)
    return "Article"


def main():
    text = LINKS_MD.read_text(encoding="utf-8")
    links = parse_links_md(text)

    # Filter out wikilinks with no URL (internal notes)
    links = [l for l in links if l["url"]]

    # Drop manual fields (user-added, ephemeral)
    for l in links:
        l.pop("tags", None)
        l.pop("section", None)

    # Stats
    print(f"Parsed {len(links)} links")
    cats = {}
    for l in links:
        c = l["category"]
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    domains = {}
    for l in links:
        d = l["domain"]
        if d:
            domains[d] = domains.get(d, 0) + 1
    top = sorted(domains.items(), key=lambda x: -x[1])[:10]
    print(f"Top domains: {', '.join(f'{d}({n})' for d,n in top)}")

    OUTPUT.write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOutput: {OUTPUT}")


if __name__ == "__main__":
    main()
