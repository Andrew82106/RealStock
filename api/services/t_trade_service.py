"""
做T交易服务 - T-Trade Service
Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""
from collections import defaultdict
from typing import Optional
import uuid

from api.services.t_trade_models import (
    TTradeRecord,
    TTradeStatistics,
    TradeRecord,
)


class TTradeService:
    """做T交易服务"""
    
    def detect_t_trades(self, trade_history: list[TradeRecord]) -> list[TTradeRecord]:
        """
        从交易历史中检测做T交易
        
        做T定义：在同一交易日内，对同一只股票先卖出后买入（正T）
        
        检测逻辑：
        1. 按日期和股票代码分组交易
        2. 在每组中，找到卖出后跟随买入的配对
        3. 计算每对做T的盈亏
        
        Args:
            trade_history: 交易历史记录列表
            
        Returns:
            检测到的做T交易记录列表
        """
        if not trade_history:
            return []
        
        # 按日期和股票代码分组
        grouped_trades: dict[str, dict[str, list[TradeRecord]]] = defaultdict(lambda: defaultdict(list))
        
        for trade in trade_history:
            date = trade.trade_date
            code = trade.code
            grouped_trades[date][code].append(trade)
        
        t_trades = []
        
        # 遍历每个日期和股票的交易
        for date, stocks in grouped_trades.items():
            for code, trades in stocks.items():
                # 按时间排序
                sorted_trades = sorted(trades, key=lambda t: t.timestamp)
                
                # 查找做T配对：卖出后买入
                sell_queue = []  # 待匹配的卖出订单
                
                for trade in sorted_trades:
                    if trade.order_type == "sell":
                        sell_queue.append(trade)
                    elif trade.order_type == "buy" and sell_queue:
                        # 找到一个做T配对
                        sell_trade = sell_queue.pop(0)
                        
                        # 计算做T数量（取较小值）
                        t_quantity = min(sell_trade.quantity, trade.quantity)
                        
                        # 计算盈亏
                        # 做T盈亏 = (卖出价 - 买入价) * 数量 - 手续费
                        gross_profit = (sell_trade.price - trade.price) * t_quantity
                        
                        # 按比例计算手续费
                        sell_fee_ratio = t_quantity / sell_trade.quantity if sell_trade.quantity > 0 else 1
                        buy_fee_ratio = t_quantity / trade.quantity if trade.quantity > 0 else 1
                        sell_fee = sell_trade.fee * sell_fee_ratio
                        buy_fee = trade.fee * buy_fee_ratio
                        
                        net_profit = gross_profit - sell_fee - buy_fee
                        
                        t_trade = TTradeRecord(
                            id=f"t_{uuid.uuid4().hex[:8]}",
                            stock_code=code,
                            sell_price=sell_trade.price,
                            buy_price=trade.price,
                            quantity=t_quantity,
                            sell_fee=sell_fee,
                            buy_fee=buy_fee,
                            profit=net_profit,
                            trade_date=date,
                            sell_time=sell_trade.timestamp,
                            buy_time=trade.timestamp,
                        )
                        t_trades.append(t_trade)
                        
                        # 如果卖出数量大于买入数量，剩余部分放回队列
                        if sell_trade.quantity > trade.quantity:
                            remaining_sell = TradeRecord(
                                order_id=sell_trade.order_id + "_remaining",
                                code=sell_trade.code,
                                order_type="sell",
                                price=sell_trade.price,
                                quantity=sell_trade.quantity - trade.quantity,
                                fee=sell_trade.fee * (1 - sell_fee_ratio),
                                timestamp=sell_trade.timestamp,
                            )
                            sell_queue.insert(0, remaining_sell)
        
        return t_trades
    
    def calculate_statistics(self, t_trades: list[TTradeRecord]) -> TTradeStatistics:
        """
        计算做T统计数据
        
        Args:
            t_trades: 做T交易记录列表
            
        Returns:
            做T统计数据
        """
        if not t_trades:
            return TTradeStatistics()
        
        total_trades = len(t_trades)
        successful_trades = sum(1 for t in t_trades if t.is_successful)
        failed_trades = total_trades - successful_trades
        
        success_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        total_profit = sum(t.profit for t in t_trades)
        total_fees = sum(t.total_fee for t in t_trades)
        
        profits = [t.profit for t in t_trades]
        best_trade_profit = max(profits) if profits else 0.0
        worst_trade_loss = min(profits) if profits else 0.0
        
        average_profit = total_profit / total_trades if total_trades > 0 else 0.0
        
        return TTradeStatistics(
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            success_rate=success_rate,
            total_profit=total_profit,
            total_fees=total_fees,
            best_trade_profit=best_trade_profit,
            worst_trade_loss=worst_trade_loss,
            average_profit=average_profit,
            trades=t_trades,
        )
    
    def get_daily_t_trade_count(self, t_trades: list[TTradeRecord], date: str) -> tuple[int, int]:
        """
        获取指定日期的做T统计
        
        Args:
            t_trades: 做T交易记录列表
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            (总做T次数, 成功做T次数)
        """
        daily_trades = [t for t in t_trades if t.trade_date == date]
        total = len(daily_trades)
        successful = sum(1 for t in daily_trades if t.is_successful)
        return total, successful
    
    def get_t_trades_by_stock(self, t_trades: list[TTradeRecord], stock_code: str) -> list[TTradeRecord]:
        """
        获取指定股票的做T记录
        
        Args:
            t_trades: 做T交易记录列表
            stock_code: 股票代码
            
        Returns:
            该股票的做T记录列表
        """
        return [t for t in t_trades if t.stock_code == stock_code]
    
    def get_t_trades_by_date_range(
        self, 
        t_trades: list[TTradeRecord], 
        start_date: str, 
        end_date: str
    ) -> list[TTradeRecord]:
        """
        获取指定日期范围的做T记录
        
        Args:
            t_trades: 做T交易记录列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            该日期范围内的做T记录列表
        """
        return [
            t for t in t_trades 
            if start_date <= t.trade_date <= end_date
        ]
    
    def calculate_statistics_from_save(self, save_data) -> TTradeStatistics:
        """
        从存档数据计算做T统计
        
        Args:
            save_data: 存档数据
            
        Returns:
            做T统计数据
        """
        # 将存档中的交易历史转换为 TradeRecord
        trade_records = []
        for t in save_data.trade_history:
            if isinstance(t, dict):
                trade_records.append(TradeRecord(
                    order_id=t.get("order_id", ""),
                    code=t.get("code", ""),
                    order_type=t.get("order_type", ""),
                    price=t.get("price", 0.0),
                    quantity=t.get("quantity", 0),
                    fee=t.get("fee", 0.0),
                    timestamp=t.get("timestamp", ""),
                ))
            else:
                trade_records.append(TradeRecord(
                    order_id=getattr(t, "order_id", ""),
                    code=getattr(t, "code", ""),
                    order_type=getattr(t, "order_type", ""),
                    price=getattr(t, "price", 0.0),
                    quantity=getattr(t, "quantity", 0),
                    fee=getattr(t, "fee", 0.0),
                    timestamp=getattr(t, "timestamp", ""),
                ))
        
        # 检测做T交易
        t_trades = self.detect_t_trades(trade_records)
        
        # 计算统计
        return self.calculate_statistics(t_trades)


# 全局服务实例
t_trade_service = TTradeService()
