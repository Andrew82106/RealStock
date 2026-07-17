"""
股票数据 API 路由
"""
import asyncio
import json
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.data_engine.engine import DataEngine

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# 全局数据引擎实例
_data_engine: DataEngine | None = None


def get_data_engine() -> DataEngine:
    """获取数据引擎单例"""
    global _data_engine
    if _data_engine is None:
        _data_engine = DataEngine(cache_dir="./storage/stock_data")
    return _data_engine


class StockInfoResponse(BaseModel):
    """股票信息响应"""
    code: str
    name: str
    market: str


class DailyBarResponse(BaseModel):
    """日线数据响应"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class CacheRange(BaseModel):
    start: str
    end: str


class CacheStatusResponse(BaseModel):
    code: str
    name: str | None = None
    adjust: str
    complete: bool
    ranges: list[CacheRange]
    missing_ranges: list[CacheRange]
    row_count: int
    data_start: str | None = None
    data_end: str | None = None
    file_size: int
    updated_at: str | None = None


class CacheDownloadRequest(BaseModel):
    stock_codes: list[str]
    start_date: str
    end_date: str
    adjust: str = "qfq"


class CachePreflightResponse(BaseModel):
    ready: bool
    items: list[CacheStatusResponse]


@router.get("/", response_model=list[StockInfoResponse])
async def get_stock_list(
    keyword: str = Query(default="", description="搜索关键词")
):
    """
    获取股票列表
    
    - 支持按代码或名称搜索
    - 返回前 100 条结果
    """
    try:
        engine = get_data_engine()
        stocks = engine.get_stock_list()
        
        # 过滤搜索
        if keyword:
            keyword = keyword.lower()
            stocks = [
                s for s in stocks 
                if keyword in s.code.lower() or keyword in s.name.lower()
            ]
        
        # 限制返回数量
        stocks = stocks[:100]
        
        return [
            StockInfoResponse(code=s.code, name=s.name, market=s.market)
            for s in stocks
        ]
    except Exception as e:
        import traceback
        print(f"获取股票列表错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-stream")
async def search_stock_stream(
    keyword: str = Query(..., description="搜索关键词")
):
    """
    流式搜索股票（带进度）
    
    使用 SSE 推送搜索进度和结果
    """
    async def generate():
        try:
            engine = get_data_engine()
            
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': '开始搜索...'})}\n\n"
            await asyncio.sleep(0.01)
            
            # 获取股票列表（这是耗时操作）
            yield f"data: {json.dumps({'type': 'progress', 'progress': 10, 'message': '正在获取股票列表...'})}\n\n"
            await asyncio.sleep(0.01)
            
            stocks = engine.get_stock_list()
            total = len(stocks)
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 50, 'message': f'已获取 {total} 只股票，正在筛选...'})}\n\n"
            await asyncio.sleep(0.01)
            
            # 过滤搜索
            if keyword:
                keyword_lower = keyword.lower()
                matched = [
                    s for s in stocks 
                    if keyword_lower in s.code.lower() or keyword_lower in s.name.lower()
                ]
            else:
                matched = stocks
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 80, 'message': f'找到 {len(matched)} 只匹配股票'})}\n\n"
            await asyncio.sleep(0.01)
            
            # 限制返回数量
            matched = matched[:100]
            
            # 发送结果
            results = [
                {"code": s.code, "name": s.name, "market": s.market}
                for s in matched
            ]
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 100, 'message': '搜索完成'})}\n\n"
            yield f"data: {json.dumps({'type': 'result', 'data': results})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/cache", response_model=list[CacheStatusResponse])
async def list_daily_cache():
    """列出真实保存在后端磁盘上的日线缓存。"""
    return get_data_engine().list_daily_cache()


@router.post("/cache/preflight", response_model=CachePreflightResponse)
async def preflight_daily_cache(request: CacheDownloadRequest):
    """检查游戏日期范围是否已经全部缓存，不触发联网。"""
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
        items = [
            get_data_engine().get_cache_status(code, start, end, request.adjust)
            for code in request.stock_codes
        ]
        return CachePreflightResponse(
            ready=bool(items) and all(item["complete"] for item in items),
            items=items,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cache/download", response_model=CachePreflightResponse)
async def download_daily_cache(request: CacheDownloadRequest):
    """显式下载并持久化游戏所需的日线数据。"""
    try:
        if not request.stock_codes:
            raise ValueError("请至少选择一只股票")
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
        engine = get_data_engine()
        items = []
        for code in request.stock_codes:
            items.append(await asyncio.to_thread(
                engine.ensure_daily_cache, code, start, end, request.adjust
            ))
        return CachePreflightResponse(
            ready=all(item["complete"] for item in items),
            items=items,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/{code}/cache")
async def delete_daily_cache(
    code: str,
    adjust: str = Query(default="qfq", description="复权方式")
):
    """删除指定股票的本地日线缓存。"""
    try:
        deleted = get_data_engine().delete_daily_cache(code, adjust)
        if not deleted:
            raise HTTPException(status_code=404, detail="缓存不存在")
        return {"success": True, "code": code, "adjust": adjust}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{code}/daily", response_model=list[DailyBarResponse])
async def get_daily_data(
    code: str,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    cache_only: bool = Query(default=True, description="只读本地缓存")
):
    """
    获取股票日线数据
    
    - code: 股票代码，如 600519
    - start_date: 开始日期
    - end_date: 结束日期
    """
    try:
        engine = get_data_engine()
        
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        if cache_only:
            df = engine.get_cached_daily_data(code, start, end)
        else:
            df = engine.get_daily_data(code, start, end)
        
        if df.empty:
            return []
        
        result = []
        for _, row in df.iterrows():
            result.append(DailyBarResponse(
                date=row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            ))
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
