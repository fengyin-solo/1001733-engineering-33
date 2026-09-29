#!/usr/bin/env bash
# 可重复的本地构建流程：装依赖 -> 校验基础数据 -> 校验前端依赖锁。
# 任意一步失败都会打印卡在哪一步以及如何重试；脚本本身可安全反复执行。
#
#   ./setup.sh            执行全部步骤
#   ./setup.sh backend    只装后端依赖并校验基础数据
#   ./setup.sh frontend   只按 lockfile 安装前端依赖
set -uo pipefail
cd "$(dirname "$0")"

PIP_RETRIES=5
NPM_RETRIES=5

step() { printf '\n\033[1;36m[setup]\033[0m %s\n' "$*"; }
fail() {
  printf '\n\033[1;31m[setup] ✗ 失败：%s\033[0m\n' "$*" >&2
  printf '\033[1;31m[setup] 重试方法：修复网络或配置后重新执行 ./setup.sh（已完成的步骤会跳过/复用）\033[0m\n' >&2
  exit 1
}

setup_backend() {
  step "1/4 检查 Python（需要 3.10 及以上）"
  command -v python3 >/dev/null || fail "找不到 python3，请先安装 Python 3.10+"
  python3 - <<'PY' || fail "Python 版本低于 3.10，请升级后重试"
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
  python3 --version

  step "2/4 创建/修复后端虚拟环境 .venv"
  if [ ! -x backend/.venv/bin/python ] || ! backend/.venv/bin/python -c 'import sys' >/dev/null 2>&1; then
    echo "[setup] .venv 缺失或解释器已失效，重新创建"
    rm -rf backend/.venv
    if ! python3 -m venv backend/.venv 2>/dev/null || [ ! -x backend/.venv/bin/pip ]; then
      # 精简系统（如未装 python3-venv）创建不出 pip：改用无 pip 的 venv，
      # 再用官方 get-pip.py 引导，避免要求手工安装系统包。
      echo "[setup] 标准 venv 不可用（缺少 ensurepip），改用 get-pip.py 引导 pip"
      rm -rf backend/.venv
      python3 -m venv --without-pip backend/.venv \
        || fail "第 2 步：venv 创建失败，请确认 Python 3.10+ 自带 venv 模块"
      get_pip="$(mktemp /tmp/get-pip.XXXXXX.py)"
      if command -v curl >/dev/null; then
        curl -fsSL --retry "${PIP_RETRIES}" https://bootstrap.pypa.io/get-pip.py -o "$get_pip" \
          || fail "第 2 步：下载 get-pip.py 失败，检查网络后重试"
      else
        fail "第 2 步：系统既无 venv pip 也无 curl 可引导 pip，请安装 python3-venv 后重试"
      fi
      backend/.venv/bin/python "$get_pip" --quiet \
        || fail "第 2 步：get-pip.py 引导 pip 失败，重试 ./setup.sh backend 即可"
      rm -f "$get_pip"
    fi
  else
    echo "[setup] .venv 可用，跳过创建"
  fi

  step "3/4 安装后端依赖（requirements.txt 已精确锁定版本，pip 失败自动重试 ${PIP_RETRIES} 次）"
  (
    cd backend
    for attempt in $(seq 1 "${PIP_RETRIES}"); do
      echo "[setup] pip install 第 ${attempt}/${PIP_RETRIES} 次尝试"
      if .venv/bin/pip install --disable-pip-version-check -r requirements.txt; then
        exit 0
      fi
      echo "[setup] pip install 第 ${attempt} 次失败，2 秒后重试……"
      sleep 2
    done
    exit 1
  ) || fail "第 3 步：后端依赖安装失败（网络或 pip 源问题），重试 ./setup.sh backend 即可续装"

  step "4/4 校验基础数据 data/seed.json（结构、id 唯一性、检验类别/机构引用）"
  (cd backend && .venv/bin/python -m app.seed check) \
    || fail "第 4 步：基础数据校验未通过，按上面的说明修正 backend/data/seed.json 后重试"

  echo "[setup] 幂等性自检：再装载一遍种子数据，确认不产生重复记录"
  (cd backend && .venv/bin/python -m app.seed load) \
    || fail "第 4 步：基础数据装载不自洽，请检查 seed.json"
}

setup_frontend() {
  step "前端：检查 Node/npm"
  command -v npm >/dev/null || fail "找不到 npm，请先安装 Node.js 20+"
  node --version
  npm --version

  step "前端：按 package-lock.json 精确安装依赖（npm ci，失败自动重试 ${NPM_RETRIES} 次）"
  (
    cd frontend
    for attempt in $(seq 1 "${NPM_RETRIES}"); do
      echo "[setup] npm ci 第 ${attempt}/${NPM_RETRIES} 次尝试"
      if npm ci --no-audit --no-fund; then
        exit 0
      fi
      echo "[setup] npm ci 第 ${attempt} 次失败，2 秒后重试……"
      sleep 2
    done
    exit 1
  ) || fail "前端依赖安装失败：若提示 lockfile 与 package.json 不同步，请先执行 npm install --package-lock-only 更新锁文件，再重试 ./setup.sh frontend"
}

case "${1:-all}" in
  backend) setup_backend ;;
  frontend) setup_frontend ;;
  all)
    setup_backend
    setup_frontend
    step "全部完成"
    echo "[setup] 启动方式保持不变：make backend（后端）/ make frontend（前端）"
    ;;
  *)
    echo "用法：./setup.sh [all|backend|frontend]" >&2
    exit 2
    ;;
esac
