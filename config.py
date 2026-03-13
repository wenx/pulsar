"""Pulsar shared configuration."""

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Load .env if present
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Server
PORT = 3460

# Network
JINA_TIMEOUT = 15        # Jina Reader timeout (seconds)
PIPELINE_TIMEOUT = 120   # pipeline script timeout (seconds)
FETCH_DELAY = 0.5        # rate limit between fetches (seconds)

# Jina Reader
JINA_BASE_URL = "https://r.jina.ai/"
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")

# GitHub API (optional token raises rate limit from 60 to 5000 req/hr)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Content limits
BODY_TEXT_LIMIT = 3000           # max chars for body text

# AI analysis
AI_MODEL = "claude-haiku-4-5-20251001"
AI_MAX_TOKENS = 300
AI_BODY_LIMIT = 2500             # max chars of body text in prompt
AI_DESC_LIMIT = 300              # max chars of description in prompt
AI_DELAY = 0.3                   # rate limit between API calls (seconds)

AI_CATEGORIES = [
    "Crypto", "Technology", "Investing", "Economics", "Geopolitics",
    "Philosophy", "Science", "History", "Culture", "Business",
    "Health", "Thinking", "Learning", "Productivity", "Resource",
]

AI_ANALYZE_PROMPT = """根据以下链接信息，返回 JSON：
- "category": 从 [{categories}] 中选一个最匹配的
- "tags": 1-5 个英文标签，简短有区分度
- "summary": 一句中文摘要，像编辑写导语一样精炼，抓住最核心的一个观点

示例输出：
{{"category": "Technology", "tags": ["AI", "LLM", "OpenAI"], "summary": "GPT-4o 将多模态能力整合进单一模型，推理速度提升两倍且成本减半。"}}

{context}

如果信息不足以判断内容，category 填 "Resource"，summary 根据标题和域名做合理推测。
只输出 JSON，不要其他内容。"""

# Thumbnail download
THUMB_DOWNLOAD_DELAY = 0.3       # rate limit between downloads (seconds)
THUMB_DOWNLOAD_TIMEOUT = 15      # download timeout (seconds)
MICROLINK_SCREENSHOT_URL = "https://api.microlink.io/?url={url}&screenshot=true&meta=false&embed=screenshot.url"

# Metadata cache
CACHE_TTL_DAYS = 30              # days before cached fetch data is considered stale

# Obsidian vault
VAULT_PATH = Path(os.environ.get(
    "VAULT_PATH",
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/SOLARIS"
))

# RSS feed
SITE_URL = "http://pulsar.wenxin.io"
FEED_TITLE = "Pulsar"
FEED_DESC = "Curated links from SOLARIS"

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication: lowercase scheme/host, strip trailing slash, drop fragment."""
    try:
        p = urlparse(url.strip())
        return urlunparse((
            p.scheme.lower(),
            p.netloc.lower(),
            p.path.rstrip("/"),
            p.params,
            p.query,
            "",  # drop fragment
        ))
    except Exception:
        return url.strip()


def url_hash(url: str) -> str:
    """Short hash of URL for filename."""
    return hashlib.md5(url.encode()).hexdigest()[:10]


def classify_format(domain: str) -> str:
    """Auto-detect link format from domain."""
    d = domain.lower()
    video_domains = {
        "youtube.com", "youtu.be", "bilibili.com", "b23.tv",
        "vimeo.com", "netflix.com",
    }
    if any(d.endswith(v) or d == v for v in video_domains):
        return "Video"
    if any(kw in d for kw in ["podcast", "joincolossus", "whatbitcoindid"]):
        return "Podcast"
    if "github.com" in d or "gitlab.com" in d:
        return "GitHub"
    return "Article"
