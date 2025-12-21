/**
 * 成就解锁通知组件
 * Requirements: 11.1, 11.2, 11.3, 11.4
 */
import { useEffect, useState } from 'react';
import { notification } from 'antd';
import { TrophyOutlined, StarOutlined, FireOutlined, CrownOutlined } from '@ant-design/icons';
import type { AchievementDefinition, AchievementRarity } from '../types';

interface AchievementNotificationProps {
  achievements: AchievementDefinition[];
  onClose?: () => void;
}

// 稀有度配置
const rarityConfig: Record<AchievementRarity, { 
  color: string; 
  bgColor: string; 
  label: string; 
  icon: React.ReactNode;
  duration: number;
}> = {
  common: { 
    color: '#8b949e', 
    bgColor: '#21262d', 
    label: '普通', 
    icon: <StarOutlined />,
    duration: 4,
  },
  rare: { 
    color: '#58a6ff', 
    bgColor: '#1f3a5f', 
    label: '稀有', 
    icon: <TrophyOutlined />,
    duration: 5,
  },
  epic: { 
    color: '#a371f7', 
    bgColor: '#3d2a5f', 
    label: '史诗', 
    icon: <FireOutlined />,
    duration: 6,
  },
  legendary: { 
    color: '#f0883e', 
    bgColor: '#5f3a1f', 
    label: '传说', 
    icon: <CrownOutlined />,
    duration: 8,
  },
};

// 分类图标映射
const categoryIcons: Record<string, string> = {
  trading: '📊',
  profit: '💰',
  milestone: '🏆',
  streak: '🔥',
  t_trade: '⚡',
  special: '✨',
  challenge: '🎯',
};

export function showAchievementNotification(achievement: AchievementDefinition) {
  const rarity = rarityConfig[achievement.rarity];
  
  notification.open({
    message: (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 20 }}>🎉</span>
        <span style={{ fontWeight: 600, color: rarity.color }}>
          成就解锁！
        </span>
      </div>
    ),
    description: (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
        <div style={{
          fontSize: 32,
          width: 48,
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 8,
          background: rarity.bgColor,
        }}>
          {categoryIcons[achievement.category] || achievement.icon}
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: rarity.color }}>
            {achievement.name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--ant-color-text-secondary)' }}>
            {achievement.description}
          </div>
          <div style={{ 
            fontSize: 11, 
            color: rarity.color,
            marginTop: 4,
          }}>
            {rarity.icon} {rarity.label}成就
          </div>
        </div>
      </div>
    ),
    duration: rarity.duration,
    placement: 'topRight',
    style: {
      background: rarity.bgColor,
      borderLeft: `4px solid ${rarity.color}`,
    },
  });
}

export default function AchievementNotification({ 
  achievements, 
  onClose 
}: AchievementNotificationProps) {
  const [shown, setShown] = useState<Set<string>>(new Set());

  useEffect(() => {
    // 显示新成就通知
    achievements.forEach((achievement, index) => {
      if (!shown.has(achievement.id)) {
        // 延迟显示，避免同时弹出太多
        setTimeout(() => {
          showAchievementNotification(achievement);
        }, index * 500);
        
        setShown(prev => new Set([...prev, achievement.id]));
      }
    });

    // 所有通知显示完后调用 onClose
    if (achievements.length > 0 && onClose) {
      const totalDelay = achievements.length * 500 + 1000;
      const timer = setTimeout(onClose, totalDelay);
      return () => clearTimeout(timer);
    }
  }, [achievements, shown, onClose]);

  return null; // 这个组件不渲染任何内容，只负责显示通知
}
