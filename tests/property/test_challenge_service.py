"""
挑战模式服务属性测试 - Challenge Service Property Tests
Property 10: Challenge Mode Constraints
Property 11: Challenge Evaluation Correctness
"""
import pytest
from hypothesis import given, strategies as st, assume, settings

from api.services.achievement_models import (
    ChallengeConfig,
    ChallengeDifficulty,
)
from api.services.challenge_models import (
    CHALLENGE_CONFIGS,
    CHALLENGE_INITIAL_CASH,
    get_all_challenges,
    get_challenge_by_id,
)
from api.services.challenge_service import ChallengeService, challenge_service


# Strategies
@st.composite
def challenge_config_strategy(draw):
    """生成有效的挑战配置"""
    challenges = get_all_challenges()
    return draw(st.sampled_from(challenges))


@st.composite
def valid_date_strategy(draw):
    """生成有效日期字符串"""
    year = draw(st.integers(min_value=2020, max_value=2025))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    return f"{year:04d}-{month:02d}-{day:02d}"


class TestChallengeConstraints:
    """Property 10: Challenge Mode Constraints"""
    
    @given(challenge=challenge_config_strategy())
    def test_challenge_initial_cash_is_fixed(self, challenge: ChallengeConfig):
        """挑战模式初始资金必须是10000"""
        assert challenge.initial_cash == CHALLENGE_INITIAL_CASH
        assert challenge.initial_cash == 10000.0
    
    @given(challenge=challenge_config_strategy())
    def test_challenge_has_single_stock(self, challenge: ChallengeConfig):
        """挑战模式只能有一只股票"""
        assert challenge.stock_code is not None
        assert len(challenge.stock_code) > 0
    
    @given(challenge=challenge_config_strategy())
    def test_challenge_has_valid_target(self, challenge: ChallengeConfig):
        """挑战目标资产必须大于初始资金"""
        assert challenge.target_assets > challenge.initial_cash
    
    @given(challenge=challenge_config_strategy())
    def test_challenge_has_valid_dates(self, challenge: ChallengeConfig):
        """挑战必须有有效的开始和结束日期"""
        assert challenge.start_date is not None
        assert challenge.end_date is not None
        assert challenge.start_date < challenge.end_date
    
    @given(
        challenge=challenge_config_strategy(),
        wrong_cash=st.floats(min_value=1000, max_value=100000).filter(lambda x: x != 10000.0)
    )
    def test_validate_rejects_wrong_initial_cash(
        self, challenge: ChallengeConfig, wrong_cash: float
    ):
        """验证拒绝错误的初始资金"""
        service = ChallengeService()
        is_valid, error = service.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=wrong_cash,
            stock_codes=[challenge.stock_code],
        )
        assert not is_valid
        assert "initial cash" in error.lower() or "10000" in error
    
    @given(challenge=challenge_config_strategy())
    def test_validate_rejects_multiple_stocks(self, challenge: ChallengeConfig):
        """验证拒绝多只股票"""
        service = ChallengeService()
        is_valid, error = service.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=[challenge.stock_code, "000002"],
        )
        assert not is_valid
        assert "one stock" in error.lower() or "only" in error.lower()
    
    @given(challenge=challenge_config_strategy())
    def test_validate_rejects_wrong_stock(self, challenge: ChallengeConfig):
        """验证拒绝错误的股票代码"""
        service = ChallengeService()
        wrong_stock = "999999"  # 不存在的股票
        assume(wrong_stock != challenge.stock_code)
        
        is_valid, error = service.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=[wrong_stock],
        )
        assert not is_valid
        assert "stock" in error.lower()
    
    @given(challenge=challenge_config_strategy())
    def test_validate_accepts_correct_config(self, challenge: ChallengeConfig):
        """验证接受正确的配置"""
        service = ChallengeService()
        is_valid, error = service.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=[challenge.stock_code],
        )
        assert is_valid
        assert error == ""


class TestChallengeEvaluation:
    """Property 11: Challenge Evaluation Correctness"""
    
    @given(
        challenge=challenge_config_strategy(),
        final_assets=st.floats(min_value=5000, max_value=50000)
    )
    def test_evaluation_pass_when_target_reached(
        self, challenge: ChallengeConfig, final_assets: float
    ):
        """当最终资产达到目标时，挑战通过"""
        service = ChallengeService()
        
        # 确保资产达到目标
        final_assets = max(final_assets, challenge.target_assets)
        
        result = service.evaluate_challenge(
            challenge=challenge,
            final_assets=final_assets,
            completion_date="2024-12-31",
        )
        
        assert result.passed is True
        assert result.final_assets == final_assets
        assert result.target_assets == challenge.target_assets
    
    @given(
        challenge=challenge_config_strategy(),
        final_assets=st.floats(min_value=1000, max_value=9999)
    )
    def test_evaluation_fail_when_target_not_reached(
        self, challenge: ChallengeConfig, final_assets: float
    ):
        """当最终资产未达到目标时，挑战失败"""
        service = ChallengeService()
        
        # 确保资产低于目标
        assume(final_assets < challenge.target_assets)
        
        result = service.evaluate_challenge(
            challenge=challenge,
            final_assets=final_assets,
            completion_date="2024-12-31",
        )
        
        assert result.passed is False
        assert result.final_assets == final_assets
    
    @given(
        challenge=challenge_config_strategy(),
        final_assets=st.floats(min_value=5000, max_value=50000)
    )
    def test_return_percentage_calculation(
        self, challenge: ChallengeConfig, final_assets: float
    ):
        """收益率计算正确"""
        service = ChallengeService()
        
        result = service.evaluate_challenge(
            challenge=challenge,
            final_assets=final_assets,
            completion_date="2024-12-31",
        )
        
        expected_return = (final_assets - challenge.initial_cash) / challenge.initial_cash * 100
        assert abs(result.return_pct - expected_return) < 0.01
    
    @given(
        challenge=challenge_config_strategy(),
        current_assets=st.floats(min_value=5000, max_value=50000)
    )
    def test_progress_percentage_bounds(
        self, challenge: ChallengeConfig, current_assets: float
    ):
        """进度百分比在0-100之间"""
        service = ChallengeService()
        
        progress = service.calculate_progress(
            challenge=challenge,
            current_assets=current_assets,
            current_date="2024-06-15",
        )
        
        assert 0.0 <= progress.progress_pct <= 100.0
    
    @given(challenge=challenge_config_strategy())
    def test_progress_zero_at_initial(self, challenge: ChallengeConfig):
        """初始资产时进度为0"""
        service = ChallengeService()
        
        progress = service.calculate_progress(
            challenge=challenge,
            current_assets=challenge.initial_cash,
            current_date=challenge.start_date,
        )
        
        assert progress.progress_pct == 0.0
    
    @given(challenge=challenge_config_strategy())
    def test_progress_hundred_at_target(self, challenge: ChallengeConfig):
        """达到目标时进度为100"""
        service = ChallengeService()
        
        progress = service.calculate_progress(
            challenge=challenge,
            current_assets=challenge.target_assets,
            current_date=challenge.start_date,
        )
        
        assert progress.progress_pct == 100.0
    
    @given(challenge=challenge_config_strategy())
    def test_days_remaining_calculation(self, challenge: ChallengeConfig):
        """剩余天数计算正确"""
        service = ChallengeService()
        
        # 在开始日期
        progress = service.calculate_progress(
            challenge=challenge,
            current_assets=challenge.initial_cash,
            current_date=challenge.start_date,
        )
        
        assert progress.days_remaining >= 0
        
        # 在结束日期
        progress_end = service.calculate_progress(
            challenge=challenge,
            current_assets=challenge.initial_cash,
            current_date=challenge.end_date,
        )
        
        assert progress_end.days_remaining == 0
    
    @given(challenge=challenge_config_strategy())
    def test_challenge_completion_detection(self, challenge: ChallengeConfig):
        """挑战完成检测正确"""
        service = ChallengeService()
        
        # 结束日期前未完成
        assert not service.is_challenge_completed(challenge.start_date, challenge)
        
        # 结束日期时完成
        assert service.is_challenge_completed(challenge.end_date, challenge)


class TestChallengeServiceIntegrity:
    """挑战服务完整性测试"""
    
    def test_all_challenges_have_unique_ids(self):
        """所有挑战ID唯一"""
        challenges = get_all_challenges()
        ids = [c.id for c in challenges]
        assert len(ids) == len(set(ids))
    
    def test_all_difficulties_have_challenges(self):
        """每个难度都有挑战"""
        service = ChallengeService()
        
        for difficulty in ChallengeDifficulty:
            challenges = service.get_challenges_by_difficulty(difficulty)
            assert len(challenges) > 0, f"No challenges for {difficulty}"
    
    def test_get_challenge_by_id_returns_correct(self):
        """通过ID获取挑战返回正确结果"""
        challenges = get_all_challenges()
        
        for challenge in challenges:
            retrieved = get_challenge_by_id(challenge.id)
            assert retrieved is not None
            assert retrieved.id == challenge.id
            assert retrieved.difficulty == challenge.difficulty
    
    def test_get_nonexistent_challenge_returns_none(self):
        """获取不存在的挑战返回None"""
        result = get_challenge_by_id("nonexistent_challenge_id")
        assert result is None
    
    def test_validate_nonexistent_challenge_fails(self):
        """验证不存在的挑战失败"""
        service = ChallengeService()
        is_valid, error = service.validate_challenge_save_config(
            challenge_id="nonexistent",
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=["000001"],
        )
        assert not is_valid
        assert "not found" in error.lower()
