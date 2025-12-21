/**
 * 做T统计 API 服务
 */
import axios from 'axios';
import type {
  TTradeStatistics,
  TTradeRecord,
  TTradeHistoryResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api/t-trades',
  timeout: 30000,
});

// 转换 API 响应到前端类型
const transformStatistics = (data: {
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  success_rate: number;
  total_profit: number;
  total_fees: number;
  best_trade_profit: number;
  worst_trade_loss: number;
  average_profit: number;
}): TTradeStatistics => ({
  totalTrades: data.total_trades,
  successfulTrades: data.successful_trades,
  failedTrades: data.failed_trades,
  successRate: data.success_rate,
  totalProfit: data.total_profit,
  totalFees: data.total_fees,
  bestTradeProfit: data.best_trade_profit,
  worstTradeLoss: data.worst_trade_loss,
  averageProfit: data.average_profit,
});

const transformRecord = (data: {
  id: string;
  stock_code: string;
  sell_price: number;
  buy_price: number;
  quantity: number;
  sell_fee: number;
  buy_fee: number;
  profit: number;
  trade_date: string;
  sell_time: string;
  buy_time: string;
  is_successful: boolean;
}): TTradeRecord => ({
  id: data.id,
  stockCode: data.stock_code,
  sellPrice: data.sell_price,
  buyPrice: data.buy_price,
  quantity: data.quantity,
  sellFee: data.sell_fee,
  buyFee: data.buy_fee,
  profit: data.profit,
  tradeDate: data.trade_date,
  sellTime: data.sell_time,
  buyTime: data.buy_time,
  isSuccessful: data.is_successful,
});

export const tTradeApi = {
  // 获取做T统计数据
  getStatistics: async (saveId: string): Promise<TTradeStatistics> => {
    const response = await api.get<{
      total_trades: number;
      successful_trades: number;
      failed_trades: number;
      success_rate: number;
      total_profit: number;
      total_fees: number;
      best_trade_profit: number;
      worst_trade_loss: number;
      average_profit: number;
    }>(`/${saveId}/statistics`);
    return transformStatistics(response.data);
  },

  // 获取做T历史记录
  getHistory: async (saveId: string, limit: number = 100): Promise<TTradeHistoryResponse> => {
    const response = await api.get<{
      statistics: {
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
      trades: Array<{
        id: string;
        stock_code: string;
        sell_price: number;
        buy_price: number;
        quantity: number;
        sell_fee: number;
        buy_fee: number;
        profit: number;
        trade_date: string;
        sell_time: string;
        buy_time: string;
        is_successful: boolean;
      }>;
    }>(`/${saveId}/history`, { params: { limit } });
    return {
      statistics: transformStatistics(response.data.statistics),
      trades: response.data.trades.map(transformRecord),
    };
  },

  // 重新计算做T统计
  recalculate: async (saveId: string): Promise<TTradeStatistics> => {
    const response = await api.post<{
      total_trades: number;
      successful_trades: number;
      failed_trades: number;
      success_rate: number;
      total_profit: number;
      total_fees: number;
      best_trade_profit: number;
      worst_trade_loss: number;
      average_profit: number;
    }>(`/${saveId}/recalculate`);
    return transformStatistics(response.data);
  },
};

export default tTradeApi;
