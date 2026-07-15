"""属性测试 - 交易引擎模块 Property-based tests for trading engine module."""

from datetime import date, timedelta

import pytest
from hypothesis import given, settings, strategies as st, assume

from src.account.account import Account
from src.account.models import Position
from src.trading.models import Order, OrderType, OrderStatus, DailyBar
from src.trading.engine import TradingEngine
from src.exceptions import InvalidOrderError


# 测试数据生成策略
stock_codes = st.sampled_from(["600519", "000001", "300750", "601318", "002594"])

prices = st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False).map(
    lambda x: round(x, 2)
)

quantities = st.integers(min_value=100, max_value=10000).map(lambda x: (x // 100) * 100)

cash_amounts = st.floats(min_value=1000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False).map(
    lambda x: round(x, 2)
)


@st.composite
def daily_bars(draw):
    """生成有效的日线数据"""
    low = draw(st.floats(min_value=1.0, max_value=9000.0, allow_nan=False, allow_infinity=False))
    low = round(low, 2)
    high = draw(st.floats(min_value=low, max_value=low * 1.2, allow_nan=False, allow_infinity=False))
    high = round(max(high, low + 0.01), 2)  # 确保 high > low
    open_price = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
    open_price = round(open_price, 2)
    close = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
    close = round(close, 2)
    
    return DailyBar(
        date=draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31))),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=draw(st.integers(min_value=1000, max_value=100000000))
    )


class TestBuyOrderFundValidation:
    """
    Property 3: 买入订单资金验证
    Feature: stock-trading-simulator, Property 3: 买入订单资金验证
    **Validates: Requirements 3.1, 3.2**
    
    验证资金充足时接受订单，不足时拒绝：
    - 如果 cash >= price * quantity + buy_fee，订单应被接受
    - 如果 cash < price * quantity + buy_fee，订单应被拒绝
    """
    
    @settings(max_examples=100)
    @given(
        initial_cash=cash_amounts,
        price=prices,
        quantity=quantities,
        code=stock_codes
    )
    def test_buy_order_accepted_when_sufficient_funds(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证资金充足时买入订单被接受。
        
        *For any* 买入订单（代码、价格、数量）和账户状态：
        如果 cash >= price * quantity + buy_fee，订单应被接受
        """
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 只测试资金充足的情况
        assume(account.cash >= total_cost)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        assert order.status == OrderStatus.FILLED, \
            f"资金充足时订单应被接受: cash={account.cash}, total_cost={total_cost}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_buy_order_rejected_when_insufficient_funds(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证资金不足时买入订单被拒绝。
        
        *For any* 买入订单（代码、价格、数量）和账户状态：
        如果 cash < price * quantity + buy_fee，订单应被拒绝
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 只测试资金不足的情况
        assume(account.cash < total_cost)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"资金不足时订单应被拒绝: cash={account.cash}, total_cost={total_cost}"
        assert order.reject_reason == "可用资金不足", \
            f"拒绝原因应为'可用资金不足': 实际 '{order.reject_reason}'"



class TestBuyOrderAccountStateConsistency:
    """
    Property 4: 买入后账户状态一致性
    Feature: stock-trading-simulator, Property 4: 买入后账户状态一致性
    **Validates: Requirements 3.3**
    
    验证买入后现金和持仓变化正确：
    - 新现金 = 原现金 - (成交价 * 数量 + 手续费)
    - 新持仓数量 = 原持仓数量 + 买入数量
    - 总资产变化仅来自手续费
    """
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_cash_decreases_correctly_after_buy(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证买入后现金正确减少。
        
        *For any* 成功执行的买入订单，执行后：
        新现金 = 原现金 - (成交价 * 数量 + 手续费)
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        original_cash = account.cash
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 确保资金充足
        assume(original_cash >= total_cost)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        expected_cash = original_cash - total_cost
        actual_cash = account.cash
        
        assert abs(actual_cash - expected_cash) < 0.01, \
            f"现金减少不正确: 期望 {expected_cash}, 实际 {actual_cash}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_position_increases_correctly_after_buy(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证买入后持仓数量正确增加。
        
        *For any* 成功执行的买入订单，执行后：
        新持仓数量 = 原持仓数量 + 买入数量
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        original_quantity = account.positions.get(code, Position(
            code=code, quantity=0, cost_price=0, current_price=0, buy_date=date.today()
        )).quantity
        
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 确保资金充足
        assume(account.cash >= total_cost)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        expected_quantity = original_quantity + quantity
        actual_quantity = account.positions[code].quantity
        
        assert actual_quantity == expected_quantity, \
            f"持仓数量不正确: 期望 {expected_quantity}, 实际 {actual_quantity}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_total_assets_decrease_equals_fee(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证买入后总资产变化仅来自手续费。
        
        *For any* 成功执行的买入订单，执行后：
        总资产变化 = -手续费
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        original_total_assets = account.total_assets
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        total_cost = amount + fee
        
        # 确保资金充足
        assume(account.cash >= total_cost)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        new_total_assets = account.total_assets
        assets_change = new_total_assets - original_total_assets
        
        # 总资产变化应等于负的手续费（因为手续费是损失）
        assert abs(assets_change + fee) < 0.01, \
            f"总资产变化应等于负手续费: 变化 {assets_change}, 手续费 {fee}"



@st.composite
def account_with_position(draw, code: str = None):
    """生成带有指定股票持仓的账户"""
    if code is None:
        code = draw(stock_codes)
    
    initial_cash = draw(st.floats(min_value=10000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False))
    initial_cash = round(initial_cash, 2)
    
    account = Account(initial_cash=initial_cash)
    
    # 创建持仓
    quantity = draw(st.integers(min_value=100, max_value=10000).map(lambda x: (x // 100) * 100))
    cost_price = draw(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    cost_price = round(cost_price, 2)
    current_price = draw(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    current_price = round(current_price, 2)
    # 买入日期设为过去，以满足 T+1 限制
    buy_date = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 11, 30)))
    
    account.positions[code] = Position(
        code=code,
        quantity=quantity,
        cost_price=cost_price,
        current_price=current_price,
        buy_date=buy_date
    )
    
    return account, code


class TestSellOrderPositionValidation:
    """
    Property 5: 卖出订单持仓验证
    Feature: stock-trading-simulator, Property 5: 卖出订单持仓验证
    **Validates: Requirements 4.1, 4.2**
    
    验证持仓充足时接受订单，不足时拒绝：
    - 如果 positions[code].quantity >= quantity，订单应被接受
    - 如果 positions[code].quantity < quantity 或代码不存在，订单应被拒绝
    """
    
    @settings(max_examples=100)
    @given(
        data=st.data(),
        price=prices
    )
    def test_sell_order_accepted_when_sufficient_position(self, data, price: float):
        """
        验证持仓充足时卖出订单被接受。
        
        *For any* 卖出订单（代码、价格、数量）和账户状态：
        如果 positions[code].quantity >= quantity，订单应被接受
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        # 卖出数量不超过持仓数量
        sell_quantity = data.draw(
            st.integers(min_value=100, max_value=position.quantity).map(lambda x: (x // 100) * 100)
        )
        assume(sell_quantity > 0)
        assume(sell_quantity <= position.quantity)
        
        # 确保满足 T+1 限制（当前日期晚于买入日期）
        current_date = position.buy_date + timedelta(days=1)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date
        )
        
        assert order.status == OrderStatus.FILLED, \
            f"持仓充足时订单应被接受: position={position.quantity}, sell={sell_quantity}"
    
    @settings(max_examples=100)
    @given(
        data=st.data(),
        price=prices
    )
    def test_sell_order_rejected_when_insufficient_position(self, data, price: float):
        """
        验证持仓不足时卖出订单被拒绝。
        
        *For any* 卖出订单（代码、价格、数量）和账户状态：
        如果 positions[code].quantity < quantity，订单应被拒绝
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        # 卖出数量超过持仓数量
        sell_quantity = data.draw(
            st.integers(min_value=position.quantity + 100, max_value=position.quantity + 10000).map(
                lambda x: (x // 100) * 100
            )
        )
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"持仓不足时订单应被拒绝: position={position.quantity}, sell={sell_quantity}"
        assert order.reject_reason.startswith("可卖数量不足"), \
            f"拒绝原因应为'可卖数量不足': 实际 '{order.reject_reason}'"
    
    @settings(max_examples=100)
    @given(
        initial_cash=cash_amounts,
        price=prices,
        quantity=quantities,
        code=stock_codes
    )
    def test_sell_order_rejected_when_no_position(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证无持仓时卖出订单被拒绝。
        
        *For any* 卖出订单（代码、价格、数量）和账户状态：
        如果代码不存在于持仓中，订单应被拒绝
        """
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 确保没有该股票的持仓
        assume(code not in account.positions)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=date.today()
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"无持仓时订单应被拒绝"
        assert order.reject_reason == "无持仓", \
            f"拒绝原因应为'无持仓': 实际 '{order.reject_reason}'"



class TestSellOrderAccountStateConsistency:
    """
    Property 6: 卖出后账户状态一致性
    Feature: stock-trading-simulator, Property 6: 卖出后账户状态一致性
    **Validates: Requirements 4.3**
    
    验证卖出后现金和持仓变化正确：
    - 新现金 = 原现金 + (成交价 * 数量 - 手续费)
    - 新持仓数量 = 原持仓数量 - 卖出数量
    - 如果持仓数量变为 0，应从持仓列表移除
    """
    
    @settings(max_examples=100)
    @given(data=st.data(), price=prices)
    def test_cash_increases_correctly_after_sell(self, data, price: float):
        """
        验证卖出后现金正确增加。
        
        *For any* 成功执行的卖出订单，执行后：
        新现金 = 原现金 + (成交价 * 数量 - 手续费)
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        sell_quantity = data.draw(
            st.integers(min_value=100, max_value=position.quantity).map(lambda x: (x // 100) * 100)
        )
        assume(sell_quantity > 0)
        assume(sell_quantity <= position.quantity)
        
        original_cash = account.cash
        amount = price * sell_quantity
        fee = account.calculate_sell_fee(amount)
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        expected_cash = original_cash + amount - fee
        actual_cash = account.cash
        
        assert abs(actual_cash - expected_cash) < 0.01, \
            f"现金增加不正确: 期望 {expected_cash}, 实际 {actual_cash}"
    
    @settings(max_examples=100)
    @given(data=st.data(), price=prices)
    def test_position_decreases_correctly_after_sell(self, data, price: float):
        """
        验证卖出后持仓数量正确减少。
        
        *For any* 成功执行的卖出订单，执行后：
        新持仓数量 = 原持仓数量 - 卖出数量
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        original_quantity = position.quantity
        
        # 卖出部分持仓（不全部卖出）
        sell_quantity = data.draw(
            st.integers(min_value=100, max_value=max(100, original_quantity - 100)).map(
                lambda x: (x // 100) * 100
            )
        )
        assume(sell_quantity > 0)
        assume(sell_quantity < original_quantity)
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        expected_quantity = original_quantity - sell_quantity
        actual_quantity = account.positions[code].quantity
        
        assert actual_quantity == expected_quantity, \
            f"持仓数量不正确: 期望 {expected_quantity}, 实际 {actual_quantity}"
    
    @settings(max_examples=100)
    @given(data=st.data(), price=prices)
    def test_position_removed_when_fully_sold(self, data, price: float):
        """
        验证全部卖出后持仓从列表移除。
        
        *For any* 成功执行的卖出订单，如果卖出全部持仓：
        该股票应从持仓列表中移除
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        sell_quantity = position.quantity  # 卖出全部
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date
        )
        
        # 验证订单成功
        assume(order.status == OrderStatus.FILLED)
        
        assert code not in account.positions, \
            f"全部卖出后持仓应被移除: {code} 仍在持仓列表中"



class TestPriceRangeValidation:
    """
    Property 7: 回测模式价格范围验证
    Feature: stock-trading-simulator, Property 7: 回测模式价格范围验证
    **Validates: Requirements 3.4, 4.4**
    
    验证委托价格在日线范围内时有效：
    - 如果 daily_bar.low <= price <= daily_bar.high，订单价格有效
    - 如果 price < daily_bar.low 或 price > daily_bar.high，订单应被拒绝
    """
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        daily_bar=daily_bars(),
        quantity=quantities,
        code=stock_codes
    )
    def test_buy_order_accepted_when_price_in_range(
        self, initial_cash: float, daily_bar: DailyBar, quantity: int, code: str
    ):
        """
        验证买入价格在范围内时订单被接受。
        
        *For any* 委托订单和当日行情数据：
        如果 daily_bar.low <= price <= daily_bar.high，订单价格有效
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 选择范围内的价格
        price = round((daily_bar.low + daily_bar.high) / 2, 2)
        
        # 确保资金充足
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        assume(account.cash >= amount + fee)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=daily_bar.date,
            daily_bar=daily_bar
        )
        
        assert order.status == OrderStatus.FILLED, \
            f"价格在范围内时订单应被接受: price={price}, range=[{daily_bar.low}, {daily_bar.high}]"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        daily_bar=daily_bars(),
        quantity=quantities,
        code=stock_codes
    )
    def test_buy_order_rejected_when_price_below_range(
        self, initial_cash: float, daily_bar: DailyBar, quantity: int, code: str
    ):
        """
        验证买入价格低于范围时订单被拒绝。
        
        *For any* 委托订单和当日行情数据：
        如果 price < daily_bar.low，订单应被拒绝
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 选择低于范围的价格
        price = round(daily_bar.low - 0.01, 2)
        assume(price > 0)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=daily_bar.date,
            daily_bar=daily_bar
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"价格低于范围时订单应被拒绝: price={price}, low={daily_bar.low}"
        assert order.reject_reason == "委托价格超出当日价格范围", \
            f"拒绝原因不正确: {order.reject_reason}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        daily_bar=daily_bars(),
        quantity=quantities,
        code=stock_codes
    )
    def test_buy_order_rejected_when_price_above_range(
        self, initial_cash: float, daily_bar: DailyBar, quantity: int, code: str
    ):
        """
        验证买入价格高于范围时订单被拒绝。
        
        *For any* 委托订单和当日行情数据：
        如果 price > daily_bar.high，订单应被拒绝
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 选择高于范围的价格
        price = round(daily_bar.high + 0.01, 2)
        
        order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=daily_bar.date,
            daily_bar=daily_bar
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"价格高于范围时订单应被拒绝: price={price}, high={daily_bar.high}"
        assert order.reject_reason == "委托价格超出当日价格范围", \
            f"拒绝原因不正确: {order.reject_reason}"
    
    @settings(max_examples=100)
    @given(data=st.data(), daily_bar=daily_bars())
    def test_sell_order_accepted_when_price_in_range(self, data, daily_bar: DailyBar):
        """
        验证卖出价格在范围内时订单被接受。
        
        *For any* 委托订单和当日行情数据：
        如果 daily_bar.low <= price <= daily_bar.high，订单价格有效
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        sell_quantity = data.draw(
            st.integers(min_value=100, max_value=position.quantity).map(lambda x: (x // 100) * 100)
        )
        assume(sell_quantity > 0)
        assume(sell_quantity <= position.quantity)
        
        # 选择范围内的价格
        price = round((daily_bar.low + daily_bar.high) / 2, 2)
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        # 更新 daily_bar 的日期以匹配
        daily_bar_with_date = DailyBar(
            date=current_date,
            open=daily_bar.open,
            high=daily_bar.high,
            low=daily_bar.low,
            close=daily_bar.close,
            volume=daily_bar.volume
        )
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date,
            daily_bar=daily_bar_with_date
        )
        
        assert order.status == OrderStatus.FILLED, \
            f"价格在范围内时订单应被接受: price={price}, range=[{daily_bar.low}, {daily_bar.high}]"
    
    @settings(max_examples=100)
    @given(data=st.data(), daily_bar=daily_bars())
    def test_sell_order_rejected_when_price_out_of_range(self, data, daily_bar: DailyBar):
        """
        验证卖出价格超出范围时订单被拒绝。
        
        *For any* 委托订单和当日行情数据：
        如果 price < daily_bar.low 或 price > daily_bar.high，订单应被拒绝
        """
        account, code = data.draw(account_with_position())
        engine = TradingEngine(account)
        
        position = account.positions[code]
        sell_quantity = data.draw(
            st.integers(min_value=100, max_value=position.quantity).map(lambda x: (x // 100) * 100)
        )
        assume(sell_quantity > 0)
        assume(sell_quantity <= position.quantity)
        
        # 选择超出范围的价格（高于最高价）
        price = round(daily_bar.high + 0.01, 2)
        
        # 确保满足 T+1 限制
        current_date = position.buy_date + timedelta(days=1)
        daily_bar_with_date = DailyBar(
            date=current_date,
            open=daily_bar.open,
            high=daily_bar.high,
            low=daily_bar.low,
            close=daily_bar.close,
            volume=daily_bar.volume
        )
        
        order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=sell_quantity,
            current_date=current_date,
            daily_bar=daily_bar_with_date
        )
        
        assert order.status == OrderStatus.REJECTED, \
            f"价格超出范围时订单应被拒绝: price={price}, high={daily_bar.high}"
        assert order.reject_reason == "委托价格超出当日价格范围", \
            f"拒绝原因不正确: {order.reject_reason}"



class TestTPlusOneRestriction:
    """
    Property 8: T+1 交易限制
    Feature: stock-trading-simulator, Property 8: T+1 交易限制
    **Validates: Requirements 5.1, 5.2, 5.3**
    
    验证当天买入不可卖出，次日可卖：
    - 如果 position.buy_date == current_date，该持仓不可卖出
    - 如果 position.buy_date < current_date，该持仓可以卖出
    """
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=prices,
        quantity=quantities,
        code=stock_codes,
        buy_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 11, 30))
    )
    def test_cannot_sell_on_same_day_as_buy(
        self, initial_cash: float, price: float, quantity: int, code: str, buy_date: date
    ):
        """
        验证当天买入的股票当天不可卖出。
        
        *For any* 持仓和当前日期：
        如果 position.buy_date == current_date，该持仓不可卖出
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 先买入
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        assume(account.cash >= amount + fee)
        
        buy_order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=buy_date
        )
        assume(buy_order.status == OrderStatus.FILLED)
        
        # 同一天尝试卖出
        sell_order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=buy_date  # 同一天
        )
        
        assert sell_order.status == OrderStatus.REJECTED, \
            f"当天买入的股票当天不可卖出"
        assert sell_order.reject_reason == "T+1限制，当天买入不可卖出", \
            f"拒绝原因不正确: {sell_order.reject_reason}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=prices,
        quantity=quantities,
        code=stock_codes,
        buy_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 11, 30))
    )
    def test_can_sell_on_next_day(
        self, initial_cash: float, price: float, quantity: int, code: str, buy_date: date
    ):
        """
        验证次日可以卖出。
        
        *For any* 持仓和当前日期：
        如果 position.buy_date < current_date，该持仓可以卖出
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 先买入
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        assume(account.cash >= amount + fee)
        
        buy_order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=buy_date
        )
        assume(buy_order.status == OrderStatus.FILLED)
        
        # 次日卖出
        next_day = buy_date + timedelta(days=1)
        sell_order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=next_day  # 次日
        )
        
        assert sell_order.status == OrderStatus.FILLED, \
            f"次日应可以卖出: buy_date={buy_date}, sell_date={next_day}"
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=prices,
        quantity=quantities,
        code=stock_codes,
        buy_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 6, 30)),
        days_later=st.integers(min_value=2, max_value=365)
    )
    def test_can_sell_any_day_after_buy(
        self, initial_cash: float, price: float, quantity: int, code: str, 
        buy_date: date, days_later: int
    ):
        """
        验证买入后任意天数后都可以卖出。
        
        *For any* 持仓和当前日期：
        如果 position.buy_date < current_date，该持仓可以卖出
        """
        initial_cash = round(initial_cash, 2)
        account = Account(initial_cash=initial_cash)
        engine = TradingEngine(account)
        
        # 先买入
        amount = price * quantity
        fee = account.calculate_buy_fee(amount)
        assume(account.cash >= amount + fee)
        
        buy_order = engine.submit_buy_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=buy_date
        )
        assume(buy_order.status == OrderStatus.FILLED)
        
        # 多天后卖出
        sell_date = buy_date + timedelta(days=days_later)
        sell_order = engine.submit_sell_order(
            code=code,
            price=price,
            quantity=quantity,
            current_date=sell_date
        )
        
        assert sell_order.status == OrderStatus.FILLED, \
            f"买入后 {days_later} 天应可以卖出: buy_date={buy_date}, sell_date={sell_date}"
