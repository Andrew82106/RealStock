# Design Document: Save System (存档系统)

## Overview

存档系统为A股模拟交易系统提供持久化存储功能，允许用户创建、保存、加载和删除游戏存档。系统采用文件系统存储方案，将存档数据以JSON格式保存在 `storage` 目录下。

主要设计目标：
- 简单可靠的文件存储方案
- 支持多存档管理
- 自动保存游戏进度
- 支持动态添加股票到投资组合

## Architecture

```mermaid
graph TB
    subgraph Frontend
        HomePage[主页 - 存档列表]
        TradingPage[交易页面]
        SaveModal[存档命名弹窗]
        StockAddModal[添加股票弹窗]
    end
    
    subgraph Backend API
        SaveRouter[/api/saves]
        GameRouter[/api/game]
    end
    
    subgraph Services
        SaveService[SaveService]
        SessionManager[SessionManager]
    end
    
    subgraph Storage
        StorageDir[storage/]
        SaveFile[save_name.json]
        StockDataDir[save_name/stocks/]
    end
    
    HomePage --> SaveRouter
    TradingPage --> GameRouter
    SaveRouter --> SaveService
    GameRouter --> SessionManager
    SaveService --> StorageDir
    SessionManager --> SaveService
```

## Components and Interfaces

### 1. SaveService (后端服务)

负责存档文件的读写操作。

```python
class SaveService:
    """存档服务"""
    
    def __init__(self, storage_dir: str = "./storage"):
        self.storage_dir = Path(storage_dir)
        self.saves_dir = self.storage_dir / "saves"
        self.stock_data_dir = self.storage_dir / "stock_data"
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        self.stock_data_dir.mkdir(parents=True, exist_ok=True)
    
    def list_saves(self) -> list[SaveMetadata]:
        """列出所有存档"""
        pass
    
    def create_save(self, name: str, initial_cash: float = 100000.0) -> SaveData:
        """创建新存档"""
        pass
    
    def load_save(self, save_id: str) -> SaveData:
        """加载存档"""
        pass
    
    def update_save(self, save_id: str, data: SaveData) -> None:
        """更新存档"""
        pass
    
    def delete_save(self, save_id: str) -> bool:
        """删除存档"""
        pass
    
    def add_stock_to_save(self, save_id: str, stock_code: str) -> None:
        """添加股票到存档（只添加代码，数据由DataEngine管理）"""
        pass
    
    def sanitize_filename(self, name: str) -> str:
        """清理文件名，移除非法字符"""
        pass
    
    def validate_save_data(self, data: dict) -> bool:
        """验证存档数据结构"""
        pass
```

### 2. Save API Router (后端路由)

```python
# api/routers/saves.py

@router.get("/")
async def list_saves() -> list[SaveMetadata]:
    """获取所有存档列表"""
    pass

@router.post("/")
async def create_save(request: CreateSaveRequest) -> SaveData:
    """创建新存档"""
    pass

@router.get("/{save_id}")
async def get_save(save_id: str) -> SaveData:
    """获取存档详情"""
    pass

@router.put("/{save_id}")
async def update_save(save_id: str, data: UpdateSaveRequest) -> SaveData:
    """更新存档"""
    pass

@router.delete("/{save_id}")
async def delete_save(save_id: str) -> dict:
    """删除存档"""
    pass

@router.post("/{save_id}/stocks")
async def add_stock(save_id: str, request: AddStockRequest) -> dict:
    """添加股票到存档"""
    pass
```

### 3. Frontend API Service

```typescript
// frontend/src/services/saveApi.ts

export const saveApi = {
  // 获取存档列表
  listSaves: async (): Promise<SaveMetadata[]> => { ... },
  
  // 创建新存档
  createSave: async (name: string, initialCash?: number): Promise<SaveData> => { ... },
  
  // 加载存档
  loadSave: async (saveId: string): Promise<SaveData> => { ... },
  
  // 更新存档
  updateSave: async (saveId: string, data: Partial<SaveData>): Promise<SaveData> => { ... },
  
  // 删除存档
  deleteSave: async (saveId: string): Promise<void> => { ... },
  
  // 添加股票
  addStock: async (saveId: string, stockCode: string): Promise<void> => { ... },
};
```

### 4. Frontend Pages

#### HomePage (主页)
- 显示存档列表
- 创建新存档按钮
- 删除存档功能
- 点击存档进入交易页面

#### TradingView (交易页面)
- 添加股票工具栏按钮
- 自动保存功能
- 基于存档ID而非session_id

## Data Models

### SaveMetadata (存档元数据)

```typescript
interface SaveMetadata {
  id: string;           // 存档ID (sanitized name)
  name: string;         // 存档显示名称
  createdAt: string;    // 创建时间 ISO 8601
  updatedAt: string;    // 最后更新时间 ISO 8601
  currentDate: string;  // 当前模拟日期
  totalAssets: number;  // 总资产
  stockCount: number;   // 股票数量
}
```

### SaveData (完整存档数据)

```typescript
interface SaveData {
  version: string;      // 存档版本号
  id: string;           // 存档ID
  name: string;         // 存档名称
  createdAt: string;    // 创建时间
  updatedAt: string;    // 最后更新时间
  
  // 游戏配置
  config: {
    initialCash: number;
    startDate: string;
    endDate: string;
  };
  
  // 账户状态
  account: {
    cash: number;
    positions: Position[];
  };
  
  // 游戏状态
  gameState: {
    currentDate: string;
    playbackState: string;
    tickIndex: number;
  };
  
  // 股票列表
  stockCodes: string[];
  
  // 交易历史
  tradeHistory: TradeRecord[];
  
  // 资产历史
  assetHistory: DailySnapshot[];
}
```

### 存档文件结构

所有数据统一存储在 `storage` 目录下：

```
storage/                        # 根存储目录
├── saves/                      # 用户存档目录
│   ├── my-first-save.json      # 存档文件1
│   ├── another-save.json       # 存档文件2
│   └── ...
└── stock_data/                 # 股票数据缓存（全局共享）
    ├── daily/                  # 日线数据
    │   ├── 600519.csv
    │   └── 000001.csv
    └── intraday/               # 分时数据
        ├── 600519_2025-01-01.csv
        └── ...
```

**设计说明**:
- 所有数据统一存储在 `storage` 目录下
- `saves/` 子目录存放用户存档文件（JSON格式）
- `stock_data/` 子目录存放股票市场数据（CSV格式）
- 存档文件只记录股票代码列表，加载时从 stock_data 获取数据
- 多个存档共享同一份股票数据，避免重复存储

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Save-Load Round Trip

*For any* valid save data, saving to a file and then loading from that file SHALL produce an equivalent SaveData object.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 2: Save List Completeness

*For any* set of save files in the storage directory, listing saves SHALL return metadata for all and only those saves, with all required fields (name, createdAt, updatedAt, currentDate) populated.

**Validates: Requirements 1.1, 1.2**

### Property 3: Save Creation Produces Valid File

*For any* valid (non-empty, non-duplicate) save name, creating a save SHALL produce a valid JSON file in the storage directory with the correct filename and all required fields.

**Validates: Requirements 2.2, 7.1, 7.2, 7.3**

### Property 4: Empty Name Rejection

*For any* string composed entirely of whitespace (including empty string), attempting to create a save SHALL be rejected with an error.

**Validates: Requirements 2.3**

### Property 5: Duplicate Name Rejection

*For any* existing save name, attempting to create another save with the same name SHALL be rejected with an error.

**Validates: Requirements 2.4**

### Property 6: New Save Has Empty Portfolio

*For any* newly created save, the stockCodes list SHALL be empty and positions SHALL be empty.

**Validates: Requirements 2.5**

### Property 7: Stock Addition Persistence

*For any* save and any valid stock code, after adding the stock, the save file SHALL contain that stock code in the stockCodes list. Stock market data is fetched from the shared data_cache directory, not stored in the save file.

**Validates: Requirements 3.1, 5.3, 5.4**

### Property 8: Save Data Completeness

*For any* save file, it SHALL contain all required fields: version, id, name, config, account, gameState, stockCodes, tradeHistory, assetHistory.

**Validates: Requirements 3.4, 3.5**

### Property 9: Invalid Save Rejection

*For any* corrupted or invalid JSON file, or file missing required fields, loading SHALL fail with an appropriate error rather than returning partial data.

**Validates: Requirements 4.5, 7.4**

### Property 10: Save Deletion Removes File

*For any* existing save, after deletion, the save file SHALL no longer exist in the storage directory and SHALL not appear in the save list.

**Validates: Requirements 6.2, 6.3**

### Property 11: Filename Sanitization

*For any* save name containing special characters, the resulting filename SHALL only contain safe characters (alphanumeric, hyphen, underscore, Chinese characters) and SHALL have .json extension.

**Validates: Requirements 7.2**

## Error Handling

### 错误类型

```python
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
```

### 错误处理策略

1. **文件不存在**: 返回 404 错误，前端显示"存档不存在"
2. **文件损坏**: 返回 400 错误，前端显示"存档文件损坏，无法加载"
3. **名称重复**: 返回 409 错误，前端显示"存档名称已存在"
4. **名称为空**: 返回 400 错误，前端显示"请输入存档名称"
5. **IO错误**: 返回 500 错误，前端显示"保存失败，请重试"

## Testing Strategy

### 单元测试

- SaveService 的各个方法
- 文件名清理函数
- 数据验证函数
- API 路由处理

### 属性测试 (Property-Based Testing)

使用 Hypothesis 库进行属性测试：

- **Round-trip 测试**: 生成随机 SaveData，保存后加载，验证等价性
- **文件名清理测试**: 生成包含各种字符的名称，验证清理后的文件名安全
- **数据完整性测试**: 生成随机存档数据，验证所有必需字段存在

### 集成测试

- 完整的存档创建-加载-更新-删除流程
- 前后端交互测试
- 并发访问测试

### 测试配置

- 属性测试最少运行 100 次迭代
- 使用临时目录进行文件系统测试
- 测试后清理所有测试文件
