"""
成就系统数据模型 - Achievement System Data Models
Requirements: 1.1, 1.2, 1.3, 16.1, 17.1
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any


class AchievementRarity(Enum):
    """成就稀有度等级"""
    COMMON = "common"       # 普通
    RARE = "rare"           # 稀有
    EPIC = "epic"           # 史诗
    LEGENDARY = "legendary" # 传说


class AchievementCategory(Enum):
    """成就分类"""
    TRADING = "trading"       # 交易
    PROFIT = "profit"         # 收益
    MILESTONE = "milestone"   # 里程碑
    STREAK = "streak"         # 连续
    T_TRADE = "t_trade"       # 做T
    SPECIAL = "special"       # 特殊
    CHALLENGE = "challenge"   # 挑战


class ProgressType(Enum):
    """进度类型"""
    BOOLEAN = "boolean"       # 是/否类型
    COUNT = "count"           # 计数类型
    PERCENTAGE = "percentage" # 百分比类型
    AMOUNT = "amount"         # 金额类型


class GameMode(Enum):
    """游戏模式"""
    FREE = "free"           # 自由模式
    CHALLENGE = "challenge" # 挑战模式


class ChallengeDifficulty(Enum):
    """挑战难度"""
    EASY = "easy"       # 简单 - 50% return target
    MEDIUM = "medium"   # 中等 - 100% return target
    HARD = "hard"       # 困难 - 200% return target


@dataclass
class AchievementDefinition:
    """成就定义"""
    id: str
    name: str
    description: str
    icon: str
    category: AchievementCategory
    rarity: AchievementRarity
    progress_type: ProgressType
    target_value: float
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category.value,
            "rarity": self.rarity.value,
            "progress_type": self.progress_type.value,
            "target_value": self.target_value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AchievementDefinition":
        """从字典创建"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            icon=data["icon"],
            category=AchievementCategory(data["category"]),
            rarity=AchievementRarity(data["rarity"]),
            progress_type=ProgressType(data["progress_type"]),
            target_value=data["target_value"],
        )


@dataclass
class UnlockedAchievement:
    """已解锁的成就"""
    achievement_id: str
    unlocked_at: str  # ISO 8601 格式
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "achievement_id": self.achievement_id,
            "unlocked_at": self.unlocked_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UnlockedAchievement":
        """从字典创建"""
        return cls(
            achievement_id=data["achievement_id"],
            unlocked_at=data["unlocked_at"],
        )


@dataclass
class AchievementProgress:
    """成就进度"""
    unlocked_achievements: list[UnlockedAchievement] = field(default_factory=list)
    progress_map: dict[str, float] = field(default_factory=dict)
    new_achievements: list[str] = field(default_factory=list)  # 新解锁的成就ID列表
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "unlocked_achievements": [a.to_dict() for a in self.unlocked_achievements],
            "progress_map": self.progress_map,
            "new_achievements": self.new_achievements,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AchievementProgress":
        """从字典创建"""
        return cls(
            unlocked_achievements=[
                UnlockedAchievement.from_dict(a) 
                for a in data.get("unlocked_achievements", [])
            ],
            progress_map=data.get("progress_map", {}),
            new_achievements=data.get("new_achievements", []),
        )
    
    def is_unlocked(self, achievement_id: str) -> bool:
        """检查成就是否已解锁"""
        return any(a.achievement_id == achievement_id for a in self.unlocked_achievements)
    
    def get_progress(self, achievement_id: str) -> float:
        """获取成就进度"""
        return self.progress_map.get(achievement_id, 0.0)
    
    def unlock(self, achievement_id: str) -> bool:
        """解锁成就，返回是否是新解锁"""
        if self.is_unlocked(achievement_id):
            return False
        
        self.unlocked_achievements.append(UnlockedAchievement(
            achievement_id=achievement_id,
            unlocked_at=datetime.now().isoformat(),
        ))
        self.new_achievements.append(achievement_id)
        return True
    
    def update_progress(self, achievement_id: str, value: float) -> None:
        """更新成就进度"""
        self.progress_map[achievement_id] = value
    
    def clear_new_achievements(self) -> list[str]:
        """清除新成就列表并返回"""
        new_list = self.new_achievements.copy()
        self.new_achievements = []
        return new_list


@dataclass
class AchievementContext:
    """成就检查上下文 - 包含检查成就所需的所有数据"""
    # 交易相关
    total_trades: int = 0
    total_buy_trades: int = 0
    total_sell_trades: int = 0
    largest_single_trade_amount: float = 0.0
    unique_stocks_held: int = 0
    
    # 收益相关
    total_return_pct: float = 0.0
    daily_profit: float = 0.0
    current_total_assets: float = 0.0
    initial_cash: float = 100000.0
    
    # 里程碑相关
    trading_days_count: int = 0
    
    # 连续相关
    consecutive_profit_days: int = 0
    consecutive_trading_days: int = 0
    
    # 做T相关
    total_t_trades: int = 0
    successful_t_trades: int = 0
    t_trade_success_rate: float = 0.0
    best_t_trade_profit: float = 0.0
    cumulative_t_trade_profit: float = 0.0
    daily_successful_t_trades: int = 0
    
    # 特殊成就相关
    caught_limit_up: bool = False
    avoided_limit_down: bool = False
    best_single_stock_gain_pct: float = 0.0
    recovered_from_drawdown: bool = False
    sharpe_ratio_30d: float = 0.0
    
    # 挑战相关
    challenges_passed: int = 0
    easy_challenges_passed: int = 0
    medium_challenges_passed: int = 0
    hard_challenges_passed: int = 0
    challenge_exceeded_target_50pct: bool = False
    challenge_passed_with_only_t_trades: bool = False


@dataclass
class ChallengeConfig:
    """挑战配置"""
    id: str
    name: str
    difficulty: ChallengeDifficulty
    stock_code: str
    stock_name: str
    start_date: str
    end_date: str
    initial_cash: float  # 固定为 10000
    target_assets: float
    description: str
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "difficulty": self.difficulty.value,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_cash": self.initial_cash,
            "target_assets": self.target_assets,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChallengeConfig":
        """从字典创建"""
        return cls(
            id=data["id"],
            name=data["name"],
            difficulty=ChallengeDifficulty(data["difficulty"]),
            stock_code=data["stock_code"],
            stock_name=data.get("stock_name", ""),
            start_date=data["start_date"],
            end_date=data["end_date"],
            initial_cash=data["initial_cash"],
            target_assets=data["target_assets"],
            description=data["description"],
        )


@dataclass
class ChallengeResult:
    """挑战结果"""
    challenge_id: str
    passed: bool
    final_assets: float
    target_assets: float
    return_pct: float
    completion_date: str
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "challenge_id": self.challenge_id,
            "passed": self.passed,
            "final_assets": self.final_assets,
            "target_assets": self.target_assets,
            "return_pct": self.return_pct,
            "completion_date": self.completion_date,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChallengeResult":
        """从字典创建"""
        return cls(
            challenge_id=data["challenge_id"],
            passed=data["passed"],
            final_assets=data["final_assets"],
            target_assets=data["target_assets"],
            return_pct=data["return_pct"],
            completion_date=data["completion_date"],
        )


@dataclass
class ChallengeProgress:
    """挑战进度"""
    challenge_id: str
    current_assets: float
    target_assets: float
    progress_pct: float
    days_remaining: int
    current_date: str
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "challenge_id": self.challenge_id,
            "current_assets": self.current_assets,
            "target_assets": self.target_assets,
            "progress_pct": self.progress_pct,
            "days_remaining": self.days_remaining,
            "current_date": self.current_date,
        }
