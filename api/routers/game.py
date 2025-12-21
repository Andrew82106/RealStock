"""
游戏控制 API 路由
"""
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.session import session_manager
from api.services.save_service import SaveService, SaveNotFoundError
from src.playback.models import PlaybackState
from src.trading.models import OrderStatus
from src.account.models import Position

router = APIRouter(prefix="/api/game", tags=["game"])

# 全局存档服务实例
_save_service: SaveService | None = None


def get_save_service() -> SaveService:
    """获取存档服务单例"""
    global _save_service
    if _save_service is None:
        _save_service = SaveService(storage_dir="./storage")
    return _save_service


class GameStartRequest(BaseModel):
    """开始游戏请求"""
    stock_codes: list[str]
    start_date: str
    end_date: str
    initial_cash: float = 100000.0


class GameStartResponse(BaseModel):
    """开始游戏响应"""
    session_id: str
    current_date: str
    trading_dates: list[str]


class OrderRequest(BaseModel):
    """订单请求"""
    session_id: str
    code: str
    price: float
    quantity: int


class OrderResponse(BaseModel):
    """订单响应"""
    success: bool
    order_id: str | None = None
    message: str
    fee: float | None = None


class PositionResponse(BaseModel):
    """持仓响应"""
    code: str
    quantity: int
    cost_price: float
    current_price: float
    profit_loss: float
    profit_loss_pct: float
    buy_date: str | None = None  # 买入日期，用于T+1判断


class AccountResponse(BaseModel):
    """账户响应"""
    cash: float
    total_assets: float
    total_market_value: float
    positions: list[PositionResponse]


class MetricsResponse(BaseModel):
    """绩效指标响应"""
    total_return: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int


class GameStateResponse(BaseModel):
    """游戏状态响应"""
    session_id: str
    current_date: str
    playback_state: str
    is_last_day: bool


@router.post("/start", response_model=GameStartResponse)
async def start_game(request: GameStartRequest):
    """开始新游戏"""
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
        
        session = session_manager.create_session(
            stock_codes=request.stock_codes,
            start_date=start,
            end_date=end,
            initial_cash=request.initial_cash
        )
        
        # 加载第一天
        session.simulator.start_day()
        
        return GameStartResponse(
            session_id=session.session_id,
            current_date=session.simulator.current_date.isoformat(),
            trading_dates=[d.isoformat() for d in session.simulator.trading_dates]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StartFromSaveRequest(BaseModel):
    """从存档开始游戏请求"""
    save_id: str


class StartFromSaveResponse(BaseModel):
    """从存档开始游戏响应"""
    session_id: str
    save_id: str
    current_date: str
    trading_dates: list[str]
    stock_codes: list[str]


@router.post("/start-from-save", response_model=StartFromSaveResponse)
async def start_game_from_save(request: StartFromSaveRequest):
    """从存档开始游戏
    
    加载存档数据并创建游戏会话。如果存档没有股票，返回空会话。
    """
    try:
        save_service = get_save_service()
        save_data = save_service.load_save(request.save_id)
        
        stock_codes = save_data.stock_codes
        initial_cash = save_data.config.initial_cash
        
        # 如果存档没有股票，创建一个空会话
        if not stock_codes:
            # 创建一个空的会话，只有账户信息
            session_id = f"save_{request.save_id}"
            return StartFromSaveResponse(
                session_id=session_id,
                save_id=request.save_id,
                current_date=save_data.game_state.current_date or "",
                trading_dates=[],
                stock_codes=[]
            )
        
        # 确定日期范围
        # 如果存档有当前日期，从当前日期开始；否则使用默认范围
        if save_data.game_state.current_date:
            start = date.fromisoformat(save_data.game_state.current_date)
        else:
            # 默认从6个月前开始
            start = date.today() - timedelta(days=180)
        
        # 结束日期：从开始日期往后1年
        end = start + timedelta(days=365)
        
        # 创建会话
        session = session_manager.create_session(
            stock_codes=stock_codes,
            start_date=start,
            end_date=end,
            initial_cash=initial_cash
        )
        
        # 恢复账户状态
        if save_data.account.cash != initial_cash:
            session.simulator.account.cash = save_data.account.cash
        
        # 恢复持仓
        for pos in save_data.account.positions:
            session.simulator.account.positions[pos["code"]] = Position(
                code=pos["code"],
                quantity=pos["quantity"],
                cost_price=pos["cost_price"],
                current_price=pos.get("current_price", pos["cost_price"]),
                buy_date=date.today(),  # 使用当前日期作为默认买入日期
            )
        
        # 恢复挂单
        from src.trading.models import Order, OrderType, OrderStatus
        for pending in save_data.pending_orders:
            order = Order(
                code=pending.code,
                order_type=OrderType.BUY if pending.order_type == "buy" else OrderType.SELL,
                price=pending.price,
                quantity=pending.quantity,
                order_date=date.fromisoformat(pending.order_date) if pending.order_date else session.simulator.current_date,
                status=OrderStatus.PENDING,
                order_id=pending.order_id,
                frozen_cash=pending.frozen_cash,
                frozen_quantity=pending.frozen_quantity,
            )
            session.simulator.trading_engine.pending_orders.append(order)
        
        # 加载第一天
        session.simulator.start_day()
        
        return StartFromSaveResponse(
            session_id=session.session_id,
            save_id=request.save_id,
            current_date=session.simulator.current_date.isoformat(),
            trading_dates=[d.isoformat() for d in session.simulator.trading_dates],
            stock_codes=stock_codes
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/state", response_model=GameStateResponse)
async def get_game_state(session_id: str):
    """获取游戏状态"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    is_last = sim.date_index >= len(sim.trading_dates) - 1
    
    return GameStateResponse(
        session_id=session_id,
        current_date=sim.current_date.isoformat() if sim.current_date else "",
        playback_state=sim.playback_engine.state.value,
        is_last_day=is_last
    )


@router.get("/{session_id}/account", response_model=AccountResponse)
async def get_account(session_id: str):
    """获取账户状态"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    account = session.simulator.account
    
    positions = []
    for code, pos in account.positions.items():
        positions.append(PositionResponse(
            code=pos.code,
            quantity=pos.quantity,
            cost_price=pos.cost_price,
            current_price=pos.current_price,
            profit_loss=pos.profit_loss,
            profit_loss_pct=pos.profit_loss_pct,
            buy_date=pos.buy_date.isoformat() if pos.buy_date else None
        ))
    
    return AccountResponse(
        cash=account.cash,
        total_assets=account.total_assets,
        total_market_value=account.total_market_value,
        positions=positions
    )


@router.post("/buy", response_model=OrderResponse)
async def buy_stock(request: OrderRequest):
    """买入股票（挂单模式）"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    
    try:
        order = sim.buy(request.code, request.price, request.quantity)
        
        if order.status == OrderStatus.FILLED:
            return OrderResponse(
                success=True,
                order_id=order.order_id,
                message="买入成功",
                fee=order.fee
            )
        elif order.status == OrderStatus.PENDING:
            return OrderResponse(
                success=True,
                order_id=order.order_id,
                message="挂单成功，等待成交",
                fee=order.fee
            )
        else:
            return OrderResponse(
                success=False,
                order_id=order.order_id,
                message=order.reject_reason or "订单被拒绝"
            )
    except Exception as e:
        return OrderResponse(success=False, message=str(e))


@router.post("/sell", response_model=OrderResponse)
async def sell_stock(request: OrderRequest):
    """卖出股票（挂单模式）"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    
    try:
        order = sim.sell(request.code, request.price, request.quantity)
        
        if order.status == OrderStatus.FILLED:
            return OrderResponse(
                success=True,
                order_id=order.order_id,
                message="卖出成功",
                fee=order.fee
            )
        elif order.status == OrderStatus.PENDING:
            return OrderResponse(
                success=True,
                order_id=order.order_id,
                message="挂单成功，等待成交",
                fee=order.fee
            )
        else:
            return OrderResponse(
                success=False,
                order_id=order.order_id,
                message=order.reject_reason or "订单被拒绝"
            )
    except Exception as e:
        return OrderResponse(success=False, message=str(e))


class CancelOrderRequest(BaseModel):
    """撤单请求"""
    session_id: str
    order_id: str


@router.post("/cancel", response_model=OrderResponse)
async def cancel_order(request: CancelOrderRequest):
    """撤销挂单"""
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    success = session.simulator.cancel_order(request.order_id)
    
    if success:
        return OrderResponse(
            success=True,
            order_id=request.order_id,
            message="撤单成功"
        )
    else:
        return OrderResponse(
            success=False,
            order_id=request.order_id,
            message="撤单失败，订单不存在或已成交"
        )


class PendingOrderResponse(BaseModel):
    """挂单响应"""
    order_id: str
    code: str
    order_type: str
    price: float
    quantity: int
    frozen_cash: float
    frozen_quantity: int


@router.get("/{session_id}/pending-orders")
async def get_pending_orders(session_id: str):
    """获取所有挂单"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    orders = session.simulator.get_pending_orders()
    
    return [
        PendingOrderResponse(
            order_id=o.order_id,
            code=o.code,
            order_type=o.order_type.value,
            price=o.price,
            quantity=o.quantity,
            frozen_cash=o.frozen_cash,
            frozen_quantity=o.frozen_quantity
        )
        for o in orders
    ]


class TradeHistoryResponse(BaseModel):
    """交易历史响应"""
    order_id: str
    code: str
    order_type: str
    price: float
    quantity: int
    status: str
    filled_price: float | None = None
    filled_quantity: int | None = None
    fee: float
    order_date: str
    reject_reason: str | None = None


@router.get("/{session_id}/trade-history")
async def get_trade_history(session_id: str):
    """获取交易历史（已成交和已拒绝的订单）"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    history = session.simulator.trading_engine.get_trade_history()
    
    return [
        TradeHistoryResponse(
            order_id=o.order_id,
            code=o.code,
            order_type=o.order_type.value,
            price=o.price,
            quantity=o.quantity,
            status=o.status.value,
            filled_price=o.filled_price,
            filled_quantity=o.filled_quantity,
            fee=o.fee,
            order_date=o.order_date.isoformat(),
            reject_reason=o.reject_reason
        )
        for o in history
    ]


@router.post("/{session_id}/next-day", response_model=GameStateResponse)
async def next_day(session_id: str):
    """进入下一交易日"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    
    # 记录当天结束时的资产快照
    session.record_daily_snapshot()
    
    has_next = sim.next_day()
    if has_next:
        sim.start_day()
    
    is_last = sim.date_index >= len(sim.trading_dates) - 1
    
    return GameStateResponse(
        session_id=session_id,
        current_date=sim.current_date.isoformat() if sim.current_date else "",
        playback_state=sim.playback_engine.state.value,
        is_last_day=is_last or not has_next
    )


@router.get("/{session_id}/metrics", response_model=MetricsResponse)
async def get_metrics(session_id: str):
    """获取绩效指标"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    metrics = session.simulator.calculate_metrics()
    
    return MetricsResponse(
        total_return=metrics.total_return,
        max_drawdown=metrics.max_drawdown,
        win_rate=metrics.win_rate,
        sharpe_ratio=metrics.sharpe_ratio,
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades
    )


class DailySnapshotResponse(BaseModel):
    """每日快照响应"""
    date: str
    total_assets: float
    cash: float
    market_value: float
    daily_return: float
    daily_profit: float
    cumulative_return: float


class AssetHistoryResponse(BaseModel):
    """资产历史响应"""
    initial_cash: float
    current_assets: float
    total_return: float
    history: list[DailySnapshotResponse]


@router.get("/{session_id}/asset-history", response_model=AssetHistoryResponse)
async def get_asset_history(session_id: str):
    """获取资产历史记录"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    account = session.simulator.account
    current_assets = account.total_assets
    total_return = (current_assets - session.initial_cash) / session.initial_cash if session.initial_cash > 0 else 0
    
    history = [
        DailySnapshotResponse(
            date=s.date,
            total_assets=s.total_assets,
            cash=s.cash,
            market_value=s.market_value,
            daily_return=s.daily_return,
            daily_profit=s.daily_profit,
            cumulative_return=s.cumulative_return
        )
        for s in session.asset_history
    ]
    
    return AssetHistoryResponse(
        initial_cash=session.initial_cash,
        current_assets=current_assets,
        total_return=total_return,
        history=history
    )


@router.get("/{session_id}/bars")
async def get_current_bars(session_id: str):
    """获取当前日期的行情数据"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    bars = session.simulator.get_current_bars()
    
    result = {}
    for code, bar in bars.items():
        result[code] = {
            "date": bar.date.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        }
    
    return result


class PlaybackControlRequest(BaseModel):
    """播放控制请求"""
    speed: float = 10.0


@router.post("/{session_id}/pause")
async def pause_playback(session_id: str):
    """暂停播放（HTTP 备用接口）"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    
    # 取消 WebSocket 播放任务（如果有）
    from api.routers.websocket import manager
    manager.cancel_playback(session_id)
    
    # 强制设置为暂停状态（无论当前是什么状态）
    if sim.playback_engine.state == PlaybackState.PLAYING:
        sim.pause()
    elif sim.playback_engine.state == PlaybackState.IDLE:
        # IDLE 状态也可以暂停（用于交易）
        sim.playback_engine.state = PlaybackState.PAUSED
    # DAY_ENDED 和 FINISHED 状态保持不变
    
    return {
        "success": True,
        "playback_state": sim.playback_engine.state.value
    }


@router.post("/{session_id}/play")
async def start_playback(session_id: str, request: PlaybackControlRequest):
    """开始播放（HTTP 备用接口，仅设置状态，实际播放需要 WebSocket）"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    sim.play(request.speed)
    
    return {
        "success": True,
        "playback_state": sim.playback_engine.state.value
    }


@router.post("/{session_id}/tick")
async def single_tick(session_id: str):
    """执行单个 tick（HTTP 接口）"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    sim = session.simulator
    
    # 如果是 IDLE 状态，先切换到 PLAYING
    if sim.playback_engine.state == PlaybackState.IDLE:
        sim.playback_engine.state = PlaybackState.PLAYING
    
    # 执行一个 tick
    tick_data = sim.playback_engine.tick()
    
    # 获取当前日期
    current_date = sim.current_date.isoformat() if sim.current_date else ""
    
    if tick_data:
        prices = {code: tick.price for code, tick in tick_data.items()}
        sim.account.update_prices(prices)
        
        return {
            "success": True,
            "tick_index": sim.playback_engine.current_tick_index,
            "prices": prices,
            "playback_state": sim.playback_engine.state.value,
            "current_date": current_date,
        }
    
    return {
        "success": False,
        "playback_state": sim.playback_engine.state.value,
        "current_date": current_date,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除游戏会话"""
    if session_manager.delete_session(session_id):
        return {"message": "会话已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/{session_id}/exists")
async def check_session_exists(session_id: str):
    """检查会话是否存在且有效"""
    session = session_manager.get_session(session_id)
    if session:
        return {
            "exists": True,
            "session_id": session_id,
            "current_date": session.simulator.current_date.isoformat() if session.simulator.current_date else "",
            "stock_codes": session.stock_codes,
        }
    return {"exists": False}
