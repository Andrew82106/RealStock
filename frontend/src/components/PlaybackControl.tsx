/**
 * 播放控制组件 - 支持自动播放
 */
import { Button, Slider, Space, Typography, Tag, Tooltip, Switch } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepForwardOutlined,
  ThunderboltOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { GameState } from '../types';

const { Text } = Typography;

interface PlaybackControlProps {
  state: GameState | null;
  speed: number;
  autoPlay: boolean;
  onPlay: () => void;
  onPause: () => void;
  onSpeedChange: (speed: number) => void;
  onNextDay: () => void;
  onAutoPlayChange: (enabled: boolean) => void;
}

const stateLabels: Record<string, { text: string; color: string; icon: string }> = {
  idle: { text: '等待开始', color: 'default', icon: '⏸️' },
  playing: { text: '播放中', color: 'processing', icon: '▶️' },
  paused: { text: '已暂停', color: 'warning', icon: '⏸️' },
  day_ended: { text: '当日结束', color: 'success', icon: '✅' },
  finished: { text: '已完成', color: 'default', icon: '🏁' },
};

export default function PlaybackControl({
  state,
  speed,
  autoPlay,
  onPlay,
  onPause,
  onSpeedChange,
  onNextDay,
  onAutoPlayChange,
}: PlaybackControlProps) {
  if (!state) {
    return <div style={{ padding: 12 }}>加载中...</div>;
  }

  const playbackState = state.playbackState;
  const stateInfo = stateLabels[playbackState] || stateLabels.idle;
  const canPlay = playbackState === 'idle' || playbackState === 'paused';
  const canPause = playbackState === 'playing';
  const canNextDay = playbackState === 'day_ended';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      {/* 状态显示 */}
      <Space size="small">
        <Text type="secondary">状态</Text>
        <Tag color={stateInfo.color} style={{ fontSize: 13, padding: '2px 10px' }}>
          {stateInfo.icon} {stateInfo.text}
        </Tag>
      </Space>

      {/* 日期显示 */}
      <Space size="small">
        <Text type="secondary">📅 日期</Text>
        <Text strong style={{ fontSize: 15 }}>{state.currentDate}</Text>
      </Space>

      {/* 播放控制按钮 */}
      <Space size="small">
        <Tooltip title="开始播放行情">
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={onPlay}
            disabled={!canPlay}
            style={{ 
              background: canPlay ? 'linear-gradient(90deg, #52c41a 0%, #73d13d 100%)' : undefined,
              borderColor: canPlay ? '#52c41a' : undefined,
            }}
          >
            播放
          </Button>
        </Tooltip>
        <Tooltip title="暂停播放">
          <Button
            icon={<PauseCircleOutlined />}
            onClick={onPause}
            disabled={!canPause}
            style={{
              background: canPause ? '#faad14' : undefined,
              borderColor: canPause ? '#faad14' : undefined,
              color: canPause ? '#fff' : undefined,
            }}
          >
            暂停
          </Button>
        </Tooltip>
        <Tooltip title="进入下一个交易日">
          <Button
            icon={<StepForwardOutlined />}
            onClick={onNextDay}
            disabled={!canNextDay}
            type={canNextDay ? 'primary' : 'default'}
          >
            下一交易日
          </Button>
        </Tooltip>
      </Space>

      {/* 速度控制 */}
      <Space size="small" style={{ minWidth: 200 }}>
        <ThunderboltOutlined style={{ color: '#faad14' }} />
        <Text type="secondary">速度</Text>
        <Slider
          value={speed}
          onChange={onSpeedChange}
          min={0.1}
          max={10}
          step={0.1}
          style={{ width: 100 }}
          tooltip={{ formatter: (v) => `${v}x` }}
        />
        <Tag color="blue">{speed}x</Tag>
      </Space>

      {/* 自动播放开关 */}
      <Tooltip title="开启后，当天结束会自动进入下一交易日并继续播放">
        <Space size="small">
          <RocketOutlined style={{ color: autoPlay ? '#1890ff' : undefined }} />
          <Text type="secondary">自动播放</Text>
          <Switch 
            size="small" 
            checked={autoPlay} 
            onChange={onAutoPlayChange}
          />
        </Space>
      </Tooltip>

      {/* 最后一天提示 */}
      {state.isLastDay && (
        <Tag color="red" style={{ fontSize: 13 }}>🚨 最后一个交易日</Tag>
      )}
    </div>
  );
}