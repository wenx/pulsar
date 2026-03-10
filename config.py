"""Pulsar shared configuration."""

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

# AI summarization
AI_MODEL = "claude-haiku-4-5-20251001"
AI_MAX_TOKENS = 150
AI_BODY_LIMIT = 2500             # max chars of body text in prompt
AI_DESC_LIMIT = 300              # max chars of description in prompt
AI_DELAY = 0.3                   # rate limit between API calls (seconds)
AI_SKIP_DESC_THRESHOLD = 50      # skip if existing desc longer than this

AI_SUMMARY_PROMPT = """根据以下信息，写一句简短精辟的摘要。抓住核心观点，不要废话。语言与标题一致。

{context}

只输出摘要，不要其他内容。"""

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
