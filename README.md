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

# 3. 首次导入 Obsidian Links.md（可选）
python3 sync.py

# 4. 启动服务
python3 server.py          # http://localhost:3460
```

启动后点击 **Sync** 按钮触发完整 pipeline（同步 + 抓取 + 分析 + 资源）。

---

## Pipeline

四步流水线，每步输入输出都是 `links.json`：

```
sync.py    — 增量合并 Obsidian Links.md + Telegram links → links.json
  ↓
fetch.py   — 抓取网页元数据（title / desc / og:image / body_text）
  ↓
analyze.py — Claude Haiku：分类 + 标签 + 中文摘要（跳过已有 ai_summary 的链接）
  ↓
assets.py  — 下载缩略图到 thumbs/ + SVG 兜底 + 生成 feed.xml
```

Pipeline 是**增量**的——只处理缺少数据的链接。添加新链接后，server 自动在后台运行完整 pipeline。

### 手动触发

```bash
# 前端 Sync 按钮 → POST /api/sync → 触发完整 pipeline
# 或命令行单步运行：
python3 sync.py
python3 fetch.py
python3 analyze.py
python3 assets.py
```

### 强制重新分析

```bash
python3 analyze.py --force   # 清掉所有 ai_summary/category/tags，全量重新分析
```

---

## 抓取策略（fetch.py）

### 平台路由

| 平台 | 方式 | 返回数据 |
|------|------|----------|
| YouTube | oEmbed API | 标题、作者、缩略图 |
| Bilibili | B站 API | 标题、UP主、封面 |
| Vimeo | oEmbed API | 标题、作者、缩略图 |
| GitHub | REST API | repo 名、描述、语言、stars |
| Spotify | oEmbed API | 标题、封面 |
| Reddit | oEmbed API | 标题、作者 |
| Wikipedia | REST API | 标题、摘要、首图 |
| 微信公众号 | **跳过** | 反爬 + JS 渲染，保留用户手填数据 |
| 其他 | Jina Reader JSON mode | 标题、描述、正文、图片列表 |

### 缩略图优先级

```
1. og:image          ← 作者为社交分享精选的图
2. twitter:image     ← 同上 fallback
3. 视频平台封面       ← YouTube maxresdefault / Bilibili 封面直链
4. Jina images 首张  ← 跳过 SVG、logo、1x1 追踪像素、favicon
5. Microlink 截屏     ← 无图时截屏兜底（检查 Content-Type 是否为 image/*）
6. SVG 占位图         ← 最终兜底，程序化生成
```

### 缓存策略

- `meta-cache.json` 缓存所有成功的抓取结果，TTL 30 天（`CACHE_TTL_DAYS`）
- 错误结果（`_error`）不缓存，下次自动重试
- 已完整富化的链接（有 `thumbnail` + `desc` + `content_file`）直接跳过

### 全文存档

Jina Reader 返回的 Markdown 正文存入 `content/` 目录，以 URL MD5 hash 命名，可直接被 Obsidian 读取。

---

## 数据同步

### Obsidian（sync.py）

从 `VAULT_PATH/Links.md` 增量导入：
- 新 URL → 写入 `links.json`，pipeline 后续富化
- 已有 URL → 只同步 `done` / `notes` 字段，保留富化数据
- 删除的 URL → 保留在 `links.json`，不删除

`VAULT_PATH` 默认为 iCloud Obsidian SOLARIS vault，可通过环境变量覆盖：

```bash
VAULT_PATH=/path/to/vault python3 sync.py
```

### Telegram（Marvin 🤖）

通过 OpenClaw 自动同步 Telegram 频道链接：

```
Telegram 频道发送链接 → Marvin AI 抓取 + 生成摘要/分类
  → 更新 pulsar-links-telegram.json → Heartbeat 每30分钟推送 GitHub
  → sync.py 合并进 links.json → assets.py 补全缩略图
```

Telegram links 已含 `ai_summary`/`tags`/`category`（Marvin 预填），`analyze.py` 自动跳过，只补 `thumbnail`。

---

## 配置（config.py）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `PORT` | 3460 | 服务端口 |
| `VAULT_PATH` | iCloud SOLARIS | Obsidian vault 路径，支持环境变量覆盖 |
| `CACHE_TTL_DAYS` | 30 | 元数据缓存过期天数 |
| `AI_MODEL` | claude-haiku-4-5-20251001 | AI 模型 |
| `AI_CATEGORIES` | 15 个分类 | 可用分类列表 |
| `JINA_BASE_URL` | r.jina.ai | Jina Reader 地址 |
| `JINA_TIMEOUT` | 15s | Jina Reader 超时 |
| `THUMB_DOWNLOAD_TIMEOUT` | 15s | 缩略图下载超时 |
| `SITE_URL` | http://pulsar.wenxin.io | RSS feed 站点地址（443 被 xray 占用，暂用 HTTP） |

API Key 放在 `.env`（已在 .gitignore），由 `config.py` 统一加载。

---

## 功能

### 界面
- **侧边栏**：按格式分类（Article、Video、Podcast 等）+ 按内容主题分类
- **搜索**：快捷键 `/` 激活，`Esc` 清除
- **双视图**：Grid（瀑布流）/ List 切换
- **卡片**：缩略图 + 标题 + 描述 + 标签 + 日期

### 链接管理
- **添加**：快捷键 `n` → 输入 URL → 即时保存 → 后台 pipeline 自动运行
- **同步**：Sync 按钮 → 合并 Obsidian + Telegram → pipeline 富化
- **删除**：卡片 `⋯` 菜单 → `./delete` → 10 秒内可撤销

### AI 能力
- **自动分类**：15 个内容主题（Technology、Economics、Crypto 等）
- **自动标签**：1-5 个标签
- **AI 摘要**：中文一句话摘要（Claude Haiku，单次调用）

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/add` | 添加链接，body: `{"url": "..."}` |
| POST | `/api/delete` | 删除链接，body: `{"url": "..."}` |
| POST | `/api/sync` | 触发 sync + pipeline |
| GET | `/api/status` | Pipeline 运行状态 |

---

## 文件结构

```
pulsar/
├── index.html                    # 主页面 SPA
├── server.py                     # 开发服务器 + API
├── config.py                     # 集中配置 + 共用工具函数
├── sync.py                       # 增量同步 Links.md + Telegram → links.json
├── fetch.py                      # Step 1: 网页抓取 + 元数据提取
├── analyze.py                    # Step 2: AI 分析（分类 + 标签 + 摘要）
├── assets.py                     # Step 3: 缩略图下载 + SVG 生成 + RSS
├── parse-links.py                # Links.md 解析器（供 sync.py 调用）
├── deploy-code.sh                # 部署代码：git push + 服务器 pull + restart
├── push-obsidian-links.sh        # 推送 Obsidian Links.md 到服务器并触发 pipeline
├── pulsar-links-telegram.json    # Telegram 频道链接（Marvin bot 维护）
├── meta-cache.json               # 元数据缓存（TTL 30天，不入库）
├── links.json                    # 链接数据（不入库，服务器 source of truth）
├── feed.xml                      # RSS 订阅源（不入库，pipeline 生成）
├── content/                      # 全文 Markdown 存档
├── thumbs/                       # 本地缩略图（不入库）
├── fonts/                        # 自定义字体（TX-02, Tamzen）
├── CLAUDE.md                     # Claude Code 工作提示和工作流
├── docs/                         # 文档
│   ├── fetch-strategy.md         # 抓取策略详解
│   ├── deployment.md             # 部署架构和运维命令
│   └── ROADMAP.md                # 待办事项
└── .env                          # API Key（不入库）
```

---

## Changelog

### 2026-03-15

**布局**
- **响应式百分比断点**：masonry 从 min-width 改为百分比断点方案（5/4/3/2/1 列，按内容区宽度 1920/1440/1024/640 切换），卡片始终填满宽度
- **分割线对齐**：header/toolbar/footer 统一高度，左右分割线完美对齐

### 2026-03-14

**部署**
- **DMIT 服务器**：部署到 `154.17.28.133`，Nginx 反代 + systemd 守护进程，`http://pulsar.wenxin.io` 可访问
- **域名**：DNS A 记录 `pulsar.wenxin.io` → `154.17.28.133`（HTTPS 暂不可用，443 被 xray 占用）
- **自动同步**：服务器 cron 每小时自动跑完整 pipeline（git pull → sync → fetch → analyze → assets）
- **deploy-code.sh**：一键部署代码（git push + 服务器 pull + restart）
- **push-obsidian-links.sh**：推送本地 Obsidian Links.md 到服务器并触发 pipeline
- **数据架构**：服务器为 source of truth；`links.json` / `feed.xml` 移出 git，由 pipeline 维护

**主题**
- **Light Theme**：CSS 变量系统重构，`[data-theme="light"]` 暖纸色调（`#f5f2ee`）；☀/☽ 切换按钮，跟随系统 `prefers-color-scheme`，偏好存 localStorage

**代码质量**
- **URL 规范化**：改用 `urlparse` 标准化去重（lowercase scheme/host，strip trailing slash，drop fragment）
- **GitHub API rate limit**：检测 403/429，报错含 remaining/reset 信息；`GITHUB_TOKEN` 可选
- **CLAUDE.md**：新增 Claude Code 工作提示文件，记录工作流程和操作步骤

### 2026-03-13

**数据同步**
- **sync.py**：新增增量同步脚本，合并 Obsidian Links.md + Telegram links，替代 parse-links.py 全量覆盖
- **Telegram 字段同步**：重新 sync 时更新 `ai_summary` / `tags` / `category` / `desc`，空值不覆盖本地数据
- **date 字段**：所有 link 统一记录添加日期，前端卡片显示 M/D 格式
- **Sync 按钮**：前端 Scan 替换为 Sync，调用 `/api/sync` 触发完整 pipeline

**安全修复**
- **XSS**：侧边栏 category-nav / topic-nav 的 innerHTML 补全 `escHtml` / `escAttr`
- **DoS**：server.py 请求体限制 64KB（`MAX_BODY`），防止 Content-Length 攻击

**Bug 修复**
- **缓存 TTL 逻辑**：修复 `cache_age is None` 死代码，旧缓存条目（无 `_cached_at`）视为 fresh 保留
- **analyze.py code fence**：正确处理 ` ```json ` 带语言标记的返回格式
- **favicon**：加 `'.' in domain` 校验，跳过 localhost 等无效域名
- **Microlink 错误检测**：改为检查 `Content-Type` 是否为 `image/*`

**配置**
- **Vault 路径配置化**：`VAULT_PATH` 移入 `config.py`，支持环境变量覆盖
- **缓存 TTL**：`meta-cache.json` 加入 30 天过期机制（`CACHE_TTL_DAYS`）

### 2026-03-11
- **Microlink 错误检测**：改为检查 `Content-Type` 是否为 `image/*`，修复大 JSON 错误响应漏判问题
- **Vault 路径配置化**：`VAULT_PATH` 移入 `config.py`，支持环境变量覆盖
- **缓存 TTL**：`meta-cache.json` 加入 30 天过期机制，超期自动重新 fetch
- **XSS 修复**：`renderSummary` 等处全面使用 `escHtml`
- **pipeline 重构**：6 个脚本合并为 3 步（fetch / analyze / assets）
