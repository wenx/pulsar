# Deployment — DMIT Server

## 服务器信息

- IP: `154.17.28.133`
- SSH alias: `dmit`（见 `~/.ssh/config`）
- OS: Debian 12
- 代码路径: `/opt/pulsar`

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

## 常用命令

```bash
# 查看服务状态
ssh dmit "systemctl status pulsar"

# 重启服务
ssh dmit "systemctl restart pulsar"

# 查看日志
ssh dmit "journalctl -u pulsar -f"

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

## 待完成

- [ ] DNS 配置：`pulsar.wenxin.io` A 记录 → `154.17.28.133`
- [ ] HTTPS：Let's Encrypt 证书（Certbot）
