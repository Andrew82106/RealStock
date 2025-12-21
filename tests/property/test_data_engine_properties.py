"""属性测试 - 数据引擎模块 Property-based tests for data engine module."""

import tempfile
from datetime import date

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

from src.data_engine import DataEngine


# 测试数据生成策略
REQUIRED_DAILY_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


@st.composite
def valid_daily_dataframe(draw):
    """生成有效的日线数据 DataFrame"""
    n_rows = draw(st.integers(min_value=1, max_value=10))
    
    rows = []
    base_date = date(2024, 1, 1)
    
    for i in range(n_rows):
        low = draw(st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False))
        low = round(low, 2)
        high = draw(st.floats(min_value=low, max_value=low * 1.2, allow_nan=False, allow_infinity=False))
        high = round(high, 2)
        open_price = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
        open_price = round(open_price, 2)
        close = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
        close = round(close, 2)
        volume = draw(st.integers(min_value=1000, max_value=100000000))
        
        row_date = date(base_date.year, base_date.month, base_date.day + i)
        rows.append({
            "date": row_date,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
    
    return pd.DataFrame(rows)


class TestDailyDataFieldCompleteness:
    """
    Property 1.2: 日线数据字段完整性
    Feature: stock-trading-simulator, Property 1.2: 日线数据字段完整性
    **Validates: Requirements 1.2**
    """
    
    @settings(max_examples=100)
    @given(df=valid_daily_dataframe())
    def test_daily_data_contains_required_fields(self, df: pd.DataFrame):
        """
        验证日线数据 DataFrame 包含所有必需字段。
        
        *For any* 有效的日线数据 DataFrame，它应该包含以下字段：
        date, open, high, low, close, volume
        """
        # 验证所有必需列都存在
        for col in REQUIRED_DAILY_COLUMNS:
            assert col in df.columns, f"缺少必需字段: {col}"
    
    @settings(max_examples=100)
    @given(df=valid_daily_dataframe())
    def test_daily_data_price_relationships(self, df: pd.DataFrame):
        """
        验证日线数据中价格关系的正确性。
        
        *For any* 有效的日线数据，应满足：
        - low <= open <= high
        - low <= close <= high
        - low <= high
        """
        for _, row in df.iterrows():
            assert row["low"] <= row["high"], "最低价应小于等于最高价"
            assert row["low"] <= row["open"] <= row["high"], "开盘价应在最低价和最高价之间"
            assert row["low"] <= row["close"] <= row["high"], "收盘价应在最低价和最高价之间"
    
    @settings(max_examples=100)
    @given(df=valid_daily_dataframe())
    def test_daily_data_volume_positive(self, df: pd.DataFrame):
        """
        验证日线数据中成交量为正数。
        
        *For any* 有效的日线数据，成交量应为正整数。
        """
        for _, row in df.iterrows():
            assert row["volume"] > 0, "成交量应为正数"


class TestDataEngineCacheRoundTrip:
    """
    测试数据引擎缓存的 Round-Trip 属性
    """
    
    @settings(max_examples=50)
    @given(df=valid_daily_dataframe())
    def test_cache_save_load_roundtrip(self, df: pd.DataFrame):
        """
        验证缓存保存和加载的 Round-Trip 属性。
        
        *For any* 有效的日线数据，保存到缓存后再加载应得到等价的数据。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            test_code = "600519"
            
            # 保存到缓存
            engine._save_to_cache(test_code, df)
            
            # 从缓存加载
            if not df.empty:
                start_date = df["date"].min()
                end_date = df["date"].max()
                loaded_df = engine._load_from_cache(test_code, start_date, end_date)
                
                assert loaded_df is not None, "缓存加载失败"
                assert len(loaded_df) == len(df), "加载的数据行数不匹配"
                
                # 验证所有列都存在
                for col in REQUIRED_DAILY_COLUMNS:
                    assert col in loaded_df.columns, f"加载的数据缺少字段: {col}"



# 导入 DailyBar 用于分时数据测试
from src.data_engine.models import DailyBar


@st.composite
def valid_daily_bar(draw):
    """生成有效的 DailyBar 对象"""
    low = draw(st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    low = round(low, 2)
    high = draw(st.floats(min_value=low * 1.001, max_value=low * 1.2, allow_nan=False, allow_infinity=False))
    high = round(high, 2)
    open_price = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
    open_price = round(open_price, 2)
    close = draw(st.floats(min_value=low, max_value=high, allow_nan=False, allow_infinity=False))
    close = round(close, 2)
    volume = draw(st.integers(min_value=10000, max_value=100000000))
    bar_date = draw(st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)))
    
    return DailyBar(
        date=bar_date,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume
    )


class TestSimulatedIntradayDataConsistency:
    """
    Property 18: 模拟分时数据一致性
    Feature: stock-trading-simulator, Property 18: 模拟分时数据一致性
    **Validates: Requirements 10.4**
    
    验证分时数据与日线数据的价格范围一致：
    - 分时数据的第一个价格应接近开盘价
    - 分时数据的最后一个价格应等于收盘价
    - 分时数据的最高价不应超过日线最高价
    - 分时数据的最低价不应低于日线最低价
    """
    
    @settings(max_examples=100)
    @given(daily_bar=valid_daily_bar())
    def test_simulated_intraday_price_range(self, daily_bar: DailyBar):
        """
        验证模拟分时数据的价格范围与日线数据一致。
        
        *For any* 日线数据 daily_bar 和生成的分时数据：
        - 分时数据的最高价不应超过日线最高价
        - 分时数据的最低价不应低于日线最低价
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            
            # 生成模拟分时数据
            intraday_df = engine.generate_simulated_intraday(daily_bar)
            
            # 验证数据不为空
            assert not intraday_df.empty, "分时数据不应为空"
            
            # 验证价格范围
            intraday_max = intraday_df["price"].max()
            intraday_min = intraday_df["price"].min()
            
            assert intraday_max <= daily_bar.high, \
                f"分时最高价 {intraday_max} 超过日线最高价 {daily_bar.high}"
            assert intraday_min >= daily_bar.low, \
                f"分时最低价 {intraday_min} 低于日线最低价 {daily_bar.low}"
    
    @settings(max_examples=100)
    @given(daily_bar=valid_daily_bar())
    def test_simulated_intraday_close_price(self, daily_bar: DailyBar):
        """
        验证模拟分时数据的收盘价等于日线收盘价。
        
        *For any* 日线数据，分时数据的最后一个价格应等于收盘价。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            
            # 生成模拟分时数据
            intraday_df = engine.generate_simulated_intraday(daily_bar)
            
            # 验证收盘价
            last_price = intraday_df["price"].iloc[-1]
            assert last_price == daily_bar.close, \
                f"分时收盘价 {last_price} 不等于日线收盘价 {daily_bar.close}"
    
    @settings(max_examples=100)
    @given(daily_bar=valid_daily_bar())
    def test_simulated_intraday_open_price(self, daily_bar: DailyBar):
        """
        验证模拟分时数据的开盘价接近日线开盘价。
        
        *For any* 日线数据，分时数据的第一个价格应等于开盘价。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            
            # 生成模拟分时数据
            intraday_df = engine.generate_simulated_intraday(daily_bar)
            
            # 验证开盘价
            first_price = intraday_df["price"].iloc[0]
            assert first_price == daily_bar.open, \
                f"分时开盘价 {first_price} 不等于日线开盘价 {daily_bar.open}"
    
    @settings(max_examples=100)
    @given(daily_bar=valid_daily_bar())
    def test_simulated_intraday_data_points(self, daily_bar: DailyBar):
        """
        验证模拟分时数据生成 240 个数据点。
        
        *For any* 日线数据，应生成 240 个分时数据点（9:30-11:30, 13:00-15:00）。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            
            # 生成模拟分时数据
            intraday_df = engine.generate_simulated_intraday(daily_bar)
            
            # 验证数据点数量
            assert len(intraday_df) == 240, \
                f"分时数据点数量 {len(intraday_df)} 不等于 240"
    
    @settings(max_examples=100)
    @given(daily_bar=valid_daily_bar())
    def test_simulated_intraday_required_columns(self, daily_bar: DailyBar):
        """
        验证模拟分时数据包含所有必需字段。
        
        *For any* 日线数据，生成的分时数据应包含 time, price, volume, turnover_rate 字段。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = DataEngine(cache_dir=tmpdir)
            
            # 生成模拟分时数据
            intraday_df = engine.generate_simulated_intraday(daily_bar)
            
            # 验证必需字段
            required_columns = ["time", "price", "volume", "turnover_rate"]
            for col in required_columns:
                assert col in intraday_df.columns, f"缺少必需字段: {col}"
