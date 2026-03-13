# Pulsar Roadmap

## 已完成

### P1 — 可靠性

- [x] **Microlink 错误检测改进** — 改为检查 Content-Type 是否为 `image/*`
- [x] **SVG 标题转义补全** — 已核查：文本节点无需转义，无问题
- [x] **XSS — category/topic nav** — innerHTML 补全 `escHtml` / `escAttr`
- [x] **Content-Length DoS** — server.py 请求体限制 64KB（`MAX_BODY`）
- [x] **缓存 TTL 逻辑** — 修复 `cache_age is None` 死代码，旧条目视为 fresh 保留
- [x] **analyze.py code fence** — 正确处理 ` ```json ` 带语言标记的返回格式

### P2 — 代码质量

- [x] **Vault 路径移入配置** — 移入 `config.py` 的 `VAULT_PATH`，支持环境变量覆盖
- [x] **元数据缓存过期机制** — `CACHE_TTL_DAYS=30`，写入时记录 `_cached_at`
- [x] **favicon 按需生成** — 加 `'.' in domain` 校验，跳过无 TLD 域名

### P3 — 增强

- [x] **删除操作确认** — 已核查：`commitDelete()` 验证服务端响应，失败时 `loadLinks()` 恢复
- [x] **Sync 按钮进度轮询** — 每 2 秒轮询 `/api/status`，pipeline 完成后自动刷新链接
- [x] **Light Theme** — CSS 变量系统重构，`[data-theme="light"]` 暖纸色调；☀/☽ 切换按钮，跟随系统 `prefers-color-scheme`，偏好存 localStorage

---

## 待办

### P1 — 可靠性

- [x] **GitHub API rate limit** — `_api_get` 检测 403/429，报错含 remaining/reset；`GITHUB_TOKEN` 可选提升至 5000 次/小时

### P2 — 代码质量

- [x] **URL 规范化** — 改用 `urlparse` 标准化：lowercase scheme/host，strip trailing slash，drop fragment

### P3 — 增强

- [ ] **全文搜索** — `content/` 目录已有 Markdown 全文（96 条中 66 条有内容），可接入本地搜索（如 Fuse.js）；现有搜索只匹配 title/domain/tags
- [ ] **标签过滤多选** — 当前只能单标签过滤，支持多标签 AND/OR 会更实用
- [ ] **自动同步** — 当前需手动点 Sync 按钮；可改为 server 启动时自动跑一次 sync，或监听 `pulsar-links-telegram.json` / `Links.md` 文件变更触发（watchdog）
- [ ] **Light Theme** — 当前仅暗色主题；可加亮色主题切换，跟随系统 `prefers-color-scheme` 或手动切换
- [ ] **标签去重验证** — analyze.py 生成的 tags 可能与 category 重复（如 category=Technology，tags 含 "Technology"）；写入前过滤掉与 category 相同的 tag
- [ ] **Topics 侧边栏可收起** — Topics 列表较长，加折叠/展开按钮
- [ ] **Category 与 Tags 分离** — tags 中不应包含 category 值，前端渲染和 AI prompt 均需约束
- [x] **部署** — DMIT 服务器（154.17.28.133），Nginx 反代 + systemd 守护进程，代码在 `/opt/pulsar`
- [x] **域名配置** — DNS A 记录 `pulsar.wenxin.io` → `154.17.28.133`，Let's Encrypt 证书，自动续期
