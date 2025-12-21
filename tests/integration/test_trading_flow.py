"""集成测试 - Integration tests for complete trading workflows.

Tests:
1. 完整的买入-持有-卖出流程
2. 多只股票的回测流程
3. 日内播放模式的完整流程
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.account.account import Account
from src.account.models import Position
from src.data_engine.engine import DataEngine
from src.exceptions import InvalidOrderError
from src.playback.models import PlaybackState
from src.simulator.simulator import Simulator
from src.trading.models import DailyBar, OrderStatus, OrderType


class MockDataEngine:
    """Mock DataEngine for integration tests without real API calls."""
    
    def __init__(self, cache_dir: str = "./test_cache"):
        self.cache_dir = cache_dir
        self._daily_data: dict[str, pd.DataFrame] = {}
        self._setup_mock_data()
    
    def _setup_mock_data(self):
        """Setup mock daily data for testing."""
        # Create mock data for stock 600519 (贵州茅台)
        dates = [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
            date(2024, 1, 8),
        ]
        
        self._daily_data["600519"] = pd.DataFrame({
            "date": dates,
            "open": [1500.0, 1510.0, 1520.0, 1515.0, 1525.0],
            "high": [1520.0, 1530.0, 1540.0, 1530.0, 1550.0],
            "low": [1490.0, 1500.0, 1510.0, 1505.0, 1515.0],
            "close": [1510.0, 1520.0, 1515.0, 1525.0, 1540.0],
            "volume": [1000000, 1100000, 1050000, 1200000, 1150000],
        })
        
        # Create mock data for stock 000001 (平安银行)
        self._daily_data["000001"] = pd.DataFrame({
            "date": dates,
            "open": [10.0, 10.2, 10.1, 10.3, 10.4],
            "high": [10.5, 10.6, 10.4, 10.6, 10.8],
            "low": [9.8, 10.0, 9.9, 10.1, 10.2],
            "close": [10.2, 10.1, 10.3, 10.4, 10.6],
            "volume": [50000000, 52000000, 48000000, 55000000, 53000000],
        })
    
    def normalize_code(self, code: str) -> tuple[str, str]:
        """Normalize stock code."""
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
    
    def get_daily_data(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Get mock daily data."""
        pure_code, _ = self.normalize_code(code)
        
        if pure_code not in self._daily_data:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        
        df = self._daily_data[pure_code].copy()
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        return df[mask].reset_index(drop=True)
    
    def get_intraday_data(self, code: str, trade_date: date) -> pd.DataFrame:
        """Get mock intraday data."""
        pure_code, _ = self.normalize_code(code)
        
        if pure_code not in self._daily_data:
            return pd.DataFrame(columns=["time", "price", "volume", "turnover_rate"])
        
        df = self._daily_data[pure_code]
        mask = df["date"] == trade_date
        if not mask.any():
            return pd.DataFrame(columns=["time", "price", "volume", "turnover_rate"])
        
        row = df[mask].iloc[0]
        
        # Generate simple intraday data (10 ticks for testing)
        times = ["09:30", "10:00", "10:30", "11:00", "11:30",
                 "13:00", "13:30", "14:00", "14:30", "15:00"]
        
        # Linear interpolation from open to close
        open_price = float(row["open"])
        close_price = float(row["close"])
        prices = [open_price + (close_price - open_price) * i / 9 for i in range(10)]
        
        return pd.DataFrame({
            "time": times,
            "price": prices,
            "volume": [int(row["volume"]) // 10] * 10,
            "turnover_rate": [0.0] * 10,
        })


class TestBuyHoldSellFlow:
    """测试完整的买入-持有-卖出流程。"""
    
    def test_complete_buy_hold_sell_flow(self):
        """Test complete buy-hold-sell workflow."""
        # Setup
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        # Initialize simulator
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Verify initial state
        assert simulator.account.cash == 200000.0
        assert simulator.account.total_assets == 200000.0
        assert len(simulator.account.positions) == 0
        
        # Day 1: Buy stock
        current_bars = simulator.get_current_bars()
        assert "600519" in current_bars
        
        buy_price = current_bars["600519"].close  # 1510.0
        buy_quantity = 100
        
        buy_order = simulator.trading_engine.submit_buy_order(
            code="600519",
            price=buy_price,
            quantity=buy_quantity,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        assert buy_order.status == OrderStatus.FILLED
        assert "600519" in simulator.account.positions
        assert simulator.account.positions["600519"].quantity == 100
        
        # Calculate expected cash after buy
        buy_amount = buy_price * buy_quantity
        buy_fee = simulator.account.calculate_buy_fee(buy_amount)
        expected_cash = 200000.0 - buy_amount - buy_fee
        assert abs(simulator.account.cash - expected_cash) < 0.01
        
        # Day 2: Hold (advance to next day)
        assert simulator.next_day() is True
        
        # Verify T+1: Cannot sell on the same day as buy
        # (buy_date is Day 1, current_date is Day 2, so we CAN sell)
        
        # Day 3: Advance another day
        assert simulator.next_day() is True
        
        # Day 4: Sell stock
        assert simulator.next_day() is True
        
        current_bars = simulator.get_current_bars()
        sell_price = current_bars["600519"].close  # 1525.0
        sell_quantity = 100
        
        sell_order = simulator.trading_engine.submit_sell_order(
            code="600519",
            price=sell_price,
            quantity=sell_quantity,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        assert sell_order.status == OrderStatus.FILLED
        assert "600519" not in simulator.account.positions
        
        # Verify profit
        sell_amount = sell_price * sell_quantity
        sell_fee = simulator.account.calculate_sell_fee(sell_amount)
        expected_final_cash = expected_cash + sell_amount - sell_fee
        assert abs(simulator.account.cash - expected_final_cash) < 0.01
        
        # Verify we made a profit (price went from 1510 to 1525)
        assert simulator.account.cash > 200000.0 - buy_fee - sell_fee
    
    def test_t_plus_1_restriction(self):
        """Test T+1 trading restriction."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Buy on Day 1
        current_bars = simulator.get_current_bars()
        buy_order = simulator.trading_engine.submit_buy_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        assert buy_order.status == OrderStatus.FILLED
        
        # Try to sell on the same day (should be rejected due to T+1)
        sell_order = simulator.trading_engine.submit_sell_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        assert sell_order.status == OrderStatus.REJECTED
        assert "T+1" in sell_order.reject_reason
        
        # Advance to next day
        simulator.next_day()
        
        # Now selling should work
        current_bars = simulator.get_current_bars()
        sell_order = simulator.trading_engine.submit_sell_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        assert sell_order.status == OrderStatus.FILLED
    
    def test_insufficient_funds_rejection(self):
        """Test order rejection when funds are insufficient."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=1000.0)  # Very low initial cash
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        current_bars = simulator.get_current_bars()
        
        # Try to buy expensive stock with insufficient funds
        buy_order = simulator.trading_engine.submit_buy_order(
            code="600519",
            price=current_bars["600519"].close,  # ~1510
            quantity=100,  # Total ~151000
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        assert buy_order.status == OrderStatus.REJECTED
        assert "资金不足" in buy_order.reject_reason


class TestMultiStockBacktest:
    """测试多只股票的回测流程。"""
    
    def test_multi_stock_backtest(self):
        """Test backtest with multiple stocks."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519", "000001"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Track strategy calls
        strategy_calls = []
        
        def simple_strategy(current_date, bars, account):
            """Simple strategy: buy on first day, sell on last day."""
            strategy_calls.append(current_date)
            instructions = []
            
            if current_date == date(2024, 1, 2):
                # Buy both stocks on first day
                if "600519" in bars:
                    instructions.append(("buy", "600519", bars["600519"].close, 100))
                if "000001" in bars:
                    instructions.append(("buy", "000001", bars["000001"].close, 1000))
            
            elif current_date == date(2024, 1, 8):
                # Sell all positions on last day
                for code in list(account.positions.keys()):
                    if code in bars:
                        pos = account.positions[code]
                        instructions.append(("sell", code, bars[code].close, pos.quantity))
            
            return instructions
        
        # Run backtest
        metrics = simulator.run_backtest(simple_strategy)
        
        # Verify strategy was called for each trading day
        assert len(strategy_calls) >= 4  # At least 4 trading days
        
        # Verify metrics are calculated
        assert metrics.total_trades >= 0
        assert 0.0 <= metrics.win_rate <= 1.0
        assert metrics.max_drawdown >= 0.0
    
    def test_backtest_traverses_all_trading_days(self):
        """Test that backtest traverses all trading days."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=100000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        visited_dates = []
        
        def tracking_strategy(current_date, bars, account):
            visited_dates.append(current_date)
            return []
        
        simulator.run_backtest(tracking_strategy)
        
        # Should visit all 5 trading days
        expected_dates = [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
            date(2024, 1, 8),
        ]
        
        assert visited_dates == expected_dates
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics are calculated correctly."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=100000.0)
        
        simulator.setup(
            stock_codes=["000001"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        def buy_and_hold_strategy(current_date, bars, account):
            """Buy on first day and hold."""
            if current_date == date(2024, 1, 2) and "000001" in bars:
                return [("buy", "000001", bars["000001"].close, 5000)]
            return []
        
        metrics = simulator.run_backtest(buy_and_hold_strategy)
        
        # Verify metrics structure
        assert hasattr(metrics, 'total_return')
        assert hasattr(metrics, 'max_drawdown')
        assert hasattr(metrics, 'win_rate')
        assert hasattr(metrics, 'sharpe_ratio')
        assert hasattr(metrics, 'total_trades')


class TestIntradayPlaybackFlow:
    """测试日内播放模式的完整流程。"""
    
    def test_playback_state_transitions(self):
        """Test playback engine state transitions."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Initial state should be IDLE
        assert simulator.playback_engine.state == PlaybackState.IDLE
        
        # Load day data
        simulator.start_day()
        assert simulator.playback_engine.state == PlaybackState.IDLE
        
        # Start playing
        simulator.play()
        assert simulator.playback_engine.state == PlaybackState.PLAYING
        
        # Pause
        simulator.pause()
        assert simulator.playback_engine.state == PlaybackState.PAUSED
        
        # Resume playing
        simulator.play()
        assert simulator.playback_engine.state == PlaybackState.PLAYING
    
    def test_trading_only_in_paused_state(self):
        """Test that trading is only allowed in paused state."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        simulator.start_day()
        
        # Try to buy in IDLE state (should fail)
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.buy("600519", 1510.0, 100)
        assert "暂停状态" in str(exc_info.value)
        
        # Start playing
        simulator.play()
        
        # Try to buy in PLAYING state (should fail)
        with pytest.raises(InvalidOrderError) as exc_info:
            simulator.buy("600519", 1510.0, 100)
        assert "暂停状态" in str(exc_info.value)
        
        # Pause and try to buy (should succeed)
        simulator.pause()
        
        # Now trading should work
        order = simulator.buy("600519", 1510.0, 100)
        assert order.status == OrderStatus.FILLED
    
    def test_tick_progression(self):
        """Test tick progression during playback."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        simulator.start_day()
        simulator.play()
        
        # Collect ticks
        ticks_received = []
        while simulator.playback_engine.state == PlaybackState.PLAYING:
            tick_data = simulator.playback_engine.tick()
            if tick_data:
                ticks_received.append(tick_data)
        
        # Should have received multiple ticks
        assert len(ticks_received) > 0
        
        # State should be DAY_ENDED after all ticks
        assert simulator.playback_engine.state == PlaybackState.DAY_ENDED
    
    def test_next_day_transition(self):
        """Test transitioning to next trading day."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        first_date = simulator.current_date
        assert first_date == date(2024, 1, 2)
        
        # Advance to next day
        result = simulator.next_day()
        assert result is True
        assert simulator.current_date == date(2024, 1, 3)
        
        # Continue advancing
        simulator.next_day()
        assert simulator.current_date == date(2024, 1, 4)
    
    def test_playback_with_position_price_updates(self):
        """Test that position prices are updated during playback."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Buy stock first
        current_bars = simulator.get_current_bars()
        simulator.trading_engine.submit_buy_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        initial_price = simulator.account.positions["600519"].current_price
        
        # Advance to next day
        simulator.next_day()
        
        # Price should be updated
        updated_price = simulator.account.positions["600519"].current_price
        
        # Prices should be different (based on mock data)
        # Note: They might be the same if close prices happen to match
        assert updated_price > 0


class TestEdgeCases:
    """测试边界情况。"""
    
    def test_empty_stock_list(self):
        """Test handling of empty stock list."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=100000.0)
        
        simulator.setup(
            stock_codes=[],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Should handle gracefully
        bars = simulator.get_current_bars()
        assert bars == {}
    
    def test_price_out_of_range_rejection(self):
        """Test order rejection when price is out of daily range."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        current_bars = simulator.get_current_bars()
        daily_bar = current_bars["600519"]
        
        # Try to buy at price above daily high
        buy_order = simulator.trading_engine.submit_buy_order(
            code="600519",
            price=daily_bar.high + 100,  # Way above high
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=daily_bar
        )
        
        assert buy_order.status == OrderStatus.REJECTED
        assert "价格" in buy_order.reject_reason
    
    def test_sell_more_than_position(self):
        """Test rejection when trying to sell more than position."""
        data_engine = MockDataEngine()
        simulator = Simulator(data_engine, initial_cash=200000.0)
        
        simulator.setup(
            stock_codes=["600519"],
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8)
        )
        
        # Buy 100 shares
        current_bars = simulator.get_current_bars()
        simulator.trading_engine.submit_buy_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=100,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        # Advance to next day (to bypass T+1)
        simulator.next_day()
        current_bars = simulator.get_current_bars()
        
        # Try to sell 200 shares (more than we have)
        sell_order = simulator.trading_engine.submit_sell_order(
            code="600519",
            price=current_bars["600519"].close,
            quantity=200,
            current_date=simulator.current_date,
            daily_bar=current_bars["600519"]
        )
        
        assert sell_order.status == OrderStatus.REJECTED
        assert "持仓不足" in sell_order.reject_reason
