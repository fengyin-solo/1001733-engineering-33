#!/usr/bin/env bash
# 启动后端：依赖安装与监听地址都按仓库根目录 .env.example 的配置来。
# 用法不变：cd backend && ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

# venv 损坏（解释器路径不存在）时重建，避免旧机器上的环境拖垮启动。
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys' >/dev/null 2>&1; then
  echo "[run] 虚拟环境不可用，重新创建 .venv"
  rm -rf .venv
  if ! python3 -m venv .venv 2>/dev/null || [ ! -x .venv/bin/pip ]; then
    # 精简系统缺少 ensurepip 时，用 get-pip.py 引导，无需手工装 python3-venv。
    echo "[run] venv 未自带 pip，改用 get-pip.py 引导"
    python3 -m venv --without-pip .venv
    get_pip="$(mktemp /tmp/get-pip.XXXXXX.py)"
    curl -fsSL --retry 3 https://bootstrap.pypa.io/get-pip.py -o "$get_pip"
    .venv/bin/python "$get_pip" --quiet
    rm -f "$get_pip"
  fi
fi

# 读入配置基线（端口/地址），已存在的环境变量以外部注入为准。
# 复用服务自身的解析器，避免 source 对值中的特殊字符做 shell 展开。
eval "$(.venv/bin/python - <<'PY'
from app.config import _load_values
for key in ("APP_HOST", "APP_PORT"):
    value = _load_values().get(key)
    if value is not None:
        escaped = value.replace("'", "'\\''")
        print(f"{key}='{escaped}'")
PY
)"

# 依赖按锁定版本安装；失败由 pip 自行重试，并提示卡在哪一步。
.venv/bin/pip install \
  --disable-pip-version-check \
  --retries 3 \
  -r requirements.txt

exec .venv/bin/python -m uvicorn app.main:app \
  --host "${APP_HOST:-127.0.0.1}" \
  --port "${APP_PORT:-8000}"
