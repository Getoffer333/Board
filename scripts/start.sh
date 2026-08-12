#!/bin/bash
# 求职工作台启动脚本：后端单端口 7788，前端由后端静态托管。
# 局域网访问：本机绑 0..0.0，手机连同一 WiFi 访问 http://<本机内网IP>:7788
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
exec .venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 7788
