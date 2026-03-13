# Pulsar 抓取策略

## 整体架构

```
数据来源
  ├─ Obsidian Links.md      → sync.py 增量合并
  └─ Telegram bot JSON      → sync.py 增量合并（已含 ai_summary/tags/category）
         ↓
链接 URL
  ↓ 平台识别（fetch.py）
  ├─ 已知平台 → 专用 API（免费、快、不消耗 Jina token）
  ├─ 微信公众号 → 跳过抓取（反爬无解，保留用户手填数据）
  └─ 未知站点 → Jina Reader（正文提取 + metadata）
                    ↓ 缩略图缺失时
                    Microlink 截屏兜底
                    ↓ 截屏也失败时
                    SVG 程序化占位图
         ↓
AI 分析（analyze.py）
  ├─ Telegram 链接（已有 ai_summary）→ 跳过
  └─ 其他 → Claude Haiku 生成 category / tags / summary
```

## 一、抓取路由

| 平台 | 方式 | 返回数据 | 备注 |
|------|------|----------|------|
| YouTube | oEmbed API | 标题、作者、缩略图 | 免费，无需 key |
| Bilibili | B站 API | 标题、UP主、封面 | 免费，秒回 |
| Vimeo | oEmbed API | 标题、作者、缩略图 | 免费 |
| GitHub | REST API | repo 名、描述、语言、stars | 免费，60 req/hr |
| Spotify | oEmbed API | 标题、封面 | 免费 |
| Reddit | oEmbed API | 标题、作者 | 免费 |
| Wikipedia | REST API | 标题、摘要、首图 | 免费 |
| 微信公众号 | 跳过 | 无（保留用户手填） | 反爬 + JS 渲染，无公开 API |
| 其他（博客、新闻等） | Jina Reader JSON mode | 标题、描述、正文、图片 | 免费 100 万 token/月 |

### 不走 Jina 的原因

- **视频/音乐平台**（YouTube、Bilibili、Vimeo、Spotify）：专用 API 秒回，返回结构化数据，无需消耗 Jina token
- **GitHub**：REST API 返回 stars、语言等结构化信息，比网页抓取更丰富
- **Reddit**：oEmbed 免费获取标题和作者
- **Wikipedia**：REST API 返回干净摘要和首图
- **微信公众号**：反爬严格，HTML 空壳（所有内容 JS 渲染），`<meta>` 标签为空，Jina 也超时。直接跳过

### 仍走 Jina 的平台

- **豆瓣**：反爬严格但 Jina 能处理
- **小宇宙**：API 需认证，Jina 可抓取页面
- **Twitter/X**：API 需付费，Jina 可抓取
- **Notion 公开页面**：无公开 API（需 integration token），Jina 可抓取
- **其他博客、新闻、Newsletter 等**：Jina 的核心场景

## 二、缩略图选取优先级

```
1. og:image          ← 作者为社交分享精选的图，几乎一定是最佳代表
2. twitter:image     ← 同上，作为 fallback
3. 视频平台封面构造    ← YouTube maxresdefault / Bilibili 封面直链
4. Jina images 首张   ← 页面内提取的图片（跳过 1x1、favicon、SVG、logo）
5. Microlink 截屏     ← 无图时用截屏服务兜底
6. SVG 占位图         ← 最终兜底，程序化生成（assets.py）
```

### 过滤规则

- **已知占位图跳过**：Notion 默认 og:image (`notion.so/images/meta/default.png`)
- **协议相对 URL**（`//` 开头）→ 补 `https:`
- **Bilibili 缩放后缀**（`@100w_100h_1c.png`）→ 去掉拿原图
- **Jina images 过滤**：跳过 `.svg` 文件、含 `logo` 的 URL、`1x1` 追踪像素、`favicon`
- **YouTube maxresdefault 不存在时** → fallback 到 hqdefault（assets.py 下载阶段处理）
- **Microlink 返回 JSON 错误时** → 跳过（检查 `Content-Type` 是否为 `image/*`）

## 三、服务对比（2026.03）

| | Jina Reader | Firecrawl | Microlink |
|---|---|---|---|
| **免费额度** | 100 万 token/月 | 500 页（终身，不重置） | 250 次/天 |
| **核心能力** | 单页正文提取 + metadata | 整站递归爬取 | metadata + 截屏 |
| **正文质量** | 强 | 最强（更干净） | 弱 |
| **截屏** | ✗ | ✗ | ✓ |
| **og:image** | ✓（metadata 字段） | ✓ | ✓ |
| **付费起步** | — | $16/月 3000 页 | — |
| **最适合** | 抓单页正文 + AI 分析 | 大量爬站、RAG | 截屏兜底 |

### 结论

- **Jina Reader** 是主力：单页正文提取 + metadata，免费额度大，适合「收藏一篇文章」的场景
- **Firecrawl** 不需要：强项是递归爬整站，Pulsar 只抓单页；免费额度不重置，性价比低
- **Microlink** 做兜底：仅用于无图时的截屏服务，嵌入式 URL 直接返回图片

## 四、全文存档

Jina Reader 返回的 Markdown 内容存入 `content/` 目录：

```
content/
├── a1b2c3d4e5.md    ← URL MD5 hash 前 10 位
└── ...

# 每个文件格式：
---
title: "文章标题"
source: "https://原始URL"
saved: 2026-03-11
---

正文 Markdown...
```

- Obsidian 可直接读取
- 未来可做全文搜索、RAG、二次分析
- 空间占用小（69/96 篇 ≈ 1.4MB）

## 五、缓存策略

- `meta-cache.json` 缓存所有成功的抓取结果，TTL 30 天（`CACHE_TTL_DAYS`）
- 错误结果（`_error`）不缓存，下次运行自动重试
- 超过 TTL 的缓存条目视为过期，下次运行重新 fetch
- 已完整富化的链接（有 `thumbnail` + `desc` + `content_file`）直接跳过
- 微信公众号标记为 `wechat_skip`，不计入错误统计
