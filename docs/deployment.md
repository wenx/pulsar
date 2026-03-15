# Deployment — DMIT Server

## 架构总览

```
┌─ 输入源 ─────────────────────────────────────────────────────┐
│                                                               │
│  Telegram 频道 → Marvin bot → pulsar-links-telegram.json     │
│                    (OpenClaw workspace, 只写文件)              │
│                         ↓                                     │
│                  crontab */30 → GitHub API push               │
│                                                               │
│  Obsidian Links.md → ./push-obsidian-links.sh → rsync 到服务器│
│                                                               │
│  前端 Add Link → POST /api/add → 立即触发 pipeline           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                         ↓
┌─ 服务器 /opt/pulsar (source of truth) ───────────────────────┐
│                                                               │
│  crontab 0 * → git pull → sync.py → fetch.py → analyze.py   │
│                              → assets.py → links.json 更新    │
│                                                               │
│  systemd pulsar.service → server.py :3460                    │
│       ↓                                                       │
│  Nginx :80 → pulsar.wenxin.io                                │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 关键路径

| 路径 | 用途 |
|------|------|
| `/opt/pulsar` | 生产环境，Pulsar 服务 + pipeline |
| `/root/.openclaw/workspace/` | OpenClaw Marvin 工作目录 |
| `/root/sync-telegram-github.sh` | GitHub API 推送脚本 |

### Crontab

| 频率 | 任务 |
|------|------|
| 每小时 | `git pull` → pipeline（sync → fetch → analyze → assets） |
| 每 30 分钟 | `sync-telegram-github.sh`（GitHub API 推 telegram json） |

### 职责分离

| 角色 | 职责 | 不做 |
|------|------|------|
| **Marvin** | 监听频道、生成摘要、写 json | 不碰 git |
| **crontab** | 推 GitHub、跑 pipeline | 不做 AI 分析 |
| **deploy-code.sh** | 部署代码 | 不跑 pipeline |
| **push-obsidian-links.sh** | 推 Links.md + 触发 pipeline | 不推代码 |

---

## 服务器信息

- IP: `154.17.28.133`
- SSH alias: `dmit`（见 `~/.ssh/config`）
- OS: Debian 12
- 代码路径: `/opt/pulsar`

## 依赖安装

首次部署需安装 Python 依赖：

```bash
ssh dmit "python3 -m pip install anthropic --break-system-packages"
```

已安装：`anthropic 0.84.0`（AI 分析）

## 多应用架构

DMIT 服务器用 Nginx 作为统一入口，按子域名路由到不同应用。每个应用跑在各自的端口，由独立的 systemd 服务管理。

```
                    Nginx (80/443)
                         │
          ┌──────────────┼──────────────┐
          │              │              │
  pulsar.wenxin.io  app2.wenxin.io  api.wenxin.io
          │              │              │
    :3460 (Pulsar)  :3461 (App2)   :3462 (App3)
```

每个应用的标准结构：

| 项目 | 路径/配置 |
|------|-----------|
| 代码 | `/opt/<appname>/` |
| 端口 | 独立端口，不冲突 |
| 进程守护 | `/etc/systemd/system/<appname>.service` |
| Nginx 配置 | `/etc/nginx/sites-available/<appname>` |
| 域名 | `<appname>.wenxin.io` → DNS A 记录指向 `154.17.28.133` |

## Pulsar 当前配置

**systemd** `/etc/systemd/system/pulsar.service`：
```ini
[Unit]
Description=Pulsar Link Organizer
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pulsar
ExecStart=/usr/bin/python3 /opt/pulsar/server.py
Restart=always
RestartSec=5
Environment=VAULT_PATH=/opt/pulsar

[Install]
WantedBy=multi-user.target
```

**Nginx** `/etc/nginx/sites-available/pulsar`：
```nginx
server {
    listen 80;
    server_name pulsar.wenxin.io 154.17.28.133;

    location / {
        proxy_pass http://127.0.0.1:3460;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300;
    }
}
```

## 本地开发工作流

**改代码：**
```bash
python3 server.py        # 本地调试（数据较旧，需要先从服务器 rsync 回 links.json）
./deploy-code.sh         # 完成后一键 push + 服务器 pull + restart
```

**更新链接：**
```bash
./push-obsidian-links.sh # 推送 Obsidian Links.md 并触发 pipeline
```

**日常无需操作** — 服务器 cron 每小时自动处理 Telegram 新链接。

**本地拉取最新数据（需要时）：**
```bash
rsync -az dmit:/opt/pulsar/links.json .
```

---

## 数据同步工作流

服务器是 source of truth，本地不管 `links.json`。

```
Telegram 新链接   → Marvin 写入 → crontab 推 GitHub → 每小时 pipeline 处理
Obsidian Links.md → ./push-obsidian-links.sh 手动触发
临时加单个链接    → 前端 Add Link 立即触发 pipeline
```

### Telegram 链接同步

Marvin bot（OpenClaw）监听 Telegram 频道，生成中文摘要/分类，写入 `pulsar-links-telegram.json`（OpenClaw workspace）。Marvin 只写文件，不执行 git 操作。

系统 crontab 每 30 分钟通过 GitHub API 将文件推到仓库：
```
*/30 * * * * /root/sync-telegram-github.sh
```

脚本位置：`/root/sync-telegram-github.sh`，逻辑：读取本地文件 → base64 编码 → GitHub Contents API PUT → 更新仓库文件。内容无变化时静默跳过。

### Pipeline

**`push-obsidian-links.sh`**：把本地 Obsidian 的 `Links.md` rsync 到服务器，然后触发完整 pipeline。

**cron**（服务器每小时整点自动跑）：
```
0 * * * * cd /opt/pulsar && git pull && python3 sync.py && python3 fetch.py && python3 analyze.py && python3 assets.py >> /opt/pulsar/pipeline.log 2>&1
```

查看 pipeline 日志：
```bash
ssh dmit "tail -50 /opt/pulsar/pipeline.log"
```

## 常用命令

```bash
# 推送 Obsidian Links.md 并触发 pipeline
./push-obsidian-links.sh

# 查看服务状态
ssh dmit "systemctl status pulsar"

# 重启服务
ssh dmit "systemctl restart pulsar"

# 查看服务日志
ssh dmit "journalctl -u pulsar -f"

# 查看 pipeline 日志
ssh dmit "tail -50 /opt/pulsar/pipeline.log"

# 更新代码
ssh dmit "cd /opt/pulsar && git pull"

# 重载 Nginx 配置
ssh dmit "nginx -t && systemctl reload nginx"
```

## 新增应用步骤

1. 代码部署到 `/opt/<appname>/`
2. 创建 systemd service，选一个空闲端口
3. 创建 Nginx `server {}` 块，绑定子域名
4. DNS 加 A 记录：`<appname>.wenxin.io` → `154.17.28.133`
5. （可选）用 Certbot 签 HTTPS 证书

## 已完成

- [x] DNS 配置：`pulsar.wenxin.io` A 记录 → `154.17.28.133`
- [x] 数据同步工作流：cron 每小时自动跑 pipeline，`push-obsidian-links.sh` 手动推 Links.md
- [ ] HTTPS：服务器 443 端口被 xray（REALITY 协议）占用，目前只走 HTTP（port 80）
