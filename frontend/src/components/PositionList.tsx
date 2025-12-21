/**
 * 持仓列表组件 - 优化样式
 */
import { Card, Table, Empty, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Position } from '../types';

interface PositionListProps {
  positions: Position[];
  onSelect: (code: string) => void;
}

export default function PositionList({ positions, onSelect }: PositionListProps) {
  const columns: ColumnsType<Position> = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 90,
      render: (code: string) => <Tag color="blue">{code}</Tag>,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 70,
      align: 'right',
      render: (v: number) => <span style={{ fontWeight: 500 }}>{v}</span>,
    },
    {
      title: '成本',
      dataIndex: 'costPrice',
      key: 'costPrice',
      width: 80,
      align: 'right',
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '现价',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      width: 80,
      align: 'right',
      render: (v: number, record: Position) => {
        const isUp = v >= record.costPrice;
        return <span style={{ color: isUp ? '#cf1322' : '#3f8600', fontWeight: 500 }}>{v.toFixed(2)}</span>;
      },
    },
    {
      title: '盈亏',
      dataIndex: 'profitLoss',
      key: 'profitLoss',
      width: 100,
      align: 'right',
      render: (v: number, record: Position) => {
        const color = v >= 0 ? '#cf1322' : '#3f8600';
        const pct = (record.profitLossPct * 100).toFixed(2);
        return (
          <div style={{ color, fontWeight: 500 }}>
            <div>{v >= 0 ? '+' : ''}{v.toFixed(2)}</div>
            <div style={{ fontSize: 12 }}>({v >= 0 ? '+' : ''}{pct}%)</div>
          </div>
        );
      },
    },
  ];

  return (
    <Card 
      title={<span>📊 持仓列表</span>}
      size="small" 
      bodyStyle={{ padding: 0 }}
      style={{ 
        borderRadius: 8, 
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
      headStyle={{
        background: 'linear-gradient(90deg, #f6f8fc 0%, #fff 100%)',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      {positions.length === 0 ? (
        <Empty 
          description="暂无持仓" 
          style={{ padding: 32 }}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Table
          columns={columns}
          dataSource={positions}
          rowKey="code"
          size="small"
          pagination={false}
          scroll={{ y: 180 }}
          onRow={(record) => ({
            onClick: () => onSelect(record.code),
            style: { cursor: 'pointer' },
          })}
          rowClassName={() => 'position-row'}
        />
      )}
    </Card>
  );
}