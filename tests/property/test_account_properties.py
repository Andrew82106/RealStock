"""属性测试 - 账户系统模块 Property-based tests for account system module."""

from datetime import date

import pytest
from hypothesis import given, settings, strategies as st

from src.account.models import Position, TradeFee


# 测试数据生成策略
@st.composite
def valid_position(draw):
    """生成有效的 Position 对象"""
    code = draw(st.sampled_from(["600519", "000001", "300750", "601318"]))
    quantity = draw(st.integers(min_value=100, max_value=10000).map(lambda x: (x // 100) * 100))
    cost_price = draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    cost_price = round(cost_price, 2)
    current_price = draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    current_price = round(current_price, 2)
    buy_date = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)))
    
    return Position(
        code=code,
        quantity=quantity,
        cost_price=cost_price,
        current_price=current_price,
        buy_date=buy_date
    )


class TestPositionProfitLossCalculation:
    """
    Property 17: 持仓浮动盈亏计算
    Feature: stock-trading-simulator, Property 17: 持仓浮动盈亏计算
    **Validates: Requirements 2.3**
    
    验证 profit_loss 和 profit_loss_pct 计算正确：
    - profit_loss = (current_price - cost_price) * quantity
    - profit_loss_pct = (current_price - cost_price) / cost_price
    """
    
    @settings(max_examples=100)
    @given(position=valid_position())
    def test_profit_loss_calculation(self, position: Position):
        """
        验证浮动盈亏计算正确。
        
        *For any* 持仓 position：
        profit_loss = (current_price - cost_price) * quantity
        """
        expected_profit_loss = (position.current_price - position.cost_price) * position.quantity
        actual_profit_loss = position.profit_loss
        
        assert abs(actual_profit_loss - expected_profit_loss) < 0.01, \
            f"浮动盈亏计算错误: 期望 {expected_profit_loss}, 实际 {actual_profit_loss}"
    
    @settings(max_examples=100)
    @given(position=valid_position())
    def test_profit_loss_pct_calculation(self, position: Position):
        """
        验证浮动盈亏百分比计算正确。
        
        *For any* 持仓 position：
        profit_loss_pct = (current_price - cost_price) / cost_price
        """
        if position.cost_price == 0:
            assert position.profit_loss_pct == 0.0, "成本价为0时，盈亏百分比应为0"
        else:
            expected_pct = (position.current_price - position.cost_price) / position.cost_price
            actual_pct = position.profit_loss_pct
            
            assert abs(actual_pct - expected_pct) < 0.0001, \
                f"浮动盈亏百分比计算错误: 期望 {expected_pct}, 实际 {actual_pct}"
    
    @settings(max_examples=100)
    @given(position=valid_position())
    def test_market_value_calculation(self, position: Position):
        """
        验证持仓市值计算正确。
        
        *For any* 持仓 position：
        market_value = quantity * current_price
        """
        expected_market_value = position.quantity * position.current_price
        actual_market_value = position.market_value
        
        assert abs(actual_market_value - expected_market_value) < 0.01, \
            f"持仓市值计算错误: 期望 {expected_market_value}, 实际 {actual_market_value}"


from src.account.account import Account


@st.composite
def valid_account_with_positions(draw):
    """生成带有持仓的有效 Account 对象"""
    initial_cash = draw(st.floats(min_value=10000.0, max_value=1000000.0, allow_nan=False, allow_infinity=False))
    initial_cash = round(initial_cash, 2)
    
    account = Account(initial_cash=initial_cash)
    
    # 随机生成 0-5 个持仓
    num_positions = draw(st.integers(min_value=0, max_value=5))
    codes = ["600519", "000001", "300750", "601318", "002594"]
    
    for i in range(num_positions):
        code = codes[i]
        position = draw(valid_position())
        position.code = code  # 确保代码唯一
        account.positions[code] = position
    
    # 随机调整现金（模拟交易后的状态）
    cash_adjustment = draw(st.floats(min_value=-initial_cash * 0.5, max_value=initial_cash * 0.5, allow_nan=False, allow_infinity=False))
    account.cash = max(0, initial_cash + cash_adjustment)
    
    return account


class TestAccountTotalAssetsInvariant:
    """
    Property 1: 账户总资产不变量
    Feature: stock-trading-simulator, Property 1: 账户总资产不变量
    **Validates: Requirements 2.4**
    
    验证 total_assets == cash + total_market_value
    """
    
    @settings(max_examples=100)
    @given(account=valid_account_with_positions())
    def test_total_assets_equals_cash_plus_market_value(self, account: Account):
        """
        验证总资产等于现金加持仓市值。
        
        *For any* 账户状态，总资产应始终等于可用现金加上所有持仓市值的总和。
        total_assets == cash + sum(position.quantity * position.current_price for position in positions)
        """
        expected_total_assets = account.cash + sum(
            p.quantity * p.current_price for p in account.positions.values()
        )
        actual_total_assets = account.total_assets
        
        assert abs(actual_total_assets - expected_total_assets) < 0.01, \
            f"总资产计算错误: 期望 {expected_total_assets}, 实际 {actual_total_assets}"
    
    @settings(max_examples=100)
    @given(account=valid_account_with_positions())
    def test_total_market_value_calculation(self, account: Account):
        """
        验证持仓总市值计算正确。
        
        *For any* 账户状态，持仓总市值应等于所有持仓市值之和。
        """
        expected_market_value = sum(p.market_value for p in account.positions.values())
        actual_market_value = account.total_market_value
        
        assert abs(actual_market_value - expected_market_value) < 0.01, \
            f"持仓总市值计算错误: 期望 {expected_market_value}, 实际 {actual_market_value}"



class TestTradeFeeCalculation:
    """
    Property 2: 交易费用计算正确性
    Feature: stock-trading-simulator, Property 2: 交易费用计算正确性
    **Validates: Requirements 2.5, 2.6**
    
    验证买入佣金和卖出费用计算正确：
    - 买入佣金 = max(amount * 0.00025, 5.0)
    - 卖出费用 = max(amount * 0.00025, 5.0) + amount * 0.0005
    """
    
    @settings(max_examples=100)
    @given(amount=st.floats(min_value=100.0, max_value=10000000.0, allow_nan=False, allow_infinity=False))
    def test_buy_fee_calculation(self, amount: float):
        """
        验证买入手续费计算正确。
        
        *For any* 交易金额 amount：
        买入佣金 = max(amount * 0.00025, 5.0)
        """
        account = Account()
        
        expected_fee = max(amount * 0.00025, 5.0)
        actual_fee = account.calculate_buy_fee(amount)
        
        assert abs(actual_fee - expected_fee) < 0.01, \
            f"买入手续费计算错误: 期望 {expected_fee}, 实际 {actual_fee}"
    
    @settings(max_examples=100)
    @given(amount=st.floats(min_value=100.0, max_value=10000000.0, allow_nan=False, allow_infinity=False))
    def test_sell_fee_calculation(self, amount: float):
        """
        验证卖出手续费计算正确。
        
        *For any* 交易金额 amount：
        卖出费用 = max(amount * 0.00025, 5.0) + amount * 0.0005
        """
        account = Account()
        
        commission = max(amount * 0.00025, 5.0)
        stamp_tax = amount * 0.0005
        expected_fee = commission + stamp_tax
        actual_fee = account.calculate_sell_fee(amount)
        
        assert abs(actual_fee - expected_fee) < 0.01, \
            f"卖出手续费计算错误: 期望 {expected_fee}, 实际 {actual_fee}"
    
    @settings(max_examples=100)
    @given(amount=st.floats(min_value=100.0, max_value=10000000.0, allow_nan=False, allow_infinity=False))
    def test_sell_fee_greater_than_buy_fee(self, amount: float):
        """
        验证卖出费用大于买入费用（因为包含印花税）。
        
        *For any* 交易金额 amount：
        卖出费用 > 买入费用（因为卖出包含印花税）
        """
        account = Account()
        
        buy_fee = account.calculate_buy_fee(amount)
        sell_fee = account.calculate_sell_fee(amount)
        
        assert sell_fee > buy_fee, \
            f"卖出费用应大于买入费用: 买入 {buy_fee}, 卖出 {sell_fee}"
    
    @settings(max_examples=100)
    @given(amount=st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    def test_minimum_commission_applied(self, amount: float):
        """
        验证最低佣金限制生效。
        
        *For any* 小额交易金额，佣金应不低于最低佣金（5元）。
        """
        account = Account()
        
        buy_fee = account.calculate_buy_fee(amount)
        
        # 对于小额交易，佣金应为最低佣金
        if amount * 0.00025 < 5.0:
            assert buy_fee == 5.0, \
                f"小额交易应收取最低佣金5元: 实际 {buy_fee}"


class TestAccountSerializationRoundTrip:
    """
    Property 16: 账户序列化 Round-Trip
    Feature: stock-trading-simulator, Property 16: 账户序列化 Round-Trip
    **Validates: Requirements 9.2, 9.3**
    
    验证序列化后反序列化得到等价账户：
    - Account.from_dict(account.to_dict()) 应产生等价的账户状态
    - 所有字段值应保持不变
    """
    
    @settings(max_examples=100)
    @given(account=valid_account_with_positions())
    def test_serialization_round_trip(self, account: Account):
        """
        验证账户序列化后反序列化得到等价账户。
        
        *For any* 有效的账户状态 account：
        Account.from_dict(account.to_dict()) 应产生等价的账户状态
        """
        # 序列化然后反序列化
        serialized = account.to_dict()
        restored = Account.from_dict(serialized)
        
        # 验证基本属性
        assert restored.initial_cash == account.initial_cash, \
            f"initial_cash 不匹配: 期望 {account.initial_cash}, 实际 {restored.initial_cash}"
        
        assert abs(restored.cash - account.cash) < 0.01, \
            f"cash 不匹配: 期望 {account.cash}, 实际 {restored.cash}"
        
        # 验证费用配置
        assert restored.fee_config.stamp_tax_rate == account.fee_config.stamp_tax_rate, \
            f"stamp_tax_rate 不匹配"
        assert restored.fee_config.commission_rate == account.fee_config.commission_rate, \
            f"commission_rate 不匹配"
        assert restored.fee_config.min_commission == account.fee_config.min_commission, \
            f"min_commission 不匹配"
        
        # 验证持仓数量
        assert len(restored.positions) == len(account.positions), \
            f"持仓数量不匹配: 期望 {len(account.positions)}, 实际 {len(restored.positions)}"
        
        # 验证每个持仓
        for code, original_pos in account.positions.items():
            assert code in restored.positions, f"持仓 {code} 丢失"
            restored_pos = restored.positions[code]
            
            assert restored_pos.code == original_pos.code, f"持仓代码不匹配"
            assert restored_pos.quantity == original_pos.quantity, f"持仓数量不匹配"
            assert abs(restored_pos.cost_price - original_pos.cost_price) < 0.01, f"成本价不匹配"
            assert abs(restored_pos.current_price - original_pos.current_price) < 0.01, f"当前价不匹配"
            assert restored_pos.buy_date == original_pos.buy_date, f"买入日期不匹配"
    
    @settings(max_examples=100)
    @given(account=valid_account_with_positions())
    def test_total_assets_preserved_after_round_trip(self, account: Account):
        """
        验证序列化后总资产保持不变。
        
        *For any* 有效的账户状态 account：
        序列化后反序列化的账户总资产应与原账户相等
        """
        serialized = account.to_dict()
        restored = Account.from_dict(serialized)
        
        assert abs(restored.total_assets - account.total_assets) < 0.01, \
            f"总资产不匹配: 期望 {account.total_assets}, 实际 {restored.total_assets}"
    
    @settings(max_examples=100)
    @given(account=valid_account_with_positions())
    def test_double_round_trip(self, account: Account):
        """
        验证双重序列化后仍然等价。
        
        *For any* 有效的账户状态 account：
        两次序列化/反序列化后应与原账户等价
        """
        # 第一次 round-trip
        restored1 = Account.from_dict(account.to_dict())
        # 第二次 round-trip
        restored2 = Account.from_dict(restored1.to_dict())
        
        assert abs(restored2.cash - account.cash) < 0.01, "双重 round-trip 后 cash 不匹配"
        assert restored2.initial_cash == account.initial_cash, "双重 round-trip 后 initial_cash 不匹配"
        assert len(restored2.positions) == len(account.positions), "双重 round-trip 后持仓数量不匹配"
