"""交易引擎 - Trading engine for order processing and execution."""

from datetime import date
from typing import Optional
import csv

from ..account.account import Account
from ..account.models import Position
from ..exceptions import InvalidOrderError
from .models import Order, OrderType, OrderStatus, DailyBar


class TradingEngine:
    """交易引擎 - Handles order validation and execution."""
    
    def __init__(self, account: Account):
        """
        初始化交易引擎。
        
        Args:
            account: 关联的交易账户
        """
        self.account = account
        self.trade_log: list[Order] = []
        self.pending_orders: list[Order] = []  # 挂单列表
    
    @property
    def frozen_cash(self) -> float:
        """计算所有买单冻结的资金"""
        return sum(o.frozen_cash for o in self.pending_orders if o.order_type == OrderType.BUY)
    
    @property
    def available_cash(self) -> float:
        """可用资金 = 现金 - 冻结资金"""
        return self.account.cash - self.frozen_cash
    
    def get_frozen_quantity(self, code: str) -> int:
        """获取某只股票的冻结数量（卖单挂单）"""
        return sum(
            o.frozen_quantity for o in self.pending_orders 
            if o.order_type == OrderType.SELL and o.code == code
        )
    
    def get_available_quantity(self, code: str, current_date: date) -> int:
        """获取某只股票的可卖数量（考虑T+1和冻结）"""
        if code not in self.account.positions:
            return 0
        position = self.account.positions[code]
        # T+1 限制
        if position.buy_date >= current_date:
            return 0
        return position.quantity - self.get_frozen_quantity(code)
    
    def submit_buy_order(
        self,
        code: str,
        price: float,
        quantity: int,
        current_date: date,
        current_price: Optional[float] = None,
        daily_bar: Optional[DailyBar] = None
    ) -> Order:
        """
        提交买入订单。

        成交规则：
        - 提供 current_price（实时/回放模式）：委托价 >= 当前价时立即以当前价成交，
          否则进入挂单列表等待价格触及
        - 未提供 current_price（回测/直接成交模式）：立即以委托价成交
        - 提供 daily_bar 时，委托价必须在当日 [low, high] 范围内（回测价格范围验证）

        Args:
            code: 股票代码
            price: 委托价格
            quantity: 委托数量
            current_date: 当前日期
            current_price: 当前市场价格（用于判断是否立即成交）
            daily_bar: 当日行情（用于回测模式的价格范围验证）

        Returns:
            Order: 订单对象
        """
        # 验证数量
        if quantity <= 0 or not isinstance(quantity, int):
            raise InvalidOrderError("委托数量必须为正整数")

        if price <= 0:
            raise InvalidOrderError("委托价格必须为正数")

        order = Order(
            code=code,
            order_type=OrderType.BUY,
            price=price,
            quantity=quantity,
            order_date=current_date
        )

        # 回测模式价格范围验证
        if daily_bar is not None and not (daily_bar.low <= price <= daily_bar.high):
            order.status = OrderStatus.REJECTED
            order.reject_reason = "委托价格超出当日价格范围"
            self.trade_log.append(order)
            return order

        # 计算所需资金
        amount = price * quantity
        fee = self.account.calculate_buy_fee(amount)
        total_cost = amount + fee

        # 验证可用资金是否充足
        if self.available_cash < total_cost:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "可用资金不足"
            self.trade_log.append(order)
            return order

        # 冻结资金
        order.fee = fee
        order.frozen_cash = total_cost

        if current_price is None:
            # 回测/直接成交模式：立即以委托价成交
            self._execute_buy(order, price)
            self.trade_log.append(order)
        elif price >= current_price:
            # 委托价 >= 当前价，立即以当前价成交
            self._execute_buy(order, current_price)
            self.trade_log.append(order)
        else:
            # 加入挂单列表
            self.pending_orders.append(order)

        return order

    def submit_sell_order(
        self,
        code: str,
        price: float,
        quantity: int,
        current_date: date,
        current_price: Optional[float] = None,
        daily_bar: Optional[DailyBar] = None
    ) -> Order:
        """
        提交卖出订单。

        成交规则：
        - 提供 current_price（实时/回放模式）：委托价 <= 当前价时立即以当前价成交，
          否则进入挂单列表等待价格触及
        - 未提供 current_price（回测/直接成交模式）：立即以委托价成交
        - 提供 daily_bar 时，委托价必须在当日 [low, high] 范围内（回测价格范围验证）

        Args:
            code: 股票代码
            price: 委托价格
            quantity: 委托数量
            current_date: 当前日期
            current_price: 当前市场价格（用于判断是否立即成交）
            daily_bar: 当日行情（用于回测模式的价格范围验证）

        Returns:
            Order: 订单对象
        """
        # 验证数量
        if quantity <= 0 or not isinstance(quantity, int):
            raise InvalidOrderError("委托数量必须为正整数")

        if price <= 0:
            raise InvalidOrderError("委托价格必须为正数")

        order = Order(
            code=code,
            order_type=OrderType.SELL,
            price=price,
            quantity=quantity,
            order_date=current_date
        )

        # 回测模式价格范围验证
        if daily_bar is not None and not (daily_bar.low <= price <= daily_bar.high):
            order.status = OrderStatus.REJECTED
            order.reject_reason = "委托价格超出当日价格范围"
            self.trade_log.append(order)
            return order

        # 验证持仓是否存在
        if code not in self.account.positions:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "无持仓"
            self.trade_log.append(order)
            return order

        # 验证可卖数量是否充足
        available = self.get_available_quantity(code, current_date)
        if available < quantity:
            position = self.account.positions[code]
            order.status = OrderStatus.REJECTED
            if available == 0 and position.buy_date >= current_date:
                order.reject_reason = "T+1限制，当天买入不可卖出"
            else:
                order.reject_reason = f"可卖数量不足（可卖: {available}）"
            self.trade_log.append(order)
            return order

        # 计算手续费
        amount = price * quantity
        fee = self.account.calculate_sell_fee(amount)
        order.fee = fee
        order.frozen_quantity = quantity

        if current_price is None:
            # 回测/直接成交模式：立即以委托价成交
            self._execute_sell(order, price)
            self.trade_log.append(order)
        elif price <= current_price:
            # 委托价 <= 当前价，立即以当前价成交
            self._execute_sell(order, current_price)
            self.trade_log.append(order)
        else:
            # 加入挂单列表
            self.pending_orders.append(order)

        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销挂单。
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 是否撤单成功
        """
        for i, order in enumerate(self.pending_orders):
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.pending_orders.pop(i)
                self.trade_log.append(order)
                return True
        return False
    
    def check_pending_orders(self, prices: dict[str, float]) -> list[Order]:
        """
        检查挂单是否可以成交。
        
        Args:
            prices: 当前价格字典 {code: price}
            
        Returns:
            list[Order]: 本次成交的订单列表
        """
        filled_orders = []
        remaining_orders = []
        
        for order in self.pending_orders:
            current_price = prices.get(order.code)
            if current_price is None:
                remaining_orders.append(order)
                continue
            
            filled = False
            if order.order_type == OrderType.BUY:
                # 买单：委托价 >= 当前价 时成交
                if order.price >= current_price:
                    self._execute_buy(order, current_price)
                    filled = True
            else:
                # 卖单：委托价 <= 当前价 时成交
                if order.price <= current_price:
                    self._execute_sell(order, current_price)
                    filled = True
            
            if filled:
                self.trade_log.append(order)
                filled_orders.append(order)
            else:
                remaining_orders.append(order)
        
        self.pending_orders = remaining_orders
        return filled_orders
    
    def cancel_all_pending_orders(self) -> int:
        """
        撤销所有挂单（日终清理）。
        
        Returns:
            int: 撤销的订单数量
        """
        count = len(self.pending_orders)
        for order in self.pending_orders:
            order.status = OrderStatus.CANCELLED
            order.reject_reason = "日终自动撤单"
            self.trade_log.append(order)
        self.pending_orders = []
        return count
    
    def _execute_buy(self, order: Order, fill_price: float) -> None:
        """
        执行买入，更新账户。
        
        Args:
            order: 买入订单
            fill_price: 成交价格
        """
        # 实际成交金额（可能以更优价格成交）
        amount = fill_price * order.quantity
        fee = self.account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 扣减现金（如果有冻结资金，先解冻再扣减）
        if order.frozen_cash > 0:
            # 解冻后扣减实际成本，多余的返还
            self.account.cash -= total_cost
            order.frozen_cash = 0
        else:
            self.account.cash -= total_cost
        
        # 更新持仓
        if order.code in self.account.positions:
            existing = self.account.positions[order.code]
            total_quantity = existing.quantity + order.quantity
            old_total_cost = existing.cost_price * existing.quantity
            new_total_cost = (fill_price + fee / order.quantity) * order.quantity
            new_cost_price = (old_total_cost + new_total_cost) / total_quantity
            
            existing.quantity = total_quantity
            existing.cost_price = new_cost_price
            existing.buy_date = order.order_date
        else:
            cost_price = fill_price + fee / order.quantity
            self.account.positions[order.code] = Position(
                code=order.code,
                quantity=order.quantity,
                cost_price=cost_price,
                current_price=fill_price,
                buy_date=order.order_date
            )
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.fee = fee

    def _execute_sell(self, order: Order, fill_price: float) -> None:
        """
        执行卖出，更新账户。
        
        Args:
            order: 卖出订单
            fill_price: 成交价格
        """
        amount = fill_price * order.quantity
        fee = self.account.calculate_sell_fee(amount)
        net_proceeds = amount - fee
        
        # 增加现金
        self.account.cash += net_proceeds
        
        # 更新持仓
        position = self.account.positions[order.code]
        position.quantity -= order.quantity
        
        if position.quantity == 0:
            del self.account.positions[order.code]
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.fee = fee
        order.frozen_quantity = 0

    def get_pending_orders(self) -> list[Order]:
        """获取所有挂单"""
        return self.pending_orders
    
    def get_trade_history(self) -> list[Order]:
        """获取交易历史"""
        return self.trade_log
    
    def export_trade_log_to_csv(self, filepath: str) -> None:
        """导出交易日志到 CSV 文件"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'order_id', 'order_date', 'code', 'order_type', 'price', 'quantity',
                'status', 'filled_price', 'filled_quantity', 'fee', 'reject_reason'
            ])
            
            for order in self.trade_log:
                writer.writerow([
                    order.order_id,
                    order.order_date.isoformat(),
                    order.code,
                    order.order_type.value,
                    order.price,
                    order.quantity,
                    order.status.value,
                    order.filled_price if order.filled_price else '',
                    order.filled_quantity if order.filled_quantity else '',
                    order.fee,
                    order.reject_reason if order.reject_reason else ''
                ])
    
    def clear_trade_log(self) -> None:
        """清空交易日志"""
        self.trade_log = []
