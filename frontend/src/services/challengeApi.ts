/**
 * 挑战模式 API 服务
 */
import axios from 'axios';
import type {
  ChallengeConfig,
  ChallengeProgress,
  ChallengeResult,
  ChallengeDifficulty,
  CreateChallengeRequest,
  CreateChallengeResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api/challenges',
  timeout: 30000,
});

// 转换 API 响应到前端类型
const transformConfig = (data: {
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
}): ChallengeConfig => ({
  id: data.id,
  name: data.name,
  difficulty: data.difficulty as ChallengeDifficulty,
  stockCode: data.stock_code,
  stockName: data.stock_name,
  startDate: data.start_date,
  endDate: data.end_date,
  initialCash: data.initial_cash,
  targetAssets: data.target_assets,
  description: data.description,
});

const transformProgress = (data: {
  challenge_id: string;
  current_assets: number;
  target_assets: number;
  progress_pct: number;
  days_remaining: number;
  current_date: string;
}): ChallengeProgress => ({
  challengeId: data.challenge_id,
  currentAssets: data.current_assets,
  targetAssets: data.target_assets,
  progressPct: data.progress_pct,
  daysRemaining: data.days_remaining,
  currentDate: data.current_date,
});

const transformResult = (data: {
  challenge_id: string;
  passed: boolean;
  final_assets: number;
  target_assets: number;
  return_pct: number;
  completion_date: string;
}): ChallengeResult => ({
  challengeId: data.challenge_id,
  passed: data.passed,
  finalAssets: data.final_assets,
  targetAssets: data.target_assets,
  returnPct: data.return_pct,
  completionDate: data.completion_date,
});

export const challengeApi = {
  // 获取所有可用挑战
  getAvailableChallenges: async (): Promise<ChallengeConfig[]> => {
    const response = await api.get<Array<{
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
    }>>('/');
    return response.data.map(transformConfig);
  },

  // 获取指定难度的挑战
  getChallengesByDifficulty: async (difficulty: ChallengeDifficulty): Promise<ChallengeConfig[]> => {
    const response = await api.get<Array<{
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
    }>>(`/difficulty/${difficulty}`);
    return response.data.map(transformConfig);
  },

  // 获取单个挑战配置
  getChallenge: async (challengeId: string): Promise<ChallengeConfig> => {
    const response = await api.get<{
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
    }>(`/${challengeId}`);
    return transformConfig(response.data);
  },

  // 创建挑战存档
  createChallenge: async (request: CreateChallengeRequest): Promise<CreateChallengeResponse> => {
    const response = await api.post<{
      save_id: string;
      challenge: {
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
    }>('/create', {
      name: request.name,
      challenge_id: request.challengeId,
    });
    return {
      saveId: response.data.save_id,
      challenge: transformConfig(response.data.challenge),
    };
  },

  // 获取挑战进度
  getProgress: async (saveId: string): Promise<ChallengeProgress> => {
    const response = await api.get<{
      challenge_id: string;
      current_assets: number;
      target_assets: number;
      progress_pct: number;
      days_remaining: number;
      current_date: string;
    }>(`/${saveId}/progress`);
    return transformProgress(response.data);
  },

  // 评估挑战结果
  evaluateChallenge: async (saveId: string): Promise<ChallengeResult> => {
    const response = await api.post<{
      challenge_id: string;
      passed: boolean;
      final_assets: number;
      target_assets: number;
      return_pct: number;
      completion_date: string;
    }>(`/${saveId}/evaluate`);
    return transformResult(response.data);
  },
};

export default challengeApi;
