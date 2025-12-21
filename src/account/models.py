"""账户系统数据模型 - Data models for the account system."""

from dataclasses import dataclass
from datetime import date


@dataclass
class Position:
    """持仓记录 - Position record for a stock holding."""
    
    code: str               # 股票代码
    quantity: int           # 持仓数量
    cost_price: float       # 买入成本价（含手续费均摊）
    current_price: float    # 当前价格
    buy_date: date          # 买入日期（用于 T+1 判断）
    
    @property
    def market_value(self) -> float:
        """持仓市值 - Market value of the position."""
        return self.quantity * self.current_price
    
    @property
    def profit_loss(self) -> float:
        """浮动盈亏 - Unrealized profit/loss."""
        return (self.current_price - self.cost_price) * self.quantity
    
    @property
    def profit_loss_pct(self) -> float:
        """浮动盈亏百分比 - Unrealized profit/loss percentage."""
        if self.cost_price == 0:
            return 0.0
        return (self.current_price - self.cost_price) / self.cost_price


@dataclass
class TradeFee:
    """交易费用配置 - Trading fee configuration."""
    
    stamp_tax_rate: float = 0.0005      # 印花税率 0.05%（仅卖出）
    commission_rate: float = 0.00025    # 佣金率 0.025%
    min_commission: float = 5.0         # 最低佣金 5 元
