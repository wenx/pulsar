# Pulsar — Claude 工作提示

## 工作流程

### 1. 改代码后部署

```bash
./deploy-code.sh
```

发生的动作：
1. `git push` — 把本地代码推到 GitHub
2. `ssh dmit "git pull"` — 服务器从 GitHub 拉取最新代码
3. `systemctl restart pulsar` — 重启服务器上的 Pulsar 进程，使新代码生效

### 2. 更新 Obsidian 链接

```bash
./push-obsidian-links.sh
```

发生的动作：
1. `rsync Links.md → dmit:/opt/pulsar/Links.md` — 把本地 Obsidian vault 里的 Links.md 推到服务器
2. `python3 sync.py` — 解析 Links.md + telegram.json，增量合并到服务器的 links.json
3. `python3 fetch.py` — 抓取新链接的元数据（标题、描述、缩略图 URL）
4. `python3 analyze.py` — 调用 Claude Haiku 分析新链接，生成 category / tags / summary
5. `python3 assets.py` — 下载缩略图到 thumbs/，生成 SVG 占位图，更新 feed.xml

### 3. 日常 Telegram 链接（全自动）

服务器 cron 每小时整点自动执行：
1. `git pull` — 拉取最新代码和 telegram.json
2. `python3 sync.py` — 合并 telegram.json 新链接到 links.json
3. `python3 fetch.py` — 抓取新链接元数据
4. `python3 analyze.py` — AI 分析
5. `python3 assets.py` — 下载缩略图，更新 feed.xml

日志：`ssh dmit "tail -50 /opt/pulsar/pipeline.log"`

### 4. 本地调试

```bash
rsync -az dmit:/opt/pulsar/links.json .   # 先拉取服务器最新数据
python3 server.py                          # 启动本地服务，访问 http://localhost:3460
```

注意：本地的 links.json 是服务器的副本，调试完不要推回服务器（服务器是 source of truth）。

---

## 重要原则

- **服务器是 source of truth** — `links.json` 和 `feed.xml` 只在服务器上由 pipeline 写入，本地不直接修改
- **代码改动走 git** — 本地开发 → `git commit` → `./deploy-code.sh`
- **链接更新走 rsync** — Obsidian 编辑 Links.md → `./push-obsidian-links.sh`
- **不要手动 rsync links.json 到服务器** — 会覆盖服务器上 pipeline 生成的最新数据

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `docs/ROADMAP.md` | 待办事项和已完成功能 |
| `docs/deployment.md` | 部署架构、运维命令、依赖安装 |
| `config.py` | 所有配置项（端口、API、路径、模型等） |
| `.env` | API keys，不在 git 里，需手动维护 |
| `links.json` | 主数据，不在 git 里，服务器 source of truth |

## 服务器信息

- SSH: `ssh dmit`
- 代码: `/opt/pulsar`
- 服务: `systemctl status pulsar`
- 网址: `http://pulsar.wenxin.io`（443 被 xray 占用，暂用 HTTP）
