"""
成就系统 API 路由 - Achievement System API Routes
Requirements: 7.1-7.5, 10.1-10.5
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from api.services.achievement_service import achievement_service
from api.services.achievement_models import AchievementProgress
from api.services.save_service import SaveService, SaveNotFoundError

router = APIRouter(prefix="/api/achievements", tags=["achievements"])

# 全局存档服务实例
_save_service: SaveService | None = None


def get_save_service() -> SaveService:
    """获取存档服务单例"""
    global _save_service
    if _save_service is None:
        _save_service = SaveService(storage_dir="./storage")
    return _save_service


# Response Models
class AchievementDefinitionResponse(BaseModel):
    """成就定义响应"""
    id: str
    name: str
    description: str
    icon: str
    category: str
    rarity: str
    progress_type: str
    target_value: float


class UnlockedAchievementResponse(BaseModel):
    """已解锁成就响应"""
    achievement_id: str
    unlocked_at: str


class AchievementProgressResponse(BaseModel):
    """成就进度响应"""
    unlocked_achievements: list[UnlockedAchievementResponse]
    progress_map: dict[str, float]
    new_achievements: list[str]
    total_unlocked: int
    total_achievements: int


class CheckAchievementsResponse(BaseModel):
    """检查成就响应"""
    new_achievements: list[str]
    progress: AchievementProgressResponse


# API Endpoints
@router.get("/definitions", response_model=list[AchievementDefinitionResponse])
async def get_achievement_definitions():
    """
    获取所有成就定义
    
    返回所有可用成就的定义信息
    """
    definitions = achievement_service.get_all_definitions()
    return [
        AchievementDefinitionResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            icon=d.icon,
            category=d.category.value,
            rarity=d.rarity.value,
            progress_type=d.progress_type.value,
            target_value=d.target_value,
        )
        for d in definitions
    ]


@router.get("/definitions/{category}", response_model=list[AchievementDefinitionResponse])
async def get_achievements_by_category(category: str):
    """
    获取指定分类的成就定义
    
    - category: 成就分类 (trading, profit, milestone, streak, t_trade, special, challenge)
    """
    definitions = achievement_service.get_definitions_by_category(category)
    return [
        AchievementDefinitionResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            icon=d.icon,
            category=d.category.value,
            rarity=d.rarity.value,
            progress_type=d.progress_type.value,
            target_value=d.target_value,
        )
        for d in definitions
    ]


@router.get("/{save_id}/progress", response_model=AchievementProgressResponse)
async def get_achievement_progress(save_id: str):
    """
    获取存档的成就进度
    
    - save_id: 存档ID
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        progress = save_data.achievement_progress or AchievementProgress()
        total_achievements = len(achievement_service.get_all_definitions())
        
        return AchievementProgressResponse(
            unlocked_achievements=[
                UnlockedAchievementResponse(
                    achievement_id=a.achievement_id,
                    unlocked_at=a.unlocked_at,
                )
                for a in progress.unlocked_achievements
            ],
            progress_map=progress.progress_map,
            new_achievements=progress.new_achievements,
            total_unlocked=len(progress.unlocked_achievements),
            total_achievements=total_achievements,
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{save_id}/check", response_model=CheckAchievementsResponse)
async def check_achievements(save_id: str):
    """
    检查并解锁成就
    
    - save_id: 存档ID
    
    根据当前存档状态检查所有成就条件，解锁满足条件的成就
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 构建成就上下文
        context = achievement_service.build_context_from_save(save_data)
        
        # 获取或创建成就进度
        progress = save_data.achievement_progress or AchievementProgress()
        
        # 检查并解锁成就
        new_achievements = achievement_service.check_and_unlock_achievements(progress, context)
        
        # 更新存档
        save_data.achievement_progress = progress
        service.update_save(save_id, save_data)
        
        total_achievements = len(achievement_service.get_all_definitions())
        
        return CheckAchievementsResponse(
            new_achievements=new_achievements,
            progress=AchievementProgressResponse(
                unlocked_achievements=[
                    UnlockedAchievementResponse(
                        achievement_id=a.achievement_id,
                        unlocked_at=a.unlocked_at,
                    )
                    for a in progress.unlocked_achievements
                ],
                progress_map=progress.progress_map,
                new_achievements=progress.new_achievements,
                total_unlocked=len(progress.unlocked_achievements),
                total_achievements=total_achievements,
            ),
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{save_id}/clear-new")
async def clear_new_achievements(save_id: str):
    """
    清除新成就标记
    
    - save_id: 存档ID
    
    返回被清除的新成就ID列表
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        progress = save_data.achievement_progress or AchievementProgress()
        cleared = progress.clear_new_achievements()
        
        save_data.achievement_progress = progress
        service.update_save(save_id, save_data)
        
        return {"cleared_achievements": cleared}
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
