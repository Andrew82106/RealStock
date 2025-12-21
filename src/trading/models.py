"""交易引擎数据模型 - Data models for the trading engine."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional
import uuid


class OrderType(Enum):
    """订单类型 - Order type enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态 - Order status enumeration."""
    PENDING = "pending"      # 挂单中
    FILLED = "filled"        # 已成交
    REJECTED = "rejected"    # 已拒绝
    CANCELLED = "cancelled"  # 已撤单


@dataclass
class Order:
    """交易订单 - Trading order."""
    
    code: str                                   # 股票代码
    order_type: OrderType                       # 订单类型
    price: float                                # 委托价格
    quantity: int                               # 委托数量
    order_date: date                            # 订单日期
    status: OrderStatus = OrderStatus.PENDING   # 订单状态
    reject_reason: Optional[str] = None         # 拒绝原因
    filled_price: Optional[float] = None        # 成交价格
    filled_quantity: Optional[int] = None       # 成交数量
    fee: float = 0.0                            # 手续费
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])  # 订单ID
    frozen_cash: float = 0.0                    # 冻结资金（买单）
    frozen_quantity: int = 0                    # 冻结股票数量（卖单）


@dataclass
class DailyBar:
    """日线数据 - Daily bar data."""
    
    date: date      # 日期
    open: float     # 开盘价
    high: float     # 最高价
    low: float      # 最低价
    close: float    # 收盘价
    volume: int     # 成交量
