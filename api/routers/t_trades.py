"""
做T统计 API 路由 - T-Trade Statistics API Routes
Requirements: 9.1-9.6
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from api.services.t_trade_service import t_trade_service
from api.services.t_trade_models import TTradeStatistics, TTradeRecord
from api.services.save_service import SaveService, SaveNotFoundError

router = APIRouter(prefix="/api/t-trades", tags=["t-trades"])

# 全局存档服务实例
_save_service: SaveService | None = None


def get_save_service() -> SaveService:
    """获取存档服务单例"""
    global _save_service
    if _save_service is None:
        _save_service = SaveService(storage_dir="./storage")
    return _save_service


# Response Models
class TTradeRecordResponse(BaseModel):
    """做T记录响应"""
    id: str
    stock_code: str
    sell_price: float
    buy_price: float
    quantity: int
    sell_fee: float
    buy_fee: float
    profit: float
    trade_date: str
    sell_time: str
    buy_time: str
    is_successful: bool


class TTradeStatisticsResponse(BaseModel):
    """做T统计响应"""
    total_trades: int
    successful_trades: int
    failed_trades: int
    success_rate: float
    total_profit: float
    total_fees: float
    best_trade_profit: float
    worst_trade_loss: float
    average_profit: float


class TTradeHistoryResponse(BaseModel):
    """做T历史响应"""
    statistics: TTradeStatisticsResponse
    trades: list[TTradeRecordResponse]


# API Endpoints
@router.get("/{save_id}/statistics", response_model=TTradeStatisticsResponse)
async def get_t_trade_statistics(save_id: str):
    """
    获取做T统计数据
    
    - save_id: 存档ID
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 如果存档有缓存的统计数据，直接返回
        if save_data.t_trade_statistics:
            stats = save_data.t_trade_statistics
        else:
            # 否则从交易历史重新计算
            stats = t_trade_service.calculate_statistics_from_save(save_data)
            # 更新缓存
            save_data.t_trade_statistics = stats
            service.update_save(save_id, save_data)
        
        return TTradeStatisticsResponse(
            total_trades=stats.total_trades,
            successful_trades=stats.successful_trades,
            failed_trades=stats.failed_trades,
            success_rate=stats.success_rate,
            total_profit=stats.total_profit,
            total_fees=stats.total_fees,
            best_trade_profit=stats.best_trade_profit,
            worst_trade_loss=stats.worst_trade_loss,
            average_profit=stats.average_profit,
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{save_id}/history", response_model=TTradeHistoryResponse)
async def get_t_trade_history(save_id: str, limit: int = 100):
    """
    获取做T历史记录
    
    - save_id: 存档ID
    - limit: 返回记录数量限制，默认100
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 获取或计算统计数据
        if save_data.t_trade_statistics:
            stats = save_data.t_trade_statistics
        else:
            stats = t_trade_service.calculate_statistics_from_save(save_data)
            save_data.t_trade_statistics = stats
            service.update_save(save_id, save_data)
        
        # 限制返回数量
        trades = stats.trades[:limit]
        
        return TTradeHistoryResponse(
            statistics=TTradeStatisticsResponse(
                total_trades=stats.total_trades,
                successful_trades=stats.successful_trades,
                failed_trades=stats.failed_trades,
                success_rate=stats.success_rate,
                total_profit=stats.total_profit,
                total_fees=stats.total_fees,
                best_trade_profit=stats.best_trade_profit,
                worst_trade_loss=stats.worst_trade_loss,
                average_profit=stats.average_profit,
            ),
            trades=[
                TTradeRecordResponse(
                    id=t.id,
                    stock_code=t.stock_code,
                    sell_price=t.sell_price,
                    buy_price=t.buy_price,
                    quantity=t.quantity,
                    sell_fee=t.sell_fee,
                    buy_fee=t.buy_fee,
                    profit=t.profit,
                    trade_date=t.trade_date,
                    sell_time=t.sell_time,
                    buy_time=t.buy_time,
                    is_successful=t.is_successful,
                )
                for t in trades
            ],
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{save_id}/recalculate", response_model=TTradeStatisticsResponse)
async def recalculate_t_trade_statistics(save_id: str):
    """
    重新计算做T统计数据
    
    - save_id: 存档ID
    
    从交易历史重新检测和计算做T统计
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 强制重新计算
        stats = t_trade_service.calculate_statistics_from_save(save_data)
        
        # 更新缓存
        save_data.t_trade_statistics = stats
        service.update_save(save_id, save_data)
        
        return TTradeStatisticsResponse(
            total_trades=stats.total_trades,
            successful_trades=stats.successful_trades,
            failed_trades=stats.failed_trades,
            success_rate=stats.success_rate,
            total_profit=stats.total_profit,
            total_fees=stats.total_fees,
            best_trade_profit=stats.best_trade_profit,
            worst_trade_loss=stats.worst_trade_loss,
            average_profit=stats.average_profit,
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
