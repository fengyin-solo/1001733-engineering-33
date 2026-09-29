FROM python:3.12.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

WORKDIR /srv/app

# 依赖单独一层：以 lock 文件为准，缓存命中率高、版本可重复
COPY requirements.lock.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# 应用代码与示例数据（本地、镜像构建用的是同一份 data/seed.json）
COPY app ./app
COPY data ./data
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    # 构建期就做一次基础数据校验，数据有问题直接让构建失败
    && python -m app.seed verify

EXPOSE 8000
# shell 形式以便 APP_PORT 在运行时生效（端口以环境变量这份配置为准）
ENTRYPOINT ["docker-entrypoint.sh"]
CMD uvicorn app.main:app --host "0.0.0.0" --port "${APP_PORT:-8000}"
