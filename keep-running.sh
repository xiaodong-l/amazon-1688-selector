#!/bin/bash
# 亚马逊选品系统 - 持久化运行脚本

LOG="/tmp/amazon-web.log"
PIDFILE="/tmp/amazon-web.pid"

start_service() {
    cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector
    nohup python3 web/app.py > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 3
}

check_service() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# 主循环
while true; do
    if ! check_service; then
        echo "[$(date)] 服务未运行，启动..." >> "$LOG"
        start_service
        echo "[$(date)] 服务已启动 (PID: $(cat $PIDFILE))" >> "$LOG"
    fi
    sleep 10
done
