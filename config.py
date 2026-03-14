"""Pulsar shared configuration."""

import fcntl
import hashlib
import json
import os
import tempfile
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

# ─── Server ───────────────────────────────────────────────────────────────────

PORT = 3460                  # HTTP server port，访问 http://localhost:3460

# ─── Network ──────────────────────────────────────────────────────────────────

JINA_TIMEOUT = 15            # Jina Reader 单次请求超时（秒）
PIPELINE_TIMEOUT = 120       # 单个 pipeline 脚本最长运行时间（秒），超时强制终止
FETCH_DELAY = 0.5            # fetch.py 每条链接之间的间隔（秒），避免触发限速

# ─── Jina Reader ──────────────────────────────────────────────────────────────
# 用于抓取普通网页的正文和 metadata
# 免费额度：100 万 token/月；有 key 可提升速率上限
# 文档：https://jina.ai/reader

JINA_BASE_URL = "https://r.jina.ai/"
JINA_API_KEY = os.environ.get("JINA_API_KEY", "")   # 可选，填入 .env 的 JINA_API_KEY

# ─── GitHub API ───────────────────────────────────────────────────────────────
# 用于抓取 GitHub repo 的描述、stars、语言等信息
# 无 token：60 req/hr；有 token：5000 req/hr

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")   # 可选，填入 .env 的 GITHUB_TOKEN

# ─── Content Limits ───────────────────────────────────────────────────────────

BODY_TEXT_LIMIT = 3000       # fetch.py 保存到 links.json 的 body_text 最大字符数

# ─── AI Analysis ──────────────────────────────────────────────────────────────
# analyze.py 调用 Claude Haiku 对链接进行分类、打标签、生成摘要
# API key 从 .env 的 ANTHROPIC_API_KEY 读取

AI_MODEL = "claude-haiku-4-5-20251001"  # 使用最新 Haiku，速度快、成本低
AI_MAX_TOKENS = 300          # 输出 JSON 足够，无需更多 token
AI_BODY_LIMIT = 2500         # 送入 prompt 的 body_text 最大字符数（节省 token）
AI_DESC_LIMIT = 300          # 送入 prompt 的 description 最大字符数
AI_DELAY = 0.3               # 每次 API 调用之间的间隔（秒），避免触发限速

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

# ─── Thumbnail Download ───────────────────────────────────────────────────────
# assets.py 下载缩略图到 thumbs/ 目录

THUMB_DOWNLOAD_DELAY = 0.3       # 每张图下载之间的间隔（秒）
THUMB_DOWNLOAD_TIMEOUT = 15      # 单张图下载超时（秒）
MICROLINK_SCREENSHOT_URL = "https://api.microlink.io/?url={url}&screenshot=true&meta=false&embed=screenshot.url"
                                 # 无缩略图时调用 Microlink 截屏兜底，免费 250 次/天

# ─── Metadata Cache ───────────────────────────────────────────────────────────
# fetch.py 的抓取结果缓存在 meta-cache.json，避免重复请求

CACHE_TTL_DAYS = 30              # 缓存有效期（天），过期后重新 fetch

# ─── Obsidian Vault ───────────────────────────────────────────────────────────
# sync.py 从 vault 里的 Links.md 读取链接
# 本地默认指向 iCloud SOLARIS vault；服务器通过 .env 的 VAULT_PATH 覆盖为 /opt/pulsar

VAULT_PATH = Path(os.environ.get(
    "VAULT_PATH",
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/SOLARIS"
))

# ─── RSS Feed ─────────────────────────────────────────────────────────────────
# assets.py 生成 feed.xml，供 RSS 阅读器订阅

SITE_URL = "http://pulsar.wenxin.io"   # 注：443 被 xray 占用，暂用 HTTP
FEED_TITLE = "Pulsar"
FEED_DESC = "Curated links from SOLARIS"

# ─── User Agent ───────────────────────────────────────────────────────────────

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ─── Utilities ────────────────────────────────────────────────────────────────

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


ROOT = Path(__file__).parent
LINKS_FILE = ROOT / "links.json"
LINKS_LOCK = ROOT / ".links.lock"


def read_links() -> list:
    """Read links.json with shared lock."""
    if not LINKS_FILE.exists():
        return []
    with open(LINKS_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_SH)
        return json.loads(LINKS_FILE.read_text("utf-8"))


def write_links(links: list):
    """Write links.json atomically with exclusive lock."""
    with open(LINKS_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", dir=LINKS_FILE.parent, suffix=".tmp", delete=False
        )
        try:
            tmp.write(json.dumps(links, ensure_ascii=False, indent=2))
            tmp.close()
            Path(tmp.name).replace(LINKS_FILE)
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise


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
