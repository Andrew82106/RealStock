"""行情播放引擎 - Playback engine for intraday market replay."""

from datetime import date, time
from typing import Callable, Optional

import pandas as pd

from src.playback.models import IntradayTick, PlaybackConfig, PlaybackState


class PlaybackEngine:
    """日内行情播放引擎 - Intraday market playback engine."""
    
    def __init__(self, data_engine: "DataEngine"):
        """
        初始化播放引擎。
        
        Args:
            data_engine: 数据引擎实例，用于获取行情数据
        """
        self.data_engine = data_engine
        self.state: PlaybackState = PlaybackState.IDLE
        self.config: PlaybackConfig = PlaybackConfig()
        self.current_date: Optional[date] = None
        self.current_tick_index: int = 0
        self.intraday_data: dict[str, list[IntradayTick]] = {}  # code -> ticks
        self.stock_codes: list[str] = []
        self.trading_dates: list[date] = []
        self.date_index: int = 0
        self._on_tick_callback: Optional[Callable[[dict[str, IntradayTick]], None]] = None
        self._on_day_end_callback: Optional[Callable[[date], None]] = None
        self._daily_data: dict[str, pd.DataFrame] = {}  # 缓存日线数据
    
    def setup(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date
    ) -> None:
        """
        初始化播放引擎。
        
        - 设置股票列表和日期范围
        - 生成交易日历
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        """
        self.stock_codes = stock_codes
        self.state = PlaybackState.IDLE
        self.current_tick_index = 0
        self.date_index = 0
        self.intraday_data = {}
        
        # 获取交易日历（使用第一只股票的日线数据来确定交易日）
        if stock_codes:
            df = self.data_engine.get_daily_data(
                stock_codes[0], start_date, end_date
            )
            self._daily_data[stock_codes[0]] = df
            
            if not df.empty:
                self.trading_dates = sorted(df["date"].tolist())
            else:
                self.trading_dates = []
            
            # 预加载其他股票的日线数据
            for code in stock_codes[1:]:
                self._daily_data[code] = self.data_engine.get_daily_data(
                    code, start_date, end_date
                )
        else:
            self.trading_dates = []
        
        if self.trading_dates:
            self.current_date = self.trading_dates[0]
    
    def set_speed(self, speed: float) -> None:
        """
        设置播放速度（1.0-100.0）。
        
        Args:
            speed: 播放速度倍数
        """
        self.config.speed = max(1.0, min(100.0, speed))
    
    def load_day(self, trade_date: date) -> None:
        """
        加载指定日期的分时数据。
        
        - 为每只股票加载或生成分时数据
        - 重置 tick 索引
        
        Args:
            trade_date: 交易日期
        """
        self.current_date = trade_date
        self.current_tick_index = 0
        self.intraday_data = {}
        
        for code in self.stock_codes:
            # 获取分时数据
            df = self.data_engine.get_intraday_data(code, trade_date)
            
            if df.empty:
                continue
            
            # 获取前一日收盘价用于计算涨跌幅
            prev_close = self._get_prev_close(code, trade_date)
            
            # 转换为 IntradayTick 列表
            ticks = []
            for _, row in df.iterrows():
                price = float(row["price"])
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                
                tick = IntradayTick.from_time_str(
                    time_str=str(row["time"]),
                    price=price,
                    volume=int(row["volume"]),
                    turnover_rate=float(row.get("turnover_rate", 0.0)),
                    change_pct=round(change_pct, 2)
                )
                ticks.append(tick)
            
            self.intraday_data[code] = ticks
        
        # 设置状态为 IDLE，等待播放
        self.state = PlaybackState.IDLE
    
    def _get_prev_close(self, code: str, trade_date: date) -> float:
        """获取前一交易日收盘价。"""
        if code not in self._daily_data:
            return 0.0
        
        df = self._daily_data[code]
        if df.empty:
            return 0.0
        
        # 找到当前日期在交易日列表中的位置
        dates = df["date"].tolist()
        if trade_date not in dates:
            return 0.0
        
        idx = dates.index(trade_date)
        if idx == 0:
            # 第一天，使用当天开盘价作为参考
            return float(df.iloc[0]["open"])
        
        return float(df.iloc[idx - 1]["close"])
    
    def play(self) -> None:
        """开始/继续播放。"""
        if self.state in (PlaybackState.IDLE, PlaybackState.PAUSED):
            self.state = PlaybackState.PLAYING
    
    def pause(self) -> None:
        """暂停播放。"""
        if self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.PAUSED
    
    def tick(self) -> Optional[dict[str, IntradayTick]]:
        """
        推进一个 tick。
        
        - 返回当前所有股票的分时数据
        - 如果到达收盘，切换到 DAY_ENDED 状态
        
        Returns:
            当前所有股票的分时数据字典，或 None（如果无数据）
        """
        if self.state != PlaybackState.PLAYING:
            return None
        
        if not self.intraday_data:
            self.state = PlaybackState.DAY_ENDED
            return None
        
        # 获取最大 tick 数量
        max_ticks = max(len(ticks) for ticks in self.intraday_data.values()) if self.intraday_data else 0
        
        if self.current_tick_index >= max_ticks:
            # 到达收盘
            self.state = PlaybackState.DAY_ENDED
            return None
        
        # 获取当前 tick 的数据
        result = {}
        for code, ticks in self.intraday_data.items():
            if self.current_tick_index < len(ticks):
                result[code] = ticks[self.current_tick_index]
        
        self.current_tick_index += 1
        
        return result
    
    def get_current_prices(self) -> dict[str, float]:
        """
        获取当前所有股票的价格。
        
        Returns:
            股票代码到当前价格的映射
        """
        prices = {}
        
        for code, ticks in self.intraday_data.items():
            if ticks and self.current_tick_index > 0:
                # 使用上一个 tick 的价格（因为 current_tick_index 指向下一个要播放的）
                idx = min(self.current_tick_index - 1, len(ticks) - 1)
                prices[code] = ticks[idx].price
            elif ticks:
                # 还没开始播放，使用第一个价格
                prices[code] = ticks[0].price
        
        return prices
    
    def get_current_price(self, code: str) -> Optional[float]:
        """
        获取指定股票的当前价格。
        
        Args:
            code: 股票代码
            
        Returns:
            当前价格，如果没有数据则返回 None
        """
        if code not in self.intraday_data:
            return None
        
        ticks = self.intraday_data[code]
        if not ticks:
            return None
        
        if self.current_tick_index > 0:
            idx = min(self.current_tick_index - 1, len(ticks) - 1)
            return ticks[idx].price
        else:
            return ticks[0].price
    
    def next_day(self) -> bool:
        """
        切换到下一个交易日。
        
        Returns:
            True 表示成功切换，False 表示已到达最后一天
        """
        self.date_index += 1
        
        if self.date_index >= len(self.trading_dates):
            self.state = PlaybackState.FINISHED
            return False
        
        self.current_date = self.trading_dates[self.date_index]
        self.load_day(self.current_date)
        return True
    
    def on_tick(self, callback: Callable[[dict[str, IntradayTick]], None]) -> None:
        """
        注册 tick 回调函数。
        
        Args:
            callback: 每个 tick 时调用的回调函数，参数为当前所有股票的分时数据
        """
        self._on_tick_callback = callback
    
    def on_day_end(self, callback: Callable[[date], None]) -> None:
        """
        注册当日结束回调函数。
        
        Args:
            callback: 当日结束时调用的回调函数，参数为当前日期
        """
        self._on_day_end_callback = callback
    
    def run_playback_loop(self) -> None:
        """
        运行播放循环（阻塞式）。
        
        - 根据速度设置控制 tick 间隔
        - 调用回调函数更新 UI
        """
        import time as time_module
        
        while self.state == PlaybackState.PLAYING:
            tick_data = self.tick()
            
            if tick_data and self._on_tick_callback:
                self._on_tick_callback(tick_data)
            
            if self.state == PlaybackState.DAY_ENDED:
                if self._on_day_end_callback and self.current_date:
                    self._on_day_end_callback(self.current_date)
                break
            
            # 根据速度调整等待时间
            time_module.sleep(self.config.tick_interval / self.config.speed)
