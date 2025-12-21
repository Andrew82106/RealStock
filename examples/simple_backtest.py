#!/usr/bin/env python3
"""
简单回测示例 - Simple Backtest Example

本示例展示如何使用 A 股模拟交易回测系统进行简单的策略回测。
策略：简单均线策略 - 当收盘价高于5日均线时买入，低于5日均线时卖出。

使用方法:
    python examples/simple_backtest.py

注意:
    - 首次运行需要从 AkShare 下载数据，可能需要一些时间
    - 数据会缓存到本地，后续运行会更快
"""

from datetime import date, timedelta
from typing import Optional

from src.account.account import Account
from src.data_engine.engine import DataEngine
from src.simulator.simulator import Simulator, PerformanceMetrics
from src.trading.models import DailyBar


def calculate_ma(prices: list[float], period: int) -> Optional[float]:
    """
    计算移动平均线。
    
    Args:
        prices: 价格列表（从旧到新）
        period: 均线周期
        
    Returns:
        均线值，如果数据不足则返回 None
    """
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


class SimpleMAStrategy:
    """
    简单均线策略。
    
    策略逻辑:
    - 当收盘价 > 5日均线时，买入
    - 当收盘价 < 5日均线时，卖出
    - 每次交易使用 30% 的可用资金
    """
    
    def __init__(self, ma_period: int = 5, position_ratio: float = 0.3):
        """
        初始化策略。
        
        Args:
            ma_period: 均线周期，默认5日
            position_ratio: 每次交易使用的资金比例，默认30%
        """
        self.ma_period = ma_period
        self.position_ratio = position_ratio
        self.price_history: dict[str, list[float]] = {}
    
    def __call__(
        self,
        current_date: date,
        bars: dict[str, DailyBar],
        account: Account
    ) -> list[tuple]:
        """
        策略执行函数。
        
        Args:
            current_date: 当前日期
            bars: 当日行情数据
            account: 账户状态
            
        Returns:
            交易指令列表 [(order_type, code, price, quantity), ...]
        """
        instructions = []
        
        for code, bar in bars.items():
            # 更新价格历史
            if code not in self.price_history:
                self.price_history[code] = []
            self.price_history[code].append(bar.close)
            
            # 只保留最近的数据
            if len(self.price_history[code]) > self.ma_period * 2:
                self.price_history[code] = self.price_history[code][-self.ma_period * 2:]
            
            # 计算均线
            ma = calculate_ma(self.price_history[code], self.ma_period)
            if ma is None:
                continue
            
            # 判断信号
            if bar.close > ma:
                # 买入信号
                if code not in account.positions:
                    # 计算买入数量（使用可用资金的一定比例）
                    available_cash = account.cash * self.position_ratio
                    quantity = int(available_cash / bar.close / 100) * 100  # 取整到100股
                    
                    if quantity >= 100:
                        instructions.append(("buy", code, bar.close, quantity))
            
            elif bar.close < ma:
                # 卖出信号
                if code in account.positions:
                    position = account.positions[code]
                    instructions.append(("sell", code, bar.close, position.quantity))
        
        return instructions


def run_backtest():
    """运行回测示例。"""
    print("=" * 60)
    print("A 股模拟交易回测系统 - 简单均线策略回测示例")
    print("=" * 60)
    
    # 配置参数
    stock_codes = ["000001"]  # 平安银行
    start_date = date(2024, 1, 1)
    end_date = date(2024, 6, 30)
    initial_cash = 100000.0
    
    print(f"\n回测参数:")
    print(f"  股票代码: {stock_codes}")
    print(f"  回测区间: {start_date} 至 {end_date}")
    print(f"  初始资金: {initial_cash:,.2f} 元")
    
    # 初始化组件
    print("\n正在初始化数据引擎...")
    data_engine = DataEngine(cache_dir="./data_cache")
    
    print("正在初始化模拟器...")
    simulator = Simulator(data_engine, initial_cash=initial_cash)
    
    print("正在加载历史数据...")
    try:
        simulator.setup(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        print(f"\n错误: 无法加载数据 - {e}")
        print("提示: 请确保已安装 akshare 并且网络连接正常")
        return
    
    print(f"已加载 {len(simulator.trading_dates)} 个交易日的数据")
    
    # 创建策略
    strategy = SimpleMAStrategy(ma_period=5, position_ratio=0.3)
    
    # 运行回测
    print("\n正在运行回测...")
    metrics = simulator.run_backtest(strategy)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    print(f"\n绩效指标:")
    print(f"  总收益率: {metrics.total_return * 100:.2f}%")
    print(f"  最大回撤: {metrics.max_drawdown * 100:.2f}%")
    print(f"  胜率: {metrics.win_rate * 100:.2f}%")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    
    print(f"\n交易统计:")
    print(f"  总交易次数: {metrics.total_trades}")
    print(f"  盈利交易: {metrics.winning_trades}")
    print(f"  亏损交易: {metrics.losing_trades}")
    
    print(f"\n账户状态:")
    print(f"  期末总资产: {simulator.account.total_assets:,.2f} 元")
    print(f"  可用现金: {simulator.account.cash:,.2f} 元")
    print(f"  持仓市值: {simulator.account.total_market_value:,.2f} 元")
    
    if simulator.account.positions:
        print(f"\n当前持仓:")
        for code, pos in simulator.account.positions.items():
            print(f"  {code}: {pos.quantity} 股, "
                  f"成本价 {pos.cost_price:.2f}, "
                  f"现价 {pos.current_price:.2f}, "
                  f"盈亏 {pos.profit_loss:.2f} ({pos.profit_loss_pct * 100:.2f}%)")
    
    # 导出交易日志
    log_file = "./trade_log.csv"
    simulator.trading_engine.export_trade_log_to_csv(log_file)
    print(f"\n交易日志已导出到: {log_file}")
    
    print("\n" + "=" * 60)
    print("回测完成!")
    print("=" * 60)


if __name__ == "__main__":
    run_backtest()
