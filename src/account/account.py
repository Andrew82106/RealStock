"""账户类 - Account class for managing virtual trading accounts."""

from dataclasses import dataclass, field
from typing import Optional
import json

from .models import Position, TradeFee


@dataclass
class Account:
    """虚拟交易账户 - Virtual trading account."""
    
    initial_cash: float = 100000.0
    cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    fee_config: TradeFee = field(default_factory=TradeFee)
    
    def __post_init__(self):
        self.cash = self.initial_cash
    
    @property
    def total_market_value(self) -> float:
        """所有持仓总市值 - Total market value of all positions."""
        return sum(p.market_value for p in self.positions.values())
    
    @property
    def total_assets(self) -> float:
        """总资产 = 现金 + 持仓市值 - Total assets = cash + market value."""
        return self.cash + self.total_market_value
    
    def calculate_buy_fee(self, amount: float) -> float:
        """
        计算买入手续费 - Calculate buy fee.
        
        Args:
            amount: 交易金额
            
        Returns:
            买入佣金（最低5元）
        """
        commission = max(amount * self.fee_config.commission_rate, self.fee_config.min_commission)
        return commission
    
    def calculate_sell_fee(self, amount: float) -> float:
        """
        计算卖出手续费（含印花税）- Calculate sell fee (including stamp tax).
        
        Args:
            amount: 交易金额
            
        Returns:
            卖出费用 = 佣金 + 印花税
        """
        commission = max(amount * self.fee_config.commission_rate, self.fee_config.min_commission)
        stamp_tax = amount * self.fee_config.stamp_tax_rate
        return commission + stamp_tax
    
    def update_prices(self, price_dict: dict[str, float]) -> None:
        """
        更新持仓当前价格 - Update current prices for positions.
        
        Args:
            price_dict: 股票代码到价格的映射
        """
        for code, price in price_dict.items():
            if code in self.positions:
                self.positions[code].current_price = price
    
    def to_dict(self) -> dict:
        """序列化为字典 - Serialize to dictionary."""
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "positions": {
                code: {
                    "code": pos.code,
                    "quantity": pos.quantity,
                    "cost_price": pos.cost_price,
                    "current_price": pos.current_price,
                    "buy_date": pos.buy_date.isoformat()
                }
                for code, pos in self.positions.items()
            },
            "fee_config": {
                "stamp_tax_rate": self.fee_config.stamp_tax_rate,
                "commission_rate": self.fee_config.commission_rate,
                "min_commission": self.fee_config.min_commission
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """从字典反序列化 - Deserialize from dictionary."""
        from datetime import date
        
        account = cls(initial_cash=data["initial_cash"])
        account.cash = data["cash"]
        
        # 恢复持仓
        for code, pos_data in data.get("positions", {}).items():
            account.positions[code] = Position(
                code=pos_data["code"],
                quantity=pos_data["quantity"],
                cost_price=pos_data["cost_price"],
                current_price=pos_data["current_price"],
                buy_date=date.fromisoformat(pos_data["buy_date"])
            )
        
        # 恢复费用配置
        if "fee_config" in data:
            account.fee_config = TradeFee(
                stamp_tax_rate=data["fee_config"]["stamp_tax_rate"],
                commission_rate=data["fee_config"]["commission_rate"],
                min_commission=data["fee_config"]["min_commission"]
            )
        
        return account
    
    def save(self, filepath: str) -> None:
        """保存账户状态到文件 - Save account state to file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "Account":
        """从文件加载账户状态 - Load account state from file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
