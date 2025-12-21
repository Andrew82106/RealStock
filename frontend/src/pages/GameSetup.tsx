/**
 * 游戏设置页面 - 带搜索历史和进度条
 */
import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  DatePicker,
  InputNumber,
  Button,
  message,
  Space,
  Typography,
  Input,
  List,
  Tag,
  Progress,
  Divider,
  Empty,
  Popconfirm,
} from 'antd';
import { 
  PlayCircleOutlined, 
  SearchOutlined, 
  HistoryOutlined,
  DeleteOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { stockApi, gameApi } from '../services/api';
import { 
  getSearchHistory, 
  addToSearchHistory, 
  removeFromSearchHistory,
  clearSearchHistory,
  type CachedStock,
} from '../services/stockCache';
import type { StockInfo } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

interface FormValues {
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  initialCash: number;
}

interface SearchTask {
  id: string;
  keyword: string;
  progress: number;
  message: string;
  status: 'searching' | 'done' | 'error';
  results?: StockInfo[];
}

export default function GameSetup() {
  const navigate = useNavigate();
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedStocks, setSelectedStocks] = useState<StockInfo[]>([]);
  const [searchHistory, setSearchHistory] = useState<CachedStock[]>([]);
  const [searchTasks, setSearchTasks] = useState<SearchTask[]>([]);
  const cancelFnRef = useRef<(() => void) | null>(null);

  // 加载搜索历史
  useEffect(() => {
    setSearchHistory(getSearchHistory());
  }, []);

  // 搜索股票 - 使用SSE流式搜索
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

    setSearchTasks(prev => [newTask, ...prev.filter(t => t.status !== 'searching')]);

    const cancel = stockApi.searchStockStream(
      searchKeyword,
      // onProgress
      (progress, msg) => {
        setSearchTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, progress, message: msg } : t
        ));
      },
      // onResult
      (stocks) => {
        setSearchTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, results: stocks } : t
        ));
      },
      // onError
      (error) => {
        setSearchTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'error', message: error } : t
        ));
        message.error(error);
      },
      // onDone
      () => {
        setSearchTasks(prev => prev.map(t => 
          t.id === taskId ? { ...t, status: 'done' } : t
        ));
      }
    );

    cancelFnRef.current = cancel;
  };

  // 添加股票
  const handleAddStock = (stock: StockInfo) => {
    if (selectedStocks.find(s => s.code === stock.code)) {
      message.warning('该股票已添加');
      return;
    }
    setSelectedStocks([...selectedStocks, stock]);
    // 添加到搜索历史
    addToSearchHistory(stock);
    setSearchHistory(getSearchHistory());
  };

  // 从历史记录添加
  const handleAddFromHistory = (stock: CachedStock) => {
    handleAddStock({ code: stock.code, name: stock.name, market: stock.market });
  };

  // 移除股票
  const handleRemoveStock = (code: string) => {
    setSelectedStocks(selectedStocks.filter(s => s.code !== code));
  };

  // 删除历史记录
  const handleRemoveHistory = (code: string) => {
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
    setSearchTasks(prev => prev.filter(t => t.id !== taskId));
  };

  // 开始游戏
  const handleSubmit = async (values: FormValues) => {
    if (selectedStocks.length === 0) {
      message.error('请至少选择一只股票');
      return;
    }

    setLoading(true);
    try {
      const response = await gameApi.startGame({
        stock_codes: selectedStocks.map(s => s.code),
        start_date: values.dateRange[0].format('YYYY-MM-DD'),
        end_date: values.dateRange[1].format('YYYY-MM-DD'),
        initial_cash: values.initialCash,
      });
      
      message.success('游戏初始化成功！');
      navigate(`/trading/${response.session_id}`);
    } catch (error) {
      message.error('游戏初始化失败，请重试');
      console.error('开始游戏失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#f0f2f5', 
      padding: '40px 20px',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'flex-start',
    }}>
      <Card 
        style={{ width: '100%', maxWidth: 800 }}
        title={
          <Space>
            <PlayCircleOutlined style={{ fontSize: 24, color: '#1890ff' }} />
            <Title level={3} style={{ margin: 0 }}>A股模拟交易游戏</Title>
          </Space>
        }
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
          选择股票和时间范围，开始你的模拟交易之旅
        </Text>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            initialCash: 100000,
            dateRange: [dayjs().subtract(6, 'month'), dayjs().subtract(1, 'day')],
          }}
        >
          {/* 股票搜索 */}
          <Form.Item label="搜索股票">
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="输入股票代码或名称，如：600519 或 茅台"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onPressEnter={handleSearch}
                style={{ flex: 1 }}
              />
              <Button 
                type="primary" 
                icon={<SearchOutlined />}
                onClick={handleSearch}
              >
                搜索
              </Button>
            </Space.Compact>
          </Form.Item>

          {/* 搜索任务列表 */}
          {searchTasks.length > 0 && (
            <Form.Item label="搜索任务">
              <div style={{ 
                border: '1px solid #d9d9d9', 
                borderRadius: 6,
                padding: 12,
                maxHeight: 300,
                overflow: 'auto',
              }}>
                {searchTasks.map(task => (
                  <div key={task.id} style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
                      status={task.status === 'error' ? 'exception' : task.status === 'done' ? 'success' : 'active'}
                      size="small"
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>{task.message}</Text>
                    
                    {/* 搜索结果 */}
                    {task.status === 'done' && task.results && task.results.length > 0 && (
                      <div style={{ 
                        marginTop: 8, 
                        maxHeight: 150, 
                        overflow: 'auto',
                        background: '#fafafa',
                        borderRadius: 4,
                        padding: 8,
                      }}>
                        <List
                          size="small"
                          dataSource={task.results}
                          renderItem={(stock) => (
                            <List.Item
                              style={{ cursor: 'pointer', padding: '4px 8px' }}
                              onClick={() => handleAddStock(stock)}
                            >
                              <span style={{ fontWeight: 500 }}>{stock.code}</span>
                              <span style={{ marginLeft: 8, color: '#666' }}>{stock.name}</span>
                              <Tag color="blue" style={{ marginLeft: 'auto' }}>{stock.market}</Tag>
                            </List.Item>
                          )}
                        />
                      </div>
                    )}
                    {task.status === 'done' && task.results && task.results.length === 0 && (
                      <Text type="secondary" style={{ fontSize: 12 }}>未找到匹配的股票</Text>
                    )}
                  </div>
                ))}
              </div>
            </Form.Item>
          )}

          {/* 搜索历史 */}
          {searchHistory.length > 0 && (
            <Form.Item 
              label={
                <Space>
                  <HistoryOutlined />
                  <span>搜索历史（点击添加）</span>
                  <Popconfirm
                    title="确定清空所有历史记录？"
                    onConfirm={handleClearHistory}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button type="link" size="small" icon={<ClearOutlined />}>
                      清空
                    </Button>
                  </Popconfirm>
                </Space>
              }
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {searchHistory.map((stock) => (
                  <Tag
                    key={stock.code}
                    style={{ cursor: 'pointer', padding: '4px 8px' }}
                    onClick={() => handleAddFromHistory(stock)}
                    closable
                    onClose={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleRemoveHistory(stock.code);
                    }}
                  >
                    {stock.code} - {stock.name}
                  </Tag>
                ))}
              </div>
            </Form.Item>
          )}

          <Divider />

          {/* 已选股票 */}
          <Form.Item 
            label={`已选股票 (${selectedStocks.length})`}
            required
          >
            {selectedStocks.length === 0 ? (
              <Empty 
                description="请搜索并添加股票，或从历史记录中选择" 
                style={{ 
                  padding: 24, 
                  border: '1px dashed #d9d9d9',
                  borderRadius: 6,
                }}
              />
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {selectedStocks.map((stock) => (
                  <Tag
                    key={stock.code}
                    color="blue"
                    closable
                    onClose={() => handleRemoveStock(stock.code)}
                    style={{ padding: '4px 8px', fontSize: 14 }}
                  >
                    {stock.code} - {stock.name}
                  </Tag>
                ))}
              </div>
            )}
          </Form.Item>

          <Form.Item
            name="dateRange"
            label="回测时间范围"
            rules={[{ required: true, message: '请选择时间范围' }]}
          >
            <RangePicker 
              style={{ width: '100%' }} 
              format="YYYY-MM-DD"
            />
          </Form.Item>

          <Form.Item
            name="initialCash"
            label="初始资金（元）"
            rules={[{ required: true, message: '请输入初始资金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={100}
              max={100000000}
              step={100}
              formatter={(value) => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number(value?.replace(/¥\s?|(,*)/g, '') || 0) as 100}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              size="large"
              block
              icon={<PlayCircleOutlined />}
              disabled={selectedStocks.length === 0}
            >
              开始游戏
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
