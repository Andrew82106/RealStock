/**
 * 持仓摘要组件 - 下拉显示持仓列表
 */
import { Popover, Button, Empty, Tag } from 'antd';
import { UnorderedListOutlined, CaretDownOutlined } from '@ant-design/icons';
import type { Position } from '../types';

interface PositionSummaryProps {
  positions: Position[];
  onSelect: (code: string) => void;
}

export default function PositionSummary({ positions, onSelect }: PositionSummaryProps) {
  const totalValue = positions.reduce((sum, p) => sum + p.currentPrice * p.quantity, 0);
  const totalProfitLoss = positions.reduce((sum, p) => sum + p.profitLoss, 0);
  const isProfit = totalProfitLoss >= 0;

  const content = (
    <div style={{ 
      minWidth: 320,
      maxHeight: 400,
      overflow: 'auto',
    }}>
      {positions.length === 0 ? (
        <Empty 
          description="暂无持仓"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: 16 }}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {positions.map(p => {
            const isPosProfit = p.profitLoss >= 0;
            return (
              <div 
                key={p.code}
                onClick={() => onSelect(p.code)}
                style={{ 
                  padding: '10px 12px', 
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  border: '1px solid var(--ant-color-border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <Tag color="blue" style={{ margin: 0 }}>{p.code}</Tag>
                  <span style={{ 
                    color: isPosProfit ? '#f85149' : '#3fb950', 
                    fontWeight: 600,
                    fontSize: 14,
                  }}>
                    {isPosProfit ? '+' : ''}{p.profitLoss.toFixed(2)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, opacity: 0.7 }}>
                  <span>数量: {p.quantity}</span>
                  <span>成本: {p.costPrice.toFixed(2)}</span>
                  <span>现价: <span style={{ color: isPosProfit ? '#f85149' : '#3fb950' }}>{p.currentPrice.toFixed(2)}</span></span>
                </div>
                <div style={{ 
                  marginTop: 4, 
                  fontSize: 12, 
                  color: isPosProfit ? '#f85149' : '#3fb950',
                  textAlign: 'right',
                }}>
                  {isPosProfit ? '+' : ''}{(p.profitLossPct * 100).toFixed(2)}%
                </div>
              </div>
            );
          })}
          
          {/* 汇总 */}
          <div style={{ 
            marginTop: 8, 
            paddingTop: 8, 
            borderTop: '1px solid var(--ant-color-border)',
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 13,
          }}>
            <span>持仓市值: ¥{totalValue.toFixed(2)}</span>
            <span style={{ color: isProfit ? '#f85149' : '#3fb950', fontWeight: 600 }}>
              盈亏: {isProfit ? '+' : ''}¥{totalProfitLoss.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <Popover 
      content={content}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>📊 持仓列表</span>
          {positions.length > 0 && (
            <span style={{ fontSize: 12, opacity: 0.7 }}>
              共 {positions.length} 只
            </span>
          )}
        </div>
      }
      trigger="click"
      placement="bottomRight"
    >
      <Button 
        style={{ 
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <UnorderedListOutlined />
        <span>持仓</span>
        {positions.length > 0 && (
          <Tag color={isProfit ? 'red' : 'green'} style={{ margin: 0, marginLeft: 4 }}>
            {positions.length}
          </Tag>
        )}
        <CaretDownOutlined style={{ fontSize: 10 }} />
      </Button>
    </Popover>
  );
}
