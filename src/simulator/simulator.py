"""模拟器 - Simulator for backtesting and interactive trading."""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

import pandas as pd

from src.account.account import Account
from src.data_engine.engine import DataEngine
from src.exceptions import InvalidOrderError
from src.playback.engine import PlaybackEngine
from src.playback.models import PlaybackState
from src.trading.engine import TradingEngine
from src.trading.models import DailyBar, Order, OrderStatus, OrderType


@dataclass
class PerformanceMetrics:
    """绩效指标 - Performance metrics for backtesting."""
    
    total_return: float         # 总收益率
    max_drawdown: float         # 最大回撤
    win_rate: float             # 胜率
    sharpe_ratio: float         # 夏普比率
    total_trades: int           # 总交易次数
    winning_trades: int         # 盈利交易次数
    losing_trades: int          # 亏损交易次数


# 策略函数类型定义
# 输入: 当前日期, 当日行情字典, 账户状态
# 输出: 交易指令列表 [(order_type, code, price, quantity), ...]
StrategyFunc = Callable[[date, dict[str, DailyBar], Account], list[tuple]]


class Simulator:
    """模拟器 - Main simulator class for backtesting and interactive trading."""
    
    def __init__(
        self,
        data_engine: DataEngine,
        initial_cash: float = 100000.0,
        daily_mode: bool = False,
    ):
        """
        初始化模拟器。
        
        Args:
            data_engine: 数据引擎实例
            initial_cash: 初始资金，默认 100,000 RMB
        """
        self.data_engine = data_engine
        self.daily_mode = daily_mode
        self.account = Account(initial_cash=initial_cash)
        self.trading_engine = TradingEngine(self.account)
        self.playback_engine = PlaybackEngine(data_engine)
        self.current_date: Optional[date] = None
        self.trading_dates: list[date] = []
        self.date_index: int = 0
        self.stock_codes: list[str] = []
        self.daily_data: dict[str, pd.DataFrame] = {}
        self.net_value_history: list[tuple[date, float]] = []
        self._initial_cash = initial_cash
    
    def setup(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        history_start_date: Optional[date] = None,
    ) -> None:
        """
        初始化模拟器。
        
        - 加载指定股票的历史数据
        - 生成交易日历
        - 初始化播放引擎
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        """
        self.stock_codes = stock_codes
        self.daily_data = {}
        self.trading_dates = []
        self.date_index = 0
        self.net_value_history = []
        
        data_start_date = history_start_date or start_date

        # 加载每只股票的日线数据。日线游戏可额外加载开始日前的观察窗口，
        # 但正式交易日历仍从 start_date 开始。
        for code in stock_codes:
            if self.daily_mode:
                df = self.data_engine.get_cached_daily_data(code, data_start_date, end_date)
            else:
                df = self.data_engine.get_daily_data(code, start_date, end_date)
            self.daily_data[code] = df
        
        # 生成交易日历（使用第一只股票的交易日）
        if stock_codes and not self.daily_data[stock_codes[0]].empty:
            self.trading_dates = sorted(
                trading_date
                for trading_date in self.daily_data[stock_codes[0]]["date"].tolist()
                if trading_date >= start_date
            )
        
        # 设置当前日期
        if self.trading_dates:
            self.current_date = self.trading_dates[0]
        
        # 初始化播放引擎
        if self.daily_mode:
            # 日线模式只保留状态字段兼容旧接口，不加载或生成任何分时数据。
            self.playback_engine.stock_codes = stock_codes
            self.playback_engine.trading_dates = self.trading_dates.copy()
            self.playback_engine.current_date = self.current_date
            self.playback_engine.date_index = 0
            self.playback_engine.current_tick_index = 0
            self.playback_engine.intraday_data = {}
            self.playback_engine.state = PlaybackState.PAUSED
        else:
            self.playback_engine.setup(stock_codes, start_date, end_date)
        
        # 记录初始净值
        if self.current_date:
            self.net_value_history.append((self.current_date, self.account.total_assets))
    
    def get_current_bars(self) -> dict[str, DailyBar]:
        """
        获取当前日期所有股票的行情。
        
        Returns:
            股票代码到 DailyBar 的映射
        """
        if self.current_date is None:
            return {}
        
        bars = {}
        for code in self.stock_codes:
            bar = self._get_current_daily_bar(code)
            if bar:
                bars[code] = bar
        
        return bars
    
    def _get_current_daily_bar(self, code: str) -> Optional[DailyBar]:
        """
        获取指定股票当日的日线数据。
        
        Args:
            code: 股票代码
            
        Returns:
            DailyBar 或 None
        """
        if code not in self.daily_data or self.current_date is None:
            return None
        
        df = self.daily_data[code]
        if df.empty:
            return None
        
        # 查找当前日期的数据
        mask = df["date"] == self.current_date
        if not mask.any():
            return None
        
        row = df[mask].iloc[0]
        return DailyBar(
            date=row["date"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"])
        )

    
    def start_day(self) -> None:
        """
        开始当日交易。
        
        - 加载当日分时数据
        - 准备播放
        """
        if self.current_date is None:
            raise InvalidOrderError("模拟器未初始化，请先调用 setup()")
        
        if self.daily_mode:
            self.playback_engine.current_date = self.current_date
            self.playback_engine.current_tick_index = 0
            self.playback_engine.state = PlaybackState.PAUSED
            self._update_position_prices()
            return
        self.playback_engine.load_day(self.current_date)
    
    def play(self, speed: float = 1.0) -> None:
        """
        开始播放行情。
        
        Args:
            speed: 播放速度倍数，默认 1.0
        """
        self.playback_engine.set_speed(speed)
        self.playback_engine.play()
    
    def pause(self) -> None:
        """暂停播放。"""
        self.playback_engine.pause()
    
    def _ensure_tradable_state(self) -> None:
        """
        校验当前播放状态是否允许交易。

        允许：IDLE（未开始）、PAUSED（暂停）、DAY_ENDED（收盘后挂单）
        禁止：PLAYING（播放中）、FINISHED（行情播放完毕）
        """
        state = self.playback_engine.state
        if state == PlaybackState.PLAYING:
            raise InvalidOrderError("播放中无法交易，请先暂停")
        if state == PlaybackState.FINISHED:
            raise InvalidOrderError("行情已播放完毕，无法交易")

    def buy(self, code: str, price: float, quantity: int) -> Order:
        """
        买入股票（挂单模式，IDLE/暂停/收盘后可下单）。

        Args:
            code: 股票代码
            price: 委托价格
            quantity: 委托数量

        Returns:
            Order: 订单对象
        """
        if self.current_date is None:
            raise InvalidOrderError("模拟器未初始化")

        self._ensure_tradable_state()

        # 获取当前价格
        if self.daily_mode:
            bar = self._get_current_daily_bar(code)
            current_price = bar.close if bar else None
        else:
            current_price = self.playback_engine.get_current_price(code)

        return self.trading_engine.submit_buy_order(
            code, price, quantity, self.current_date, current_price
        )

    def sell(self, code: str, price: float, quantity: int) -> Order:
        """
        卖出股票（挂单模式，IDLE/暂停/收盘后可下单）。

        Args:
            code: 股票代码
            price: 委托价格
            quantity: 委托数量

        Returns:
            Order: 订单对象
        """
        if self.current_date is None:
            raise InvalidOrderError("模拟器未初始化")

        self._ensure_tradable_state()

        # 获取当前价格
        if self.daily_mode:
            bar = self._get_current_daily_bar(code)
            current_price = bar.close if bar else None
        else:
            current_price = self.playback_engine.get_current_price(code)

        return self.trading_engine.submit_sell_order(
            code, price, quantity, self.current_date, current_price
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销挂单。
        
        Args:
            order_id: 订单ID
            
        Returns:
            bool: 是否撤单成功
        """
        return self.trading_engine.cancel_order(order_id)
    
    def get_pending_orders(self) -> list[Order]:
        """获取所有挂单"""
        return self.trading_engine.get_pending_orders()
    
    def check_pending_orders(
        self,
        prices: dict[str, float],
        current_date: Optional[date] = None,
    ) -> list[Order]:
        """
        检查挂单是否可以成交。
        
        Args:
            prices: 当前价格字典
            
        Returns:
            list[Order]: 本次成交的订单列表
        """
        return self.trading_engine.check_pending_orders(
            prices,
            current_date or self.current_date,
        )
    
    def next_day(self) -> bool:
        """
        进入下一个交易日。
        
        - 更新日期
        - 更新持仓价格（使用前一日收盘价）
        - 记录净值
        - 保留未成交的挂单（不自动撤销）
        
        Returns:
            False 表示已到达结束日期
        """
        self.date_index += 1
        
        if self.date_index >= len(self.trading_dates):
            return False
        
        self.current_date = self.trading_dates[self.date_index]
        
        # 更新持仓价格（使用当日收盘价）
        self._update_position_prices()
        
        # 记录净值
        self.net_value_history.append((self.current_date, self.account.total_assets))
        
        # 同步状态。日线模式不调用分时播放引擎，也不会读取分钟数据。
        if self.daily_mode:
            self.playback_engine.date_index = self.date_index
            self.playback_engine.current_date = self.current_date
            self.playback_engine.state = PlaybackState.PAUSED
            closing_prices = {
                code: bar.close for code, bar in self.get_current_bars().items()
            }
            self.check_pending_orders(closing_prices, self.current_date)
        else:
            self.playback_engine.next_day()
        
        return True
    
    def step(self) -> bool:
        """
        推进一天（兼容旧接口）。
        
        - 更新日期
        - 更新持仓价格
        - 记录净值
        
        Returns:
            False 表示已到达结束日期
        """
        return self.next_day()
    
    def _update_position_prices(self) -> None:
        """更新所有持仓的当前价格。"""
        if self.current_date is None:
            return
        
        price_dict = {}
        for code in self.account.positions:
            bar = self._get_current_daily_bar(code)
            if bar:
                price_dict[code] = bar.close
        
        self.account.update_prices(price_dict)

    
    def run_backtest(self, strategy: StrategyFunc) -> PerformanceMetrics:
        """
        自动回测模式。
        
        - 遍历所有交易日
        - 每天调用策略函数
        - 执行策略返回的交易指令
        - 计算并返回绩效指标
        
        Args:
            strategy: 策略函数，接收 (当前日期, 当日行情字典, 账户状态)，
                     返回交易指令列表 [(order_type, code, price, quantity), ...]
                     
        Returns:
            PerformanceMetrics: 绩效指标
        """
        if not self.trading_dates:
            raise InvalidOrderError("模拟器未初始化或无交易日数据")
        
        # 重置到第一个交易日
        self.date_index = 0
        self.current_date = self.trading_dates[0]
        self.net_value_history = [(self.current_date, self.account.total_assets)]
        
        # 遍历所有交易日
        while True:
            # 获取当日行情
            current_bars = self.get_current_bars()

            if current_bars:
                # 更新持仓价格
                self._update_position_prices()

                # 检查历史挂单能否以当日收盘价成交
                close_prices = {code: bar.close for code, bar in current_bars.items()}
                self.trading_engine.check_pending_orders(close_prices, self.current_date)

                # 调用策略函数
                trade_instructions = strategy(
                    self.current_date,
                    current_bars,
                    self.account
                )
                
                # 执行交易指令
                if trade_instructions:
                    self._execute_trade_instructions(trade_instructions, current_bars)
            
            # 记录净值
            self.net_value_history.append((self.current_date, self.account.total_assets))
            
            # 推进到下一天
            if not self.next_day():
                break
        
        # 计算并返回绩效指标
        return self.calculate_metrics()
    
    def _execute_trade_instructions(
        self,
        instructions: list[tuple],
        current_bars: dict[str, DailyBar]
    ) -> None:
        """
        执行交易指令列表。
        
        Args:
            instructions: 交易指令列表 [(order_type, code, price, quantity), ...]
            current_bars: 当日行情字典
        """
        for instruction in instructions:
            if len(instruction) < 4:
                continue
            
            order_type, code, price, quantity = instruction[:4]
            
            # 获取当日行情用于价格验证
            daily_bar = current_bars.get(code)
            
            if order_type == "buy" or order_type == OrderType.BUY:
                self.trading_engine.submit_buy_order(
                    code=code,
                    price=price,
                    quantity=quantity,
                    current_date=self.current_date,
                    current_price=daily_bar.close if daily_bar else None,
                    daily_bar=daily_bar
                )
            elif order_type == "sell" or order_type == OrderType.SELL:
                self.trading_engine.submit_sell_order(
                    code=code,
                    price=price,
                    quantity=quantity,
                    current_date=self.current_date,
                    current_price=daily_bar.close if daily_bar else None,
                    daily_bar=daily_bar
                )

    
    def calculate_metrics(self) -> PerformanceMetrics:
        """
        计算绩效指标。
        
        Returns:
            PerformanceMetrics: 包含总收益率、最大回撤、胜率、夏普比率等指标
        """
        # 计算总收益率
        total_return = self._calculate_total_return()
        
        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()
        
        # 计算胜率
        win_rate, winning_trades, losing_trades, total_trades = self._calculate_win_rate()
        
        # 计算夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        return PerformanceMetrics(
            total_return=total_return,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    def _calculate_total_return(self) -> float:
        """
        计算总收益率。
        
        公式: (期末总资产 - 初始资金) / 初始资金
        
        Returns:
            总收益率（小数形式，如 0.1 表示 10%）
        """
        if self._initial_cash == 0:
            return 0.0
        
        final_assets = self.account.total_assets
        return (final_assets - self._initial_cash) / self._initial_cash
    
    def _calculate_max_drawdown(self) -> float:
        """
        计算最大回撤。
        
        公式: max((peak - trough) / peak)
        其中 peak 是某点之前的最高值，trough 是该点之后的最低值
        
        Returns:
            最大回撤（小数形式，如 0.1 表示 10%）
        """
        if not self.net_value_history:
            return 0.0
        
        values = [v for _, v in self.net_value_history]
        
        if len(values) < 2:
            return 0.0
        
        max_drawdown = 0.0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            
            if peak > 0:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率。
        
        公式: (平均收益率 - 无风险利率) / 收益率标准差
        
        Args:
            risk_free_rate: 年化无风险利率，默认 3%
            
        Returns:
            夏普比率
        """
        if len(self.net_value_history) < 2:
            return 0.0
        
        import numpy as np
        
        values = [v for _, v in self.net_value_history]
        
        # 计算日收益率
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                daily_return = (values[i] - values[i - 1]) / values[i - 1]
                returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        returns = np.array(returns)
        
        # 计算平均日收益率和标准差
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # 年化（假设 252 个交易日）
        annual_return = mean_return * 252
        annual_std = std_return * np.sqrt(252)
        
        # 计算夏普比率
        sharpe = (annual_return - risk_free_rate) / annual_std
        
        return float(sharpe)
    
    def _calculate_win_rate(self) -> tuple[float, int, int, int]:
        """
        计算胜率。
        
        公式: 盈利交易次数 / 总交易次数
        盈利交易定义为：卖出价 > 买入成本价
        
        Returns:
            tuple: (胜率, 盈利交易数, 亏损交易数, 总交易数)
        """
        trade_history = self.trading_engine.get_trade_history()
        
        # 只统计已成交的卖出订单
        sell_orders = [
            order for order in trade_history
            if order.order_type == OrderType.SELL and order.status == OrderStatus.FILLED
        ]
        
        if not sell_orders:
            return 0.0, 0, 0, 0
        
        # 计算每笔卖出是否盈利
        # 简化处理：比较卖出价与买入成本价
        # 需要追踪买入成本，这里使用简化方法
        winning_trades = 0
        losing_trades = 0
        
        # 构建买入记录用于计算成本
        buy_costs: dict[str, list[tuple[float, int]]] = {}  # code -> [(cost_price, quantity), ...]
        
        for order in trade_history:
            if order.order_type == OrderType.BUY and order.status == OrderStatus.FILLED:
                if order.code not in buy_costs:
                    buy_costs[order.code] = []
                # 成本价包含手续费
                cost_per_share = order.price + order.fee / order.quantity
                buy_costs[order.code].append((cost_per_share, order.quantity))
        
        for sell_order in sell_orders:
            code = sell_order.code
            sell_price = sell_order.price
            sell_quantity = sell_order.quantity
            
            # 计算该卖出对应的平均买入成本（FIFO）
            if code in buy_costs and buy_costs[code]:
                total_cost = 0.0
                remaining_quantity = sell_quantity
                
                while remaining_quantity > 0 and buy_costs[code]:
                    cost_price, buy_quantity = buy_costs[code][0]
                    
                    if buy_quantity <= remaining_quantity:
                        total_cost += cost_price * buy_quantity
                        remaining_quantity -= buy_quantity
                        buy_costs[code].pop(0)
                    else:
                        total_cost += cost_price * remaining_quantity
                        buy_costs[code][0] = (cost_price, buy_quantity - remaining_quantity)
                        remaining_quantity = 0
                
                avg_cost = total_cost / sell_quantity if sell_quantity > 0 else 0
                
                # 判断是否盈利（考虑卖出手续费）
                net_sell_price = sell_price - sell_order.fee / sell_quantity
                if net_sell_price > avg_cost:
                    winning_trades += 1
                else:
                    losing_trades += 1
            else:
                # 没有对应的买入记录，视为亏损
                losing_trades += 1
        
        total_trades = winning_trades + losing_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return win_rate, winning_trades, losing_trades, total_trades
