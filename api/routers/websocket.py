"""
WebSocket 播放服务路由 - 带详细日志
"""
import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.session import session_manager
from src.playback.models import PlaybackState

router = APIRouter(tags=["websocket"])

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 写入本地日志文件
file_handler = logging.FileHandler('websocket_debug.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


def log(msg: str):
    """写入日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    log_msg = f"[{timestamp}] {msg}"
    logger.info(log_msg)
    print(log_msg)  # 同时打印到控制台


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.playback_tasks: dict[str, asyncio.Task] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        log(f"WebSocket CONNECTED: {session_id}")
    
    def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.playback_tasks:
            self.playback_tasks[session_id].cancel()
            del self.playback_tasks[session_id]
        log(f"WebSocket DISCONNECTED: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """发送消息"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
                log(f"SENT to {session_id}: {message.get('type')} - {json.dumps(message.get('data', {}))[:100]}")
            except Exception as e:
                log(f"SEND ERROR to {session_id}: {e}")
    
    def cancel_playback(self, session_id: str):
        """取消播放任务"""
        if session_id in self.playback_tasks:
            log(f"CANCELLING playback task for {session_id}")
            self.playback_tasks[session_id].cancel()
            del self.playback_tasks[session_id]


manager = ConnectionManager()


@router.websocket("/ws/playback/{session_id}")
async def playback_websocket(websocket: WebSocket, session_id: str):
    """WebSocket 播放端点"""
    log(f"WebSocket CONNECTING: {session_id}")
    
    session = session_manager.get_session(session_id)
    if not session:
        log(f"Session NOT FOUND: {session_id}")
        await websocket.close(code=4004, reason="会话不存在")
        return

    if session.simulator.daily_mode:
        await websocket.close(code=4009, reason="日线模式不提供分时 WebSocket")
        return
    
    await manager.connect(session_id, websocket)
    
    try:
        # 发送初始状态
        await send_state_update(session_id, session)
        
        while True:
            # 接收客户端消息
            log(f"WAITING for message from {session_id}...")
            data = await websocket.receive_text()
            message = json.loads(data)
            log(f"RECEIVED from {session_id}: {message}")
            
            action = message.get("action")
            
            if action == "play":
                speed = message.get("speed", 10.0)
                log(f"ACTION: play, speed={speed}")
                manager.cancel_playback(session_id)
                task = asyncio.create_task(playback_loop(session_id, session, speed))
                manager.playback_tasks[session_id] = task
                log(f"Playback task CREATED for {session_id}")
            
            elif action == "pause":
                log(f"ACTION: pause")
                await handle_pause(session_id, session)
            
            elif action == "tick":
                log(f"ACTION: tick")
                await handle_tick(session_id, session)
            
            elif action == "get_state":
                log(f"ACTION: get_state")
                await send_state_update(session_id, session)
    
    except WebSocketDisconnect:
        log(f"WebSocket DISCONNECT (client closed): {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        log(f"WebSocket ERROR: {session_id} - {e}")
        import traceback
        traceback.print_exc()
        try:
            await manager.send_message(session_id, {
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass
        manager.disconnect(session_id)


async def playback_loop(session_id: str, session, speed: float):
    """播放循环"""
    sim = session.simulator
    sim.playback_engine.set_speed(speed)
    sim.play(speed)
    
    log(f"PLAYBACK STARTED: state={sim.playback_engine.state.value}")
    
    await manager.send_message(session_id, {
        "type": "state_change",
        "data": {"playback_state": sim.playback_engine.state.value}
    })
    
    try:
        tick_count = 0
        while sim.playback_engine.state == PlaybackState.PLAYING:
            tick_data = sim.playback_engine.tick()
            tick_count += 1
            
            if tick_data:
                prices = {code: tick.price for code, tick in tick_data.items()}
                sim.account.update_prices(prices)
                
                # 检查挂单是否可以成交
                filled_orders = sim.check_pending_orders(prices, sim.current_date)
                if filled_orders:
                    for order in filled_orders:
                        await manager.send_message(session_id, {
                            "type": "order_filled",
                            "data": {
                                "order_id": order.order_id,
                                "code": order.code,
                                "order_type": order.order_type.value,
                                "filled_price": order.filled_price,
                                "filled_quantity": order.filled_quantity,
                                "fee": order.fee
                            }
                        })
                
                await manager.send_message(session_id, {
                    "type": "tick",
                    "data": {
                        "tick_index": sim.playback_engine.current_tick_index,
                        "prices": prices,
                        "current_date": sim.current_date.isoformat() if sim.current_date else ""
                    }
                })
                
                await send_account_update(session_id, session)
            
            if sim.playback_engine.state == PlaybackState.DAY_ENDED:
                log(f"DAY ENDED after {tick_count} ticks")
                await manager.send_message(session_id, {
                    "type": "day_end",
                    "data": {"date": sim.current_date.isoformat()}
                })
                break
            
            await asyncio.sleep(0.1 / speed)
        
        log(f"PLAYBACK LOOP ENDED: state={sim.playback_engine.state.value}, ticks={tick_count}")
        await send_state_update(session_id, session)
        
    except asyncio.CancelledError:
        log(f"PLAYBACK CANCELLED for {session_id}")
    except Exception as e:
        log(f"PLAYBACK ERROR: {e}")
        import traceback
        traceback.print_exc()


async def handle_pause(session_id: str, session):
    """处理暂停"""
    log(f"PAUSE HANDLER called for {session_id}")
    
    manager.cancel_playback(session_id)
    
    sim = session.simulator
    old_state = sim.playback_engine.state.value
    sim.pause()
    new_state = sim.playback_engine.state.value
    
    log(f"PAUSE: state changed from {old_state} to {new_state}")
    
    await manager.send_message(session_id, {
        "type": "state_change",
        "data": {"playback_state": new_state}
    })
    
    await send_state_update(session_id, session)


async def handle_tick(session_id: str, session):
    """处理单步"""
    sim = session.simulator
    
    if sim.playback_engine.state not in (PlaybackState.PLAYING, PlaybackState.PAUSED, PlaybackState.IDLE):
        return
    
    original_state = sim.playback_engine.state
    if original_state == PlaybackState.IDLE:
        sim.playback_engine.state = PlaybackState.PLAYING
    
    tick_data = sim.playback_engine.tick()
    
    if tick_data:
        prices = {code: tick.price for code, tick in tick_data.items()}
        sim.account.update_prices(prices)
        
        await manager.send_message(session_id, {
            "type": "tick",
            "data": {
                "tick_index": sim.playback_engine.current_tick_index,
                "prices": prices
            }
        })
        
        await send_account_update(session_id, session)
    
    if sim.playback_engine.state == PlaybackState.DAY_ENDED:
        await manager.send_message(session_id, {
            "type": "day_end",
            "data": {"date": sim.current_date.isoformat()}
        })
    
    await send_state_update(session_id, session)


async def send_state_update(session_id: str, session):
    """发送状态更新"""
    sim = session.simulator
    is_last = sim.date_index >= len(sim.trading_dates) - 1
    
    state_data = {
        "current_date": sim.current_date.isoformat() if sim.current_date else "",
        "playback_state": sim.playback_engine.state.value,
        "tick_index": sim.playback_engine.current_tick_index,
        "is_last_day": is_last
    }
    
    log(f"STATE UPDATE: {state_data}")
    
    await manager.send_message(session_id, {
        "type": "state_update",
        "data": state_data
    })


async def send_account_update(session_id: str, session):
    """发送账户更新"""
    account = session.simulator.account
    
    positions = []
    for code, pos in account.positions.items():
        positions.append({
            "code": pos.code,
            "quantity": pos.quantity,
            "cost_price": pos.cost_price,
            "current_price": pos.current_price,
            "profit_loss": pos.profit_loss,
            "profit_loss_pct": pos.profit_loss_pct
        })
    
    await manager.send_message(session_id, {
        "type": "account_update",
        "data": {
            "cash": account.cash,
            "total_assets": account.total_assets,
            "total_market_value": account.total_market_value,
            "positions": positions
        }
    })
