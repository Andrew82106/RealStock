#!/usr/bin/env python3
"""
交互式播放示例 - Interactive Playback Example

本示例展示如何使用 A 股模拟交易回测系统的日内播放模式。
用户可以控制行情播放速度，在暂停时进行交易决策。

使用方法:
    python examples/interactive_play.py

功能:
    - 播放日内分时行情
    - 暂停/继续播放
    - 在暂停状态下进行买入/卖出操作
    - 查看账户状态和持仓信息
    - 切换到下一个交易日

注意:
    - 首次运行需要从 AkShare 下载数据
    - 分时数据可能基于日线数据模拟生成
"""

import sys
import time
from datetime import date
from typing import Optional

from src.account.account import Account
from src.data_engine.engine import DataEngine
from src.exceptions import InvalidOrderError
from src.playback.models import IntradayTick, PlaybackState
from src.simulator.simulator import Simulator
from src.trading.models import OrderStatus


class InteractivePlayer:
    """交互式播放器。"""
    
    def __init__(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
        initial_cash: float = 100000.0
    ):
        """
        初始化交互式播放器。
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
        """
        self.stock_codes = stock_codes
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        
        self.data_engine: Optional[DataEngine] = None
        self.simulator: Optional[Simulator] = None
        self.current_prices: dict[str, float] = {}
        self.speed = 10.0  # 默认10倍速
    
    def initialize(self) -> bool:
        """
        初始化系统。
        
        Returns:
            是否初始化成功
        """
        print("正在初始化数据引擎...")
        self.data_engine = DataEngine(cache_dir="./data_cache")
        
        print("正在初始化模拟器...")
        self.simulator = Simulator(self.data_engine, initial_cash=self.initial_cash)
        
        print("正在加载历史数据...")
        try:
            self.simulator.setup(
                stock_codes=self.stock_codes,
                start_date=self.start_date,
                end_date=self.end_date
            )
        except Exception as e:
            print(f"错误: 无法加载数据 - {e}")
            return False
        
        print(f"已加载 {len(self.simulator.trading_dates)} 个交易日的数据")
        return True
    
    def print_status(self):
        """打印当前状态。"""
        print("\n" + "-" * 50)
        print(f"日期: {self.simulator.current_date}")
        print(f"播放状态: {self.simulator.playback_engine.state.value}")
        print(f"播放速度: {self.speed}x")
        
        print(f"\n账户状态:")
        print(f"  总资产: {self.simulator.account.total_assets:,.2f} 元")
        print(f"  可用现金: {self.simulator.account.cash:,.2f} 元")
        print(f"  持仓市值: {self.simulator.account.total_market_value:,.2f} 元")
        
        if self.current_prices:
            print(f"\n当前行情:")
            for code, price in self.current_prices.items():
                print(f"  {code}: {price:.2f}")
        
        if self.simulator.account.positions:
            print(f"\n持仓明细:")
            for code, pos in self.simulator.account.positions.items():
                print(f"  {code}: {pos.quantity} 股, "
                      f"成本 {pos.cost_price:.2f}, "
                      f"现价 {pos.current_price:.2f}, "
                      f"盈亏 {pos.profit_loss:.2f}")
        
        print("-" * 50)
    
    def print_help(self):
        """打印帮助信息。"""
        print("\n可用命令:")
        print("  p, play     - 开始/继续播放")
        print("  s, stop     - 暂停播放")
        print("  b <code> <price> <qty> - 买入股票")
        print("  l <code> <price> <qty> - 卖出股票")
        print("  n, next     - 下一个交易日")
        print("  v, view     - 查看当前状态")
        print("  speed <n>   - 设置播放速度 (1-100)")
        print("  h, help     - 显示帮助")
        print("  q, quit     - 退出")
    
    def handle_buy(self, args: list[str]):
        """处理买入命令。"""
        if len(args) < 3:
            print("用法: b <股票代码> <价格> <数量>")
            print("示例: b 600519 1500 100")
            return
        
        try:
            code = args[0]
            price = float(args[1])
            quantity = int(args[2])
            
            order = self.simulator.buy(code, price, quantity)
            
            if order.status == OrderStatus.FILLED:
                print(f"买入成功: {code} {quantity}股 @ {price:.2f}")
                print(f"手续费: {order.fee:.2f} 元")
            else:
                print(f"买入失败: {order.reject_reason}")
                
        except InvalidOrderError as e:
            print(f"错误: {e}")
        except ValueError:
            print("错误: 价格和数量必须是有效的数字")
    
    def handle_sell(self, args: list[str]):
        """处理卖出命令。"""
        if len(args) < 3:
            print("用法: l <股票代码> <价格> <数量>")
            print("示例: l 600519 1520 100")
            return
        
        try:
            code = args[0]
            price = float(args[1])
            quantity = int(args[2])
            
            order = self.simulator.sell(code, price, quantity)
            
            if order.status == OrderStatus.FILLED:
                print(f"卖出成功: {code} {quantity}股 @ {price:.2f}")
                print(f"手续费: {order.fee:.2f} 元")
            else:
                print(f"卖出失败: {order.reject_reason}")
                
        except InvalidOrderError as e:
            print(f"错误: {e}")
        except ValueError:
            print("错误: 价格和数量必须是有效的数字")
    
    def handle_speed(self, args: list[str]):
        """处理速度设置命令。"""
        if len(args) < 1:
            print(f"当前速度: {self.speed}x")
            print("用法: speed <1-100>")
            return
        
        try:
            speed = float(args[0])
            if 1 <= speed <= 100:
                self.speed = speed
                self.simulator.playback_engine.set_speed(speed)
                print(f"播放速度已设置为: {speed}x")
            else:
                print("错误: 速度必须在 1-100 之间")
        except ValueError:
            print("错误: 速度必须是有效的数字")
    
    def play_ticks(self, max_ticks: int = 10):
        """
        播放若干个 tick。
        
        Args:
            max_ticks: 最大播放 tick 数
        """
        self.simulator.play(self.speed)
        
        ticks_played = 0
        while (self.simulator.playback_engine.state == PlaybackState.PLAYING 
               and ticks_played < max_ticks):
            tick_data = self.simulator.playback_engine.tick()
            
            if tick_data:
                ticks_played += 1
                self.current_prices = {
                    code: tick.price for code, tick in tick_data.items()
                }
                
                # 更新持仓价格
                self.simulator.account.update_prices(self.current_prices)
                
                # 显示当前价格
                price_str = ", ".join(
                    f"{code}: {price:.2f}" 
                    for code, price in self.current_prices.items()
                )
                print(f"[Tick {ticks_played}] {price_str}")
            
            time.sleep(0.1 / self.speed)
        
        # 暂停播放
        self.simulator.pause()
        
        if self.simulator.playback_engine.state == PlaybackState.DAY_ENDED:
            print("\n当日行情播放完毕!")
            print("输入 'n' 或 'next' 进入下一个交易日")
    
    def run(self):
        """运行交互式播放器。"""
        print("=" * 60)
        print("A 股模拟交易回测系统 - 交互式播放模式")
        print("=" * 60)
        
        if not self.initialize():
            return
        
        # 加载第一天的数据
        self.simulator.start_day()
        
        self.print_help()
        self.print_status()
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                
                if not cmd:
                    continue
                
                parts = cmd.split()
                command = parts[0]
                args = parts[1:]
                
                if command in ("q", "quit", "exit"):
                    print("再见!")
                    break
                
                elif command in ("h", "help"):
                    self.print_help()
                
                elif command in ("v", "view"):
                    self.print_status()
                
                elif command in ("p", "play"):
                    if self.simulator.playback_engine.state == PlaybackState.DAY_ENDED:
                        print("当日已结束，请输入 'n' 进入下一交易日")
                    else:
                        print("开始播放... (播放10个tick后自动暂停)")
                        self.play_ticks(10)
                
                elif command in ("s", "stop"):
                    self.simulator.pause()
                    print("已暂停")
                
                elif command in ("b", "buy"):
                    self.handle_buy(args)
                
                elif command in ("l", "sell"):
                    self.handle_sell(args)
                
                elif command in ("n", "next"):
                    if self.simulator.next_day():
                        self.simulator.start_day()
                        print(f"已进入交易日: {self.simulator.current_date}")
                        self.print_status()
                    else:
                        print("已到达最后一个交易日!")
                        self.print_final_report()
                        break
                
                elif command == "speed":
                    self.handle_speed(args)
                
                else:
                    print(f"未知命令: {command}")
                    print("输入 'h' 或 'help' 查看帮助")
                    
            except KeyboardInterrupt:
                print("\n\n已中断")
                break
            except EOFError:
                print("\n再见!")
                break
    
    def print_final_report(self):
        """打印最终报告。"""
        print("\n" + "=" * 60)
        print("最终绩效报告")
        print("=" * 60)
        
        metrics = self.simulator.calculate_metrics()
        
        print(f"\n绩效指标:")
        print(f"  总收益率: {metrics.total_return * 100:.2f}%")
        print(f"  最大回撤: {metrics.max_drawdown * 100:.2f}%")
        print(f"  胜率: {metrics.win_rate * 100:.2f}%")
        print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
        
        print(f"\n交易统计:")
        print(f"  总交易次数: {metrics.total_trades}")
        print(f"  盈利交易: {metrics.winning_trades}")
        print(f"  亏损交易: {metrics.losing_trades}")
        
        print(f"\n最终账户状态:")
        print(f"  期末总资产: {self.simulator.account.total_assets:,.2f} 元")
        print(f"  可用现金: {self.simulator.account.cash:,.2f} 元")
        print(f"  持仓市值: {self.simulator.account.total_market_value:,.2f} 元")
        
        print("=" * 60)


def main():
    """主函数。"""
    # 配置参数
    stock_codes = ["000001"]  # 平安银行
    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)  # 只播放一个月
    initial_cash = 100000.0
    
    print(f"配置:")
    print(f"  股票: {stock_codes}")
    print(f"  日期范围: {start_date} 至 {end_date}")
    print(f"  初始资金: {initial_cash:,.2f} 元")
    
    player = InteractivePlayer(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash
    )
    
    player.run()


if __name__ == "__main__":
    main()
