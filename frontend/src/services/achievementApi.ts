/**
 * 成就系统 API 服务
 */
import axios from 'axios';
import type {
  AchievementDefinition,
  AchievementProgress,
  CheckAchievementsResponse,
  AchievementCategory,
} from '../types';

const api = axios.create({
  baseURL: '/api/achievements',
  timeout: 30000,
});

// 转换 API 响应到前端类型
const transformDefinition = (data: {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  rarity: string;
  progress_type: string;
  target_value: number;
}): AchievementDefinition => ({
  id: data.id,
  name: data.name,
  description: data.description,
  icon: data.icon,
  category: data.category as AchievementCategory,
  rarity: data.rarity as AchievementDefinition['rarity'],
  progressType: data.progress_type as AchievementDefinition['progressType'],
  targetValue: data.target_value,
});

const transformProgress = (data: {
  unlocked_achievements: Array<{ achievement_id: string; unlocked_at: string }>;
  progress_map: Record<string, number>;
  new_achievements: string[];
  total_unlocked: number;
  total_achievements: number;
}): AchievementProgress => ({
  unlockedAchievements: data.unlocked_achievements.map(a => ({
    achievementId: a.achievement_id,
    unlockedAt: a.unlocked_at,
  })),
  progressMap: data.progress_map,
  newAchievements: data.new_achievements,
  totalUnlocked: data.total_unlocked,
  totalAchievements: data.total_achievements,
});

export const achievementApi = {
  // 获取所有成就定义
  getDefinitions: async (): Promise<AchievementDefinition[]> => {
    const response = await api.get<Array<{
      id: string;
      name: string;
      description: string;
      icon: string;
      category: string;
      rarity: string;
      progress_type: string;
      target_value: number;
    }>>('/definitions');
    return response.data.map(transformDefinition);
  },

  // 获取指定分类的成就定义
  getDefinitionsByCategory: async (category: AchievementCategory): Promise<AchievementDefinition[]> => {
    const response = await api.get<Array<{
      id: string;
      name: string;
      description: string;
      icon: string;
      category: string;
      rarity: string;
      progress_type: string;
      target_value: number;
    }>>(`/definitions/${category}`);
    return response.data.map(transformDefinition);
  },

  // 获取存档的成就进度
  getProgress: async (saveId: string): Promise<AchievementProgress> => {
    const response = await api.get<{
      unlocked_achievements: Array<{ achievement_id: string; unlocked_at: string }>;
      progress_map: Record<string, number>;
      new_achievements: string[];
      total_unlocked: number;
      total_achievements: number;
    }>(`/${saveId}/progress`);
    return transformProgress(response.data);
  },

  // 检查并解锁成就
  checkAchievements: async (saveId: string): Promise<CheckAchievementsResponse> => {
    const response = await api.post<{
      new_achievements: string[];
      progress: {
        unlocked_achievements: Array<{ achievement_id: string; unlocked_at: string }>;
        progress_map: Record<string, number>;
        new_achievements: string[];
        total_unlocked: number;
        total_achievements: number;
      };
    }>(`/${saveId}/check`);
    return {
      newAchievements: response.data.new_achievements,
      progress: transformProgress(response.data.progress),
    };
  },

  // 清除新成就标记
  clearNewAchievements: async (saveId: string): Promise<string[]> => {
    const response = await api.post<{ cleared_achievements: string[] }>(`/${saveId}/clear-new`);
    return response.data.cleared_achievements;
  },
};

export default achievementApi;
