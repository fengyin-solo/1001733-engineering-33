FROM python:3.12.8-slim
WORKDIR /srv/app

# 第一步：先装依赖（利用层缓存）。版本在 requirements.txt 中精确锁定，
# 网络抖动时 pip 自行重试，构建日志能明确看到卡在依赖安装这一步。
COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check --retries 5 -r requirements.txt

# 第二步：拷入代码与基础数据，并在镜像构建期校验种子数据；
# 校验不过（JSON 非法、id 重复、基础数据引用缺失）镜像直接构建失败。
COPY app ./app
COPY data ./data
RUN python -m app.seed check

EXPOSE 8000

# 第三步：启动。监听地址/端口取环境变量，与本地 run.sh 读同一份配置。
CMD ["sh", "-c", "exec uvicorn app.main:app --host \"${APP_HOST:-0.0.0.0}\" --port \"${APP_PORT:-8000}\""]
