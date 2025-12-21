/**
 * 挂单列表组件
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Table, Button, Tag, Empty, message, Popconfirm } from 'antd';
import { DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { gameApi } from '../services/api';
import type { PendingOrder, StockInfo } from '../types';

interface PendingOrderListProps {
  sessionId: string | null;
  stockInfoMap: Record<string, StockInfo>;
  onOrderCancelled?: () => void;
}

export default function PendingOrderList({
  sessionId,
  stockInfoMap,
  onOrderCancelled,
}: PendingOrderListProps) {
  const [orders, setOrders] = useState<PendingOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [cancelling, setCancelling] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  const fetchOrders = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await gameApi.getPendingOrders(sessionId);
      setOrders(data);
    } catch (error) {
      console.error('Failed to fetch pending orders:', error);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    // 防止 StrictMode 重复调用
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    
    fetchOrders();
    // 每10秒刷新一次（减少频率）
    const interval = setInterval(fetchOrders, 10000);
    return () => {
      clearInterval(interval);
      fetchedRef.current = false;
    };
  }, [fetchOrders]);

  const handleCancel = async (orderId: string) => {
    if (!sessionId) return;
    setCancelling(orderId);
    try {
      const result = await gameApi.cancelOrder(sessionId, orderId);
      if (result.success) {
        message.success('撤单成功');
        fetchOrders();
        onOrderCancelled?.();
      } else {
        message.error(result.message || '撤单失败');
      }
    } catch (error) {
      message.error('撤单失败');
    } finally {
      setCancelling(null);
    }
  };

  const columns = [
    {
      title: '股票',
      dataIndex: 'code',
      key: 'code',
      width: 80,
      ellipsis: true,
      render: (code: string) => (
        <div>
          <div>{code}</div>
          {stockInfoMap[code]?.name && (
            <div style={{ fontSize: 11, opacity: 0.7 }}>
              {stockInfoMap[code].name}
            </div>
          )}
        </div>
      ),
    },
    {
      title: '方向',
      dataIndex: 'orderType',
      key: 'orderType',
      width: 50,
      render: (type: string) => (
        <Tag color={type === 'buy' ? 'red' : 'green'} style={{ margin: 0 }}>
          {type === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '委托价',
      dataIndex: 'price',
      key: 'price',
      width: 70,
      render: (price: number) => `¥${price.toFixed(2)}`,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 50,
      render: (qty: number) => `${qty}股`,
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      render: (_: unknown, record: PendingOrder) => (
        <Popconfirm
          title="确定要撤销这个挂单吗？"
          onConfirm={() => handleCancel(record.orderId)}
          okText="确定"
          cancelText="取消"
        >
          <Button
            type="link"
            danger
            size="small"
            icon={<DeleteOutlined />}
            loading={cancelling === record.orderId}
          >
            撤单
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card
      title="📋 挂单记录"
      size="small"
      style={{
        borderRadius: 8,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
      styles={{
        body: {
          flex: 1,
          overflow: 'auto',
          padding: orders.length === 0 ? undefined : '8px 12px',
        },
      }}
      extra={
        <Button
          type="text"
          icon={<ReloadOutlined />}
          onClick={fetchOrders}
          loading={loading}
        />
      }
    >
      {orders.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无挂单"
          style={{ padding: '20px 0' }}
        />
      ) : (
        <Table
          dataSource={orders}
          columns={columns}
          rowKey="orderId"
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          style={{ fontSize: 12 }}
        />
      )}
    </Card>
  );
}
