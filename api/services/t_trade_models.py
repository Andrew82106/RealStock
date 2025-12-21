"""
做T交易数据模型 - T-Trade Data Models
Requirements: 7.1, 7.2
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TTradeRecord:
    """做T交易记录"""
    id: str                    # 唯一标识
    stock_code: str            # 股票代码
    sell_price: float          # 卖出价格
    buy_price: float           # 买入价格
    quantity: int              # 交易数量
    sell_fee: float            # 卖出手续费
    buy_fee: float             # 买入手续费
    profit: float              # 盈亏（已扣除手续费）
    trade_date: str            # 交易日期
    sell_time: str             # 卖出时间
    buy_time: str              # 买入时间
    
    @property
    def total_fee(self) -> float:
        """总手续费"""
        return self.sell_fee + self.buy_fee
    
    @property
    def is_successful(self) -> bool:
        """是否成功（盈利）"""
        return self.profit > 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "stock_code": self.stock_code,
            "sell_price": self.sell_price,
            "buy_price": self.buy_price,
            "quantity": self.quantity,
            "sell_fee": self.sell_fee,
            "buy_fee": self.buy_fee,
            "profit": self.profit,
            "trade_date": self.trade_date,
            "sell_time": self.sell_time,
            "buy_time": self.buy_time,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TTradeRecord":
        """从字典创建"""
        return cls(
            id=data["id"],
            stock_code=data["stock_code"],
            sell_price=data["sell_price"],
            buy_price=data["buy_price"],
            quantity=data["quantity"],
            sell_fee=data.get("sell_fee", 0),
            buy_fee=data.get("buy_fee", 0),
            profit=data["profit"],
            trade_date=data["trade_date"],
            sell_time=data.get("sell_time", ""),
            buy_time=data.get("buy_time", ""),
        )


@dataclass
class TTradeStatistics:
    """做T统计数据"""
    total_trades: int = 0                    # 总做T次数
    successful_trades: int = 0               # 成功次数
    failed_trades: int = 0                   # 失败次数
    success_rate: float = 0.0                # 成功率 (0-100)
    total_profit: float = 0.0                # 累计盈亏
    total_fees: float = 0.0                  # 累计手续费
    best_trade_profit: float = 0.0           # 最佳单次盈利
    worst_trade_loss: float = 0.0            # 最差单次亏损
    average_profit: float = 0.0              # 平均盈亏
    trades: list[TTradeRecord] = field(default_factory=list)  # 所有做T记录
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "success_rate": self.success_rate,
            "total_profit": self.total_profit,
            "total_fees": self.total_fees,
            "best_trade_profit": self.best_trade_profit,
            "worst_trade_loss": self.worst_trade_loss,
            "average_profit": self.average_profit,
            "trades": [t.to_dict() for t in self.trades],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TTradeStatistics":
        """从字典创建"""
        return cls(
            total_trades=data.get("total_trades", 0),
            successful_trades=data.get("successful_trades", 0),
            failed_trades=data.get("failed_trades", 0),
            success_rate=data.get("success_rate", 0.0),
            total_profit=data.get("total_profit", 0.0),
            total_fees=data.get("total_fees", 0.0),
            best_trade_profit=data.get("best_trade_profit", 0.0),
            worst_trade_loss=data.get("worst_trade_loss", 0.0),
            average_profit=data.get("average_profit", 0.0),
            trades=[TTradeRecord.from_dict(t) for t in data.get("trades", [])],
        )


@dataclass
class TradeRecord:
    """普通交易记录（用于做T检测）"""
    order_id: str
    code: str
    order_type: str  # "buy" or "sell"
    price: float
    quantity: int
    fee: float
    timestamp: str   # ISO 8601 格式，包含日期和时间
    
    @property
    def trade_date(self) -> str:
        """获取交易日期（YYYY-MM-DD）"""
        return self.timestamp[:10] if len(self.timestamp) >= 10 else self.timestamp
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "order_id": self.order_id,
            "code": self.code,
            "order_type": self.order_type,
            "price": self.price,
            "quantity": self.quantity,
            "fee": self.fee,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TradeRecord":
        """从字典创建"""
        return cls(
            order_id=data.get("order_id", data.get("orderId", "")),
            code=data["code"],
            order_type=data.get("order_type", data.get("orderType", "")),
            price=data["price"],
            quantity=data["quantity"],
            fee=data["fee"],
            timestamp=data["timestamp"],
        )
