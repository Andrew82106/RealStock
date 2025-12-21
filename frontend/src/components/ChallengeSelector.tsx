/**
 * 挑战选择组件
 * Requirements: 16.1, 16.2, 17.1, 17.2
 */
import { Card, Row, Col, Tag, Button, Empty, Spin } from 'antd';
import { 
  TrophyOutlined, 
  AimOutlined,
  CalendarOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import type { ChallengeConfig, ChallengeDifficulty } from '../types';

interface ChallengeSelectorProps {
  challenges: ChallengeConfig[];
  loading?: boolean;
  onSelect: (challenge: ChallengeConfig) => void;
}

// 难度配置
const difficultyConfig: Record<ChallengeDifficulty, { 
  label: string; 
  color: string; 
  bgColor: string;
}> = {
  easy: { label: '简单', color: '#3fb950', bgColor: 'rgba(63, 185, 80, 0.1)' },
  medium: { label: '中等', color: '#f0883e', bgColor: 'rgba(240, 136, 62, 0.1)' },
  hard: { label: '困难', color: '#f85149', bgColor: 'rgba(248, 81, 73, 0.1)' },
};

export default function ChallengeSelector({ 
  challenges, 
  loading,
  onSelect 
}: ChallengeSelectorProps) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (challenges.length === 0) {
    return <Empty description="暂无可用挑战" />;
  }

  // 按难度分组
  const groupedChallenges = challenges.reduce((acc, challenge) => {
    if (!acc[challenge.difficulty]) {
      acc[challenge.difficulty] = [];
    }
    acc[challenge.difficulty].push(challenge);
    return acc;
  }, {} as Record<ChallengeDifficulty, ChallengeConfig[]>);

  return (
    <div>
      {(['easy', 'medium', 'hard'] as ChallengeDifficulty[]).map(difficulty => {
        const config = difficultyConfig[difficulty];
        const items = groupedChallenges[difficulty] || [];
        
        if (items.length === 0) return null;

        return (
          <div key={difficulty} style={{ marginBottom: 24 }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8, 
              marginBottom: 12,
              paddingBottom: 8,
              borderBottom: `2px solid ${config.color}`,
            }}>
              <TrophyOutlined style={{ color: config.color }} />
              <span style={{ fontWeight: 600, color: config.color }}>
                {config.label}难度
              </span>
              <Tag color={config.color}>{items.length} 个挑战</Tag>
            </div>

            <Row gutter={[16, 16]}>
              {items.map(challenge => (
                <Col span={12} key={challenge.id}>
                  <Card
                    hoverable
                    style={{ 
                      background: config.bgColor,
                      borderColor: config.color,
                    }}
                    onClick={() => onSelect(challenge)}
                  >
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ 
                        fontWeight: 600, 
                        fontSize: 16,
                        marginBottom: 4,
                      }}>
                        {challenge.name}
                      </div>
                      <div style={{ 
                        fontSize: 12, 
                        color: 'var(--ant-color-text-secondary)',
                      }}>
                        {challenge.description}
                      </div>
                    </div>

                    <div style={{ 
                      display: 'flex', 
                      flexWrap: 'wrap',
                      gap: 8,
                      fontSize: 12,
                    }}>
                      <Tag icon={<DollarOutlined />}>
                        目标: ¥{challenge.targetAssets.toLocaleString()}
                      </Tag>
                      <Tag icon={<AimOutlined />}>
                        收益率: {((challenge.targetAssets - challenge.initialCash) / challenge.initialCash * 100).toFixed(0)}%
                      </Tag>
                      <Tag icon={<CalendarOutlined />}>
                        {challenge.startDate} ~ {challenge.endDate}
                      </Tag>
                    </div>

                    <div style={{ 
                      marginTop: 12,
                      fontSize: 12,
                      color: 'var(--ant-color-text-secondary)',
                    }}>
                      股票: {challenge.stockName} ({challenge.stockCode})
                    </div>

                    <Button 
                      type="primary" 
                      block 
                      style={{ marginTop: 12 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(challenge);
                      }}
                    >
                      开始挑战
                    </Button>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        );
      })}
    </div>
  );
}
