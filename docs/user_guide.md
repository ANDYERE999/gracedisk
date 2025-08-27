# GraceDisk 部署指南

本指南面向希望在自己的服务器上部署 GraceDisk 文件管理系统的用户。作为一个开源项目，我尽力让部署过程尽可能简单，但如果你遇到任何问题，请随时通过 GitHub Issues 寻求帮助。

## 系统要求

### 硬件要求

- **最低配置**:
  - CPU: 1 核心
  - 内存: 512MB RAM
  - 存储: 1GB 系统空间 + 你的文件存储空间
  - 网络: 100Mbps 带宽

- **推荐配置**:
  - CPU: 2+ 核心
  - 内存: 2GB+ RAM
  - 存储: SSD 硬盘，根据需要规划存储空间
  - 网络: 1Gbps 带宽

### 软件要求

- **操作系统**: 
  - Ubuntu 20.04+ / Debian 11+ (推荐)
  - CentOS 8+ / RHEL 8+
  - Windows 10+ / Windows Server 2019+
  - macOS 11+

- **Python**: 3.11 或更高版本
- **数据库**: SQLite (内置，无需额外安装)

## 快速部署

### 方式一：使用 uv (推荐)

uv 是现代的 Python 包管理器，速度更快，依赖管理更好。

```bash
# 1. 下载项目
git clone https://github.com/your-username/gracedisk.git
cd gracedisk

# 2. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或在 Windows 上：
# powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 3. 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/macOS
# 或 Windows：
# .venv\Scripts\activate

uv pip install -r requirements.txt

# 4. 配置系统
cp config.yaml.example config.yaml
# 编辑 config.yaml（见配置说明部分）

# 5. 启动服务
python app.py
```

### 方式二：使用传统 pip

```bash
# 1. 下载项目
git clone https://github.com/your-username/gracedisk.git
cd gracedisk

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 Windows：
# venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置系统
cp config.yaml.example config.yaml
# 编辑 config.yaml

# 5. 启动服务
python app.py
```

## 详细配置

### 1. 基础配置 (config.yaml)

```yaml
# 管理员账号设置
admin:
  username: admin          # 管理员用户名
  password: YourStrongPassword123!  # 请务必修改为强密码

# 文件存储路径配置
storage_path: "/var/www/gracedisk/files"  # 管理员和文件存储路径
users_db_path: "gracedisk.db"             # 数据库文件路径

# 访客功能配置
allow_visiter: true                       # 是否允许访客访问
visitor_storage_path: "/var/www/gracedisk/public"  # 访客可访问的路径

# 关于页面配置
about:
  title: "我的文件管理系统"
  version: "v2.0"
  description: |
    这是我的私人文件管理系统，
    支持多用户、文件分享、安全访问等功能。
  footer: "© 2025 我的文件系统"
```

### 2. 目录结构设置

```bash
# 创建必要的目录
sudo mkdir -p /var/www/gracedisk
sudo mkdir -p /var/www/gracedisk/files      # 主要文件存储
sudo mkdir -p /var/www/gracedisk/public     # 访客文件
sudo mkdir -p /var/www/gracedisk/userfiles  # 用户个人文件

# 设置权限（根据你的系统用户调整）
sudo chown -R www-data:www-data /var/www/gracedisk
# 或者
sudo chown -R $(whoami):$(whoami) /var/www/gracedisk

# 设置适当的权限
chmod -R 755 /var/www/gracedisk
```

### 3. 系统服务配置 (Linux)

创建 systemd 服务文件以实现开机自启：

```bash
sudo nano /etc/systemd/system/gracedisk.service
```

服务文件内容：

```ini
[Unit]
Description=GraceDisk File Management System
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/gracedisk
Environment=PATH=/var/www/gracedisk/.venv/bin
ExecStart=/var/www/gracedisk/.venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable gracedisk
sudo systemctl start gracedisk
sudo systemctl status gracedisk
```

### 4. 反向代理配置

#### 使用 Nginx (推荐)

安装 Nginx：

```bash
sudo apt update
sudo apt install nginx  # Ubuntu/Debian
# sudo yum install nginx  # CentOS/RHEL
```

创建 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/gracedisk
```

配置内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名
    
    # 文件上传大小限制
    client_max_body_size 1000M;
    
    # 反向代理到 Flask 应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 静态文件直接服务（可选优化）
    location /static/ {
        alias /var/www/gracedisk/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/gracedisk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 使用 Apache

```bash
sudo apt install apache2
sudo a2enmod proxy proxy_http
```

创建虚拟主机配置：

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # 文件上传大小限制
    LimitRequestBody 1073741824  # 1GB
</VirtualHost>
```

### 5. SSL 证书配置

使用 Let's Encrypt 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书（自动配置 Nginx）
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 生产环境优化

### 1. 使用 Gunicorn (推荐)

安装 Gunicorn：

```bash
uv pip install gunicorn
# 或
pip install gunicorn
```

创建 Gunicorn 配置文件：

```bash
nano gunicorn.conf.py
```

配置内容：

```python
bind = "127.0.0.1:5000"
workers = 4  # CPU 核心数 * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
preload_app = True
```

更新 systemd 服务文件：

```ini
[Service]
ExecStart=/var/www/gracedisk/.venv/bin/gunicorn --config gunicorn.conf.py app:app
```

### 2. 数据库优化

虽然使用 SQLite，但仍可以优化：

```python
# 在 app.py 中添加 SQLite 优化
def init_db():
    # ... 现有代码 ...
    
    # 优化 SQLite 性能
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.execute("PRAGMA temp_store=MEMORY")
```

### 3. 文件系统优化

```bash
# 如果使用 SSD，启用 TRIM
sudo systemctl enable fstrim.timer

# 调整文件系统挂载选项
# 在 /etc/fstab 中添加 noatime 选项
/dev/sda1 /var/www/gracedisk ext4 defaults,noatime 0 2
```

### 4. 监控和日志

#### 日志配置

```python
# 在 app.py 中添加日志配置
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler(
        'gracedisk.log', 
        maxBytes=10240000, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

#### 系统监控

安装系统监控依赖（Dashboard 功能需要）：

```bash
uv pip install psutil
```

## 安全配置

### 1. 防火墙设置

```bash
# Ubuntu/Debian
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 文件权限安全

```bash
# 确保敏感文件权限正确
chmod 600 config.yaml
chmod 600 gracedisk.db
chmod 700 userfiles/
```

### 3. 定期备份

创建备份脚本：

```bash
nano backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backup/gracedisk"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
cp gracedisk.db $BACKUP_DIR/gracedisk_$DATE.db

# 备份配置文件
cp config.yaml $BACKUP_DIR/config_$DATE.yaml

# 备份用户文件（如果不太大的话）
tar -czf $BACKUP_DIR/userfiles_$DATE.tar.gz userfiles/

# 保留最近 30 天的备份
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.yaml" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "备份完成: $DATE"
```

设置定时备份：

```bash
chmod +x backup.sh
crontab -e
# 添加每天凌晨 2 点备份
0 2 * * * /var/www/gracedisk/backup.sh
```

## 维护和更新

### 1. 应用更新

```bash
cd /var/www/gracedisk

# 停止服务
sudo systemctl stop gracedisk

# 备份当前版本
cp -r . ../gracedisk_backup_$(date +%Y%m%d)

# 拉取更新
git pull origin main

# 更新依赖
source .venv/bin/activate
uv pip install -r requirements.txt

# 重启服务
sudo systemctl start gracedisk
```

### 2. 日志清理

```bash
# 清理应用日志
find . -name "*.log" -size +100M -delete

# 清理系统日志
sudo journalctl --vacuum-time=30d
```

### 3. 性能监控

```bash
# 查看服务状态
sudo systemctl status gracedisk

# 查看资源使用
htop
df -h
free -h

# 查看 Nginx 访问日志
sudo tail -f /var/log/nginx/access.log
```

## 故障排除

### 常见问题

1. **服务无法启动**
   ```bash
   # 查看详细错误信息
   sudo journalctl -u gracedisk -f
   
   # 检查端口占用
   sudo netstat -tlnp | grep :5000
   ```

2. **文件上传失败**
   ```bash
   # 检查磁盘空间
   df -h
   
   # 检查目录权限
   ls -la /var/www/gracedisk/
   ```

3. **数据库错误**
   ```bash
   # 检查数据库文件权限
   ls -la gracedisk.db
   
   # 测试数据库连接
   sqlite3 gracedisk.db ".tables"
   ```

4. **访问速度慢**
   - 检查网络带宽
   - 优化 Nginx 配置
   - 考虑启用文件压缩

### 获取帮助

如果你遇到其他问题：

1. 查看 [项目 Issues](https://github.com/your-username/gracedisk/issues)
2. 提交新的 Issue 并附上：
   - 操作系统版本
   - Python 版本
   - 错误日志
   - 具体的操作步骤

## 升级指南

### 从旧版本升级

如果你从旧版本升级，请注意：

1. **备份数据**：升级前务必备份数据库和配置文件
2. **检查配置**：新版本可能有配置格式变更
3. **数据库迁移**：某些版本可能需要数据库结构更新

### 版本兼容性

- v1.x → v2.x：需要手动迁移配置文件格式
- v2.x 内部版本：通常可以直接升级

---

感谢你选择 GraceDisk！这个项目是我个人开发的开源文件管理系统，希望它能为你提供良好的文件管理体验。

如果你在部署过程中遇到任何问题，或者有功能建议，请随时通过 GitHub 联系我。你的反馈对项目的改进非常重要！

项目地址：https://github.com/your-username/gracedisk
