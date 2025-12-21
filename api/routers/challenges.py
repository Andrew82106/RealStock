"""
挑战模式 API 路由 - Challenge Mode API Routes
Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from api.services.challenge_service import challenge_service
from api.services.challenge_models import CHALLENGE_INITIAL_CASH
from api.services.achievement_models import ChallengeConfig, ChallengeDifficulty
from api.services.save_service import SaveService, SaveNotFoundError, SaveNameError

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

# 全局存档服务实例
_save_service: SaveService | None = None


def get_save_service() -> SaveService:
    """获取存档服务单例"""
    global _save_service
    if _save_service is None:
        _save_service = SaveService(storage_dir="./storage")
    return _save_service


# Request Models
class CreateChallengeRequest(BaseModel):
    """创建挑战存档请求"""
    name: str = Field(..., description="存档名称")
    challenge_id: str = Field(..., description="挑战ID")


# Response Models
class ChallengeConfigResponse(BaseModel):
    """挑战配置响应"""
    id: str
    name: str
    difficulty: str
    stock_code: str
    stock_name: str
    start_date: str
    end_date: str
    initial_cash: float
    target_assets: float
    description: str


class ChallengeProgressResponse(BaseModel):
    """挑战进度响应"""
    challenge_id: str
    current_assets: float
    target_assets: float
    progress_pct: float
    days_remaining: int
    current_date: str


class ChallengeResultResponse(BaseModel):
    """挑战结果响应"""
    challenge_id: str
    passed: bool
    final_assets: float
    target_assets: float
    return_pct: float
    completion_date: str


class CreateChallengeResponse(BaseModel):
    """创建挑战响应"""
    save_id: str
    challenge: ChallengeConfigResponse


# API Endpoints
@router.get("/", response_model=list[ChallengeConfigResponse])
async def get_available_challenges():
    """
    获取所有可用挑战
    
    返回所有预设的挑战配置
    """
    challenges = challenge_service.get_available_challenges()
    return [
        ChallengeConfigResponse(
            id=c.id,
            name=c.name,
            difficulty=c.difficulty.value,
            stock_code=c.stock_code,
            stock_name=c.stock_name,
            start_date=c.start_date,
            end_date=c.end_date,
            initial_cash=c.initial_cash,
            target_assets=c.target_assets,
            description=c.description,
        )
        for c in challenges
    ]


@router.get("/difficulty/{difficulty}", response_model=list[ChallengeConfigResponse])
async def get_challenges_by_difficulty(difficulty: str):
    """
    获取指定难度的挑战
    
    - difficulty: 难度等级 (easy, medium, hard)
    """
    try:
        diff = ChallengeDifficulty(difficulty)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty: {difficulty}")
    
    challenges = challenge_service.get_challenges_by_difficulty(diff)
    return [
        ChallengeConfigResponse(
            id=c.id,
            name=c.name,
            difficulty=c.difficulty.value,
            stock_code=c.stock_code,
            stock_name=c.stock_name,
            start_date=c.start_date,
            end_date=c.end_date,
            initial_cash=c.initial_cash,
            target_assets=c.target_assets,
            description=c.description,
        )
        for c in challenges
    ]


@router.get("/{challenge_id}", response_model=ChallengeConfigResponse)
async def get_challenge(challenge_id: str):
    """
    获取单个挑战配置
    
    - challenge_id: 挑战ID
    """
    challenge = challenge_service.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge '{challenge_id}' not found")
    
    return ChallengeConfigResponse(
        id=challenge.id,
        name=challenge.name,
        difficulty=challenge.difficulty.value,
        stock_code=challenge.stock_code,
        stock_name=challenge.stock_name,
        start_date=challenge.start_date,
        end_date=challenge.end_date,
        initial_cash=challenge.initial_cash,
        target_assets=challenge.target_assets,
        description=challenge.description,
    )


@router.post("/create", response_model=CreateChallengeResponse)
async def create_challenge_save(request: CreateChallengeRequest):
    """
    创建挑战模式存档
    
    - name: 存档名称
    - challenge_id: 挑战ID
    
    创建一个新的挑战模式存档，初始资金固定为10000，只能交易指定股票
    """
    # 获取挑战配置
    challenge = challenge_service.get_challenge(request.challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge '{request.challenge_id}' not found")
    
    try:
        service = get_save_service()
        
        # 创建挑战存档
        save_data = service.create_save(
            name=request.name,
            initial_cash=CHALLENGE_INITIAL_CASH,
            start_date=challenge.start_date,
            game_mode="challenge",
            challenge_id=challenge.id,
            challenge_config=challenge,
        )
        
        # 添加挑战指定的股票
        service.add_stock_to_save(save_data.id, challenge.stock_code)
        
        return CreateChallengeResponse(
            save_id=save_data.id,
            challenge=ChallengeConfigResponse(
                id=challenge.id,
                name=challenge.name,
                difficulty=challenge.difficulty.value,
                stock_code=challenge.stock_code,
                stock_name=challenge.stock_name,
                start_date=challenge.start_date,
                end_date=challenge.end_date,
                initial_cash=challenge.initial_cash,
                target_assets=challenge.target_assets,
                description=challenge.description,
            ),
        )
    except SaveNameError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{save_id}/progress", response_model=ChallengeProgressResponse)
async def get_challenge_progress(save_id: str):
    """
    获取挑战进度
    
    - save_id: 存档ID
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 验证是挑战模式存档
        if save_data.config.game_mode != "challenge":
            raise HTTPException(status_code=400, detail="Not a challenge mode save")
        
        if not save_data.challenge_config:
            raise HTTPException(status_code=400, detail="Challenge config not found")
        
        # 计算当前总资产
        cash = save_data.account.cash
        positions = save_data.account.positions
        market_value = sum(
            p.get("quantity", 0) * p.get("current_price", 0) 
            if isinstance(p, dict) else p.quantity * p.current_price
            for p in positions
        )
        current_assets = cash + market_value
        
        # 获取当前日期：优先使用 game_state.current_date，
        # 如果为空则使用 asset_history 中的最后一个日期，
        # 如果还是空则使用挑战的开始日期
        current_date = save_data.game_state.current_date
        if not current_date and save_data.asset_history:
            # 从 asset_history 获取最后一个日期
            last_snapshot = save_data.asset_history[-1]
            if isinstance(last_snapshot, dict):
                current_date = last_snapshot.get("date", "")
            else:
                current_date = last_snapshot.date
            # 同时使用 asset_history 中的最新资产数据
            if isinstance(last_snapshot, dict):
                current_assets = last_snapshot.get("total_assets", current_assets)
            else:
                current_assets = last_snapshot.total_assets
        if not current_date:
            current_date = save_data.challenge_config.start_date
        
        # 计算进度
        progress = challenge_service.calculate_progress(
            challenge=save_data.challenge_config,
            current_assets=current_assets,
            current_date=current_date,
        )
        
        return ChallengeProgressResponse(
            challenge_id=progress.challenge_id,
            current_assets=progress.current_assets,
            target_assets=progress.target_assets,
            progress_pct=progress.progress_pct,
            days_remaining=progress.days_remaining,
            current_date=progress.current_date,
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{save_id}/evaluate", response_model=ChallengeResultResponse)
async def evaluate_challenge(save_id: str):
    """
    评估挑战结果
    
    - save_id: 存档ID
    
    评估挑战是否完成，返回最终结果
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        
        # 验证是挑战模式存档
        if save_data.config.game_mode != "challenge":
            raise HTTPException(status_code=400, detail="Not a challenge mode save")
        
        if not save_data.challenge_config:
            raise HTTPException(status_code=400, detail="Challenge config not found")
        
        # 计算最终总资产
        cash = save_data.account.cash
        positions = save_data.account.positions
        market_value = sum(
            p.get("quantity", 0) * p.get("current_price", 0) 
            if isinstance(p, dict) else p.quantity * p.current_price
            for p in positions
        )
        final_assets = cash + market_value
        
        # 评估结果
        result = challenge_service.evaluate_challenge(
            challenge=save_data.challenge_config,
            final_assets=final_assets,
            completion_date=save_data.game_state.current_date,
        )
        
        # 保存结果到存档
        save_data.challenge_results.append(result.to_dict())
        service.update_save(save_id, save_data)
        
        return ChallengeResultResponse(
            challenge_id=result.challenge_id,
            passed=result.passed,
            final_assets=result.final_assets,
            target_assets=result.target_assets,
            return_pct=result.return_pct,
            completion_date=result.completion_date,
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
