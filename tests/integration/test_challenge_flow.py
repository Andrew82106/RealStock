"""集成测试 - 挑战模式完整流程测试

Tests:
1. 挑战创建流程
2. 挑战进行流程
3. 挑战完成流程

Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6
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
from api.services.challenge_service import ChallengeService, challenge_service
from api.services.challenge_models import (
    CHALLENGE_CONFIGS,
    CHALLENGE_INITIAL_CASH,
    get_challenge_by_id,
    get_challenges_by_difficulty,
)
from api.services.achievement_models import (
    ChallengeConfig,
    ChallengeResult,
    ChallengeProgress,
    ChallengeDifficulty,
    GameMode,
)


class TestChallengeCreation:
    """测试挑战创建流程"""
    
    def test_create_challenge_save(self):
        """
        测试创建挑战模式存档
        
        Requirements: 16.1, 16.4, 16.5
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        challenge_svc = ChallengeService()
        
        try:
            # 获取一个简单难度挑战
            challenge = get_challenge_by_id("easy_pingan")
            assert challenge is not None
            
            # 创建挑战存档
            save_data = save_service.create_save(
                name="Challenge Test",
                initial_cash=CHALLENGE_INITIAL_CASH,
                start_date=challenge.start_date,
                game_mode="challenge",
                challenge_id=challenge.id,
                challenge_config=challenge,
            )
            
            # 验证存档配置
            assert save_data.config.game_mode == "challenge"
            assert save_data.config.initial_cash == CHALLENGE_INITIAL_CASH
            assert save_data.config.challenge_id == challenge.id
            assert save_data.challenge_config is not None
            assert save_data.challenge_config.id == challenge.id
            
            # 验证初始资金为10000
            assert save_data.account.cash == CHALLENGE_INITIAL_CASH
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_challenge_save_constraints(self):
        """
        测试挑战模式存档约束
        
        Requirements: 16.4, 17.4, 17.5
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        
        # 测试初始资金必须是10000
        is_valid, error = challenge_svc.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=100000.0,  # 错误的初始资金
            stock_codes=[challenge.stock_code],
        )
        assert not is_valid
        assert "10000" in error
        
        # 测试只能有一只股票
        is_valid, error = challenge_svc.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=[challenge.stock_code, "600519"],  # 多只股票
        )
        assert not is_valid
        assert "one stock" in error
        
        # 测试股票代码必须匹配
        is_valid, error = challenge_svc.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=["600519"],  # 错误的股票代码
        )
        assert not is_valid
        assert challenge.stock_code in error
        
        # 测试正确的配置
        is_valid, error = challenge_svc.validate_challenge_save_config(
            challenge_id=challenge.id,
            initial_cash=CHALLENGE_INITIAL_CASH,
            stock_codes=[challenge.stock_code],
        )
        assert is_valid
        assert error == ""
    
    def test_challenge_difficulties_available(self):
        """
        测试不同难度的挑战可用
        
        Requirements: 16.1, 17.6
        """
        challenge_svc = ChallengeService()
        
        # 验证每个难度都有挑战
        easy_challenges = get_challenges_by_difficulty(ChallengeDifficulty.EASY)
        medium_challenges = get_challenges_by_difficulty(ChallengeDifficulty.MEDIUM)
        hard_challenges = get_challenges_by_difficulty(ChallengeDifficulty.HARD)
        
        assert len(easy_challenges) > 0
        assert len(medium_challenges) > 0
        assert len(hard_challenges) > 0
        
        # 验证目标收益率
        for challenge in easy_challenges:
            expected_return = (challenge.target_assets - challenge.initial_cash) / challenge.initial_cash * 100
            assert expected_return == 50.0  # Easy: 50%
        
        for challenge in medium_challenges:
            expected_return = (challenge.target_assets - challenge.initial_cash) / challenge.initial_cash * 100
            assert expected_return == 100.0  # Medium: 100%
        
        for challenge in hard_challenges:
            expected_return = (challenge.target_assets - challenge.initial_cash) / challenge.initial_cash * 100
            assert expected_return == 200.0  # Hard: 200%


class TestChallengeProgress:
    """测试挑战进行流程"""
    
    def test_challenge_progress_calculation(self):
        """
        测试挑战进度计算
        
        Requirements: 17.3
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        
        # 测试初始进度 (10000 -> 15000, 当前10000)
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=10000.0,
            current_date="2024-01-02",
        )
        
        assert progress.challenge_id == challenge.id
        assert progress.current_assets == 10000.0
        assert progress.target_assets == 15000.0
        assert progress.progress_pct == 0.0
        assert progress.days_remaining > 0
        
        # 测试50%进度 (10000 -> 15000, 当前12500)
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=12500.0,
            current_date="2024-02-01",
        )
        
        assert progress.progress_pct == 50.0
        
        # 测试100%进度 (达到目标)
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=15000.0,
            current_date="2024-03-01",
        )
        
        assert progress.progress_pct == 100.0
        
        # 测试超过100%进度
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=20000.0,
            current_date="2024-03-01",
        )
        
        assert progress.progress_pct == 100.0  # 应该被限制在100%
    
    def test_challenge_days_remaining(self):
        """
        测试挑战剩余天数计算
        
        Requirements: 17.3
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        # end_date: 2024-03-29
        
        # 测试开始日期
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=10000.0,
            current_date="2024-01-02",
        )
        
        # 从1月2日到3月29日
        assert progress.days_remaining > 80
        
        # 测试接近结束
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=10000.0,
            current_date="2024-03-28",
        )
        
        assert progress.days_remaining == 1
        
        # 测试结束日期
        progress = challenge_svc.calculate_progress(
            challenge=challenge,
            current_assets=10000.0,
            current_date="2024-03-29",
        )
        
        assert progress.days_remaining == 0
    
    def test_challenge_save_persistence(self):
        """
        测试挑战存档持久化
        
        Requirements: 16.5
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 获取挑战配置
            challenge = get_challenge_by_id("medium_maotai")
            
            # 创建挑战存档
            save_data = save_service.create_save(
                name="Challenge Persistence Test",
                initial_cash=CHALLENGE_INITIAL_CASH,
                start_date=challenge.start_date,
                game_mode="challenge",
                challenge_id=challenge.id,
                challenge_config=challenge,
            )
            
            # 添加股票
            save_service.add_stock_to_save(save_data.id, challenge.stock_code)
            
            # 更新账户状态
            save_data = save_service.load_save(save_data.id)
            save_data.account = AccountState(
                cash=5000.0,
                positions=[{
                    "code": challenge.stock_code,
                    "quantity": 10,
                    "cost_price": 500.0,
                    "current_price": 550.0,
                    "profit_loss": 500.0,
                    "profit_loss_pct": 10.0,
                }],
            )
            save_data.game_state = GameState(
                current_date="2024-03-01",
                playback_state="paused",
                tick_index=0,
            )
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载验证
            loaded_save = save_service.load_save(save_data.id)
            
            assert loaded_save.config.game_mode == "challenge"
            assert loaded_save.challenge_config is not None
            assert loaded_save.challenge_config.id == challenge.id
            assert loaded_save.challenge_config.difficulty == ChallengeDifficulty.MEDIUM
            assert loaded_save.account.cash == 5000.0
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestChallengeCompletion:
    """测试挑战完成流程"""
    
    def test_challenge_evaluation_passed(self):
        """
        测试挑战成功评估
        
        Requirements: 18.1, 18.2
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        
        # 评估成功的挑战 (达到目标)
        result = challenge_svc.evaluate_challenge(
            challenge=challenge,
            final_assets=15000.0,  # 达到目标
            completion_date="2024-03-29",
        )
        
        assert result.challenge_id == challenge.id
        assert result.passed is True
        assert result.final_assets == 15000.0
        assert result.target_assets == 15000.0
        assert result.return_pct == 50.0
        assert result.completion_date == "2024-03-29"
    
    def test_challenge_evaluation_failed(self):
        """
        测试挑战失败评估
        
        Requirements: 18.1, 18.3
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        
        # 评估失败的挑战 (未达到目标)
        result = challenge_svc.evaluate_challenge(
            challenge=challenge,
            final_assets=12000.0,  # 未达到目标
            completion_date="2024-03-29",
        )
        
        assert result.passed is False
        assert result.final_assets == 12000.0
        assert result.return_pct == 20.0  # (12000-10000)/10000 * 100
    
    def test_challenge_exceeded_target(self):
        """
        测试超额完成挑战
        
        Requirements: 18.2
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        # target: 15000, initial: 10000, target_profit: 5000
        
        # 测试超额50% (需要达到 10000 + 5000 * 1.5 = 17500)
        exceeded = challenge_svc.check_exceeded_target(
            challenge=challenge,
            final_assets=17500.0,
            exceed_percentage=50.0,
        )
        assert exceeded is True
        
        # 测试未超额50%
        exceeded = challenge_svc.check_exceeded_target(
            challenge=challenge,
            final_assets=16000.0,
            exceed_percentage=50.0,
        )
        assert exceeded is False
    
    def test_challenge_completion_check(self):
        """
        测试挑战是否结束检查
        
        Requirements: 18.5
        """
        challenge_svc = ChallengeService()
        
        # 获取挑战配置
        challenge = get_challenge_by_id("easy_pingan")
        # end_date: 2024-03-29
        
        # 测试未结束
        is_completed = challenge_svc.is_challenge_completed(
            current_date="2024-03-28",
            challenge=challenge,
        )
        assert is_completed is False
        
        # 测试结束日期
        is_completed = challenge_svc.is_challenge_completed(
            current_date="2024-03-29",
            challenge=challenge,
        )
        assert is_completed is True
        
        # 测试超过结束日期
        is_completed = challenge_svc.is_challenge_completed(
            current_date="2024-04-01",
            challenge=challenge,
        )
        assert is_completed is True
    
    def test_challenge_result_persistence(self):
        """
        测试挑战结果持久化
        
        Requirements: 18.4, 18.6
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        challenge_svc = ChallengeService()
        
        try:
            # 获取挑战配置
            challenge = get_challenge_by_id("easy_pingan")
            
            # 创建挑战存档
            save_data = save_service.create_save(
                name="Challenge Result Test",
                initial_cash=CHALLENGE_INITIAL_CASH,
                start_date=challenge.start_date,
                game_mode="challenge",
                challenge_id=challenge.id,
                challenge_config=challenge,
            )
            
            # 模拟挑战完成
            result = challenge_svc.evaluate_challenge(
                challenge=challenge,
                final_assets=16000.0,
                completion_date="2024-03-29",
            )
            
            # 保存挑战结果
            save_data.challenge_results.append(result.to_dict())
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载验证
            loaded_save = save_service.load_save(save_data.id)
            
            assert len(loaded_save.challenge_results) == 1
            assert loaded_save.challenge_results[0]["passed"] is True
            assert loaded_save.challenge_results[0]["final_assets"] == 16000.0
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestChallengeIntegration:
    """测试挑战模式完整集成流程"""
    
    def test_complete_challenge_flow(self):
        """
        测试完整的挑战流程：创建 -> 进行 -> 完成
        
        Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        challenge_svc = ChallengeService()
        
        try:
            # Step 1: 选择挑战
            available_challenges = challenge_svc.get_available_challenges()
            assert len(available_challenges) > 0
            
            challenge = get_challenge_by_id("easy_pingan")
            
            # Step 2: 验证配置
            is_valid, _ = challenge_svc.validate_challenge_save_config(
                challenge_id=challenge.id,
                initial_cash=CHALLENGE_INITIAL_CASH,
                stock_codes=[challenge.stock_code],
            )
            assert is_valid
            
            # Step 3: 创建挑战存档
            save_data = save_service.create_save(
                name="Complete Flow Test",
                initial_cash=CHALLENGE_INITIAL_CASH,
                start_date=challenge.start_date,
                game_mode="challenge",
                challenge_id=challenge.id,
                challenge_config=challenge,
            )
            save_service.add_stock_to_save(save_data.id, challenge.stock_code)
            
            # Step 4: 模拟交易进行
            save_data = save_service.load_save(save_data.id)
            
            # 添加交易记录
            trade = TradeRecord(
                order_id="order_001",
                code=challenge.stock_code,
                order_type="buy",
                price=10.0,
                quantity=500,
                fee=7.5,
                timestamp="2024-01-02T10:30:00",
            )
            save_data.trade_history.append(trade)
            
            # 更新账户状态 (模拟盈利)
            save_data.account = AccountState(
                cash=5000.0,
                positions=[{
                    "code": challenge.stock_code,
                    "quantity": 500,
                    "cost_price": 10.0,
                    "current_price": 22.0,  # 股价上涨
                    "profit_loss": 6000.0,
                    "profit_loss_pct": 120.0,
                }],
            )
            save_data.game_state = GameState(
                current_date="2024-03-28",
                playback_state="paused",
                tick_index=0,
            )
            save_service.update_save(save_data.id, save_data)
            
            # Step 5: 检查进度
            current_assets = 5000.0 + 500 * 22.0  # cash + market_value = 16000
            progress = challenge_svc.calculate_progress(
                challenge=challenge,
                current_assets=current_assets,
                current_date="2024-03-28",
            )
            
            assert progress.progress_pct == 100.0  # 已达到目标
            assert progress.days_remaining == 1
            
            # Step 6: 评估挑战结果
            result = challenge_svc.evaluate_challenge(
                challenge=challenge,
                final_assets=current_assets,
                completion_date="2024-03-29",
            )
            
            assert result.passed is True
            assert result.return_pct == 60.0  # (16000-10000)/10000 * 100
            
            # Step 7: 保存结果
            save_data = save_service.load_save(save_data.id)
            save_data.challenge_results.append(result.to_dict())
            save_service.update_save(save_data.id, save_data)
            
            # Step 8: 验证最终状态
            final_save = save_service.load_save(save_data.id)
            
            assert final_save.config.game_mode == "challenge"
            assert len(final_save.challenge_results) == 1
            assert final_save.challenge_results[0]["passed"] is True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_multiple_challenge_attempts(self):
        """
        测试多次挑战尝试
        
        Requirements: 18.6
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        challenge_svc = ChallengeService()
        
        try:
            # 创建存档
            save_data = save_service.create_save(
                name="Multiple Attempts Test",
                initial_cash=CHALLENGE_INITIAL_CASH,
                game_mode="challenge",
            )
            
            # 模拟多次挑战结果
            challenges = [
                ("easy_pingan", 16000.0, True),   # 成功
                ("easy_gree", 12000.0, False),    # 失败
                ("medium_maotai", 22000.0, True), # 成功
            ]
            
            for challenge_id, final_assets, expected_passed in challenges:
                challenge = get_challenge_by_id(challenge_id)
                result = challenge_svc.evaluate_challenge(
                    challenge=challenge,
                    final_assets=final_assets,
                    completion_date="2024-12-31",
                )
                
                assert result.passed == expected_passed
                save_data.challenge_results.append(result.to_dict())
            
            save_service.update_save(save_data.id, save_data)
            
            # 验证挑战历史
            loaded_save = save_service.load_save(save_data.id)
            
            assert len(loaded_save.challenge_results) == 3
            
            passed_count = sum(1 for r in loaded_save.challenge_results if r["passed"])
            assert passed_count == 2
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestChallengeConfigValidation:
    """测试挑战配置验证"""
    
    def test_all_challenges_have_required_fields(self):
        """
        测试所有挑战配置都有必需字段
        
        Requirements: 16.1, 17.1, 17.2
        """
        for challenge in CHALLENGE_CONFIGS:
            assert challenge.id is not None and challenge.id != ""
            assert challenge.name is not None and challenge.name != ""
            assert challenge.difficulty is not None
            assert challenge.stock_code is not None and challenge.stock_code != ""
            assert challenge.start_date is not None
            assert challenge.end_date is not None
            assert challenge.initial_cash == CHALLENGE_INITIAL_CASH
            assert challenge.target_assets > challenge.initial_cash
            assert challenge.description is not None
    
    def test_challenge_dates_valid(self):
        """
        测试挑战日期有效
        
        Requirements: 17.1
        """
        from datetime import datetime
        
        for challenge in CHALLENGE_CONFIGS:
            start = datetime.strptime(challenge.start_date, "%Y-%m-%d")
            end = datetime.strptime(challenge.end_date, "%Y-%m-%d")
            
            # 结束日期必须在开始日期之后
            assert end > start
    
    def test_challenge_target_matches_difficulty(self):
        """
        测试挑战目标与难度匹配
        
        Requirements: 17.2, 17.6
        """
        for challenge in CHALLENGE_CONFIGS:
            expected_return = (challenge.target_assets - challenge.initial_cash) / challenge.initial_cash * 100
            
            if challenge.difficulty == ChallengeDifficulty.EASY:
                assert expected_return == 50.0
            elif challenge.difficulty == ChallengeDifficulty.MEDIUM:
                assert expected_return == 100.0
            elif challenge.difficulty == ChallengeDifficulty.HARD:
                assert expected_return == 200.0
