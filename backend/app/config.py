"""运行配置：端口、跨域、运行环境，统一从环境变量读取。

配置来源（后者覆盖前者，但已存在的真实环境变量永远优先）：

1. 仓库根目录 ``.env.example`` —— 提交进仓库的唯一基线，端口以它为准，
   本地开发与 docker-compose 构建结果一致；
2. 本地 ``backend/.env``（不存在则跳过）—— 不提交，仅用于本机临时覆盖；
3. 进程环境变量 —— 部署平台注入的值优先级最高。

非法值（比如 APP_PORT 不是数字）在这里直接抛出 ConfigError，
服务拒绝启动并说明卡在哪一步，而不是静默回退。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
BASELINE_ENV = REPO_ROOT / ".env.example"


class ConfigError(RuntimeError):
    """环境变量不合法：消息会说明具体是哪一项、期望什么值。"""


def _parse_env_file(path: Path) -> dict[str, str]:
    """解析简单 KEY=VALUE 文件：忽略空行与 # 注释，不去除引号以外的特殊语法。"""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not key:
            raise ConfigError(f"配置文件 {path} 第 {lineno} 行缺少变量名")
        values[key] = value
    return values


def _load_values() -> dict[str, str]:
    # 先放基线默认值，再叠加本地覆盖；最后用真实环境变量补齐，
    # 保证平台注入的值不会被文件覆盖。
    values = _parse_env_file(BASELINE_ENV)
    for local_file in (REPO_ROOT / ".env", BACKEND_DIR / ".env"):
        values.update(_parse_env_file(local_file))
    for key, value in os.environ.items():
        values[key] = value
    return values


def _resolve_port(values: dict[str, str], key: str, default: int) -> int:
    raw = values.get(key, str(default)).strip()
    try:
        port = int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {key}={raw!r} 不是合法端口号，应为 1-65535 的整数") from exc
    if not 1 <= port <= 65535:
        raise ConfigError(f"环境变量 {key}={port} 超出端口范围，应为 1-65535 的整数")
    return port


def _resolve_origins(values: dict[str, str], frontend_port: int) -> list[str]:
    raw = values.get("CORS_ALLOW_ORIGINS", "").strip()
    if raw:
        origins = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        if not origins:
            raise ConfigError("环境变量 CORS_ALLOW_ORIGINS 已设置但解析不出任何来源，请用逗号分隔")
        return origins
    return [f"http://127.0.0.1:{frontend_port}", f"http://localhost:{frontend_port}"]


@dataclass(frozen=True)
class Settings:
    app_name: str
    env: str
    host: str
    port: int
    frontend_port: int
    allowed_origins: list[str] = field(default_factory=list)
    page_size_default: int = 20
    page_size_max: int = 200


def _build_settings() -> Settings:
    values = _load_values()
    frontend_port = _resolve_port(values, "FRONTEND_PORT", 5173)
    return Settings(
        app_name=values.get("APP_NAME", "特种设备点检运维平台").strip() or "特种设备点检运维平台",
        env=values.get("APP_ENV", "local").strip() or "local",
        host=values.get("APP_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=_resolve_port(values, "APP_PORT", 8000),
        frontend_port=frontend_port,
        allowed_origins=_resolve_origins(values, frontend_port),
    )


settings = _build_settings()
