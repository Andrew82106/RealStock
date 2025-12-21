"""行情播放模块数据模型 - Data models for the playback engine module."""

from dataclasses import dataclass
from datetime import time
from enum import Enum


class PlaybackState(Enum):
    """播放状态 - Playback state enumeration."""
    
    IDLE = "idle"               # 空闲，等待开始
    PLAYING = "playing"         # 播放中
    PAUSED = "paused"           # 已暂停
    DAY_ENDED = "day_ended"     # 当日结束
    FINISHED = "finished"       # 全部结束


@dataclass
class IntradayTick:
    """分时数据点 - Intraday tick data point."""
    
    time: time              # 时间 HH:MM
    price: float            # 当前价格
    volume: int             # 累计成交量
    turnover_rate: float    # 换手率
    change_pct: float       # 涨跌幅
    
    @classmethod
    def from_time_str(
        cls,
        time_str: str,
        price: float,
        volume: int,
        turnover_rate: float,
        change_pct: float
    ) -> "IntradayTick":
        """从时间字符串创建 IntradayTick 实例。
        
        Args:
            time_str: 时间字符串，格式为 "HH:MM"
            price: 当前价格
            volume: 累计成交量
            turnover_rate: 换手率
            change_pct: 涨跌幅
            
        Returns:
            IntradayTick 实例
        """
        hour, minute = map(int, time_str.split(":"))
        return cls(
            time=time(hour, minute),
            price=price,
            volume=volume,
            turnover_rate=turnover_rate,
            change_pct=change_pct
        )


@dataclass
class PlaybackConfig:
    """播放配置 - Playback configuration."""
    
    speed: float = 1.0          # 播放速度倍数（1.0 = 实时，10.0 = 10倍速）
    tick_interval: float = 1.0  # 每个 tick 的实际间隔（秒），会被 speed 调整
