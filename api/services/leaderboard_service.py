"""
排行榜服务 - Leaderboard Service
Requirements: 12.1-12.9, 20.1-20.6
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from api.services.save_service import SaveService, SaveData, SaveMetadata


class LeaderboardType(str, Enum):
    """排行榜类型"""
    TOTAL_ASSETS = "total_assets"           # 总资产排名
    TOTAL_RETURN = "total_return"           # 总收益率排名
    ACHIEVEMENT_COUNT = "achievement_count"  # 成就数量排名
    T_TRADE_PROFIT = "t_trade_profit"       # 做T收益排名
    WIN_RATE = "win_rate"                   # 胜率排名
    TRADE_COUNT = "trade_count"             # 交易次数排名


@dataclass
class LeaderboardEntry:
    """排行榜条目"""
    rank: int
    save_id: str
    save_name: str
    value: float
    achievement_count: int = 0
    is_current: bool = False  # 是否是当前存档
    
    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "save_id": self.save_id,
            "save_name": self.save_name,
            "value": self.value,
            "achievement_count": self.achievement_count,
            "is_current": self.is_current,
        }


class LeaderboardService:
    """排行榜服务"""
    
    def __init__(self, save_service: Optional[SaveService] = None):
        self.save_service = save_service or SaveService()
    
    def _calculate_total_assets(self, save_data: SaveData) -> float:
        """计算总资产"""
        cash = save_data.account.cash
        positions = save_data.account.positions
        
        market_value = 0.0
        for pos in positions:
            if isinstance(pos, dict):
                market_value += pos.get("quantity", 0) * pos.get("current_price", 0)
            else:
                market_value += getattr(pos, "quantity", 0) * getattr(pos, "current_price", 0)
        
        return cash + market_value
    
    def _calculate_total_return(self, save_data: SaveData) -> float:
        """计算总收益率"""
        initial_cash = save_data.config.initial_cash
        if initial_cash <= 0:
            return 0.0
        
        total_assets = self._calculate_total_assets(save_data)
        return (total_assets - initial_cash) / initial_cash * 100
    
    def _calculate_win_rate(self, save_data: SaveData) -> float:
        """计算胜率（盈利交易占比）"""
        trades = save_data.trade_history
        if not trades:
            return 0.0
        
        # 简化计算：统计卖出交易的盈亏
        sell_trades = [t for t in trades if self._get_trade_type(t) == "sell"]
        if not sell_trades:
            return 0.0
        
        # 这里简化处理，实际需要配对买卖计算
        # 暂时返回50%作为默认值
        return 50.0
    
    def _get_trade_type(self, trade) -> str:
        """获取交易类型"""
        if isinstance(trade, dict):
            return trade.get("order_type", "")
        return getattr(trade, "order_type", "")
    
    def _get_achievement_count(self, save_data: SaveData) -> int:
        """获取成就数量"""
        # 从存档数据中获取成就数量
        # 如果存档有 achievement_progress 字段
        if hasattr(save_data, "achievement_progress") and save_data.achievement_progress:
            progress = save_data.achievement_progress
            if isinstance(progress, dict):
                unlocked = progress.get("unlocked_achievements", [])
                return len(unlocked)
        return 0
    
    def _get_t_trade_profit(self, save_data: SaveData) -> float:
        """获取做T收益"""
        # 从存档数据中获取做T统计
        if hasattr(save_data, "t_trade_statistics") and save_data.t_trade_statistics:
            stats = save_data.t_trade_statistics
            if isinstance(stats, dict):
                return stats.get("total_profit", 0.0)
        return 0.0
    
    def _get_value_for_type(
        self, 
        leaderboard_type: LeaderboardType, 
        save_data: SaveData
    ) -> float:
        """根据排行榜类型获取对应值"""
        if leaderboard_type == LeaderboardType.TOTAL_ASSETS:
            return self._calculate_total_assets(save_data)
        elif leaderboard_type == LeaderboardType.TOTAL_RETURN:
            return self._calculate_total_return(save_data)
        elif leaderboard_type == LeaderboardType.ACHIEVEMENT_COUNT:
            return float(self._get_achievement_count(save_data))
        elif leaderboard_type == LeaderboardType.T_TRADE_PROFIT:
            return self._get_t_trade_profit(save_data)
        elif leaderboard_type == LeaderboardType.WIN_RATE:
            return self._calculate_win_rate(save_data)
        elif leaderboard_type == LeaderboardType.TRADE_COUNT:
            return float(len(save_data.trade_history))
        else:
            return 0.0
    
    def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        current_save_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[LeaderboardEntry]:
        """
        获取排行榜
        
        Args:
            leaderboard_type: 排行榜类型
            current_save_id: 当前存档ID（用于高亮）
            limit: 返回条目数量限制
            
        Returns:
            排行榜条目列表
        """
        # 获取所有存档
        save_metas = self.save_service.list_saves()
        
        entries = []
        for meta in save_metas:
            try:
                save_data = self.save_service.load_save(meta.id)
                value = self._get_value_for_type(leaderboard_type, save_data)
                achievement_count = self._get_achievement_count(save_data)
                
                entries.append({
                    "save_id": meta.id,
                    "save_name": meta.name,
                    "value": value,
                    "achievement_count": achievement_count,
                    "is_current": meta.id == current_save_id,
                })
            except Exception:
                # 跳过无法加载的存档
                continue
        
        # 排序（降序）
        entries.sort(key=lambda x: x["value"], reverse=True)
        
        # 添加排名并限制数量
        result = []
        for i, entry in enumerate(entries[:limit]):
            result.append(LeaderboardEntry(
                rank=i + 1,
                save_id=entry["save_id"],
                save_name=entry["save_name"],
                value=entry["value"],
                achievement_count=entry["achievement_count"],
                is_current=entry["is_current"],
            ))
        
        return result
    
    def get_save_rank(
        self,
        save_id: str,
        leaderboard_type: LeaderboardType,
    ) -> Optional[int]:
        """
        获取指定存档在排行榜中的排名
        
        Args:
            save_id: 存档ID
            leaderboard_type: 排行榜类型
            
        Returns:
            排名（从1开始），如果存档不存在返回None
        """
        leaderboard = self.get_leaderboard(
            leaderboard_type=leaderboard_type,
            current_save_id=save_id,
            limit=1000,  # 获取所有
        )
        
        for entry in leaderboard:
            if entry.save_id == save_id:
                return entry.rank
        
        return None
    
    def get_all_leaderboards(
        self,
        current_save_id: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, list[LeaderboardEntry]]:
        """
        获取所有类型的排行榜
        
        Args:
            current_save_id: 当前存档ID
            limit: 每个排行榜的条目数量限制
            
        Returns:
            排行榜类型到条目列表的映射
        """
        result = {}
        for lb_type in LeaderboardType:
            result[lb_type.value] = self.get_leaderboard(
                leaderboard_type=lb_type,
                current_save_id=current_save_id,
                limit=limit,
            )
        return result


# 全局服务实例
leaderboard_service = LeaderboardService()
