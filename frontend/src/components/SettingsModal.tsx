/**
 * 设置弹窗组件 - 主题设置和缓存管理
 */
import { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Radio,
  Space,
  Typography,
  List,
  Button,
  Input,
  message,
  Empty,
  Tag,
  Popconfirm,
} from 'antd';
import {
  SettingOutlined,
  BulbOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  SearchOutlined,
  DownloadOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useTheme } from '../contexts/ThemeContext';
import { stockCache, getSearchHistory, clearSearchHistory } from '../services/stockCache';
import { stockApi } from '../services/api';
import type { StockInfo } from '../types';

const { Text, Title } = Typography;

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const { theme, setTheme } = useTheme();
  const [cachedStocks, setCachedStocks] = useState<Record<string, StockInfo>>({});
  const [searchHistory, setSearchHistory] = useState<Array<{ code: string; name: string }>>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState<StockInfo[]>([]);
  const [searching, setSearching] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  // 加载缓存数据
  useEffect(() => {
    if (open) {
      setCachedStocks(stockCache.getAll());
      setSearchHistory(getSearchHistory());
    }
  }, [open]);

  // 搜索股票
  const handleSearch = async () => {
    if (!searchKeyword || searchKeyword.length < 2) {
      message.warning('请输入至少2个字符');
      return;
    }
    setSearching(true);
    try {
      const results = await stockApi.getStockList(searchKeyword);
      setSearchResults(results);
      if (results.length === 0) {
        message.info('未找到匹配的股票');
      }
    } catch (error) {
      console.error('Search failed:', error);
      message.error('搜索失败');
    } finally {
      setSearching(false);
    }
  };

  // 下载股票信息到缓存
  const handleDownload = async (stock: StockInfo) => {
    setDownloading(stock.code);
    try {
      stockCache.set(stock.code, stock);
      setCachedStocks(stockCache.getAll());
      message.success(`已缓存 ${stock.code} ${stock.name}`);
    } catch (error) {
      console.error('Download failed:', error);
      message.error('缓存失败');
    } finally {
      setDownloading(null);
    }
  };

  // 删除单个缓存
  const handleDeleteCache = (code: string) => {
    const all = stockCache.getAll();
    delete all[code];
    stockCache.clear();
    Object.entries(all).forEach(([k, v]) => stockCache.set(k, v));
    setCachedStocks(stockCache.getAll());
    message.success('已删除');
  };

  // 清空所有缓存
  const handleClearAllCache = () => {
    stockCache.clear();
    setCachedStocks({});
    message.success('已清空所有股票缓存');
  };

  // 清空搜索历史
  const handleClearHistory = () => {
    clearSearchHistory();
    setSearchHistory([]);
    message.success('已清空搜索历史');
  };

  const cachedList = Object.values(cachedStocks);

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          <span>设置</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
      styles={{ body: { padding: '12px 0' } }}
    >
      <Tabs
        items={[
          {
            key: 'theme',
            label: (
              <Space>
                <BulbOutlined />
                主题设置
              </Space>
            ),
            children: (
              <div style={{ padding: '16px 24px' }}>
                <Title level={5} style={{ marginBottom: 16 }}>显示模式</Title>
                <Radio.Group
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  size="large"
                >
                  <Radio.Button value="light">
                    <Space>
                      ☀️ 浅色模式
                    </Space>
                  </Radio.Button>
                  <Radio.Button value="dark">
                    <Space>
                      🌙 深色模式
                    </Space>
                  </Radio.Button>
                </Radio.Group>
                <div style={{ marginTop: 16 }}>
                  <Text type="secondary">
                    {theme === 'light' ? '当前使用浅色主题，适合白天使用' : '当前使用深色主题，适合夜间使用'}
                  </Text>
                </div>
              </div>
            ),
          },
          {
            key: 'cache',
            label: (
              <Space>
                <DatabaseOutlined />
                缓存管理
              </Space>
            ),
            children: (
              <div style={{ padding: '0 24px' }}>
                {/* 搜索并下载 */}
                <div style={{ marginBottom: 20 }}>
                  <Title level={5} style={{ marginBottom: 12 }}>搜索并缓存股票</Title>
                  <Space.Compact style={{ width: '100%' }}>
                    <Input
                      placeholder="输入股票代码或名称"
                      value={searchKeyword}
                      onChange={(e) => setSearchKeyword(e.target.value)}
                      onPressEnter={handleSearch}
                      prefix={<SearchOutlined />}
                      allowClear
                    />
                    <Button type="primary" onClick={handleSearch} loading={searching}>
                      搜索
                    </Button>
                  </Space.Compact>
                  
                  {searchResults.length > 0 && (
                    <div style={{ 
                      marginTop: 12, 
                      maxHeight: 200, 
                      overflow: 'auto',
                      border: '1px solid #d9d9d9',
                      borderRadius: 6,
                    }}>
                      <List
                        size="small"
                        dataSource={searchResults}
                        renderItem={(stock) => {
                          const isCached = !!cachedStocks[stock.code];
                          return (
                            <List.Item
                              style={{ padding: '8px 12px' }}
                              actions={[
                                isCached ? (
                                  <Tag color="green" key="cached">已缓存</Tag>
                                ) : (
                                  <Button
                                    key="download"
                                    type="link"
                                    size="small"
                                    icon={<DownloadOutlined />}
                                    loading={downloading === stock.code}
                                    onClick={() => handleDownload(stock)}
                                  >
                                    缓存
                                  </Button>
                                ),
                              ]}
                            >
                              <Space>
                                <Text strong>{stock.code}</Text>
                                <Text type="secondary">{stock.name}</Text>
                                <Tag color="blue">{stock.market}</Tag>
                              </Space>
                            </List.Item>
                          );
                        }}
                      />
                    </div>
                  )}
                </div>

                {/* 已缓存的股票 */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <Title level={5} style={{ margin: 0 }}>
                      已缓存股票 <Tag color="blue">{cachedList.length}</Tag>
                    </Title>
                    {cachedList.length > 0 && (
                      <Popconfirm
                        title="确定清空所有缓存？"
                        onConfirm={handleClearAllCache}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Button size="small" danger icon={<ClearOutlined />}>
                          清空全部
                        </Button>
                      </Popconfirm>
                    )}
                  </div>
                  
                  {cachedList.length === 0 ? (
                    <Empty description="暂无缓存" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <div style={{ 
                      maxHeight: 200, 
                      overflow: 'auto',
                      border: '1px solid #d9d9d9',
                      borderRadius: 6,
                    }}>
                      <List
                        size="small"
                        dataSource={cachedList}
                        renderItem={(stock) => (
                          <List.Item
                            style={{ padding: '8px 12px' }}
                            actions={[
                              <Button
                                key="delete"
                                type="text"
                                size="small"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={() => handleDeleteCache(stock.code)}
                              />,
                            ]}
                          >
                            <Space>
                              <Text strong>{stock.code}</Text>
                              <Text type="secondary">{stock.name}</Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </div>
                  )}
                </div>

                {/* 搜索历史 */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <Title level={5} style={{ margin: 0 }}>
                      搜索历史 <Tag>{searchHistory.length}</Tag>
                    </Title>
                    {searchHistory.length > 0 && (
                      <Popconfirm
                        title="确定清空搜索历史？"
                        onConfirm={handleClearHistory}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Button size="small" icon={<ClearOutlined />}>
                          清空
                        </Button>
                      </Popconfirm>
                    )}
                  </div>
                  
                  {searchHistory.length === 0 ? (
                    <Empty description="暂无搜索历史" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {searchHistory.map((item) => (
                        <Tag key={item.code}>
                          {item.code} - {item.name}
                        </Tag>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
}
