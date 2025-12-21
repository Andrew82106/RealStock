"""
存档服务 - Save Service for managing game saves
Requirements: 1.5, 14.1, 14.2, 14.4, 16.5
"""
import json
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from api.services.achievement_models import (
    GameMode,
    ChallengeConfig,
    AchievementProgress,
)
from api.services.t_trade_models import TTradeStatistics


@dataclass
class SaveConfig:
    """存档配置"""
    initial_cash: float = 100000.0
    start_date: str = ""
    end_date: str = ""
    game_mode: str = "free"  # "free" or "challenge"
    challenge_id: Optional[str] = None  # 挑战ID（仅挑战模式）


@dataclass
class AccountState:
    """账户状态"""
    cash: float = 100000.0
    positions: list = field(default_factory=list)


@dataclass
class GameState:
    """游戏状态"""
    current_date: str = ""
    playback_state: str = "paused"
    tick_index: int = 0
    session_id: str = ""  # 会话ID，用于复用会话


@dataclass
class TradeRecord:
    """交易记录"""
    order_id: str = ""
    code: str = ""
    order_type: str = ""
    price: float = 0.0
    quantity: int = 0
    fee: float = 0.0
    timestamp: str = ""


@dataclass
class PendingOrderRecord:
    """挂单记录"""
    order_id: str = ""
    code: str = ""
    order_type: str = ""
    price: float = 0.0
    quantity: int = 0
    frozen_cash: float = 0.0
    frozen_quantity: int = 0
    order_date: str = ""


@dataclass
class DailySnapshot:
    """每日资产快照"""
    date: str = ""
    total_assets: float = 0.0
    cash: float = 0.0
    market_value: float = 0.0
    daily_return: float = 0.0
    daily_profit: float = 0.0
    cumulative_return: float = 0.0


@dataclass
class SaveMetadata:
    """存档元数据"""
    id: str
    name: str
    created_at: str
    updated_at: str
    current_date: str
    total_assets: float
    stock_count: int


@dataclass
class SaveData:
    """完整存档数据"""
    version: str
    id: str
    name: str
    created_at: str
    updated_at: str
    config: SaveConfig
    account: AccountState
    game_state: GameState
    stock_codes: list[str]
    trade_history: list[TradeRecord]
    asset_history: list[DailySnapshot]
    pending_orders: list[PendingOrderRecord] = field(default_factory=list)
    # 成就系统相关字段
    achievement_progress: Optional[AchievementProgress] = None
    t_trade_statistics: Optional[TTradeStatistics] = None
    challenge_config: Optional[ChallengeConfig] = None
    challenge_results: list[dict] = field(default_factory=list)  # 历史挑战结果

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "version": self.version,
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config": {
                "initial_cash": self.config.initial_cash,
                "start_date": self.config.start_date,
                "end_date": self.config.end_date,
                "game_mode": self.config.game_mode,
                "challenge_id": self.config.challenge_id,
            },
            "account": asdict(self.account),
            "game_state": asdict(self.game_state),
            "stock_codes": self.stock_codes,
            "trade_history": [asdict(t) for t in self.trade_history],
            "asset_history": [asdict(a) for a in self.asset_history],
            "pending_orders": [asdict(p) for p in self.pending_orders],
            "challenge_results": self.challenge_results,
        }
        
        # 添加成就进度
        if self.achievement_progress:
            result["achievement_progress"] = self.achievement_progress.to_dict()
        
        # 添加做T统计
        if self.t_trade_statistics:
            result["t_trade_statistics"] = self.t_trade_statistics.to_dict()
        
        # 添加挑战配置
        if self.challenge_config:
            result["challenge_config"] = self.challenge_config.to_dict()
        
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SaveData":
        """从字典创建"""
        # 解析配置
        config_data = data["config"]
        config = SaveConfig(
            initial_cash=config_data.get("initial_cash", 100000.0),
            start_date=config_data.get("start_date", ""),
            end_date=config_data.get("end_date", ""),
            game_mode=config_data.get("game_mode", "free"),
            challenge_id=config_data.get("challenge_id"),
        )
        
        # 解析成就进度
        achievement_progress = None
        if "achievement_progress" in data and data["achievement_progress"]:
            achievement_progress = AchievementProgress.from_dict(data["achievement_progress"])
        
        # 解析做T统计
        t_trade_statistics = None
        if "t_trade_statistics" in data and data["t_trade_statistics"]:
            t_trade_statistics = TTradeStatistics.from_dict(data["t_trade_statistics"])
        
        # 解析挑战配置
        challenge_config = None
        if "challenge_config" in data and data["challenge_config"]:
            challenge_config = ChallengeConfig.from_dict(data["challenge_config"])
        
        return cls(
            version=data["version"],
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            config=config,
            account=AccountState(**data["account"]),
            game_state=GameState(**data["game_state"]),
            stock_codes=data["stock_codes"],
            trade_history=[TradeRecord(**t) for t in data["trade_history"]],
            asset_history=[DailySnapshot(**a) for a in data["asset_history"]],
            pending_orders=[PendingOrderRecord(**p) for p in data.get("pending_orders", [])],
            achievement_progress=achievement_progress,
            t_trade_statistics=t_trade_statistics,
            challenge_config=challenge_config,
            challenge_results=data.get("challenge_results", []),
        )


# 错误类型
class SaveError(Exception):
    """存档错误基类"""
    pass


class SaveNotFoundError(SaveError):
    """存档不存在"""
    pass


class SaveValidationError(SaveError):
    """存档数据验证失败"""
    pass


class SaveNameError(SaveError):
    """存档名称错误（空名称或重复）"""
    pass


class SaveIOError(SaveError):
    """存档读写错误"""
    pass


# 存档版本号
SAVE_VERSION = "1.0"

# 必需字段列表
REQUIRED_FIELDS = [
    "version", "id", "name", "config", "account", 
    "game_state", "stock_codes", "trade_history", "asset_history"
]


class SaveService:
    """存档服务"""

    def __init__(self, storage_dir: str = "./storage"):
        self.storage_dir = Path(storage_dir)
        self.saves_dir = self.storage_dir / "saves"
        self.stock_data_dir = self.storage_dir / "stock_data"
        self._init_storage()

    def _init_storage(self) -> None:
        """初始化存储目录结构"""
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        self.stock_data_dir.mkdir(parents=True, exist_ok=True)
        # 创建日线和分时数据子目录
        (self.stock_data_dir / "daily").mkdir(exist_ok=True)
        (self.stock_data_dir / "intraday").mkdir(exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """清理文件名，移除非法字符
        
        保留：字母、数字、中文、下划线、连字符
        """
        # 移除首尾空白
        name = name.strip()
        # 替换空格为下划线
        name = name.replace(" ", "_")
        # 只保留安全字符：字母、数字、中文、下划线、连字符
        safe_name = re.sub(r'[^\w\u4e00-\u9fff-]', '', name)
        # 如果结果为空，使用时间戳
        if not safe_name:
            safe_name = f"save_{int(time.time())}"
        return safe_name

    def _get_save_path(self, save_id: str) -> Path:
        """获取存档文件路径"""
        return self.saves_dir / f"{save_id}.json"

    def validate_save_data(self, data: dict) -> bool:
        """验证存档数据结构
        
        Returns:
            True if valid, raises SaveValidationError if invalid
        """
        # 检查必需字段
        for field in REQUIRED_FIELDS:
            if field not in data:
                raise SaveValidationError(f"Missing required field: {field}")
        
        # 验证 config 结构
        config = data.get("config", {})
        if not isinstance(config, dict):
            raise SaveValidationError("Invalid config structure")
        
        # 验证 account 结构
        account = data.get("account", {})
        if not isinstance(account, dict):
            raise SaveValidationError("Invalid account structure")
        if "cash" not in account:
            raise SaveValidationError("Missing cash in account")
        
        # 验证 game_state 结构
        game_state = data.get("game_state", {})
        if not isinstance(game_state, dict):
            raise SaveValidationError("Invalid game_state structure")
        
        # 验证 stock_codes 是列表
        if not isinstance(data.get("stock_codes"), list):
            raise SaveValidationError("stock_codes must be a list")
        
        # 验证 trade_history 是列表
        if not isinstance(data.get("trade_history"), list):
            raise SaveValidationError("trade_history must be a list")
        
        # 验证 asset_history 是列表
        if not isinstance(data.get("asset_history"), list):
            raise SaveValidationError("asset_history must be a list")
        
        return True

    def list_saves(self) -> list[SaveMetadata]:
        """列出所有存档"""
        saves = []
        for save_file in self.saves_dir.glob("*.json"):
            try:
                with open(save_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 计算总资产
                account = data.get("account", {})
                cash = account.get("cash", 0)
                positions = account.get("positions", [])
                market_value = sum(
                    p.get("quantity", 0) * p.get("current_price", 0) 
                    for p in positions
                )
                total_assets = cash + market_value
                
                metadata = SaveMetadata(
                    id=data.get("id", save_file.stem),
                    name=data.get("name", save_file.stem),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    current_date=data.get("game_state", {}).get("current_date", ""),
                    total_assets=total_assets,
                    stock_count=len(data.get("stock_codes", []))
                )
                saves.append(metadata)
            except (json.JSONDecodeError, KeyError):
                # 跳过损坏的文件
                continue
        
        # 按更新时间排序，最新的在前
        saves.sort(key=lambda s: s.updated_at, reverse=True)
        return saves

    def create_save(
        self, 
        name: str, 
        initial_cash: float = 100000.0, 
        start_date: str = None,
        game_mode: str = "free",
        challenge_id: Optional[str] = None,
        challenge_config: Optional[ChallengeConfig] = None,
    ) -> SaveData:
        """创建新存档"""
        # 验证名称
        stripped_name = name.strip() if name else ""
        if not stripped_name:
            raise SaveNameError("Save name cannot be empty")
        
        # 生成 save_id
        save_id = self.sanitize_filename(stripped_name)
        
        # 检查重复
        save_path = self._get_save_path(save_id)
        if save_path.exists():
            raise SaveNameError(f"Save with name '{name}' already exists")
        
        # 创建存档数据
        now = datetime.now().isoformat()
        save_data = SaveData(
            version=SAVE_VERSION,
            id=save_id,
            name=stripped_name,
            created_at=now,
            updated_at=now,
            config=SaveConfig(
                initial_cash=initial_cash, 
                start_date=start_date or "",
                game_mode=game_mode,
                challenge_id=challenge_id,
            ),
            account=AccountState(cash=initial_cash, positions=[]),
            game_state=GameState(current_date=start_date or ""),
            stock_codes=[],
            trade_history=[],
            asset_history=[],
            achievement_progress=AchievementProgress(),  # 初始化空成就进度
            t_trade_statistics=TTradeStatistics(),  # 初始化空做T统计
            challenge_config=challenge_config,
        )
        
        # 保存到文件
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(save_data.to_dict(), f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise SaveIOError(f"Failed to create save file: {e}")
        
        return save_data

    def load_save(self, save_id: str) -> SaveData:
        """加载存档"""
        save_path = self._get_save_path(save_id)
        
        if not save_path.exists():
            raise SaveNotFoundError(f"Save '{save_id}' not found")
        
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SaveValidationError(f"Invalid JSON in save file: {e}")
        except IOError as e:
            raise SaveIOError(f"Failed to read save file: {e}")
        
        # 验证数据结构
        self.validate_save_data(data)
        
        return SaveData.from_dict(data)

    def update_save(self, save_id: str, data: SaveData) -> None:
        """更新存档"""
        save_path = self._get_save_path(save_id)
        
        if not save_path.exists():
            raise SaveNotFoundError(f"Save '{save_id}' not found")
        
        # 更新时间戳
        data.updated_at = datetime.now().isoformat()
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise SaveIOError(f"Failed to update save file: {e}")

    def delete_save(self, save_id: str) -> bool:
        """删除存档"""
        save_path = self._get_save_path(save_id)
        
        if not save_path.exists():
            raise SaveNotFoundError(f"Save '{save_id}' not found")
        
        try:
            save_path.unlink()
            return True
        except IOError as e:
            raise SaveIOError(f"Failed to delete save file: {e}")

    def add_stock_to_save(self, save_id: str, stock_code: str) -> None:
        """添加股票到存档（只添加代码，数据由DataEngine管理）"""
        save_data = self.load_save(save_id)
        
        # 避免重复添加
        if stock_code not in save_data.stock_codes:
            save_data.stock_codes.append(stock_code)
            self.update_save(save_id, save_data)
