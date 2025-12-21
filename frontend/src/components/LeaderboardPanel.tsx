/**
 * 排行榜面板组件
 * Requirements: 12.7, 12.8, 12.9, 20.1-20.6
 */
import { Card, Table, Tabs, Tag, Empty, Spin, Avatar } from 'antd';
import { 
  TrophyOutlined, 
  CrownOutlined,
  StarOutlined,
} from '@ant-design/icons';
import type { LeaderboardEntry, LeaderboardType } from '../types';

interface LeaderboardPanelProps {
  leaderboards: Record<LeaderboardType, LeaderboardEntry[]> | null;
  loading?: boolean;
  currentSaveId?: string;
}

// 排行榜类型配置
const leaderboardConfig: Record<LeaderboardType, { 
  label: string; 
  icon: string;
  format: (value: number) => string;
}> = {
  total_assets: { 
    label: '总资产', 
    icon: '💰',
    format: (v) => `¥${v.toLocaleString()}`,
  },
  total_return: { 
    label: '收益率', 
    icon: '📈',
    format: (v) => `${v.toFixed(2)}%`,
  },
  achievement_count: { 
    label: '成就数', 
    icon: '🏆',
    format: (v) => `${v} 个`,
  },
  t_trade_profit: { 
    label: '做T收益', 
    icon: '⚡',
    format: (v) => `¥${v.toLocaleString()}`,
  },
  win_rate: { 
    label: '胜率', 
    icon: '🎯',
    format: (v) => `${v.toFixed(1)}%`,
  },
  trade_count: { 
    label: '交易次数', 
    icon: '📊',
    format: (v) => `${v} 次`,
  },
};

// 排名图标
const getRankIcon = (rank: number) => {
  switch (rank) {
    case 1:
      return <CrownOutlined style={{ color: '#f0883e', fontSize: 18 }} />;
    case 2:
      return <CrownOutlined style={{ color: '#8b949e', fontSize: 16 }} />;
    case 3:
      return <CrownOutlined style={{ color: '#cd7f32', fontSize: 14 }} />;
    default:
      return <span style={{ color: 'var(--ant-color-text-secondary)' }}>{rank}</span>;
  }
};

export default function LeaderboardPanel({ 
  leaderboards, 
  loading,
  currentSaveId: _currentSaveId,
}: LeaderboardPanelProps) {
  if (loading) {
    return (
      <Card title={<><TrophyOutlined /> 排行榜</>}>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (!leaderboards) {
    return (
      <Card title={<><TrophyOutlined /> 排行榜</>}>
        <Empty description="暂无排行榜数据" />
      </Card>
    );
  }

  const columns = (type: LeaderboardType) => [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 60,
      render: (rank: number) => getRankIcon(rank),
    },
    {
      title: '存档',
      dataIndex: 'saveName',
      key: 'saveName',
      render: (name: string, record: LeaderboardEntry) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Avatar size="small" style={{ background: record.isCurrent ? '#3fb950' : '#21262d' }}>
            {name.charAt(0).toUpperCase()}
          </Avatar>
          <span style={{ fontWeight: record.isCurrent ? 600 : 400 }}>
            {name}
            {record.isCurrent && <Tag color="green" style={{ marginLeft: 4 }}>当前</Tag>}
          </span>
        </div>
      ),
    },
    {
      title: leaderboardConfig[type].label,
      dataIndex: 'value',
      key: 'value',
      width: 120,
      render: (value: number) => (
        <span style={{ fontWeight: 600 }}>
          {leaderboardConfig[type].format(value)}
        </span>
      ),
    },
    {
      title: '成就',
      dataIndex: 'achievementCount',
      key: 'achievementCount',
      width: 60,
      render: (count: number) => (
        <Tag icon={<StarOutlined />} color="gold">
          {count}
        </Tag>
      ),
    },
  ];

  const tabItems = Object.entries(leaderboardConfig).map(([type, config]) => ({
    key: type,
    label: (
      <span>
        {config.icon} {config.label}
      </span>
    ),
    children: (
      <Table
        dataSource={leaderboards[type as LeaderboardType] || []}
        columns={columns(type as LeaderboardType)}
        rowKey="saveId"
        size="small"
        pagination={false}
        rowClassName={(record) => record.isCurrent ? 'current-row' : ''}
      />
    ),
  }));

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrophyOutlined style={{ color: '#f0883e' }} />
          <span>排行榜</span>
        </div>
      }
    >
      <Tabs items={tabItems} size="small" />
      
      <style>{`
        .current-row {
          background: rgba(63, 185, 80, 0.1) !important;
        }
      `}</style>
    </Card>
  );
}
