# Pulsar Roadmap

## 待修复

### P1 — 可靠性

- [x] **Microlink 错误检测改进** — 改为检查 Content-Type 是否为 `image/*`
- [x] **SVG 标题转义补全** — 已核查：`display_title` 和 `domain_esc` 均插入文本节点，非属性值，单引号无需转义，无问题

### P2 — 代码质量

- [x] **Vault 路径移入配置** — 移入 `config.py` 的 `VAULT_PATH`，支持 `VAULT_PATH` 环境变量覆盖
- [x] **元数据缓存过期机制** — 加 `CACHE_TTL_DAYS=30`，缓存条目写入时记录 `_cached_at` 时间戳，超期自动重新 fetch

### P3 — 增强

- [x] **删除操作确认** — 已核查：`commitDelete()` 验证服务端响应，失败时调 `loadLinks()` 恢复状态
- [x] **favicon 按需生成** — 加 `'.' in domain` 校验，跳过 localhost 等无 TLD 域名
