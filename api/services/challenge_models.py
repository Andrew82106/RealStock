"""
挑战模式数据模型和预设配置 - Challenge Mode Models and Configurations
Requirements: 16.1, 17.1, 17.2, 17.6
"""
from api.services.achievement_models import (
    ChallengeConfig,
    ChallengeResult,
    ChallengeProgress,
    ChallengeDifficulty,
    GameMode,
)


# 挑战模式固定初始资金
CHALLENGE_INITIAL_CASH = 10000.0


# ============ 预设挑战配置 ============

CHALLENGE_CONFIGS: list[ChallengeConfig] = [
    # 简单难度挑战
    ChallengeConfig(
        id="easy_pingan",
        name="新手试炼 - 平安银行",
        difficulty=ChallengeDifficulty.EASY,
        stock_code="000001",
        stock_name="平安银行",
        start_date="2024-01-02",
        end_date="2024-03-29",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=15000.0,  # 50% return
        description="在3个月内将1万元增值到1.5万元，目标收益率50%",
    ),
    ChallengeConfig(
        id="easy_gree",
        name="新手试炼 - 格力电器",
        difficulty=ChallengeDifficulty.EASY,
        stock_code="000651",
        stock_name="格力电器",
        start_date="2024-01-02",
        end_date="2024-03-29",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=15000.0,
        description="在3个月内将1万元增值到1.5万元，目标收益率50%",
    ),
    ChallengeConfig(
        id="easy_midea",
        name="新手试炼 - 美的集团",
        difficulty=ChallengeDifficulty.EASY,
        stock_code="000333",
        stock_name="美的集团",
        start_date="2024-01-02",
        end_date="2024-03-29",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=15000.0,
        description="在3个月内将1万元增值到1.5万元，目标收益率50%",
    ),
    
    # 中等难度挑战
    ChallengeConfig(
        id="medium_maotai",
        name="进阶挑战 - 贵州茅台",
        difficulty=ChallengeDifficulty.MEDIUM,
        stock_code="600519",
        stock_name="贵州茅台",
        start_date="2024-01-02",
        end_date="2024-06-28",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=20000.0,  # 100% return
        description="在6个月内将1万元翻倍到2万元，目标收益率100%",
    ),
    ChallengeConfig(
        id="medium_zhaoshang",
        name="进阶挑战 - 招商银行",
        difficulty=ChallengeDifficulty.MEDIUM,
        stock_code="600036",
        stock_name="招商银行",
        start_date="2024-01-02",
        end_date="2024-06-28",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=20000.0,
        description="在6个月内将1万元翻倍到2万元，目标收益率100%",
    ),
    ChallengeConfig(
        id="medium_wuliangye",
        name="进阶挑战 - 五粮液",
        difficulty=ChallengeDifficulty.MEDIUM,
        stock_code="000858",
        stock_name="五粮液",
        start_date="2024-01-02",
        end_date="2024-06-28",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=20000.0,
        description="在6个月内将1万元翻倍到2万元，目标收益率100%",
    ),
    
    # 困难难度挑战
    ChallengeConfig(
        id="hard_catl",
        name="大师之路 - 宁德时代",
        difficulty=ChallengeDifficulty.HARD,
        stock_code="300750",
        stock_name="宁德时代",
        start_date="2024-01-02",
        end_date="2024-12-31",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=30000.0,  # 200% return
        description="在一年内将1万元增值到3万元，目标收益率200%",
    ),
    ChallengeConfig(
        id="hard_byd",
        name="大师之路 - 比亚迪",
        difficulty=ChallengeDifficulty.HARD,
        stock_code="002594",
        stock_name="比亚迪",
        start_date="2024-01-02",
        end_date="2024-12-31",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=30000.0,
        description="在一年内将1万元增值到3万元，目标收益率200%",
    ),
    ChallengeConfig(
        id="hard_longi",
        name="大师之路 - 隆基绿能",
        difficulty=ChallengeDifficulty.HARD,
        stock_code="601012",
        stock_name="隆基绿能",
        start_date="2024-01-02",
        end_date="2024-12-31",
        initial_cash=CHALLENGE_INITIAL_CASH,
        target_assets=30000.0,
        description="在一年内将1万元增值到3万元，目标收益率200%",
    ),
]


# 挑战ID到配置的映射
CHALLENGE_MAP: dict[str, ChallengeConfig] = {
    config.id: config for config in CHALLENGE_CONFIGS
}


def get_all_challenges() -> list[ChallengeConfig]:
    """获取所有挑战配置"""
    return CHALLENGE_CONFIGS


def get_challenge_by_id(challenge_id: str) -> ChallengeConfig | None:
    """根据ID获取挑战配置"""
    return CHALLENGE_MAP.get(challenge_id)


def get_challenges_by_difficulty(difficulty: ChallengeDifficulty) -> list[ChallengeConfig]:
    """根据难度获取挑战列表"""
    return [c for c in CHALLENGE_CONFIGS if c.difficulty == difficulty]


def get_target_return_by_difficulty(difficulty: ChallengeDifficulty) -> float:
    """根据难度获取目标收益率"""
    targets = {
        ChallengeDifficulty.EASY: 50.0,    # 50%
        ChallengeDifficulty.MEDIUM: 100.0,  # 100%
        ChallengeDifficulty.HARD: 200.0,    # 200%
    }
    return targets.get(difficulty, 50.0)
