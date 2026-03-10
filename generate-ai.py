#!/usr/bin/env python3
"""
Generate AI descriptions + hacker-style SVG thumbnails for links missing them.
Uses Claude Code's context (no API key needed — descriptions provided as input).
"""

import json
import hashlib
import random
from pathlib import Path

INPUT = Path(__file__).parent / "links.json"
OUTPUT = Path(__file__).parent / "links.json"
THUMBS = Path(__file__).parent / "thumbs"
DESCS_FILE = Path(__file__).parent / "ai-descriptions.json"
CATS_FILE = Path(__file__).parent / "ai-categories.json"
FMTS_FILE = Path(__file__).parent / "ai-formats.json"
TAGS_FILE = Path(__file__).parent / "ai-tags.json"

# Hacker-style SVG colors and patterns
ACCENT_COLORS = [
    "#c4a44a",  # gold
    "#4ac4a4",  # teal
    "#a44ac4",  # purple
    "#c44a4a",  # red
    "#4a8ec4",  # blue
    "#4ac44a",  # green
    "#c4884a",  # orange
]

CATEGORY_GLYPHS = {
    "Article": "//",
    "Video": "▶",
    "WeChat": "◈",
    "News": "◆",
    "GitHub": ">_",
    "Podcast": "♪",
    "Book": "□",
    "Notion": "≡",
    "Social": "@",
    "Reference": "※",
}


def make_svg_thumbnail(title: str, category: str, domain: str, index: int) -> str:
    """Generate a hacker-style SVG thumbnail."""
    # Deterministic color from title hash
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    accent = ACCENT_COLORS[h % len(ACCENT_COLORS)]
    glyph = CATEGORY_GLYPHS.get(category, "//")

    # Truncate title for display
    display_title = title[:40] + ("..." if len(title) > 40 else "")
    # Escape XML
    display_title = display_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    domain_esc = domain.replace("&", "&amp;")

    # Generate pseudo-random scan line positions
    random.seed(h)
    scan_lines = "".join(
        f'<line x1="0" y1="{y}" x2="480" y2="{y}" stroke="{accent}" stroke-opacity="0.03"/>'
        for y in range(0, 270, random.randint(4, 8))
    )

    # Grid dots
    dots = ""
    for x in range(20, 460, 40):
        for y in range(20, 250, 40):
            opacity = random.uniform(0.02, 0.08)
            dots += f'<circle cx="{x}" cy="{y}" r="1" fill="{accent}" opacity="{opacity}"/>'

    # Corner decorations
    corner_size = 12

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0a0a"/>
      <stop offset="100%" stop-color="#111"/>
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="480" height="270" fill="url(#bg{index})"/>

  <!-- Scan lines -->
  {scan_lines}

  <!-- Grid dots -->
  {dots}

  <!-- Border frame -->
  <rect x="1" y="1" width="478" height="268" fill="none" stroke="{accent}" stroke-opacity="0.15" rx="2"/>

  <!-- Corner marks -->
  <path d="M{corner_size},1 L1,1 L1,{corner_size}" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M{480-corner_size},1 L479,1 L479,{corner_size}" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M1,{270-corner_size} L1,269 L{corner_size},269" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>
  <path d="M479,{270-corner_size} L479,269 L{480-corner_size},269" fill="none" stroke="{accent}" stroke-opacity="0.5" stroke-width="1.5"/>

  <!-- Category glyph -->
  <text x="24" y="44" font-family="'SF Mono','Cascadia Code',monospace" font-size="18" fill="{accent}" opacity="0.6">{glyph}</text>

  <!-- Accent line -->
  <line x1="24" y1="60" x2="120" y2="60" stroke="{accent}" stroke-opacity="0.3" stroke-width="1"/>

  <!-- Title -->
  <text x="24" y="120" font-family="'SF Mono','Cascadia Code',monospace" font-size="16" fill="#e8e4de" opacity="0.9">
    <tspan x="24" dy="0">{display_title}</tspan>
  </text>

  <!-- Domain -->
  <text x="24" y="245" font-family="'SF Mono','Cascadia Code',monospace" font-size="11" fill="{accent}" opacity="0.4">{domain_esc}</text>

  <!-- Signal indicator -->
  <circle cx="456" cy="245" r="3" fill="{accent}" opacity="0.5">
    <animate attributeName="opacity" values="0.2;0.7;0.2" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>'''
    return svg


def apply_categories(links: list, cats: dict):
    """Apply AI-generated categories (topics) to links."""
    applied = 0
    for link in links:
        url = link.get("url", "")
        if url in cats:
            link["category"] = cats[url]
            applied += 1
    print(f"Applied {applied} AI categories")


def apply_formats(links: list, fmts: dict):
    """Apply AI-generated format overrides to links."""
    applied = 0
    for link in links:
        url = link.get("url", "")
        if url in fmts:
            link["format"] = fmts[url]
            applied += 1
    print(f"Applied {applied} AI format overrides")


def apply_tags(links: list, tags: dict):
    """Apply AI-generated tags to links."""
    applied = 0
    for link in links:
        url = link.get("url", "")
        if url in tags:
            link["tags"] = tags[url]
            applied += 1
    print(f"Applied {applied} AI tags")


def apply_descriptions(links: list, descs: dict):
    """Apply AI-generated descriptions to links."""
    applied = 0
    for link in links:
        url = link.get("url", "")
        if url in descs and not link.get("desc"):
            link["desc"] = descs[url]
            applied += 1
    print(f"Applied {applied} AI descriptions")


def url_hash(url: str) -> str:
    """Short hash of URL for stable file naming."""
    return hashlib.md5(url.encode()).hexdigest()[:10]


def generate_thumbnails(links: list):
    """Generate SVG thumbnails for links without one."""
    generated = 0
    for i, link in enumerate(links):
        if link.get("thumbnail"):
            continue

        h = url_hash(link.get("url", str(i)))
        svg = make_svg_thumbnail(
            link["title"],
            link.get("category", "Article"),
            link.get("domain", ""),
            i,
        )
        filename = f"{h}.svg"
        (THUMBS / filename).write_text(svg, encoding="utf-8")
        link["thumbnail"] = f"thumbs/{filename}"
        generated += 1

    print(f"Generated {generated} SVG thumbnails")


def main():
    links = json.loads(INPUT.read_text("utf-8"))

    # Apply AI categories if file exists
    if CATS_FILE.exists():
        cats = json.loads(CATS_FILE.read_text("utf-8"))
        apply_categories(links, cats)

    # Apply AI format overrides if file exists
    if FMTS_FILE.exists():
        fmts = json.loads(FMTS_FILE.read_text("utf-8"))
        apply_formats(links, fmts)

    # Apply AI tags if file exists
    if TAGS_FILE.exists():
        tags = json.loads(TAGS_FILE.read_text("utf-8"))
        apply_tags(links, tags)

    # Apply AI descriptions if file exists
    if DESCS_FILE.exists():
        descs = json.loads(DESCS_FILE.read_text("utf-8"))
        apply_descriptions(links, descs)

    # Generate missing thumbnails
    generate_thumbnails(links)

    # Save
    OUTPUT.write_text(json.dumps(links, ensure_ascii=False, indent=2), "utf-8")

    # Stats
    with_desc = sum(1 for l in links if l.get("desc"))
    with_thumb = sum(1 for l in links if l.get("thumbnail"))
    print(f"\nFinal: {with_desc}/{len(links)} descriptions, {with_thumb}/{len(links)} thumbnails")


if __name__ == "__main__":
    main()
