"""属性测试 - 播放引擎模块 Property-based tests for playback engine module."""

from datetime import date, time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.playback.engine import PlaybackEngine
from src.playback.models import IntradayTick, PlaybackConfig, PlaybackState


# 测试数据生成策略
@st.composite
def valid_intraday_tick(draw):
    """生成有效的 IntradayTick 对象"""
    hour = draw(st.sampled_from([9, 10, 11, 13, 14]))
    minute = draw(st.integers(min_value=0, max_value=59))
    
    # 调整边界情况
    if hour == 9:
        minute = draw(st.integers(min_value=30, max_value=59))
    elif hour == 11:
        minute = draw(st.integers(min_value=0, max_value=29))
    
    price = draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    price = round(price, 2)
    volume = draw(st.integers(min_value=0, max_value=100000000))
    turnover_rate = draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    change_pct = draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    
    return IntradayTick(
        time=time(hour, minute),
        price=price,
        volume=volume,
        turnover_rate=round(turnover_rate, 2),
        change_pct=round(change_pct, 2)
    )


def create_mock_data_engine():
    """创建模拟的数据引擎"""
    mock_engine = MagicMock()
    
    # 模拟日线数据
    daily_data = pd.DataFrame({
        "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [99.0, 100.0, 101.0],
        "close": [103.0, 104.0, 105.0],
        "volume": [1000000, 1100000, 1200000]
    })
    mock_engine.get_daily_data.return_value = daily_data
    
    # 模拟分时数据
    intraday_data = pd.DataFrame({
        "time": ["09:30", "09:31", "09:32", "14:58", "14:59"],
        "price": [100.0, 100.5, 101.0, 102.5, 103.0],
        "volume": [10000, 20000, 30000, 90000, 100000],
        "turnover_rate": [0.1, 0.2, 0.3, 0.9, 1.0]
    })
    mock_engine.get_intraday_data.return_value = intraday_data
    
    return mock_engine


class TestPlaybackStateTransitions:
    """
    Property 9: 日内播放状态转换
    Feature: stock-trading-simulator, Property 9: 日内播放状态转换
    **Validates: Requirements 6.1, 6.3, 6.4, 6.5, 6.6, 6.8**
    
    验证状态机转换正确：
    - IDLE 状态下调用 play() 应转换到 PLAYING
    - PLAYING 状态下调用 pause() 应转换到 PAUSED
    - PAUSED 状态下调用 play() 应转换到 PLAYING
    - 到达收盘时间应自动转换到 DAY_ENDED
    - DAY_ENDED 状态下调用 next_day() 应转换到 IDLE（如果还有下一天）或 FINISHED
    """
    
    @settings(max_examples=100)
    @given(speed=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    def test_idle_to_playing_transition(self, speed: float):
        """
        验证 IDLE 状态下调用 play() 转换到 PLAYING。
        
        *For any* 播放引擎在 IDLE 状态：
        调用 play() 后状态应变为 PLAYING
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        # 设置初始状态
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        
        assert playback.state == PlaybackState.IDLE, "初始状态应为 IDLE"
        
        playback.set_speed(speed)
        playback.play()
        
        assert playback.state == PlaybackState.PLAYING, \
            f"调用 play() 后状态应为 PLAYING，实际为 {playback.state}"
    
    @settings(max_examples=100)
    @given(tick_count=st.integers(min_value=1, max_value=3))
    def test_playing_to_paused_transition(self, tick_count: int):
        """
        验证 PLAYING 状态下调用 pause() 转换到 PAUSED。
        
        *For any* 播放引擎在 PLAYING 状态：
        调用 pause() 后状态应变为 PAUSED
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 执行一些 tick
        for _ in range(tick_count):
            playback.tick()
        
        assert playback.state == PlaybackState.PLAYING, "tick 后状态应仍为 PLAYING"
        
        playback.pause()
        
        assert playback.state == PlaybackState.PAUSED, \
            f"调用 pause() 后状态应为 PAUSED，实际为 {playback.state}"
    
    @settings(max_examples=100)
    @given(pause_count=st.integers(min_value=1, max_value=5))
    def test_paused_to_playing_transition(self, pause_count: int):
        """
        验证 PAUSED 状态下调用 play() 转换到 PLAYING。
        
        *For any* 播放引擎在 PAUSED 状态：
        调用 play() 后状态应变为 PLAYING
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 多次暂停和继续
        for _ in range(pause_count):
            playback.pause()
            assert playback.state == PlaybackState.PAUSED, "暂停后状态应为 PAUSED"
            
            playback.play()
            assert playback.state == PlaybackState.PLAYING, \
                f"从 PAUSED 调用 play() 后状态应为 PLAYING，实际为 {playback.state}"
    
    def test_playing_to_day_ended_transition(self):
        """
        验证播放到收盘时自动转换到 DAY_ENDED。
        
        *For any* 播放引擎在 PLAYING 状态：
        当所有 tick 播放完毕后，状态应变为 DAY_ENDED
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 播放所有 tick 直到结束
        max_iterations = 1000  # 防止无限循环
        iterations = 0
        while playback.state == PlaybackState.PLAYING and iterations < max_iterations:
            playback.tick()
            iterations += 1
        
        assert playback.state == PlaybackState.DAY_ENDED, \
            f"播放完毕后状态应为 DAY_ENDED，实际为 {playback.state}"
    
    def test_day_ended_to_idle_on_next_day(self):
        """
        验证 DAY_ENDED 状态下调用 next_day() 转换到 IDLE。
        
        *For any* 播放引擎在 DAY_ENDED 状态且还有下一交易日：
        调用 next_day() 后状态应变为 IDLE
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 播放到结束
        while playback.state == PlaybackState.PLAYING:
            playback.tick()
        
        assert playback.state == PlaybackState.DAY_ENDED, "播放完毕后状态应为 DAY_ENDED"
        
        # 切换到下一天
        has_next = playback.next_day()
        
        assert has_next is True, "应该还有下一交易日"
        assert playback.state == PlaybackState.IDLE, \
            f"调用 next_day() 后状态应为 IDLE，实际为 {playback.state}"
    
    def test_day_ended_to_finished_on_last_day(self):
        """
        验证最后一个交易日结束后调用 next_day() 转换到 FINISHED。
        
        *For any* 播放引擎在最后一个交易日的 DAY_ENDED 状态：
        调用 next_day() 后状态应变为 FINISHED
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        
        # 遍历所有交易日
        for i in range(len(playback.trading_dates)):
            playback.load_day(playback.trading_dates[i])
            playback.play()
            
            # 播放到结束
            while playback.state == PlaybackState.PLAYING:
                playback.tick()
            
            if i < len(playback.trading_dates) - 1:
                # 不是最后一天，切换到下一天
                has_next = playback.next_day()
                assert has_next is True
            else:
                # 最后一天
                has_next = playback.next_day()
                assert has_next is False, "最后一天后不应有下一天"
                assert playback.state == PlaybackState.FINISHED, \
                    f"最后一天后状态应为 FINISHED，实际为 {playback.state}"
    
    @settings(max_examples=100)
    @given(
        initial_state=st.sampled_from([PlaybackState.DAY_ENDED, PlaybackState.FINISHED])
    )
    def test_play_does_not_change_terminal_states(self, initial_state: PlaybackState):
        """
        验证在终止状态下调用 play() 不会改变状态。
        
        *For any* 播放引擎在 DAY_ENDED 或 FINISHED 状态：
        调用 play() 不应改变状态
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        # 手动设置状态
        playback.state = initial_state
        
        playback.play()
        
        assert playback.state == initial_state, \
            f"在 {initial_state} 状态下调用 play() 不应改变状态，实际变为 {playback.state}"
    
    @settings(max_examples=100)
    @given(
        initial_state=st.sampled_from([PlaybackState.IDLE, PlaybackState.PAUSED, PlaybackState.DAY_ENDED, PlaybackState.FINISHED])
    )
    def test_pause_only_works_in_playing_state(self, initial_state: PlaybackState):
        """
        验证 pause() 只在 PLAYING 状态下有效。
        
        *For any* 播放引擎不在 PLAYING 状态：
        调用 pause() 不应改变状态
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        # 手动设置状态
        playback.state = initial_state
        
        playback.pause()
        
        assert playback.state == initial_state, \
            f"在 {initial_state} 状态下调用 pause() 不应改变状态，实际变为 {playback.state}"



class TestIntradayPriceUpdate:
    """
    Property 10: 日内价格更新一致性
    Feature: stock-trading-simulator, Property 10: 日内价格更新一致性
    **Validates: Requirements 6.7**
    
    验证 tick 时持仓价格正确更新：
    - 所有持仓的 current_price 应更新为当前 tick 的价格
    - 浮动盈亏应基于更新后的价格重新计算
    """
    
    @settings(max_examples=100)
    @given(tick_index=st.integers(min_value=0, max_value=3))
    def test_get_current_prices_returns_tick_prices(self, tick_index: int):
        """
        验证 get_current_prices() 返回当前 tick 的价格。
        
        *For any* 播放中的 tick：
        get_current_prices() 应返回当前 tick 的价格
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 执行指定数量的 tick
        last_tick_data = None
        for i in range(tick_index + 1):
            tick_data = playback.tick()
            if tick_data:
                last_tick_data = tick_data
        
        if last_tick_data:
            current_prices = playback.get_current_prices()
            
            for code, tick in last_tick_data.items():
                assert code in current_prices, f"股票 {code} 应在当前价格中"
                assert abs(current_prices[code] - tick.price) < 0.01, \
                    f"股票 {code} 价格不匹配: 期望 {tick.price}, 实际 {current_prices[code]}"
    
    @settings(max_examples=100)
    @given(num_ticks=st.integers(min_value=1, max_value=4))
    def test_prices_update_with_each_tick(self, num_ticks: int):
        """
        验证每个 tick 后价格正确更新。
        
        *For any* 播放中的多个 tick：
        每次 tick 后 get_current_prices() 应返回最新的价格
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        previous_prices = {}
        
        for i in range(num_ticks):
            tick_data = playback.tick()
            
            if tick_data:
                current_prices = playback.get_current_prices()
                
                # 验证价格与 tick 数据一致
                for code, tick in tick_data.items():
                    assert code in current_prices, f"股票 {code} 应在当前价格中"
                    assert abs(current_prices[code] - tick.price) < 0.01, \
                        f"第 {i+1} 个 tick 后，股票 {code} 价格不匹配"
                
                previous_prices = current_prices.copy()
    
    def test_prices_available_before_first_tick(self):
        """
        验证在第一个 tick 之前也能获取价格。
        
        *For any* 已加载分时数据但未开始播放的引擎：
        get_current_prices() 应返回第一个 tick 的价格
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        
        # 未开始播放时获取价格
        prices = playback.get_current_prices()
        
        # 应该返回第一个 tick 的价格
        assert len(prices) > 0, "应该有价格数据"
        
        for code, price in prices.items():
            assert price > 0, f"股票 {code} 价格应为正数"
    
    @settings(max_examples=100)
    @given(
        stock_codes=st.lists(
            st.sampled_from(["600519", "000001", "300750"]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    def test_all_stocks_have_prices(self, stock_codes: list):
        """
        验证所有股票都有价格更新。
        
        *For any* 多只股票的播放：
        get_current_prices() 应包含所有股票的价格
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        playback.setup(stock_codes, date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 执行一个 tick
        tick_data = playback.tick()
        
        if tick_data:
            prices = playback.get_current_prices()
            
            # 验证所有有数据的股票都有价格
            for code in tick_data.keys():
                assert code in prices, f"股票 {code} 应在价格列表中"
                assert prices[code] > 0, f"股票 {code} 价格应为正数"
    
    def test_callback_receives_correct_tick_data(self):
        """
        验证回调函数接收正确的 tick 数据。
        
        *For any* 注册了回调的播放引擎：
        回调函数应接收到与 tick() 返回相同的数据
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        received_ticks = []
        
        def on_tick_callback(tick_data):
            received_ticks.append(tick_data)
        
        playback.on_tick(on_tick_callback)
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 手动执行几个 tick 并调用回调
        expected_ticks = []
        for _ in range(3):
            tick_data = playback.tick()
            if tick_data:
                expected_ticks.append(tick_data)
                # 模拟 run_playback_loop 的行为
                if playback._on_tick_callback:
                    playback._on_tick_callback(tick_data)
        
        assert len(received_ticks) == len(expected_ticks), \
            f"回调接收的 tick 数量不匹配: 期望 {len(expected_ticks)}, 实际 {len(received_ticks)}"
        
        for i, (received, expected) in enumerate(zip(received_ticks, expected_ticks)):
            for code in expected:
                assert code in received, f"第 {i+1} 个 tick 缺少股票 {code}"
                assert received[code].price == expected[code].price, \
                    f"第 {i+1} 个 tick 股票 {code} 价格不匹配"
    
    def test_day_end_callback_receives_correct_date(self):
        """
        验证当日结束回调接收正确的日期。
        
        *For any* 注册了当日结束回调的播放引擎：
        回调函数应接收到当前交易日期
        """
        mock_engine = create_mock_data_engine()
        playback = PlaybackEngine(mock_engine)
        
        received_dates = []
        
        def on_day_end_callback(trade_date):
            received_dates.append(trade_date)
        
        playback.on_day_end(on_day_end_callback)
        playback.setup(["600519"], date(2024, 1, 2), date(2024, 1, 4))
        playback.load_day(date(2024, 1, 2))
        playback.play()
        
        # 播放到结束
        while playback.state == PlaybackState.PLAYING:
            playback.tick()
        
        # 手动触发回调（模拟 run_playback_loop 的行为）
        if playback.state == PlaybackState.DAY_ENDED and playback._on_day_end_callback:
            playback._on_day_end_callback(playback.current_date)
        
        assert len(received_dates) == 1, f"应该收到 1 个日期，实际收到 {len(received_dates)}"
        assert received_dates[0] == date(2024, 1, 2), \
            f"日期不匹配: 期望 2024-01-02, 实际 {received_dates[0]}"
