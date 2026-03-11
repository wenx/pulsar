# Pulsar

个人链接收藏管理工具，灵感来自 [Poche.app](https://poche.app)。

暗黑 / 黑客美学风格，TX-02 等宽字体，金色主色调 `#c4a44a`。

## 技术栈

- 前端：原生 HTML + CSS + JavaScript（无框架）
- 后端：Python 自定义 HTTP Server
- AI：Claude Haiku API（分类 + 标签 + 摘要，一次 API 调用完成）
- 数据：JSON 文件存储

## 快速开始

```bash
# 1. 安装依赖
pip install anthropic

# 2. 配置 API Key
echo 'ANTHROPIC_API_KEY=sk-ant-xxx' > .env
echo 'JINA_API_KEY=jina_xxx' >> .env

# 3. 首次运行 pipeline
python3 parse-links.py    # 解析 Links.md → links.json（仅首次）
python3 fetch.py           # 抓取网页元数据（title, desc, og:image, body text）
python3 analyze.py         # AI 分析：分类 + 标签 + 摘要（Claude Haiku）
python3 assets.py          # 下载缩略图 + 生成 SVG 兜底 + 生成 RSS

# 4. 启动服务
python3 server.py          # http://localhost:3460
```

## Pipeline

三步流水线，每步输入输出都是 `links.json`：

```
links.json
  ↓ fetch.py — 抓取网页，提取 title/desc/og:image/favicon/body_text
links.json + meta-cache.json
  ↓ analyze.py — Claude Haiku 一次调用：分类 + 标签 + 中文摘要
links.json
  ↓ assets.py — 下载缩略图到 thumbs/ + SVG 兜底 + 生成 feed.xml
links.json + thumbs/ + feed.xml
```

Pipeline 是**增量**的——只处理新增或缺少数据的链接。添加新链接后，server 自动在后台运行 pipeline。

### 手动全量重跑

修改了 AI 提示词或分类列表后，用 `--force` 重跑：

```bash
python3 analyze.py --force   # 清掉所有 ai_summary/category/tags，全量重新分析
```

`fetch.py` 和 `assets.py` 不需要 `--force`，它们用 cache 和本地文件自动判断增量。

## 配置

所有配置集中在 `config.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | 3460 | 服务端口 |
| `AI_MODEL` | claude-haiku-4-5-20251001 | AI 模型 |
| `AI_CATEGORIES` | 15 个分类 | 可用分类列表 |
| `AI_ANALYZE_PROMPT` | — | 分析提示词（分类+标签+摘要） |
| `JINA_BASE_URL` | r.jina.ai | Jina Reader 地址 |
| `JINA_API_KEY` | .env | Jina Reader API Key |
| `JINA_TIMEOUT` | 15s | Jina Reader 超时 |
| `THUMB_DOWNLOAD_TIMEOUT` | 15s | 缩略图下载超时 |
| `SITE_URL` | pulsar.wenxin.io | RSS feed 站点地址 |

API Key 放在 `.env` 文件中（已在 .gitignore）。`.env` 由 `config.py` 统一加载，所有脚本自动继承。

## 功能

### 界面
- **侧边栏**：按格式分类（Article、Video、Podcast 等）+ 按内容主题分类
- **搜索**：快捷键 `/` 激活，`Esc` 清除
- **双视图**：Grid（JS 瀑布流）/ List 切换
- **卡片**：缩略图 + 标题 + 描述 + 标签，悬停动效
- **Summary 面板**：最近 10 条 AI 摘要，可折叠

### 链接管理
- **添加链接**：快捷键 `n` 或侧边栏 `./add` → 输入 URL → 即时保存 → 后台 pipeline 自动运行
- **删除链接**：卡片右上角 `⋯` 菜单 → `./delete` → 10 秒内可撤销
- **URL 清理**：自动去除 utm_*、fbclid 等追踪参数
- **RSS 订阅**：自动生成 `feed.xml`

### AI 能力（Claude Haiku，单次调用）
- **自动分类**：15 个内容主题（Technology、Economics、Crypto 等）
- **自动标签**：1-5 个标签
- **AI 摘要**：中文一句话摘要

### 网页抓取（Jina Reader JSON mode）
- 一次 API 调用返回 title、description、content、images
- 自动提取缩略图：YouTube 直链 > Jina images > mshots 兜底

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/add` | 添加链接，body: `{"url": "..."}` |
| POST | `/api/delete` | 删除链接，body: `{"url": "..."}` |
| GET | `/api/status` | Pipeline 运行状态 |

## 文件结构

```
pulsar/
├── index.html         # 主页面 SPA
├── server.py          # 开发服务器 + API
├── config.py          # 集中配置
├── fetch.py           # Step 1: 网页抓取 + 元数据提取
├── analyze.py         # Step 2: AI 分析（分类 + 标签 + 摘要）
├── assets.py          # Step 3: 缩略图下载 + SVG 生成 + RSS
├── parse-links.py     # Links.md → links.json（首次导入）
├── links.json         # 链接数据
├── meta-cache.json    # 元数据缓存
├── feed.xml           # RSS 订阅源
├── thumbs/            # 本地缩略图
├── fonts/             # 自定义字体（TX-02, Tamzen）
└── .env               # API Key（不入库）
```
