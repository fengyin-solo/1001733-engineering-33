"""定期检验接口：维护检验任务，覆盖提交报检、确认出具、退回重检等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.inspect import InspectService

router = APIRouter(prefix="/api/inspect", tags=["定期检验"])

service = InspectService()

LIST_FIELDS = ["检验编号", "检验对象", "检验类别", "检验机构", "计划检验日", "检验人员", "检验日期", "检验状态"]
STATUSES = ["待报检", "检验中", "已出具", "已退回"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按检验编号检索"),
    status: str | None = Query(default=None, description="待报检、检验中、已出具、已退回"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按检验编号与状态过滤定期检验列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


# 注意：以下静态子路径必须声明在 /{entry_id} 之前，
# 否则 "export" 会被当成 entry_id 解析成 int，直接返回 422。
@router.get("/categories", response_model=PageResult[dict])
def list_categories() -> PageResult[dict]:
    """检验类别基础数据：上线即有值，无需手工补录。"""
    items = service.categories()
    return PageResult(items=items, total=len(items), page=1, size=len(items))


@router.get("/agencies", response_model=PageResult[dict])
def list_agencies() -> PageResult[dict]:
    """检验机构基础数据：上线即有值，无需手工补录。"""
    items = service.agencies()
    return PageResult(items=items, total=len(items), page=1, size=len(items))


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出定期检验清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "inspect", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条检验任务明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"检验任务 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条检验任务，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="检验任务已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条检验任务执行提交报检、确认出具、退回重检；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
