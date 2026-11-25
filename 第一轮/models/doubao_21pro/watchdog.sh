#!/bin/bash
# 监控本项目机器人进程，死亡则自动重启（只管自己的 pidfile）
DIR="/Users/yuanf/DoubaoWork/chats/2026-11-21/new-chat-5"
PIDFILE="$DIR/bot.pid"
while true; do
  ALIVE=0
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
      ALIVE=1
    fi
  fi
  if [ "$ALIVE" -eq 0 ]; then
    cd "$DIR" || exit 1
    nohup python3 "$DIR/trader_bot.py" >> "$DIR/logs/stdout.log" 2>&1 &
    echo $! > "$PIDFILE"
    echo "$(date '+%H:%M:%S') watchdog 重启机器人 PID=$!" >> "$DIR/logs/watchdog.log"
  fi
  sleep 10
done
