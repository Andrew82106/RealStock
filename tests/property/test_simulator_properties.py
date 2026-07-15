"""属性测试 - 模拟器模块 Property-based tests for simulator module."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st, assume

from src.account.account import Account
from src.account.models import Position
from src.data_engine.engine import DataEngine
from src.exceptions import InvalidOrderError
from src.playback.models import PlaybackState
from src.simulator.simulator import Simulator, PerformanceMetrics
from src.trading.models import DailyBar, OrderStatus


# 测试数据生成策略
stock_codes = st.sampled_from(["600519", "000001", "300750", "601318", "002594"])

prices = st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False).map(
    lambda x: round(x, 2)
)

quantities = st.integers(min_value=100, max_value=10000).map(lambda x: (x // 100) * 100)

cash_amounts = st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False).map(
    lambda x: round(x, 2)
)


class MockDataEngine:
    """模拟数据引擎，用于测试"""
    
    def __init__(self, cache_dir: str = "./test_cache"):
        self.cache_dir = cache_dir
    
    def get_daily_data(self, code: str, start_date: date, end_date: date, adjust: str = "qfq"):
        """返回模拟的日线数据"""
        import pandas as pd
        
        # 生成交易日列表（简化：每天都是交易日）
        dates = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # 排除周末
                dates.append(current)
            current += timedelta(days=1)
        
        if not dates:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        
        # 生成模拟数据
        data = []
        base_price = 100.0
        for d in dates:
            open_price = base_price * (1 + (hash(str(d)) % 10 - 5) / 100)
            high = open_price * 1.05
            low = open_price * 0.95
            close = open_price * (1 + (hash(str(d) + "close") % 10 - 5) / 100)
            volume = 1000000
            data.append({
                "date": d,
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume
            })
        
        return pd.DataFrame(data)
    
    def get_intraday_data(self, code: str, trade_date: date):
        """返回模拟的分时数据"""
        import pandas as pd
        
        times = []
        prices_list = []
        volumes = []
        
        # 生成 240 个数据点
        base_price = 100.0
        for i in range(240):
            if i < 120:
                hour = 9 + (i + 30) // 60
                minute = (i + 30) % 60
            else:
                hour = 13 + (i - 120) // 60
                minute = (i - 120) % 60
            
            times.append(f"{hour:02d}:{minute:02d}")
            prices_list.append(round(base_price * (1 + (i % 10 - 5) / 1000), 2))
            volumes.append(10000)
        
        return pd.DataFrame({
            "time": times,
            "price": prices_list,
            "volume": volumes,
            "turnover_rate": [0.0] * 240
        })
    
    def normalize_code(self, code: str):
        """规范化股票代码"""
        code = code.strip().lower()
        if code.startswith("sh") or code.startswith("sz"):
            market = code[:2]
            pure_code = code[2:]
        else:
            pure_code = code
            if pure_code.startswith("6"):
                market = "sh"
            else:
                market = "sz"
        return pure_code, market


class TestTradingStateRestriction:
    """
    Property 11: 交易状态限制
    Feature: stock-trading-simulator, Property 11: 交易状态限制
    **Validates: Requirements 6.3**

    验证交易状态限制（2026-07 契约更新：与前端和挂单模型对齐）：
    - PLAYING / FINISHED 状态下交易应抛出错误
    - IDLE / PAUSED / DAY_ENDED 状态下应正常处理订单
      （DAY_ENDED 允许交易对应真实券商的收盘后挂单）
    """

    @settings(max_examples=100)
    @given(
        initial_cash=cash_amounts,
        price=prices,
        quantity=quantities,
        code=stock_codes
    )
    def test_buy_raises_error_when_not_tradable(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证播放中和播放结束状态下买入抛出错误。

        *For any* 交易操作（买入）：
        如果播放状态是 PLAYING 或 FINISHED，应抛出错误
        """
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)

        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        simulator.start_day()

        # 测试 PLAYING 状态
        simulator.playback_engine.state = PlaybackState.PLAYING
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.buy(code, price, quantity)
        assert "播放中无法交易" in str(exc_info.value)

        # 测试 FINISHED 状态
        simulator.playback_engine.state = PlaybackState.FINISHED
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.buy(code, price, quantity)
        assert "无法交易" in str(exc_info.value)

    @settings(max_examples=100)
    @given(
        initial_cash=cash_amounts,
        price=prices,
        quantity=quantities,
        code=stock_codes
    )
    def test_sell_raises_error_when_not_tradable(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证播放中和播放结束状态下卖出抛出错误。

        *For any* 交易操作（卖出）：
        如果播放状态是 PLAYING 或 FINISHED，应抛出错误
        """
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)

        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        simulator.start_day()

        # 测试 PLAYING 状态
        simulator.playback_engine.state = PlaybackState.PLAYING
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.sell(code, price, quantity)
        assert "播放中无法交易" in str(exc_info.value)

        # 测试 FINISHED 状态
        simulator.playback_engine.state = PlaybackState.FINISHED
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.sell(code, price, quantity)
        assert "无法交易" in str(exc_info.value)

    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_buy_works_in_day_ended_state(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证收盘（DAY_ENDED）状态下可以挂单买入。

        *For any* 交易操作（买入）：
        如果播放状态是 DAY_ENDED，应正常处理订单（对应收盘后挂单）
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)

        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)

        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        simulator.start_day()

        simulator.playback_engine.state = PlaybackState.DAY_ENDED

        amount = price * quantity
        fee = simulator.account.calculate_buy_fee(amount)
        assume(simulator.account.cash >= amount + fee)

        order = simulator.buy(code, price, quantity)

        assert order is not None
        assert order.status in [OrderStatus.FILLED, OrderStatus.PENDING, OrderStatus.REJECTED]
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_buy_works_when_paused(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证暂停状态下买入正常工作。
        
        *For any* 交易操作（买入）：
        如果播放状态是 PAUSED，应正常处理订单
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        simulator.start_day()
        
        # 设置为暂停状态
        simulator.playback_engine.state = PlaybackState.PAUSED
        
        # 确保资金充足
        amount = price * quantity
        fee = simulator.account.calculate_buy_fee(amount)
        assume(simulator.account.cash >= amount + fee)
        
        # 买入应该正常工作（不抛出 InvalidOrderError）
        order = simulator.buy(code, price, quantity)

        # 订单应该被处理（可能成交、挂单或被拒绝，但不应抛出状态错误）
        assert order is not None
        assert order.status in [OrderStatus.FILLED, OrderStatus.PENDING, OrderStatus.REJECTED]
    
    @settings(max_examples=100)
    @given(
        initial_cash=st.floats(min_value=100000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        price=st.floats(min_value=10.0, max_value=200.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_sell_works_when_paused(
        self, initial_cash: float, price: float, quantity: int, code: str
    ):
        """
        验证暂停状态下卖出正常工作。
        
        *For any* 交易操作（卖出）：
        如果播放状态是 PAUSED，应正常处理订单
        """
        initial_cash = round(initial_cash, 2)
        price = round(price, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        simulator.start_day()
        
        # 设置为暂停状态
        simulator.playback_engine.state = PlaybackState.PAUSED
        
        # 卖出应该正常工作（不抛出 InvalidOrderError 关于状态的错误）
        # 可能因为没有持仓而被拒绝，但不应抛出状态错误
        order = simulator.sell(code, price, quantity)

        # 订单应该被处理
        assert order is not None
        assert order.status in [OrderStatus.FILLED, OrderStatus.PENDING, OrderStatus.REJECTED]



class TestBacktestTraversalCompleteness:
    """
    Property 12: 回测遍历完整性
    Feature: stock-trading-simulator, Property 12: 回测遍历完整性
    **Validates: Requirements 7.1, 7.3**
    
    验证策略函数在每个交易日被调用：
    - run_backtest() 应遍历该范围内的所有交易日
    - 策略函数应在每个交易日被调用一次
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=cash_amounts,
        code=stock_codes,
        num_days=st.integers(min_value=5, max_value=30)
    )
    def test_strategy_called_for_each_trading_day(
        self, initial_cash: float, code: str, num_days: int
    ):
        """
        验证策略函数在每个交易日被调用一次。
        
        *For any* 策略函数和时间范围 [start_date, end_date]：
        策略函数应在每个交易日被调用一次
        """
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = start_date + timedelta(days=num_days)
        simulator.setup([code], start_date, end_date)
        
        # 记录策略被调用的日期
        called_dates = []
        
        def tracking_strategy(current_date, bars, account):
            called_dates.append(current_date)
            return []  # 不执行任何交易
        
        # 运行回测
        simulator.run_backtest(tracking_strategy)
        
        # 验证策略在每个交易日被调用
        expected_dates = simulator.trading_dates
        
        # 策略应该在每个交易日被调用一次
        assert len(called_dates) == len(expected_dates), \
            f"策略调用次数不正确: 期望 {len(expected_dates)}, 实际 {len(called_dates)}"
        
        # 验证调用的日期与交易日匹配
        for expected, actual in zip(expected_dates, called_dates):
            assert expected == actual, \
                f"策略调用日期不匹配: 期望 {expected}, 实际 {actual}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=cash_amounts,
        code=stock_codes,
        num_days=st.integers(min_value=5, max_value=30)
    )
    def test_backtest_traverses_all_trading_days(
        self, initial_cash: float, code: str, num_days: int
    ):
        """
        验证回测遍历所有交易日。
        
        *For any* 策略函数和时间范围 [start_date, end_date]：
        run_backtest() 应遍历该范围内的所有交易日
        """
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = start_date + timedelta(days=num_days)
        simulator.setup([code], start_date, end_date)
        
        # 记录遍历的日期
        traversed_dates = []
        
        def tracking_strategy(current_date, bars, account):
            traversed_dates.append(current_date)
            return []
        
        # 运行回测
        simulator.run_backtest(tracking_strategy)
        
        # 验证遍历了所有交易日
        expected_trading_days = simulator.trading_dates
        
        assert set(traversed_dates) == set(expected_trading_days), \
            f"未遍历所有交易日: 期望 {expected_trading_days}, 实际 {traversed_dates}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=cash_amounts,
        code=stock_codes,
        num_days=st.integers(min_value=5, max_value=30)
    )
    def test_strategy_receives_correct_bars(
        self, initial_cash: float, code: str, num_days: int
    ):
        """
        验证策略函数接收正确的行情数据。
        
        *For any* 策略函数和时间范围：
        策略函数应接收当日的行情数据
        """
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = start_date + timedelta(days=num_days)
        simulator.setup([code], start_date, end_date)
        
        # 记录接收到的行情数据
        received_bars = []
        
        def tracking_strategy(current_date, bars, account):
            received_bars.append((current_date, bars.copy() if bars else {}))
            return []
        
        # 运行回测
        simulator.run_backtest(tracking_strategy)
        
        # 验证每次调用都接收到了行情数据
        for call_date, bars in received_bars:
            # 应该有当前股票的行情
            if code in bars:
                bar = bars[code]
                assert bar.date == call_date, \
                    f"行情日期不匹配: 期望 {call_date}, 实际 {bar.date}"
                assert bar.high >= bar.low, \
                    f"行情数据无效: high={bar.high} < low={bar.low}"
                assert bar.high >= bar.open >= bar.low, \
                    f"开盘价超出范围: open={bar.open}, range=[{bar.low}, {bar.high}]"
                assert bar.high >= bar.close >= bar.low, \
                    f"收盘价超出范围: close={bar.close}, range=[{bar.low}, {bar.high}]"



class TestTotalReturnCalculation:
    """
    Property 13: 收益率计算正确性
    Feature: stock-trading-simulator, Property 13: 收益率计算正确性
    **Validates: Requirements 8.1**
    
    验证 total_return 计算公式正确：
    total_return = (final_assets - initial_cash) / initial_cash
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        final_multiplier=st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False)
    )
    def test_total_return_formula(
        self, initial_cash: float, final_multiplier: float
    ):
        """
        验证收益率计算公式正确。
        
        *For any* 初始资金 initial_cash 和期末总资产 final_assets：
        total_return = (final_assets - initial_cash) / initial_cash
        """
        initial_cash = round(initial_cash, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        # 模拟期末资产变化
        final_assets = initial_cash * final_multiplier
        simulator.account.cash = final_assets
        
        # 计算期望的收益率
        expected_return = (final_assets - initial_cash) / initial_cash
        
        # 获取实际计算的收益率
        actual_return = simulator._calculate_total_return()
        
        assert abs(actual_return - expected_return) < 0.0001, \
            f"收益率计算不正确: 期望 {expected_return}, 实际 {actual_return}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False)
    )
    def test_zero_return_when_no_change(self, initial_cash: float):
        """
        验证资产不变时收益率为零。
        
        *For any* 初始资金 initial_cash：
        如果期末资产等于初始资金，收益率应为 0
        """
        initial_cash = round(initial_cash, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        # 资产不变
        actual_return = simulator._calculate_total_return()
        
        assert abs(actual_return) < 0.0001, \
            f"资产不变时收益率应为 0: 实际 {actual_return}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        profit=st.floats(min_value=100.0, max_value=1000000.0, allow_nan=False, allow_infinity=False)
    )
    def test_positive_return_when_profit(self, initial_cash: float, profit: float):
        """
        验证盈利时收益率为正。
        
        *For any* 初始资金和盈利金额：
        如果期末资产大于初始资金，收益率应为正
        """
        initial_cash = round(initial_cash, 2)
        profit = round(profit, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        # 增加现金（模拟盈利）
        simulator.account.cash = initial_cash + profit
        
        actual_return = simulator._calculate_total_return()
        
        assert actual_return > 0, \
            f"盈利时收益率应为正: 实际 {actual_return}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=10000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        loss_pct=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False)
    )
    def test_negative_return_when_loss(self, initial_cash: float, loss_pct: float):
        """
        验证亏损时收益率为负。
        
        *For any* 初始资金和亏损比例：
        如果期末资产小于初始资金，收益率应为负
        """
        initial_cash = round(initial_cash, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        # 减少现金（模拟亏损）
        simulator.account.cash = initial_cash * (1 - loss_pct)
        
        actual_return = simulator._calculate_total_return()
        
        assert actual_return < 0, \
            f"亏损时收益率应为负: 实际 {actual_return}"



class TestMaxDrawdownCalculation:
    """
    Property 14: 最大回撤计算正确性
    Feature: stock-trading-simulator, Property 14: 最大回撤计算正确性
    **Validates: Requirements 8.2**
    
    验证 max_drawdown 计算正确：
    max_drawdown = max((peak - trough) / peak)
    其中 peak 是某点之前的最高值，trough 是该点之后的最低值
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_value=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        values=st.lists(
            st.floats(min_value=0.5, max_value=1.5, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50
        )
    )
    def test_max_drawdown_formula(self, initial_value: float, values: list[float]):
        """
        验证最大回撤计算公式正确。
        
        *For any* 净值序列 [v1, v2, ..., vn]：
        max_drawdown = max((peak - trough) / peak)
        """
        initial_value = round(initial_value, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_value)
        
        # 构建净值历史
        net_values = [initial_value * v for v in values]
        simulator.net_value_history = [
            (date(2024, 1, 1) + timedelta(days=i), v) for i, v in enumerate(net_values)
        ]
        
        # 手动计算期望的最大回撤
        expected_max_drawdown = 0.0
        peak = net_values[0]
        
        for value in net_values:
            if value > peak:
                peak = value
            if peak > 0:
                drawdown = (peak - value) / peak
                expected_max_drawdown = max(expected_max_drawdown, drawdown)
        
        # 获取实际计算的最大回撤
        actual_max_drawdown = simulator._calculate_max_drawdown()
        
        assert abs(actual_max_drawdown - expected_max_drawdown) < 0.0001, \
            f"最大回撤计算不正确: 期望 {expected_max_drawdown}, 实际 {actual_max_drawdown}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_value=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        growth_rates=st.lists(
            st.floats(min_value=1.0, max_value=1.1, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=20
        )
    )
    def test_zero_drawdown_when_always_increasing(
        self, initial_value: float, growth_rates: list[float]
    ):
        """
        验证净值持续上涨时回撤为零。
        
        *For any* 单调递增的净值序列：
        最大回撤应为 0
        """
        initial_value = round(initial_value, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_value)
        
        # 构建单调递增的净值历史
        net_values = [initial_value]
        for rate in growth_rates:
            net_values.append(net_values[-1] * rate)
        
        simulator.net_value_history = [
            (date(2024, 1, i + 1), v) for i, v in enumerate(net_values)
        ]
        
        actual_max_drawdown = simulator._calculate_max_drawdown()
        
        assert actual_max_drawdown == 0.0, \
            f"净值持续上涨时回撤应为 0: 实际 {actual_max_drawdown}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_value=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False),
        drop_pct=st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    def test_drawdown_equals_drop_for_simple_case(
        self, initial_value: float, drop_pct: float
    ):
        """
        验证简单下跌情况的回撤计算。
        
        *For any* 从高点下跌的净值序列：
        最大回撤应等于下跌幅度
        """
        initial_value = round(initial_value, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_value)
        
        # 构建简单的下跌序列：高点 -> 低点
        peak_value = initial_value
        trough_value = initial_value * (1 - drop_pct)
        
        simulator.net_value_history = [
            (date(2024, 1, 1), peak_value),
            (date(2024, 1, 2), trough_value)
        ]
        
        expected_drawdown = drop_pct
        actual_max_drawdown = simulator._calculate_max_drawdown()
        
        assert abs(actual_max_drawdown - expected_drawdown) < 0.0001, \
            f"简单下跌回撤计算不正确: 期望 {expected_drawdown}, 实际 {actual_max_drawdown}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_value=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    )
    def test_drawdown_non_negative(self, initial_value: float):
        """
        验证最大回撤始终非负。
        
        *For any* 净值序列：
        最大回撤应 >= 0
        """
        initial_value = round(initial_value, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_value)
        
        # 空历史
        simulator.net_value_history = []
        assert simulator._calculate_max_drawdown() >= 0
        
        # 单点历史
        simulator.net_value_history = [(date(2024, 1, 1), initial_value)]
        assert simulator._calculate_max_drawdown() >= 0
        
        # 多点历史
        simulator.net_value_history = [
            (date(2024, 1, 1), initial_value),
            (date(2024, 1, 2), initial_value * 1.1),
            (date(2024, 1, 3), initial_value * 0.9)
        ]
        assert simulator._calculate_max_drawdown() >= 0
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_value=st.floats(min_value=10000.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    )
    def test_drawdown_at_most_one(self, initial_value: float):
        """
        验证最大回撤不超过 100%。
        
        *For any* 净值序列（净值 > 0）：
        最大回撤应 <= 1.0
        """
        initial_value = round(initial_value, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_value)
        
        # 构建各种净值历史
        simulator.net_value_history = [
            (date(2024, 1, 1), initial_value),
            (date(2024, 1, 2), initial_value * 0.1),  # 90% 下跌
            (date(2024, 1, 3), initial_value * 0.05)  # 95% 下跌
        ]
        
        actual_max_drawdown = simulator._calculate_max_drawdown()
        
        assert actual_max_drawdown <= 1.0, \
            f"最大回撤不应超过 100%: 实际 {actual_max_drawdown}"



class TestWinRateCalculation:
    """
    Property 15: 胜率计算正确性
    Feature: stock-trading-simulator, Property 15: 胜率计算正确性
    **Validates: Requirements 8.3**
    
    验证 win_rate 计算正确：
    win_rate = 盈利交易次数 / 总交易次数
    盈利交易定义为：卖出价 > 买入成本价
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        buy_price=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        sell_price_multiplier=st.floats(min_value=1.1, max_value=1.5, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_win_rate_100_when_all_profitable(
        self, initial_cash: float, buy_price: float, sell_price_multiplier: float,
        quantity: int, code: str
    ):
        """
        验证所有交易盈利时胜率为 100%。
        
        *For any* 交易记录列表：
        如果所有卖出都盈利，胜率应为 1.0
        """
        initial_cash = round(initial_cash, 2)
        buy_price = round(buy_price, 2)
        sell_price = round(buy_price * sell_price_multiplier, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        
        # 确保资金充足
        amount = buy_price * quantity
        fee = simulator.account.calculate_buy_fee(amount)
        assume(simulator.account.cash >= amount + fee)
        
        # 执行买入
        buy_order = simulator.trading_engine.submit_buy_order(
            code=code,
            price=buy_price,
            quantity=quantity,
            current_date=date(2024, 1, 2)
        )
        assume(buy_order.status == OrderStatus.FILLED)
        
        # 计算买入成本（含手续费）
        buy_cost_per_share = buy_price + buy_order.fee / quantity
        
        # 计算卖出后的净收入
        sell_amount = sell_price * quantity
        sell_fee = simulator.account.calculate_sell_fee(sell_amount)
        net_sell_price_per_share = sell_price - sell_fee / quantity
        
        # 确保卖出价格足够高以覆盖所有费用
        assume(net_sell_price_per_share > buy_cost_per_share)
        
        # 执行盈利卖出（次日）
        sell_order = simulator.trading_engine.submit_sell_order(
            code=code,
            price=sell_price,
            quantity=quantity,
            current_date=date(2024, 1, 3)
        )
        assume(sell_order.status == OrderStatus.FILLED)
        
        # 计算胜率
        win_rate, winning, losing, total = simulator._calculate_win_rate()
        
        assert total == 1, f"总交易数应为 1: 实际 {total}"
        assert winning == 1, f"盈利交易数应为 1: 实际 {winning}"
        assert losing == 0, f"亏损交易数应为 0: 实际 {losing}"
        assert win_rate == 1.0, f"胜率应为 1.0: 实际 {win_rate}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        buy_price=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        sell_price_multiplier=st.floats(min_value=0.5, max_value=0.95, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_win_rate_0_when_all_losing(
        self, initial_cash: float, buy_price: float, sell_price_multiplier: float,
        quantity: int, code: str
    ):
        """
        验证所有交易亏损时胜率为 0%。
        
        *For any* 交易记录列表：
        如果所有卖出都亏损，胜率应为 0.0
        """
        initial_cash = round(initial_cash, 2)
        buy_price = round(buy_price, 2)
        sell_price = round(buy_price * sell_price_multiplier, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        
        # 确保资金充足
        amount = buy_price * quantity
        fee = simulator.account.calculate_buy_fee(amount)
        assume(simulator.account.cash >= amount + fee)
        
        # 执行买入
        buy_order = simulator.trading_engine.submit_buy_order(
            code=code,
            price=buy_price,
            quantity=quantity,
            current_date=date(2024, 1, 2)
        )
        assume(buy_order.status == OrderStatus.FILLED)
        
        # 执行亏损卖出（次日）
        sell_order = simulator.trading_engine.submit_sell_order(
            code=code,
            price=sell_price,
            quantity=quantity,
            current_date=date(2024, 1, 3)
        )
        assume(sell_order.status == OrderStatus.FILLED)
        
        # 计算胜率
        win_rate, winning, losing, total = simulator._calculate_win_rate()
        
        assert total == 1, f"总交易数应为 1: 实际 {total}"
        assert winning == 0, f"盈利交易数应为 0: 实际 {winning}"
        assert losing == 1, f"亏损交易数应为 1: 实际 {losing}"
        assert win_rate == 0.0, f"胜率应为 0.0: 实际 {win_rate}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False)
    )
    def test_win_rate_0_when_no_trades(self, initial_cash: float):
        """
        验证无交易时胜率为 0。
        
        *For any* 空交易记录：
        胜率应为 0.0
        """
        initial_cash = round(initial_cash, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        # 不执行任何交易
        win_rate, winning, losing, total = simulator._calculate_win_rate()
        
        assert total == 0, f"总交易数应为 0: 实际 {total}"
        assert winning == 0, f"盈利交易数应为 0: 实际 {winning}"
        assert losing == 0, f"亏损交易数应为 0: 实际 {losing}"
        assert win_rate == 0.0, f"胜率应为 0.0: 实际 {win_rate}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        initial_cash=st.floats(min_value=1000000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        buy_price=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=100, max_value=1000).map(lambda x: (x // 100) * 100),
        code=stock_codes
    )
    def test_win_rate_in_valid_range(
        self, initial_cash: float, buy_price: float, quantity: int, code: str
    ):
        """
        验证胜率始终在 [0, 1] 范围内。
        
        *For any* 交易记录列表：
        胜率应在 0.0 到 1.0 之间
        """
        initial_cash = round(initial_cash, 2)
        buy_price = round(buy_price, 2)
        
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=initial_cash)
        
        start_date = date(2024, 1, 2)
        end_date = date(2024, 1, 31)
        simulator.setup([code], start_date, end_date)
        
        # 执行一些交易
        amount = buy_price * quantity
        fee = simulator.account.calculate_buy_fee(amount)
        
        if simulator.account.cash >= amount + fee:
            simulator.trading_engine.submit_buy_order(
                code=code,
                price=buy_price,
                quantity=quantity,
                current_date=date(2024, 1, 2)
            )
        
        # 计算胜率
        win_rate, winning, losing, total = simulator._calculate_win_rate()
        
        assert 0.0 <= win_rate <= 1.0, \
            f"胜率应在 [0, 1] 范围内: 实际 {win_rate}"
        assert winning >= 0, f"盈利交易数应 >= 0: 实际 {winning}"
        assert losing >= 0, f"亏损交易数应 >= 0: 实际 {losing}"
        assert total >= 0, f"总交易数应 >= 0: 实际 {total}"
        assert winning + losing == total, \
            f"盈利 + 亏损应等于总数: {winning} + {losing} != {total}"
