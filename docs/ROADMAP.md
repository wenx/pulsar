# Pulsar Roadmap

## 已完成

### P1 — 可靠性

- [x] **Microlink 错误检测改进** — 改为检查 Content-Type 是否为 `image/*`
- [x] **SVG 标题转义补全** — 已核查：文本节点无需转义，无问题
- [x] **XSS — category/topic nav** — innerHTML 补全 `escHtml` / `escAttr`
- [x] **Content-Length DoS** — server.py 请求体限制 64KB（`MAX_BODY`）
- [x] **缓存 TTL 逻辑** — 修复 `cache_age is None` 死代码，旧条目视为 fresh 保留
- [x] **analyze.py code fence** — 正确处理 ` ```json ` 带语言标记的返回格式
- [x] **GitHub API rate limit** — `_api_get` 检测 403/429，报错含 remaining/reset；`GITHUB_TOKEN` 可选提升至 5000 次/小时

### P2 — 代码质量

- [x] **Vault 路径移入配置** — 移入 `config.py` 的 `VAULT_PATH`，支持环境变量覆盖
- [x] **元数据缓存过期机制** — `CACHE_TTL_DAYS=30`，写入时记录 `_cached_at`
- [x] **favicon 按需生成** — 加 `'.' in domain` 校验，跳过无 TLD 域名
- [x] **URL 规范化** — 改用 `urlparse` 标准化：lowercase scheme/host，strip trailing slash，drop fragment

### P3 — 增强

- [x] **删除操作确认** — 已核查：`commitDelete()` 验证服务端响应，失败时 `loadLinks()` 恢复
- [x] **Sync 按钮进度轮询** — 每 2 秒轮询 `/api/status`，pipeline 完成后自动刷新链接
- [x] **Light Theme** — CSS 变量系统重构，`[data-theme="light"]` 暖纸色调；☀/☽ 切换按钮，跟随系统 `prefers-color-scheme`，偏好存 localStorage
- [x] **自动同步** — 服务器 cron 每小时自动跑完整 pipeline；Obsidian Links.md 用 `push-obsidian-links.sh` 手动推送触发
- [x] **部署** — DMIT 服务器（154.17.28.133），Nginx 反代 + systemd 守护进程，`anthropic` SDK 已安装，pipeline 完整可用
- [x] **域名配置** — DNS A 记录 `pulsar.wenxin.io` → `154.17.28.133`，HTTP 可用；443 被 xray（REALITY）占用，暂不支持 HTTPS
- [x] **响应式布局优化** — 参考 Poche.app，masonry 改为百分比断点方案（5/4/3/2/1 列，按内容区宽度 1920/1440/1024/640 切换），sidebar 208px，header/toolbar/footer 分割线对齐
- [x] **Topics 侧边栏可收起** — 默认收起，点击标题展开/收起，箭头旋转动画
- [x] **安全与性能加固** — 文件锁原子写、缩略图 10MB 限制、SVG 转义补全、masonry reflow 优化

- [x] **Pipeline 竞争修复** — 并发 pipeline 线程读写 links.json 导致 AI summary 丢失；改用 rerun flag 机制，新链接到来时排队重跑而非启动新线程
- [x] **Telegram 同步架构重构** — Marvin 只写 `pulsar-links-telegram.json`，不执行 git 操作；系统 crontab 通过 GitHub API 推送，去掉 OpenClaw workspace 下的 git clone
- [x] **OpenClaw workspace 清理** — Pulsar 代码与 Marvin bot 文件分离，workspace 不再维护 Pulsar 仓库副本

---

## 待办

### P3 — 增强

- [ ] **AI Categories 重新定义** — 现有 category 是主题分类（Technology、Economics…），改为内容类型分类：`Article / Media / Tool / Design / Development / Crypto / Other`；同步更新 `config.py` 的 `AI_CATEGORIES`、AI prompt、前端过滤逻辑
- [ ] **标签过滤多选** — 当前只能单标签过滤，支持多标签 AND/OR 会更实用
- [ ] **全文搜索** — `content/` 目录已有 Markdown 全文，可接入本地搜索（如 Fuse.js）；现有搜索只匹配 title/domain/tags
- [ ] **HTTPS** — 443 被 xray 占用；解法：xray 迁移到其他端口，或换 IP 单独部署 Pulsar
