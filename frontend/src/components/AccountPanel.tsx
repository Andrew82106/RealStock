/**
 * 账户信息面板 - 优化样式
 */
import { Card, Statistic, Row, Col } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined, StockOutlined } from '@ant-design/icons';
import type { Account } from '../types';

interface AccountPanelProps {
  account: Account | null;
  initialCash: number;
}

export default function AccountPanel({ account, initialCash }: AccountPanelProps) {
  if (!account) {
    return <Card loading style={{ borderRadius: 8 }} />;
  }

  const profitLoss = account.totalAssets - initialCash;
  const profitLossPct = initialCash > 0 ? (profitLoss / initialCash) * 100 : 0;
  const isProfit = profitLoss >= 0;

  return (
    <Card 
      title={<span>💰 账户概览</span>}
      size="small"
      style={{ 
        borderRadius: 8, 
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
      headStyle={{
        background: 'linear-gradient(90deg, #f6f8fc 0%, #fff 100%)',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Statistic
            title={<span style={{ color: '#666' }}>总资产</span>}
            value={account.totalAssets}
            precision={2}
            prefix="¥"
            valueStyle={{ fontSize: 22, fontWeight: 600, color: '#1a1a2e' }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={<span style={{ color: '#666' }}>收益率</span>}
            value={profitLossPct}
            precision={2}
            prefix={isProfit ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            suffix="%"
            valueStyle={{ 
              fontSize: 22,
              fontWeight: 600,
              color: isProfit ? '#cf1322' : '#3f8600',
            }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={<span style={{ color: '#999' }}><WalletOutlined /> 可用现金</span>}
            value={account.cash}
            precision={2}
            prefix="¥"
            valueStyle={{ fontSize: 16, color: '#666' }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={<span style={{ color: '#999' }}><StockOutlined /> 持仓市值</span>}
            value={account.totalMarketValue}
            precision={2}
            prefix="¥"
            valueStyle={{ fontSize: 16, color: '#666' }}
          />
        </Col>
      </Row>
    </Card>
  );
}