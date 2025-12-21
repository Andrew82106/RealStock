"""
游戏会话管理服务
"""
import uuid
from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from src.data_engine.engine import DataEngine
from src.simulator.simulator import Simulator
from src.playback.models import PlaybackState


@dataclass
class DailySnapshot:
    """每日资产快照"""
    date: str
    total_assets: float
    cash: float
    market_value: float
    daily_return: float  # 当日收益率
    daily_profit: float  # 当日盈亏金额
    cumulative_return: float  # 累计收益率


@dataclass
class GameSession:
    """游戏会话"""
    session_id: str
    simulator: Simulator
    stock_codes: list[str]
    start_date: date
    end_date: date
    initial_cash: float
    created_at: float = field(default_factory=lambda: __import__('time').time())
    asset_history: list[DailySnapshot] = field(default_factory=list)
    last_snapshot_date: str = ""
    
    def record_daily_snapshot(self):
        """记录每日资产快照"""
        account = self.simulator.account
        current_date = self.simulator.current_date.isoformat() if self.simulator.current_date else ""
        
        # 避免重复记录同一天
        if current_date == self.last_snapshot_date:
            return
        
        total_assets = account.total_assets
        
        # 计算当日收益
        if self.asset_history:
            prev = self.asset_history[-1]
            daily_profit = total_assets - prev.total_assets
            daily_return = daily_profit / prev.total_assets if prev.total_assets > 0 else 0
        else:
            daily_profit = total_assets - self.initial_cash
            daily_return = daily_profit / self.initial_cash if self.initial_cash > 0 else 0
        
        # 累计收益率
        cumulative_return = (total_assets - self.initial_cash) / self.initial_cash if self.initial_cash > 0 else 0
        
        snapshot = DailySnapshot(
            date=current_date,
            total_assets=total_assets,
            cash=account.cash,
            market_value=account.total_market_value,
            daily_return=daily_return,
            daily_profit=daily_profit,
            cumulative_return=cumulative_return
        )
        
        self.asset_history.append(snapshot)
        self.last_snapshot_date = current_date


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self._sessions: dict[str, GameSession] = {}
        self._data_engine: DataEngine | None = None
    
    def get_data_engine(self) -> DataEngine:
        """获取数据引擎单例"""
        if self._data_engine is None:
            self._data_engine = DataEngine(cache_dir="./storage/stock_data")
        return self._data_engine
    
    def create_session(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0
    ) -> GameSession:
        """创建新游戏会话"""
        session_id = str(uuid.uuid4())[:8]
        
        data_engine = self.get_data_engine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        simulator.setup(stock_codes, start_date, end_date)
        
        session = GameSession(
            session_id=session_id,
            simulator=simulator,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash
        )
        
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """列出所有会话 ID"""
        return list(self._sessions.keys())


# 全局会话管理器
session_manager = SessionManager()
