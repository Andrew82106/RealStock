"""可跨服务重启恢复的日线游戏会话。"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from src.account.models import Position
from src.data_engine.engine import DataEngine
from src.playback.models import PlaybackState
from src.simulator.simulator import Simulator
from src.trading.models import Order, OrderStatus, OrderType


GAME_LOOKBACK_DAYS = 31


@dataclass
class DailySnapshot:
    """每日资产快照。"""

    date: str
    total_assets: float
    cash: float
    market_value: float
    daily_return: float
    daily_profit: float
    cumulative_return: float


@dataclass
class GameSession:
    """日线游戏会话。"""

    session_id: str
    simulator: Simulator
    stock_codes: list[str]
    start_date: date
    end_date: date
    initial_cash: float
    indicator_id: str | None = None
    created_at: float = field(default_factory=time.time)
    asset_history: list[DailySnapshot] = field(default_factory=list)
    last_snapshot_date: str = ""
    indicator_cache_signature: str = ""
    indicator_values_by_code: dict[str, list[dict]] = field(default_factory=dict)
    indicator_cache_lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def record_daily_snapshot(self) -> None:
        account = self.simulator.account
        current_date = self.simulator.current_date.isoformat() if self.simulator.current_date else ""
        if not current_date or current_date == self.last_snapshot_date:
            return

        total_assets = account.total_assets
        if self.asset_history:
            previous_assets = self.asset_history[-1].total_assets
        else:
            previous_assets = self.initial_cash
        daily_profit = total_assets - previous_assets
        daily_return = daily_profit / previous_assets if previous_assets > 0 else 0
        cumulative_return = (
            (total_assets - self.initial_cash) / self.initial_cash
            if self.initial_cash > 0 else 0
        )
        self.asset_history.append(DailySnapshot(
            date=current_date,
            total_assets=total_assets,
            cash=account.cash,
            market_value=account.total_market_value,
            daily_return=daily_return,
            daily_profit=daily_profit,
            cumulative_return=cumulative_return,
        ))
        self.last_snapshot_date = current_date


class SessionManager:
    """管理内存会话，并用 JSON 快照跨热重载恢复。"""

    def __init__(self, storage_dir: str = "./storage/game_sessions"):
        self._sessions: dict[str, GameSession] = {}
        self._data_engine: DataEngine | None = None
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def get_data_engine(self) -> DataEngine:
        if self._data_engine is None:
            self._data_engine = DataEngine(cache_dir="./storage/stock_data")
        return self._data_engine

    @staticmethod
    def _safe_session_id(session_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            raise ValueError("无效的会话 ID")
        return session_id

    def _path(self, session_id: str) -> Path:
        return self.storage_dir / f"{self._safe_session_id(session_id)}.json"

    def create_session(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0,
        indicator_id: str | None = None,
    ) -> GameSession:
        session_id = uuid.uuid4().hex[:8]
        simulator = Simulator(
            self.get_data_engine(), initial_cash=initial_cash, daily_mode=True
        )
        simulator.setup(
            stock_codes,
            start_date,
            end_date,
            history_start_date=start_date - timedelta(days=GAME_LOOKBACK_DAYS),
        )
        session = GameSession(
            session_id=session_id,
            simulator=simulator,
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            indicator_id=indicator_id,
        )
        with self._lock:
            self._sessions[session_id] = session
            self.persist_session(session_id)
        return session

    @staticmethod
    def _order_to_dict(order: Order) -> dict:
        return {
            "order_id": order.order_id,
            "code": order.code,
            "order_type": order.order_type.value,
            "price": order.price,
            "quantity": order.quantity,
            "order_date": order.order_date.isoformat(),
            "status": order.status.value,
            "reject_reason": order.reject_reason,
            "filled_price": order.filled_price,
            "filled_quantity": order.filled_quantity,
            "filled_date": order.filled_date.isoformat() if order.filled_date else None,
            "fee": order.fee,
            "frozen_cash": order.frozen_cash,
            "frozen_quantity": order.frozen_quantity,
        }

    @staticmethod
    def _order_from_dict(payload: dict) -> Order:
        order_date = date.fromisoformat(payload["order_date"])
        status = OrderStatus(str(payload.get("status", "pending")))
        filled_date_value = payload.get("filled_date")
        filled_date = (
            date.fromisoformat(str(filled_date_value))
            if filled_date_value
            else order_date if status == OrderStatus.FILLED else None
        )
        return Order(
            code=str(payload["code"]),
            order_type=OrderType(str(payload["order_type"])),
            price=float(payload["price"]),
            quantity=int(payload["quantity"]),
            order_date=order_date,
            status=status,
            reject_reason=payload.get("reject_reason"),
            filled_price=payload.get("filled_price"),
            filled_quantity=payload.get("filled_quantity"),
            filled_date=filled_date,
            fee=float(payload.get("fee", 0)),
            order_id=str(payload["order_id"]),
            frozen_cash=float(payload.get("frozen_cash", 0)),
            frozen_quantity=int(payload.get("frozen_quantity", 0)),
        )

    def persist_session(self, session_id: str) -> None:
        """原子写入会话快照。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            simulator = session.simulator
            payload = {
                "version": 1,
                "session_id": session.session_id,
                "stock_codes": session.stock_codes,
                "start_date": session.start_date.isoformat(),
                "end_date": session.end_date.isoformat(),
                "initial_cash": session.initial_cash,
                "indicator_id": session.indicator_id,
                "created_at": session.created_at,
                "date_index": simulator.date_index,
                "account": {
                    "cash": simulator.account.cash,
                    "positions": [
                        {
                            "code": position.code,
                            "quantity": position.quantity,
                            "cost_price": position.cost_price,
                            "current_price": position.current_price,
                            "buy_date": position.buy_date.isoformat(),
                        }
                        for position in simulator.account.positions.values()
                    ],
                },
                "trade_log": [
                    self._order_to_dict(order)
                    for order in simulator.trading_engine.trade_log
                ],
                "pending_orders": [
                    self._order_to_dict(order)
                    for order in simulator.trading_engine.pending_orders
                ],
                "net_value_history": [
                    {"date": item_date.isoformat(), "value": value}
                    for item_date, value in simulator.net_value_history
                ],
                "asset_history": [asdict(snapshot) for snapshot in session.asset_history],
                "last_snapshot_date": session.last_snapshot_date,
            }
            path = self._path(session_id)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temp_path.replace(path)

    def _restore_session(self, session_id: str) -> Optional[GameSession]:
        path = self._path(session_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        start_date = date.fromisoformat(payload["start_date"])
        end_date = date.fromisoformat(payload["end_date"])
        initial_cash = float(payload["initial_cash"])
        simulator = Simulator(
            self.get_data_engine(), initial_cash=initial_cash, daily_mode=True
        )
        simulator.setup(
            list(payload["stock_codes"]),
            start_date,
            end_date,
            history_start_date=start_date - timedelta(days=GAME_LOOKBACK_DAYS),
        )
        if not simulator.trading_dates:
            return None

        simulator.date_index = min(
            int(payload.get("date_index", 0)), len(simulator.trading_dates) - 1
        )
        simulator.current_date = simulator.trading_dates[simulator.date_index]
        simulator.playback_engine.date_index = simulator.date_index
        simulator.playback_engine.current_date = simulator.current_date
        simulator.playback_engine.state = PlaybackState.PAUSED

        account_payload = payload.get("account", {})
        simulator.account.cash = float(account_payload.get("cash", initial_cash))
        simulator.account.positions = {}
        for item in account_payload.get("positions", []):
            simulator.account.positions[item["code"]] = Position(
                code=item["code"],
                quantity=int(item["quantity"]),
                cost_price=float(item["cost_price"]),
                current_price=float(item["current_price"]),
                buy_date=date.fromisoformat(item["buy_date"]),
            )
        simulator.trading_engine.trade_log = [
            self._order_from_dict(item) for item in payload.get("trade_log", [])
        ]
        simulator.trading_engine.pending_orders = [
            self._order_from_dict(item) for item in payload.get("pending_orders", [])
        ]
        simulator.net_value_history = [
            (date.fromisoformat(item["date"]), float(item["value"]))
            for item in payload.get("net_value_history", [])
        ] or [(simulator.current_date, simulator.account.total_assets)]

        session = GameSession(
            session_id=session_id,
            simulator=simulator,
            stock_codes=list(payload["stock_codes"]),
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            indicator_id=payload.get("indicator_id"),
            created_at=float(payload.get("created_at", time.time())),
            asset_history=[
                DailySnapshot(**item) for item in payload.get("asset_history", [])
            ],
            last_snapshot_date=str(payload.get("last_snapshot_date", "")),
        )
        return session

    def get_session(self, session_id: str) -> Optional[GameSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is not None:
                return session
            try:
                session = self._restore_session(session_id)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                return None
            if session is not None:
                self._sessions[session_id] = session
            return session

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            existed = self._sessions.pop(session_id, None) is not None
            try:
                path = self._path(session_id)
            except ValueError:
                return existed
            existed = path.exists() or existed
            path.unlink(missing_ok=True)
            return existed

    def list_sessions(self) -> list[str]:
        with self._lock:
            disk_ids = {path.stem for path in self.storage_dir.glob("*.json")}
            return sorted(set(self._sessions) | disk_ids)

    def list_session_summaries(self) -> list[dict]:
        """列出可以从本地快照继续的游戏会话。"""
        summaries: list[dict] = []
        for session_id in self.list_sessions():
            session = self.get_session(session_id)
            if session is None:
                continue
            path = self._path(session_id)
            updated_timestamp = path.stat().st_mtime if path.exists() else session.created_at
            simulator = session.simulator
            summaries.append({
                "session_id": session_id,
                "created_at": datetime.fromtimestamp(session.created_at).astimezone().isoformat(timespec="seconds"),
                "updated_at": datetime.fromtimestamp(updated_timestamp).astimezone().isoformat(timespec="seconds"),
                "current_date": simulator.current_date.isoformat() if simulator.current_date else "",
                "start_date": session.start_date.isoformat(),
                "end_date": session.end_date.isoformat(),
                "stock_codes": session.stock_codes,
                "initial_cash": session.initial_cash,
                "total_assets": simulator.account.total_assets,
                "indicator_id": session.indicator_id,
                "date_index": simulator.date_index,
                "total_dates": len(simulator.trading_dates),
                "is_last_day": simulator.date_index >= len(simulator.trading_dates) - 1,
            })
        summaries.sort(key=lambda item: item["updated_at"], reverse=True)
        return summaries


session_manager = SessionManager()
