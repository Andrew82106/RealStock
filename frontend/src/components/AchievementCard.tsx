/**
 * 成就卡片组件
 * Requirements: 10.1, 10.2, 10.3, 10.4, 15.5
 */
import { Card, Progress, Tag, Tooltip } from 'antd';
import { 
  TrophyOutlined, 
  LockOutlined, 
  CheckCircleOutlined,
  StarOutlined,
  CrownOutlined,
  FireOutlined,
} from '@ant-design/icons';
import type { AchievementDefinition, AchievementRarity } from '../types';

interface AchievementCardProps {
  definition: AchievementDefinition;
  isUnlocked: boolean;
  progress: number;
  unlockedAt?: string;
  isNew?: boolean;
  onClick?: () => void;
}

// 稀有度颜色配置
const rarityConfig: Record<AchievementRarity, { color: string; bgColor: string; label: string; icon: React.ReactNode }> = {
  common: { color: '#8b949e', bgColor: '#21262d', label: '普通', icon: <StarOutlined /> },
  rare: { color: '#58a6ff', bgColor: '#1f3a5f', label: '稀有', icon: <TrophyOutlined /> },
  epic: { color: '#a371f7', bgColor: '#3d2a5f', label: '史诗', icon: <FireOutlined /> },
  legendary: { color: '#f0883e', bgColor: '#5f3a1f', label: '传说', icon: <CrownOutlined /> },
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

export default function AchievementCard({
  definition,
  isUnlocked,
  progress,
  unlockedAt,
  isNew,
  onClick,
}: AchievementCardProps) {
  const rarity = rarityConfig[definition.rarity];
  const progressPct = definition.targetValue > 0 
    ? Math.min(100, (progress / definition.targetValue) * 100) 
    : 0;

  return (
    <Card
      size="small"
      hoverable
      onClick={onClick}
      style={{
        opacity: isUnlocked ? 1 : 0.7,
        borderColor: isUnlocked ? rarity.color : undefined,
        background: isUnlocked ? rarity.bgColor : undefined,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 新成就标记 */}
      {isNew && (
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          background: '#f85149',
          color: 'white',
          padding: '2px 8px',
          fontSize: 10,
          fontWeight: 600,
        }}>
          NEW
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        {/* 图标 */}
        <div style={{
          fontSize: 32,
          width: 48,
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 8,
          background: isUnlocked ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.2)',
          filter: isUnlocked ? 'none' : 'grayscale(100%)',
        }}>
          {categoryIcons[definition.category] || definition.icon}
        </div>

        {/* 内容 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ 
              fontWeight: 600, 
              fontSize: 14,
              color: isUnlocked ? rarity.color : undefined,
            }}>
              {definition.name}
            </span>
            <Tag 
              color={rarity.color} 
              style={{ 
                fontSize: 10, 
                padding: '0 4px',
                margin: 0,
              }}
            >
              {rarity.icon} {rarity.label}
            </Tag>
          </div>

          <div style={{ 
            fontSize: 12, 
            color: 'var(--ant-color-text-secondary)',
            marginBottom: 8,
          }}>
            {definition.description}
          </div>

          {/* 进度条 */}
          {!isUnlocked && definition.progressType !== 'boolean' && (
            <Tooltip title={`${progress} / ${definition.targetValue}`}>
              <Progress 
                percent={progressPct} 
                size="small" 
                showInfo={false}
                strokeColor={rarity.color}
              />
            </Tooltip>
          )}

          {/* 解锁状态 */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 4,
            fontSize: 11,
            color: 'var(--ant-color-text-tertiary)',
          }}>
            {isUnlocked ? (
              <>
                <CheckCircleOutlined style={{ color: '#3fb950' }} />
                <span>已解锁 {unlockedAt ? `· ${new Date(unlockedAt).toLocaleDateString()}` : ''}</span>
              </>
            ) : (
              <>
                <LockOutlined />
                <span>
                  {definition.progressType === 'boolean' 
                    ? '未解锁' 
                    : `${progress} / ${definition.targetValue}`}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
