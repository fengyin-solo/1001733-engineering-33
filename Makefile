.PHONY: help config install install-backend install-frontend seed verify backend frontend clean

help: ## 显示可用目标
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

config: ## 根目录缺 .env 时从 .env.example 复制一份（端口以这份配置为准）
	@test -f .env || cp .env.example .env && echo "已就绪 .env（来自 .env.example，按需修改）"

install: config install-backend install-frontend ## 一键构建：后端依赖 + 前端依赖（失败可重跑，各步幂等）

install-back: install-backend
install-backend: ## 后端：虚拟环境 + 按 lock 文件装依赖 + 基础数据自检
	cd backend && ./scripts/setup.sh

install-front: install-frontend
install-frontend: ## 前端：按 package-lock.json 干净安装（npm ci）
	cd frontend && npm ci

seed: ## 幂等初始化基础数据（重复执行不产生重复记录）
	cd backend && .venv/bin/python -m app.seed init

verify: ## 只校验示例数据，不启动服务
	cd backend && .venv/bin/python -m app.seed verify

backend: ## 原有启动方式：cd backend && ./run.sh
	cd backend && ./run.sh

frontend: ## 原有启动方式：cd frontend && npm run dev
	cd frontend && npm run dev

clean: ## 删除虚拟环境与前端依赖目录
	rm -rf backend/.venv frontend/node_modules
