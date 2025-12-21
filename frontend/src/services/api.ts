/**
 * API 服务封装
 */
import axios from 'axios';
import type {
  StockInfo,
  DailyBar,
  GameStartRequest,
  GameStartResponse,
  OrderRequest,
  OrderResponse,
  Account,
  GameState,
  PerformanceMetrics,
  AssetHistory,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// 股票相关 API
export const stockApi = {
  // 获取股票列表
  getStockList: async (keyword?: string): Promise<StockInfo[]> => {
    const params = keyword ? { keyword } : {};
    const response = await api.get<StockInfo[]>('/stocks/', { params });
    return response.data;
  },

  // 流式搜索股票（带进度）
  searchStockStream: (
    keyword: string,
    onProgress: (progress: number, message: string) => void,
    onResult: (stocks: StockInfo[]) => void,
    onError: (error: string) => void,
    onDone: () => void
  ): (() => void) => {
    const eventSource = new EventSource(`/api/stocks/search-stream?keyword=${encodeURIComponent(keyword)}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'start':
            onProgress(0, data.message);
            break;
          case 'progress':
            onProgress(data.progress, data.message);
            break;
          case 'result':
            onResult(data.data);
            break;
          case 'done':
            eventSource.close();
            onDone();
            break;
          case 'error':
            eventSource.close();
            onError(data.message);
            break;
        }
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      onError('搜索连接失败');
    };
    
    // 返回取消函数
    return () => {
      eventSource.close();
    };
  },

  // 获取日线数据
  getDailyData: async (
    code: string,
    startDate: string,
    endDate: string
  ): Promise<DailyBar[]> => {
    const response = await api.get<DailyBar[]>(`/stocks/${code}/daily`, {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },
};

// 游戏相关 API
export const gameApi = {
  // 开始游戏
  startGame: async (request: GameStartRequest): Promise<GameStartResponse> => {
    const response = await api.post<GameStartResponse>('/game/start', request);
    return response.data;
  },

  // 从存档开始游戏
  startFromSave: async (saveId: string): Promise<{
    session_id: string;
    save_id: string;
    current_date: string;
    trading_dates: string[];
    stock_codes: string[];
  }> => {
    const response = await api.post<{
      session_id: string;
      save_id: string;
      current_date: string;
      trading_dates: string[];
      stock_codes: string[];
    }>('/game/start-from-save', { save_id: saveId });
    return response.data;
  },

  // 获取游戏状态
  getGameState: async (sessionId: string): Promise<GameState> => {
    const response = await api.get<{
      session_id: string;
      current_date: string;
      playback_state: string;
      is_last_day: boolean;
    }>(`/game/${sessionId}/state`);
    return {
      sessionId: response.data.session_id,
      currentDate: response.data.current_date,
      playbackState: response.data.playback_state as GameState['playbackState'],
      isLastDay: response.data.is_last_day,
    };
  },

  // 获取账户状态
  getAccount: async (sessionId: string): Promise<Account> => {
    const response = await api.get<{
      cash: number;
      total_assets: number;
      total_market_value: number;
      positions: Array<{
        code: string;
        quantity: number;
        cost_price: number;
        current_price: number;
        profit_loss: number;
        profit_loss_pct: number;
        buy_date?: string;
      }>;
    }>(`/game/${sessionId}/account`);
    return {
      cash: response.data.cash,
      totalAssets: response.data.total_assets,
      totalMarketValue: response.data.total_market_value,
      positions: response.data.positions.map((p) => ({
        code: p.code,
        quantity: p.quantity,
        costPrice: p.cost_price,
        currentPrice: p.current_price,
        profitLoss: p.profit_loss,
        profitLossPct: p.profit_loss_pct,
        buyDate: p.buy_date,
      })),
    };
  },

  // 买入
  buy: async (request: OrderRequest): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>('/game/buy', request);
    return response.data;
  },

  // 卖出
  sell: async (request: OrderRequest): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>('/game/sell', request);
    return response.data;
  },

  // 下一交易日
  nextDay: async (sessionId: string): Promise<GameState> => {
    const response = await api.post<{
      session_id: string;
      current_date: string;
      playback_state: string;
      is_last_day: boolean;
    }>(`/game/${sessionId}/next-day`);
    return {
      sessionId: response.data.session_id,
      currentDate: response.data.current_date,
      playbackState: response.data.playback_state as GameState['playbackState'],
      isLastDay: response.data.is_last_day,
    };
  },

  // 获取绩效指标
  getMetrics: async (sessionId: string): Promise<PerformanceMetrics> => {
    const response = await api.get<{
      total_return: number;
      max_drawdown: number;
      win_rate: number;
      sharpe_ratio: number;
      total_trades: number;
      winning_trades: number;
      losing_trades: number;
    }>(`/game/${sessionId}/metrics`);
    return {
      totalReturn: response.data.total_return,
      maxDrawdown: response.data.max_drawdown,
      winRate: response.data.win_rate,
      sharpeRatio: response.data.sharpe_ratio,
      totalTrades: response.data.total_trades,
      winningTrades: response.data.winning_trades,
      losingTrades: response.data.losing_trades,
    };
  },

  // 获取当前行情
  getCurrentBars: async (
    sessionId: string
  ): Promise<Record<string, DailyBar>> => {
    const response = await api.get<Record<string, DailyBar>>(
      `/game/${sessionId}/bars`
    );
    return response.data;
  },

  // 删除会话
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/game/${sessionId}`);
  },

  // HTTP 暂停播放（备用接口）
  pausePlayback: async (sessionId: string): Promise<{ success: boolean; playback_state: string }> => {
    const response = await api.post<{ success: boolean; playback_state: string }>(
      `/game/${sessionId}/pause`
    );
    return response.data;
  },

  // HTTP 开始播放（备用接口）
  startPlayback: async (sessionId: string, speed: number = 10): Promise<{ success: boolean; playback_state: string }> => {
    const response = await api.post<{ success: boolean; playback_state: string }>(
      `/game/${sessionId}/play`,
      { speed }
    );
    return response.data;
  },

  // HTTP 单步执行
  singleTick: async (sessionId: string): Promise<{
    success: boolean;
    tick_index?: number;
    prices?: Record<string, number>;
    playback_state: string;
    current_date?: string;
  }> => {
    const response = await api.post<{
      success: boolean;
      tick_index?: number;
      prices?: Record<string, number>;
      playback_state: string;
      current_date?: string;
    }>(`/game/${sessionId}/tick`);
    return response.data;
  },

  // 获取资产历史
  getAssetHistory: async (sessionId: string): Promise<AssetHistory> => {
    const response = await api.get<{
      initial_cash: number;
      current_assets: number;
      total_return: number;
      history: Array<{
        date: string;
        total_assets: number;
        cash: number;
        market_value: number;
        daily_return: number;
        daily_profit: number;
        cumulative_return: number;
      }>;
    }>(`/game/${sessionId}/asset-history`);
    return {
      initialCash: response.data.initial_cash,
      currentAssets: response.data.current_assets,
      totalReturn: response.data.total_return,
      history: response.data.history.map(h => ({
        date: h.date,
        totalAssets: h.total_assets,
        cash: h.cash,
        marketValue: h.market_value,
        dailyReturn: h.daily_return,
        dailyProfit: h.daily_profit,
        cumulativeReturn: h.cumulative_return,
      })),
    };
  },

  // 检查会话是否存在
  checkSessionExists: async (sessionId: string): Promise<{
    exists: boolean;
    session_id?: string;
    current_date?: string;
    stock_codes?: string[];
  }> => {
    const response = await api.get<{
      exists: boolean;
      session_id?: string;
      current_date?: string;
      stock_codes?: string[];
    }>(`/game/${sessionId}/exists`);
    return response.data;
  },

  // 获取挂单列表
  getPendingOrders: async (sessionId: string): Promise<Array<{
    orderId: string;
    code: string;
    orderType: 'buy' | 'sell';
    price: number;
    quantity: number;
    frozenCash: number;
    frozenQuantity: number;
  }>> => {
    const response = await api.get<Array<{
      order_id: string;
      code: string;
      order_type: string;
      price: number;
      quantity: number;
      frozen_cash: number;
      frozen_quantity: number;
    }>>(`/game/${sessionId}/pending-orders`);
    return response.data.map(o => ({
      orderId: o.order_id,
      code: o.code,
      orderType: o.order_type as 'buy' | 'sell',
      price: o.price,
      quantity: o.quantity,
      frozenCash: o.frozen_cash,
      frozenQuantity: o.frozen_quantity,
    }));
  },

  // 撤销挂单
  cancelOrder: async (sessionId: string, orderId: string): Promise<OrderResponse> => {
    const response = await api.post<OrderResponse>('/game/cancel', {
      session_id: sessionId,
      order_id: orderId,
    });
    return response.data;
  },

  // 获取交易历史
  getTradeHistory: async (sessionId: string): Promise<Array<{
    orderId: string;
    code: string;
    orderType: string;
    price: number;
    quantity: number;
    status: string;
    filledPrice: number | null;
    filledQuantity: number | null;
    fee: number;
    orderDate: string;
    rejectReason: string | null;
  }>> => {
    const response = await api.get<Array<{
      order_id: string;
      code: string;
      order_type: string;
      price: number;
      quantity: number;
      status: string;
      filled_price: number | null;
      filled_quantity: number | null;
      fee: number;
      order_date: string;
      reject_reason: string | null;
    }>>(`/game/${sessionId}/trade-history`);
    return response.data.map(o => ({
      orderId: o.order_id,
      code: o.code,
      orderType: o.order_type,
      price: o.price,
      quantity: o.quantity,
      status: o.status,
      filledPrice: o.filled_price,
      filledQuantity: o.filled_quantity,
      fee: o.fee,
      orderDate: o.order_date,
      rejectReason: o.reject_reason,
    }));
  },
};


export default api;
