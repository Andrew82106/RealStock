/**
 * 排行榜 API 服务
 */
import axios from 'axios';
import type {
  LeaderboardType,
  LeaderboardEntry,
  LeaderboardResponse,
  AllLeaderboardsResponse,
  SaveRankResponse,
} from '../types';

const api = axios.create({
  baseURL: '/api/leaderboard',
  timeout: 30000,
});

// 转换 API 响应到前端类型
const transformEntry = (data: {
  rank: number;
  save_id: string;
  save_name: string;
  value: number;
  achievement_count: number;
  is_current: boolean;
}): LeaderboardEntry => ({
  rank: data.rank,
  saveId: data.save_id,
  saveName: data.save_name,
  value: data.value,
  achievementCount: data.achievement_count,
  isCurrent: data.is_current,
});

export const leaderboardApi = {
  // 获取排行榜类型列表
  getTypes: async (): Promise<Array<{ id: LeaderboardType; name: string }>> => {
    const response = await api.get<{
      types: Array<{ id: string; name: string }>;
    }>('/types');
    return response.data.types.map(t => ({
      id: t.id as LeaderboardType,
      name: t.name,
    }));
  },

  // 获取指定类型的排行榜
  getLeaderboard: async (
    type: LeaderboardType,
    currentSaveId?: string,
    limit: number = 10
  ): Promise<LeaderboardResponse> => {
    const params: Record<string, string | number> = { limit };
    if (currentSaveId) {
      params.current_save_id = currentSaveId;
    }
    
    const response = await api.get<{
      type: string;
      entries: Array<{
        rank: number;
        save_id: string;
        save_name: string;
        value: number;
        achievement_count: number;
        is_current: boolean;
      }>;
    }>(`/${type}`, { params });
    
    return {
      type: response.data.type as LeaderboardType,
      entries: response.data.entries.map(transformEntry),
    };
  },

  // 获取所有排行榜
  getAllLeaderboards: async (
    currentSaveId?: string,
    limit: number = 10
  ): Promise<AllLeaderboardsResponse> => {
    const params: Record<string, string | number> = { limit };
    if (currentSaveId) {
      params.current_save_id = currentSaveId;
    }
    
    const response = await api.get<{
      leaderboards: Record<string, Array<{
        rank: number;
        save_id: string;
        save_name: string;
        value: number;
        achievement_count: number;
        is_current: boolean;
      }>>;
    }>('/', { params });
    
    const leaderboards: Record<LeaderboardType, LeaderboardEntry[]> = {} as Record<LeaderboardType, LeaderboardEntry[]>;
    for (const [key, entries] of Object.entries(response.data.leaderboards)) {
      leaderboards[key as LeaderboardType] = entries.map(transformEntry);
    }
    
    return { leaderboards };
  },

  // 获取存档在指定排行榜中的排名
  getSaveRank: async (saveId: string, type: LeaderboardType): Promise<SaveRankResponse> => {
    const response = await api.get<{
      save_id: string;
      type: string;
      rank: number | null;
    }>(`/rank/${saveId}/${type}`);
    
    return {
      saveId: response.data.save_id,
      type: response.data.type as LeaderboardType,
      rank: response.data.rank,
    };
  },
};

export default leaderboardApi;
