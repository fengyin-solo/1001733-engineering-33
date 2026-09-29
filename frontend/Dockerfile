FROM node:20.20.2-alpine3.21

ENV VITE_DEV_HOST=0.0.0.0 \
    VITE_DEV_PORT=5173 \
    VITE_PROXY_TARGET=http://backend:8000

WORKDIR /srv/web

# 依赖层：有 lock 文件才允许 ci，保证装出的依赖树可重复
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# 主机/端口/strictPort 全部由 vite.config 读环境变量决定（见 VITE_DEV_*），
# 这里不再用 CLI 写死端口，避免覆盖部署时的端口配置
CMD ["npm", "run", "dev"]
