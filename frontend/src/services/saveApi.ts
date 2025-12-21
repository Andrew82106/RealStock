/**
 * 存档 API 服务
 * Save System API Service
 */
import axios from 'axios';
import type {
  SaveMetadata,
  CreateSaveRequest,
  UpdateSaveRequest,
  DeleteSaveResponse,
  AddStockResponse,
  SaveAccountState,
  SaveGameState,
  SaveTradeRecord,
  SaveDailySnapshot,
  SavePendingOrder,
  ExtendedSaveData,
  AchievementProgress,
  TTradeStatistics,
  ChallengeConfig,
  ChallengeResult,
} from '../types';

const api = axios.create({
  baseURL: '/api/saves',
  timeout: 30000,
});

// 后端响应类型（snake_case）
interface SaveMetadataResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  current_date: string;
  total_assets: number;
  stock_count: number;
}

interface SaveDataResponse {
  version: string;
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  config: {
    initial_cash: number;
    start_date: string;
    end_date: string;
    game_mode?: string;
    challenge_id?: string;
  };
  account: {
    cash: number;
    positions: Array<{
      code: string;
      quantity: number;
      cost_price: number;
      current_price: number;
      profit_loss: number;
      profit_loss_pct: number;
    }>;
  };
  game_state: {
    current_date: string;
    playback_state: string;
    tick_index: number;
    session_id?: string;
  };
  stock_codes: string[];
  trade_history: Array<{
    order_id: string;
    code: string;
    order_type: string;
    price: number;
    quantity: number;
    fee: number;
    timestamp: string;
  }>;
  asset_history: Array<{
    date: string;
    total_assets: number;
    cash: number;
    market_value: number;
    daily_return: number;
    daily_profit: number;
    cumulative_return: number;
  }>;
  pending_orders: Array<{
    order_id: string;
    code: string;
    order_type: string;
    price: number;
    quantity: number;
    frozen_cash: number;
    frozen_quantity: number;
    order_date: string;
  }>;
  // Extended fields for achievement and challenge systems
  achievement_progress?: {
    unlocked_achievements: Array<{
      achievement_id: string;
      unlocked_at: string;
    }>;
    progress_map: Record<string, number>;
    new_achievements: string[];
  };
  t_trade_statistics?: {
    total_trades: number;
    successful_trades: number;
    failed_trades: number;
    success_rate: number;
    total_profit: number;
    total_fees: number;
    best_trade_profit: number;
    worst_trade_loss: number;
    average_profit: number;
  };
  challenge_config?: {
    id: string;
    name: string;
    difficulty: string;
    stock_code: string;
    stock_name: string;
    start_date: string;
    end_date: string;
    initial_cash: number;
    target_assets: number;
    description: string;
  };
  challenge_results?: Array<{
    challenge_id: string;
    passed: boolean;
    final_assets: number;
    target_assets: number;
    return_pct: number;
    completion_date: string;
  }>;
}

// 转换函数：后端响应 -> 前端类型
function toSaveMetadata(response: SaveMetadataResponse): SaveMetadata {
  return {
    id: response.id,
    name: response.name,
    createdAt: response.created_at,
    updatedAt: response.updated_at,
    currentDate: response.current_date,
    totalAssets: response.total_assets,
    stockCount: response.stock_count,
  };
}

function toSaveData(response: SaveDataResponse): ExtendedSaveData {
  // Convert achievement progress
  let achievementProgress: AchievementProgress | undefined;
  if (response.achievement_progress) {
    achievementProgress = {
      unlockedAchievements: response.achievement_progress.unlocked_achievements.map(a => ({
        achievementId: a.achievement_id,
        unlockedAt: a.unlocked_at,
      })),
      progressMap: response.achievement_progress.progress_map,
      newAchievements: response.achievement_progress.new_achievements,
      totalUnlocked: response.achievement_progress.unlocked_achievements.length,
      totalAchievements: 0, // Will be set by the component
    };
  }

  // Convert T-trade statistics
  let tTradeStatistics: TTradeStatistics | undefined;
  if (response.t_trade_statistics) {
    tTradeStatistics = {
      totalTrades: response.t_trade_statistics.total_trades,
      successfulTrades: response.t_trade_statistics.successful_trades,
      failedTrades: response.t_trade_statistics.failed_trades,
      successRate: response.t_trade_statistics.success_rate,
      totalProfit: response.t_trade_statistics.total_profit,
      totalFees: response.t_trade_statistics.total_fees,
      bestTradeProfit: response.t_trade_statistics.best_trade_profit,
      worstTradeLoss: response.t_trade_statistics.worst_trade_loss,
      averageProfit: response.t_trade_statistics.average_profit,
    };
  }

  // Convert challenge config
  let challengeConfig: ChallengeConfig | undefined;
  if (response.challenge_config) {
    challengeConfig = {
      id: response.challenge_config.id,
      name: response.challenge_config.name,
      difficulty: response.challenge_config.difficulty as 'easy' | 'medium' | 'hard',
      stockCode: response.challenge_config.stock_code,
      stockName: response.challenge_config.stock_name,
      startDate: response.challenge_config.start_date,
      endDate: response.challenge_config.end_date,
      initialCash: response.challenge_config.initial_cash,
      targetAssets: response.challenge_config.target_assets,
      description: response.challenge_config.description,
    };
  }

  // Convert challenge results
  let challengeResults: ChallengeResult[] | undefined;
  if (response.challenge_results && response.challenge_results.length > 0) {
    challengeResults = response.challenge_results.map(r => ({
      challengeId: r.challenge_id,
      passed: r.passed,
      finalAssets: r.final_assets,
      targetAssets: r.target_assets,
      returnPct: r.return_pct,
      completionDate: r.completion_date,
    }));
  }

  return {
    version: response.version,
    id: response.id,
    name: response.name,
    createdAt: response.created_at,
    updatedAt: response.updated_at,
    config: {
      initialCash: response.config.initial_cash,
      startDate: response.config.start_date,
      endDate: response.config.end_date,
      gameMode: (response.config.game_mode || 'free') as 'free' | 'challenge',
      challengeId: response.config.challenge_id,
    },
    account: {
      cash: response.account.cash,
      positions: response.account.positions.map((p) => ({
        code: p.code,
        quantity: p.quantity,
        costPrice: p.cost_price,
        currentPrice: p.current_price,
        profitLoss: p.profit_loss,
        profitLossPct: p.profit_loss_pct,
      })),
    },
    gameState: {
      currentDate: response.game_state.current_date,
      playbackState: response.game_state.playback_state,
      tickIndex: response.game_state.tick_index,
      sessionId: response.game_state.session_id,
    },
    stockCodes: response.stock_codes,
    tradeHistory: response.trade_history.map((t) => ({
      orderId: t.order_id,
      code: t.code,
      orderType: t.order_type,
      price: t.price,
      quantity: t.quantity,
      fee: t.fee,
      timestamp: t.timestamp,
    })),
    assetHistory: response.asset_history.map((a) => ({
      date: a.date,
      totalAssets: a.total_assets,
      cash: a.cash,
      marketValue: a.market_value,
      dailyReturn: a.daily_return,
      dailyProfit: a.daily_profit,
      cumulativeReturn: a.cumulative_return,
    })),
    pendingOrders: (response.pending_orders || []).map((p) => ({
      orderId: p.order_id,
      code: p.code,
      orderType: p.order_type,
      price: p.price,
      quantity: p.quantity,
      frozenCash: p.frozen_cash,
      frozenQuantity: p.frozen_quantity,
      orderDate: p.order_date,
    })),
    achievementProgress,
    tTradeStatistics,
    challengeConfig,
    challengeResults,
  };
}

// 转换函数：前端类型 -> 后端请求
function toBackendAccount(account: SaveAccountState) {
  return {
    cash: account.cash,
    positions: account.positions.map((p) => ({
      code: p.code,
      quantity: p.quantity,
      cost_price: p.costPrice,
      current_price: p.currentPrice,
      profit_loss: p.profitLoss,
      profit_loss_pct: p.profitLossPct,
    })),
  };
}

function toBackendGameState(gameState: SaveGameState) {
  return {
    current_date: gameState.currentDate,
    playback_state: gameState.playbackState,
    tick_index: gameState.tickIndex,
    session_id: gameState.sessionId,
  };
}

function toBackendTradeHistory(tradeHistory: SaveTradeRecord[]) {
  return tradeHistory.map((t) => ({
    order_id: t.orderId,
    code: t.code,
    order_type: t.orderType,
    price: t.price,
    quantity: t.quantity,
    fee: t.fee,
    timestamp: t.timestamp,
  }));
}

function toBackendAssetHistory(assetHistory: SaveDailySnapshot[]) {
  return assetHistory.map((a) => ({
    date: a.date,
    total_assets: a.totalAssets,
    cash: a.cash,
    market_value: a.marketValue,
    daily_return: a.dailyReturn,
    daily_profit: a.dailyProfit,
    cumulative_return: a.cumulativeReturn,
  }));
}

function toBackendPendingOrders(pendingOrders: SavePendingOrder[]) {
  return pendingOrders.map((p) => ({
    order_id: p.orderId,
    code: p.code,
    order_type: p.orderType,
    price: p.price,
    quantity: p.quantity,
    frozen_cash: p.frozenCash,
    frozen_quantity: p.frozenQuantity,
    order_date: p.orderDate,
  }));
}

export const saveApi = {
  /**
   * 获取存档列表
   * Requirements: 1.1
   */
  listSaves: async (): Promise<SaveMetadata[]> => {
    const response = await api.get<SaveMetadataResponse[]>('/');
    return response.data.map(toSaveMetadata);
  },

  /**
   * 创建新存档
   * Requirements: 2.2
   */
  createSave: async (name: string, initialCash: number = 100000, startDate?: string): Promise<ExtendedSaveData> => {
    const request: CreateSaveRequest = { name, initialCash };
    const response = await api.post<SaveDataResponse>('/', {
      name: request.name,
      initial_cash: request.initialCash,
      start_date: startDate,
    });
    return toSaveData(response.data);
  },

  /**
   * 加载存档
   * Requirements: 4.1
   */
  loadSave: async (saveId: string): Promise<ExtendedSaveData> => {
    const response = await api.get<SaveDataResponse>(`/${saveId}`);
    return toSaveData(response.data);
  },

  /**
   * 更新存档
   * Requirements: 3.2, 3.3
   */
  updateSave: async (saveId: string, data: UpdateSaveRequest): Promise<ExtendedSaveData> => {
    const backendRequest: Record<string, unknown> = {};
    
    if (data.account !== undefined) {
      backendRequest.account = toBackendAccount(data.account);
    }
    if (data.gameState !== undefined) {
      backendRequest.game_state = toBackendGameState(data.gameState);
    }
    if (data.stockCodes !== undefined) {
      backendRequest.stock_codes = data.stockCodes;
    }
    if (data.tradeHistory !== undefined) {
      backendRequest.trade_history = toBackendTradeHistory(data.tradeHistory);
    }
    if (data.assetHistory !== undefined) {
      backendRequest.asset_history = toBackendAssetHistory(data.assetHistory);
    }
    if (data.pendingOrders !== undefined) {
      backendRequest.pending_orders = toBackendPendingOrders(data.pendingOrders);
    }
    
    const response = await api.put<SaveDataResponse>(`/${saveId}`, backendRequest);
    return toSaveData(response.data);
  },

  /**
   * 删除存档
   * Requirements: 6.2
   */
  deleteSave: async (saveId: string): Promise<DeleteSaveResponse> => {
    const response = await api.delete<DeleteSaveResponse>(`/${saveId}`);
    return response.data;
  },

  /**
   * 添加股票到存档
   * Requirements: 5.3
   */
  addStock: async (saveId: string, stockCode: string): Promise<AddStockResponse> => {
    const response = await api.post<AddStockResponse>(`/${saveId}/stocks`, {
      stock_code: stockCode,
    });
    return response.data;
  },
};

export default saveApi;
