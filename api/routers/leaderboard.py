"""
排行榜 API 路由 - Leaderboard API Routes
Requirements: 12.1-12.9, 20.1-20.6
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from api.services.leaderboard_service import leaderboard_service, LeaderboardType

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


# Response Models
class LeaderboardEntryResponse(BaseModel):
    """排行榜条目响应"""
    rank: int
    save_id: str
    save_name: str
    value: float
    achievement_count: int
    is_current: bool


class LeaderboardResponse(BaseModel):
    """排行榜响应"""
    type: str
    entries: list[LeaderboardEntryResponse]


class AllLeaderboardsResponse(BaseModel):
    """所有排行榜响应"""
    leaderboards: dict[str, list[LeaderboardEntryResponse]]


class SaveRankResponse(BaseModel):
    """存档排名响应"""
    save_id: str
    type: str
    rank: Optional[int]


# API Endpoints
@router.get("/types")
async def get_leaderboard_types():
    """
    获取所有排行榜类型
    
    返回可用的排行榜类型列表
    """
    return {
        "types": [
            {"id": t.value, "name": _get_type_name(t)}
            for t in LeaderboardType
        ]
    }


@router.get("/{leaderboard_type}", response_model=LeaderboardResponse)
async def get_leaderboard(
    leaderboard_type: str,
    current_save_id: Optional[str] = None,
    limit: int = 10,
):
    """
    获取指定类型的排行榜
    
    - leaderboard_type: 排行榜类型
    - current_save_id: 当前存档ID（用于高亮）
    - limit: 返回条目数量限制
    """
    try:
        lb_type = LeaderboardType(leaderboard_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid leaderboard type: {leaderboard_type}. Valid types: {[t.value for t in LeaderboardType]}"
        )
    
    entries = leaderboard_service.get_leaderboard(
        leaderboard_type=lb_type,
        current_save_id=current_save_id,
        limit=limit,
    )
    
    return LeaderboardResponse(
        type=leaderboard_type,
        entries=[
            LeaderboardEntryResponse(
                rank=e.rank,
                save_id=e.save_id,
                save_name=e.save_name,
                value=e.value,
                achievement_count=e.achievement_count,
                is_current=e.is_current,
            )
            for e in entries
        ],
    )


@router.get("/", response_model=AllLeaderboardsResponse)
async def get_all_leaderboards(
    current_save_id: Optional[str] = None,
    limit: int = 10,
):
    """
    获取所有类型的排行榜
    
    - current_save_id: 当前存档ID（用于高亮）
    - limit: 每个排行榜的条目数量限制
    """
    all_boards = leaderboard_service.get_all_leaderboards(
        current_save_id=current_save_id,
        limit=limit,
    )
    
    return AllLeaderboardsResponse(
        leaderboards={
            lb_type: [
                LeaderboardEntryResponse(
                    rank=e.rank,
                    save_id=e.save_id,
                    save_name=e.save_name,
                    value=e.value,
                    achievement_count=e.achievement_count,
                    is_current=e.is_current,
                )
                for e in entries
            ]
            for lb_type, entries in all_boards.items()
        }
    )


@router.get("/rank/{save_id}/{leaderboard_type}", response_model=SaveRankResponse)
async def get_save_rank(save_id: str, leaderboard_type: str):
    """
    获取存档在指定排行榜中的排名
    
    - save_id: 存档ID
    - leaderboard_type: 排行榜类型
    """
    try:
        lb_type = LeaderboardType(leaderboard_type)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid leaderboard type: {leaderboard_type}"
        )
    
    rank = leaderboard_service.get_save_rank(save_id, lb_type)
    
    return SaveRankResponse(
        save_id=save_id,
        type=leaderboard_type,
        rank=rank,
    )


def _get_type_name(lb_type: LeaderboardType) -> str:
    """获取排行榜类型的显示名称"""
    names = {
        LeaderboardType.TOTAL_ASSETS: "总资产",
        LeaderboardType.TOTAL_RETURN: "总收益率",
        LeaderboardType.ACHIEVEMENT_COUNT: "成就数量",
        LeaderboardType.T_TRADE_PROFIT: "做T收益",
        LeaderboardType.WIN_RATE: "胜率",
        LeaderboardType.TRADE_COUNT: "交易次数",
    }
    return names.get(lb_type, lb_type.value)
