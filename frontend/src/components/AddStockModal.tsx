/**
 * 添加股票弹窗组件
 * Requirements: 5.1, 5.2, 5.5
 */
import { useState, useRef, useEffect } from 'react';
import {
  Modal,
  Input,
  List,
  Tag,
  Progress,
  Typography,
  Space,
  Empty,
  message,
  Button,
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  HistoryOutlined,
  DeleteOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { stockApi } from '../services/api';
import {
  getSearchHistory,
  addToSearchHistory,
  removeFromSearchHistory,
  clearSearchHistory,
  type CachedStock,
} from '../services/stockCache';
import type { StockInfo } from '../types';

const { Text } = Typography;

interface SearchTask {
  id: string;
  keyword: string;
  progress: number;
  message: string;
  status: 'searching' | 'done' | 'error';
  results?: StockInfo[];
}

interface AddStockModalProps {
  open: boolean;
  onClose: () => void;
  onAddStock: (stockCode: string) => Promise<void>;
  existingStocks: string[];
}

export default function AddStockModal({
  open,
  onClose,
  onAddStock,
  existingStocks,
}: AddStockModalProps) {
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchHistory, setSearchHistory] = useState<CachedStock[]>([]);
  const [searchTasks, setSearchTasks] = useState<SearchTask[]>([]);
  const [adding, setAdding] = useState<string | null>(null);
  const cancelFnRef = useRef<(() => void) | null>(null);

  // 加载搜索历史
  useEffect(() => {
    if (open) {
      setSearchHistory(getSearchHistory());
    }
  }, [open]);

  // 关闭时清理
  useEffect(() => {
    return () => {
      if (cancelFnRef.current) {
        cancelFnRef.current();
      }
    };
  }, []);

  // 搜索股票
  const handleSearch = () => {
    if (!searchKeyword || searchKeyword.length < 2) {
      message.warning('请输入至少2个字符');
      return;
    }

    // 取消之前的搜索
    if (cancelFnRef.current) {
      cancelFnRef.current();
    }

    const taskId = Date.now().toString();
    const newTask: SearchTask = {
      id: taskId,
      keyword: searchKeyword,
      progress: 0,
      message: '准备搜索...',
      status: 'searching',
    };

    setSearchTasks((prev) => [newTask, ...prev.filter((t) => t.status !== 'searching')]);

    const cancel = stockApi.searchStockStream(
      searchKeyword,
      // onProgress
      (progress, msg) => {
        setSearchTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, progress, message: msg } : t))
        );
      },
      // onResult
      (stocks) => {
        setSearchTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, results: stocks } : t))
        );
      },
      // onError
      (error) => {
        setSearchTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: 'error', message: error } : t))
        );
        message.error(error);
      },
      // onDone
      () => {
        setSearchTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, status: 'done' } : t))
        );
      }
    );

    cancelFnRef.current = cancel;
  };

  // 添加股票
  const handleAddStock = async (stock: StockInfo) => {
    if (existingStocks.includes(stock.code)) {
      message.warning('该股票已在列表中');
      return;
    }

    setAdding(stock.code);
    try {
      await onAddStock(stock.code);
      // 添加到搜索历史
      addToSearchHistory(stock);
      setSearchHistory(getSearchHistory());
      message.success(`已添加股票 ${stock.code}`);
    } catch (error) {
      console.error('Failed to add stock:', error);
      message.error('添加股票失败');
    } finally {
      setAdding(null);
    }
  };

  // 从历史记录添加
  const handleAddFromHistory = async (stock: CachedStock) => {
    await handleAddStock({ code: stock.code, name: stock.name, market: stock.market });
  };

  // 删除历史记录
  const handleRemoveHistory = (code: string, e: React.MouseEvent) => {
    e.stopPropagation();
    removeFromSearchHistory(code);
    setSearchHistory(getSearchHistory());
  };

  // 清空历史记录
  const handleClearHistory = () => {
    clearSearchHistory();
    setSearchHistory([]);
  };

  // 移除搜索任务
  const handleRemoveTask = (taskId: string) => {
    setSearchTasks((prev) => prev.filter((t) => t.id !== taskId));
  };

  // 检查股票是否已存在
  const isStockExists = (code: string) => existingStocks.includes(code);

  return (
    <Modal
      title={
        <Space>
          <PlusOutlined />
          <span>添加股票</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
      styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
    >
      {/* 搜索框 */}
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Input
          placeholder="输入股票代码或名称，如：600519 或 茅台"
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
          allowClear
        />
        <Button type="primary" onClick={handleSearch}>
          搜索
        </Button>
      </Space.Compact>

      {/* 搜索任务列表 */}
      {searchTasks.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
            搜索结果
          </Text>
          <div
            style={{
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              padding: 12,
              maxHeight: 300,
              overflow: 'auto',
            }}
          >
            {searchTasks.map((task) => (
              <div key={task.id} style={{ marginBottom: 16 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Text strong>搜索: {task.keyword}</Text>
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemoveTask(task.id)}
                  />
                </div>
                <Progress
                  percent={task.progress}
                  status={
                    task.status === 'error'
                      ? 'exception'
                      : task.status === 'done'
                      ? 'success'
                      : 'active'
                  }
                  size="small"
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {task.message}
                </Text>

                {/* 搜索结果 */}
                {task.status === 'done' && task.results && task.results.length > 0 && (
                  <div
                    style={{
                      marginTop: 8,
                      maxHeight: 200,
                      overflow: 'auto',
                      background: '#fafafa',
                      borderRadius: 4,
                    }}
                  >
                    <List
                      size="small"
                      dataSource={task.results}
                      renderItem={(stock) => {
                        const exists = isStockExists(stock.code);
                        return (
                          <List.Item
                            style={{
                              cursor: exists ? 'not-allowed' : 'pointer',
                              padding: '8px 12px',
                              opacity: exists ? 0.5 : 1,
                            }}
                            onClick={() => !exists && handleAddStock(stock)}
                          >
                            <Space>
                              <Text strong>{stock.code}</Text>
                              <Text type="secondary">{stock.name}</Text>
                              <Tag color="blue">{stock.market}</Tag>
                            </Space>
                            {exists ? (
                              <Tag color="default">已添加</Tag>
                            ) : (
                              <Button
                                type="link"
                                size="small"
                                icon={<PlusOutlined />}
                                loading={adding === stock.code}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAddStock(stock);
                                }}
                              >
                                添加
                              </Button>
                            )}
                          </List.Item>
                        );
                      }}
                    />
                  </div>
                )}
                {task.status === 'done' && task.results && task.results.length === 0 && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    未找到匹配的股票
                  </Text>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 搜索历史 */}
      {searchHistory.length > 0 && (
        <div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 8,
            }}
          >
            <Space>
              <HistoryOutlined />
              <Text type="secondary">搜索历史（点击添加）</Text>
            </Space>
            <Button
              type="link"
              size="small"
              icon={<ClearOutlined />}
              onClick={handleClearHistory}
            >
              清空
            </Button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {searchHistory.map((stock) => {
              const exists = isStockExists(stock.code);
              return (
                <Tag
                  key={stock.code}
                  style={{
                    cursor: exists ? 'not-allowed' : 'pointer',
                    padding: '4px 8px',
                    opacity: exists ? 0.5 : 1,
                  }}
                  color={exists ? 'default' : undefined}
                  onClick={() => !exists && handleAddFromHistory(stock)}
                  closable={!exists}
                  onClose={(e) => handleRemoveHistory(stock.code, e as React.MouseEvent)}
                >
                  {stock.code} - {stock.name}
                  {exists && ' (已添加)'}
                </Tag>
              );
            })}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {searchTasks.length === 0 && searchHistory.length === 0 && (
        <Empty
          description="搜索股票代码或名称来添加到投资组合"
          style={{ padding: '40px 0' }}
        />
      )}
    </Modal>
  );
}
