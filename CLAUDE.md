# Pulsar — Claude 工作提示

## 工作流程

| 场景 | 命令 |
|------|------|
| 改代码后部署 | `./deploy-code.sh` |
| 更新 Obsidian 链接 | `./push-obsidian-links.sh` |
| 日常 Telegram 链接 | 自动（服务器 cron 每小时） |
| 本地调试 | `python3 server.py`（先 rsync 数据：`rsync -az dmit:/opt/pulsar/links.json .`）|

## 重要原则

- **服务器是 source of truth** — `links.json` 只在服务器上写，本地不直接修改
- **代码改动** — 本地开发 → git commit → `./deploy-code.sh`
- **链接更新** — Obsidian 编辑 Links.md → `./push-obsidian-links.sh`

## 关键文件

- `docs/ROADMAP.md` — 待办事项
- `docs/deployment.md` — 部署架构和运维命令
- `.env` — API keys（不在 git 里）
