/**
 * 账户摘要组件 - 紧凑显示在顶部栏
 */
import { Popover, Space } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined } from '@ant-design/icons';
import type { Account } from '../types';

interface AccountSummaryProps {
  account: Account | null;
  initialCash: number;
}

export default function AccountSummary({ account, initialCash }: AccountSummaryProps) {
  if (!account) {
    return (
      <div style={{ fontSize: 13 }}>
        <WalletOutlined /> 加载中...
      </div>
    );
  }

  const profitLoss = account.totalAssets - initialCash;
  const profitLossPct = initialCash > 0 ? (profitLoss / initialCash) * 100 : 0;
  const isProfit = profitLoss >= 0;

  const content = (
    <div style={{ minWidth: 200 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 4 }}>
        <span>总资产:</span>
        <span style={{ fontWeight: 600 }}>¥{account.totalAssets.toFixed(2)}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 4 }}>
        <span>可用现金:</span>
        <span>¥{account.cash.toFixed(2)}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 4 }}>
        <span>持仓市值:</span>
        <span>¥{account.totalMarketValue.toFixed(2)}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--ant-color-border)' }}>
        <span>盈亏:</span>
        <span style={{ color: isProfit ? '#f85149' : '#3fb950', fontWeight: 600 }}>
          {isProfit ? '+' : ''}{profitLoss.toFixed(2)} ({isProfit ? '+' : ''}{profitLossPct.toFixed(2)}%)
        </span>
      </div>
    </div>
  );

  return (
    <Popover 
      content={content}
      title="💰 账户详情"
      placement="bottomRight"
      trigger="hover"
    >
      <Space size={16} style={{ cursor: 'pointer', padding: '4px 12px', borderRadius: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <WalletOutlined />
          <span style={{ fontSize: 12 }}>总资产</span>
          <span style={{ fontWeight: 600, fontSize: 14 }}>
            ¥{account.totalAssets.toFixed(0)}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {isProfit ? (
            <ArrowUpOutlined style={{ color: '#f85149', fontSize: 12 }} />
          ) : (
            <ArrowDownOutlined style={{ color: '#3fb950', fontSize: 12 }} />
          )}
          <span style={{ 
            color: isProfit ? '#f85149' : '#3fb950', 
            fontWeight: 600, 
            fontSize: 13 
          }}>
            {isProfit ? '+' : ''}{profitLossPct.toFixed(2)}%
          </span>
        </div>
      </Space>
    </Popover>
  );
}
