# GraceDisk 开发者指南

欢迎来到 GraceDisk 项目！这是一个用 Python Flask 构建的现代化网络文件管理系统。作为一个个人开发的开源项目，我真诚地欢迎社区的贡献和改进建议。

## 项目概览

GraceDisk 是一个基于 Web 的文件管理系统，提供多用户支持、文件分享、权限管理等功能。项目采用 MIT 协议开源，鼓励学习、使用和贡献。

### 技术栈

- **后端**: Python 3.11+ + Flask 2.x
- **数据库**: SQLite 3
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **样式**: 毛玻璃效果 (Glassmorphism) 设计
- **系统监控**: psutil (可选)

## 开发环境设置

### 1. 克隆项目

```bash
git clone https://github.com/your-username/gracedisk.git
cd gracedisk
```

### 2. 环境配置

推荐使用 uv (现代的 Python 包管理器):

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

uv pip install -r requirements.txt
```

或使用传统的 pip:

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# 或
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

### 3. 配置文件

复制并修改配置文件：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml` 中的关键配置：

```yaml
admin:
  username: admin
  password: your_strong_password_here

storage_path: "/path/to/your/files"
users_db_path: "users.db"

allow_visiter: true
visitor_storage_path: "/path/to/visitor/files"
```

### 4. 运行开发服务器

```bash
python app.py
```

访问 http://localhost:5000

## 项目结构

```
gracedisk/
├── app.py                 # 主应用文件
├── config.yaml           # 配置文件
├── requirements.txt       # Python 依赖
├── users.db              # SQLite 数据库
├── static/               # 静态资源
│   ├── css/
│   │   └── style.css     # 主样式文件
│   ├── icons/            # 文件类型图标
│   └── images/           # 图片资源
├── templates/            # Jinja2 模板
│   ├── base.html         # 基础模板
│   ├── index.html        # 文件管理页面
│   ├── login.html        # 登录页面
│   ├── dashboard.html    # 管理员仪表盘
│   ├── video_preview.html # 视频预览页面
│   └── ...               # 其他页面模板
└── userfiles/            # 用户文件存储
```

## 核心架构

### 1. 数据库设计

项目使用 SQLite 数据库，包含以下主要表：

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    quota_gb INTEGER DEFAULT 10,
    can_login BOOLEAN DEFAULT 1,
    must_change_password BOOLEAN DEFAULT 0
);

-- 分享链接表
CREATE TABLE shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    password_hash TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 文件操作记录表
CREATE TABLE file_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    operation_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 登录日志表
CREATE TABLE login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    login_type TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 用户角色系统

- **管理员**: 拥有所有权限，可以管理用户、查看系统统计
- **普通用户**: 可以管理自己的文件、创建分享链接（最长90天）
- **访客**: 只读权限，只能浏览和下载指定目录的文件

### 3. 权限装饰器

```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('root'))
        return f(*args, **kwargs)
    return decorated_function

def password_change_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('must_change_password'):
            return redirect(url_for('change_password'))
        return f(*args, **kwargs)
    return decorated_function
```

## 主要功能模块

### 1. 文件管理 (`_render_file_list`)

```python
def _render_file_list(subpath=""):
    """渲染文件列表的核心逻辑"""
    # 根据用户类型确定基础路径
    if session.get('is_admin'):
        base_path = config.get('storage_path')
    elif session.get('is_visitor'):
        base_path = config.get('visitor_storage_path')
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    # 安全路径处理
    # 获取文件列表
    # 计算存储统计
    # 渲染模板
```

### 2. 文件上传 (`upload_file`)

- 多文件上传支持
- 用户配额检查
- 安全路径验证
- 操作日志记录

### 3. 分享系统 (`create_share`, `share/<token>`)

- UUID token 生成
- 密码保护支持
- 过期时间设置
- 权限级别控制

### 4. 系统监控 (`dashboard`)

- 使用 psutil 获取系统资源
- 数据库统计查询
- 实时状态显示

## 前端开发

### 1. 毛玻璃效果实现

```css
.glassmorphism {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
}
```

### 2. JavaScript 交互

- 使用 Fetch API 进行 AJAX 请求
- 模块化的事件处理
- 响应式设计支持

### 3. 图标系统

使用 SVG 图标，支持的文件类型：
- 文档: `.pdf`, `.doc`, `.docx`, `.txt`
- 图片: `.jpg`, `.png`, `.gif`, `.webp`
- 视频: `.mp4`, `.webm`, `.mov`
- 音频: `.mp3`, `.wav`, `.ogg`
- 压缩: `.zip`, `.rar`, `.7z`

## 贡献指南

### 1. 代码风格

- Python: 遵循 PEP 8 标准
- HTML: 语义化标签，适当缩进
- CSS: BEM 命名规范优先
- JavaScript: ES6+ 语法，函数式编程

### 2. 提交规范

```bash
# 功能添加
git commit -m "feat: 添加视频预览功能"

# Bug 修复
git commit -m "fix: 修复文件上传权限检查"

# 文档更新
git commit -m "docs: 更新开发者指南"

# 样式调整
git commit -m "style: 优化毛玻璃效果透明度"
```

### 3. Pull Request 流程

1. Fork 项目到你的 GitHub 账号
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交你的修改: `git commit -m 'feat: 添加amazing功能'`
4. 推送到分支: `git push origin feature/amazing-feature`
5. 打开 Pull Request

### 4. 测试

目前项目还没有完整的测试覆盖，这是一个很好的贡献机会：

```bash
# 计划添加的测试
tests/
├── test_auth.py          # 认证测试
├── test_file_ops.py      # 文件操作测试
├── test_shares.py        # 分享功能测试
└── test_api.py           # API 接口测试
```

## 扩展开发

### 1. 添加新的文件类型支持

1. 在 `get_file_type()` 函数中添加扩展名映射
2. 在 `static/icons/` 中添加相应图标
3. 如需特殊预览，修改 `preview_file()` 路由

### 2. 添加新的用户权限级别

1. 修改 `users` 表结构
2. 更新权限装饰器
3. 调整前端权限判断逻辑

### 3. 集成外部存储

项目目前使用本地文件系统，可以扩展支持：
- Amazon S3
- 阿里云 OSS
- 腾讯云 COS
- 自建 MinIO

### 4. 添加更多预览类型

当前支持图片和视频预览，可以扩展：
- PDF 文档预览
- Office 文档预览
- 代码语法高亮
- 音频播放器

## 常见问题

### Q: 如何添加新的配置项？

A: 在 `config.yaml` 中添加配置，然后在 `load_config()` 函数后通过 `app.config['GRACEDISK_CONFIG']` 访问。

### Q: 如何修改数据库结构？

A: 修改 `init_db()` 函数中的表创建语句，注意做好向后兼容处理。

### Q: 如何自定义主题？

A: 修改 `static/css/style.css` 中的 CSS 变量和样式类。

### Q: 如何优化性能？

A: 
- 对大文件夹启用分页
- 添加缓存机制
- 优化数据库查询
- 使用 CDN 加速静态资源

## 路线图

以下是项目的一些发展方向，欢迎贡献：

- [ ] 完整的单元测试覆盖
- [ ] Docker 容器化部署
- [ ] 多语言支持 (i18n)
- [ ] 文件版本控制
- [ ] 在线协作编辑
- [ ] 移动端适配优化
- [ ] 插件系统
- [ ] API 文档和 SDK

## 社区

- GitHub Issues: 报告 Bug 和功能请求
- GitHub Discussions: 讨论想法和获取帮助
- Pull Requests: 贡献代码

## 许可证

本项目采用 MIT 许可证。这意味着你可以：

- ✅ 商业使用
- ✅ 修改源码
- ✅ 分发
- ✅ 私人使用

但需要保留版权声明和许可证声明。

---

感谢你对 GraceDisk 项目的关注！作为一个个人维护的开源项目，你的每一个贡献都非常宝贵。无论是代码、文档、测试还是问题反馈，都能帮助这个项目变得更好。

如果你有任何问题或建议，请随时通过 GitHub Issues 联系我。让我们一起构建一个更好的文件管理系统！
