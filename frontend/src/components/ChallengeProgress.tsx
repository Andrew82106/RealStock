/**
 * 挑战进度组件
 * Requirements: 17.3
 * 
 * 直接使用实时数据渲染，不依赖 API 返回的进度数据
 */
import { useMemo } from 'react';
import { Card, Progress, Statistic, Row, Col, Tag } from 'antd';
import { 
  AimOutlined, 
  ClockCircleOutlined,
  DollarOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import type { ChallengeConfig, ChallengeDifficulty } from '../types';

interface ChallengeProgressProps {
  config: ChallengeConfig | null;
  currentAssets: number;  // 实时总资产
  currentDate: string;    // 实时当前日期
  loading?: boolean;
}

// 难度配置
const difficultyConfig: Record<ChallengeDifficulty, { 
  label: string; 
  color: string;
}> = {
  easy: { label: '简单', color: '#3fb950' },
  medium: { label: '中等', color: '#f0883e' },
  hard: { label: '困难', color: '#f85149' },
};

export default function ChallengeProgressComponent({ 
  config,
  currentAssets,
  currentDate,
  loading 
}: ChallengeProgressProps) {
  // 实时计算进度数据
  const progressData = useMemo(() => {
    if (!config) return null;
    
    const targetAssets = config.targetAssets;
    const initialCash = config.initialCash;
    
    // 计算进度百分比
    let progressPct = 0;
    if (targetAssets > initialCash) {
      progressPct = ((currentAssets - initialCash) / (targetAssets - initialCash)) * 100;
    } else if (currentAssets >= targetAssets) {
      progressPct = 100;
    }
    progressPct = Math.max(0, Math.min(100, progressPct));
    
    // 计算剩余天数（交易日）- 使用当前日期或开始日期
    const dateToUse = currentDate || config.startDate;
    const current = new Date(dateToUse);
    const end = new Date(config.endDate);
    const daysRemaining = Math.max(0, Math.ceil((end.getTime() - current.getTime()) / (1000 * 60 * 60 * 24)));
    
    return {
      currentAssets,
      targetAssets,
      progressPct,
      daysRemaining,
    };
  }, [config, currentAssets, currentDate]);

  if (!config || !progressData) {
    return null;
  }

  const difficulty = difficultyConfig[config.difficulty];
  const isOnTrack = progressData.progressPct >= (100 - progressData.daysRemaining * 2); // 简单的进度判断

  return (
    <Card
      size="small"
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrophyOutlined style={{ color: difficulty.color }} />
          <span>挑战进度</span>
          <Tag color={difficulty.color}>{difficulty.label}</Tag>
        </div>
      }
      loading={loading}
      style={{ marginBottom: 16 }}
    >
      {/* 进度条 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          marginBottom: 4,
          fontSize: 12,
        }}>
          <span>当前资产: ¥{progressData.currentAssets.toLocaleString()}</span>
          <span>目标: ¥{progressData.targetAssets.toLocaleString()}</span>
        </div>
        <Progress
          percent={progressData.progressPct}
          strokeColor={{
            '0%': '#3fb950',
            '50%': '#f0883e',
            '100%': '#f85149',
          }}
          format={(pct) => `${pct?.toFixed(1)}%`}
        />
      </div>

      {/* 统计数据 */}
      <Row gutter={16}>
        <Col span={8}>
          <Statistic
            title={<><ClockCircleOutlined /> 剩余天数</>}
            value={progressData.daysRemaining}
            suffix="天"
            valueStyle={{ 
              fontSize: 18,
              color: progressData.daysRemaining <= 5 ? '#f85149' : undefined,
            }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<><DollarOutlined /> 还需盈利</>}
            value={Math.max(0, progressData.targetAssets - progressData.currentAssets)}
            precision={0}
            prefix="¥"
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<><AimOutlined /> 状态</>}
            value={isOnTrack ? '进度正常' : '需要加油'}
            valueStyle={{ 
              fontSize: 14,
              color: isOnTrack ? '#3fb950' : '#f0883e',
            }}
          />
        </Col>
      </Row>

      {/* 挑战信息 */}
      <div style={{ 
        marginTop: 12, 
        paddingTop: 12, 
        borderTop: '1px solid var(--ant-color-border)',
        fontSize: 12,
        color: 'var(--ant-color-text-secondary)',
      }}>
        <div>{config.name}: {config.description}</div>
        <div style={{ marginTop: 4 }}>
          股票: {config.stockName} ({config.stockCode}) | 
          初始资金: ¥{config.initialCash.toLocaleString()}
        </div>
      </div>
    </Card>
  );
}
