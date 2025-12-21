"""
存档 API 路由 - Save System API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from api.services.save_service import (
    SaveService,
    SaveMetadata,
    SaveData,
    SaveNotFoundError,
    SaveValidationError,
    SaveNameError,
    SaveIOError,
)

router = APIRouter(prefix="/api/saves", tags=["saves"])

# 全局存档服务实例
_save_service: SaveService | None = None


def get_save_service() -> SaveService:
    """获取存档服务单例"""
    global _save_service
    if _save_service is None:
        _save_service = SaveService(storage_dir="./storage")
    return _save_service


# Request/Response Models
class CreateSaveRequest(BaseModel):
    """创建存档请求"""
    name: str = Field(..., description="存档名称")
    initial_cash: float = Field(default=100000.0, description="初始资金")
    start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD")


class UpdateSaveRequest(BaseModel):
    """更新存档请求"""
    account: Optional[dict] = Field(default=None, description="账户状态")
    game_state: Optional[dict] = Field(default=None, description="游戏状态")
    stock_codes: Optional[list[str]] = Field(default=None, description="股票代码列表")
    trade_history: Optional[list[dict]] = Field(default=None, description="交易历史")
    asset_history: Optional[list[dict]] = Field(default=None, description="资产历史")
    pending_orders: Optional[list[dict]] = Field(default=None, description="挂单列表")


class AddStockRequest(BaseModel):
    """添加股票请求"""
    stock_code: str = Field(..., description="股票代码")


class SaveMetadataResponse(BaseModel):
    """存档元数据响应"""
    id: str
    name: str
    created_at: str
    updated_at: str
    current_date: str
    total_assets: float
    stock_count: int


class SaveDataResponse(BaseModel):
    """完整存档数据响应"""
    version: str
    id: str
    name: str
    created_at: str
    updated_at: str
    config: dict
    account: dict
    game_state: dict
    stock_codes: list[str]
    trade_history: list[dict]
    asset_history: list[dict]
    pending_orders: list[dict] = []
    # Extended fields for achievement and challenge systems
    achievement_progress: Optional[dict] = None
    t_trade_statistics: Optional[dict] = None
    challenge_config: Optional[dict] = None
    challenge_results: list[dict] = []


class DeleteResponse(BaseModel):
    """删除响应"""
    success: bool
    message: str


class AddStockResponse(BaseModel):
    """添加股票响应"""
    success: bool
    message: str
    stock_code: str


# API Endpoints
@router.get("/", response_model=list[SaveMetadataResponse])
async def list_saves():
    """
    获取所有存档列表
    
    返回所有存档的元数据，按最后更新时间排序
    """
    try:
        service = get_save_service()
        saves = service.list_saves()
        return [
            SaveMetadataResponse(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                updated_at=s.updated_at,
                current_date=s.current_date,
                total_assets=s.total_assets,
                stock_count=s.stock_count
            )
            for s in saves
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=SaveDataResponse)
async def create_save(request: CreateSaveRequest):
    """
    创建新存档
    
    - name: 存档名称（不能为空，不能重复）
    - initial_cash: 初始资金，默认 100000
    - start_date: 开始日期，格式 YYYY-MM-DD
    """
    try:
        service = get_save_service()
        save_data = service.create_save(request.name, request.initial_cash, request.start_date)
        return _save_data_to_response(save_data)
    except SaveNameError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SaveIOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{save_id}", response_model=SaveDataResponse)
async def get_save(save_id: str):
    """
    获取存档详情
    
    - save_id: 存档ID
    """
    try:
        service = get_save_service()
        save_data = service.load_save(save_id)
        return _save_data_to_response(save_data)
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SaveValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SaveIOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{save_id}", response_model=SaveDataResponse)
async def update_save(save_id: str, request: UpdateSaveRequest):
    """
    更新存档
    
    - save_id: 存档ID
    - 只更新请求中提供的字段
    """
    try:
        service = get_save_service()
        
        # 加载现有存档
        save_data = service.load_save(save_id)
        
        # 更新提供的字段
        if request.account is not None:
            from api.services.save_service import AccountState
            save_data.account = AccountState(**request.account)
        
        if request.game_state is not None:
            from api.services.save_service import GameState
            save_data.game_state = GameState(**request.game_state)
        
        if request.stock_codes is not None:
            save_data.stock_codes = request.stock_codes
        
        if request.trade_history is not None:
            from api.services.save_service import TradeRecord
            save_data.trade_history = [TradeRecord(**t) for t in request.trade_history]
        
        if request.asset_history is not None:
            from api.services.save_service import DailySnapshot
            save_data.asset_history = [DailySnapshot(**a) for a in request.asset_history]
        
        if request.pending_orders is not None:
            from api.services.save_service import PendingOrderRecord
            save_data.pending_orders = [PendingOrderRecord(**p) for p in request.pending_orders]
        
        # 保存更新
        service.update_save(save_id, save_data)
        
        # 重新加载并返回
        updated_data = service.load_save(save_id)
        return _save_data_to_response(updated_data)
        
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SaveValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SaveIOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{save_id}", response_model=DeleteResponse)
async def delete_save(save_id: str):
    """
    删除存档
    
    - save_id: 存档ID
    """
    try:
        service = get_save_service()
        service.delete_save(save_id)
        return DeleteResponse(success=True, message=f"存档 '{save_id}' 已删除")
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SaveIOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{save_id}/stocks", response_model=AddStockResponse)
async def add_stock(save_id: str, request: AddStockRequest):
    """
    添加股票到存档
    
    - save_id: 存档ID
    - stock_code: 股票代码
    """
    try:
        service = get_save_service()
        service.add_stock_to_save(save_id, request.stock_code)
        return AddStockResponse(
            success=True,
            message=f"股票 '{request.stock_code}' 已添加到存档",
            stock_code=request.stock_code
        )
    except SaveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SaveValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SaveIOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _save_data_to_response(save_data: SaveData) -> SaveDataResponse:
    """将 SaveData 转换为响应模型"""
    data_dict = save_data.to_dict()
    return SaveDataResponse(
        version=data_dict["version"],
        id=data_dict["id"],
        name=data_dict["name"],
        created_at=data_dict["created_at"],
        updated_at=data_dict["updated_at"],
        config=data_dict["config"],
        account=data_dict["account"],
        game_state=data_dict["game_state"],
        stock_codes=data_dict["stock_codes"],
        trade_history=data_dict["trade_history"],
        asset_history=data_dict["asset_history"],
        pending_orders=data_dict.get("pending_orders", []),
        achievement_progress=data_dict.get("achievement_progress"),
        t_trade_statistics=data_dict.get("t_trade_statistics"),
        challenge_config=data_dict.get("challenge_config"),
        challenge_results=data_dict.get("challenge_results", []),
    )
