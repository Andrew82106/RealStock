/**
 * 主页 - 存档列表
 * Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 6.1, 6.2, 16.1, 16.2, 16.5, 16.6
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  List,
  Typography,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  message,
  Empty,
  Spin,
  Popconfirm,
  Tag,
  Tooltip,
  Segmented,
} from 'antd';
import type { Dayjs } from 'dayjs';
import {
  PlusOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  FolderOpenOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  StockOutlined,
  SettingOutlined,
  TrophyOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { saveApi } from '../services/saveApi';
import { challengeApi } from '../services/challengeApi';
import { useTheme } from '../contexts/ThemeContext';
import SettingsModal from '../components/SettingsModal';
import ChallengeSelector from '../components/ChallengeSelector';
import type { SaveMetadata, GameMode, ChallengeConfig } from '../types';

const { Title, Text } = Typography;

interface CreateSaveFormValues {
  name: string;
  initialCash: number;
  startDate: Dayjs;
}

export default function HomePage() {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [saves, setSaves] = useState<SaveMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [form] = Form.useForm<CreateSaveFormValues>();
  
  // 游戏模式相关状态
  const [gameMode, setGameMode] = useState<GameMode>('free');
  const [challenges, setChallenges] = useState<ChallengeConfig[]>([]);
  const [loadingChallenges, setLoadingChallenges] = useState(false);
  const [selectedChallenge, setSelectedChallenge] = useState<ChallengeConfig | null>(null);

  // 加载存档列表
  const loadSaves = useCallback(async () => {
    try {
      setLoading(true);
      const data = await saveApi.listSaves();
      // 按更新时间倒序排列
      data.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
      setSaves(data);
    } catch (error) {
      console.error('Failed to load saves:', error);
      message.error('加载存档列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSaves();
  }, [loadSaves]);

  // 加载挑战列表
  const loadChallenges = useCallback(async () => {
    try {
      setLoadingChallenges(true);
      const data = await challengeApi.getAvailableChallenges();
      setChallenges(data);
    } catch (error) {
      console.error('Failed to load challenges:', error);
      message.error('加载挑战列表失败');
    } finally {
      setLoadingChallenges(false);
    }
  }, []);

  // 当打开创建弹窗且选择挑战模式时加载挑战列表
  useEffect(() => {
    if (createModalVisible && gameMode === 'challenge' && challenges.length === 0) {
      loadChallenges();
    }
  }, [createModalVisible, gameMode, challenges.length, loadChallenges]);

  // 创建新存档
  const handleCreate = async (values: CreateSaveFormValues) => {
    try {
      setCreating(true);
      const startDateStr = values.startDate.format('YYYY-MM-DD');
      const saveData = await saveApi.createSave(values.name, values.initialCash, startDateStr);
      message.success('存档创建成功！');
      setCreateModalVisible(false);
      form.resetFields();
      setGameMode('free');
      setSelectedChallenge(null);
      // 导航到交易页面
      navigate(`/trading/${saveData.id}`);
    } catch (error: unknown) {
      console.error('Failed to create save:', error);
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosError.response?.status === 409) {
          message.error('存档名称已存在，请使用其他名称');
        } else if (axiosError.response?.status === 400) {
          message.error(axiosError.response?.data?.detail || '存档名称无效');
        } else {
          message.error('创建存档失败');
        }
      } else {
        message.error('创建存档失败');
      }
    } finally {
      setCreating(false);
    }
  };

  // 创建挑战存档
  const handleCreateChallenge = async (challenge: ChallengeConfig) => {
    try {
      setCreating(true);
      const result = await challengeApi.createChallenge({
        name: `${challenge.name}_${Date.now()}`,
        challengeId: challenge.id,
      });
      message.success('挑战存档创建成功！');
      setCreateModalVisible(false);
      setGameMode('free');
      setSelectedChallenge(null);
      // 导航到交易页面
      navigate(`/trading/${result.saveId}`);
    } catch (error: unknown) {
      console.error('Failed to create challenge:', error);
      message.error('创建挑战存档失败');
    } finally {
      setCreating(false);
    }
  };

  // 选择挑战
  const handleSelectChallenge = (challenge: ChallengeConfig) => {
    setSelectedChallenge(challenge);
  };

  // 删除存档
  const handleDelete = async (saveId: string) => {
    try {
      setDeleting(saveId);
      await saveApi.deleteSave(saveId);
      message.success('存档已删除');
      setSaves(saves.filter(s => s.id !== saveId));
    } catch (error) {
      console.error('Failed to delete save:', error);
      message.error('删除存档失败');
    } finally {
      setDeleting(null);
    }
  };

  // 加载存档并进入交易页面
  const handleLoadSave = (saveId: string) => {
    navigate(`/trading/${saveId}`);
  };

  // 格式化日期时间
  const formatDateTime = (dateStr: string) => {
    return dayjs(dateStr).format('YYYY-MM-DD HH:mm');
  };

  // 格式化金额
  const formatMoney = (amount: number) => {
    return `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: theme === 'dark' 
        ? 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)'
        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '40px 20px',
    }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        {/* 标题区域 */}
        <div style={{ textAlign: 'center', marginBottom: 32, position: 'relative' }}>
          {/* 设置按钮 */}
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => setSettingsVisible(true)}
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              color: 'rgba(255,255,255,0.8)',
              fontSize: 18,
            }}
          >
            设置
          </Button>
          
          <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>
            🥬 韭菜模拟器
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 16 }}>
            在这里体验股市的酸甜苦辣，成为一棵坚强的韭菜！
          </Text>
        </div>

        {/* 存档列表卡片 */}
        <Card
          title={
            <Space>
              <FolderOpenOutlined />
              <span>我的存档</span>
              <Tag color="blue">{saves.length} 个</Tag>
            </Space>
          }
          extra={
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              新建存档
            </Button>
          }
          style={{ borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.1)' }}
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>加载存档列表...</div>
            </div>
          ) : saves.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="还没有存档，点击右上角按钮创建第一个存档"
              style={{ padding: '60px 0' }}
            />
          ) : (
            <List
              dataSource={saves}
              renderItem={(save) => (
                <List.Item
                  style={{
                    padding: '16px',
                    marginBottom: 12,
                    background: theme === 'dark' ? '#21262d' : '#fafafa',
                    borderRadius: 8,
                    border: theme === 'dark' ? '1px solid #30363d' : '1px solid #f0f0f0',
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = theme === 'dark' ? '#30363d' : '#e6f7ff';
                    e.currentTarget.style.borderColor = theme === 'dark' ? '#58a6ff' : '#91d5ff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = theme === 'dark' ? '#21262d' : '#fafafa';
                    e.currentTarget.style.borderColor = theme === 'dark' ? '#30363d' : '#f0f0f0';
                  }}
                  onClick={() => handleLoadSave(save.id)}
                  actions={[
                    <Tooltip title="进入游戏" key="play">
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLoadSave(save.id);
                        }}
                      >
                        继续
                      </Button>
                    </Tooltip>,
                    <Popconfirm
                      key="delete"
                      title="确定删除此存档？"
                      description="删除后无法恢复，请谨慎操作"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        handleDelete(save.id);
                      }}
                      onCancel={(e) => e?.stopPropagation()}
                      okText="确定删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                    >
                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        loading={deleting === save.id}
                        onClick={(e) => e.stopPropagation()}
                      >
                        删除
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Text strong style={{ fontSize: 16 }}>{save.name}</Text>
                        {save.stockCount > 0 && (
                          <Tag icon={<StockOutlined />} color="green">
                            {save.stockCount} 只股票
                          </Tag>
                        )}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={4} style={{ marginTop: 8 }}>
                        <Space split={<span style={{ color: theme === 'dark' ? '#484f58' : '#d9d9d9' }}>|</span>}>
                          <Tooltip title="当前模拟日期">
                            <Text type="secondary">
                              <ClockCircleOutlined style={{ marginRight: 4 }} />
                              模拟日期: {save.currentDate}
                            </Text>
                          </Tooltip>
                          <Tooltip title="总资产">
                            <Text type="secondary">
                              <DollarOutlined style={{ marginRight: 4 }} />
                              总资产: {formatMoney(save.totalAssets)}
                            </Text>
                          </Tooltip>
                        </Space>
                        <Space split={<span style={{ color: theme === 'dark' ? '#484f58' : '#d9d9d9' }}>|</span>}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            创建: {formatDateTime(save.createdAt)}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            更新: {formatDateTime(save.updatedAt)}
                          </Text>
                        </Space>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </div>

      {/* 创建存档弹窗 */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            <span>创建新存档</span>
          </Space>
        }
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
          setGameMode('free');
          setSelectedChallenge(null);
        }}
        footer={null}
        destroyOnClose
        width={gameMode === 'challenge' ? 700 : 520}
      >
        {/* 游戏模式选择 */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>选择游戏模式</div>
          <Segmented
            block
            value={gameMode}
            onChange={(value) => {
              setGameMode(value as GameMode);
              setSelectedChallenge(null);
            }}
            options={[
              {
                value: 'free',
                label: (
                  <div style={{ padding: '8px 0' }}>
                    <RocketOutlined style={{ marginRight: 8, color: '#3fb950' }} />
                    <span>自由模式</span>
                    <div style={{ fontSize: 11, color: 'var(--ant-color-text-secondary)', marginTop: 4 }}>
                      自定义资金、日期和股票
                    </div>
                  </div>
                ),
              },
              {
                value: 'challenge',
                label: (
                  <div style={{ padding: '8px 0' }}>
                    <TrophyOutlined style={{ marginRight: 8, color: '#f0883e' }} />
                    <span>挑战模式</span>
                    <div style={{ fontSize: 11, color: 'var(--ant-color-text-secondary)', marginTop: 4 }}>
                      固定条件，达成目标
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </div>

        {/* 自由模式表单 */}
        {gameMode === 'free' && (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleCreate}
            initialValues={{ initialCash: 100000, startDate: dayjs().subtract(1, 'year') }}
          >
            <Form.Item
              name="name"
              label="存档名称"
              rules={[
                { required: true, message: '请输入存档名称' },
                { whitespace: true, message: '存档名称不能为空' },
                { max: 50, message: '存档名称不能超过50个字符' },
              ]}
            >
              <Input
                placeholder="例如：我的第一个存档"
                maxLength={50}
                showCount
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

            <Form.Item
              name="startDate"
              label="开始日期"
              rules={[{ required: true, message: '请选择开始日期' }]}
              extra="模拟交易将从此日期开始"
            >
              <DatePicker 
                style={{ width: '100%' }}
                disabledDate={(current) => current && current > dayjs().subtract(1, 'day')}
                placeholder="选择开始日期"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={() => {
                  setCreateModalVisible(false);
                  form.resetFields();
                  setGameMode('free');
                }}>
                  取消
                </Button>
                <Button type="primary" htmlType="submit" loading={creating}>
                  创建并开始
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}

        {/* 挑战模式选择器 */}
        {gameMode === 'challenge' && (
          <div>
            {selectedChallenge ? (
              <div>
                {/* 已选择挑战的确认界面 */}
                <Card
                  style={{ marginBottom: 16 }}
                  title={
                    <Space>
                      <TrophyOutlined style={{ color: '#f0883e' }} />
                      <span>{selectedChallenge.name}</span>
                    </Space>
                  }
                >
                  <p>{selectedChallenge.description}</p>
                  <Space wrap>
                    <Tag color="blue">初始资金: ¥{selectedChallenge.initialCash.toLocaleString()}</Tag>
                    <Tag color="green">目标资产: ¥{selectedChallenge.targetAssets.toLocaleString()}</Tag>
                    <Tag color="orange">
                      目标收益: {((selectedChallenge.targetAssets - selectedChallenge.initialCash) / selectedChallenge.initialCash * 100).toFixed(0)}%
                    </Tag>
                  </Space>
                  <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ant-color-text-secondary)' }}>
                    股票: {selectedChallenge.stockName} ({selectedChallenge.stockCode})
                    <br />
                    时间: {selectedChallenge.startDate} ~ {selectedChallenge.endDate}
                  </div>
                </Card>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setSelectedChallenge(null)}>
                    重新选择
                  </Button>
                  <Button 
                    type="primary" 
                    loading={creating}
                    onClick={() => handleCreateChallenge(selectedChallenge)}
                  >
                    开始挑战
                  </Button>
                </Space>
              </div>
            ) : (
              <ChallengeSelector
                challenges={challenges}
                loading={loadingChallenges}
                onSelect={handleSelectChallenge}
              />
            )}
          </div>
        )}
      </Modal>

      {/* 设置弹窗 */}
      <SettingsModal
        open={settingsVisible}
        onClose={() => setSettingsVisible(false)}
      />
    </div>
  );
}
