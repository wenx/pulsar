#!/usr/bin/env python3
"""
Auto-enrich links with category, tags, and format using keyword matching.
No API key needed — rule-based classification.
Only processes links missing category/tags. Does not overwrite existing values.
"""

import json
import re
from pathlib import Path

INPUT = Path(__file__).parent / "links.json"
OUTPUT = Path(__file__).parent / "links.json"
CATS_FILE = Path(__file__).parent / "ai-categories.json"
TAGS_FILE = Path(__file__).parent / "ai-tags.json"
FMTS_FILE = Path(__file__).parent / "ai-formats.json"

# Category rules: (category, keywords)
# Checked in order — first match wins
CATEGORY_RULES = [
    ("Crypto", [
        "crypto", "bitcoin", "btc", "ethereum", "defi", "dao", "nft",
        "web3", "blockchain", "steth", "aave", "token", "加密", "区块链",
        "币", "链上", "钱包",
    ]),
    ("Technology", [
        "ai", "artificial intelligence", "llm", "gpt", "claude",
        "chip", "semiconductor", "tsmc", "nvidia", "5g", "huawei",
        "software", "hardware", "computing", "algorithm", "code",
        "人工智能", "芯片", "半导体", "算法", "技术", "编程",
    ]),
    ("Investing", [
        "invest", "portfolio", "fund", "stock", "market", "asset",
        "warren buffett", "munger", "value investing", "hedge",
        "投资", "基金", "资产", "股票", "财富", "理财",
    ]),
    ("Economics", [
        "economy", "economic", "gdp", "inflation", "fiscal",
        "monetary", "currency", "forex", "trade war", "tariff",
        "debt", "recession", "央行", "经济", "货币", "汇率",
        "财政", "贸易", "通胀", "衰退", "资产负债",
    ]),
    ("Geopolitics", [
        "geopolit", "war", "sanction", "nato", "china-us",
        "taiwan", "hong kong", "censorship", "authorit",
        "地缘", "台湾", "香港", "制裁", "霸权",
    ]),
    ("Philosophy", [
        "philosophy", "meaning", "existential", "stoic", "ethics",
        "consciousness", "happiness", "life advice", "wisdom",
        "哲学", "人生", "意义", "幸福", "智慧", "思想",
    ]),
    ("Science", [
        "science", "physics", "biology", "evolution", "quantum",
        "energy", "climate", "cybernetics", "neuroscience",
        "科学", "物理", "生物", "进化", "量子", "能源",
    ]),
    ("History", [
        "history", "ancient", "medieval", "empire", "dynasty",
        "civilization", "war ", "century", "历史", "文明",
        "朝代", "帝国", "古代",
    ]),
    ("Culture", [
        "culture", "art", "music", "film", "movie", "cinema",
        "literature", "design", "aesthetic", "文化", "艺术",
        "音乐", "电影", "文学", "审美", "设计",
    ]),
    ("Business", [
        "business", "startup", "entrepreneur", "company", "ceo",
        "management", "org", "product", "创业", "企业",
        "公司", "管理", "产品",
    ]),
    ("Health", [
        "health", "diet", "exercise", "sleep", "cortisol",
        "ketosis", "nutrition", "mental health", "健康",
        "饮食", "运动", "睡眠",
    ]),
    ("Thinking", [
        "mental model", "cognition", "thinking", "decision",
        "rational", "bias", "first principles", "思维",
        "认知", "决策", "理性",
    ]),
    ("Learning", [
        "learning", "study", "education", "tutorial", "course",
        "book review", "reading", "学习", "教育", "读书",
    ]),
    ("Productivity", [
        "productivity", "routine", "workflow", "habit", "pkm",
        "note-taking", "效率", "习惯", "工作流",
    ]),
    ("Resource", [
        "curated", "collection", "list", "directory", "best of",
        "awesome", "合集", "精选", "目录", "索引",
    ]),
]

# Tag extraction: domain/keyword → suggested tags
TAG_PATTERNS = {
    "youtube.com": ["YouTube"],
    "youtu.be": ["YouTube"],
    "bilibili.com": ["bilibili"],
    "b23.tv": ["bilibili"],
    "github.com": ["GitHub", "open-source"],
    "mp.weixin.qq.com": ["WeChat"],
    "substack.com": ["newsletter"],
    "notion.so": ["Notion"],
    "notion.site": ["Notion"],
    "mirror.xyz": ["Web3", "mirror"],
}

KEYWORD_TAGS = [
    ("AI", ["artificial intelligence", " ai ", "llm", "gpt", "claude", "机器学习", "人工智能"]),
    ("Bitcoin", ["bitcoin", "btc", "比特币"]),
    ("Ethereum", ["ethereum", "eth", "以太坊"]),
    ("DeFi", ["defi", "aave", "uniswap", "compound"]),
    ("DAO", ["dao", "去中心化自治"]),
    ("Web3", ["web3", "web 3"]),
    ("China", ["china", "中国", "chinese"]),
    ("US", ["america", "united states", "美国"]),
    ("startup", ["startup", "创业", "entrepreneur"]),
    ("book-review", ["书评", "book review", "读书笔记"]),
    ("documentary", ["documentary", "纪录片"]),
    ("podcast", ["podcast", "播客"]),
    ("macro", ["macro", "宏观"]),
    ("long-form", ["longread", "long-form", "longreads"]),
]


def classify_category(title: str, desc: str, domain: str) -> str:
    """Classify link category by keyword matching."""
    text = f"{title} {desc} {domain}".lower()
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return cat
    return "Unknown"


def extract_tags(title: str, desc: str, domain: str) -> list:
    """Extract tags from title, description, and domain."""
    tags = []
    text = f"{title} {desc}".lower()

    # Domain-based tags
    for d, t in TAG_PATTERNS.items():
        if d in domain.lower():
            tags.extend(t)
            break

    # Keyword-based tags
    for tag, keywords in KEYWORD_TAGS:
        for kw in keywords:
            if kw in text:
                tags.append(tag)
                break

    # Extract capitalized proper nouns from title (likely names/brands)
    words = re.findall(r'\b[A-Z][a-z]{2,}\b', title)
    for w in words[:2]:
        if w not in tags and w not in ("The", "How", "Why", "What", "This", "And", "For", "Not"):
            tags.append(w)

    return list(dict.fromkeys(tags))[:5]  # dedupe, max 5


def main():
    links = json.loads(INPUT.read_text("utf-8"))

    # Load existing AI data
    cats = json.loads(CATS_FILE.read_text("utf-8")) if CATS_FILE.exists() else {}
    tags = json.loads(TAGS_FILE.read_text("utf-8")) if TAGS_FILE.exists() else {}
    fmts = json.loads(FMTS_FILE.read_text("utf-8")) if FMTS_FILE.exists() else {}

    new_cats = 0
    new_tags = 0

    for link in links:
        url = link.get("url", "")
        if not url:
            continue
        title = link.get("title", "")
        desc = link.get("desc", "")
        domain = link.get("domain", "")

        # Auto-classify category if missing
        if url not in cats and not link.get("category"):
            cat = classify_category(title, desc, domain)
            cats[url] = cat
            new_cats += 1

        # Auto-extract tags if missing
        if url not in tags and not link.get("tags"):
            t = extract_tags(title, desc, domain)
            if t:
                tags[url] = t
                new_tags += 1

    # Save updated AI data
    CATS_FILE.write_text(json.dumps(cats, ensure_ascii=False, indent=2), "utf-8")
    TAGS_FILE.write_text(json.dumps(tags, ensure_ascii=False, indent=2), "utf-8")

    print(f"Auto-enriched: {new_cats} categories, {new_tags} tags")


if __name__ == "__main__":
    main()
