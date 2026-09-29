"""特种设备点检运维平台 后端服务入口。

启动：uvicorn app.main:app --host 127.0.0.1 --port 8000
健康检查：GET /api/health
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ROUTERS
from app.seed import SeedError, run_check
from app.store import store

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in ROUTERS:
    app.include_router(module.router)


@app.on_event("startup")
def verify_seed() -> None:
    """启动前确认基础数据文件可用且重复装载不产生重复记录；失败时让服务起不来并说明原因。"""
    if settings.seed_on_startup:
        try:
            run_check(settings.seed_file)
        except SeedError as exc:
            raise RuntimeError(f"基础数据初始化失败，服务中止启动：{exc}") from exc
        # 自检用的是独立内存表，通过后再幂等装载进仓库（已存在的记录会被跳过）
        store.load_seed()


@app.get("/api/health")
def health() -> dict[str, object]:
    """健康检查：确认服务已经监听、示例数据已经就绪。"""
    return {
        "ok": True,
        "app": settings.app_name,
        "env": settings.env,
        "modules": len(store.module_names()),
        "inspect_categories": len(store.inspect_categories()),
        "inspect_agencies": len(store.inspect_agencies()),
    }


@app.get("/api/overview")
def overview() -> dict[str, object]:
    """运营概览：把各业务模块的待处理量汇总成看板卡片。"""
    return store.overview()
