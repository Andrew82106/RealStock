"""
成就服务属性测试
Property 3: Trade Count Achievement Thresholds
Property 4: Profit Achievement Thresholds
Property 5: Milestone Achievement Thresholds
Property 6: Streak Detection Correctness
Property 13: New Save Achievement Initialization
Validates: Requirements 1.4, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.6
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.services.achievement_models import (
    AchievementProgress,
    AchievementContext,
)
from api.services.achievement_service import AchievementService


# ============ Property Tests ============

class TestNewSaveAchievementInitialization:
    """
    Property 13: New Save Achievement Initialization
    For any newly created save, the achievement progress SHALL be initialized
    with zero unlocked achievements and empty progress map.
    """
    
    def test_empty_progress_initialization(self):
        """Feature: achievement-system, Property 13: New Save Achievement Initialization"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        assert len(progress.unlocked_achievements) == 0
        assert len(progress.progress_map) == 0
        assert len(progress.new_achievements) == 0


class TestTradeCountAchievementThresholds:
    """
    Property 3: Trade Count Achievement Thresholds
    For any trade history with N completed trades, the Achievement_System SHALL
    unlock exactly the trade count achievements whose thresholds are ≤ N.
    """
    
    @given(st.integers(min_value=0, max_value=200))
    @settings(max_examples=100)
    def test_trade_count_thresholds(self, total_trades: int):
        """Feature: achievement-system, Property 3: Trade Count Achievement Thresholds"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(
            total_trades=total_trades,
            total_buy_trades=total_trades // 2 + 1 if total_trades > 0 else 0,
        )
        
        service.check_and_unlock_achievements(progress, context)
        
        # 验证阈值逻辑
        # first_trade: 需要至少1次买入
        if context.total_buy_trades >= 1:
            assert progress.is_unlocked("first_trade"), f"first_trade should be unlocked with {context.total_buy_trades} buy trades"
        else:
            assert not progress.is_unlocked("first_trade")
        
        # active_trader: 10笔交易
        if total_trades >= 10:
            assert progress.is_unlocked("active_trader"), f"active_trader should be unlocked with {total_trades} trades"
        else:
            assert not progress.is_unlocked("active_trader")
        
        # trading_master: 100笔交易
        if total_trades >= 100:
            assert progress.is_unlocked("trading_master"), f"trading_master should be unlocked with {total_trades} trades"
        else:
            assert not progress.is_unlocked("trading_master")
    
    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=100)
    def test_diversified_portfolio_threshold(self, unique_stocks: int):
        """测试分散投资成就阈值"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(unique_stocks_held=unique_stocks)
        service.check_and_unlock_achievements(progress, context)
        
        if unique_stocks >= 5:
            assert progress.is_unlocked("diversified_portfolio")
        else:
            assert not progress.is_unlocked("diversified_portfolio")
    
    @given(st.floats(min_value=0, max_value=500000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_big_spender_threshold(self, trade_amount: float):
        """测试大手笔成就阈值"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(largest_single_trade_amount=trade_amount)
        service.check_and_unlock_achievements(progress, context)
        
        if trade_amount >= 100000:
            assert progress.is_unlocked("big_spender")
        else:
            assert not progress.is_unlocked("big_spender")


class TestProfitAchievementThresholds:
    """
    Property 4: Profit Achievement Thresholds
    For any account state with total return R%, the Achievement_System SHALL
    unlock exactly the profit achievements whose thresholds are ≤ R.
    """
    
    @given(st.floats(min_value=-50, max_value=600, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_return_percentage_thresholds(self, return_pct: float):
        """Feature: achievement-system, Property 4: Profit Achievement Thresholds"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(total_return_pct=return_pct)
        service.check_and_unlock_achievements(progress, context)
        
        # profitable_beginner: 10%
        if return_pct >= 10:
            assert progress.is_unlocked("profitable_beginner")
        else:
            assert not progress.is_unlocked("profitable_beginner")
        
        # skilled_investor: 50%
        if return_pct >= 50:
            assert progress.is_unlocked("skilled_investor")
        else:
            assert not progress.is_unlocked("skilled_investor")
        
        # double_your_money: 100%
        if return_pct >= 100:
            assert progress.is_unlocked("double_your_money")
        else:
            assert not progress.is_unlocked("double_your_money")
        
        # trading_legend: 500%
        if return_pct >= 500:
            assert progress.is_unlocked("trading_legend")
        else:
            assert not progress.is_unlocked("trading_legend")
    
    @given(st.floats(min_value=-10000, max_value=200000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_daily_profit_thresholds(self, daily_profit: float):
        """测试日盈利成就阈值"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(daily_profit=daily_profit)
        service.check_and_unlock_achievements(progress, context)
        
        # daily_winner: 10000
        if daily_profit >= 10000:
            assert progress.is_unlocked("daily_winner")
        else:
            assert not progress.is_unlocked("daily_winner")
        
        # jackpot_day: 100000
        if daily_profit >= 100000:
            assert progress.is_unlocked("jackpot_day")
        else:
            assert not progress.is_unlocked("jackpot_day")


class TestMilestoneAchievementThresholds:
    """
    Property 5: Milestone Achievement Thresholds
    For any account with total assets A, the Achievement_System SHALL
    unlock exactly the milestone achievements whose asset thresholds are ≤ A.
    """
    
    @given(st.floats(min_value=0, max_value=2000000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_asset_milestone_thresholds(self, total_assets: float):
        """Feature: achievement-system, Property 5: Milestone Achievement Thresholds"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(current_total_assets=total_assets)
        service.check_and_unlock_achievements(progress, context)
        
        # first_milestone: 200000
        if total_assets >= 200000:
            assert progress.is_unlocked("first_milestone")
        else:
            assert not progress.is_unlocked("first_milestone")
        
        # half_millionaire: 500000
        if total_assets >= 500000:
            assert progress.is_unlocked("half_millionaire")
        else:
            assert not progress.is_unlocked("half_millionaire")
        
        # millionaire: 1000000
        if total_assets >= 1000000:
            assert progress.is_unlocked("millionaire")
        else:
            assert not progress.is_unlocked("millionaire")
    
    @given(st.integers(min_value=0, max_value=300))
    @settings(max_examples=100)
    def test_trading_days_thresholds(self, trading_days: int):
        """测试交易日数成就阈值"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(trading_days_count=trading_days)
        service.check_and_unlock_achievements(progress, context)
        
        # monthly_trader: 30
        if trading_days >= 30:
            assert progress.is_unlocked("monthly_trader")
        else:
            assert not progress.is_unlocked("monthly_trader")
        
        # annual_veteran: 250
        if trading_days >= 250:
            assert progress.is_unlocked("annual_veteran")
        else:
            assert not progress.is_unlocked("annual_veteran")


class TestStreakDetectionCorrectness:
    """
    Property 6: Streak Detection Correctness
    For any sequence of daily returns, the streak counter SHALL correctly
    identify consecutive sequences and unlock streak achievements at thresholds.
    """
    
    @given(st.integers(min_value=0, max_value=50))
    @settings(max_examples=100)
    def test_consecutive_profit_days_thresholds(self, consecutive_days: int):
        """Feature: achievement-system, Property 6: Streak Detection Correctness"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(consecutive_profit_days=consecutive_days)
        service.check_and_unlock_achievements(progress, context)
        
        # winning_streak: 3
        if consecutive_days >= 3:
            assert progress.is_unlocked("winning_streak")
        else:
            assert not progress.is_unlocked("winning_streak")
        
        # hot_hand: 7
        if consecutive_days >= 7:
            assert progress.is_unlocked("hot_hand")
        else:
            assert not progress.is_unlocked("hot_hand")
        
        # unstoppable: 30
        if consecutive_days >= 30:
            assert progress.is_unlocked("unstoppable")
        else:
            assert not progress.is_unlocked("unstoppable")
    
    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=100)
    def test_consecutive_trading_days_threshold(self, consecutive_days: int):
        """测试连续交易日成就阈值"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(consecutive_trading_days=consecutive_days)
        service.check_and_unlock_achievements(progress, context)
        
        # dedicated_trader: 5
        if consecutive_days >= 5:
            assert progress.is_unlocked("dedicated_trader")
        else:
            assert not progress.is_unlocked("dedicated_trader")


class TestAchievementProgressTracking:
    """测试成就进度追踪"""
    
    def test_progress_updates_correctly(self):
        """测试进度值正确更新"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        # 设置一些进度
        context = AchievementContext(
            total_trades=5,
            total_return_pct=8,
            current_total_assets=150000,
        )
        
        service.check_and_unlock_achievements(progress, context)
        
        # 验证进度值被记录
        assert progress.get_progress("active_trader") == 5
        assert progress.get_progress("profitable_beginner") == 8
        assert progress.get_progress("first_milestone") == 150000
    
    def test_achievements_not_unlocked_twice(self):
        """测试成就不会重复解锁"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        context = AchievementContext(total_trades=15, total_buy_trades=8)
        
        # 第一次检查
        newly_unlocked_1 = service.check_and_unlock_achievements(progress, context)
        assert "active_trader" in newly_unlocked_1
        
        # 第二次检查 - 不应该再次解锁
        newly_unlocked_2 = service.check_and_unlock_achievements(progress, context)
        assert "active_trader" not in newly_unlocked_2


class TestAchievementStatistics:
    """测试成就统计"""
    
    def test_statistics_calculation(self):
        """测试统计计算"""
        service = AchievementService()
        progress = service.create_empty_progress()
        
        # 解锁一些成就
        context = AchievementContext(
            total_trades=15,
            total_buy_trades=8,
            total_return_pct=55,
            current_total_assets=250000,
        )
        service.check_and_unlock_achievements(progress, context)
        
        stats = service.calculate_statistics(progress)
        
        assert stats["total"] > 0
        assert stats["unlocked"] > 0
        assert stats["percentage"] > 0
        assert "by_category" in stats
        assert "by_rarity" in stats
        assert "recent_unlocked" in stats
        assert "rarest_unlocked" in stats
