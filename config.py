"""Pulsar shared configuration."""

import os
from pathlib import Path

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
FETCH_TIMEOUT = 10       # direct scrape timeout (seconds)
JINA_TIMEOUT = 15        # Jina Reader timeout (seconds)
PIPELINE_TIMEOUT = 120   # pipeline script timeout (seconds)
FETCH_DELAY = 0.5        # rate limit between fetches (seconds)

# Jina Reader
JINA_BASE_URL = "https://r.jina.ai/"

# Content limits
HTML_READ_LIMIT = 200_000       # max bytes to read from HTML
BODY_TEXT_LIMIT = 3000           # max chars for body text
BODY_TEXT_MIN = 200              # min chars to consider body text valid

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

# RSS feed
SITE_URL = "https://pulsar.wenxin.io"
FEED_TITLE = "Pulsar"
FEED_DESC = "Curated links from SOLARIS"

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
