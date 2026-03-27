#!/bin/bash
# 亚马逊选品系统 - Web 服务后台运行脚本

cd "$(dirname "$0")"

# 停止旧进程
pkill -f "python.*web/app.py" 2>/dev/null
sleep 1

# 启动新进程 (后台运行)
nohup python3 web/app.py > /tmp/amazon-web.log 2>&1 &
PID=$!

echo "======================================"
echo "✅ 亚马逊选品系统 - Web 服务已启动"
echo "======================================"
echo ""
echo "📍 访问地址："
echo "   http://localhost:5000"
echo "   http://192.168.1.46:5000"
echo ""
echo "📋 进程 PID: $PID"
echo ""
echo "📄 日志文件：/tmp/amazon-web.log"
echo ""
echo "🛑 停止服务：pkill -f 'python.*web/app.py'"
echo "🔍 查看日志：tail -f /tmp/amazon-web.log"
echo ""

# 等待服务启动
sleep 3

# 检查服务状态
if curl -s http://127.0.0.1:5000 > /dev/null 2>&1; then
    echo "✅ 服务状态：运行中"
else
    echo "⚠️  服务状态：启动中，请稍候..."
fi
