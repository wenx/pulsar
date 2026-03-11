# Pulsar Roadmap

## 待修复

### P1 — 可靠性

- [ ] **Microlink 错误检测改进** — `assets.py` 用 `len(data) < 1000` 判断截屏失败，应检查 Content-Type 是否为 image
- [ ] **SVG 标题转义补全** — `assets.py` `make_svg_thumbnail` 中单引号 `'` 未转义，可能破坏 SVG 属性

### P2 — 代码质量

- [ ] **Vault 路径移入配置** — `parse-links.py` 硬编码了 iCloud Obsidian 路径，应移到 `config.py` 或环境变量
- [ ] **元数据缓存过期机制** — `meta-cache.json` 永不刷新，URL 内容变化后仍用旧数据。可加 TTL 或手动刷新 UI

### P3 — 增强

- [ ] **删除操作确认** — 前端立即删除后 10 秒 undo，但未验证服务端是否成功
- [ ] **favicon 按需生成** — 当前所有链接都生成 Google S2 URL，即使域名无效
