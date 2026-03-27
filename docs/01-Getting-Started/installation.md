# 🚀 安装指南

**版本:** v2.1.0  
**最后更新:** 2026-03-27  
**状态:** ✅ 已完成  
**预计时间:** 15-30 分钟

---

## 📋 系统要求

### 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核心 | 4 核心+ |
| 内存 | 4 GB | 8 GB+ |
| 存储 | 2 GB | 10 GB+ |
| 网络 | 宽带连接 | 高速宽带 |

### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 推荐 3.12 |
| pip | 23.0+ | Python 包管理 |
| Git | 2.30+ | 版本控制 |
| Node.js | 18.0+ | 可选 (前端开发) |

### 操作系统

- ✅ Ubuntu 20.04+
- ✅ Debian 11+
- ✅ macOS 11+
- ✅ Windows 10+ (WSL2 推荐)

---

## 🔧 安装步骤

### 步骤 1: 安装 Python

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
python3 --version  # 验证：应显示 3.10+
```

#### macOS
```bash
# 使用 Homebrew
brew install python@3.12
python3 --version
```

#### Windows (WSL2)
```bash
# 在 WSL2 中执行
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

---

### 步骤 2: 克隆项目

```bash
# 克隆仓库
git clone https://github.com/xiaodong-l/amazon-1688-selector.git
cd amazon-1688-selector

# 查看项目结构
ls -la
```

**预期输出:**
```
total 100+
drwxr-xr-x  admina  admina  4096  Mar 27 06:17  .
drwxr-xr-x  admina  admina  4096  Mar 27 06:17  ..
drwxr-xr-x  admina  admina  4096  Mar 27 06:17  .git
-rw-r--r--  admina  admina   389  Mar 27 02:00  .gitignore
-rw-r--r--  admina  admina  1079  Mar 27 02:00  LICENSE
-rw-r--r--  admina  admina  8500  Mar 27 02:00  README.md
-rw-r--r--  admina  admina  2300  Mar 27 02:00  requirements.txt
drwxr-xr-x  admina  admina  4096  Mar 27 02:00  src/
drwxr-xr-x  admina  admina  4096  Mar 27 02:00  web/
drwxr-xr-x  admina  admina  4096  Mar 27 06:17  docs/
...
```

---

### 步骤 3: 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate

# Windows:
# venv\Scripts\activate

# 验证激活
which python  # Linux/macOS
# 或
where python  # Windows
```

**预期输出:**
```
/home/your-user/amazon-1688-selector/venv/bin/python
```

---

### 步骤 4: 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

**依赖清单:**
```
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
aiofiles>=23.0.0
matplotlib>=3.8.0
plotly>=5.18.0
scipy>=1.11.0
kaleido>=0.2.0
flask>=3.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-timeout>=2.2.0
black>=23.0.0
flake8>=6.1.0
mypy>=1.5.0
```

**安装时间:** 约 2-5 分钟 (取决于网络)

---

### 步骤 5: 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置文件
vim .env
# 或
nano .env
```

**配置文件 (.env):**
```bash
# Rainforest API 配置
RAINFOREST_API_KEY=your_api_key_here
RAINFOREST_API_URL=https://api.rainforestapi.com/request

# 项目配置
PROJECT_ROOT=/home/your-user/amazon-1688-selector
DATA_DIR=data
LOGS_DIR=logs

# Web 服务配置
FLASK_ENV=development
FLASK_PORT=5000
FLASK_HOST=0.0.0.0

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=detailed
```

**⚠️ 重要:**
- 不要将 `.env` 文件提交到 Git
- 使用真实的 API 密钥替换 `your_api_key_here`
- 根据实际路径修改 `PROJECT_ROOT`

---

### 步骤 6: 验证安装

```bash
# 运行测试套件
python -m pytest tests/ -v

# 预期输出：所有测试通过
==================== XX passed in X.XXs =====================

# 检查 Python 导入
python -c "import pandas; import numpy; import flask; print('✅ 所有依赖正常')"
```

**预期输出:**
```
✅ 所有依赖正常
```

---

## 🧪 快速测试

### 测试 1: 数据采集模块
```bash
cd src/amazon
python -c "from collector import AmazonCollector; print('✅ 采集模块正常')"
```

### 测试 2: 趋势分析模块
```bash
cd src/analysis
python -c "from trend_analyzer import TrendAnalyzer; print('✅ 分析模块正常')"
```

### 测试 3: Web 服务
```bash
# 启动 Web 服务
cd web
python app.py

# 在另一个终端测试
curl http://localhost:5000/api/health
```

**预期响应:**
```json
{"status": "ok", "version": "v2.1.0"}
```

---

## ⚙️ 可选配置

### 1. 启用图表 PNG 导出

Kaleido 需要 Chrome/Chromium:

```bash
# Ubuntu/Debian
sudo apt install chromium-browser -y

# macOS
brew install --cask google-chrome

# 验证
which chromium-browser || which google-chrome
```

### 2. 启用异步处理

```bash
# 安装 Redis (可选)
sudo apt install redis-server -y

# 安装 Celery (可选)
pip install celery[redis]
```

### 3. 启用数据库持久化

```bash
# 安装 PostgreSQL (可选)
sudo apt install postgresql postgresql-contrib -y

# 安装 Python 驱动
pip install psycopg2-binary sqlalchemy
```

---

## 🐛 常见问题

### 问题 1: pip 安装失败

**错误:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案:**
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 问题 2: 虚拟环境激活失败

**错误:**
```
bash: venv/bin/activate: No such file or directory
```

**解决方案:**
```bash
# 删除并重新创建
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

---

### 问题 3: 权限错误

**错误:**
```
Permission denied: 'venv/bin/pip'
```

**解决方案:**
```bash
# 修复权限
chmod -R u+w venv/

# 或使用 --user 安装
pip install --user -r requirements.txt
```

---

### 问题 4: Python 版本不兼容

**错误:**
```
Python 3.8 is not supported. Please use Python 3.10+
```

**解决方案:**
```bash
# 检查 Python 版本
python3 --version

# 安装 Python 3.12 (Ubuntu)
sudo apt install python3.12 python3.12-venv python3.12-dev -y
python3.12 -m venv venv
source venv/bin/activate
```

---

### 问题 5: API 密钥未配置

**错误:**
```
ValueError: RAINFOREST_API_KEY not configured
```

**解决方案:**
```bash
# 检查 .env 文件
cat .env | grep RAINFOREST_API_KEY

# 确保已设置真实 API 密钥
# 获取 API 密钥：https://www.rainforestapi.com/
```

---

## 📊 安装验证清单

- [ ] Python 3.10+ 已安装
- [ ] Git 已安装
- [ ] 项目已克隆
- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装
- [ ] .env 配置文件已创建
- [ ] API 密钥已配置
- [ ] 测试套件通过
- [ ] Web 服务可启动

**全部勾选后，安装完成！✅**

---

## 🚀 下一步

安装完成后，继续:

1. **[快速开始](./quickstart.md)** - 5 分钟上手指南
2. **[配置说明](./configuration.md)** - 详细配置选项
3. **[用户指南](../02-User-Guide/)** - 功能使用说明

---

## 📚 相关资源

| 资源 | 链接 |
|------|------|
| 项目 README | [README.md](../README.md) |
| 贡献指南 | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| 更新日志 | [CHANGELOG.md](../05-Project-Docs/changelog.md) |
| GitHub 仓库 | https://github.com/xiaodong-l/amazon-1688-selector |
| Issue 追踪 | https://github.com/xiaodong-l/amazon-1688-selector/issues |

---

## 💡 获取帮助

### 遇到问题？

1. **查看文档:** [文档中心](../README.md)
2. **搜索 Issue:** https://github.com/xiaodong-l/amazon-1688-selector/issues
3. **提交 Issue:** 提供错误信息和复现步骤
4. **讨论区:** https://github.com/xiaodong-l/amazon-1688-selector/discussions

---

**安装指南版本:** v1.0  
**最后更新:** 2026-03-27  
**维护者:** @admina

---

<div align="center">

**🎉 安装完成!**

[开始使用](./quickstart.md) | [查看文档](../README.md) | [报告问题](https://github.com/xiaodong-l/amazon-1688-selector/issues)

</div>
