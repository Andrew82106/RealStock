"""
排行榜服务属性测试 - Leaderboard Service Property Tests
Property 12: Leaderboard Ordering
"""
import pytest
from hypothesis import HealthCheck, given, strategies as st, assume, settings
from unittest.mock import Mock, patch
from dataclasses import dataclass, field

from api.services.leaderboard_service import (
    LeaderboardService,
    LeaderboardType,
    LeaderboardEntry,
)
from api.services.save_service import (
    SaveData,
    SaveConfig,
    AccountState,
    GameState,
    SaveMetadata,
)


# Mock save data generator
@st.composite
def mock_save_data_strategy(draw):
    """生成模拟存档数据"""
    save_id = draw(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"))
    name = draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz "))
    initial_cash = draw(st.floats(min_value=10000, max_value=1000000))
    current_cash = draw(st.floats(min_value=0, max_value=2000000))
    
    # 生成持仓
    num_positions = draw(st.integers(min_value=0, max_value=2))
    positions = []
    for _ in range(num_positions):
        positions.append({
            "quantity": draw(st.integers(min_value=0, max_value=10000)),
            "current_price": draw(st.floats(min_value=1, max_value=100)),
        })
    
    # 生成交易历史
    num_trades = draw(st.integers(min_value=0, max_value=4))
    trade_history = []
    for _ in range(num_trades):
        trade_history.append({
            "order_type": draw(st.sampled_from(["buy", "sell"])),
            "price": draw(st.floats(min_value=1, max_value=100)),
            "quantity": draw(st.integers(min_value=100, max_value=1000)),
        })
    
    return SaveData(
        version="1.0",
        id=save_id,
        name=name,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        config=SaveConfig(initial_cash=initial_cash),
        account=AccountState(cash=current_cash, positions=positions),
        game_state=GameState(),
        stock_codes=[],
        trade_history=trade_history,
        asset_history=[],
    )


@st.composite
def mock_save_list_strategy(draw):
    """生成模拟存档列表"""
    num_saves = draw(st.integers(min_value=1, max_value=5))
    saves = []
    
    for i in range(num_saves):
        save_data = draw(mock_save_data_strategy())
        save_data.id = f"save{i}_{save_data.id}"
        saves.append(save_data)
    
    return saves


class TestLeaderboardOrdering:
    """Property 12: Leaderboard Ordering"""
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(saves=mock_save_list_strategy())
    def test_leaderboard_is_sorted_descending(self, saves: list[SaveData]):
        """排行榜按值降序排列"""
        # 创建mock服务
        mock_save_service = Mock()
        mock_save_service.list_saves.return_value = [
            SaveMetadata(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_date="",
                total_assets=0,
                stock_count=0,
            )
            for s in saves
        ]
        mock_save_service.load_save.side_effect = lambda sid: next(
            (s for s in saves if s.id == sid), None
        )
        
        service = LeaderboardService(save_service=mock_save_service)
        
        for lb_type in LeaderboardType:
            leaderboard = service.get_leaderboard(lb_type, limit=100)
            
            # 验证降序排列
            values = [entry.value for entry in leaderboard]
            assert values == sorted(values, reverse=True), f"Leaderboard {lb_type} not sorted"
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(saves=mock_save_list_strategy())
    def test_ranks_are_sequential(self, saves: list[SaveData]):
        """排名是连续的从1开始"""
        mock_save_service = Mock()
        mock_save_service.list_saves.return_value = [
            SaveMetadata(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_date="",
                total_assets=0,
                stock_count=0,
            )
            for s in saves
        ]
        mock_save_service.load_save.side_effect = lambda sid: next(
            (s for s in saves if s.id == sid), None
        )
        
        service = LeaderboardService(save_service=mock_save_service)
        
        leaderboard = service.get_leaderboard(LeaderboardType.TOTAL_ASSETS, limit=100)
        
        ranks = [entry.rank for entry in leaderboard]
        expected_ranks = list(range(1, len(leaderboard) + 1))
        assert ranks == expected_ranks
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(saves=mock_save_list_strategy())
    def test_current_save_is_marked(self, saves: list[SaveData]):
        """当前存档被正确标记"""
        assume(len(saves) > 0)
        
        mock_save_service = Mock()
        mock_save_service.list_saves.return_value = [
            SaveMetadata(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_date="",
                total_assets=0,
                stock_count=0,
            )
            for s in saves
        ]
        mock_save_service.load_save.side_effect = lambda sid: next(
            (s for s in saves if s.id == sid), None
        )
        
        service = LeaderboardService(save_service=mock_save_service)
        
        current_id = saves[0].id
        leaderboard = service.get_leaderboard(
            LeaderboardType.TOTAL_ASSETS,
            current_save_id=current_id,
            limit=100,
        )
        
        # 验证只有一个条目被标记为当前
        current_entries = [e for e in leaderboard if e.is_current]
        assert len(current_entries) == 1
        assert current_entries[0].save_id == current_id
    
    @settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(saves=mock_save_list_strategy(), limit=st.integers(min_value=1, max_value=20))
    def test_limit_is_respected(self, saves: list[SaveData], limit: int):
        """限制数量被正确应用"""
        mock_save_service = Mock()
        mock_save_service.list_saves.return_value = [
            SaveMetadata(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_date="",
                total_assets=0,
                stock_count=0,
            )
            for s in saves
        ]
        mock_save_service.load_save.side_effect = lambda sid: next(
            (s for s in saves if s.id == sid), None
        )
        
        service = LeaderboardService(save_service=mock_save_service)
        
        leaderboard = service.get_leaderboard(LeaderboardType.TOTAL_ASSETS, limit=limit)
        
        assert len(leaderboard) <= limit
        assert len(leaderboard) <= len(saves)


class TestLeaderboardCalculations:
    """排行榜计算测试"""
    
    @given(
        initial_cash=st.floats(min_value=10000, max_value=1000000),
        current_cash=st.floats(min_value=0, max_value=2000000),
    )
    def test_total_assets_calculation(self, initial_cash: float, current_cash: float):
        """总资产计算正确"""
        save_data = SaveData(
            version="1.0",
            id="test",
            name="Test",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            config=SaveConfig(initial_cash=initial_cash),
            account=AccountState(cash=current_cash, positions=[]),
            game_state=GameState(),
            stock_codes=[],
            trade_history=[],
            asset_history=[],
        )
        
        service = LeaderboardService()
        total = service._calculate_total_assets(save_data)
        
        assert total == current_cash
    
    @given(
        initial_cash=st.floats(min_value=10000, max_value=1000000),
        current_cash=st.floats(min_value=1000, max_value=2000000),
    )
    def test_total_return_calculation(self, initial_cash: float, current_cash: float):
        """总收益率计算正确"""
        save_data = SaveData(
            version="1.0",
            id="test",
            name="Test",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            config=SaveConfig(initial_cash=initial_cash),
            account=AccountState(cash=current_cash, positions=[]),
            game_state=GameState(),
            stock_codes=[],
            trade_history=[],
            asset_history=[],
        )
        
        service = LeaderboardService()
        return_pct = service._calculate_total_return(save_data)
        
        expected = (current_cash - initial_cash) / initial_cash * 100
        assert abs(return_pct - expected) < 0.01
    
    def test_trade_count_calculation(self):
        """交易次数计算正确"""
        trades = [{"order_type": "buy"} for _ in range(5)]
        
        save_data = SaveData(
            version="1.0",
            id="test",
            name="Test",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            config=SaveConfig(),
            account=AccountState(),
            game_state=GameState(),
            stock_codes=[],
            trade_history=trades,
            asset_history=[],
        )
        
        service = LeaderboardService()
        value = service._get_value_for_type(LeaderboardType.TRADE_COUNT, save_data)
        
        assert value == 5.0


class TestLeaderboardEntry:
    """排行榜条目测试"""
    
    def test_entry_to_dict(self):
        """条目转换为字典"""
        entry = LeaderboardEntry(
            rank=1,
            save_id="test",
            save_name="Test Save",
            value=100000.0,
            achievement_count=5,
            is_current=True,
        )
        
        d = entry.to_dict()
        
        assert d["rank"] == 1
        assert d["save_id"] == "test"
        assert d["save_name"] == "Test Save"
        assert d["value"] == 100000.0
        assert d["achievement_count"] == 5
        assert d["is_current"] is True


class TestLeaderboardTypes:
    """排行榜类型测试"""
    
    def test_all_types_are_strings(self):
        """所有类型都是字符串枚举"""
        for lb_type in LeaderboardType:
            assert isinstance(lb_type.value, str)
    
    def test_all_types_have_unique_values(self):
        """所有类型值唯一"""
        values = [lb_type.value for lb_type in LeaderboardType]
        assert len(values) == len(set(values))
    
    def test_get_all_leaderboards_returns_all_types(self):
        """获取所有排行榜返回所有类型"""
        mock_save_service = Mock()
        mock_save_service.list_saves.return_value = []
        
        service = LeaderboardService(save_service=mock_save_service)
        all_boards = service.get_all_leaderboards()
        
        for lb_type in LeaderboardType:
            assert lb_type.value in all_boards
