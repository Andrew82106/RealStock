"""
成就数据模型属性测试
Property 1: Achievement Data Round-Trip Consistency
Property 2: Achievement Definition Completeness
Validates: Requirements 1.1, 1.2, 1.3, 1.6
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.services.achievement_models import (
    AchievementRarity,
    AchievementCategory,
    ProgressType,
    GameMode,
    ChallengeDifficulty,
    AchievementDefinition,
    UnlockedAchievement,
    AchievementProgress,
    ChallengeConfig,
    ChallengeResult,
)


# ============ Strategies ============

@st.composite
def achievement_definition_strategy(draw):
    """生成随机成就定义"""
    return AchievementDefinition(
        id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'))),
        name=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=0, max_size=500)),
        icon=draw(st.text(min_size=1, max_size=50)),
        category=draw(st.sampled_from(list(AchievementCategory))),
        rarity=draw(st.sampled_from(list(AchievementRarity))),
        progress_type=draw(st.sampled_from(list(ProgressType))),
        target_value=draw(st.floats(min_value=0, max_value=1e10, allow_nan=False, allow_infinity=False)),
    )


@st.composite
def unlocked_achievement_strategy(draw):
    """生成随机已解锁成就"""
    return UnlockedAchievement(
        achievement_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'))),
        unlocked_at=draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31))).isoformat(),
    )


@st.composite
def achievement_progress_strategy(draw):
    """生成随机成就进度"""
    unlocked = draw(st.lists(unlocked_achievement_strategy(), min_size=0, max_size=20))
    progress_keys = draw(st.lists(
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-')),
        min_size=0, max_size=20
    ))
    progress_values = draw(st.lists(
        st.floats(min_value=0, max_value=1e10, allow_nan=False, allow_infinity=False),
        min_size=len(progress_keys), max_size=len(progress_keys)
    ))
    progress_map = dict(zip(progress_keys, progress_values))
    new_achievements = draw(st.lists(
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-')),
        min_size=0, max_size=5
    ))
    
    return AchievementProgress(
        unlocked_achievements=unlocked,
        progress_map=progress_map,
        new_achievements=new_achievements,
    )


@st.composite
def challenge_config_strategy(draw):
    """生成随机挑战配置"""
    return ChallengeConfig(
        id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'))),
        name=draw(st.text(min_size=1, max_size=100)),
        difficulty=draw(st.sampled_from(list(ChallengeDifficulty))),
        stock_code=draw(st.text(min_size=6, max_size=6, alphabet='0123456789')),
        stock_name=draw(st.text(min_size=0, max_size=50)),
        start_date=draw(st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())).isoformat(),
        end_date=draw(st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())).isoformat(),
        initial_cash=10000.0,  # 固定值
        target_assets=draw(st.floats(min_value=10000, max_value=100000, allow_nan=False, allow_infinity=False)),
        description=draw(st.text(min_size=0, max_size=500)),
    )


@st.composite
def challenge_result_strategy(draw):
    """生成随机挑战结果"""
    target = draw(st.floats(min_value=10000, max_value=100000, allow_nan=False, allow_infinity=False))
    final = draw(st.floats(min_value=0, max_value=200000, allow_nan=False, allow_infinity=False))
    return ChallengeResult(
        challenge_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'))),
        passed=final >= target,
        final_assets=final,
        target_assets=target,
        return_pct=(final - 10000) / 10000 * 100 if final > 0 else 0,
        completion_date=draw(st.dates(min_value=datetime(2020, 1, 1).date(), max_value=datetime(2025, 12, 31).date())).isoformat(),
    )


# ============ Property Tests ============

class TestAchievementDefinitionRoundTrip:
    """
    Property 1 (partial): Achievement Definition Round-Trip Consistency
    For any valid AchievementDefinition, serializing to dict then deserializing
    SHALL produce an equivalent object.
    """
    
    @given(achievement_definition_strategy())
    @settings(max_examples=100)
    def test_round_trip(self, definition: AchievementDefinition):
        """Feature: achievement-system, Property 1: Achievement Data Round-Trip Consistency"""
        # Serialize
        data = definition.to_dict()
        
        # Deserialize
        restored = AchievementDefinition.from_dict(data)
        
        # Verify equivalence
        assert restored.id == definition.id
        assert restored.name == definition.name
        assert restored.description == definition.description
        assert restored.icon == definition.icon
        assert restored.category == definition.category
        assert restored.rarity == definition.rarity
        assert restored.progress_type == definition.progress_type
        assert restored.target_value == definition.target_value


class TestAchievementProgressRoundTrip:
    """
    Property 1 (partial): Achievement Progress Round-Trip Consistency
    For any valid AchievementProgress, serializing to dict then deserializing
    SHALL produce an equivalent object.
    """
    
    @given(achievement_progress_strategy())
    @settings(max_examples=100)
    def test_round_trip(self, progress: AchievementProgress):
        """Feature: achievement-system, Property 1: Achievement Data Round-Trip Consistency"""
        # Serialize
        data = progress.to_dict()
        
        # Deserialize
        restored = AchievementProgress.from_dict(data)
        
        # Verify equivalence
        assert len(restored.unlocked_achievements) == len(progress.unlocked_achievements)
        for orig, rest in zip(progress.unlocked_achievements, restored.unlocked_achievements):
            assert rest.achievement_id == orig.achievement_id
            assert rest.unlocked_at == orig.unlocked_at
        
        assert restored.progress_map == progress.progress_map
        assert restored.new_achievements == progress.new_achievements


class TestChallengeConfigRoundTrip:
    """
    Property 1 (partial): Challenge Config Round-Trip Consistency
    """
    
    @given(challenge_config_strategy())
    @settings(max_examples=100)
    def test_round_trip(self, config: ChallengeConfig):
        """Feature: achievement-system, Property 1: Achievement Data Round-Trip Consistency"""
        # Serialize
        data = config.to_dict()
        
        # Deserialize
        restored = ChallengeConfig.from_dict(data)
        
        # Verify equivalence
        assert restored.id == config.id
        assert restored.name == config.name
        assert restored.difficulty == config.difficulty
        assert restored.stock_code == config.stock_code
        assert restored.start_date == config.start_date
        assert restored.end_date == config.end_date
        assert restored.initial_cash == config.initial_cash
        assert restored.target_assets == config.target_assets
        assert restored.description == config.description


class TestChallengeResultRoundTrip:
    """
    Property 1 (partial): Challenge Result Round-Trip Consistency
    """
    
    @given(challenge_result_strategy())
    @settings(max_examples=100)
    def test_round_trip(self, result: ChallengeResult):
        """Feature: achievement-system, Property 1: Achievement Data Round-Trip Consistency"""
        # Serialize
        data = result.to_dict()
        
        # Deserialize
        restored = ChallengeResult.from_dict(data)
        
        # Verify equivalence
        assert restored.challenge_id == result.challenge_id
        assert restored.passed == result.passed
        assert restored.final_assets == result.final_assets
        assert restored.target_assets == result.target_assets
        assert restored.return_pct == result.return_pct
        assert restored.completion_date == result.completion_date


class TestAchievementDefinitionCompleteness:
    """
    Property 2: Achievement Definition Completeness
    For any achievement definition, it SHALL have all required fields with valid values.
    """
    
    @given(achievement_definition_strategy())
    @settings(max_examples=100)
    def test_all_fields_present(self, definition: AchievementDefinition):
        """Feature: achievement-system, Property 2: Achievement Definition Completeness"""
        # All required fields must be present and non-empty for strings
        assert definition.id is not None and len(definition.id) > 0
        assert definition.name is not None
        assert definition.description is not None
        assert definition.icon is not None and len(definition.icon) > 0
        
        # Category must be valid enum value
        assert definition.category in AchievementCategory
        
        # Rarity must be valid enum value (one of 4 levels)
        assert definition.rarity in AchievementRarity
        valid_rarities = {AchievementRarity.COMMON, AchievementRarity.RARE, 
                         AchievementRarity.EPIC, AchievementRarity.LEGENDARY}
        assert definition.rarity in valid_rarities
        
        # Progress type must be valid enum value
        assert definition.progress_type in ProgressType
        
        # Target value must be non-negative
        assert definition.target_value >= 0
    
    def test_rarity_has_four_levels(self):
        """Verify that exactly 4 rarity levels exist"""
        assert len(AchievementRarity) == 4
        assert AchievementRarity.COMMON in AchievementRarity
        assert AchievementRarity.RARE in AchievementRarity
        assert AchievementRarity.EPIC in AchievementRarity
        assert AchievementRarity.LEGENDARY in AchievementRarity
    
    def test_category_has_required_types(self):
        """Verify that at least 6 categories exist"""
        assert len(AchievementCategory) >= 6
        required_categories = {
            AchievementCategory.TRADING,
            AchievementCategory.PROFIT,
            AchievementCategory.MILESTONE,
            AchievementCategory.STREAK,
            AchievementCategory.T_TRADE,
            AchievementCategory.SPECIAL,
        }
        for cat in required_categories:
            assert cat in AchievementCategory


class TestAchievementProgressOperations:
    """测试成就进度操作"""
    
    def test_unlock_new_achievement(self):
        """测试解锁新成就"""
        progress = AchievementProgress()
        
        # 解锁新成就应返回 True
        result = progress.unlock("test_achievement")
        assert result is True
        assert progress.is_unlocked("test_achievement")
        assert "test_achievement" in progress.new_achievements
    
    def test_unlock_existing_achievement(self):
        """测试重复解锁成就"""
        progress = AchievementProgress()
        progress.unlock("test_achievement")
        
        # 重复解锁应返回 False
        result = progress.unlock("test_achievement")
        assert result is False
    
    def test_update_progress(self):
        """测试更新进度"""
        progress = AchievementProgress()
        progress.update_progress("test_achievement", 50.0)
        
        assert progress.get_progress("test_achievement") == 50.0
        assert progress.get_progress("nonexistent") == 0.0
    
    def test_clear_new_achievements(self):
        """测试清除新成就列表"""
        progress = AchievementProgress()
        progress.unlock("achievement1")
        progress.unlock("achievement2")
        
        new_list = progress.clear_new_achievements()
        
        assert len(new_list) == 2
        assert "achievement1" in new_list
        assert "achievement2" in new_list
        assert len(progress.new_achievements) == 0


class TestGameModeEnum:
    """测试游戏模式枚举"""
    
    def test_game_modes_exist(self):
        """验证游戏模式存在"""
        assert GameMode.FREE.value == "free"
        assert GameMode.CHALLENGE.value == "challenge"
        assert len(GameMode) == 2


class TestChallengeDifficultyEnum:
    """测试挑战难度枚举"""
    
    def test_difficulties_exist(self):
        """验证挑战难度存在"""
        assert ChallengeDifficulty.EASY.value == "easy"
        assert ChallengeDifficulty.MEDIUM.value == "medium"
        assert ChallengeDifficulty.HARD.value == "hard"
        assert len(ChallengeDifficulty) == 3
