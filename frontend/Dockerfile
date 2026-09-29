FROM node:20.18.1-alpine
WORKDIR /srv/web

# 依赖依据 package-lock.json 精确安装；lockfile 与 package.json 不同步时
# npm ci 会直接失败并指出原因，避免 npm install 装出和本地不一样的版本。
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund --fetch-retries=5

COPY . .
EXPOSE 5173

# 地址/端口/后端代理全部取环境变量，与本地 dev 共用 vite.config.ts。
CMD ["sh", "-c", "npm run dev -- --host \"${VITE_HOST:-0.0.0.0}\" --port \"${FRONTEND_PORT:-5173}\" --strictPort"]
