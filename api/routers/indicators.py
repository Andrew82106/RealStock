"""指标工坊 API。"""

import asyncio
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routers.stocks import get_data_engine
from api.services.indicator_service import (
    IndicatorNotFoundError,
    IndicatorService,
    IndicatorValidationError,
)


router = APIRouter(prefix="/api/indicators", tags=["indicators"])
service = IndicatorService()


class IndicatorComponent(BaseModel):
    metric: str
    window: int = Field(ge=2, le=250)
    weight: float = Field(ge=-20, le=20)


class IndicatorDefinition(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    version: int = 1
    language: str = "python"
    code: str = ""
    components: list[IndicatorComponent] = Field(default_factory=list)
    buy_threshold: float = 1
    sell_threshold: float = -1
    builtin: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class IndicatorPreviewRequest(BaseModel):
    code: str
    start_date: str
    end_date: str
    indicator_id: str | None = None
    definition: IndicatorDefinition | None = None


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


@router.get("")
async def list_indicators():
    return service.list()


@router.get("/{indicator_id}")
async def get_indicator(indicator_id: str):
    try:
        return service.get(indicator_id)
    except IndicatorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("")
async def save_indicator(definition: IndicatorDefinition):
    try:
        return service.save(_dump(definition))
    except IndicatorValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{indicator_id}")
async def update_indicator(indicator_id: str, definition: IndicatorDefinition):
    try:
        payload = _dump(definition)
        payload["id"] = indicator_id
        return service.save(payload)
    except IndicatorValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: str):
    try:
        if not service.delete(indicator_id):
            raise HTTPException(status_code=404, detail="指标不存在")
        return {"success": True}
    except IndicatorValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/preview/calculate")
async def preview_indicator(request: IndicatorPreviewRequest):
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
        if request.definition is not None:
            definition = _dump(request.definition)
        elif request.indicator_id:
            definition = service.get(request.indicator_id)
        else:
            raise IndicatorValidationError("请选择已保存指标或提交指标定义")

        frame = get_data_engine().get_cached_daily_data(request.code, start, end)
        return {
            "definition": service.validate(definition),
            "values": await asyncio.to_thread(service.compute, definition, frame),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {exc}")
    except IndicatorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IndicatorValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc))
