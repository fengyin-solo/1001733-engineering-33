.PHONY: install install-backend install-frontend backend frontend seed seed-check

# 一键可重复构建：依赖锁定安装 + 基础数据校验，失败按提示重试。
install:
	./setup.sh all

install-backend:
	./setup.sh backend

install-frontend:
	./setup.sh frontend

# 幂等装载示例数据与基础数据（检验类别、检验机构），重复执行不产生重复记录。
seed:
	cd backend && (if [ -x .venv/bin/python ]; then .venv/bin/python -m app.seed load; else python3 -m app.seed load; fi)

seed-check:
	cd backend && (if [ -x .venv/bin/python ]; then .venv/bin/python -m app.seed check; else python3 -m app.seed check; fi)

# 启动方式保持不变。
backend:
	cd backend && ./run.sh

frontend:
	cd frontend && npm run dev
