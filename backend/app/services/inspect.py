"""定期检验业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "inspect"
REQUIRED_FIELDS = ["检验编号", "检验对象", "检验类别"]
STATUS_ORDER = ["待报检", "检验中", "已出具", "已退回"]
ACTION_RULES = {"提交报检": "检验中", "确认出具": "已出具", "退回重检": "已退回"}
NEGATIVE_ACTIONS = []


class InspectService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("检验编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if category:
            rows = [row for row in rows if row.get("检验类别") == category]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str] | str]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        category = str(values.get("检验类别") or "").strip()
        if category and category not in store.inspect_categories():
            return None, f"检验类别「{category}」不在基础数据里，请从 /api/inspect/categories 选取"
        agency = str(values.get("检验机构") or "").strip()
        if agency and agency not in store.inspect_agencies():
            return None, f"检验机构「{agency}」不在基础数据里，请从 /api/inspect/agencies 选取"
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        if agency:
            entry["检验机构"] = agency
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"检验任务 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于定期检验可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"检验任务已{action}"
