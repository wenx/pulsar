# Pulsar

个人链接收藏管理工具，灵感来自 [Poche.app](https://poche.app)。

暗黑 / 黑客美学风格，TX-02 等宽字体，金色主色调 `#c4a44a`。

## 技术栈

- 前端：原生 HTML + CSS + JavaScript（无框架）
- 后端：Python 自定义 HTTP Server
- AI：Claude Haiku API（自动摘要）
- 数据：JSON 文件存储

## 快速开始

```bash
# 1. 安装依赖
pip install anthropic

# 2. 配置 API Key（AI 摘要功能需要）
export ANTHROPIC_API_KEY="sk-ant-xxx"

# 3. 首次运行数据处理 pipeline
python3 parse-links.py        # 解析 Links.md → links.json
python3 enrich-links.py       # 抓取 og 元数据（缩略图、描述、favicon）
python3 ai-enrich.py          # 规则分类：自动分配 category + tags
python3 ai-summarize.py       # AI 摘要生成（Claude Haiku）
python3 generate-ai.py        # 应用 AI 数据 + 生成 SVG 备用缩略图
python3 download-thumbs.py    # 下载缩略图到本地
python3 generate-feed.py      # 生成 RSS 订阅源

# 4. 启动服务
python3 server.py              # http://localhost:3460
```

## 数据流

```
Links.md (Obsidian)
  ↓ parse-links.py
links.json
  ↓ enrich-links.py
links.json + meta-cache.json (og:image, description, favicon)
  ↓ ai-enrich.py
ai-categories.json + ai-tags.json (规则分类)
  ↓ ai-summarize.py
ai-descriptions.json (Claude Haiku 摘要)
  ↓ generate-ai.py
links.json (合并所有 AI 数据 + SVG 缩略图)
  ↓ download-thumbs.py
thumbs/ (本地缩略图)
  ↓ generate-feed.py
feed.xml (RSS 2.0)
  ↓
index.html (客户端渲染)
```

## 功能

### 界面
- **侧边栏**：按格式分类（Article、Video、Podcast 等）+ 按内容主题分类（Technology、Economics 等）
- **搜索**：快捷键 `/` 激活，`Esc` 清除
- **双视图**：Grid（JS 瀑布流）/ List 切换
- **卡片**：缩略图 + 标题 + 描述 + 标签，悬停动效
- **Summary 面板**：最近 10 条 AI 摘要，可折叠

### 链接管理
- **添加链接**：侧边栏 `./add` → 输入 URL → 自动抓取标题 → 运行完整 pipeline
- **删除链接**：卡片右上角 `⋯` 菜单 → `./delete`
- **RSS 订阅**：自动生成 `feed.xml`

### AI 能力
- **自动分类**：基于关键词规则匹配 15 个内容主题
- **自动标签**：域名 + 关键词提取，每条最多 5 个标签
- **AI 摘要**：Claude Haiku 生成 1-2 句描述（中英文自适应）

### 数据处理
- **元数据抓取**：og:image、og:description、favicon，带缓存
- **YouTube 优化**：oEmbed API 获取标题，直连高清缩略图
- **缩略图策略**：YouTube 直连 > og:image > WordPress mshots > SVG 生成
- **稳定命名**：URL hash（`md5(url)[:10]`）作为文件名，增删链接不影响已有数据

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/add` | 添加链接，body: `{"url": "..."}` |
| POST | `/api/delete` | 删除链接，body: `{"url": "..."}` |

添加链接后会自动在后台运行完整 pipeline（抓取元数据 → 分类 → AI 摘要 → 下载缩略图 → 更新 RSS）。

## 文件结构

```
pulsar/
├── index.html           # 主页面 SPA
├── server.py            # 开发服务器 + API
├── links.json           # 链接数据
├── feed.xml             # RSS 订阅源
├── thumbs/              # 本地缩略图
├── parse-links.py       # Links.md 解析
├── enrich-links.py      # 元数据抓取
├── ai-enrich.py         # 规则分类
├── ai-summarize.py      # AI 摘要生成
├── generate-ai.py       # AI 数据应用 + SVG 生成
├── download-thumbs.py   # 缩略图下载
├── generate-feed.py     # RSS 生成
├── meta-cache.json      # 元数据缓存
├── ai-categories.json   # 内容主题分类
├── ai-tags.json         # 关键词标签
├── ai-formats.json      # 格式覆盖
└── ai-descriptions.json # AI 摘要
```

## 分类体系

- **Format**（链接类型）：Article、Video、Podcast、GitHub、Book、Film、Documentary
- **Category**（内容主题）：Technology、Economics、Philosophy、Crypto、Investing 等 15 个
- **Tags**（关键词标签）：AI、Bitcoin、China、startup 等细粒度标签
