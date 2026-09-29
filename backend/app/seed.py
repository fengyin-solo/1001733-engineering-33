"""示例数据装载器：从 data/seed.json 读取、校验并幂等装载基础数据。

为什么不再把数据写在代码里：
- 本地与镜像构建用同一份文件，产出一致；
- 校验集中在这里，文件缺失/损坏/引用不一致时直接给出可读原因；
- merge_tables 按「模块 + id」去重，重复装载不会产生重复记录。

命令行：
    python -m app.seed init      初始化/自检基础数据（幂等，可重复执行）
    python -m app.seed verify   只做校验，供构建与启动探针使用
"""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings


class SeedError(RuntimeError):
    """示例数据文件缺失或不符合约定。"""


@dataclass(frozen=True)
class SeedData:
    version: int
    modules: list[dict[str, str]]
    inspect_categories: list[str]
    inspect_agencies: list[str]
    tables: dict[str, list[dict[str, Any]]]

    @property
    def table_order(self) -> list[str]:
        return [item["name"] for item in self.modules]

    @property
    def module_labels(self) -> dict[str, str]:
        return {item["name"]: item["label"] for item in self.modules}

    def table_rows(self, module: str) -> list[dict[str, Any]]:
        return self.tables.get(module, [])


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SeedError(message)


def load_seed(path: str | Path | None = None) -> SeedData:
    """读取并校验示例数据文件；任何问题都以 SeedError 说明具体原因。"""
    seed_path = Path(path) if path else settings.seed_file
    if not seed_path.exists():
        raise SeedError(
            f"示例数据文件不存在：{seed_path}。"
            "请确认 data/seed.json 已随代码/镜像一起提供，或检查环境变量 APP_SEED_FILE。"
        )
    try:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError(f"示例数据文件不是合法 JSON：{seed_path}（第 {exc.lineno} 行第 {exc.colno} 列）") from exc
    except OSError as exc:
        raise SeedError(f"示例数据文件读取失败：{seed_path}：{exc}") from exc

    _require(isinstance(raw, dict), f"{seed_path} 顶层结构应为对象")
    version = raw.get("version")
    _require(isinstance(version, int), f"{seed_path} 缺少整数版本号字段 version")

    raw_modules = raw.get("modules")
    _require(isinstance(raw_modules, list) and raw_modules, f"{seed_path} 的 modules 应为非空列表")
    modules: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_modules):
        _require(isinstance(item, dict), f"{seed_path} modules[{index}] 应为对象")
        name, label = item.get("name"), item.get("label")
        _require(isinstance(name, str) and name, f"{seed_path} modules[{index}] 缺少 name")
        _require(isinstance(label, str) and label, f"{seed_path} modules[{index}] 缺少 label")
        _require(name not in seen, f"{seed_path} 模块 {name} 重复声明")
        seen.add(name)
        modules.append({"name": name, "label": label})

    raw_tables = raw.get("tables")
    _require(isinstance(raw_tables, dict), f"{seed_path} 的 tables 应为对象")

    tables: dict[str, list[dict[str, Any]]] = {}
    for module in modules:
        name = module["name"]
        rows = raw_tables.get(name)
        _require(isinstance(rows, list), f"{seed_path} 缺少模块 {name} 的示例数据表 tables.{name}")
        ids: set[int] = set()
        for index, row in enumerate(rows):
            where = f"{seed_path} tables.{name}[{index}]"
            _require(isinstance(row, dict), f"{where} 应为对象")
            for key in ("id", "status", "pending", "abnormal"):
                _require(key in row, f"{where} 缺少必填键 {key}")
            _require(isinstance(row["id"], int) and row["id"] > 0, f"{where} 的 id 应为正整数")
            _require(row["id"] not in ids, f"{where} 的 id={row['id']} 在模块内重复")
            ids.add(row["id"])
            _require(isinstance(row["status"], str) and row["status"], f"{where} 的 status 应为非空字符串")
            _require(isinstance(row["pending"], bool), f"{where} 的 pending 应为布尔值")
            _require(isinstance(row["abnormal"], bool), f"{where} 的 abnormal 应为布尔值")
            tables.setdefault(name, []).append(copy.deepcopy(row))

    categories = _require_string_list(raw, "inspect_categories", seed_path)
    agencies = _require_string_list(raw, "inspect_agencies", seed_path)

    for index, row in enumerate(tables.get("inspect", [])):
        where = f"{seed_path} tables.inspect[{index}]"
        _require(row.get("检验类别") in categories, f"{where} 的检验类别不在 inspect_categories 基础数据里")
        _require(row.get("检验机构") in agencies, f"{where} 的检验机构不在 inspect_agencies 基础数据里")

    return SeedData(
        version=version,
        modules=modules,
        inspect_categories=categories,
        inspect_agencies=agencies,
        tables=tables,
    )


def _require_string_list(raw: dict[str, Any], key: str, seed_path: Path) -> list[str]:
    value = raw.get(key)
    _require(isinstance(value, list) and value, f"{seed_path} 的 {key} 应为非空列表")
    for index, item in enumerate(value):
        _require(isinstance(item, str) and item.strip(), f"{seed_path} {key}[{index}] 应为非空字符串")
    return [str(item) for item in value]


def merge_tables(
    tables: dict[str, list[dict[str, Any]]], seed: SeedData
) -> tuple[int, int]:
    """把示例数据幂等合并进已有表：按「模块 + id」对齐，存在即跳过。

    返回 (新增条数, 跳过条数)。连续执行任意次，表内容保持不变。
    """
    inserted = skipped = 0
    for name in seed.table_order:
        target = tables.setdefault(name, [])
        existing_ids = {int(row.get("id", 0)) for row in target}
        for row in seed.table_rows(name):
            if row["id"] in existing_ids:
                skipped += 1
                continue
            target.append(copy.deepcopy(row))
            inserted += 1
    return inserted, skipped


def _summary(seed: SeedData) -> str:
    total = sum(len(seed.table_rows(name)) for name in seed.table_order)
    return (
        f"version={seed.version}，模块 {len(seed.table_order)} 个，"
        f"示例记录 {total} 条，检验类别 {len(seed.inspect_categories)} 项，"
        f"检验机构 {len(seed.inspect_agencies)} 家"
    )


def run_check(path: str | Path | None = None) -> SeedData:
    """装载 + 连续两次幂等合并自检：重复装载不应新增记录。"""
    seed = load_seed(path)
    tables: dict[str, list[dict[str, Any]]] = {}
    first_inserted, first_skipped = merge_tables(tables, seed)
    second_inserted, second_skipped = merge_tables(tables, seed)
    expected = sum(len(seed.table_rows(name)) for name in seed.table_order)
    actual = sum(len(rows) for rows in tables.values())
    if first_inserted != expected or second_inserted != 0 or actual != expected:
        raise SeedError(
            "幂等装载自检失败："
            f"首轮新增 {first_inserted}/跳过 {first_skipped}，"
            f"次轮新增 {second_inserted}/跳过 {second_skipped}，实际记录 {actual}，期望 {expected}"
        )
    return seed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="定期检验平台示例数据初始化/校验")
    parser.add_argument("command", choices=["init", "verify"], help="init=初始化并自检，verify=仅校验")
    parser.add_argument("--file", default=None, help="示例数据文件路径（默认取 APP_SEED_FILE）")
    args = parser.parse_args(argv)

    try:
        seed = run_check(args.file)
    except SeedError as exc:
        print(f"[基础数据] 失败：{exc}")
        return 1

    if args.command == "init":
        print(f"[基础数据] 初始化完成（幂等，可重复执行）：{_summary(seed)}")
    else:
        print(f"[基础数据] 校验通过：{_summary(seed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
