/**
 * 交易主界面 - 支持存档系统
 * Requirements: 2.5, 3.2, 3.3, 4.2, 4.3, 4.4, 5.1, 5.2, 5.5, 15.1, 15.2, 15.3, 17.3
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Row, Col, message, Spin, Button, Tooltip, Badge, Segmented, Empty } from 'antd';
import { HomeOutlined, SwapOutlined, LineChartOutlined, FundOutlined, PlusOutlined, TrophyOutlined } from '@ant-design/icons';
import { gameApi, stockApi } from '../services/api';
import { saveApi } from '../services/saveApi';
import { achievementApi } from '../services/achievementApi';
import { challengeApi } from '../services/challengeApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { useTheme } from '../contexts/ThemeContext';
import StockChart from '../components/StockChart';
import IntradayChart from '../components/IntradayChart';
import AccountSummary from '../components/AccountSummary';
import PositionSummary from '../components/PositionSummary';
import TradingPanel from '../components/TradingPanel';
import PlaybackControl from '../components/PlaybackControl';
import AssetChart from '../components/AssetChart';
import AddStockModal from '../components/AddStockModal';
import PendingOrderList from '../components/PendingOrderList';
import AchievementModal from '../components/AchievementModal';
import AchievementNotification, { showAchievementNotification } from '../components/AchievementNotification';
import ChallengeProgressComponent from '../components/ChallengeProgress';
import ChallengeResultModal from '../components/ChallengeResult';
import type { 
  GameState, Account, DailyBar, TickData, AccountUpdateData, 
  StateUpdateData, DailySnapshot, ExtendedSaveData, StockInfo, SaveTradeRecord,
  AchievementDefinition, AchievementProgress, ChallengeProgress, ChallengeConfig
} from '../types';
import { stockCache } from '../services/stockCache';

const { Header, Content } = Layout;

export default function TradingView() {
  const { sessionId: urlId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { theme } = useTheme();
  
  // 主题相关样式
  const themeStyles = {
    bg: theme === 'dark' ? '#0d1117' : '#f0f2f5',
    headerBg: theme === 'dark' ? '#161b22' : '#fff',
    border: theme === 'dark' ? '#30363d' : '#d9d9d9',
    text: theme === 'dark' ? '#c9d1d9' : '#000',
    textSecondary: theme === 'dark' ? '#8b949e' : '#666',
    cardBg: theme === 'dark' ? '#21262d' : '#fff',
  };
  
  // 存档相关状态
  const [saveId, setSaveId] = useState<string | null>(null);
  const [saveData, setSaveData] = useState<ExtendedSaveData | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState<Array<{ name: string; status: 'pending' | 'loading' | 'done' | 'error'; detail?: string }>>([
    { name: '加载存档', status: 'pending' },
    { name: '初始化会话', status: 'pending' },
    { name: '获取股票信息', status: 'pending', detail: '' },
    { name: '加载游戏状态', status: 'pending' },
    { name: '加载K线数据', status: 'pending', detail: '' },
  ]);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [initialCash, setInitialCash] = useState(0);
  const [dailyData, setDailyData] = useState<Record<string, DailyBar[]>>({});
  const [currentPrices, setCurrentPrices] = useState<Record<string, number>>({});
  const [selectedStock, setSelectedStock] = useState<string>('');
  const [stockCodes, setStockCodes] = useState<string[]>([]);
  const [speed, setSpeed] = useState(1);
  const [autoPlay, setAutoPlay] = useState(false);
  const [tickIndex, setTickIndex] = useState(0);
  const [showTrading, setShowTrading] = useState(false);
  const [showAddStock, setShowAddStock] = useState(false);
  const [stockInfoMap, setStockInfoMap] = useState<Record<string, StockInfo>>({});
  const [tradeHistory, setTradeHistory] = useState<SaveTradeRecord[]>([]);

  const [priceHistory, setPriceHistory] = useState<Record<string, Array<{ tick: number; price: number }>>>({});
  const [viewMode, setViewMode] = useState<'trading' | 'assets'>('trading');
  const [assetHistory, setAssetHistory] = useState<DailySnapshot[]>([]);
  const openPricesRef = useRef<Record<string, number>>({});
  const playingRef = useRef(false);
  const autoPlayRef = useRef(false);
  const playIntervalRef = useRef<number | null>(null);
  const autoSaveTimeoutRef = useRef<number | null>(null);

  // 成就系统相关状态
  const [showAchievementModal, setShowAchievementModal] = useState(false);
  const [achievementDefinitions, setAchievementDefinitions] = useState<AchievementDefinition[]>([]);
  const [achievementProgress, setAchievementProgress] = useState<AchievementProgress | null>(null);
  const [loadingAchievements, setLoadingAchievements] = useState(false);
  const [newAchievementCount, setNewAchievementCount] = useState(0);
  const [newlyUnlockedAchievements, setNewlyUnlockedAchievements] = useState<AchievementDefinition[]>([]);
  
  // 挑战模式相关状态
  const [challengeProgress, setChallengeProgress] = useState<ChallengeProgress | null>(null);
  const [challengeConfig, setChallengeConfig] = useState<ChallengeConfig | null>(null);
  const [isChallenge, setIsChallenge] = useState(false);
  const [challengeCompleted, setChallengeCompleted] = useState(false);
  const [challengeResult, setChallengeResult] = useState<{ passed: boolean; finalAssets: number; targetAssets: number } | null>(null);

  // 更新任务状态的辅助函数
  const updateTask = (index: number, status: 'pending' | 'loading' | 'done' | 'error', detail?: string) => {
    setLoadingTasks(prev => prev.map((t, i) => i === index ? { ...t, status, detail: detail ?? t.detail } : t));
  };

  // 自动保存函数
  const autoSave = useCallback(async () => {
    if (!saveId || !account || !gameState) return;
    
    try {
      // 获取当前挂单列表
      let pendingOrders: Array<{
        orderId: string;
        code: string;
        orderType: string;
        price: number;
        quantity: number;
        frozenCash: number;
        frozenQuantity: number;
        orderDate: string;
      }> = [];
      
      if (sessionId) {
        try {
          const orders = await gameApi.getPendingOrders(sessionId);
          pendingOrders = orders.map(o => ({
            orderId: o.orderId,
            code: o.code,
            orderType: o.orderType,
            price: o.price,
            quantity: o.quantity,
            frozenCash: o.frozenCash,
            frozenQuantity: o.frozenQuantity,
            orderDate: gameState.currentDate,
          }));
        } catch (e) {
          console.error('Failed to get pending orders for save:', e);
        }
      }
      
      await saveApi.updateSave(saveId, {
        account: {
          cash: account.cash,
          positions: account.positions,
        },
        gameState: {
          currentDate: gameState.currentDate,
          playbackState: gameState.playbackState,
          tickIndex: tickIndex,
          sessionId: sessionId || undefined,
        },
        stockCodes: stockCodes,
        pendingOrders: pendingOrders,
        assetHistory: assetHistory,
        tradeHistory: tradeHistory,
      });
    } catch (error) {
      console.error('Auto-save failed:', error);
    }
  }, [saveId, account, gameState, tickIndex, stockCodes, sessionId, assetHistory, tradeHistory]);

  // 防抖自动保存
  const scheduleAutoSave = useCallback(() => {
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }
    autoSaveTimeoutRef.current = window.setTimeout(() => {
      autoSave();
    }, 2000); // 2秒后保存
  }, [autoSave]);

  // 加载成就定义
  const loadAchievementDefinitions = useCallback(async () => {
    try {
      const definitions = await achievementApi.getDefinitions();
      setAchievementDefinitions(definitions);
    } catch (error) {
      console.error('Failed to load achievement definitions:', error);
    }
  }, []);

  // 加载成就进度
  const loadAchievementProgress = useCallback(async () => {
    if (!saveId) return;
    try {
      setLoadingAchievements(true);
      const progress = await achievementApi.getProgress(saveId);
      setAchievementProgress(progress);
      setNewAchievementCount(progress.newAchievements.length);
    } catch (error) {
      console.error('Failed to load achievement progress:', error);
    } finally {
      setLoadingAchievements(false);
    }
  }, [saveId]);

  // 检查并解锁成就
  const checkAchievements = useCallback(async () => {
    if (!saveId) return;
    try {
      const result = await achievementApi.checkAchievements(saveId);
      setAchievementProgress(result.progress);
      setNewAchievementCount(result.progress.newAchievements.length);
      
      // 显示新解锁的成就通知
      if (result.newAchievements.length > 0) {
        const newAchievements = achievementDefinitions.filter(
          d => result.newAchievements.includes(d.id)
        );
        setNewlyUnlockedAchievements(newAchievements);
        // 显示通知
        newAchievements.forEach((achievement, index) => {
          setTimeout(() => {
            showAchievementNotification(achievement);
          }, index * 600);
        });
      }
    } catch (error) {
      console.error('Failed to check achievements:', error);
    }
  }, [saveId, achievementDefinitions]);

  // 加载挑战进度
  const loadChallengeProgress = useCallback(async () => {
    if (!saveId || !isChallenge) return;
    try {
      const progress = await challengeApi.getProgress(saveId);
      // 如果有本地的实时数据，使用本地数据更新进度
      if (account && gameState?.currentDate && challengeConfig) {
        const currentAssets = account.totalAssets;
        const targetAssets = challengeConfig.targetAssets;
        const initialCash = challengeConfig.initialCash;
        
        // 计算进度百分比
        let progressPct = 0;
        if (targetAssets > initialCash) {
          progressPct = ((currentAssets - initialCash) / (targetAssets - initialCash)) * 100;
        } else if (currentAssets >= targetAssets) {
          progressPct = 100;
        }
        progressPct = Math.max(0, Math.min(100, progressPct));
        
        // 计算剩余天数
        const current = new Date(gameState.currentDate);
        const end = new Date(challengeConfig.endDate);
        const daysRemaining = Math.max(0, Math.ceil((end.getTime() - current.getTime()) / (1000 * 60 * 60 * 24)));
        
        setChallengeProgress({
          ...progress,
          currentAssets,
          progressPct,
          daysRemaining,
          currentDate: gameState.currentDate,
        });
      } else {
        setChallengeProgress(progress);
      }
    } catch (error) {
      console.error('Failed to load challenge progress:', error);
    }
  }, [saveId, isChallenge, account, gameState, challengeConfig]);

  // 打开成就弹窗
  const handleOpenAchievementModal = useCallback(async () => {
    setShowAchievementModal(true);
    // 清除新成就标记
    if (saveId && newAchievementCount > 0) {
      try {
        await achievementApi.clearNewAchievements(saveId);
        setNewAchievementCount(0);
        if (achievementProgress) {
          setAchievementProgress({
            ...achievementProgress,
            newAchievements: [],
          });
        }
      } catch (error) {
        console.error('Failed to clear new achievements:', error);
      }
    }
  }, [saveId, newAchievementCount, achievementProgress]);

  const handleTick = useCallback((data: TickData) => {
    setCurrentPrices(data.prices);
    if (data.tick_index !== undefined) {
      setTickIndex(data.tick_index);
      setPriceHistory(prev => {
        const newHistory = { ...prev };
        for (const [code, price] of Object.entries(data.prices)) {
          if (!newHistory[code]) newHistory[code] = [];
          newHistory[code] = [...newHistory[code], { tick: data.tick_index, price }];
        }
        return newHistory;
      });
    }
    // 更新当前日期（用于实时挑战进度显示）
    if (data.current_date) {
      setGameState(prev => prev ? { ...prev, currentDate: data.current_date! } : null);
    }
  }, []);

  const handleAccountUpdate = useCallback((data: AccountUpdateData) => {
    setAccount({
      cash: data.cash,
      totalAssets: data.total_assets,
      totalMarketValue: data.total_market_value,
      positions: data.positions.map(p => ({
        code: p.code,
        quantity: p.quantity,
        costPrice: p.cost_price,
        currentPrice: p.current_price,
        profitLoss: p.profit_loss,
        profitLossPct: p.profit_loss_pct,
      })),
    });
    scheduleAutoSave();
  }, [scheduleAutoSave]);

  const handleStateUpdate = useCallback((data: StateUpdateData) => {
    setGameState(prev => {
      if (!prev) return null;
      return {
        ...prev,
        currentDate: data.current_date,
        playbackState: data.playback_state as GameState['playbackState'],
        isLastDay: data.is_last_day ?? prev.isLastDay,
      };
    });
    if (data.tick_index !== undefined) setTickIndex(data.tick_index);
    scheduleAutoSave();
  }, [scheduleAutoSave]);

  // 检查挑战是否结束
  const checkChallengeCompletion = useCallback((currentDate: string, totalAssets: number) => {
    if (!isChallenge || !challengeConfig || challengeCompleted) return;
    
    const current = new Date(currentDate);
    const endDate = new Date(challengeConfig.endDate);
    
    if (current >= endDate) {
      // 挑战结束 - 停止所有播放
      playingRef.current = false;
      autoPlayRef.current = false;
      setAutoPlay(false);
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
      
      // 更新游戏状态为已结束
      setGameState(prev => prev ? { ...prev, playbackState: 'finished' } : null);
      
      setChallengeCompleted(true);
      const passed = totalAssets >= challengeConfig.targetAssets;
      setChallengeResult({
        passed,
        finalAssets: totalAssets,
        targetAssets: challengeConfig.targetAssets,
      });
      
      if (passed) {
        message.success(`🎉 恭喜！挑战成功！最终资产 ¥${totalAssets.toFixed(2)}，目标 ¥${challengeConfig.targetAssets.toFixed(2)}`);
      } else {
        message.warning(`挑战结束！最终资产 ¥${totalAssets.toFixed(2)}，未达到目标 ¥${challengeConfig.targetAssets.toFixed(2)}`);
      }
    }
  }, [isChallenge, challengeConfig, challengeCompleted]);

  const handleDayEnd = useCallback((date: string) => {
    message.info(`${date} 交易日结束`);
    playingRef.current = false;
    if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    if (sessionId) {
      // 使用 async IIFE 确保顺序执行
      (async () => {
        try {
          const acc = await gameApi.getAccount(sessionId);
          setAccount(acc);
          
          // 记录每日资产快照
          setAssetHistory(prev => {
            // 避免重复记录同一天
            if (prev.some(h => h.date === date)) return prev;
            
            const totalAssets = acc.totalAssets;
            const cash = acc.cash;
            const marketValue = acc.totalMarketValue;
            
            // 计算当日收益
            const prevSnapshot = prev.length > 0 ? prev[prev.length - 1] : null;
            const prevAssets = prevSnapshot ? prevSnapshot.totalAssets : initialCash;
            const dailyProfit = totalAssets - prevAssets;
            const dailyReturn = prevAssets > 0 ? dailyProfit / prevAssets : 0;
            const cumulativeReturn = initialCash > 0 ? (totalAssets - initialCash) / initialCash : 0;
            
            const newSnapshot: DailySnapshot = {
              date,
              totalAssets,
              cash,
              marketValue,
              dailyReturn,
              dailyProfit,
              cumulativeReturn,
            };
            
            return [...prev, newSnapshot];
          });
          
          scheduleAutoSave();
          
          // 检查成就解锁
          checkAchievements();
          
          // 检查挑战是否结束（这会设置 challengeCompleted 和 autoPlayRef.current = false）
          checkChallengeCompletion(date, acc.totalAssets);
          
          // 更新挑战进度
          if (isChallenge) {
            loadChallengeProgress();
          }
          
          // 获取游戏状态
          const state = await gameApi.getGameState(sessionId);
          setGameState(state);
          
          // 如果开启了自动播放且不是最后一天，且挑战未结束，自动进入下一天
          // 注意：checkChallengeCompletion 已经将 autoPlayRef.current 设为 false（如果挑战结束）
          if (autoPlayRef.current && !state.isLastDay) {
            setTimeout(() => {
              handleNextDayAuto();
            }, 500);
          }
        } catch (error) {
          console.error('Error in handleDayEnd:', error);
        }
      })();
    }
  }, [sessionId, scheduleAutoSave, initialCash, checkAchievements, isChallenge, loadChallengeProgress, checkChallengeCompletion]);

  const handleError = useCallback((err: string) => {
    message.error(err);
  }, []);

  const { isConnected, play, pause } = useWebSocket({
    sessionId: sessionId || '',
    onTick: handleTick,
    onAccountUpdate: handleAccountUpdate,
    onStateUpdate: handleStateUpdate,
    onDayEnd: handleDayEnd,
    onError: handleError,
  });

  // 防止 StrictMode 重复调用
  const loadedRef = useRef<string | null>(null);

  // 加载存档并创建会话
  useEffect(() => {
    if (!urlId) return;
    // 如果已经加载过相同的 urlId，跳过
    if (loadedRef.current === urlId) return;
    loadedRef.current = urlId;
    
    const loadSaveAndCreateSession = async () => {
      try {
        // 首先尝试加载存档
        updateTask(0, 'loading');
        const save = await saveApi.loadSave(urlId);
        setSaveId(urlId);
        setSaveData(save);
        setInitialCash(save.config.initialCash);
        setStockCodes(save.stockCodes);
        updateTask(0, 'done');
        
        // 设置挑战模式状态
        const isChallengeMode = save.config.gameMode === 'challenge';
        setIsChallenge(isChallengeMode);
        if (isChallengeMode && save.challengeConfig) {
          setChallengeConfig(save.challengeConfig);
        } else if (isChallengeMode) {
          // 如果是挑战模式但没有 challengeConfig，尝试从 API 获取
          try {
            const challengeId = save.config.challengeId;
            if (challengeId) {
              const config = await challengeApi.getChallenge(challengeId);
              setChallengeConfig(config);
            }
          } catch (e) {
            console.error('Failed to fetch challenge config:', e);
          }
        }
        
        // 恢复资产历史
        if (save.assetHistory && save.assetHistory.length > 0) {
          setAssetHistory(save.assetHistory);
        }
        
        // 恢复交易记录
        if (save.tradeHistory && save.tradeHistory.length > 0) {
          setTradeHistory(save.tradeHistory);
        }
        
        // 如果存档没有股票，显示空状态
        if (save.stockCodes.length === 0) {
          setAccount({
            cash: save.account.cash,
            totalAssets: save.account.cash,
            totalMarketValue: 0,
            positions: [],
          });
          // 标记所有任务完成
          setLoadingTasks(prev => prev.map(t => ({ ...t, status: 'done' as const })));
          setLoading(false);
          return;
        }
        
        // 检查存档中是否有已保存的 session_id，尝试复用
        updateTask(1, 'loading');
        const savedSessionId = save.gameState.sessionId;
        let activeSessionId: string | null = null;
        
        if (savedSessionId) {
          try {
            const sessionCheck = await gameApi.checkSessionExists(savedSessionId);
            if (sessionCheck.exists) {
              // 会话仍然有效，复用它
              activeSessionId = savedSessionId;
              console.log('Reusing existing session:', savedSessionId);
            }
          } catch (e) {
            console.log('Session check failed, will create new session');
          }
        }
        
        // 如果没有有效会话，创建新会话
        if (!activeSessionId) {
          const result = await gameApi.startFromSave(urlId);
          activeSessionId = result.session_id;
          
          // 保存新的 session_id 到存档
          await saveApi.updateSave(urlId, {
            gameState: {
              currentDate: save.gameState.currentDate || result.current_date,
              playbackState: save.gameState.playbackState || 'paused',
              tickIndex: save.gameState.tickIndex || 0,
              sessionId: activeSessionId,
            },
            stockCodes: save.stockCodes,
          });
          console.log('Created new session:', activeSessionId);
        }
        
        setSessionId(activeSessionId);
        updateTask(1, 'done');
        
        // 获取股票名称信息 - 优先从本地缓存读取
        updateTask(2, 'loading', `0/${save.stockCodes.length}`);
        try {
          const infoMap: Record<string, StockInfo> = {};
          // 先从缓存获取已有的股票信息
          const { cached, missing } = stockCache.getMany(save.stockCodes);
          Object.assign(infoMap, cached);
          
          // 只对缓存中没有的股票发起API请求
          let loadedCount = Object.keys(cached).length;
          updateTask(2, 'loading', `${loadedCount}/${save.stockCodes.length} (缓存)`);
          
          for (const code of missing) {
            try {
              updateTask(2, 'loading', `${loadedCount}/${save.stockCodes.length} ${code}`);
              const results = await stockApi.getStockList(code);
              const match = results.find(s => s.code === code);
              if (match) {
                infoMap[code] = match;
                // 保存到缓存
                stockCache.set(code, match);
              }
              loadedCount++;
            } catch (e) {
              console.error(`Failed to get info for ${code}:`, e);
              loadedCount++;
            }
          }
          setStockInfoMap(infoMap);
        } catch (e) {
          console.error('Failed to load stock info:', e);
        }
        updateTask(2, 'done', `${save.stockCodes.length}/${save.stockCodes.length}`);
        
        // 加载游戏状态
        updateTask(3, 'loading');
        const state = await gameApi.getGameState(activeSessionId);
        setGameState(state);
        
        const acc = await gameApi.getAccount(activeSessionId);
        setAccount(acc);
        updateTask(3, 'done');
        
        updateTask(4, 'loading', `0/${save.stockCodes.length}`);
        const bars = await gameApi.getCurrentBars(activeSessionId);
        const codes = Object.keys(bars);
        
        const openPrices: Record<string, number> = {};
        for (const [code, bar] of Object.entries(bars)) {
          openPrices[code] = (bar as DailyBar).open;
        }
        openPricesRef.current = openPrices;

        if (codes.length > 0) {
          setSelectedStock(codes[0]);
          
          // 加载历史日线数据
          const currentDate = new Date(state.currentDate);
          const endDate = new Date(currentDate);
          endDate.setDate(endDate.getDate() - 1);
          const startDate = new Date(currentDate);
          startDate.setMonth(startDate.getMonth() - 6);
          
          const dailyDataMap: Record<string, DailyBar[]> = {};
          let klineLoadedCount = 0;
          for (const code of codes) {
            try {
              updateTask(4, 'loading', `${klineLoadedCount}/${codes.length} ${code}`);
              const data = await stockApi.getDailyData(
                code, 
                startDate.toISOString().split('T')[0], 
                endDate.toISOString().split('T')[0]
              );
              const todayBar = bars[code] as DailyBar;
              if (todayBar) {
                // 当天开始时，只显示开盘价，high/low/close 都等于开盘价
                const initialTodayBar: DailyBar = {
                  date: state.currentDate,
                  open: todayBar.open,
                  high: todayBar.open,
                  low: todayBar.open,
                  close: todayBar.open,
                  volume: 0,
                };
                data.push(initialTodayBar);
              }
              dailyDataMap[code] = data;
              klineLoadedCount++;
            } catch (e) {
              console.error(`Failed to load daily data for ${code}:`, e);
              klineLoadedCount++;
            }
          }
          setDailyData(dailyDataMap);
          
          // 设置初始价格为开盘价
          const initialPrices: Record<string, number> = {};
          for (const code of codes) {
            const bar = bars[code] as DailyBar;
            if (bar) {
              initialPrices[code] = bar.open;
            }
          }
          setCurrentPrices(initialPrices);
        }
        updateTask(4, 'done', `${codes.length}/${codes.length}`);
      } catch (error) {
        console.error('Failed to load save:', error);
        message.error('加载存档失败');
        navigate('/');
      } finally {
        setLoading(false);
      }
    };
    
    loadSaveAndCreateSession();
  }, [urlId, navigate]);

  // 清理
  useEffect(() => {
    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      if (autoSaveTimeoutRef.current) clearTimeout(autoSaveTimeoutRef.current);
    };
  }, []);

  // 加载成就定义（只需加载一次）
  useEffect(() => {
    loadAchievementDefinitions();
  }, [loadAchievementDefinitions]);

  // 加载成就进度（当 saveId 变化时）
  useEffect(() => {
    if (saveId) {
      loadAchievementProgress();
    }
  }, [saveId, loadAchievementProgress]);

  // 加载挑战进度（当 saveId 和 isChallenge 变化时）
  useEffect(() => {
    if (saveId && isChallenge) {
      loadChallengeProgress();
      
      // 检查挑战是否已经结束（初始加载时）
      if (challengeConfig && account && gameState) {
        checkChallengeCompletion(gameState.currentDate, account.totalAssets);
      }
    }
  }, [saveId, isChallenge, loadChallengeProgress, challengeConfig, account, gameState, checkChallengeCompletion]);

  // 添加股票到存档
  const handleAddStock = async (stockCode: string) => {
    if (!saveId) return;
    
    await saveApi.addStock(saveId, stockCode);
    
    // 更新本地状态
    setStockCodes(prev => [...prev, stockCode]);
    
    // 获取新股票的名称信息 - 优先从缓存读取
    try {
      const cachedInfo = stockCache.get(stockCode);
      if (cachedInfo) {
        setStockInfoMap(prev => ({ ...prev, [stockCode]: cachedInfo }));
      } else {
        const results = await stockApi.getStockList(stockCode);
        const match = results.find(s => s.code === stockCode);
        if (match) {
          setStockInfoMap(prev => ({ ...prev, [stockCode]: match }));
          // 保存到缓存
          stockCache.set(stockCode, match);
        }
      }
    } catch (e) {
      console.error(`Failed to get info for ${stockCode}:`, e);
    }
    
    // 添加股票后需要重新创建会话以加载新股票的数据
    message.success('股票已添加，正在重新加载数据...');
    setLoading(true);
    // 重新加载页面以重新创建会话
    window.location.reload();
  };

  const startHttpPlayback = useCallback(async () => {
    if (!sessionId) return;
    playingRef.current = true;
    setGameState(prev => prev ? { ...prev, playbackState: 'playing' } : null);
    
    const tickLoop = async () => {
      if (!playingRef.current) return;
      try {
        const result = await gameApi.singleTick(sessionId);
        if (!playingRef.current) return;
        if (result.success && result.prices) {
          setCurrentPrices(result.prices);
          if (result.tick_index !== undefined) {
            setTickIndex(result.tick_index);
            setPriceHistory(prev => {
              const newHistory = { ...prev };
              for (const [code, price] of Object.entries(result.prices as Record<string, number>)) {
                if (!newHistory[code]) newHistory[code] = [];
                newHistory[code] = [...newHistory[code], { tick: result.tick_index as number, price }];
              }
              return newHistory;
            });
          }
          const acc = await gameApi.getAccount(sessionId);
          setAccount(acc);
        }
        if (result.playback_state === 'day_ended') {
          playingRef.current = false;
          if (playIntervalRef.current) clearInterval(playIntervalRef.current);
          // 使用 result.current_date 如果可用，否则使用 gameState.currentDate
          const currentDate = result.current_date || gameState?.currentDate || '';
          handleDayEnd(currentDate);
          return;
        }
        // 更新 gameState，包括 currentDate（如果 API 返回了的话）
        setGameState(prev => prev ? { 
          ...prev, 
          playbackState: 'playing',
          currentDate: result.current_date || prev.currentDate,
        } : null);
      } catch (error) {
        playingRef.current = false;
        if (playIntervalRef.current) clearInterval(playIntervalRef.current);
        console.error('Tick error:', error);
      }
    };
    
    const interval = Math.max(50, 1000 / speed);
    playIntervalRef.current = window.setInterval(tickLoop, interval);
    tickLoop();
  }, [sessionId, speed, gameState?.currentDate, handleDayEnd]);

  const handlePlay = () => {
    if (!sessionId) return;
    if (isConnected) play(speed);
    else startHttpPlayback();
  };

  const handlePause = async () => {
    playingRef.current = false;
    if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    setGameState(prev => prev ? { ...prev, playbackState: 'paused' } : null);
    if (isConnected) pause();
    if (sessionId) {
      try {
        await gameApi.pausePlayback(sessionId);
        setGameState(prev => prev ? { ...prev, playbackState: 'paused' } : null);
        scheduleAutoSave();
      } catch (error) {
        console.error('Pause error:', error);
      }
    }
  };

  const handleNextDay = async () => {
    if (!sessionId) return;
    try {
      setPriceHistory({});
      setTickIndex(0);
      const state = await gameApi.nextDay(sessionId);
      setGameState(state);
      const acc = await gameApi.getAccount(sessionId);
      setAccount(acc);
      
      // 资产历史已在 handleDayEnd 中记录，无需从后端加载
      
      const bars = await gameApi.getCurrentBars(sessionId);
      const openPrices: Record<string, number> = {};
      for (const [code, bar] of Object.entries(bars)) {
        openPrices[code] = (bar as DailyBar).open;
      }
      openPricesRef.current = openPrices;
      
      // 加载历史日线数据
      const currentDate = new Date(state.currentDate);
      const endDate = new Date(currentDate);
      endDate.setDate(endDate.getDate() - 1);
      const startDate = new Date(currentDate);
      startDate.setMonth(startDate.getMonth() - 6);
      
      const dailyDataMap: Record<string, DailyBar[]> = {};
      for (const code of stockCodes) {
        try {
          const data = await stockApi.getDailyData(
            code, 
            startDate.toISOString().split('T')[0], 
            endDate.toISOString().split('T')[0]
          );
          const todayBar = bars[code] as DailyBar;
          if (todayBar) {
            const initialTodayBar: DailyBar = {
              date: state.currentDate,
              open: todayBar.open,
              high: todayBar.open,
              low: todayBar.open,
              close: todayBar.open,
              volume: 0,
            };
            data.push(initialTodayBar);
          }
          dailyDataMap[code] = data;
        } catch (e) {
          console.error(`Failed to load daily data for ${code}:`, e);
        }
      }
      setDailyData(dailyDataMap);
      
      // 设置初始价格为开盘价
      const initialPrices: Record<string, number> = {};
      for (const code of stockCodes) {
        const bar = bars[code] as DailyBar;
        if (bar) {
          initialPrices[code] = bar.open;
        }
      }
      setCurrentPrices(initialPrices);
      
      message.success(`进入交易日: ${state.currentDate}`);
      scheduleAutoSave();
    } catch (error) {
      message.error('进入下一交易日失败');
    }
  };

  // 自动播放时进入下一天并自动开始播放
  const handleNextDayAuto = async () => {
    if (!sessionId) return;
    try {
      setPriceHistory({});
      setTickIndex(0);
      const state = await gameApi.nextDay(sessionId);
      setGameState(state);
      const acc = await gameApi.getAccount(sessionId);
      setAccount(acc);
      
      const bars = await gameApi.getCurrentBars(sessionId);
      const openPrices: Record<string, number> = {};
      for (const [code, bar] of Object.entries(bars)) {
        openPrices[code] = (bar as DailyBar).open;
      }
      openPricesRef.current = openPrices;
      
      // 加载历史日线数据
      const currentDate = new Date(state.currentDate);
      const endDate = new Date(currentDate);
      endDate.setDate(endDate.getDate() - 1);
      const startDate = new Date(currentDate);
      startDate.setMonth(startDate.getMonth() - 6);
      
      const dailyDataMap: Record<string, DailyBar[]> = {};
      for (const code of stockCodes) {
        try {
          const data = await stockApi.getDailyData(
            code, 
            startDate.toISOString().split('T')[0], 
            endDate.toISOString().split('T')[0]
          );
          const todayBar = bars[code] as DailyBar;
          if (todayBar) {
            const initialTodayBar: DailyBar = {
              date: state.currentDate,
              open: todayBar.open,
              high: todayBar.open,
              low: todayBar.open,
              close: todayBar.open,
              volume: 0,
            };
            data.push(initialTodayBar);
          }
          dailyDataMap[code] = data;
        } catch (e) {
          console.error(`Failed to load daily data for ${code}:`, e);
        }
      }
      setDailyData(dailyDataMap);
      
      // 设置初始价格为开盘价
      const initialPrices: Record<string, number> = {};
      for (const code of stockCodes) {
        const bar = bars[code] as DailyBar;
        if (bar) {
          initialPrices[code] = bar.open;
        }
      }
      setCurrentPrices(initialPrices);
      
      message.info(`自动进入交易日: ${state.currentDate}`);
      scheduleAutoSave();
      
      // 自动开始播放
      setTimeout(() => {
        if (autoPlayRef.current) {
          handlePlay();
        }
      }, 300);
    } catch (error) {
      message.error('自动进入下一交易日失败');
      // 出错时关闭自动播放
      setAutoPlay(false);
      autoPlayRef.current = false;
    }
  };

  // 自动播放开关变化
  const handleAutoPlayChange = (enabled: boolean) => {
    setAutoPlay(enabled);
    autoPlayRef.current = enabled;
  };

  const handleBuy = async (price: number, quantity: number) => {
    if (!sessionId || !selectedStock) return;
    try {
      const result = await gameApi.buy({ session_id: sessionId, code: selectedStock, price, quantity });
      if (result.success) {
        message.success(`买入成功，手续费: ¥${result.fee?.toFixed(2)}`);
        
        // 记录交易
        const newTrade: SaveTradeRecord = {
          orderId: result.order_id || `buy_${Date.now()}`,
          code: selectedStock,
          orderType: 'buy',
          price,
          quantity,
          fee: result.fee || 0,
          timestamp: gameState?.currentDate || new Date().toISOString().split('T')[0],
        };
        setTradeHistory(prev => [...prev, newTrade]);
        
        const acc = await gameApi.getAccount(sessionId);
        setAccount(acc);
        setShowTrading(false);
        scheduleAutoSave();
        
        // 检查成就解锁
        checkAchievements();
      } else {
        message.error(result.message);
      }
    } catch (error) {
      message.error('买入失败');
    }
  };

  const handleSell = async (price: number, quantity: number) => {
    if (!sessionId || !selectedStock) return;
    try {
      const result = await gameApi.sell({ session_id: sessionId, code: selectedStock, price, quantity });
      if (result.success) {
        message.success(`卖出成功，手续费: ¥${result.fee?.toFixed(2)}`);
        
        // 记录交易
        const newTrade: SaveTradeRecord = {
          orderId: result.order_id || `sell_${Date.now()}`,
          code: selectedStock,
          orderType: 'sell',
          price,
          quantity,
          fee: result.fee || 0,
          timestamp: gameState?.currentDate || new Date().toISOString().split('T')[0],
        };
        setTradeHistory(prev => [...prev, newTrade]);
        
        const acc = await gameApi.getAccount(sessionId);
        setAccount(acc);
        setShowTrading(false);
        scheduleAutoSave();
        
        // 检查成就解锁
        checkAchievements();
      } else {
        message.error(result.message);
      }
    } catch (error) {
      message.error('卖出失败');
    }
  };

  if (loading) {
    const doneCount = loadingTasks.filter(t => t.status === 'done').length;
    const progress = Math.round((doneCount / loadingTasks.length) * 100);
    
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        background: theme === 'dark' 
          ? 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)'
          : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        gap: 20,
      }}>
        <div style={{ fontSize: 48 }}>📈</div>
        <div style={{ color: theme === 'dark' ? '#c9d1d9' : '#fff', fontSize: 20, fontWeight: 600 }}>
          A股模拟交易
        </div>
        
        {/* 进度条 */}
        <div style={{ width: 300, height: 6, background: theme === 'dark' ? '#21262d' : 'rgba(255,255,255,0.3)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ 
            width: `${progress}%`, 
            height: '100%', 
            background: 'linear-gradient(90deg, #238636 0%, #2ea043 100%)',
            borderRadius: 3,
            transition: 'width 0.3s ease',
          }} />
        </div>
        
        {/* 任务列表 */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 8,
          padding: '16px 24px',
          background: theme === 'dark' ? 'rgba(33, 38, 45, 0.5)' : 'rgba(255, 255, 255, 0.2)',
          borderRadius: 8,
          minWidth: 280,
        }}>
          {loadingTasks.map((task, index) => (
            <div key={index} style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 10,
              color: task.status === 'done' ? '#3fb950' : task.status === 'loading' ? (theme === 'dark' ? '#58a6ff' : '#fff') : (theme === 'dark' ? '#484f58' : 'rgba(255,255,255,0.6)'),
              fontSize: 13,
              minHeight: 24,
            }}>
              <span style={{ width: 18, textAlign: 'center', flexShrink: 0 }}>
                {task.status === 'done' ? '✓' : task.status === 'loading' ? '◌' : '○'}
              </span>
              <span style={{ fontWeight: task.status === 'loading' ? 500 : 400 }}>
                {task.name}
              </span>
              {task.detail && (
                <span style={{ 
                  marginLeft: 'auto', 
                  fontSize: 11, 
                  color: task.status === 'loading' ? (theme === 'dark' ? '#58a6ff' : '#fff') : '#3fb950',
                  fontFamily: 'monospace',
                  background: task.status === 'loading' ? 'rgba(88, 166, 255, 0.1)' : 'rgba(63, 185, 80, 0.1)',
                  padding: '2px 6px',
                  borderRadius: 4,
                }}>
                  {task.detail}
                </span>
              )}
              {task.status === 'loading' && !task.detail && (
                <Spin size="small" style={{ marginLeft: 'auto' }} />
              )}
            </div>
          ))}
        </div>
        
        <div style={{ color: theme === 'dark' ? '#484f58' : 'rgba(255,255,255,0.7)', fontSize: 12 }}>{progress}%</div>
      </div>
    );
  }

  const currentPrice = currentPrices[selectedStock] || dailyData[selectedStock]?.slice(-1)[0]?.close || 0;
  const selectedPosition = account?.positions.find(p => p.code === selectedStock);
  const canTrade = sessionId && (
    gameState?.playbackState === 'idle' ||
    gameState?.playbackState === 'paused' ||
    gameState?.playbackState === 'day_ended'
  );
  const hasStocks = stockCodes.length > 0;

  // 空股票列表状态
  if (!hasStocks) {
    return (
      <Layout style={{ minHeight: '100vh', background: themeStyles.bg }}>
        <Header style={{ 
          background: themeStyles.headerBg, 
          padding: '0 16px', 
          height: 56, 
          lineHeight: '56px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: `1px solid ${themeStyles.border}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button 
              icon={<HomeOutlined />} 
              onClick={() => navigate('/')}
            >
              返回
            </Button>
            <span style={{ color: themeStyles.text, fontWeight: 600, fontSize: 16 }}>
              📈 {saveData?.name || 'A股模拟交易'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <AccountSummary account={account} initialCash={initialCash} />
          </div>
        </Header>
        
        <Content style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          padding: 40,
        }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span style={{ color: themeStyles.textSecondary, fontSize: 16 }}>
                {isChallenge 
                  ? '挑战模式数据加载中...' 
                  : '还没有添加股票，点击下方按钮添加第一只股票开始交易'}
              </span>
            }
          >
            {!isChallenge && (
              <Button 
                type="primary" 
                size="large"
                icon={<PlusOutlined />}
                onClick={() => setShowAddStock(true)}
              >
                添加股票
              </Button>
            )}
          </Empty>
        </Content>
        
        <AddStockModal
          open={showAddStock}
          onClose={() => setShowAddStock(false)}
          onAddStock={handleAddStock}
          existingStocks={stockCodes}
        />
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh', background: themeStyles.bg }}>
      <Header style={{ 
        background: themeStyles.headerBg, 
        padding: '0 16px', 
        height: 56, 
        lineHeight: '56px', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        borderBottom: `1px solid ${themeStyles.border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button 
            icon={<HomeOutlined />} 
            onClick={() => navigate('/')}
          >
            返回
          </Button>
          <span style={{ color: themeStyles.text, fontWeight: 600, fontSize: 16 }}>
            📈 {saveData?.name || 'A股模拟交易'}
          </span>
          <Badge status={isConnected ? 'success' : 'default'} text={
            <span style={{ color: themeStyles.textSecondary, fontSize: 12 }}>
              {isConnected ? '实时连接' : '轮询模式'}
            </span>
          } />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <AccountSummary account={account} initialCash={initialCash} />
          <PositionSummary 
            positions={account?.positions || []} 
            onSelect={(code: string) => setSelectedStock(code)} 
          />
          <Segmented
            value={viewMode}
            onChange={(v) => setViewMode(v as 'trading' | 'assets')}
            options={[
              { label: '行情', value: 'trading', icon: <LineChartOutlined /> },
              { label: '资产', value: 'assets', icon: <FundOutlined /> },
            ]}
          />
          {!isChallenge && (
            <Tooltip title="添加股票">
              <Button 
                icon={<PlusOutlined />} 
                onClick={() => setShowAddStock(true)}
              >
                添加股票
              </Button>
            </Tooltip>
          )}
          <Tooltip title="成就">
            <Badge count={newAchievementCount} size="small" offset={[-5, 5]}>
              <Button 
                icon={<TrophyOutlined />} 
                onClick={handleOpenAchievementModal}
              >
                成就
              </Button>
            </Badge>
          </Tooltip>
          <Tooltip title={canTrade ? '点击交易' : '播放中无法交易，请先暂停'}>
            <Button
              type={showTrading ? 'primary' : 'default'}
              icon={<SwapOutlined />}
              onClick={() => setShowTrading(!showTrading)}
              disabled={!canTrade}
            >
              交易
            </Button>
          </Tooltip>
        </div>
      </Header>

      <div style={{ padding: '12px 16px', background: themeStyles.headerBg, borderBottom: `1px solid ${themeStyles.border}` }}>
        <PlaybackControl
          state={gameState}
          speed={speed}
          autoPlay={autoPlay}
          onPlay={handlePlay}
          onPause={handlePause}
          onSpeedChange={setSpeed}
          onNextDay={handleNextDay}
          onAutoPlayChange={handleAutoPlayChange}
        />
      </div>

      {/* 挑战模式进度显示 - 使用实时数据 */}
      {isChallenge && challengeConfig && account && (
        <div style={{ padding: '0 16px' }}>
          <ChallengeProgressComponent
            config={challengeConfig}
            currentAssets={account.totalAssets}
            currentDate={gameState?.currentDate || challengeConfig.startDate}
          />
        </div>
      )}

      {/* 价格显示区域 */}
      {selectedStock && (
        <div style={{ 
          padding: '16px 24px', 
          background: theme === 'dark' ? 'linear-gradient(135deg, #161b22 0%, #1c2128 100%)' : 'linear-gradient(135deg, #f5f5f5 0%, #fff 100%)', 
          borderBottom: `1px solid ${themeStyles.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 32,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <span style={{ color: theme === 'dark' ? '#58a6ff' : '#1890ff', fontSize: 18, fontWeight: 600 }}>
              {selectedStock} {stockInfoMap[selectedStock]?.name || ''}
            </span>
            {openPricesRef.current[selectedStock] ? (
              <span style={{ 
                color: currentPrice >= (openPricesRef.current[selectedStock] || currentPrice) ? '#f85149' : '#3fb950',
                fontSize: 36, 
                fontWeight: 700,
                fontFamily: 'monospace',
              }}>
                ¥{currentPrice.toFixed(2)}
              </span>
            ) : (
              <span style={{ 
                color: '#faad14',
                fontSize: 16, 
                fontWeight: 500,
              }}>
                ⚠️ 该股票今日无交易数据（可能停牌）
              </span>
            )}
          </div>
          
          {openPricesRef.current[selectedStock] && (() => {
            const openPrice = openPricesRef.current[selectedStock] || currentPrice;
            const change = currentPrice - openPrice;
            const changePct = openPrice > 0 ? (change / openPrice) * 100 : 0;
            const isUp = change >= 0;
            const color = isUp ? '#f85149' : '#3fb950';
            const arrow = isUp ? '▲' : '▼';
            
            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ 
                  padding: '6px 12px', 
                  background: isUp ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)',
                  borderRadius: 6,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}>
                  <span style={{ color, fontSize: 16, fontWeight: 600 }}>
                    {arrow} {isUp ? '+' : ''}{change.toFixed(2)}
                  </span>
                  <span style={{ color, fontSize: 16, fontWeight: 600 }}>
                    ({isUp ? '+' : ''}{changePct.toFixed(2)}%)
                  </span>
                </div>
              </div>
            );
          })()}

          {openPricesRef.current[selectedStock] && (
            <div style={{ 
            display: 'flex', 
            gap: 24, 
            marginLeft: 'auto',
            color: themeStyles.textSecondary,
            fontSize: 14,
          }}>
            <div>
              <span style={{ marginRight: 8 }}>开盘</span>
              <span style={{ color: themeStyles.text, fontFamily: 'monospace' }}>
                {(openPricesRef.current[selectedStock] || 0).toFixed(2)}
              </span>
            </div>
            <div>
              <span style={{ marginRight: 8 }}>最高</span>
              <span style={{ color: '#f85149', fontFamily: 'monospace' }}>
                {(() => {
                  const history = priceHistory[selectedStock] || [];
                  if (history.length === 0) return (openPricesRef.current[selectedStock] || 0).toFixed(2);
                  return Math.max(...history.map(h => h.price)).toFixed(2);
                })()}
              </span>
            </div>
            <div>
              <span style={{ marginRight: 8 }}>最低</span>
              <span style={{ color: '#3fb950', fontFamily: 'monospace' }}>
                {(() => {
                  const history = priceHistory[selectedStock] || [];
                  if (history.length === 0) return (openPricesRef.current[selectedStock] || 0).toFixed(2);
                  return Math.min(...history.map(h => h.price)).toFixed(2);
                })()}
              </span>
            </div>
            <div>
              <span style={{ marginRight: 8 }}>Tick</span>
              <span style={{ color: themeStyles.text, fontFamily: 'monospace' }}>
                {tickIndex}/240
              </span>
            </div>
          </div>
          )}
        </div>
      )}

      <Content style={{ padding: 16, position: 'relative' }}>
        {showTrading && canTrade && (
          <div style={{ 
            position: 'absolute', 
            top: 16, 
            right: 16, 
            zIndex: 1000,
            width: 360,
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            borderRadius: 12,
          }}>
            <TradingPanel
              stockCode={selectedStock}
              currentPrice={currentPrice}
              cash={account?.cash || 0}
              position={selectedPosition}
              disabled={!canTrade}
              isTodayBought={selectedPosition?.buyDate === gameState?.currentDate}
              onBuy={handleBuy}
              onSell={handleSell}
              onClose={() => setShowTrading(false)}
            />
          </div>
        )}

        {viewMode === 'trading' ? (
          <Row gutter={12} style={{ height: 'calc(100vh - 260px)' }}>
            <Col xs={24} lg={12}>
              <div style={{ 
                background: themeStyles.cardBg, 
                borderRadius: 12, 
                border: `1px solid ${themeStyles.border}`,
                height: '100%',
                overflow: 'hidden',
              }}>
                <StockChart
                  key={`stock-${theme}`}
                  code={selectedStock}
                  dailyData={dailyData[selectedStock] || []}
                  stockCodes={stockCodes}
                  stockInfoMap={stockInfoMap}
                  onStockChange={setSelectedStock}
                  currentPrice={currentPrice}
                  tickIndex={tickIndex}
                  intradayHigh={(() => {
                    const history = priceHistory[selectedStock] || [];
                    if (history.length === 0) return undefined;
                    return Math.max(...history.map(h => h.price));
                  })()}
                  intradayLow={(() => {
                    const history = priceHistory[selectedStock] || [];
                    if (history.length === 0) return undefined;
                    return Math.min(...history.map(h => h.price));
                  })()}
                  tradeHistory={tradeHistory}
                />
              </div>
            </Col>
            <Col xs={24} lg={8}>
              <div style={{ 
                background: themeStyles.cardBg, 
                borderRadius: 12, 
                border: `1px solid ${themeStyles.border}`,
                height: '100%',
                overflow: 'hidden',
              }}>
                <IntradayChart
                  key={`intraday-${theme}`}
                  code={selectedStock}
                  priceHistory={priceHistory[selectedStock] || []}
                  openPrice={openPricesRef.current[selectedStock] || 0}
                />
              </div>
            </Col>
            <Col xs={24} lg={4}>
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
                <PendingOrderList
                  sessionId={sessionId}
                  stockInfoMap={stockInfoMap}
                  onOrderCancelled={async () => {
                    if (sessionId) {
                      const acc = await gameApi.getAccount(sessionId);
                      setAccount(acc);
                    }
                  }}
                />
              </div>
            </Col>
          </Row>
        ) : (
          <div style={{ 
            background: themeStyles.cardBg, 
            borderRadius: 12, 
            border: `1px solid ${themeStyles.border}`,
            height: 'calc(100vh - 260px)',
            overflow: 'hidden',
          }}>
            <AssetChart
              history={assetHistory}
              initialCash={initialCash}
              currentAssets={account?.totalAssets || initialCash}
              tradeHistory={tradeHistory}
              positions={account?.positions || []}
              stockInfoMap={stockInfoMap}
            />
          </div>
        )}
      </Content>
      
      <AddStockModal
        open={showAddStock}
        onClose={() => setShowAddStock(false)}
        onAddStock={handleAddStock}
        existingStocks={stockCodes}
      />
      
      {/* 成就弹窗 */}
      <AchievementModal
        open={showAchievementModal}
        onClose={() => setShowAchievementModal(false)}
        definitions={achievementDefinitions}
        progress={achievementProgress}
        loading={loadingAchievements}
      />
      
      {/* 成就通知组件 */}
      <AchievementNotification
        achievements={newlyUnlockedAchievements}
        onClose={() => setNewlyUnlockedAchievements([])}
      />
      
      {/* 挑战结果弹窗 */}
      <ChallengeResultModal
        open={challengeCompleted && challengeResult !== null}
        result={challengeResult ? {
          challengeId: challengeConfig?.id || '',
          passed: challengeResult.passed,
          finalAssets: challengeResult.finalAssets,
          targetAssets: challengeResult.targetAssets,
          returnPct: initialCash > 0 ? ((challengeResult.finalAssets - initialCash) / initialCash) * 100 : 0,
          completionDate: gameState?.currentDate || '',
        } : null}
        config={challengeConfig}
        onClose={() => {
          setChallengeCompleted(false);
          setChallengeResult(null);
        }}
        onNewChallenge={() => navigate('/')}
      />
    </Layout>
  );
}
