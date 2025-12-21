/**
 * 做T统计面板组件
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
 */
import { Card, Statistic, Row, Col, Table, Tag, Empty, Progress } from 'antd';
import { 
  ThunderboltOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { TTradeStatistics, TTradeRecord } from '../types';

interface TTradeStatsPanelProps {
  statistics: TTradeStatistics | null;
  trades?: TTradeRecord[];
  loading?: boolean;
}

export default function TTradeStatsPanel({ 
  statistics, 
  trades,
  loading 
}: TTradeStatsPanelProps) {
  if (!statistics) {
    return (
      <Card title={<><ThunderboltOutlined /> 做T统计</>} loading={loading}>
        <Empty description="暂无做T数据" />
      </Card>
    );
  }

  const columns = [
    {
      title: '日期',
      dataIndex: 'tradeDate',
      key: 'tradeDate',
      width: 100,
    },
    {
      title: '股票',
      dataIndex: 'stockCode',
      key: 'stockCode',
      width: 80,
    },
    {
      title: '卖出价',
      dataIndex: 'sellPrice',
      key: 'sellPrice',
      width: 80,
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: '买入价',
      dataIndex: 'buyPrice',
      key: 'buyPrice',
      width: 80,
      render: (v: number) => `¥${v.toFixed(2)}`,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 60,
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      width: 100,
      render: (v: number, record: TTradeRecord) => (
        <span style={{ color: record.isSuccessful ? '#f85149' : '#3fb950' }}>
          {record.isSuccessful ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          {v >= 0 ? '+' : ''}{v.toFixed(2)}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'isSuccessful',
      key: 'isSuccessful',
      width: 60,
      render: (v: boolean) => (
        <Tag color={v ? 'success' : 'error'} icon={v ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
          {v ? '成功' : '失败'}
        </Tag>
      ),
    },
  ];

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ThunderboltOutlined style={{ color: '#f0883e' }} />
          <span>做T统计</span>
          <Tag color="blue">{statistics.totalTrades} 次</Tag>
        </div>
      }
      loading={loading}
    >
      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Statistic
            title="成功率"
            value={statistics.successRate}
            precision={1}
            suffix="%"
            valueStyle={{ 
              color: statistics.successRate >= 50 ? '#3fb950' : '#f85149',
              fontSize: 20,
            }}
          />
          <Progress 
            percent={statistics.successRate} 
            size="small"
            strokeColor={statistics.successRate >= 50 ? '#3fb950' : '#f85149'}
            showInfo={false}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="累计盈亏"
            value={statistics.totalProfit}
            precision={2}
            prefix="¥"
            valueStyle={{ 
              color: statistics.totalProfit >= 0 ? '#f85149' : '#3fb950',
              fontSize: 20,
            }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="成功/失败"
            value={statistics.successfulTrades}
            suffix={`/ ${statistics.failedTrades}`}
            valueStyle={{ fontSize: 20 }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="平均盈亏"
            value={statistics.averageProfit}
            precision={2}
            prefix="¥"
            valueStyle={{ 
              color: statistics.averageProfit >= 0 ? '#f85149' : '#3fb950',
              fontSize: 20,
            }}
          />
        </Col>
      </Row>

      {/* 最佳/最差 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small" style={{ background: 'rgba(248, 81, 73, 0.1)' }}>
            <Statistic
              title="最佳单次做T"
              value={statistics.bestTradeProfit}
              precision={2}
              prefix={<ArrowUpOutlined style={{ color: '#f85149' }} />}
              suffix="元"
              valueStyle={{ color: '#f85149' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" style={{ background: 'rgba(63, 185, 80, 0.1)' }}>
            <Statistic
              title="最差单次做T"
              value={Math.abs(statistics.worstTradeLoss)}
              precision={2}
              prefix={<ArrowDownOutlined style={{ color: '#3fb950' }} />}
              suffix="元"
              valueStyle={{ color: '#3fb950' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 做T历史列表 */}
      {trades && trades.length > 0 && (
        <Table
          dataSource={trades}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 5, size: 'small' }}
          scroll={{ x: 600 }}
        />
      )}
    </Card>
  );
}
