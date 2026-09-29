#!/usr/bin/env bash
# 后端可重复构建：环境检查 -> 虚拟环境 -> 依赖（以 lock 文件为准）-> 基础数据自检。
# 每一步都可重复执行；失败时打印卡在哪一步、原因和重试办法，修正后重跑本脚本即可。
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.lock.txt}"
SEED_FILE="${APP_SEED_FILE:-data/seed.json}"

step() { printf '\n\033[1m[步骤 %s] %s\033[0m\n' "$1" "$2"; }
fail() {
  printf '\n\033[31m安装在「步骤 %s %s」失败：%s\033[0m\n' "$1" "$2" "$3" >&2
  printf '解决上面的问题后重新执行：%s\n' "$0" >&2
  exit 1
}
trap 'fail "${STEP_NO:-?}" "${STEP_NAME:-未知}" "命令异常退出（详见上方输出）"' ERR

# ---- 步骤 1：Python 环境 ----
STEP_NO=1
STEP_NAME="检查 Python"
step "$STEP_NO" "$STEP_NAME"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1 && [ ! -x "$PYTHON_BIN" ]; then
  fail "$STEP_NO" "$STEP_NAME" "找不到解释器 $PYTHON_BIN，可用 PYTHON_BIN 指定，例如 PYTHON_BIN=python3.11"
fi
py_version="$("$PYTHON_BIN" --version 2>&1)" || fail "$STEP_NO" "$STEP_NAME" "无法执行 $PYTHON_BIN：$py_version"
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
  || fail "$STEP_NO" "$STEP_NAME" "需要 Python 3.10+，当前是 $py_version"
echo "使用 $py_version"

# ---- 步骤 2：虚拟环境 ----
STEP_NO=2
STEP_NAME="准备虚拟环境 $VENV_DIR"
step "$STEP_NO" "$STEP_NAME"

bootstrap_pip() {
  # 发行版自带 venv 可能不带 pip（如 Debian 需 python3-venv）：用官方 get-pip 引导
  local get_pip
  get_pip="$(mktemp)"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$get_pip" \
      || fail "$STEP_NO" "$STEP_NAME" "下载 get-pip.py 失败，请检查网络后重试"
  else
    "$PYTHON_BIN" - "$get_pip" <<'PY'
import sys, urllib.request
try:
    urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", sys.argv[1])
except OSError as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
PY
  fi
  "$VENV_DIR/bin/python" "$get_pip" >/dev/null \
    || fail "$STEP_NO" "$STEP_NAME" "get-pip 引导失败，请检查网络后重试"
  rm -f "$get_pip"
}

if [ -x "$VENV_DIR/bin/python" ]; then
  echo "虚拟环境已存在，跳过创建（删除 $VENV_DIR 可强制重建）"
else
  # 标准 venv 成功与否都以 bin/pip 是否就绪为准，过程噪音收敛到失败时才展示
  if "$PYTHON_BIN" -m venv "$VENV_DIR" >/tmp/venv_out 2>&1 \
      && [ -x "$VENV_DIR/bin/pip" ]; then
    :
  else
    rm -rf "$VENV_DIR"
    "$PYTHON_BIN" -m venv --without-pip "$VENV_DIR" >/tmp/venv_out 2>&1 || {
      cat /tmp/venv_out >&2 || true
      fail "$STEP_NO" "$STEP_NAME" "venv 创建失败，Debian/Ubuntu 请先安装 python3-venv"
    }
    echo "系统 venv 未带 pip，改用 get-pip.py 引导安装 pip"
    bootstrap_pip
  fi
fi

# 已存在的虚拟环境也可能缺 pip（损坏/旧版本），统一兜底
if [ ! -x "$VENV_DIR/bin/pip" ]; then
  "$VENV_DIR/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || bootstrap_pip
fi

# ---- 步骤 3：安装锁定依赖 ----
STEP_NO=3
STEP_NAME="安装锁定依赖（$REQUIREMENTS_FILE）"
step "$STEP_NO" "$STEP_NAME"
[ -f "$REQUIREMENTS_FILE" ] \
  || fail "$STEP_NO" "$STEP_NAME" "找不到 $REQUIREMENTS_FILE"
"$VENV_DIR/bin/python" -m pip install --upgrade --quiet pip \
  || fail "$STEP_NO" "$STEP_NAME" "pip 自升级失败，请检查网络/镜像源后重试"
# pip 自身已做幂等：版本一致时直接跳过；网络抖动后重跑本步骤即可续装
"$VENV_DIR/bin/pip" install --disable-pip-version-check -r "$REQUIREMENTS_FILE" \
  | grep -v -E '^Requirement already satisfied' || true
if ! "$VENV_DIR/bin/pip" check >/dev/null 2>&1; then
  fail "$STEP_NO" "$STEP_NAME" "依赖完整性检查未通过（pip check），请重跑本脚本"
fi
echo "依赖已就绪，版本以 $REQUIREMENTS_FILE 为准"

# ---- 步骤 4：基础数据自检 ----
STEP_NO=4
STEP_NAME="校验示例数据（$SEED_FILE）"
step "$STEP_NO" "$STEP_NAME"
[ -f "$SEED_FILE" ] \
  || fail "$STEP_NO" "$STEP_NAME" "找不到 $SEED_FILE（可用 APP_SEED_FILE 指定路径）"
APP_SEED_FILE="$SEED_FILE" "$VENV_DIR/bin/python" -m app.seed verify \
  || fail "$STEP_NO" "$STEP_NAME" "示例数据校验未通过，按上方提示修正 $SEED_FILE"

trap - ERR
printf '\n后端构建完成：.venv 与基础数据均已就绪，可执行 ./run.sh 启动。\n'
