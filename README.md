# 🌟 GraceDisk

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Flask-2.x-green.svg" alt="Flask Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/PRs-Welcome-brightgreen.svg" alt="PRs Welcome">
</div>

<div align="center">
  <h3>🎯 现代化网络文件管理系统</h3>
  <p><em>优雅永不过时 - Elegance Never Goes Out of Style</em></p>
</div>

---

## ✨ 项目简介

GraceDisk 是一个基于 Python Flask 构建的现代化网络文件管理系统。它采用美观的毛玻璃 (Glassmorphism) 设计风格，提供多用户支持、文件分享、权限管理等丰富功能。

作为一个个人开发的开源项目，我希望为用户提供简洁、安全、高效的文件管理体验。无论是个人使用还是团队协作，GraceDisk 都能满足你的需求。

## 🚀 核心特性

### 🎨 现代化界面
- **毛玻璃设计**: 优雅的半透明视觉效果
- **响应式布局**: 完美适配桌面端和移动端
- **自定义背景**: 支持个性化背景图片
- **直观操作**: 简洁明了的用户界面

### 👥 多用户系统
- **角色管理**: 管理员、普通用户、访客三种角色
- **权限控制**: 细粒度的功能权限管理
- **配额限制**: 灵活的存储空间配额设置
- **访客模式**: 只读访问指定公共目录

### 📁 文件管理
- **拖拽上传**: 支持多文件同时上传
- **实时上传进度**: WebSocket 驱动的真实上传进度条，显示速度和剩余时间
- **上传中断保护**: 页面关闭前提示用户，避免意外中断上传
- **批量操作**: 选择多个文件进行批量下载/删除/分享
- **文件预览**: 图片和视频在线预览
- **文件夹管理**: 创建、重命名、删除文件夹
- **操作历史**: 完整的文件操作记录
- **空间检查**: 上传前自动检查用户配额，避免超限

### 🔗 文件分享
- **链接分享**: 生成安全的分享链接
- **密码保护**: 可选的访问密码设置
- **有效期控制**: 灵活的分享时间限制
- **分享管理**: 查看和管理所有分享链接

### 🎥 媒体预览
- **图片预览**: 支持 JPEG、PNG、GIF、WebP 格式
- **视频播放**: 内置现代化视频播放器
- **播放控制**: 倍速播放、全屏、进度控制
- **键盘快捷键**: 便捷的播放控制

### 📊 系统监控
- **仪表盘**: 管理员专用系统状态监控
- **资源监控**: CPU、内存、磁盘使用统计
- **用户统计**: 登录次数、文件操作统计
- **实时数据**: 动态更新的系统信息

## 📸 界面预览

<div align="center">
  <img src="docs/images/login.png" alt="登录界面" width="400">
  <img src="docs/images/dashboard.png" alt="文件管理" width="400">
</div>

<div align="center">
  <img src="docs/images/video-preview.png" alt="视频预览" width="400">
  <img src="docs/images/admin-dashboard.png" alt="管理员仪表盘" width="400">
</div>

## 🛠️ 技术栈

- **后端**: Python 3.11+ + Flask 2.x + Flask-SocketIO
- **数据库**: SQLite 3
- **前端**: HTML5 + CSS3 + Vanilla JavaScript + Socket.IO
- **实时通信**: WebSocket (文件上传进度)
- **设计**: Glassmorphism (毛玻璃效果)
- **监控**: psutil (系统资源监控)
- **安全**: Werkzeug 密码哈希

## 📦 快速开始

### 环境要求

- Python 3.11 或更高版本
- 现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+)

### 安装部署

#### 使用 uv (推荐)

```bash
# 克隆项目
git clone https://github.com/your-username/gracedisk.git
cd gracedisk

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/macOS
uv pip install -r requirements.txt

# 配置系统
cp config.yaml.example config.yaml
# 编辑 config.yaml 配置管理员账号和存储路径

# 启动服务
python app.py
```

#### 使用 pip

```bash
git clone https://github.com/your-username/gracedisk.git
cd gracedisk

python -m venv venv
source venv/bin/activate  # Linux/macOS (Windows: venv\Scripts\activate)
pip install -r requirements.txt

cp config.yaml.example config.yaml
# 编辑配置文件

python app.py
```

### 首次配置

1. 编辑 `config.yaml` 配置文件：
   ```yaml
   admin:
     username: admin
     password: your_strong_password_here
   
   storage_path: "/path/to/your/files"
   allow_visiter: true
   visitor_storage_path: "/path/to/public/files"
   ```

2. 访问 http://localhost:5000

3. 使用管理员账号登录

4. 开始使用！

### ⚡ WebSocket 实时上传功能

新版本支持 WebSocket 驱动的实时上传进度：

**特性:**
- 📊 **实时进度**: 显示准确的上传百分比、速度和剩余时间
- 🛡️ **中断保护**: 页面关闭前自动提示，避免意外中断上传
- 🔄 **断线重连**: WebSocket 连接断开时自动尝试重连
- 📱 **移动友好**: 支持移动设备的文件上传

**使用方法:**
1. 选择文件后，系统自动使用 WebSocket 上传
2. 上传过程中可以看到实时的速度和进度信息
3. 如果尝试关闭页面，会收到确认提示
4. 上传完成后自动刷新页面显示新文件

## 📚 文档指南

我们为不同类型的用户提供了详细的指南：

### 📖 [开发者指南](docs/developer_guide.md)
面向想要参与开源项目开发的开发者：
- 🏗️ 项目架构和代码结构
- 🔧 开发环境搭建
- 📝 代码贡献规范
- 🧪 测试和调试指南
- 🚀 功能扩展开发

### 🚀 [部署指南](docs/user_guide.md)
面向需要部署系统的系统管理员：
- 🖥️ 生产环境部署
- 🔒 安全配置和优化
- 🔄 备份和维护策略
- 🐞 故障排除指南
- 📈 性能优化建议

### 👤 [用户指南](docs/client_guide.md)
面向使用系统的最终用户：
- 🎯 功能使用教程
- 💡 操作技巧和最佳实践
- 🛡️ 安全使用建议
- 📱 移动端使用指南
- ❓ 常见问题解答

## 🌟 主要功能

<table>
<tr>
<td width="50%">

### 🎯 核心功能
- ✅ 多用户权限管理
- ✅ 文件上传下载
- ✅ 文件夹管理
- ✅ 批量文件操作
- ✅ 文件分享链接
- ✅ 存储配额管理

</td>
<td width="50%">

### 🎨 界面特色
- ✅ 毛玻璃视觉效果
- ✅ 响应式设计
- ✅ 自定义背景图片
- ✅ 暗色主题适配
- ✅ 移动端优化
- ✅ 现代化图标

</td>
</tr>
<tr>
<td width="50%">

### 🔧 高级特性
- ✅ 视频在线播放
- ✅ 图片预览
- ✅ 访客模式
- ✅ 操作日志记录
- ✅ 系统监控面板
- ✅ 文件操作历史
- ✅ WebSocket 实时上传
- ✅ 上传进度跟踪
- ✅ 上传中断保护

</td>
<td width="50%">

### 🛡️ 安全特性
- ✅ 密码哈希存储
- ✅ 会话管理
- ✅ 路径安全检查
- ✅ 文件类型验证
- ✅ 权限验证
- ✅ CSRF 保护

</td>
</tr>
</table>

## 🎮 使用场景

### 👨‍💼 个人使用
- 📂 个人文件云存储
- 📱 多设备文件同步
- 🔗 文件分享给朋友
- 📷 照片和视频管理

### 🏢 团队协作
- 📁 项目文件共享
- 👥 团队成员权限管理
- 📊 文件操作审计
- 🔄 版本控制和备份

### 🎓 教育机构
- 📚 课程资料分发
- 👨‍🎓 学生作业提交
- 🎥 教学视频播放
- 📝 教学资源管理

### 🏠 家庭使用
- 👨‍👩‍👧‍👦 家庭照片共享
- 🎬 影音娱乐中心
- 📄 重要文档存储
- 👥 访客资料浏览

## 🤝 贡献指南

我非常欢迎社区的贡献！这是一个个人维护的开源项目，你的每一份贡献都很宝贵。

### 🎯 如何贡献

1. **🐛 报告 Bug**
   - 提交详细的 Issue
   - 包含复现步骤和环境信息

2. **💡 功能建议**
   - 在 Issues 中描述新功能想法
   - 讨论实现方案

3. **📝 代码贡献**
   - Fork 项目
   - 创建功能分支
   - 提交 Pull Request

4. **📚 文档改进**
   - 完善使用指南
   - 修正文档错误
   - 翻译多语言版本

### 🏆 贡献者

感谢所有为项目做出贡献的开发者！

<a href="https://github.com/your-username/gracedisk/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=your-username/gracedisk" />
</a>

## 📈 项目统计

<div align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=your-username&repo=gracedisk&show_icons=true&theme=default" alt="项目统计">
</div>

## 🎯 路线图

### 🔜 即将到来
- [ ] 📱 移动端 APP
- [ ] 🔍 全文搜索功能
- [ ] 🗜️ 在线压缩解压
- [ ] 📝 在线文档编辑
- [ ] 🔄 文件版本控制
- [ ] 🔄 断点续传功能
- [ ] 📊 上传统计分析

### 🚀 长期规划
- [ ] 🌐 多语言支持 (i18n)
- [ ] 🐳 Docker 容器化
- [ ] ☁️ 云存储集成
- [ ] 🔌 插件系统
- [ ] 🤖 AI 辅助功能

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

```
MIT License

Copyright (c) 2025 GraceDisk

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 🙏 致谢

### 🛠️ 技术栈致谢
- [Flask](https://flask.palletsprojects.com/) - 优秀的 Python Web 框架
- [SQLite](https://www.sqlite.org/) - 轻量级嵌入式数据库
- [psutil](https://psutil.readthedocs.io/) - 系统资源监控库

### 🎨 设计灵感
- [Glassmorphism](https://uxdesign.cc/glassmorphism-in-user-interfaces-1f39bb1308c9) - 毛玻璃设计风格
- [Material Design](https://material.io/) - 现代化设计理念

### 🌟 特别感谢
- 所有提供反馈和建议的用户
- 开源社区的无私分享精神
- 每一位 Star 和 Fork 的开发者

## 📞 联系方式

- 📧 **邮箱**: your-email@example.com
- 🐛 **问题反馈**: [GitHub Issues](https://github.com/your-username/gracedisk/issues)
- 💬 **讨论交流**: [GitHub Discussions](https://github.com/your-username/gracedisk/discussions)
- 🌟 **项目地址**: [GitHub Repository](https://github.com/your-username/gracedisk)

---

<div align="center">
  <h3>🌟 如果这个项目对你有帮助，请给个 Star ⭐</h3>
  <p>你的支持是我继续开发的动力！</p>
  
  <a href="https://github.com/your-username/gracedisk/stargazers">
    <img src="https://img.shields.io/github/stars/your-username/gracedisk?style=social" alt="GitHub stars">
  </a>
  <a href="https://github.com/your-username/gracedisk/network/members">
    <img src="https://img.shields.io/github/forks/your-username/gracedisk?style=social" alt="GitHub forks">
  </a>
</div>

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/your-username">Your Name</a></sub>
</div>
