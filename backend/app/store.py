"""内存数据仓库：从同一份示例数据文件装载，可筛选、可流转、可重复初始化。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
示例数据的唯一事实来源是 data/seed.json（由 app.seed 校验并幂等合并），
本地开发与镜像部署读的是同一份文件，因此列表、概览看到的数据完全一致。
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.seed import SeedData, load_seed, merge_tables


class Store:
    def __init__(self, seed: SeedData | None = None) -> None:
        seed = seed or load_seed()
        self._seed = seed
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self.load_seed()

    def load_seed(self) -> tuple[int, int]:
        """（重新）装载示例数据；按「模块 + id」幂等合并，重复执行不产生重复记录。"""
        return merge_tables(self._tables, self._seed)

    def reload(self) -> tuple[int, int]:
        """从磁盘重新读取示例数据文件再装载（数据文件更新后使用）。"""
        self._seed = load_seed(settings.seed_file)
        self._tables = {}
        return merge_tables(self._tables, self._seed)

    def module_names(self) -> list[str]:
        """模块名按示例数据文件里声明的顺序返回，运营概览也用这个顺序。"""
        return list(self._seed.table_order)

    def module_label(self, name: str) -> str:
        return self._seed.module_labels.get(name, name)

    def inspect_categories(self) -> list[str]:
        return list(self._seed.inspect_categories)

    def inspect_agencies(self) -> list[str]:
        return list(self._seed.inspect_agencies)

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
                "label": self.module_label(name),
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
