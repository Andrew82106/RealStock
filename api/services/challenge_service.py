"""
挑战模式服务 - Challenge Mode Service
Requirements: 16.3, 16.4, 17.3, 17.4, 17.5, 18.1-18.6
"""
from datetime import datetime, date
from typing import Optional

from api.services.achievement_models import (
    ChallengeConfig,
    ChallengeResult,
    ChallengeProgress,
    ChallengeDifficulty,
    GameMode,
)
from api.services.challenge_models import (
    CHALLENGE_CONFIGS,
    CHALLENGE_MAP,
    CHALLENGE_INITIAL_CASH,
    get_all_challenges,
    get_challenge_by_id,
    get_challenges_by_difficulty,
)


class ChallengeService:
    """挑战模式服务"""
    
    def __init__(self):
        self.challenges = CHALLENGE_CONFIGS
        self.challenge_map = CHALLENGE_MAP
    
    def get_available_challenges(self) -> list[ChallengeConfig]:
        """获取所有可用的挑战配置"""
        return get_all_challenges()
    
    def get_challenge(self, challenge_id: str) -> Optional[ChallengeConfig]:
        """获取单个挑战配置"""
        return get_challenge_by_id(challenge_id)
    
    def get_challenges_by_difficulty(self, difficulty: ChallengeDifficulty) -> list[ChallengeConfig]:
        """根据难度获取挑战列表"""
        return get_challenges_by_difficulty(difficulty)
    
    def validate_challenge_save_config(
        self, 
        challenge_id: str,
        initial_cash: float,
        stock_codes: list[str],
    ) -> tuple[bool, str]:
        """
        验证挑战模式存档配置
        
        Returns:
            (is_valid, error_message)
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return False, f"Challenge '{challenge_id}' not found"
        
        # 验证初始资金必须是10000
        if initial_cash != CHALLENGE_INITIAL_CASH:
            return False, f"Challenge mode requires initial cash of {CHALLENGE_INITIAL_CASH}"
        
        # 验证只能有一只股票
        if len(stock_codes) != 1:
            return False, "Challenge mode allows only one stock"
        
        # 验证股票代码必须匹配挑战配置
        if stock_codes[0] != challenge.stock_code:
            return False, f"Challenge requires stock {challenge.stock_code}"
        
        return True, ""
    
    def calculate_progress(
        self,
        challenge: ChallengeConfig,
        current_assets: float,
        current_date: str,
    ) -> ChallengeProgress:
        """
        计算挑战进度
        
        Args:
            challenge: 挑战配置
            current_assets: 当前总资产
            current_date: 当前日期 (YYYY-MM-DD)
            
        Returns:
            挑战进度
        """
        # 计算进度百分比
        initial = challenge.initial_cash
        target = challenge.target_assets
        
        if target > initial:
            progress_pct = (current_assets - initial) / (target - initial) * 100
        else:
            progress_pct = 100.0 if current_assets >= target else 0.0
        
        progress_pct = max(0.0, min(100.0, progress_pct))
        
        # 计算剩余天数
        try:
            current = datetime.strptime(current_date, "%Y-%m-%d").date()
            end = datetime.strptime(challenge.end_date, "%Y-%m-%d").date()
            days_remaining = (end - current).days
            days_remaining = max(0, days_remaining)
        except ValueError:
            days_remaining = 0
        
        return ChallengeProgress(
            challenge_id=challenge.id,
            current_assets=current_assets,
            target_assets=target,
            progress_pct=progress_pct,
            days_remaining=days_remaining,
            current_date=current_date,
        )
    
    def evaluate_challenge(
        self,
        challenge: ChallengeConfig,
        final_assets: float,
        completion_date: str,
    ) -> ChallengeResult:
        """
        评估挑战结果
        
        Args:
            challenge: 挑战配置
            final_assets: 最终总资产
            completion_date: 完成日期 (YYYY-MM-DD)
            
        Returns:
            挑战结果
        """
        passed = final_assets >= challenge.target_assets
        
        return_pct = (final_assets - challenge.initial_cash) / challenge.initial_cash * 100
        
        return ChallengeResult(
            challenge_id=challenge.id,
            passed=passed,
            final_assets=final_assets,
            target_assets=challenge.target_assets,
            return_pct=return_pct,
            completion_date=completion_date,
        )
    
    def is_challenge_completed(self, current_date: str, challenge: ChallengeConfig) -> bool:
        """
        检查挑战是否已结束（到达结束日期）
        
        Args:
            current_date: 当前日期 (YYYY-MM-DD)
            challenge: 挑战配置
            
        Returns:
            是否已结束
        """
        try:
            current = datetime.strptime(current_date, "%Y-%m-%d").date()
            end = datetime.strptime(challenge.end_date, "%Y-%m-%d").date()
            return current >= end
        except ValueError:
            return False
    
    def check_exceeded_target(
        self,
        challenge: ChallengeConfig,
        final_assets: float,
        exceed_percentage: float = 50.0,
    ) -> bool:
        """
        检查是否超额完成目标
        
        Args:
            challenge: 挑战配置
            final_assets: 最终资产
            exceed_percentage: 超额百分比阈值
            
        Returns:
            是否超额完成
        """
        target = challenge.target_assets
        initial = challenge.initial_cash
        
        # 计算目标收益
        target_profit = target - initial
        
        # 计算实际收益
        actual_profit = final_assets - initial
        
        # 检查是否超过目标收益的指定百分比
        if target_profit > 0:
            exceed_ratio = (actual_profit - target_profit) / target_profit * 100
            return exceed_ratio >= exceed_percentage
        
        return False


# 全局服务实例
challenge_service = ChallengeService()
