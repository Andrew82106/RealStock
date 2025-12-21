/**
 * 成就弹窗组件
 * Requirements: 10.5, 13.1-13.6, 15.2, 15.4
 */
import { useState, useMemo } from 'react';
import { Modal, Tabs, Progress, Select, Empty, Spin, Badge, Row, Col, Statistic } from 'antd';
import { TrophyOutlined, FilterOutlined } from '@ant-design/icons';
import AchievementCard from './AchievementCard';
import type { 
  AchievementDefinition, 
  AchievementProgress, 
  AchievementCategory,
  AchievementRarity,
} from '../types';

interface AchievementModalProps {
  open: boolean;
  onClose: () => void;
  definitions: AchievementDefinition[];
  progress: AchievementProgress | null;
  loading?: boolean;
}

// 分类配置
const categoryConfig: Record<AchievementCategory, { label: string; icon: string }> = {
  trading: { label: '交易', icon: '📊' },
  profit: { label: '收益', icon: '💰' },
  milestone: { label: '里程碑', icon: '🏆' },
  streak: { label: '连续', icon: '🔥' },
  t_trade: { label: '做T', icon: '⚡' },
  special: { label: '特殊', icon: '✨' },
  challenge: { label: '挑战', icon: '🎯' },
};

// 稀有度配置
const rarityConfig: Record<AchievementRarity, { label: string; color: string }> = {
  common: { label: '普通', color: '#8b949e' },
  rare: { label: '稀有', color: '#58a6ff' },
  epic: { label: '史诗', color: '#a371f7' },
  legendary: { label: '传说', color: '#f0883e' },
};

type FilterStatus = 'all' | 'unlocked' | 'locked';

export default function AchievementModal({
  open,
  onClose,
  definitions,
  progress,
  loading,
}: AchievementModalProps) {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [filterRarity, setFilterRarity] = useState<AchievementRarity | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  // 计算统计数据
  const stats = useMemo(() => {
    if (!progress) return null;

    const unlockedIds = new Set(progress.unlockedAchievements.map(a => a.achievementId));
    const total = definitions.length;
    const unlocked = progress.unlockedAchievements.length;

    // 按分类统计
    const byCategory: Record<string, { total: number; unlocked: number }> = {};
    definitions.forEach(d => {
      if (!byCategory[d.category]) {
        byCategory[d.category] = { total: 0, unlocked: 0 };
      }
      byCategory[d.category].total++;
      if (unlockedIds.has(d.id)) {
        byCategory[d.category].unlocked++;
      }
    });

    // 按稀有度统计
    const byRarity: Record<string, { total: number; unlocked: number }> = {};
    definitions.forEach(d => {
      if (!byRarity[d.rarity]) {
        byRarity[d.rarity] = { total: 0, unlocked: 0 };
      }
      byRarity[d.rarity].total++;
      if (unlockedIds.has(d.id)) {
        byRarity[d.rarity].unlocked++;
      }
    });

    return { total, unlocked, byCategory, byRarity };
  }, [definitions, progress]);

  // 过滤成就列表
  const filteredAchievements = useMemo(() => {
    if (!progress) return [];

    const unlockedIds = new Set(progress.unlockedAchievements.map(a => a.achievementId));
    const newIds = new Set(progress.newAchievements);

    return definitions
      .filter(d => {
        // 分类过滤
        if (activeCategory !== 'all' && d.category !== activeCategory) return false;
        // 稀有度过滤
        if (filterRarity !== 'all' && d.rarity !== filterRarity) return false;
        // 状态过滤
        if (filterStatus === 'unlocked' && !unlockedIds.has(d.id)) return false;
        if (filterStatus === 'locked' && unlockedIds.has(d.id)) return false;
        return true;
      })
      .map(d => ({
        definition: d,
        isUnlocked: unlockedIds.has(d.id),
        isNew: newIds.has(d.id),
        progress: progress.progressMap[d.id] || 0,
        unlockedAt: progress.unlockedAchievements.find(a => a.achievementId === d.id)?.unlockedAt,
      }))
      .sort((a, b) => {
        // 新成就优先
        if (a.isNew && !b.isNew) return -1;
        if (!a.isNew && b.isNew) return 1;
        // 已解锁优先
        if (a.isUnlocked && !b.isUnlocked) return -1;
        if (!a.isUnlocked && b.isUnlocked) return 1;
        // 按进度排序
        return b.progress - a.progress;
      });
  }, [definitions, progress, activeCategory, filterRarity, filterStatus]);

  // 分类标签页
  const categoryTabs = [
    { key: 'all', label: '全部' },
    ...Object.entries(categoryConfig).map(([key, config]) => ({
      key,
      label: (
        <span>
          {config.icon} {config.label}
          {stats && (
            <span style={{ marginLeft: 4, fontSize: 11, opacity: 0.7 }}>
              ({stats.byCategory[key]?.unlocked || 0}/{stats.byCategory[key]?.total || 0})
            </span>
          )}
        </span>
      ),
    })),
  ];

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrophyOutlined style={{ color: '#f0883e' }} />
          <span>成就</span>
          {stats && (
            <Badge 
              count={`${stats.unlocked}/${stats.total}`} 
              style={{ backgroundColor: '#3fb950' }}
            />
          )}
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
      styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* 统计概览 */}
          {stats && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Statistic 
                  title="完成进度" 
                  value={stats.unlocked} 
                  suffix={`/ ${stats.total}`}
                  valueStyle={{ fontSize: 20 }}
                />
                <Progress 
                  percent={Math.round((stats.unlocked / stats.total) * 100)} 
                  size="small"
                  strokeColor="#3fb950"
                />
              </Col>
              {Object.entries(rarityConfig).map(([rarity, config]) => (
                <Col span={4} key={rarity}>
                  <Statistic
                    title={config.label}
                    value={stats.byRarity[rarity]?.unlocked || 0}
                    suffix={`/ ${stats.byRarity[rarity]?.total || 0}`}
                    valueStyle={{ fontSize: 16, color: config.color }}
                  />
                </Col>
              ))}
            </Row>
          )}

          {/* 过滤器 */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Select
              value={filterRarity}
              onChange={setFilterRarity}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部稀有度' },
                ...Object.entries(rarityConfig).map(([value, config]) => ({
                  value,
                  label: config.label,
                })),
              ]}
              prefix={<FilterOutlined />}
            />
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部状态' },
                { value: 'unlocked', label: '已解锁' },
                { value: 'locked', label: '未解锁' },
              ]}
            />
          </div>

          {/* 分类标签页 */}
          <Tabs
            activeKey={activeCategory}
            onChange={setActiveCategory}
            items={categoryTabs}
            size="small"
          />

          {/* 成就列表 */}
          {filteredAchievements.length === 0 ? (
            <Empty description="没有找到成就" />
          ) : (
            <Row gutter={[12, 12]}>
              {filteredAchievements.map(item => (
                <Col span={12} key={item.definition.id}>
                  <AchievementCard
                    definition={item.definition}
                    isUnlocked={item.isUnlocked}
                    progress={item.progress}
                    unlockedAt={item.unlockedAt}
                    isNew={item.isNew}
                  />
                </Col>
              ))}
            </Row>
          )}
        </>
      )}
    </Modal>
  );
}
