"""自定义异常类 - Custom exception classes for the stock trading simulator."""


class TradingSimulatorError(Exception):
    """基础异常类 - Base exception class for all trading simulator errors."""
    pass


class DataFetchError(TradingSimulatorError):
    """数据获取错误 - Raised when data fetching from AkShare API fails."""
    pass


class InvalidStockCodeError(TradingSimulatorError):
    """无效股票代码 - Raised when an invalid stock code is provided."""
    pass


class InvalidDateRangeError(TradingSimulatorError):
    """无效日期范围 - Raised when an invalid date range is specified."""
    pass


class InvalidOrderError(TradingSimulatorError):
    """无效订单 - Raised when an invalid order is submitted."""
    pass
