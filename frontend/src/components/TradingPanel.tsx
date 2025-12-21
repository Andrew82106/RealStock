/**
 * 交易面板组件 - 支持主题切换
 */
import { useState, useEffect } from 'react';
import { Card, Tabs, InputNumber, Button, Space, Typography, Alert, Divider } from 'antd';
import { ShoppingCartOutlined, DollarOutlined, CloseOutlined } from '@ant-design/icons';
import { useTheme } from '../contexts/ThemeContext';
import type { Position } from '../types';

const { Text } = Typography;

interface TradingPanelProps {
  stockCode: string;
  currentPrice: number;
  cash: number;
  position?: Position;
  disabled: boolean;
  isTodayBought?: boolean;
  onBuy: (price: number, quantity: number) => Promise<void>;
  onSell: (price: number, quantity: number) => Promise<void>;
  onClose?: () => void;
}

export default function TradingPanel({
  stockCode,
  currentPrice,
  cash,
  position,
  disabled,
  isTodayBought = false,
  onBuy,
  onSell,
  onClose,
}: TradingPanelProps) {
  const { theme } = useTheme();
  const [buyPrice, setBuyPrice] = useState(currentPrice);
  const [buyQuantity, setBuyQuantity] = useState(100);
  const [sellPrice, setSellPrice] = useState(currentPrice);
  const [sellQuantity, setSellQuantity] = useState(100);
  const [loading, setLoading] = useState(false);

  const colors = {
    cardBg: theme === 'dark' ? '#21262d' : '#fff',
    headerBg: theme === 'dark' ? '#161b22' : 'linear-gradient(90deg, #f6f8fc 0%, #fff 100%)',
    border: theme === 'dark' ? '#30363d' : '#f0f0f0',
    buyBg: theme === 'dark' ? 'rgba(207, 19, 34, 0.15)' : '#fff7f7',
    buyBorder: theme === 'dark' ? 'rgba(207, 19, 34, 0.3)' : '#ffccc7',
    sellBg: theme === 'dark' ? 'rgba(63, 134, 0, 0.15)' : '#f6ffed',
    sellBorder: theme === 'dark' ? 'rgba(63, 134, 0, 0.3)' : '#b7eb8f',
  };

  useEffect(() => {
    setBuyPrice(currentPrice);
    setSellPrice(currentPrice);
  }, [currentPrice]);

  const calculateBuyFee = (price: number, qty: number) => {
    const amount = price * qty;
    return Math.max(amount * 0.00025, 5);
  };

  const calculateSellFee = (price: number, qty: number) => {
    const amount = price * qty;
    const commission = Math.max(amount * 0.00025, 5);
    const stampTax = amount * 0.0005;
    return commission + stampTax;
  };

  const maxBuyQuantity = Math.floor(cash / (buyPrice * 1.001) / 100) * 100;

  const handleBuy = async () => {
    setLoading(true);
    try { await onBuy(buyPrice, buyQuantity); } finally { setLoading(false); }
  };

  const handleSell = async () => {
    setLoading(true);
    try { await onSell(sellPrice, sellQuantity); } finally { setLoading(false); }
  };

  const buyAmount = buyPrice * buyQuantity;
  const buyFee = calculateBuyFee(buyPrice, buyQuantity);
  const buyTotal = buyAmount + buyFee;

  const sellAmount = sellPrice * sellQuantity;
  const sellFee = calculateSellFee(sellPrice, sellQuantity);
  const sellTotal = sellAmount - sellFee;

  const items = [
    {
      key: 'buy',
      label: <span style={{ color: '#cf1322', fontWeight: 500 }}><ShoppingCartOutlined /> 买入</span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">股票代码</Text>
            <Text strong style={{ fontSize: 16, color: '#1890ff' }}>{stockCode || '-'}</Text>
          </div>
          
          <div>
            <Text type="secondary">委托价格</Text>
            <InputNumber
              value={buyPrice}
              onChange={(v) => setBuyPrice(v || 0)}
              min={0.01}
              step={0.01}
              precision={2}
              style={{ width: '100%', marginTop: 4 }}
              disabled={disabled}
              size="large"
            />
          </div>

          <div>
            <Text type="secondary">委托数量（股）</Text>
            <InputNumber
              value={buyQuantity}
              onChange={(v) => setBuyQuantity(v || 100)}
              min={100}
              step={100}
              style={{ width: '100%', marginTop: 4 }}
              disabled={disabled}
              size="large"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>最大可买: {maxBuyQuantity} 股</Text>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <div style={{ background: colors.buyBg, padding: 12, borderRadius: 8, border: `1px solid ${colors.buyBorder}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">金额</Text>
              <Text>¥{buyAmount.toFixed(2)}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">手续费</Text>
              <Text>¥{buyFee.toFixed(2)}</Text>
            </div>
            <Divider style={{ margin: '8px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text strong>总计</Text>
              <Text strong style={{ color: '#cf1322', fontSize: 16 }}>¥{buyTotal.toFixed(2)}</Text>
            </div>
          </div>

          <Button
            type="primary"
            danger
            block
            size="large"
            onClick={handleBuy}
            loading={loading}
            disabled={disabled || !stockCode || buyQuantity <= 0}
            style={{ height: 44, fontSize: 16 }}
          >
            确认买入
          </Button>
        </Space>
      ),
    },
    {
      key: 'sell',
      label: <span style={{ color: '#3f8600', fontWeight: 500 }}><DollarOutlined /> 卖出</span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">股票代码</Text>
            <Text strong style={{ fontSize: 16, color: '#1890ff' }}>{stockCode || '-'}</Text>
          </div>

          {isTodayBought && position && (
            <Alert
              message="T+1限制：今日买入的股票需要下一个交易日才能卖出"
              type="warning"
              showIcon
              style={{ borderRadius: 6 }}
            />
          )}

          <div>
            <Text type="secondary">委托价格</Text>
            <InputNumber
              value={sellPrice}
              onChange={(v) => setSellPrice(v || 0)}
              min={0.01}
              step={0.01}
              precision={2}
              style={{ width: '100%', marginTop: 4 }}
              disabled={disabled || isTodayBought}
              size="large"
            />
          </div>

          <div>
            <Text type="secondary">委托数量（股）</Text>
            <InputNumber
              value={sellQuantity}
              onChange={(v) => setSellQuantity(v || 100)}
              min={100}
              step={100}
              max={isTodayBought ? 0 : (position?.quantity || 0)}
              style={{ width: '100%', marginTop: 4 }}
              disabled={disabled || isTodayBought}
              size="large"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              可卖: {isTodayBought ? 0 : (position?.quantity || 0)} 股
              {isTodayBought && <span style={{ color: '#faad14' }}> (T+1限制)</span>}
            </Text>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <div style={{ background: colors.sellBg, padding: 12, borderRadius: 8, border: `1px solid ${colors.sellBorder}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">金额</Text>
              <Text>¥{sellAmount.toFixed(2)}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">手续费</Text>
              <Text>¥{sellFee.toFixed(2)}</Text>
            </div>
            <Divider style={{ margin: '8px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text strong>到账</Text>
              <Text strong style={{ color: '#3f8600', fontSize: 16 }}>¥{sellTotal.toFixed(2)}</Text>
            </div>
          </div>

          <Button
            type="primary"
            block
            size="large"
            onClick={handleSell}
            loading={loading}
            disabled={disabled || !stockCode || !position || sellQuantity <= 0 || isTodayBought}
            style={{ height: 44, fontSize: 16, background: '#52c41a', borderColor: '#52c41a' }}
          >
            确认卖出
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card 
      title={<span>💹 交易</span>}
      size="small"
      style={{ 
        borderRadius: 8, 
        boxShadow: theme === 'dark' ? '0 2px 8px rgba(0,0,0,0.3)' : '0 2px 8px rgba(0,0,0,0.08)',
        background: colors.cardBg,
      }}
      styles={{
        header: {
          background: colors.headerBg,
          borderBottom: `1px solid ${colors.border}`,
        },
        body: {
          background: colors.cardBg,
        },
      }}
      extra={onClose && (
        <Button 
          type="text" 
          icon={<CloseOutlined />} 
          onClick={onClose}
          size="small"
        />
      )}
    >
      {disabled && (
        <Alert
          message="请先暂停播放再进行交易"
          type="warning"
          showIcon
          style={{ marginBottom: 12, borderRadius: 6 }}
        />
      )}
      <Tabs items={items} />
    </Card>
  );
}
