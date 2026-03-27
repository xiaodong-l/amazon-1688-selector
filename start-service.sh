#!/bin/bash
# 亚马逊选品系统 - 稳定启动脚本

cd "$(dirname "$0")"

# 清理旧进程
echo "🔄 清理旧进程..."
pkill -9 -f "python.*web" 2>/dev/null
pkill -9 -f "flask" 2>/dev/null
sleep 2

# 启动服务 (使用 screen 保持后台运行)
echo "🚀 启动服务..."
python3 << 'EOF'
import subprocess
import sys
import time

# 启动 Flask
proc = subprocess.Popen(
    [sys.executable, "-m", "flask", "--app", "web.app", "run", "--host", "0.0.0.0", "--port", "5000"],
    stdout=open("/tmp/amazon-web.log", "w"),
    stderr=subprocess.STDOUT
)

print(f"✅ 服务已启动 (PID: {proc.pid})")
print("📍 访问地址：http://localhost:5000")
print("📍 局域网：http://192.168.1.46:5000")

# 等待服务就绪
time.sleep(3)

# 检查状态
import urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:5000", timeout=5)
    print("✅ 服务状态：运行正常")
except Exception as e:
    print(f"⚠️ 服务状态：{e}")

# 保持运行
proc.wait()
EOF
