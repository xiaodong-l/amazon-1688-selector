#!/bin/bash
# 亚马逊选品系统 - Web 服务启动脚本

echo "======================================"
echo "🚀 亚马逊选品系统 - Web 服务"
echo "======================================"

cd "$(dirname "$0")"

# 检查依赖
echo "📦 检查依赖..."
pip3 install --break-system-packages --quiet flask 2>/dev/null

# 启动服务
echo ""
echo "🌐 启动 Web 服务..."
echo "   访问地址：http://localhost:5000"
echo "   按 Ctrl+C 停止服务"
echo ""

python3 web/app.py
