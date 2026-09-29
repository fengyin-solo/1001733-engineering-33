#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 端口/主机以根目录 .env.example 这份配置为准（本地默认 127.0.0.1:8000，
# 容器里用 APP_HOST=0.0.0.0 覆盖）；没有虚拟环境时先按分步脚本构建。
if [ ! -d .venv ]; then
  ./scripts/setup.sh
fi

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"

exec .venv/bin/uvicorn app.main:app --host "$APP_HOST" --port "$APP_PORT"
