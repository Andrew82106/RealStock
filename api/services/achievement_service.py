"""
成就服务 - Achievement Service
Requirements: 1.4, 1.5, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.6
"""
from datetime import datetime
from typing import Optional

from api.services.achievement_models import (
    AchievementDefinition,
    AchievementProgress,
    AchievementContext,
    UnlockedAchievement,
    AchievementCategory,
    AchievementRarity,
    ChallengeDifficulty,
)
from api.services.achievement_definitions import (
    ALL_ACHIEVEMENTS,
    ACHIEVEMENT_MAP,
    get_all_achievements,
    get_achievement_by_id,
)


class AchievementService:
    """成就服务"""
    
    def __init__(self):
        self.achievements = ALL_ACHIEVEMENTS
        self.achievement_map = ACHIEVEMENT_MAP
    
    def get_all_definitions(self) -> list[AchievementDefinition]:
        """获取所有成就定义"""
        return get_all_achievements()
    
    def get_definition(self, achievement_id: str) -> Optional[AchievementDefinition]:
        """获取单个成就定义"""
        return get_achievement_by_id(achievement_id)
    
    def get_definitions_by_category(self, category: str) -> list[AchievementDefinition]:
        """获取指定分类的成就定义"""
        try:
            cat = AchievementCategory(category)
            return [a for a in self.achievements if a.category == cat]
        except ValueError:
            return []
    
    def create_empty_progress(self) -> AchievementProgress:
        """创建空的成就进度（用于新存档）"""
        return AchievementProgress(
            unlocked_achievements=[],
            progress_map={},
            new_achievements=[],
        )
    
    def check_and_unlock_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """
        检查并解锁成就
        返回新解锁的成就ID列表
        """
        newly_unlocked = []
        
        # 检查交易类成就
        newly_unlocked.extend(self._check_trading_achievements(progress, context))
        
        # 检查收益类成就
        newly_unlocked.extend(self._check_profit_achievements(progress, context))
        
        # 检查里程碑类成就
        newly_unlocked.extend(self._check_milestone_achievements(progress, context))
        
        # 检查连续类成就
        newly_unlocked.extend(self._check_streak_achievements(progress, context))
        
        # 检查做T类成就
        newly_unlocked.extend(self._check_t_trade_achievements(progress, context))
        
        # 检查特殊类成就
        newly_unlocked.extend(self._check_special_achievements(progress, context))
        
        # 检查挑战类成就
        newly_unlocked.extend(self._check_challenge_achievements(progress, context))
        
        return newly_unlocked
    
    def _check_trading_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查交易类成就"""
        newly_unlocked = []
        
        # 初次交易
        if context.total_buy_trades >= 1:
            progress.update_progress("first_trade", 1)
            if progress.unlock("first_trade"):
                newly_unlocked.append("first_trade")
        
        # 活跃交易者 (10笔)
        progress.update_progress("active_trader", context.total_trades)
        if context.total_trades >= 10:
            if progress.unlock("active_trader"):
                newly_unlocked.append("active_trader")
        
        # 交易大师 (100笔)
        progress.update_progress("trading_master", context.total_trades)
        if context.total_trades >= 100:
            if progress.unlock("trading_master"):
                newly_unlocked.append("trading_master")
        
        # 分散投资 (5只股票)
        progress.update_progress("diversified_portfolio", context.unique_stocks_held)
        if context.unique_stocks_held >= 5:
            if progress.unlock("diversified_portfolio"):
                newly_unlocked.append("diversified_portfolio")
        
        # 大手笔 (单笔10万)
        progress.update_progress("big_spender", context.largest_single_trade_amount)
        if context.largest_single_trade_amount >= 100000:
            if progress.unlock("big_spender"):
                newly_unlocked.append("big_spender")
        
        return newly_unlocked
    
    def _check_profit_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查收益类成就"""
        newly_unlocked = []
        
        # 盈利新手 (10%)
        progress.update_progress("profitable_beginner", context.total_return_pct)
        if context.total_return_pct >= 10:
            if progress.unlock("profitable_beginner"):
                newly_unlocked.append("profitable_beginner")
        
        # 投资高手 (50%)
        progress.update_progress("skilled_investor", context.total_return_pct)
        if context.total_return_pct >= 50:
            if progress.unlock("skilled_investor"):
                newly_unlocked.append("skilled_investor")
        
        # 翻倍达人 (100%)
        progress.update_progress("double_your_money", context.total_return_pct)
        if context.total_return_pct >= 100:
            if progress.unlock("double_your_money"):
                newly_unlocked.append("double_your_money")
        
        # 交易传奇 (500%)
        progress.update_progress("trading_legend", context.total_return_pct)
        if context.total_return_pct >= 500:
            if progress.unlock("trading_legend"):
                newly_unlocked.append("trading_legend")
        
        # 日赢家 (单日1万)
        progress.update_progress("daily_winner", context.daily_profit)
        if context.daily_profit >= 10000:
            if progress.unlock("daily_winner"):
                newly_unlocked.append("daily_winner")
        
        # 大丰收 (单日10万)
        progress.update_progress("jackpot_day", context.daily_profit)
        if context.daily_profit >= 100000:
            if progress.unlock("jackpot_day"):
                newly_unlocked.append("jackpot_day")
        
        return newly_unlocked
    
    def _check_milestone_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查里程碑类成就"""
        newly_unlocked = []
        
        # 小有成就 (20万)
        progress.update_progress("first_milestone", context.current_total_assets)
        if context.current_total_assets >= 200000:
            if progress.unlock("first_milestone"):
                newly_unlocked.append("first_milestone")
        
        # 半百万富翁 (50万)
        progress.update_progress("half_millionaire", context.current_total_assets)
        if context.current_total_assets >= 500000:
            if progress.unlock("half_millionaire"):
                newly_unlocked.append("half_millionaire")
        
        # 百万富翁 (100万)
        progress.update_progress("millionaire", context.current_total_assets)
        if context.current_total_assets >= 1000000:
            if progress.unlock("millionaire"):
                newly_unlocked.append("millionaire")
        
        # 月度交易员 (30天)
        progress.update_progress("monthly_trader", context.trading_days_count)
        if context.trading_days_count >= 30:
            if progress.unlock("monthly_trader"):
                newly_unlocked.append("monthly_trader")
        
        # 年度老手 (250天)
        progress.update_progress("annual_veteran", context.trading_days_count)
        if context.trading_days_count >= 250:
            if progress.unlock("annual_veteran"):
                newly_unlocked.append("annual_veteran")
        
        return newly_unlocked
    
    def _check_streak_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查连续类成就"""
        newly_unlocked = []
        
        # 连胜开始 (3天)
        progress.update_progress("winning_streak", context.consecutive_profit_days)
        if context.consecutive_profit_days >= 3:
            if progress.unlock("winning_streak"):
                newly_unlocked.append("winning_streak")
        
        # 手感火热 (7天)
        progress.update_progress("hot_hand", context.consecutive_profit_days)
        if context.consecutive_profit_days >= 7:
            if progress.unlock("hot_hand"):
                newly_unlocked.append("hot_hand")
        
        # 势不可挡 (30天)
        progress.update_progress("unstoppable", context.consecutive_profit_days)
        if context.consecutive_profit_days >= 30:
            if progress.unlock("unstoppable"):
                newly_unlocked.append("unstoppable")
        
        # 勤奋交易员 (连续5天交易)
        progress.update_progress("dedicated_trader", context.consecutive_trading_days)
        if context.consecutive_trading_days >= 5:
            if progress.unlock("dedicated_trader"):
                newly_unlocked.append("dedicated_trader")
        
        return newly_unlocked
    
    def _check_t_trade_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查做T类成就"""
        newly_unlocked = []
        
        # 做T新手
        if context.total_t_trades >= 1:
            progress.update_progress("t_trade_beginner", 1)
            if progress.unlock("t_trade_beginner"):
                newly_unlocked.append("t_trade_beginner")
        
        # 做T学徒 (10次成功)
        progress.update_progress("t_trade_apprentice", context.successful_t_trades)
        if context.successful_t_trades >= 10:
            if progress.unlock("t_trade_apprentice"):
                newly_unlocked.append("t_trade_apprentice")
        
        # 做T专家 (50次成功)
        progress.update_progress("t_trade_expert", context.successful_t_trades)
        if context.successful_t_trades >= 50:
            if progress.unlock("t_trade_expert"):
                newly_unlocked.append("t_trade_expert")
        
        # 做T大师 (100次成功)
        progress.update_progress("t_trade_master", context.successful_t_trades)
        if context.successful_t_trades >= 100:
            if progress.unlock("t_trade_master"):
                newly_unlocked.append("t_trade_master")
        
        # 稳定做T者 (60%成功率，至少20次)
        if context.total_t_trades >= 20:
            progress.update_progress("consistent_t_trader", context.t_trade_success_rate)
            if context.t_trade_success_rate >= 60:
                if progress.unlock("consistent_t_trader"):
                    newly_unlocked.append("consistent_t_trader")
        
        # 做T完美主义者 (80%成功率，至少50次)
        if context.total_t_trades >= 50:
            progress.update_progress("t_trade_perfectionist", context.t_trade_success_rate)
            if context.t_trade_success_rate >= 80:
                if progress.unlock("t_trade_perfectionist"):
                    newly_unlocked.append("t_trade_perfectionist")
        
        # 大T赢家 (单次1000元)
        progress.update_progress("big_t_win", context.best_t_trade_profit)
        if context.best_t_trade_profit >= 1000:
            if progress.unlock("big_t_win"):
                newly_unlocked.append("big_t_win")
        
        # 做T头奖 (单次10000元)
        progress.update_progress("t_trade_jackpot", context.best_t_trade_profit)
        if context.best_t_trade_profit >= 10000:
            if progress.unlock("t_trade_jackpot"):
                newly_unlocked.append("t_trade_jackpot")
        
        # 做T百万富翁 (累计5万)
        progress.update_progress("t_trade_millionaire", context.cumulative_t_trade_profit)
        if context.cumulative_t_trade_profit >= 50000:
            if progress.unlock("t_trade_millionaire"):
                newly_unlocked.append("t_trade_millionaire")
        
        # 日内交易员 (单日5次成功)
        progress.update_progress("day_trader", context.daily_successful_t_trades)
        if context.daily_successful_t_trades >= 5:
            if progress.unlock("day_trader"):
                newly_unlocked.append("day_trader")
        
        return newly_unlocked
    
    def _check_special_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查特殊类成就"""
        newly_unlocked = []
        
        # 涨停猎手
        if context.caught_limit_up:
            progress.update_progress("limit_hunter", 1)
            if progress.unlock("limit_hunter"):
                newly_unlocked.append("limit_hunter")
        
        # 风险规避者
        if context.avoided_limit_down:
            progress.update_progress("risk_avoider", 1)
            if progress.unlock("risk_avoider"):
                newly_unlocked.append("risk_avoider")
        
        # 选股高手 (单股50%)
        progress.update_progress("stock_picker", context.best_single_stock_gain_pct)
        if context.best_single_stock_gain_pct >= 50:
            if progress.unlock("stock_picker"):
                newly_unlocked.append("stock_picker")
        
        # 逆袭之王
        if context.recovered_from_drawdown:
            progress.update_progress("comeback_king", 1)
            if progress.unlock("comeback_king"):
                newly_unlocked.append("comeback_king")
        
        # 风控大师 (夏普比率2.0以上30天)
        progress.update_progress("risk_master", context.sharpe_ratio_30d)
        if context.sharpe_ratio_30d >= 2.0:
            if progress.unlock("risk_master"):
                newly_unlocked.append("risk_master")
        
        return newly_unlocked
    
    def _check_challenge_achievements(
        self, 
        progress: AchievementProgress, 
        context: AchievementContext
    ) -> list[str]:
        """检查挑战类成就"""
        newly_unlocked = []
        
        # 挑战已接受
        if context.challenges_passed >= 1:
            progress.update_progress("challenge_accepted", 1)
            if progress.unlock("challenge_accepted"):
                newly_unlocked.append("challenge_accepted")
        
        # 简单赢家
        if context.easy_challenges_passed >= 1:
            progress.update_progress("easy_winner", 1)
            if progress.unlock("easy_winner"):
                newly_unlocked.append("easy_winner")
        
        # 中等大师
        if context.medium_challenges_passed >= 1:
            progress.update_progress("medium_master", 1)
            if progress.unlock("medium_master"):
                newly_unlocked.append("medium_master")
        
        # 困难英雄
        if context.hard_challenges_passed >= 1:
            progress.update_progress("hard_mode_hero", 1)
            if progress.unlock("hard_mode_hero"):
                newly_unlocked.append("hard_mode_hero")
        
        # 挑战老手 (5个)
        progress.update_progress("challenge_veteran", context.challenges_passed)
        if context.challenges_passed >= 5:
            if progress.unlock("challenge_veteran"):
                newly_unlocked.append("challenge_veteran")
        
        # 挑战传奇 (3个困难)
        progress.update_progress("challenge_legend", context.hard_challenges_passed)
        if context.hard_challenges_passed >= 3:
            if progress.unlock("challenge_legend"):
                newly_unlocked.append("challenge_legend")
        
        # 超额完成者
        if context.challenge_exceeded_target_50pct:
            progress.update_progress("overachiever", 1)
            if progress.unlock("overachiever"):
                newly_unlocked.append("overachiever")
        
        # 纯做T交易员
        if context.challenge_passed_with_only_t_trades:
            progress.update_progress("pure_t_trader", 1)
            if progress.unlock("pure_t_trader"):
                newly_unlocked.append("pure_t_trader")
        
        return newly_unlocked
    
    def calculate_statistics(self, progress: AchievementProgress) -> dict:
        """计算成就统计数据"""
        total_achievements = len(self.achievements)
        unlocked_count = len(progress.unlocked_achievements)
        
        # 按分类统计
        category_stats = {}
        for category in AchievementCategory:
            category_achievements = [a for a in self.achievements if a.category == category]
            category_unlocked = [
                a for a in category_achievements 
                if progress.is_unlocked(a.id)
            ]
            category_stats[category.value] = {
                "total": len(category_achievements),
                "unlocked": len(category_unlocked),
                "percentage": len(category_unlocked) / len(category_achievements) * 100 if category_achievements else 0,
            }
        
        # 按稀有度统计
        rarity_stats = {}
        for rarity in AchievementRarity:
            rarity_achievements = [a for a in self.achievements if a.rarity == rarity]
            rarity_unlocked = [
                a for a in rarity_achievements 
                if progress.is_unlocked(a.id)
            ]
            rarity_stats[rarity.value] = {
                "total": len(rarity_achievements),
                "unlocked": len(rarity_unlocked),
                "percentage": len(rarity_unlocked) / len(rarity_achievements) * 100 if rarity_achievements else 0,
            }
        
        # 最近解锁的成就
        recent_unlocked = sorted(
            progress.unlocked_achievements,
            key=lambda a: a.unlocked_at,
            reverse=True
        )[:5]
        
        # 最稀有的已解锁成就
        rarity_order = {
            AchievementRarity.LEGENDARY: 4,
            AchievementRarity.EPIC: 3,
            AchievementRarity.RARE: 2,
            AchievementRarity.COMMON: 1,
        }
        unlocked_with_rarity = [
            (ua, self.achievement_map.get(ua.achievement_id))
            for ua in progress.unlocked_achievements
            if ua.achievement_id in self.achievement_map
        ]
        rarest_unlocked = sorted(
            unlocked_with_rarity,
            key=lambda x: rarity_order.get(x[1].rarity, 0) if x[1] else 0,
            reverse=True
        )[:5]
        
        return {
            "total": total_achievements,
            "unlocked": unlocked_count,
            "percentage": unlocked_count / total_achievements * 100 if total_achievements else 0,
            "by_category": category_stats,
            "by_rarity": rarity_stats,
            "recent_unlocked": [
                {
                    "achievement_id": ua.achievement_id,
                    "unlocked_at": ua.unlocked_at,
                    "definition": self.achievement_map.get(ua.achievement_id).to_dict() if ua.achievement_id in self.achievement_map else None,
                }
                for ua in recent_unlocked
            ],
            "rarest_unlocked": [
                {
                    "achievement_id": ua.achievement_id,
                    "unlocked_at": ua.unlocked_at,
                    "definition": definition.to_dict() if definition else None,
                }
                for ua, definition in rarest_unlocked
            ],
        }
    
    def build_context_from_save(self, save_data) -> AchievementContext:
        """从存档数据构建成就检查上下文"""
        # 交易统计
        trades = save_data.trade_history
        total_trades = len(trades)
        total_buy_trades = sum(1 for t in trades if self._get_order_type(t) == "buy")
        total_sell_trades = sum(1 for t in trades if self._get_order_type(t) == "sell")
        
        # 计算最大单笔交易金额
        largest_trade = 0.0
        for t in trades:
            price = self._get_trade_price(t)
            qty = self._get_trade_quantity(t)
            amount = price * qty
            if amount > largest_trade:
                largest_trade = amount
        
        # 持有股票数
        unique_stocks = len(save_data.stock_codes)
        
        # 收益计算
        initial_cash = save_data.config.initial_cash
        cash = save_data.account.cash
        positions = save_data.account.positions
        market_value = sum(
            self._get_position_value(p) for p in positions
        )
        current_assets = cash + market_value
        total_return_pct = (current_assets - initial_cash) / initial_cash * 100 if initial_cash > 0 else 0
        
        # 日收益（从资产历史获取最后一天）
        daily_profit = 0.0
        if save_data.asset_history:
            last_day = save_data.asset_history[-1]
            if isinstance(last_day, dict):
                daily_profit = last_day.get("daily_profit", 0.0)
            else:
                daily_profit = getattr(last_day, "daily_profit", 0.0)
        
        # 交易天数
        trading_days = len(save_data.asset_history)
        
        # 连续盈利天数
        consecutive_profit_days = 0
        for day in reversed(save_data.asset_history):
            profit = day.get("daily_profit", 0) if isinstance(day, dict) else getattr(day, "daily_profit", 0)
            if profit > 0:
                consecutive_profit_days += 1
            else:
                break
        
        # 做T统计
        t_stats = save_data.t_trade_statistics
        total_t_trades = 0
        successful_t_trades = 0
        t_trade_success_rate = 0.0
        best_t_trade_profit = 0.0
        cumulative_t_trade_profit = 0.0
        
        if t_stats:
            total_t_trades = t_stats.total_trades
            successful_t_trades = t_stats.successful_trades
            t_trade_success_rate = t_stats.success_rate
            best_t_trade_profit = t_stats.best_trade_profit
            cumulative_t_trade_profit = t_stats.total_profit
        
        # 挑战统计
        challenges_passed = len([r for r in save_data.challenge_results if r.get("passed", False)])
        
        return AchievementContext(
            total_trades=total_trades,
            total_buy_trades=total_buy_trades,
            total_sell_trades=total_sell_trades,
            largest_single_trade_amount=largest_trade,
            unique_stocks_held=unique_stocks,
            total_return_pct=total_return_pct,
            daily_profit=daily_profit,
            current_total_assets=current_assets,
            initial_cash=initial_cash,
            trading_days_count=trading_days,
            consecutive_profit_days=consecutive_profit_days,
            total_t_trades=total_t_trades,
            successful_t_trades=successful_t_trades,
            t_trade_success_rate=t_trade_success_rate,
            best_t_trade_profit=best_t_trade_profit,
            cumulative_t_trade_profit=cumulative_t_trade_profit,
            challenges_passed=challenges_passed,
        )
    
    def _get_order_type(self, trade) -> str:
        """获取交易类型"""
        if isinstance(trade, dict):
            return trade.get("order_type", "")
        return getattr(trade, "order_type", "")
    
    def _get_trade_price(self, trade) -> float:
        """获取交易价格"""
        if isinstance(trade, dict):
            return trade.get("price", 0.0)
        return getattr(trade, "price", 0.0)
    
    def _get_trade_quantity(self, trade) -> int:
        """获取交易数量"""
        if isinstance(trade, dict):
            return trade.get("quantity", 0)
        return getattr(trade, "quantity", 0)
    
    def _get_position_value(self, position) -> float:
        """获取持仓市值"""
        if isinstance(position, dict):
            return position.get("quantity", 0) * position.get("current_price", 0)
        return getattr(position, "quantity", 0) * getattr(position, "current_price", 0)


# 全局服务实例
achievement_service = AchievementService()
