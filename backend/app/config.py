"""运行配置：端口、跨域、运行环境，全部从环境变量读取并带默认值。

默认值与根目录 .env.example 保持一致：换环境只需要改环境变量，
不需要动代码；变量缺失或非法时在这里给出明确报错，而不是等服务起来再失败。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"环境变量 {name}={raw!r} 不是合法的布尔值（true/false）")


def _port(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"环境变量 {name}={raw!r} 不是合法端口，应为 1-65535 的整数")
    if not 1 <= value <= 65535:
        raise ValueError(f"环境变量 {name}={raw} 超出端口范围（1-65535）")
    return value


def _csv(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


BACKEND_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    app_name: str = field(
        default_factory=lambda: os.getenv("APP_NAME", "特种设备点检运维平台")
    )
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    host: str = field(default_factory=lambda: os.getenv("APP_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _port("APP_PORT", 8000))
    seed_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("APP_SEED_FILE", str(BACKEND_ROOT / "data" / "seed.json"))
        )
    )
    seed_on_startup: bool = field(
        default_factory=lambda: _bool("APP_SEED_ON_STARTUP", True)
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: _csv(
            "APP_ALLOWED_ORIGINS",
            [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
            ],
        )
    )
    page_size_default: int = 20
    page_size_max: int = 200


settings = Settings()
