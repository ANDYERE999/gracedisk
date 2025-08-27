from flask import Flask, session, render_template, request, redirect, url_for, flash, send_file, Response, stream_with_context, jsonify
import yaml
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import re
import uuid

app = Flask(__name__)
# 设置一个密钥，用于保护 session
# 在生产环境中，这应该是一个更复杂、更随机的字符串，并且不应该硬编码在代码里
app.secret_key = 'your_very_secret_key_change_it_later'

# 注册一个辅助函数，使其可以在所有模板中使用
@app.context_processor
def utility_processor():
    def format_file_size(size):
        if isinstance(size, str):
            return size
        if size < 1024: return f"{size} B"
        elif size < 1024**2: return f"{size/1024:.2f} KB"
        elif size < 1024**3: return f"{size/1024**2:.2f} MB"
        else: return f"{size/1024**3:.2f} GB"
    
    def has_background_image():
        background_path = os.path.join('static', 'images', 'background.png')
        return os.path.exists(background_path)
    
    return dict(format_file_size=format_file_size, has_background_image=has_background_image)

# 图标匹配辅助函数
@app.context_processor
def inject_icon_map():
    ICON_MAP = {
        # 图片
        'jpg': 'image.svg', 'jpeg': 'image.svg', 'png': 'image.svg', 'gif': 'image.svg', 'webp': 'image.svg',
        # 视频
        'mp4': 'video.svg', 'mov': 'video.svg', 'avi': 'video.svg', 'mkv': 'video.svg', 'webm': 'video.svg',
        # 音频
        'mp3': 'audio.svg', 'wav': 'audio.svg', 'ogg': 'audio.svg',
        # 文档
        'pdf': 'pdf.svg',
        'doc': 'document.svg', 'docx': 'document.svg', 'txt': 'document.svg',
        # 压缩包
        'zip': 'archive.svg', 'rar': 'archive.svg', '7z': 'archive.svg',
    }
    DEFAULT_ICON = 'file.svg'
    FOLDER_ICON = 'folder.svg'

    def get_icon(filename, is_dir):
        if is_dir:
            return FOLDER_ICON
        ext = filename.split('.')[-1].lower()
        return ICON_MAP.get(ext, DEFAULT_ICON)
        
    PREVIEWABLE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}

    def get_file_type(filename):
        ext = filename.split('.')[-1].lower()
        if ext in PREVIEWABLE_EXTENSIONS:
            return 'image'
        if ext in VIDEO_EXTENSIONS:
            return 'video'
        return 'other'

    def is_previewable(filename):
        ext = filename.split('.')[-1].lower()
        return ext in PREVIEWABLE_EXTENSIONS

    return dict(get_icon=get_icon, get_file_type=get_file_type, is_previewable=is_previewable)

# 加载配置文件
def load_config():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 递归计算文件夹大小的辅助函数
def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # 跳过无效的符号链接
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def log_login(user_id, username, login_type, ip_address, user_agent):
    """记录用户登录日志"""
    try:
        config = app.config['GRACEDISK_CONFIG']
        db_path = config.get('users_db_path', 'users.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO login_logs (user_id, username, login_type, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, login_type, ip_address, user_agent))
        conn.commit()
        conn.close()
    except Exception:
        pass  # 登录记录失败不应影响正常登录

def init_db():
    config = load_config()
    db_path = config.get('users_db_path', 'users.db')
    
    # Connect to the DB. It will be created if it doesn't exist.
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check for existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    # Create users table if it doesn't exist
    if 'users' not in tables:
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            quota_gb INTEGER DEFAULT 5,
            can_login BOOLEAN NOT NULL DEFAULT 1,
            must_change_password BOOLEAN NOT NULL DEFAULT 0
        )
        ''')
        
        # Insert admin user only when creating the table for the first time
        admin_user = config.get('admin', {})
        admin_username = admin_user.get('username', 'admin')
        admin_password = admin_user.get('password', 'your_strong_password_here')
        hashed_password = generate_password_hash(admin_password)
        cursor.execute(
            "INSERT INTO users (username, password, is_admin, can_login, must_change_password) VALUES (?, ?, ?, ?, ?)",
            (admin_username, hashed_password, True, True, True)
        )
        print(f"Table 'users' created and admin user '{admin_username}' inserted.")
    else:
        # Upgrade existing users table if needed
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'can_login' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN can_login BOOLEAN NOT NULL DEFAULT 1')
            print("Added 'can_login' column to users table.")

    # Create shares table if it doesn't exist
    if 'shares' not in tables:
        cursor.execute('''
        CREATE TABLE shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            password_hash TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        print("Table 'shares' created.")
    else:
        # Upgrade existing shares table
        cursor.execute("PRAGMA table_info(shares)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'password_hash' not in columns:
            cursor.execute('ALTER TABLE shares ADD COLUMN password_hash TEXT')
        if 'expires_at' not in columns:
            cursor.execute('ALTER TABLE shares ADD COLUMN expires_at TIMESTAMP')

            # Create file_operations table for tracking uploads/downloads
        if 'file_operations' not in tables:
            cursor.execute('''
            CREATE TABLE file_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                operation_type TEXT NOT NULL, -- 'upload' or 'download'
                file_path TEXT NOT NULL,
                file_size INTEGER,
                status TEXT NOT NULL DEFAULT 'completed', -- 'in_progress', 'completed', 'failed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
            print("Table 'file_operations' created.")
        
        # Create login_logs table for tracking user logins
        if 'login_logs' not in tables:
            cursor.execute('''
            CREATE TABLE login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                login_type TEXT NOT NULL, -- 'user', 'admin', 'visitor'
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            print("Table 'login_logs' created.")

    conn.commit()
    conn.close()

app.config['GRACEDISK_CONFIG'] = load_config()

# 在应用启动前执行数据库初始化
init_db()


# 仅限管理员访问的装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            # 或者可以返回一个 403 Forbidden 错误页面
            return redirect(url_for('root'))
        return f(*args, **kwargs)
    return decorated_function

def password_change_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('must_change_password'):
            # Allow access to logout
            if request.endpoint != 'logout':
                 return redirect(url_for('change_password'))
        return f(*args, **kwargs)
    return decorated_function

def _render_file_list(subpath=""):
    """Shared logic for rendering the file list for a given subpath."""
    config = app.config['GRACEDISK_CONFIG']
    storage_info = {}

    if session.get('is_admin'):
        base_path = config.get('storage_path')
        # Bug Fix: Handle Windows drive root paths like "D:"
        if os.name == 'nt' and len(base_path) == 2 and base_path[1] == ':':
            base_path += os.sep
            
        total, used, free = shutil.disk_usage(base_path)
        storage_info = {'is_disk': True, 'total': total, 'used': used}
    elif session.get('is_visitor'):
        # 访客用户
        base_path = config.get('visitor_storage_path', config.get('storage_path'))
        # Bug Fix: Handle Windows drive root paths like "D:"
        if os.name == 'nt' and len(base_path) == 2 and base_path[1] == ':':
            base_path += os.sep
            
        total, used, free = shutil.disk_usage(base_path)
        storage_info = {'is_disk': True, 'total': total, 'used': used}
    else:
        # 普通用户
        base_path = os.path.join('userfiles', session['username'])
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        # 获取用户的配额信息
        db_path = config.get('users_db_path', 'users.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT quota_gb FROM users WHERE id = ?", (session['user_id'],))
        user_db_info = cursor.fetchone()
        conn.close()

        quota_bytes = user_db_info['quota_gb'] * (1024**3)
        used_bytes = get_folder_size(base_path)
        
        storage_info = {
            'is_disk': False, # 标记为用户配额信息
            'total': quota_bytes,
            'used': used_bytes,
            'percent': round((used_bytes / quota_bytes) * 100, 2) if quota_bytes > 0 else 0
        }

    # --- 路径处理和安全校验 ---
    # 1. 将 subpath 规范化，防止 ../../ 等形式
    safe_subpath = os.path.normpath(subpath).lstrip('.\\/')
    # 2. 构建当前要访问的完整路径
    current_path = os.path.join(base_path, safe_subpath)
    # 3. 再次校验，确保最终路径仍在用户的根目录之内
    if not os.path.abspath(current_path).startswith(os.path.abspath(base_path)):
        flash("禁止访问！", 'error')
        return redirect(url_for('root'))

    # 获取当前要浏览的路径（后续将支持子目录）
    # current_path = base_path
    
    # 检查路径是否存在
    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        flash("路径不存在！", 'error')
        return redirect(url_for('root'))

    items = []
    for name in os.listdir(current_path):
        item_path = os.path.join(current_path, name)
        try:
            stat = os.stat(item_path)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': name,
                'is_dir': is_dir,
                'size': stat.st_size if not is_dir else '-',
                'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        except OSError:
            # 忽略无法访问的文件/文件夹
            continue
    
    # 按类型（文件夹优先）和名称排序
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    # 生成面包屑导航
    breadcrumbs = [{"name": "主目录", "path": ""}]
    if subpath:
        parts = subpath.split('/')
        for i, part in enumerate(parts):
            breadcrumbs.append({
                "name": part,
                "path": "/".join(parts[:i+1])
            })

    return render_template('index.html', items=items, storage_info=storage_info, breadcrumbs=breadcrumbs, current_subpath=subpath)

@app.route('/')
def root():
    """Route for the root directory."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 检查是否需要强制修改密码
    if session.get('must_change_password'):
        return redirect(url_for('change_password'))
    
    return _render_file_list()

@app.route('/browse/')
@app.route('/browse/<path:subpath>')
def browse(subpath=""):
    """Route for browsing subdirectories."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 检查是否需要强制修改密码
    if session.get('must_change_password'):
        return redirect(url_for('change_password'))
    
    return _render_file_list(subpath)


@app.route('/preview/<path:path>')
def preview_file(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    parent_path = os.path.dirname(path)
    filename = os.path.basename(path)

    # Re-implementing logic here for simplicity because context processors are not available in routes
    ext = filename.split('.')[-1].lower()
    if ext in {'jpg', 'jpeg', 'png', 'gif', 'webp'}:
        file_type = 'image'
    elif ext in {'mp4', 'webm', 'mov'}:
        file_type = 'video'
    else:
        file_type = 'other'

    if file_type == 'other':
        return "This file type cannot be previewed.", 400
    
    # 对于视频文件，使用专门的视频预览页面
    if file_type == 'video':
        return render_template('video_preview.html', 
                             file_path=path, 
                             filename=filename, 
                             parent_path=parent_path, 
                             file_type=file_type)
    
    return render_template('preview.html', file_path=path, filename=filename, parent_path=parent_path, file_type=file_type)

@app.route('/filedata/<path:path>')
def get_file_data(path):
    if 'user_id' not in session:
        return "Forbidden", 403

    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    elif session.get('is_visitor'):
        base_path = app.config['GRACEDISK_CONFIG'].get('visitor_storage_path', app.config['GRACEDISK_CONFIG'].get('storage_path'))
    else:
        base_path = os.path.join('userfiles', session['username'])

    safe_path = os.path.normpath(path).lstrip('.\\/')
    file_path = os.path.join(base_path, safe_path)

    if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
        return "Forbidden", 403
    
    if not os.path.exists(file_path):
        return "File not found", 404

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    
    start = 0
    length = file_size

    if range_header:
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = range_match.group(2)
            
            if end:
                end = int(end)
                length = end - start + 1
            else:
                length = file_size - start
            
            headers = {
                'Content-Range': f'bytes {start}-{start + length - 1}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(length),
                'Content-Type': 'video/mp4' # Or get mimetype dynamically
            }
    
    def generate():
        with open(file_path, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(4096, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data
                        remaining -= len(data)

        return Response(stream_with_context(generate()), status=206, headers=headers)

    # Fallback for non-range requests
    def generate_full():
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                yield data

    headers = {
        'Content-Length': str(file_size),
        'Content-Type': 'video/mp4' # Or get mimetype dynamically
    }
    return Response(stream_with_context(generate_full()), headers=headers)

@app.route('/download/<path:filename>')
def download_file(filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 根据用户身份确定文件基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    elif session.get('is_visitor'):
        base_path = app.config['GRACEDISK_CONFIG'].get('visitor_storage_path', app.config['GRACEDISK_CONFIG'].get('storage_path'))
    else:
        base_path = os.path.join('userfiles', session['username'])

    # 构建安全的文件路径
    safe_path = os.path.normpath(filename).lstrip('.\\/')
    file_path = os.path.join(base_path, safe_path)

    # 再次检查，确保最终路径仍然在我们期望的目录内，防止安全漏洞
    if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
        return "Forbidden", 403

    if not os.path.exists(file_path) or os.path.isdir(file_path):
        return "File not found", 404

    return send_file(file_path, as_attachment=True)

@app.route('/delete/<path:path>')
def delete_item(path):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 访客不能删除
    if session.get('is_visitor'):
        flash('访客无法删除文件', 'error')
        return redirect(request.referrer or url_for('root'))

    # 根据用户身份确定基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    elif session.get('is_visitor'):
        base_path = app.config['GRACEDISK_CONFIG'].get('visitor_storage_path', app.config['GRACEDISK_CONFIG'].get('storage_path'))
    else:
        base_path = os.path.join('userfiles', session['username'])

    # 构建并验证路径
    safe_path = os.path.normpath(path).lstrip('.\\/')
    item_path = os.path.join(base_path, safe_path)
    
    if not os.path.abspath(item_path).startswith(os.path.abspath(base_path)):
        flash('禁止访问！', 'error')
        return redirect(request.referrer or url_for('root'))
    
    if not os.path.exists(item_path):
        flash('文件或文件夹不存在', 'error')
        return redirect(request.referrer or url_for('root'))

    try:
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            flash(f"文件夹 '{os.path.basename(item_path)}' 已被删除", 'success')
        else:
            os.remove(item_path)
            flash(f"文件 '{os.path.basename(item_path)}' 已被删除", 'success')
    except OSError as e:
        flash(f"删除失败: {e}", 'error')

    parent_path = os.path.dirname(path)
    if parent_path:
        return redirect(url_for('browse', subpath=parent_path))
    return redirect(url_for('root'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 访客不能上传
    if session.get('is_visitor'):
        flash('访客无法上传文件', 'error')
        return redirect(request.referrer or url_for('root'))
    
    if 'file' not in request.files:
        flash('没有文件部分', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('未选择文件', 'error')
        return redirect(request.referrer or url_for('root'))

    # 新增：从表单获取当前子路径
    subpath = request.form.get('subpath', '')

    if file:
        filename = secure_filename(file.filename)
        
        # 获取文件大小（放在最开始）
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0) # important: reset cursor to beginning
        
        # 确定基础保存路径
        if session.get('is_admin'):
            base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
        else:
            base_path = os.path.join('userfiles', session['username'])
            
            # 检查用户配额
            config = app.config['GRACEDISK_CONFIG']
            db_path = config.get('users_db_path', 'users.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT quota_gb FROM users WHERE id = ?", (session['user_id'],))
            user_db_info = cursor.fetchone()
            conn.close()

            quota_bytes = user_db_info['quota_gb'] * (1024**3)
            used_bytes = get_folder_size(base_path)

            if used_bytes + file_size > quota_bytes:
                # 这里不能直接调用模板里的 format_file_size, 我们需要一个独立的Python版本
                def format_size_for_flash(size_bytes):
                    if size_bytes < 1024: return f"{size_bytes} B"
                    if size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
                    if size_bytes < 1024**3: return f"{size_bytes/1024**2:.2f} MB"
                    return f"{size_bytes/1024**3:.2f} GB"
                
                flash(f"空间不足。剩余空间: {format_size_for_flash(quota_bytes - used_bytes)}", 'error')
                return redirect(request.referrer or url_for('root'))

        # --- 路径处理和安全校验 ---
        safe_subpath = os.path.normpath(subpath).lstrip('.\\/')
        current_path = os.path.join(base_path, safe_subpath)
        if not os.path.abspath(current_path).startswith(os.path.abspath(base_path)):
            flash('无效的上传路径！', 'error')
            return redirect(url_for('root'))

        # 处理文件名冲突
        save_path = os.path.join(current_path, filename)
        if os.path.exists(save_path):
            # 简单的处理方式：添加后缀 (后续可以做得更智能)
            name, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(save_path):
                save_path = os.path.join(current_path, f"{name}({i}){ext}")
                i += 1
        
        file.save(save_path)
        
        # 记录上传操作
        db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO file_operations (user_id, operation_type, file_path, file_size, status) 
            VALUES (?, ?, ?, ?, ?)
        """, (session['user_id'], 'upload', os.path.basename(save_path), file_size, 'completed'))
        conn.commit()
        conn.close()
        
        flash(f"文件 '{os.path.basename(save_path)}' 上传成功", 'success')

    # 返回到上传时所在的目录
    if subpath:
        return redirect(url_for('browse', subpath=subpath))
    return redirect(url_for('root'))


@app.route('/manage_users')
@admin_required
def manage_users():
    config = app.config['GRACEDISK_CONFIG']
    db_path = config.get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查询所有非管理员用户
    cursor.execute("SELECT id, username, quota_gb FROM users WHERE is_admin = 0")
    users = cursor.fetchall()
    conn.close()
    
    return render_template('manage_users.html', users=users)


@app.route('/delete_user/<int:user_id>', methods=['GET']) # 通常删除操作会用POST或DELETE，但为简化我们用GET
@admin_required
def delete_user(user_id):
    # 安全起见，不允许删除ID为1的用户（通常是初始管理员）
    if user_id == 1:
        # 可以通过flash消息给用户更明确的提示
        return redirect(url_for('manage_users'))

    config = app.config['GRACEDISK_CONFIG']
    db_path = config.get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 删除前先获取用户名，以便删除文件夹
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        # 1. 从数据库中删除用户
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

        # 2. 删除用户对应的文件夹
        user_folder = os.path.join('userfiles', user['username'])
        if os.path.exists(user_folder):
            try:
                shutil.rmtree(user_folder)
            except OSError as e:
                # TODO: 记录删除文件夹失败的错误
                print(f"Error deleting folder {user_folder}: {e}")
    
    conn.close()
    return redirect(url_for('manage_users'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    config = app.config['GRACEDISK_CONFIG']
    db_path = config.get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    error = None
    if request.method == 'POST':
        # 处理表单提交
        new_password = request.form.get('password')
        new_quota_gb = request.form.get('quota_gb', type=int)

        if new_password:
            # 如果输入了新密码，则更新密码
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = ?, quota_gb = ? WHERE id = ?", 
                           (hashed_password, new_quota_gb, user_id))
        else:
            # 否则，只更新空间配额
            cursor.execute("UPDATE users SET quota_gb = ? WHERE id = ?", 
                           (new_quota_gb, user_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('manage_users'))

    # 处理首次加载页面 (GET请求)
    cursor.execute("SELECT id, username, quota_gb FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        # 如果找不到用户，重定向回管理页面
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user=user, error=error)


@app.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        quota_gb = request.form.get('quota_gb', 5, type=int)

        if not username or not password:
            error = '用户名和密码不能为空'
        else:
            config = app.config['GRACEDISK_CONFIG']
            db_path = config.get('users_db_path', 'users.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                error = f"用户名 '{username}' 已被占用"
            else:
                # 插入新用户
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (username, password, quota_gb, is_admin, can_login, must_change_password) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, hashed_password, quota_gb, False, True, False)
                )
                conn.commit()

                # 在 ./userfiles 文件夹下创建对应的用户目录
                try:
                    os.makedirs(os.path.join('userfiles', username), exist_ok=True)
                except OSError as e:
                    # TODO: 更好的错误处理，比如从数据库中回滚用户创建操作
                    error = f"创建用户文件夹失败: {e}"
                
                if not error:
                    return redirect(url_for('manage_users'))

            conn.close()

    return render_template('add_user.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    config = app.config['GRACEDISK_CONFIG']
    allow_visitor = config.get('allow_visiter', False)  # 注意配置文件中的拼写
    error = None
    
    if request.method == 'POST':
        # 检查是否是访客登录
        if request.form.get('visitor') == 'true':
            if allow_visitor:
                session['username'] = 'visitor'
                session['is_admin'] = False
                session['is_visitor'] = True
                session['user_id'] = -1  # 访客 ID 为 -1
                session['must_change_password'] = False
                
                # 记录访客登录
                log_login(-1, 'visitor', 'visitor', request.remote_addr, request.headers.get('User-Agent', ''))
                
                return redirect(url_for('root'))
            else:
                error = '访客登录已禁用'
                return render_template('login.html', error=error, allow_visitor=allow_visitor)
        
        username = request.form['username']
        password = request.form['password']
        
        db_path = config.get('users_db_path', 'users.db')
        conn = sqlite3.connect(db_path)
        # 让查询结果可以像字典一样通过列名访问
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            # 登录成功，设置 session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['is_visitor'] = False
            session['must_change_password'] = user['must_change_password'] # Add this to session
            
            # 记录登录日志
            login_type = 'admin' if user['is_admin'] else 'user'
            log_login(user['id'], user['username'], login_type, request.remote_addr, request.headers.get('User-Agent', ''))
            
            if user['must_change_password']:
                return redirect(url_for('change_password'))
            
            return redirect(url_for('root'))
        else:
            error = '用户名或密码无效'
            
    return render_template('login.html', error=error, allow_visitor=allow_visitor)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('must_change_password'):
        return redirect(url_for('root'))

    error = None
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            error = "两次输入的密码不匹配"
        elif len(new_password) < 8:
            error = "密码长度至少需要8位"
        else:
            hashed_password = generate_password_hash(new_password)
            db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = ?, must_change_password = ? WHERE id = ?",
                           (hashed_password, False, session['user_id']))
            conn.commit()
            conn.close()

            session['must_change_password'] = False
            flash("密码已成功更新！", "success")
            return redirect(url_for('root'))

    return render_template('change_password.html', error=error)

@app.route('/create_folder', methods=['POST'])
@password_change_required
def create_folder():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if session.get('is_visitor'):
        return jsonify({'error': '访客无法创建文件夹'}), 403
    
    data = request.get_json()
    folder_name = data.get('name', '').strip()
    subpath = data.get('subpath', '')
    
    if not folder_name:
        return jsonify({'error': '文件夹名称不能为空'}), 400
    
    # 安全检查文件夹名称
    if any(char in folder_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        return jsonify({'error': '文件夹名称包含非法字符'}), 400
    
    # 确定基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    # 构建安全路径
    safe_subpath = os.path.normpath(subpath).lstrip('.\\/')
    current_path = os.path.join(base_path, safe_subpath)
    
    if not os.path.abspath(current_path).startswith(os.path.abspath(base_path)):
        return jsonify({'error': '无效路径'}), 400
    
    folder_path = os.path.join(current_path, folder_name)
    
    if os.path.exists(folder_path):
        return jsonify({'error': '文件夹已存在'}), 400
    
    try:
        os.makedirs(folder_path)
        return jsonify({'success': True})
    except OSError as e:
        return jsonify({'error': f'创建失败: {e}'}), 500

@app.route('/rename', methods=['POST'])
@password_change_required
def rename_item():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if session.get('is_visitor'):
        return jsonify({'error': '访客无法重命名文件'}), 403
    
    data = request.get_json()
    old_path = data.get('old_path', '')
    new_name = data.get('new_name', '').strip()
    
    if not old_path or not new_name:
        return jsonify({'error': '参数不完整'}), 400
    
    # 安全检查新名称
    if any(char in new_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        return jsonify({'error': '名称包含非法字符'}), 400
    
    # 确定基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    # 构建安全路径
    safe_old_path = os.path.normpath(old_path).lstrip('.\\/')
    old_full_path = os.path.join(base_path, safe_old_path)
    
    if not os.path.abspath(old_full_path).startswith(os.path.abspath(base_path)):
        return jsonify({'error': '无效路径'}), 400
    
    if not os.path.exists(old_full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 构建新路径
    new_full_path = os.path.join(os.path.dirname(old_full_path), new_name)
    
    if os.path.exists(new_full_path):
        return jsonify({'error': '目标名称已存在'}), 400
    
    try:
        os.rename(old_full_path, new_full_path)
        return jsonify({'success': True})
    except OSError as e:
        return jsonify({'error': f'重命名失败: {e}'}), 500

@app.route('/batch_delete', methods=['POST'])
@password_change_required
def batch_delete():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if session.get('is_visitor'):
        return jsonify({'error': '访客无法删除文件'}), 403
    
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': '没有选择要删除的项目'}), 400
    
    # 确定基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    deleted_count = 0
    errors = []
    
    for item_path in items:
        try:
            safe_path = os.path.normpath(item_path).lstrip('.\\/')
            full_path = os.path.join(base_path, safe_path)
            
            if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
                errors.append(f'{item_path}: 无效路径')
                continue
            
            if not os.path.exists(full_path):
                errors.append(f'{item_path}: 文件不存在')
                continue
            
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            
            deleted_count += 1
        except OSError as e:
            errors.append(f'{item_path}: {e}')
    
    if errors:
        return jsonify({'success': False, 'errors': errors, 'deleted': deleted_count}), 207
    
    return jsonify({'success': True, 'deleted': deleted_count})

@app.route('/create_share', methods=['POST'])
@password_change_required
def create_share():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if session.get('is_visitor'):
        return jsonify({'error': '访客无法创建分享'}), 403
    
    data = request.get_json()
    path = data.get('path', '')
    password = data.get('password', '')
    duration = data.get('duration', 1)
    
    if not path:
        return jsonify({'error': '文件路径不能为空'}), 400
    
    # 验证文件是否存在
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    safe_path = os.path.normpath(path).lstrip('.\\/')
    full_path = os.path.join(base_path, safe_path)
    
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)) or not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.isdir(full_path):
        return jsonify({'error': '无法分享文件夹'}), 400
    
    # 检查持续时间限制
    if not session.get('is_admin') and duration > 90:
        return jsonify({'error': '普通用户分享时间不能超过90天'}), 400
    
    # 生成分享token
    token = str(uuid.uuid4())
    
    # 计算过期时间
    expires_at = None
    if duration > 0:
        expires_at = datetime.now() + timedelta(days=duration)
    
    # 处理密码
    password_hash = None
    if password:
        password_hash = generate_password_hash(password)
    
    # 保存到数据库
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shares (token, file_path, user_id, password_hash, expires_at) 
        VALUES (?, ?, ?, ?, ?)
    """, (token, path, session['user_id'], password_hash, expires_at))
    conn.commit()
    conn.close()
    
    share_link = url_for('shared_file', token=token, _external=True)
    return jsonify({'success': True, 'link': share_link})

@app.route('/share/<token>')
def shared_file(token):
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, u.username, u.is_admin 
        FROM shares s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.token = ?
    """, (token,))
    share_data = cursor.fetchone()
    conn.close()

    if not share_data:
        return render_template('share_error.html', 
                             error_type='invalid', 
                             message='分享链接无效或已被删除')
    
    # 检查是否过期
    if share_data['expires_at']:
        expires_at = datetime.strptime(share_data['expires_at'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expires_at:
            return render_template('share_error.html',
                                 error_type='expired', 
                                 message='分享链接已过期')
    
    # 检查密码保护
    if share_data['password_hash']:
        password = request.args.get('password', '')
        if not password or not check_password_hash(share_data['password_hash'], password):
            return render_template('share_password.html', token=token)
    
    # 获取文件
    if share_data['is_admin']:
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    else:
        base_path = os.path.join('userfiles', share_data['username'])
        
    file_path = os.path.join(base_path, os.path.normpath(share_data['file_path']).lstrip('.\\/'))
    
    if not os.path.exists(file_path):
        return render_template('share_error.html',
                             error_type='not_found', 
                             message='文件已不存在')
        
    return send_file(file_path, as_attachment=True)

@app.route('/manage_shares')
@password_change_required
def manage_shares():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if session.get('is_admin'):
        # 管理员可以看到所有分享
        cursor.execute("""
            SELECT s.*, u.username 
            FROM shares s 
            JOIN users u ON s.user_id = u.id 
            ORDER BY s.created_at DESC
        """)
    else:
    # 普通用户只能看到自己的分享
        cursor.execute("""
            SELECT s.*, u.username 
            FROM shares s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.user_id = ? 
            ORDER BY s.created_at DESC
        """, (session['user_id'],))
    
    shares = cursor.fetchall()
    conn.close()
    
    return render_template('manage_shares.html', shares=shares)

@app.route('/delete_share/<int:share_id>')
@password_change_required
def delete_share(share_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查权限
    if session.get('is_admin'):
        cursor.execute("DELETE FROM shares WHERE id = ?", (share_id,))
    else:
        cursor.execute("DELETE FROM shares WHERE id = ? AND user_id = ?", 
                      (share_id, session['user_id']))
    
        conn.commit()
        conn.close()

    flash('分享已删除', 'success')
    return redirect(url_for('manage_shares'))

@app.route('/batch_download', methods=['POST'])
@password_change_required
def batch_download():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': '没有选择要下载的项目'}), 400
    
    # 确定基础路径
    if session.get('is_admin'):
        base_path = app.config['GRACEDISK_CONFIG'].get('storage_path')
    elif session.get('is_visitor'):
        base_path = app.config['GRACEDISK_CONFIG'].get('visitor_storage_path', app.config['GRACEDISK_CONFIG'].get('storage_path'))
    else:
        base_path = os.path.join('userfiles', session['username'])
    
    import zipfile
    import io
    
    # 创建内存中的ZIP文件
    zip_buffer = io.BytesIO()
    total_size = 0
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for item_path in items:
            try:
                safe_path = os.path.normpath(item_path).lstrip('.\\/')
                full_path = os.path.join(base_path, safe_path)
                
                if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
                    continue
                
                if not os.path.exists(full_path):
                    continue
                
                if os.path.isfile(full_path):
                    # 添加文件到ZIP
                    zip_file.write(full_path, os.path.basename(full_path))
                    total_size += os.path.getsize(full_path)
                elif os.path.isdir(full_path):
                    # 添加整个文件夹到ZIP
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # 计算相对路径
                            arcname = os.path.relpath(file_path, os.path.dirname(full_path))
                            zip_file.write(file_path, arcname)
                            total_size += os.path.getsize(file_path)
                            
            except Exception as e:
                print(f"Error adding {item_path} to zip: {e}")
                continue
    
    zip_buffer.seek(0)
    
    # 生成下载文件名
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"gracedisk_files_{timestamp}.zip"
    
    # 记录下载操作
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO file_operations (user_id, operation_type, file_path, file_size, status) 
        VALUES (?, ?, ?, ?, ?)
    """, (session['user_id'], 'download', f"批量下载: {', '.join(items[:3])}{'...' if len(items) > 3 else ''}", total_size, 'completed'))
    conn.commit()
    conn.close()
    
    return Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

@app.route('/about')
@password_change_required  
def about():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    config = app.config['GRACEDISK_CONFIG']
    about_info = config.get('about', {
        'title': 'GraceDisk 文件管理系统',
        'version': 'v2.0',
        'description': 'GraceDisk 是一个现代化的网络文件管理系统。',
        'footer': '© 2025 GraceDisk. 由 Flask 强力驱动.'
    })
    
    return render_template('about.html', about=about_info)

@app.route('/file_history')
@password_change_required
def file_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取用户的文件操作历史
    cursor.execute("""
        SELECT * FROM file_operations 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (session['user_id'],))
    
    operations = cursor.fetchall()
    conn.close()
    
    return render_template('file_history.html', operations=operations)

@app.route('/record_download', methods=['POST'])
@password_change_required
def record_download():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    file_path = data.get('file_path', '')
    file_size = data.get('file_size', 0)
    
    if not file_path:
        return jsonify({'error': '文件路径不能为空'}), 400
    
    # 记录下载操作
    db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO file_operations (user_id, operation_type, file_path, file_size, status) 
        VALUES (?, ?, ?, ?, ?)
    """, (session['user_id'], 'download', os.path.basename(file_path), file_size, 'completed'))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/dashboard')
@admin_required
def dashboard():
    """管理员仪表盘"""
    try:
        import psutil
        import time
        from datetime import datetime, timedelta
        
        db_path = app.config['GRACEDISK_CONFIG'].get('users_db_path', 'users.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取统计数据
        stats = {}
        
        # 近30天登录统计
        thirty_days_ago = datetime.now() - timedelta(days=30)
        thirty_days_str = thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            SELECT COUNT(*) as total_logins,
                   COUNT(DISTINCT user_id) as unique_users,
                   login_type,
                   DATE(created_at) as login_date
            FROM login_logs 
            WHERE created_at >= ? 
            GROUP BY login_type, DATE(created_at)
            ORDER BY login_date DESC
        """, (thirty_days_str,))
        
        login_data = cursor.fetchall()
        
        # 今日登录统计
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT login_type, COUNT(*) as count
            FROM login_logs 
            WHERE DATE(created_at) = ?
            GROUP BY login_type
        """, (today,))
        
        today_logins = {row['login_type']: row['count'] for row in cursor.fetchall()}
        
        # 文件操作统计（近30天）
        cursor.execute("""
            SELECT operation_type, 
                   COUNT(*) as count,
                   SUM(CASE WHEN file_size IS NOT NULL THEN file_size ELSE 0 END) as total_size
            FROM file_operations 
            WHERE created_at >= ?
            GROUP BY operation_type
        """, (thirty_days_str,))
        
        file_operations = {row['operation_type']: {'count': row['count'], 'total_size': row['total_size']} 
                          for row in cursor.fetchall()}
        
        # 用户统计
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE can_login = 1")
        active_users = cursor.fetchone()['active_users']
        
        # 分享统计
        cursor.execute("SELECT COUNT(*) as total_shares FROM shares")
        total_shares = cursor.fetchone()['total_shares']
        
        # 活跃分享（未过期）
        cursor.execute("""
            SELECT COUNT(*) as active_shares 
            FROM shares 
            WHERE expires_at IS NULL OR expires_at > datetime('now')
        """)
        active_shares = cursor.fetchone()['active_shares']
        
        conn.close()
        
        # 简化的系统资源统计 - 只获取CPU和内存
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)  # 减少等待时间
            memory = psutil.virtual_memory()
            
            # 简化的进程信息
            try:
                current_process = psutil.Process()
                process_memory_mb = current_process.memory_info().rss / 1024 / 1024
                process_threads = current_process.num_threads()
            except:
                process_memory_mb = 0
                process_threads = 0
            
            process_info = {
                'memory_mb': process_memory_mb,
                'threads': process_threads
            }
            
        except Exception as e:
            # 如果psutil出现问题，使用默认值
            cpu_percent = 0
            memory = type('obj', (object,), {
                'total': 0, 'used': 0, 'available': 0, 'percent': 0
            })()
            process_info = {'memory_mb': 0, 'threads': 0}
        
        stats = {
            'login_data': login_data,
            'today_logins': today_logins,
            'file_operations': file_operations,
            'users': {'total': total_users, 'active': active_users},
            'shares': {'total': total_shares, 'active': active_shares},
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'used': memory.used,
                    'available': memory.available,
                    'percent': memory.percent
                },
                'process': process_info
            }
        }
        
        return render_template('dashboard.html', stats=stats)
        
    except ImportError:
        flash('系统监控功能需要安装 psutil: pip install psutil', 'error')
        return redirect(url_for('root'))
    except Exception as e:
        flash(f'获取系统信息失败: {str(e)}', 'error')
        return redirect(url_for('root'))


if __name__ == '__main__':
    config = app.config['GRACEDISK_CONFIG']
    server_config = config.get('server', {})
    
    host = server_config.get('host', '127.0.0.1')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', True)
    
    print(f"🚀 GraceDisk 启动中...")
    print(f"📡 服务器地址: http://{host}:{port}")
    if host == '0.0.0.0':
        print("🌍 服务器已向公网开放，请确保防火墙和安全设置正确！")
    print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
    print("=" * 50)
    
    app.run(host=host, port=port, debug=debug)

