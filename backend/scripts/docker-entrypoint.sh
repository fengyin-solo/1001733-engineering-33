#!/usr/bin/env sh
set -eu

# 容器入口：启动前幂等初始化基础数据（按 模块+id 去重，重复启动不产生重复记录）。
# 失败时打印原因并退出，避免带着坏数据对外提供服务。
python -m app.seed init

# CMD 默认是 uvicorn；端口以 APP_PORT 环境变量为准，与 --port 显式参数保持一致
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
