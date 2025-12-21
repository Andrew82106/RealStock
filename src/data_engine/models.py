"""数据引擎数据模型 - Data models for the data engine module."""

from dataclasses import dataclass
from datetime import date


@dataclass
class StockInfo:
    """股票基本信息 - Basic stock information."""
    
    code: str       # 股票代码，如 "600519"
    name: str       # 股票名称，如 "贵州茅台"
    market: str     # 市场，"sh" 或 "sz"
    
    def __post_init__(self):
        """验证并规范化股票代码格式"""
        # 确保 code 是纯数字格式
        self.code = self.code.strip()
        # 确保 market 是小写
        self.market = self.market.lower()
    
    @property
    def full_code(self) -> str:
        """返回带市场前缀的完整代码，如 'sh600519'"""
        return f"{self.market}{self.code}"


@dataclass
class DailyBar:
    """日线数据 - Daily OHLCV bar data."""
    
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
