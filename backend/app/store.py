"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
示例数据与基础数据统一来自 app.seed（data/seed.json），启动时通过
:func:`app.seed.upsert` 幂等装载：同一进程内重新初始化或反复调用装载命令，
都不会产生重复记录。基础数据表（检验类别、检验机构）不进入运营概览。
"""
from __future__ import annotations

from typing import Any

from app.seed import BUSINESS_MODULES, SEED_ROWS, upsert


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self.load_seed()

    def load_seed(self) -> None:
        """按 id 幂等装载种子数据：已有记录更新，缺失记录插入。"""
        for name, rows in SEED_ROWS.items():
            upsert(self.rows(name), rows)

    def module_names(self) -> list[str]:
        return sorted(name for name in BUSINESS_MODULES if name in self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
