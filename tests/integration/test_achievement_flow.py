"""集成测试 - 成就系统完整流程测试

Tests:
1. 完整的成就解锁流程
2. 成就数据持久化
3. 成就进度计算和更新

Requirements: 14.1-14.5
"""

import json
import shutil
import tempfile
from datetime import datetime

import pytest

from api.services.save_service import (
    SaveService,
    SaveData,
    SaveConfig,
    AccountState,
    GameState,
    TradeRecord,
    DailySnapshot,
)
from api.services.achievement_service import AchievementService, achievement_service
from api.services.achievement_models import (
    AchievementProgress,
    AchievementContext,
    UnlockedAchievement,
    AchievementCategory,
    AchievementRarity,
)
from api.services.t_trade_models import TTradeStatistics, TTradeRecord


class TestAchievementUnlockFlow:
    """测试成就解锁完整流程"""
    
    def test_first_trade_achievement_unlock(self):
        """
        测试首次交易成就解锁流程
        
        Requirements: 14.1, 2.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            # Step 1: 创建新存档
            save_data = save_service.create_save("Achievement Test", 100000.0)
            
            # 验证初始成就进度为空
            assert save_data.achievement_progress is not None
            assert len(save_data.achievement_progress.unlocked_achievements) == 0
            
            # Step 2: 添加交易记录
            trade = TradeRecord(
                order_id="order_001",
                code="600519",
                order_type="buy",
                price=1500.0,
                quantity=100,
                fee=22.5,
                timestamp=datetime.now().isoformat(),
            )
            save_data.trade_history.append(trade)
            save_service.update_save(save_data.id, save_data)
            
            # Step 3: 构建成就上下文并检查成就
            context = achievement_svc.build_context_from_save(save_data)
            assert context.total_buy_trades == 1
            
            newly_unlocked = achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 验证首次交易成就已解锁
            assert "first_trade" in newly_unlocked
            assert save_data.achievement_progress.is_unlocked("first_trade")
            
            # Step 4: 保存并重新加载验证持久化
            save_service.update_save(save_data.id, save_data)
            loaded_save = save_service.load_save(save_data.id)
            
            assert loaded_save.achievement_progress.is_unlocked("first_trade")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_multiple_achievements_unlock_sequence(self):
        """
        测试多个成就按顺序解锁
        
        Requirements: 14.1, 2.1-2.3
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            save_data = save_service.create_save("Multi Achievement Test", 100000.0)
            
            # 添加10笔交易
            for i in range(10):
                trade = TradeRecord(
                    order_id=f"order_{i:03d}",
                    code="600519",
                    order_type="buy" if i % 2 == 0 else "sell",
                    price=1500.0 + i * 10,
                    quantity=100,
                    fee=22.5,
                    timestamp=datetime.now().isoformat(),
                )
                save_data.trade_history.append(trade)
            
            # 检查成就
            context = achievement_svc.build_context_from_save(save_data)
            newly_unlocked = achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 验证首次交易和活跃交易者成就都已解锁
            assert "first_trade" in newly_unlocked
            assert "active_trader" in newly_unlocked
            
            # 保存并验证
            save_service.update_save(save_data.id, save_data)
            loaded_save = save_service.load_save(save_data.id)
            
            assert loaded_save.achievement_progress.is_unlocked("first_trade")
            assert loaded_save.achievement_progress.is_unlocked("active_trader")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_profit_achievement_unlock(self):
        """
        测试收益类成就解锁
        
        Requirements: 14.1, 3.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            # 创建存档，初始资金10万
            save_data = save_service.create_save("Profit Test", 100000.0)
            
            # 设置账户状态为11万（10%收益）
            save_data.account = AccountState(
                cash=110000.0,
                positions=[],
            )
            
            # 检查成就
            context = achievement_svc.build_context_from_save(save_data)
            assert context.total_return_pct >= 10
            
            newly_unlocked = achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 验证盈利新手成就已解锁
            assert "profitable_beginner" in newly_unlocked
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_milestone_achievement_unlock(self):
        """
        测试里程碑成就解锁
        
        Requirements: 14.1, 4.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            save_data = save_service.create_save("Milestone Test", 100000.0)
            
            # 设置账户状态为20万
            save_data.account = AccountState(
                cash=200000.0,
                positions=[],
            )
            
            context = achievement_svc.build_context_from_save(save_data)
            newly_unlocked = achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 验证小有成就已解锁
            assert "first_milestone" in newly_unlocked
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAchievementDataPersistence:
    """测试成就数据持久化"""
    
    def test_achievement_progress_round_trip(self):
        """
        测试成就进度保存和加载的往返一致性
        
        Requirements: 14.1, 14.2, 14.5
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("Round Trip Test", 100000.0)
            
            # 手动设置成就进度
            save_data.achievement_progress = AchievementProgress(
                unlocked_achievements=[
                    UnlockedAchievement(
                        achievement_id="first_trade",
                        unlocked_at="2024-01-02T10:30:00",
                    ),
                    UnlockedAchievement(
                        achievement_id="active_trader",
                        unlocked_at="2024-01-05T14:00:00",
                    ),
                ],
                progress_map={
                    "trading_master": 50.0,
                    "profitable_beginner": 8.5,
                },
                new_achievements=[],
            )
            
            # 保存
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载
            loaded_save = save_service.load_save(save_data.id)
            
            # 验证成就进度完整保留
            assert len(loaded_save.achievement_progress.unlocked_achievements) == 2
            assert loaded_save.achievement_progress.is_unlocked("first_trade")
            assert loaded_save.achievement_progress.is_unlocked("active_trader")
            assert loaded_save.achievement_progress.get_progress("trading_master") == 50.0
            assert loaded_save.achievement_progress.get_progress("profitable_beginner") == 8.5
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_achievement_progress_with_trade_history(self):
        """
        测试成就进度与交易历史一起持久化
        
        Requirements: 14.1, 14.2
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            save_data = save_service.create_save("Trade History Test", 100000.0)
            
            # 添加交易记录
            for i in range(5):
                trade = TradeRecord(
                    order_id=f"order_{i:03d}",
                    code="600519",
                    order_type="buy",
                    price=1500.0,
                    quantity=100,
                    fee=22.5,
                    timestamp=datetime.now().isoformat(),
                )
                save_data.trade_history.append(trade)
            
            # 检查并解锁成就
            context = achievement_svc.build_context_from_save(save_data)
            achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 保存
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载
            loaded_save = save_service.load_save(save_data.id)
            
            # 验证交易历史和成就进度都保留
            assert len(loaded_save.trade_history) == 5
            assert loaded_save.achievement_progress.is_unlocked("first_trade")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_achievement_backward_compatibility(self):
        """
        测试成就数据缺失时的向后兼容性
        
        Requirements: 14.3, 14.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("Backward Compat Test", 100000.0)
            save_id = save_data.id
            
            # 直接修改文件，移除成就数据（模拟旧版本存档）
            save_path = save_service._get_save_path(save_id)
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 移除成就相关字段
            if "achievement_progress" in data:
                del data["achievement_progress"]
            if "t_trade_statistics" in data:
                del data["t_trade_statistics"]
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 重新加载 - 应该能正常加载，成就进度为空
            loaded_save = save_service.load_save(save_id)
            
            # 成就进度应该为 None 或空
            # 系统应该能够处理这种情况
            assert loaded_save is not None
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_new_save_has_empty_achievement_progress(self):
        """
        测试新存档初始化空成就进度
        
        Requirements: 14.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = save_service.create_save("New Save Test", 100000.0)
            
            # 验证新存档有空的成就进度
            assert save_data.achievement_progress is not None
            assert len(save_data.achievement_progress.unlocked_achievements) == 0
            assert len(save_data.achievement_progress.progress_map) == 0
            
            # 保存并重新加载
            loaded_save = save_service.load_save(save_data.id)
            
            assert loaded_save.achievement_progress is not None
            assert len(loaded_save.achievement_progress.unlocked_achievements) == 0
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAchievementWithTTradeStatistics:
    """测试成就系统与做T统计的集成"""
    
    def test_t_trade_achievement_unlock(self):
        """
        测试做T成就解锁
        
        Requirements: 14.1, 8.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        achievement_svc = AchievementService()
        
        try:
            save_data = save_service.create_save("T-Trade Test", 100000.0)
            
            # 设置做T统计
            save_data.t_trade_statistics = TTradeStatistics(
                total_trades=1,
                successful_trades=1,
                success_rate=100.0,
                total_profit=500.0,
                best_trade_profit=500.0,
                worst_trade_loss=0.0,
                trades=[
                    TTradeRecord(
                        id="t_001",
                        stock_code="600519",
                        sell_price=1520.0,
                        buy_price=1510.0,
                        quantity=50,
                        sell_fee=22.5,
                        buy_fee=22.5,
                        profit=500.0,
                        trade_date="2024-01-02",
                        sell_time="10:30:00",
                        buy_time="14:00:00",
                    ),
                ],
            )
            
            # 构建上下文
            context = AchievementContext(
                total_t_trades=1,
                successful_t_trades=1,
                t_trade_success_rate=100.0,
                best_t_trade_profit=500.0,
                cumulative_t_trade_profit=500.0,
            )
            
            newly_unlocked = achievement_svc.check_and_unlock_achievements(
                save_data.achievement_progress, context
            )
            
            # 验证做T新手成就已解锁
            assert "t_trade_beginner" in newly_unlocked
            
            # 保存并验证持久化
            save_service.update_save(save_data.id, save_data)
            loaded_save = save_service.load_save(save_data.id)
            
            assert loaded_save.t_trade_statistics is not None
            assert loaded_save.t_trade_statistics.total_trades == 1
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_t_trade_statistics_persistence(self):
        """
        测试做T统计数据持久化
        
        Requirements: 14.1, 14.2
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = save_service.create_save("T-Trade Persistence Test", 100000.0)
            
            # 设置做T统计
            save_data.t_trade_statistics = TTradeStatistics(
                total_trades=10,
                successful_trades=7,
                success_rate=70.0,
                total_profit=3500.0,
                best_trade_profit=1000.0,
                worst_trade_loss=-200.0,
                trades=[
                    TTradeRecord(
                        id=f"t_{i:03d}",
                        stock_code="600519",
                        sell_price=1520.0,
                        buy_price=1510.0,
                        quantity=50,
                        sell_fee=22.5,
                        buy_fee=22.5,
                        profit=500.0 if i < 7 else -200.0,
                        trade_date=f"2024-01-{i+2:02d}",
                        sell_time="10:30:00",
                        buy_time="14:00:00",
                    )
                    for i in range(10)
                ],
            )
            
            # 保存
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载
            loaded_save = save_service.load_save(save_data.id)
            
            # 验证做T统计完整保留
            assert loaded_save.t_trade_statistics is not None
            assert loaded_save.t_trade_statistics.total_trades == 10
            assert loaded_save.t_trade_statistics.successful_trades == 7
            assert loaded_save.t_trade_statistics.success_rate == 70.0
            assert loaded_save.t_trade_statistics.total_profit == 3500.0
            assert len(loaded_save.t_trade_statistics.trades) == 10
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAchievementStatistics:
    """测试成就统计功能"""
    
    def test_achievement_statistics_calculation(self):
        """
        测试成就统计计算
        
        Requirements: 14.1
        """
        achievement_svc = AchievementService()
        
        # 创建带有一些已解锁成就的进度
        progress = AchievementProgress(
            unlocked_achievements=[
                UnlockedAchievement(
                    achievement_id="first_trade",
                    unlocked_at="2024-01-02T10:30:00",
                ),
                UnlockedAchievement(
                    achievement_id="active_trader",
                    unlocked_at="2024-01-05T14:00:00",
                ),
                UnlockedAchievement(
                    achievement_id="profitable_beginner",
                    unlocked_at="2024-01-10T09:00:00",
                ),
            ],
            progress_map={},
            new_achievements=[],
        )
        
        # 计算统计
        stats = achievement_svc.calculate_statistics(progress)
        
        # 验证统计数据
        assert stats["unlocked"] == 3
        assert stats["total"] > 0
        assert 0 <= stats["percentage"] <= 100
        assert "by_category" in stats
        assert "by_rarity" in stats
        assert "recent_unlocked" in stats
        
    def test_achievement_definitions_complete(self):
        """
        测试所有成就定义完整性
        
        Requirements: 14.4
        """
        achievement_svc = AchievementService()
        definitions = achievement_svc.get_all_definitions()
        
        # 验证有成就定义
        assert len(definitions) > 0
        
        # 验证每个成就定义都有必需字段
        for definition in definitions:
            assert definition.id is not None and definition.id != ""
            assert definition.name is not None and definition.name != ""
            assert definition.description is not None
            assert definition.icon is not None
            assert definition.category is not None
            assert definition.rarity is not None
            assert definition.progress_type is not None
            assert definition.target_value >= 0
