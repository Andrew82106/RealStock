"""
做T服务属性测试
Property 7: T-Trade Detection Accuracy
Property 8: T-Trade Profit Calculation
Property 9: T-Trade Achievement Thresholds
Validates: Requirements 7.1, 7.7, 8.1-8.6
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.services.t_trade_models import TTradeRecord, TTradeStatistics, TradeRecord
from api.services.t_trade_service import TTradeService
from api.services.achievement_models import AchievementProgress, AchievementContext
from api.services.achievement_service import AchievementService


# ============ Strategies ============

@st.composite
def trade_record_strategy(draw, date: str = None, code: str = None, order_type: str = None):
    """生成随机交易记录"""
    if date is None:
        date = draw(st.dates(
            min_value=datetime(2024, 1, 1).date(),
            max_value=datetime(2024, 12, 31).date()
        )).isoformat()
    
    if code is None:
        code = draw(st.text(min_size=6, max_size=6, alphabet='0123456789'))
    
    if order_type is None:
        order_type = draw(st.sampled_from(["buy", "sell"]))
    
    hour = draw(st.integers(min_value=9, max_value=15))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    timestamp = f"{date}T{hour:02d}:{minute:02d}:{second:02d}"
    
    return TradeRecord(
        order_id=draw(st.text(min_size=8, max_size=16, alphabet='abcdef0123456789')),
        code=code,
        order_type=order_type,
        price=draw(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        quantity=draw(st.integers(min_value=100, max_value=10000)) // 100 * 100,  # 整百
        fee=draw(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)),
        timestamp=timestamp,
    )


@st.composite
def t_trade_pair_strategy(draw):
    """生成一对做T交易（先卖后买）"""
    date = draw(st.dates(
        min_value=datetime(2024, 1, 1).date(),
        max_value=datetime(2024, 12, 31).date()
    )).isoformat()
    code = draw(st.text(min_size=6, max_size=6, alphabet='0123456789'))
    
    # 卖出交易（早于买入）
    sell_hour = draw(st.integers(min_value=9, max_value=13))
    sell_minute = draw(st.integers(min_value=0, max_value=59))
    sell_timestamp = f"{date}T{sell_hour:02d}:{sell_minute:02d}:00"
    
    # 买入交易（晚于卖出）
    buy_hour = draw(st.integers(min_value=sell_hour + 1, max_value=15))
    buy_minute = draw(st.integers(min_value=0, max_value=59))
    buy_timestamp = f"{date}T{buy_hour:02d}:{buy_minute:02d}:00"
    
    quantity = draw(st.integers(min_value=100, max_value=10000)) // 100 * 100
    
    sell_trade = TradeRecord(
        order_id=f"sell_{draw(st.text(min_size=8, max_size=8, alphabet='0123456789'))}",
        code=code,
        order_type="sell",
        price=draw(st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        quantity=quantity,
        fee=draw(st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False)),
        timestamp=sell_timestamp,
    )
    
    buy_trade = TradeRecord(
        order_id=f"buy_{draw(st.text(min_size=8, max_size=8, alphabet='0123456789'))}",
        code=code,
        order_type="buy",
        price=draw(st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        quantity=quantity,
        fee=draw(st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False)),
        timestamp=buy_timestamp,
    )
    
    return sell_trade, buy_trade


# ============ Property Tests ============

class TestTTradeDetectionAccuracy:
    """
    Property 7: T-Trade Detection Accuracy
    For any trade history, a T-trade SHALL be detected if and only if there exists
    a sell order followed by a buy order for the same stock on the same trading day.
    """
    
    @given(t_trade_pair_strategy())
    @settings(max_examples=100)
    def test_detects_valid_t_trade(self, trade_pair):
        """Feature: achievement-system, Property 7: T-Trade Detection Accuracy"""
        sell_trade, buy_trade = trade_pair
        service = TTradeService()
        
        # 检测做T
        t_trades = service.detect_t_trades([sell_trade, buy_trade])
        
        # 应该检测到一个做T
        assert len(t_trades) == 1
        t_trade = t_trades[0]
        
        # 验证做T记录的属性
        assert t_trade.stock_code == sell_trade.code
        assert t_trade.sell_price == sell_trade.price
        assert t_trade.buy_price == buy_trade.price
        assert t_trade.quantity == min(sell_trade.quantity, buy_trade.quantity)
        assert t_trade.trade_date == sell_trade.trade_date
    
    def test_no_t_trade_for_buy_only(self):
        """只有买入不应检测到做T"""
        service = TTradeService()
        
        buy_trade = TradeRecord(
            order_id="buy_001",
            code="000001",
            order_type="buy",
            price=10.0,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-15T10:00:00",
        )
        
        t_trades = service.detect_t_trades([buy_trade])
        assert len(t_trades) == 0
    
    def test_no_t_trade_for_sell_only(self):
        """只有卖出不应检测到做T"""
        service = TTradeService()
        
        sell_trade = TradeRecord(
            order_id="sell_001",
            code="000001",
            order_type="sell",
            price=10.0,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-15T10:00:00",
        )
        
        t_trades = service.detect_t_trades([sell_trade])
        assert len(t_trades) == 0
    
    def test_no_t_trade_for_different_days(self):
        """不同日期的交易不应检测为做T"""
        service = TTradeService()
        
        sell_trade = TradeRecord(
            order_id="sell_001",
            code="000001",
            order_type="sell",
            price=10.0,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-15T10:00:00",
        )
        
        buy_trade = TradeRecord(
            order_id="buy_001",
            code="000001",
            order_type="buy",
            price=9.5,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-16T10:00:00",  # 不同日期
        )
        
        t_trades = service.detect_t_trades([sell_trade, buy_trade])
        assert len(t_trades) == 0
    
    def test_no_t_trade_for_different_stocks(self):
        """不同股票的交易不应检测为做T"""
        service = TTradeService()
        
        sell_trade = TradeRecord(
            order_id="sell_001",
            code="000001",
            order_type="sell",
            price=10.0,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-15T10:00:00",
        )
        
        buy_trade = TradeRecord(
            order_id="buy_001",
            code="000002",  # 不同股票
            order_type="buy",
            price=9.5,
            quantity=100,
            fee=5.0,
            timestamp="2024-01-15T11:00:00",
        )
        
        t_trades = service.detect_t_trades([sell_trade, buy_trade])
        assert len(t_trades) == 0


class TestTTradeProfitCalculation:
    """
    Property 8: T-Trade Profit Calculation
    For any T-trade record, the profit SHALL equal
    (sell_price - buy_price) * quantity - total_fees.
    """
    
    @given(
        st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        st.integers(min_value=100, max_value=10000),
        st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_profit_calculation(self, sell_price, buy_price, quantity, sell_fee, buy_fee):
        """Feature: achievement-system, Property 8: T-Trade Profit Calculation"""
        quantity = quantity // 100 * 100  # 整百
        assume(quantity >= 100)
        
        service = TTradeService()
        
        sell_trade = TradeRecord(
            order_id="sell_001",
            code="000001",
            order_type="sell",
            price=sell_price,
            quantity=quantity,
            fee=sell_fee,
            timestamp="2024-01-15T10:00:00",
        )
        
        buy_trade = TradeRecord(
            order_id="buy_001",
            code="000001",
            order_type="buy",
            price=buy_price,
            quantity=quantity,
            fee=buy_fee,
            timestamp="2024-01-15T11:00:00",
        )
        
        t_trades = service.detect_t_trades([sell_trade, buy_trade])
        assert len(t_trades) == 1
        
        t_trade = t_trades[0]
        
        # 验证盈亏计算公式
        expected_profit = (sell_price - buy_price) * quantity - sell_fee - buy_fee
        assert abs(t_trade.profit - expected_profit) < 0.01  # 允许浮点误差


class TestTTradeStatisticsCalculation:
    """测试做T统计计算"""
    
    def test_statistics_with_mixed_results(self):
        """测试混合结果的统计"""
        service = TTradeService()
        
        # 创建一些做T记录
        t_trades = [
            TTradeRecord(
                id="t_001",
                stock_code="000001",
                sell_price=10.0,
                buy_price=9.5,
                quantity=100,
                sell_fee=5.0,
                buy_fee=5.0,
                profit=40.0,  # 盈利
                trade_date="2024-01-15",
                sell_time="2024-01-15T10:00:00",
                buy_time="2024-01-15T11:00:00",
            ),
            TTradeRecord(
                id="t_002",
                stock_code="000001",
                sell_price=10.0,
                buy_price=10.5,
                quantity=100,
                sell_fee=5.0,
                buy_fee=5.0,
                profit=-60.0,  # 亏损
                trade_date="2024-01-16",
                sell_time="2024-01-16T10:00:00",
                buy_time="2024-01-16T11:00:00",
            ),
        ]
        
        stats = service.calculate_statistics(t_trades)
        
        assert stats.total_trades == 2
        assert stats.successful_trades == 1
        assert stats.failed_trades == 1
        assert stats.success_rate == 50.0
        assert stats.total_profit == -20.0
        assert stats.best_trade_profit == 40.0
        assert stats.worst_trade_loss == -60.0
    
    def test_empty_statistics(self):
        """测试空统计"""
        service = TTradeService()
        stats = service.calculate_statistics([])
        
        assert stats.total_trades == 0
        assert stats.successful_trades == 0
        assert stats.success_rate == 0.0
        assert stats.total_profit == 0.0


class TestTTradeAchievementThresholds:
    """
    Property 9: T-Trade Achievement Thresholds
    For any T-trade statistics with S successful trades and R success rate,
    the Achievement_System SHALL unlock exactly the T-trade achievements
    whose conditions are satisfied.
    """
    
    @given(
        st.integers(min_value=0, max_value=150),
        st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_t_trade_count_thresholds(self, successful_trades: int, success_rate: float):
        """Feature: achievement-system, Property 9: T-Trade Achievement Thresholds"""
        achievement_service = AchievementService()
        progress = achievement_service.create_empty_progress()
        
        # 计算总交易数（基于成功率）
        if success_rate >= 1:
            total_trades = int(successful_trades / (success_rate / 100)) if success_rate < 100 else successful_trades
        else:
            total_trades = successful_trades + 10  # 如果成功率太低，假设有一些失败的交易
        
        total_trades = max(total_trades, successful_trades)
        
        context = AchievementContext(
            total_t_trades=total_trades,
            successful_t_trades=successful_trades,
            t_trade_success_rate=success_rate,
        )
        
        achievement_service.check_and_unlock_achievements(progress, context)
        
        # 验证做T新手 (1次)
        if total_trades >= 1:
            assert progress.is_unlocked("t_trade_beginner")
        else:
            assert not progress.is_unlocked("t_trade_beginner")
        
        # 验证做T学徒 (10次成功)
        if successful_trades >= 10:
            assert progress.is_unlocked("t_trade_apprentice")
        else:
            assert not progress.is_unlocked("t_trade_apprentice")
        
        # 验证做T专家 (50次成功)
        if successful_trades >= 50:
            assert progress.is_unlocked("t_trade_expert")
        else:
            assert not progress.is_unlocked("t_trade_expert")
        
        # 验证做T大师 (100次成功)
        if successful_trades >= 100:
            assert progress.is_unlocked("t_trade_master")
        else:
            assert not progress.is_unlocked("t_trade_master")
    
    @given(
        st.integers(min_value=20, max_value=100),
        st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_t_trade_success_rate_thresholds(self, total_trades: int, success_rate: float):
        """测试做T成功率成就阈值"""
        achievement_service = AchievementService()
        progress = achievement_service.create_empty_progress()
        
        successful_trades = int(total_trades * success_rate / 100)
        
        context = AchievementContext(
            total_t_trades=total_trades,
            successful_t_trades=successful_trades,
            t_trade_success_rate=success_rate,
        )
        
        achievement_service.check_and_unlock_achievements(progress, context)
        
        # 稳定做T者 (60%成功率，至少20次)
        if total_trades >= 20 and success_rate >= 60:
            assert progress.is_unlocked("consistent_t_trader")
        else:
            assert not progress.is_unlocked("consistent_t_trader")
        
        # 做T完美主义者 (80%成功率，至少50次)
        if total_trades >= 50 and success_rate >= 80:
            assert progress.is_unlocked("t_trade_perfectionist")
        else:
            assert not progress.is_unlocked("t_trade_perfectionist")


class TestTTradeRecordRoundTrip:
    """测试做T记录序列化往返"""
    
    def test_t_trade_record_round_trip(self):
        """测试TTradeRecord序列化往返"""
        original = TTradeRecord(
            id="t_001",
            stock_code="000001",
            sell_price=10.5,
            buy_price=10.0,
            quantity=100,
            sell_fee=5.0,
            buy_fee=5.0,
            profit=40.0,
            trade_date="2024-01-15",
            sell_time="2024-01-15T10:00:00",
            buy_time="2024-01-15T11:00:00",
        )
        
        data = original.to_dict()
        restored = TTradeRecord.from_dict(data)
        
        assert restored.id == original.id
        assert restored.stock_code == original.stock_code
        assert restored.sell_price == original.sell_price
        assert restored.buy_price == original.buy_price
        assert restored.quantity == original.quantity
        assert restored.profit == original.profit
    
    def test_t_trade_statistics_round_trip(self):
        """测试TTradeStatistics序列化往返"""
        original = TTradeStatistics(
            total_trades=10,
            successful_trades=7,
            failed_trades=3,
            success_rate=70.0,
            total_profit=1000.0,
            total_fees=100.0,
            best_trade_profit=500.0,
            worst_trade_loss=-100.0,
            average_profit=100.0,
            trades=[],
        )
        
        data = original.to_dict()
        restored = TTradeStatistics.from_dict(data)
        
        assert restored.total_trades == original.total_trades
        assert restored.successful_trades == original.successful_trades
        assert restored.success_rate == original.success_rate
        assert restored.total_profit == original.total_profit
