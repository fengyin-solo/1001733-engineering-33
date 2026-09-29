"""示例数据与基础数据：本地开发与镜像构建共用同一份 data/seed.json。

- 业务模块表：18 个模块，每个模块 3 条不同状态的示例记录。
- 基础数据表：inspect_categories（检验类别）、inspect_agencies（检验机构），
  定期检验记录里的检验类别/检验机构引用这两张表。

装载走 :meth:`upsert`：同一张表按 id 命中即更新、缺失才插入，
因此重复装载（容器重启、反复执行 init）不会产生重复记录。

命令行：
    python -m app.seed check   # 只校验：JSON 可解析、id 唯一、基础数据引用完整
    python -m app.seed load    # 装载进内存仓库，连续装载两遍以验证幂等
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed.json"

# 运营概览统计的业务模块，顺序与历史 sorted(表名) 结果保持一致。
BUSINESS_MODULES = [
    "boiler", "contract", "crane", "elevator", "forklift", "hazard",
    "inspect", "lubricate", "operator", "plan", "pressurepipe",
    "rectify", "register", "report", "settle", "spare", "spotcheck",
    "vessel",
]

# 基础数据：不属于业务模块，不计入运营概览的模块数。
CATEGORY_TABLE = "inspect_categories"
AGENCY_TABLE = "inspect_agencies"
BASE_TABLES = (CATEGORY_TABLE, AGENCY_TABLE)

# 定期检验记录 -> 基础数据表的引用关系：字段值必须在对应基础表中存在。
FOREIGN_KEYS = {
    "inspect": {
        "检验类别": (CATEGORY_TABLE, "类别名称"),
        "检验机构": (AGENCY_TABLE, "机构名称"),
    },
}


class SeedError(RuntimeError):
    """种子数据不可用时抛出：消息直接说明卡在哪一步。"""


def load_seed_rows(path: Path = SEED_FILE) -> dict[str, list[dict[str, Any]]]:
    """读取并解析种子文件；文件缺失或 JSON 非法时给出可读说明。"""
    if not path.exists():
        raise SeedError(f"基础数据初始化失败：找不到种子文件 {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError(f"基础数据初始化失败：{path} 不是合法 JSON（第 {exc.lineno} 行第 {exc.colno} 列）") from exc
    if not isinstance(data, dict):
        raise SeedError(f"基础数据初始化失败：{path} 顶层必须是表名到记录列表的映射")
    for table, rows in data.items():
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise SeedError(f"基础数据初始化失败：表 {table} 必须是对象记录的列表")
    return data


def validate(rows: dict[str, list[dict[str, Any]]]) -> list[str]:
    """结构性校验，返回问题说明列表；空列表表示通过。

    - 每张表的 id 必须存在且在表内唯一（幂等装载按 id 判重）；
    - 定期检验引用的检验类别、检验机构必须存在于基础数据表中。
    """
    problems: list[str] = []
    for table, table_rows in rows.items():
        seen: set[int] = set()
        for index, row in enumerate(table_rows, start=1):
            try:
                row_id = int(row["id"])
            except (KeyError, TypeError, ValueError):
                problems.append(f"表 {table} 第 {index} 行缺少合法 id，无法做幂等判重")
                continue
            if row_id in seen:
                problems.append(f"表 {table} 存在重复 id={row_id}，重复装载会产生重复记录")
            seen.add(row_id)
    for table, refs in FOREIGN_KEYS.items():
        for field, (ref_table, ref_column) in refs.items():
            allowed = {str(row.get(ref_column)) for row in rows.get(ref_table, [])}
            if not allowed:
                problems.append(f"基础数据表 {ref_table} 为空，{table}.{field} 无可引用的值")
                continue
            for row in rows.get(table, []):
                value = str(row.get(field) or "").strip()
                if value and value not in allowed:
                    problems.append(
                        f"表 {table} id={row.get('id')} 的{field}「{value}」"
                        f"不在基础数据 {ref_table}.{ref_column} 中"
                    )
    return problems


def upsert(
    table_rows: list[dict[str, Any]],
    seed_rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """把一个表的种子记录幂等写进 table_rows，返回 (新增数, 更新数)。

    已有 id 的记录原地更新但不新增行，缺失的 id 才插入，
    因此同一批种子连续装载任意次数，行数都不变。
    """
    index_by_id = {int(row["id"]): row for row in table_rows if "id" in row}
    inserted = updated = 0
    for seed in seed_rows:
        row_id = int(seed["id"])
        existing = index_by_id.get(row_id)
        if existing is None:
            table_rows.append(dict(seed))
            index_by_id[row_id] = table_rows[-1]
            inserted += 1
        else:
            existing.update(seed)
            updated += 1
    return inserted, updated


# 模块加载即解析：种子文件是构建期就准备好的产物，缺失时应直接报错，
# 而不是让服务在空数据状态下悄悄启动。
SEED_ROWS: dict[str, list[dict[str, Any]]] = load_seed_rows()


def _cmd_check() -> int:
    rows = load_seed_rows()
    problems = validate(rows)
    if problems:
        for problem in problems:
            print(f"[seed] ✗ {problem}")
        print(f"[seed] 校验未通过，共 {len(problems)} 个问题，请先修正 {SEED_FILE}")
        return 1
    business = sum(len(rows.get(name, [])) for name in BUSINESS_MODULES)
    print(
        f"[seed] ✓ 校验通过：{len(BUSINESS_MODULES)} 个业务模块共 {business} 条示例记录，"
        f"{len(BASE_TABLES)} 张基础数据表"
    )
    for table in BASE_TABLES:
        print(f"[seed]   - {table}: {len(rows.get(table, []))} 条")
    return 0


def _cmd_load() -> int:
    """装载进内存仓库；第二遍必须零新增，以此自检幂等性。"""
    from app.store import store

    rows = load_seed_rows()
    problems = validate(rows)
    if problems:
        for problem in problems:
            print(f"[seed] ✗ {problem}")
        return 1
    totals_inserted = 0
    for pass_no in (1, 2):
        totals_inserted = 0
        for table, table_rows in rows.items():
            inserted, _updated = upsert(store.rows(table), table_rows)
            totals_inserted += inserted
        if pass_no == 1:
            print("[seed] 第一遍装载完成，再装载一遍验证幂等……")
    if totals_inserted:
        print(f"[seed] ✗ 第二遍仍新增 {totals_inserted} 条，装载不是幂等的")
        return 1
    print(f"[seed] ✓ 基础数据已就绪：{len(BUSINESS_MODULES)} 个业务模块、{len(BASE_TABLES)} 张基础数据表，重复装载无新增")
    return 0


_COMMANDS: dict[str, Callable[[], int]] = {
    "check": _cmd_check,
    "load": _cmd_load,
}


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    handler = _COMMANDS.get(command)
    if handler is None:
        print(f"[seed] 未知命令：{command}，可用命令：{', '.join(_COMMANDS)}")
        return 2
    try:
        return handler()
    except SeedError as exc:
        print(f"[seed] ✗ {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
