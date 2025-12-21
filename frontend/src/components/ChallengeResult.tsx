/**
 * 挑战结果组件
 * Requirements: 18.2, 18.3, 18.4
 */
import { Modal, Result, Statistic, Row, Col, Button } from 'antd';
import { 
  TrophyOutlined, 
  CloseCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useEffect, useState } from 'react';
import type { ChallengeResult as ChallengeResultType, ChallengeConfig } from '../types';

interface ChallengeResultProps {
  open: boolean;
  result: ChallengeResultType | null;
  config: ChallengeConfig | null;
  onClose: () => void;
  onRetry?: () => void;
  onNewChallenge?: () => void;
}

export default function ChallengeResultModal({ 
  open,
  result, 
  config,
  onClose,
  onRetry,
  onNewChallenge,
}: ChallengeResultProps) {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    if (open && result?.passed) {
      setShowConfetti(true);
      const timer = setTimeout(() => setShowConfetti(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [open, result?.passed]);

  if (!result || !config) {
    return null;
  }

  const profit = result.finalAssets - config.initialCash;
  const targetProfit = config.targetAssets - config.initialCash;
  const achievementRate = (profit / targetProfit) * 100;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={500}
      centered
    >
      {/* 简单的庆祝效果 */}
      {showConfetti && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          overflow: 'hidden',
        }}>
          {Array.from({ length: 50 }).map((_, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${Math.random() * 100}%`,
                top: -20,
                width: 10,
                height: 10,
                background: ['#f85149', '#3fb950', '#f0883e', '#58a6ff', '#a371f7'][Math.floor(Math.random() * 5)],
                borderRadius: '50%',
                animation: `fall ${2 + Math.random() * 2}s linear forwards`,
                animationDelay: `${Math.random() * 2}s`,
              }}
            />
          ))}
          <style>{`
            @keyframes fall {
              to {
                transform: translateY(600px) rotate(720deg);
                opacity: 0;
              }
            }
          `}</style>
        </div>
      )}

      <Result
        icon={result.passed ? (
          <TrophyOutlined style={{ color: '#f0883e', fontSize: 72 }} />
        ) : (
          <CloseCircleOutlined style={{ color: '#f85149', fontSize: 72 }} />
        )}
        status={result.passed ? 'success' : 'error'}
        title={result.passed ? '🎉 挑战成功！' : '挑战失败'}
        subTitle={result.passed 
          ? `恭喜你完成了 ${config.name}！` 
          : `很遗憾，未能达成目标。再接再厉！`
        }
      >
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Statistic
              title="最终资产"
              value={result.finalAssets}
              precision={2}
              prefix="¥"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="目标资产"
              value={result.targetAssets}
              precision={2}
              prefix="¥"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Statistic
              title="收益率"
              value={result.returnPct}
              precision={2}
              suffix="%"
              prefix={result.returnPct >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
              valueStyle={{ 
                fontSize: 20,
                color: result.returnPct >= 0 ? '#f85149' : '#3fb950',
              }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="目标完成度"
              value={achievementRate}
              precision={1}
              suffix="%"
              valueStyle={{ 
                fontSize: 20,
                color: achievementRate >= 100 ? '#3fb950' : '#f0883e',
              }}
            />
          </Col>
        </Row>

        <div style={{ 
          display: 'flex', 
          gap: 12, 
          justifyContent: 'center',
          marginTop: 24,
        }}>
          {!result.passed && onRetry && (
            <Button type="primary" onClick={onRetry}>
              重新挑战
            </Button>
          )}
          {onNewChallenge && (
            <Button onClick={onNewChallenge}>
              选择其他挑战
            </Button>
          )}
          <Button onClick={onClose}>
            关闭
          </Button>
        </div>
      </Result>
    </Modal>
  );
}
