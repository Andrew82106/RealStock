"""
成就定义配置 - Achievement Definitions
Requirements: 1.1, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.5, 6.1-6.5, 8.1-8.10, 19.1-19.8
"""
from api.services.achievement_models import (
    AchievementDefinition,
    AchievementCategory,
    AchievementRarity,
    ProgressType,
)


# ============ 交易类成就 (Trading) ============

TRADING_ACHIEVEMENTS = [
    AchievementDefinition(
        id="first_trade",
        name="初次交易",
        description="完成第一笔买入交易",
        icon="🎯",
        category=AchievementCategory.TRADING,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="active_trader",
        name="活跃交易者",
        description="完成10笔交易",
        icon="📊",
        category=AchievementCategory.TRADING,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.COUNT,
        target_value=10,
    ),
    AchievementDefinition(
        id="trading_master",
        name="交易大师",
        description="完成100笔交易",
        icon="👑",
        category=AchievementCategory.TRADING,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.COUNT,
        target_value=100,
    ),
    AchievementDefinition(
        id="diversified_portfolio",
        name="分散投资",
        description="同时持有5只不同的股票",
        icon="🎨",
        category=AchievementCategory.TRADING,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.COUNT,
        target_value=5,
    ),
    AchievementDefinition(
        id="big_spender",
        name="大手笔",
        description="单笔交易金额超过10万元",
        icon="💰",
        category=AchievementCategory.TRADING,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.AMOUNT,
        target_value=100000,
    ),
]


# ============ 收益类成就 (Profit) ============

PROFIT_ACHIEVEMENTS = [
    AchievementDefinition(
        id="profitable_beginner",
        name="盈利新手",
        description="总收益率超过10%",
        icon="📈",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.PERCENTAGE,
        target_value=10,
    ),
    AchievementDefinition(
        id="skilled_investor",
        name="投资高手",
        description="总收益率超过50%",
        icon="🚀",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.PERCENTAGE,
        target_value=50,
    ),
    AchievementDefinition(
        id="double_your_money",
        name="翻倍达人",
        description="总收益率超过100%（资产翻倍）",
        icon="💎",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.PERCENTAGE,
        target_value=100,
    ),
    AchievementDefinition(
        id="trading_legend",
        name="交易传奇",
        description="总收益率超过500%",
        icon="🏆",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.PERCENTAGE,
        target_value=500,
    ),
    AchievementDefinition(
        id="daily_winner",
        name="日赢家",
        description="单日盈利超过1万元",
        icon="☀️",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.AMOUNT,
        target_value=10000,
    ),
    AchievementDefinition(
        id="jackpot_day",
        name="大丰收",
        description="单日盈利超过10万元",
        icon="🎰",
        category=AchievementCategory.PROFIT,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.AMOUNT,
        target_value=100000,
    ),
]


# ============ 里程碑类成就 (Milestone) ============

MILESTONE_ACHIEVEMENTS = [
    AchievementDefinition(
        id="first_milestone",
        name="小有成就",
        description="总资产达到20万元",
        icon="🎖️",
        category=AchievementCategory.MILESTONE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.AMOUNT,
        target_value=200000,
    ),
    AchievementDefinition(
        id="half_millionaire",
        name="半百万富翁",
        description="总资产达到50万元",
        icon="💵",
        category=AchievementCategory.MILESTONE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.AMOUNT,
        target_value=500000,
    ),
    AchievementDefinition(
        id="millionaire",
        name="百万富翁",
        description="总资产达到100万元",
        icon="🤑",
        category=AchievementCategory.MILESTONE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.AMOUNT,
        target_value=1000000,
    ),
    AchievementDefinition(
        id="monthly_trader",
        name="月度交易员",
        description="完成30个交易日",
        icon="📅",
        category=AchievementCategory.MILESTONE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.COUNT,
        target_value=30,
    ),
    AchievementDefinition(
        id="annual_veteran",
        name="年度老手",
        description="完成250个交易日（约一年）",
        icon="🗓️",
        category=AchievementCategory.MILESTONE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.COUNT,
        target_value=250,
    ),
]


# ============ 连续类成就 (Streak) ============

STREAK_ACHIEVEMENTS = [
    AchievementDefinition(
        id="winning_streak",
        name="连胜开始",
        description="连续3天盈利",
        icon="🔥",
        category=AchievementCategory.STREAK,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.COUNT,
        target_value=3,
    ),
    AchievementDefinition(
        id="hot_hand",
        name="手感火热",
        description="连续7天盈利",
        icon="🌟",
        category=AchievementCategory.STREAK,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.COUNT,
        target_value=7,
    ),
    AchievementDefinition(
        id="unstoppable",
        name="势不可挡",
        description="连续30天盈利",
        icon="⚡",
        category=AchievementCategory.STREAK,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.COUNT,
        target_value=30,
    ),
    AchievementDefinition(
        id="dedicated_trader",
        name="勤奋交易员",
        description="连续5个交易日进行交易",
        icon="💪",
        category=AchievementCategory.STREAK,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.COUNT,
        target_value=5,
    ),
]


# ============ 做T类成就 (T-Trade) ============

T_TRADE_ACHIEVEMENTS = [
    AchievementDefinition(
        id="t_trade_beginner",
        name="做T新手",
        description="完成第一次做T交易",
        icon="🔄",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="t_trade_apprentice",
        name="做T学徒",
        description="完成10次成功的做T交易",
        icon="📚",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.COUNT,
        target_value=10,
    ),
    AchievementDefinition(
        id="t_trade_expert",
        name="做T专家",
        description="完成50次成功的做T交易",
        icon="🎓",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.COUNT,
        target_value=50,
    ),
    AchievementDefinition(
        id="t_trade_master",
        name="做T大师",
        description="完成100次成功的做T交易",
        icon="🏅",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.COUNT,
        target_value=100,
    ),
    AchievementDefinition(
        id="consistent_t_trader",
        name="稳定做T者",
        description="做T成功率超过60%（至少20次）",
        icon="📊",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.PERCENTAGE,
        target_value=60,
    ),
    AchievementDefinition(
        id="t_trade_perfectionist",
        name="做T完美主义者",
        description="做T成功率超过80%（至少50次）",
        icon="💯",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.PERCENTAGE,
        target_value=80,
    ),
    AchievementDefinition(
        id="big_t_win",
        name="大T赢家",
        description="单次做T盈利超过1000元",
        icon="💸",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.AMOUNT,
        target_value=1000,
    ),
    AchievementDefinition(
        id="t_trade_jackpot",
        name="做T头奖",
        description="单次做T盈利超过10000元",
        icon="🎯",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.AMOUNT,
        target_value=10000,
    ),
    AchievementDefinition(
        id="t_trade_millionaire",
        name="做T百万富翁",
        description="累计做T盈利超过5万元",
        icon="💰",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.AMOUNT,
        target_value=50000,
    ),
    AchievementDefinition(
        id="day_trader",
        name="日内交易员",
        description="单日完成5次成功的做T交易",
        icon="⏰",
        category=AchievementCategory.T_TRADE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.COUNT,
        target_value=5,
    ),
]


# ============ 特殊类成就 (Special) ============

SPECIAL_ACHIEVEMENTS = [
    AchievementDefinition(
        id="limit_hunter",
        name="涨停猎手",
        description="买入的股票当日涨停",
        icon="🎯",
        category=AchievementCategory.SPECIAL,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="risk_avoider",
        name="风险规避者",
        description="在股票跌停前成功卖出",
        icon="🛡️",
        category=AchievementCategory.SPECIAL,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="stock_picker",
        name="选股高手",
        description="单只股票持仓盈利超过50%",
        icon="🔮",
        category=AchievementCategory.SPECIAL,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.PERCENTAGE,
        target_value=50,
    ),
    AchievementDefinition(
        id="comeback_king",
        name="逆袭之王",
        description="从20%回撤中恢复到盈亏平衡",
        icon="👑",
        category=AchievementCategory.SPECIAL,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="risk_master",
        name="风控大师",
        description="连续30天夏普比率保持在2.0以上",
        icon="📐",
        category=AchievementCategory.SPECIAL,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.COUNT,
        target_value=30,
    ),
]


# ============ 挑战类成就 (Challenge) ============

CHALLENGE_ACHIEVEMENTS = [
    AchievementDefinition(
        id="challenge_accepted",
        name="挑战已接受",
        description="首次通过任意难度的挑战",
        icon="✅",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="easy_winner",
        name="简单赢家",
        description="通过简单难度挑战",
        icon="🥉",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.COMMON,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="medium_master",
        name="中等大师",
        description="通过中等难度挑战",
        icon="🥈",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="hard_mode_hero",
        name="困难英雄",
        description="通过困难难度挑战",
        icon="🥇",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="challenge_veteran",
        name="挑战老手",
        description="通过5个任意难度的挑战",
        icon="🎖️",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.RARE,
        progress_type=ProgressType.COUNT,
        target_value=5,
    ),
    AchievementDefinition(
        id="challenge_legend",
        name="挑战传奇",
        description="通过3个困难难度挑战",
        icon="🏆",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.COUNT,
        target_value=3,
    ),
    AchievementDefinition(
        id="overachiever",
        name="超额完成者",
        description="在任意挑战中超过目标50%",
        icon="🚀",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.EPIC,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
    AchievementDefinition(
        id="pure_t_trader",
        name="纯做T交易员",
        description="仅使用做T策略通过挑战（无隔夜持仓）",
        icon="🔄",
        category=AchievementCategory.CHALLENGE,
        rarity=AchievementRarity.LEGENDARY,
        progress_type=ProgressType.BOOLEAN,
        target_value=1,
    ),
]


# ============ 所有成就汇总 ============

ALL_ACHIEVEMENTS: list[AchievementDefinition] = (
    TRADING_ACHIEVEMENTS +
    PROFIT_ACHIEVEMENTS +
    MILESTONE_ACHIEVEMENTS +
    STREAK_ACHIEVEMENTS +
    T_TRADE_ACHIEVEMENTS +
    SPECIAL_ACHIEVEMENTS +
    CHALLENGE_ACHIEVEMENTS
)

# 成就ID到定义的映射
ACHIEVEMENT_MAP: dict[str, AchievementDefinition] = {
    achievement.id: achievement for achievement in ALL_ACHIEVEMENTS
}


def get_all_achievements() -> list[AchievementDefinition]:
    """获取所有成就定义"""
    return ALL_ACHIEVEMENTS


def get_achievement_by_id(achievement_id: str) -> AchievementDefinition | None:
    """根据ID获取成就定义"""
    return ACHIEVEMENT_MAP.get(achievement_id)


def get_achievements_by_category(category: AchievementCategory) -> list[AchievementDefinition]:
    """根据分类获取成就列表"""
    return [a for a in ALL_ACHIEVEMENTS if a.category == category]


def get_achievements_by_rarity(rarity: AchievementRarity) -> list[AchievementDefinition]:
    """根据稀有度获取成就列表"""
    return [a for a in ALL_ACHIEVEMENTS if a.rarity == rarity]
