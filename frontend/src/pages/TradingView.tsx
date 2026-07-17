import { ArrowLeftOutlined, CaretRightFilled, PauseCircleOutlined, PlayCircleOutlined, SwapOutlined } from '@ant-design/icons';
import { Button, InputNumber, Modal, Progress, Segmented, Select, Table, Tag, message } from 'antd';
import type { TableColumnsType } from 'antd';
import axios from 'axios';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import EChartsWrapper from '../components/EChartsWrapper';
import { gameApi } from '../services/api';
import type { Account, AssetHistory, DailyBar, GameState, IndicatorPreview, PendingOrder, PerformanceMetrics, Position } from '../types';

interface TradeRow {
  orderId: string; code: string; orderType: string; price: number; quantity: number;
  status: string; filledPrice: number | null; filledQuantity: number | null; filledDate: string | null;
  fee: number; orderDate: string; rejectReason: string | null;
}

interface StockSnapshot {
  series: DailyBar[];
  indicator: IndicatorPreview;
}

type DetailPanel = 'assets' | 'positions' | 'trades' | 'curve' | null;
type PageMode = 'overview' | 'detail';
type AutoSpeed = 0.5 | 1 | 2 | 4 | 8;
type AutoSizeMode = 'lots' | 'percent';

interface AutoTradeSetting {
  mode: AutoSizeMode;
  value: number;
}

function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === 'string' ? detail : error.message;
  }
  return error instanceof Error ? error.message : '操作失败';
}

const money = (value: number) => `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const wait = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function sharesFromCashBudget(budget: number, price: number): number {
  if (budget <= 5 || price <= 0) return 0;
  return Math.max(0, Math.floor(((budget - 5) / 1.00025) / price / 100) * 100);
}

function volumeText(value = 0): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(2)}亿`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(2)}万`;
  return value.toLocaleString('zh-CN');
}

function latestIndicator(preview?: IndicatorPreview | null) {
  const valid = preview?.values.filter((item) => item.value !== null) || [];
  return valid[valid.length - 1];
}

function signalLabel(signal?: string): string {
  if (signal === 'buy') return '买入';
  if (signal === 'sell') return '卖出';
  if (signal === 'hold') return '观望';
  if (signal === 'warming_up') return '预热中';
  return '无信号';
}

function signalColor(signal?: string): string {
  if (signal === 'buy') return 'red';
  if (signal === 'sell') return 'green';
  return 'default';
}

export default function TradingView() {
  const { sessionId = '' } = useParams();
  const navigate = useNavigate();
  const [pageMode, setPageMode] = useState<PageMode>('overview');
  const [codes, setCodes] = useState<string[]>([]);
  const [stockNames, setStockNames] = useState<Record<string, string | null>>({});
  const [code, setCode] = useState('');
  const [state, setState] = useState<GameState | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [currentBars, setCurrentBars] = useState<Record<string, DailyBar>>({});
  const [stockSnapshots, setStockSnapshots] = useState<Record<string, StockSnapshot>>({});
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [assetHistory, setAssetHistory] = useState<AssetHistory | null>(null);
  const [pendingOrders, setPendingOrders] = useState<PendingOrder[]>([]);
  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [price, setPrice] = useState(0);
  const [quantity, setQuantity] = useState(100);
  const [loading, setLoading] = useState(false);
  const [detailPanel, setDetailPanel] = useState<DetailPanel>(null);
  const [autoConfigOpen, setAutoConfigOpen] = useState(false);
  const [autoLots, setAutoLots] = useState<Record<string, number>>({});
  const [autoSizeModes, setAutoSizeModes] = useState<Record<string, AutoSizeMode>>({});
  const [autoPercents, setAutoPercents] = useState<Record<string, number>>({});
  const [autoSpeed, setAutoSpeed] = useState<AutoSpeed>(1);
  const [autoRunning, setAutoRunning] = useState(false);
  const [autoStatus, setAutoStatus] = useState('尚未启动自动交易');
  const autoRunningRef = useRef(false);
  const autoSpeedRef = useRef<AutoSpeed>(1);
  const autoRunTokenRef = useRef(0);
  const autoProcessedDatesRef = useRef(new Set<string>());

  const handleRequestError = (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      message.error('这局游戏已失效，请重新创建；之后新建的游戏会在服务重启后自动恢复');
      navigate('/setup', { replace: true });
      return;
    }
    message.error(errorText(error));
  };

  useEffect(() => {
    gameApi.checkSessionExists(sessionId).then((result) => {
      if (!result.exists || !result.stock_codes?.length) {
        message.error('游戏会话不存在或已失效');
        navigate('/setup');
        return;
      }
      setCodes(result.stock_codes);
      setStockNames(result.stock_names || {});
      setCode(result.stock_codes[0]);
      setAutoLots(Object.fromEntries(result.stock_codes.map((item) => [item, 1])));
      setAutoSizeModes(Object.fromEntries(result.stock_codes.map((item) => [item, 'lots' as AutoSizeMode])));
      setAutoPercents(Object.fromEntries(result.stock_codes.map((item) => [item, 10])));
    }).catch(handleRequestError);
  }, [sessionId, navigate]);

  useEffect(() => () => {
    autoRunningRef.current = false;
    autoRunTokenRef.current += 1;
  }, []);

  const refresh = async (selectedCode = code) => {
    if (!selectedCode) return undefined;
    const activeCodes = codes.length ? codes : [selectedCode];
    const stockPromise = Promise.all(activeCodes.map(async (stockCode) => {
      const [dailySeries, indicatorResult] = await Promise.all([
        gameApi.getRevealedSeries(sessionId, stockCode),
        gameApi.getCurrentIndicator(sessionId, stockCode),
      ]);
      return [stockCode, { series: dailySeries, indicator: indicatorResult }] as const;
    }));
    const [nextState, nextAccount, bars, nextMetrics, tradeHistory, nextPendingOrders, nextAssetHistory, stockEntries] = await Promise.all([
      gameApi.getGameState(sessionId),
      gameApi.getAccount(sessionId),
      gameApi.getCurrentBars(sessionId),
      gameApi.getMetrics(sessionId),
      gameApi.getTradeHistory(sessionId),
      gameApi.getPendingOrders(sessionId),
      gameApi.getAssetHistory(sessionId),
      stockPromise,
    ]);
    const nextStockSnapshots = Object.fromEntries(stockEntries) as Record<string, StockSnapshot>;
    setState(nextState);
    setAccount(nextAccount);
    setCurrentBars(bars);
    setMetrics(nextMetrics);
    setTrades(tradeHistory);
    setPendingOrders(nextPendingOrders);
    setAssetHistory(nextAssetHistory);
    setStockSnapshots(nextStockSnapshots);
    if (bars[selectedCode]) setPrice(bars[selectedCode].close);
    return { state: nextState, account: nextAccount, bars, metrics: nextMetrics, pendingOrders: nextPendingOrders, stockSnapshots: nextStockSnapshots };
  };

  const refreshWithRetry = async (selectedCode: string, attempts = 3) => {
    let lastError: unknown;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      try {
        return await refresh(selectedCode);
      } catch (error) {
        lastError = error;
        if (attempt < attempts - 1) await wait(350 * (attempt + 1));
      }
    }
    throw lastError || new Error('刷新游戏状态失败');
  };

  const advanceAutoDay = async (currentDate: string, selectedCode: string) => {
    let lastError: unknown;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        await gameApi.nextDay(sessionId);
        return await refreshWithRetry(selectedCode);
      } catch (error) {
        lastError = error;
        try {
          const recovered = await refreshWithRetry(selectedCode);
          if (recovered?.state.currentDate !== currentDate) {
            setAutoStatus(`${currentDate}｜请求短暂失败，已恢复并继续运行`);
            return recovered;
          }
        } catch (refreshError) {
          lastError = refreshError;
        }
        if (attempt < 2) await wait(500 * (attempt + 1));
      }
    }
    throw lastError || new Error('推进交易日失败');
  };

  useEffect(() => {
    if (code) refresh(code).catch(handleRequestError);
  }, [code]);

  const nextDay = async () => {
    setLoading(true);
    try {
      await gameApi.nextDay(sessionId);
      await refresh();
    } catch (error) {
      handleRequestError(error);
    } finally {
      setLoading(false);
    }
  };

  const submit = async (side: 'buy' | 'sell', orderPrice = price) => {
    if (!code || orderPrice <= 0 || quantity <= 0 || quantity % 100 !== 0) {
      message.warning('价格需大于 0，数量需为 100 股的整数倍');
      return;
    }
    setLoading(true);
    try {
      const result = side === 'buy'
        ? await gameApi.buy({ session_id: sessionId, code, price: orderPrice, quantity })
        : await gameApi.sell({ session_id: sessionId, code, price: orderPrice, quantity });
      result.success ? message.success(result.message) : message.error(result.message);
      await refresh();
    } catch (error) {
      handleRequestError(error);
    } finally {
      setLoading(false);
    }
  };

  const cancelPendingOrder = async (orderId: string) => {
    try {
      const result = await gameApi.cancelOrder(sessionId, orderId);
      result.success ? message.success(result.message) : message.error(result.message);
      await refresh();
    } catch (error) {
      handleRequestError(error);
    }
  };

  const finishAutoTrading = (notice?: string) => {
    autoRunningRef.current = false;
    setAutoRunning(false);
    if (notice) message.success(notice);
  };

  const stopAutoTrading = () => {
    autoRunTokenRef.current += 1;
    autoRunningRef.current = false;
    setAutoRunning(false);
    setAutoStatus('用户已停止，停留在当前交易日');
    message.info('自动交易已停止');
    void refresh(codes[0] || code).catch(handleRequestError);
  };

  const runAutoTrading = async (runToken: number, settings: Record<string, AutoTradeSetting>) => {
    try {
      const selectedCode = codes[0] || code;
      let snapshot = await refreshWithRetry(selectedCode);
      while (autoRunningRef.current && autoRunTokenRef.current === runToken && snapshot) {
        const currentDate = snapshot.state.currentDate;
        if (!autoProcessedDatesRef.current.has(currentDate)) {
          const actions: Array<{ stockCode: string; side: 'buy' | 'sell'; shares: number; price: number }> = [];
          const summaries: string[] = [];
          const frozenBuyCash = snapshot.pendingOrders.reduce((total, order) => total + (order.orderType === 'buy' ? order.frozenCash : 0), 0);
          const availableCashForSignals = Math.max(0, snapshot.account.cash - frozenBuyCash);
          for (const stockCode of codes) {
            const setting = settings[stockCode] || { mode: 'lots', value: 0 };
            const indicatorValue = latestIndicator(snapshot.stockSnapshots[stockCode]?.indicator);
            const currentBar = snapshot.bars[stockCode];
            if (setting.value <= 0) {
              summaries.push(`${stockCode} 已停用`);
            } else if (!currentBar) {
              summaries.push(`${stockCode} 当前无行情`);
            } else if (!indicatorValue || indicatorValue.signal === 'warming_up') {
              summaries.push(`${stockCode} 指标预热`);
            } else if (indicatorValue.signal === 'hold') {
              summaries.push(`${stockCode} 观望`);
            } else {
              const side = indicatorValue.signal === 'buy' ? 'buy' : 'sell';
              let shares = setting.value * 100;
              if (setting.mode === 'percent' && side === 'buy') {
                const budget = availableCashForSignals * setting.value / 100;
                shares = sharesFromCashBudget(budget, currentBar.close);
              } else if (setting.mode === 'percent') {
                const position = snapshot.account.positions.find((item) => item.code === stockCode);
                const frozenShares = snapshot.pendingOrders
                  .filter((order) => order.code === stockCode && order.orderType === 'sell')
                  .reduce((total, order) => total + order.frozenQuantity, 0);
                const availableShares = Math.max(0, (position?.quantity || 0) - frozenShares);
                shares = Math.floor((availableShares * setting.value / 100) / 100) * 100;
              }
              if (shares > 0) actions.push({ stockCode, side, shares, price: currentBar.close });
              else summaries.push(`${stockCode} ${side === 'buy' ? '可用资金' : '可卖持仓'}不足 1 手`);
            }
          }

          actions.sort((left, right) => Number(left.side === 'buy') - Number(right.side === 'buy'));
          for (const action of actions) {
            if (!autoRunningRef.current || autoRunTokenRef.current !== runToken) break;
            const result = action.side === 'buy'
              ? await gameApi.buy({ session_id: sessionId, code: action.stockCode, price: action.price, quantity: action.shares })
              : await gameApi.sell({ session_id: sessionId, code: action.stockCode, price: action.price, quantity: action.shares });
            summaries.push(`${action.stockCode} ${action.side === 'buy' ? '买' : '卖'}${action.shares}股：${result.message}`);
          }
          autoProcessedDatesRef.current.add(currentDate);
          setAutoStatus(`${currentDate}｜${summaries.join('；') || '没有触发交易'}`);
        }

        if (!snapshot || !autoRunningRef.current || autoRunTokenRef.current !== runToken) break;
        if (snapshot.state.isLastDay) {
          await refreshWithRetry(selectedCode);
          setAutoStatus('已运行到本局最后一个交易日');
          finishAutoTrading('自动交易已运行到最后一个交易日');
          break;
        }

        await wait(1000 / autoSpeedRef.current);
        if (!autoRunningRef.current || autoRunTokenRef.current !== runToken) break;
        snapshot = await advanceAutoDay(currentDate, selectedCode);
      }
    } catch (error) {
      finishAutoTrading();
      setAutoStatus(`自动交易中断：${errorText(error)}`);
      handleRequestError(error);
    }
  };

  const startAutoTrading = () => {
    if (state?.isLastDay) return message.warning('已经到达最后一个交易日');
    const settings = Object.fromEntries(codes.map((item) => {
      const mode = autoSizeModes[item] || 'lots';
      return [item, { mode, value: mode === 'percent' ? (autoPercents[item] || 0) : (autoLots[item] || 0) }];
    })) as Record<string, AutoTradeSetting>;
    if (!codes.some((item) => settings[item].value > 0)) return message.warning('请至少启用一只股票的自动交易仓位');
    if (!codes.some((item) => stockSnapshots[item]?.indicator.definition)) return message.warning('本局没有可用于自动交易的指标');
    const runToken = autoRunTokenRef.current + 1;
    autoRunTokenRef.current = runToken;
    autoRunningRef.current = true;
    autoSpeedRef.current = 1;
    setAutoSpeed(1);
    setAutoRunning(true);
    setAutoConfigOpen(false);
    setAutoStatus('自动交易已启动（1×），正在处理当前交易日');
    void runAutoTrading(runToken, settings);
  };

  const changeAutoSpeed = (value: string | number) => {
    const nextSpeed = Number(value) as AutoSpeed;
    autoSpeedRef.current = nextSpeed;
    setAutoSpeed(nextSpeed);
    setAutoStatus(`自动交易速度已切换为 ${nextSpeed}×，下一交易日起生效`);
  };

  const openStockDetail = (selectedCode: string) => {
    if (autoRunning) return;
    setCode(selectedCode);
    setPageMode('detail');
  };

  const series = stockSnapshots[code]?.series || [];
  const indicator = stockSnapshots[code]?.indicator || null;
  const bar = currentBars[code];
  const changePct = series.length > 1 ? (series[series.length - 1].close / series[series.length - 2].close - 1) * 100 : 0;
  const latestSignal = latestIndicator(indicator);
  const progress = state && state.totalDates ? ((state.dateIndex + 1) / state.totalDates) * 100 : 0;
  const frozenCash = pendingOrders.reduce((total, order) => total + (order.orderType === 'buy' ? order.frozenCash : 0), 0);
  const availableCash = Math.max(0, (account?.cash || 0) - frozenCash);

  const chartOption = useMemo<Record<string, unknown>>(() => {
    const dates = series.map((item) => item.date);
    const indicatorMap = new Map((indicator?.values || []).map((item) => [item.date, item.value]));
    const hasIndicator = Boolean(indicator?.definition);
    return {
      backgroundColor: 'transparent', animation: false,
      legend: { top: 4, right: 16, textStyle: { color: '#8f9ba7' }, data: hasIndicator ? ['日K', indicator?.definition?.name] : ['日K'] },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: '#0d141c', borderColor: '#33404d', textStyle: { color: '#d8e0e8' } },
      axisPointer: { link: [{ xAxisIndex: 'all' }], label: { backgroundColor: '#26313d' } },
      grid: [
        { left: 62, right: 58, top: 38, height: hasIndicator ? '44%' : '68%' },
        { left: 62, right: 58, top: hasIndicator ? '53%' : '77%', height: hasIndicator ? '9%' : '12%' },
        { left: 62, right: 58, top: '67%', height: hasIndicator ? '23%' : 0 },
      ],
      xAxis: [0, 1, 2].map((index) => ({ type: 'category', gridIndex: index, data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#33404d' } }, axisLabel: { color: '#74818e', show: index === (hasIndicator ? 2 : 1) }, splitLine: { show: false }, min: 'dataMin', max: 'dataMax' })),
      yAxis: [
        { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: '#1d2732' } }, axisLabel: { color: '#74818e' } },
        { scale: true, gridIndex: 1, splitNumber: 2, splitLine: { show: false }, axisLabel: { color: '#74818e', formatter: (value: number) => `${(value / 10000).toFixed(0)}万` } },
        { scale: true, gridIndex: 2, splitNumber: 2, splitLine: { lineStyle: { color: '#1d2732' } }, axisLabel: { color: '#74818e' } },
      ],
      dataZoom: [{ type: 'inside', xAxisIndex: [0, 1, 2], start: Math.max(0, 100 - 10000 / Math.max(100, dates.length)) }, { type: 'slider', xAxisIndex: [0, 1, 2], bottom: 3, height: 16, borderColor: '#26313d', fillerColor: '#31415455' }],
      series: [
        { name: '日K', type: 'candlestick', xAxisIndex: 0, yAxisIndex: 0, data: series.map((item) => [item.open, item.close, item.low, item.high]), itemStyle: { color: '#d85151', color0: '#1ca678', borderColor: '#d85151', borderColor0: '#1ca678' } },
        { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: series.map((item) => ({ value: item.volume, itemStyle: { color: item.close >= item.open ? '#d8515177' : '#1ca67877' } })) },
        ...(hasIndicator ? [
          { name: indicator?.definition?.name, type: 'line', xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, connectNulls: false, data: dates.map((date) => indicatorMap.get(date) ?? null), lineStyle: { color: '#d6aa48', width: 2 }, areaStyle: { color: '#d6aa480d' } },
          { name: '买入阈值', type: 'line', xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, silent: true, tooltip: { show: false }, data: dates.map(() => indicator?.definition?.buy_threshold), lineStyle: { color: '#d85151', width: 1, type: 'dashed', opacity: 0.75 } },
          { name: '卖出阈值', type: 'line', xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, silent: true, tooltip: { show: false }, data: dates.map(() => indicator?.definition?.sell_threshold), lineStyle: { color: '#1ca678', width: 1, type: 'dashed', opacity: 0.75 } },
        ] : []),
      ],
    };
  }, [series, indicator]);

  const curveHistory = useMemo(() => {
    const points = [...(assetHistory?.history || [])];
    if (!assetHistory || !account || !state?.currentDate) return points;
    const previousAssets = points.length > 0 ? points[points.length - 1].totalAssets : assetHistory.initialCash;
    const livePoint = {
      date: state.currentDate,
      totalAssets: account.totalAssets,
      cash: account.cash,
      marketValue: account.totalMarketValue,
      dailyReturn: previousAssets > 0 ? (account.totalAssets - previousAssets) / previousAssets : 0,
      dailyProfit: account.totalAssets - previousAssets,
      cumulativeReturn: assetHistory.initialCash > 0 ? (account.totalAssets - assetHistory.initialCash) / assetHistory.initialCash : 0,
    };
    if (points[points.length - 1]?.date === state.currentDate) points[points.length - 1] = livePoint;
    else points.push(livePoint);
    return points;
  }, [assetHistory, account, state?.currentDate]);

  const stockProfitSeries = useMemo(() => {
    const dates = curveHistory.map((item) => item.date);
    const colors = ['#4c9bd6', '#d85151', '#1ca678', '#b58bd3', '#e07a5f', '#5fb3a2'];
    if (!dates.length) return [];

    return codes.map((stockCode, index) => {
      const closes = new Map(
        (stockSnapshots[stockCode]?.series || []).map((bar) => [bar.date, bar.close]),
      );
      const fillsByDate = new Map<string, TradeRow[]>();
      trades
        .filter((trade) => trade.code === stockCode && trade.status === 'filled' && trade.filledPrice !== null)
        .forEach((trade) => {
          const fillDate = trade.filledDate || trade.orderDate;
          fillsByDate.set(fillDate, [...(fillsByDate.get(fillDate) || []), trade]);
        });

      let quantity = 0;
      let netCashFlow = 0;
      let lastClose: number | null = null;
      const data = dates.map((date) => {
        const close = closes.get(date);
        if (close !== undefined) lastClose = close;
        for (const trade of fillsByDate.get(date) || []) {
          const filledQuantity = trade.filledQuantity || trade.quantity;
          const filledAmount = Number(trade.filledPrice) * filledQuantity;
          if (trade.orderType === 'buy') {
            quantity += filledQuantity;
            netCashFlow -= filledAmount + trade.fee;
          } else {
            quantity = Math.max(0, quantity - filledQuantity);
            netCashFlow += filledAmount - trade.fee;
          }
        }
        const marketValue = lastClose === null ? 0 : quantity * lastClose;
        return Number((netCashFlow + marketValue).toFixed(2));
      });

      return {
        name: stockNames[stockCode] ? `${stockNames[stockCode]} ${stockCode}` : stockCode,
        type: 'line',
        yAxisIndex: 0,
        showSymbol: false,
        connectNulls: false,
        data,
        lineStyle: { color: colors[index % colors.length], width: 1.5 },
        itemStyle: { color: colors[index % colors.length] },
      };
    });
  }, [codes, curveHistory, stockNames, stockSnapshots, trades]);

  const assetCurveOption = useMemo<Record<string, unknown>>(() => ({
    backgroundColor: 'transparent', animation: false,
    legend: {
      top: 4,
      right: 14,
      data: ['账户总盈亏', ...stockProfitSeries.map((item) => item.name)],
      textStyle: { color: '#a9b4bf' },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0d141c',
      borderColor: '#33404d',
      textStyle: { color: '#d8e0e8' },
      formatter: (params: Array<{ dataIndex: number; seriesName: string; value: number | null; color: string }>) => {
        const point = curveHistory[params[0]?.dataIndex];
        if (!point) return '';
        const stockLines = params
          .filter((item) => item.seriesName !== '账户总盈亏' && typeof item.value === 'number')
          .map((item) => `<br/><span style="color:${item.color}">●</span> ${item.seriesName}　${money(Number(item.value))}`)
          .join('');
        return `${point.date}<br/>账户总盈亏　${money(point.totalAssets - (assetHistory?.initialCash || 0))}<br/>总资产　${money(point.totalAssets)}<br/>累计收益率　${pct(point.cumulativeReturn)}${stockLines}`;
      },
    },
    grid: { left: 72, right: 34, top: 58, bottom: 58 },
    xAxis: { type: 'category', data: curveHistory.map((item) => item.date), boundaryGap: false, axisLine: { lineStyle: { color: '#33404d' } }, axisLabel: { color: '#74818e' } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#74818e', formatter: (value: number) => `${(value / 10000).toFixed(1)}万` }, splitLine: { lineStyle: { color: '#1d2732' } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 17, bottom: 8, borderColor: '#26313d', fillerColor: '#31415455' }],
    series: [
      {
        name: '账户总盈亏', type: 'line', yAxisIndex: 0, showSymbol: false,
        data: curveHistory.map((item) => item.totalAssets - (assetHistory?.initialCash || 0)),
        lineStyle: { color: '#d6aa48', width: 2 },
        areaStyle: { color: '#d6aa4814' },
        markLine: {
          silent: true,
          symbol: 'none',
          label: { formatter: '盈亏平衡', color: '#7f8c99', position: 'insideEndTop' },
          lineStyle: { color: '#64717e', type: 'dashed', width: 1 },
          data: [{ yAxis: 0 }],
        },
      },
      ...stockProfitSeries,
    ],
  }), [curveHistory, assetHistory?.initialCash, stockProfitSeries]);

  const positionColumns: TableColumnsType<Position> = [
    { title: '代码', dataIndex: 'code', render: (value) => <span className="mono strong">{value}</span> },
    { title: '数量', dataIndex: 'quantity', align: 'right', render: (value) => <span className="mono">{value.toLocaleString()}</span> },
    { title: '成本', dataIndex: 'costPrice', align: 'right', render: (value) => <span className="mono">{value.toFixed(2)}</span> },
    { title: '现价', dataIndex: 'currentPrice', align: 'right', render: (value) => <span className="mono">{value.toFixed(2)}</span> },
    { title: '盈亏', dataIndex: 'profitLoss', align: 'right', render: (value, row) => <span className={value >= 0 ? 'market-up mono' : 'market-down mono'}>{money(value)} / {row.profitLossPct.toFixed(2)}%</span> },
  ];

  const pendingColumns: TableColumnsType<PendingOrder> = [
    { title: '代码', dataIndex: 'code', width: 90, render: (value) => <span className="mono">{value}</span> },
    { title: '方向', dataIndex: 'orderType', width: 70, render: (value) => <Tag color={value === 'buy' ? 'red' : 'green'}>{value === 'buy' ? '买' : '卖'}</Tag> },
    { title: '委托价', dataIndex: 'price', align: 'right', render: (value) => <span className="mono">{value.toFixed(2)}</span> },
    { title: '数量', dataIndex: 'quantity', align: 'right' },
    { title: '冻结', key: 'frozen', align: 'right', render: (_, row) => <span className="mono">{row.orderType === 'buy' ? money(row.frozenCash) : `${row.frozenQuantity} 股`}</span> },
    { title: '操作', key: 'action', width: 75, render: (_, row) => <Button type="link" size="small" disabled={autoRunning} onClick={() => cancelPendingOrder(row.orderId)}>撤单</Button> },
  ];

  const tradeColumns: TableColumnsType<TradeRow> = [
    { title: '日期', dataIndex: 'orderDate', width: 105 }, { title: '代码', dataIndex: 'code', width: 85, render: (value) => <span className="mono">{value}</span> },
    { title: '方向', dataIndex: 'orderType', width: 65, render: (value) => <Tag color={value === 'buy' ? 'red' : 'green'}>{value === 'buy' ? '买' : '卖'}</Tag> },
    { title: '成交价', dataIndex: 'filledPrice', align: 'right', render: (value, row) => <span className="mono">{(value ?? row.price).toFixed(2)}</span> },
    { title: '数量', dataIndex: 'quantity', align: 'right' },
    { title: '费用', dataIndex: 'fee', align: 'right', render: (value) => <span className="mono">{value.toFixed(2)}</span> },
    { title: '状态', dataIndex: 'status', render: (value) => value === 'filled' ? '已成交' : value === 'cancelled' ? '已撤单' : '未成交' },
  ];

  const progressBlock = <div className="day-progress"><span>{state?.currentDate || '—'}</span><Progress percent={progress} showInfo={false} strokeColor="#d6aa48" trailColor="#26313d" /><small>{state ? `${state.dateIndex + 1} / ${state.totalDates} 个交易日` : '加载中'}</small></div>;

  return (
    <div className="trading-workspace">
      {pageMode === 'overview' ? <>
        <div className="trading-toolbar overview-toolbar">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>退出模拟</Button>
          <div className="overview-toolbar-title"><strong>本局股票总览</strong><small>{codes.length} 只标的{autoRunning ? ` · ${autoSpeed}× 自动运行` : ''}</small></div>
          {progressBlock}
          <Button icon={<CaretRightFilled />} loading={loading} disabled={autoRunning || state?.isLastDay} onClick={nextDay}>{state?.isLastDay ? '模拟已结束' : '手动推进一天'}</Button>
          <div className="auto-run-controls">
            {autoRunning && <div className="auto-speed-inline"><span>速度</span><Segmented size="small" value={autoSpeed} options={[{ label: '0.5×', value: 0.5 }, { label: '1×', value: 1 }, { label: '2×', value: 2 }, { label: '4×', value: 4 }, { label: '8×', value: 8 }]} onChange={changeAutoSpeed} /></div>}
            <Button type={autoRunning ? 'default' : 'primary'} danger={autoRunning} icon={autoRunning ? <PauseCircleOutlined /> : <PlayCircleOutlined />} onClick={autoRunning ? stopAutoTrading : () => setAutoConfigOpen(true)}>{autoRunning ? '停止自动买卖' : '按指标自动买卖'}</Button>
          </div>
        </div>

        <main className="simulation-overview">
          <section className="terminal-panel watchlist-panel">
            <div className="panel-title"><span>股票与指标监控</span><small className={autoRunning ? 'auto-live' : ''}>{autoRunning ? '● 自动运行中' : '未自动运行时，点击股票名称进入挂单界面'}</small></div>
            <div className="watchlist-header"><span>股票</span><span>最新价</span><span>当日量价</span><span>成交量</span><span>指标状态</span><span>持仓 / 挂单</span></div>
            <div className="watchlist-body">{codes.map((stockCode) => {
              const currentBar = currentBars[stockCode];
              const snapshot = stockSnapshots[stockCode];
              const previousBar = snapshot?.series[snapshot.series.length - 2];
              const dailyChange = currentBar && previousBar ? (currentBar.close / previousBar.close - 1) * 100 : 0;
              const indicatorValue = latestIndicator(snapshot?.indicator);
              const definition = snapshot?.indicator.definition;
              const position = account?.positions.find((item) => item.code === stockCode);
              const stockPending = pendingOrders.filter((item) => item.code === stockCode);
              return <article className="watchlist-row" key={stockCode}>
                <button type="button" className="stock-name-button" disabled={autoRunning} onClick={() => openStockDetail(stockCode)}><strong>{stockNames[stockCode] || '名称待更新'}</strong><span className="mono">{stockCode}</span><small>{!currentBar ? '当前日期尚无行情' : autoRunning ? '运行中不可进入' : '点击查看 K 线与挂单'}</small></button>
                <div className="watch-price"><strong className="mono">{currentBar?.close.toFixed(2) ?? '—'}</strong><span className={currentBar ? (dailyChange >= 0 ? 'market-up' : 'market-down') : ''}>{currentBar ? `${dailyChange >= 0 ? '+' : ''}${dailyChange.toFixed(2)}%` : '无行情'}</span></div>
                <div className="watch-ohlc"><span>开 <b>{currentBar?.open.toFixed(2) ?? '—'}</b></span><span>高 <b className="market-up">{currentBar?.high.toFixed(2) ?? '—'}</b></span><span>低 <b className="market-down">{currentBar?.low.toFixed(2) ?? '—'}</b></span><span>收 <b>{currentBar?.close.toFixed(2) ?? '—'}</b></span></div>
                <div className="watch-volume"><strong className="mono">{volumeText(currentBar?.volume)}</strong><span>当日成交量</span></div>
                <div className="watch-indicator"><div><span>{definition?.name || '未配置指标'}</span><Tag color={currentBar ? signalColor(indicatorValue?.signal) : 'default'}>{currentBar ? signalLabel(indicatorValue?.signal) : '无行情'}</Tag></div><strong className="mono">{indicatorValue?.value?.toFixed(3) ?? '—'}</strong>{definition && <small>买入 ≥ {definition.buy_threshold} · 卖出 ≤ {definition.sell_threshold}</small>}</div>
                <div className="watch-position"><strong className="mono">{position ? `${position.quantity.toLocaleString()} 股` : '无持仓'}</strong><span className={(position?.profitLoss || 0) >= 0 ? 'market-up' : 'market-down'}>{position ? `${money(position.profitLoss)} / ${position.profitLossPct.toFixed(2)}%` : '—'}</span><small>{stockPending.length ? `${stockPending.length} 笔挂单优先` : '无挂单'}</small></div>
              </article>;
            })}</div>
          </section>

          <section className="terminal-panel overview-account-panel">
            <div className="panel-title"><span>账户与收益</span><small>{autoStatus}</small></div>
            <div className="overview-account-grid">
              <div><span>总资产</span><strong className="mono">{account ? money(account.totalAssets) : '—'}</strong></div>
              <div><span>现金余额</span><strong className="mono">{account ? money(account.cash) : '—'}</strong></div>
              <div><span>挂单冻结</span><strong className="mono">{money(frozenCash)}</strong></div>
              <div><span>指标可用资金</span><strong className="mono">{money(availableCash)}</strong></div>
              <div><span>累计收益</span><strong className={`mono ${(metrics?.totalReturn || 0) >= 0 ? 'market-up' : 'market-down'}`}>{metrics ? pct(metrics.totalReturn) : '—'}</strong></div>
              <div><span>最大回撤</span><strong className="mono market-down">{metrics ? pct(metrics.maxDrawdown) : '—'}</strong></div>
              <button type="button" onClick={() => setDetailPanel('positions')}><span>持仓</span><strong>{account?.positions.length || 0}</strong><small>展开</small></button>
              <button type="button" onClick={() => setDetailPanel('trades')}><span>挂单 / 成交</span><strong>{pendingOrders.length} / {trades.length}</strong><small>展开</small></button>
              <button type="button" className="overview-curve-button" onClick={() => setDetailPanel('curve')}><span>资产曲线</span><strong>↗</strong><small>{assetHistory ? pct(assetHistory.totalReturn) : '查看收益'}</small></button>
            </div>
          </section>
        </main>
      </> : <>
        <div className="trading-toolbar">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setPageMode('overview')}>返回股票列表</Button>
          <Select value={code} onChange={setCode} options={codes.map((item) => ({ value: item, label: stockNames[item] ? `${stockNames[item]}  ${item}` : item }))} className="symbol-select" popupMatchSelectWidth={220} />
          <div className="quote-block"><strong className="mono">{bar?.close.toFixed(2) ?? '—'}</strong><span className={changePct >= 0 ? 'market-up' : 'market-down'}>{changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%</span></div>
          {progressBlock}
          <Button type="primary" icon={<CaretRightFilled />} loading={loading} disabled={state?.isLastDay} onClick={nextDay}>{state?.isLastDay ? '模拟已结束' : '推进下一交易日'}</Button>
        </div>

        <div className="trading-grid">
          <section className="terminal-panel chart-panel"><EChartsWrapper option={chartOption} style={{ width: '100%', height: '100%' }} /></section>
          <aside className="terminal-panel order-panel">
            <div className="panel-title"><span>日线委托</span><small>挂单与指标相互独立</small></div>
            <div className="ohlc-strip"><span>开 <b>{bar?.open.toFixed(2) ?? '—'}</b></span><span>高 <b className="market-up">{bar?.high.toFixed(2) ?? '—'}</b></span><span>低 <b className="market-down">{bar?.low.toFixed(2) ?? '—'}</b></span><span>收 <b>{bar?.close.toFixed(2) ?? '—'}</b></span></div>
            <label className="field-label">委托价格</label><InputNumber value={price} min={0.01} precision={2} step={0.01} onChange={(value) => setPrice(value ?? 0)} addonBefore="¥" />
            <label className="field-label">委托数量</label><InputNumber value={quantity} min={100} step={100} onChange={(value) => setQuantity(value ?? 100)} addonAfter="股" />
            <div className="order-estimate"><span>预计金额</span><strong className="mono">{money(price * quantity)}</strong></div>
            <div className="order-buttons"><Button className="buy-button" loading={loading} onClick={() => submit('buy')}>买入</Button><Button className="sell-button" loading={loading} onClick={() => submit('sell')}>卖出</Button></div>
            <div className="indicator-readout"><div><SwapOutlined /><span>{indicator?.definition?.name || '未加载指标'}</span></div><strong className="mono">{latestSignal?.value?.toFixed(3) ?? '—'}</strong><Tag color={signalColor(latestSignal?.signal)}>{signalLabel(latestSignal?.signal)}</Tag></div>
            <p className="order-note">挂单会冻结对应资金或持仓，并在新交易日优先撮合；以后启动指标自动交易时，只会使用剩余可用资金。</p>
          </aside>

          <section className="terminal-panel trading-dock" aria-label="账户与交易摘要">
            <button type="button" className="dock-metric" onClick={() => setDetailPanel('assets')}><span>总资产</span><strong className="mono">{account ? money(account.totalAssets) : '—'}</strong></button>
            <button type="button" className="dock-metric" onClick={() => setDetailPanel('assets')}><span>指标可用资金</span><strong className="mono">{money(availableCash)}</strong></button>
            <button type="button" className="dock-metric" onClick={() => setDetailPanel('assets')}><span>累计收益</span><strong className={`mono ${(metrics?.totalReturn || 0) >= 0 ? 'market-up' : 'market-down'}`}>{metrics ? pct(metrics.totalReturn) : '—'}</strong></button>
            <button type="button" className="dock-metric" onClick={() => setDetailPanel('assets')}><span>最大回撤</span><strong className="mono market-down">{metrics ? pct(metrics.maxDrawdown) : '—'}</strong></button>
            <button type="button" className="dock-metric" onClick={() => setDetailPanel('assets')}><span>交易次数</span><strong className="mono">{metrics?.totalTrades ?? 0}</strong></button>
            <button type="button" className="dock-action" onClick={() => setDetailPanel('positions')}><span>当前持仓</span><strong>{account?.positions.length || 0}</strong><small>点击展开</small></button>
            <button type="button" className="dock-action" onClick={() => setDetailPanel('trades')}><span>挂单 / 成交</span><strong>{pendingOrders.length}/{trades.length}</strong><small>点击展开</small></button>
            <button type="button" className="dock-action dock-curve" onClick={() => setDetailPanel('curve')}><span>资产曲线</span><strong>↗</strong><small>{assetHistory ? pct(assetHistory.totalReturn) : '点击查看'}</small></button>
          </section>
        </div>
      </>}

      <Modal open={autoConfigOpen} title="按指标自动买卖" onCancel={() => setAutoConfigOpen(false)} onOk={startAutoTrading} okText="开始自动运行" cancelText="取消" width={780} className="trading-detail-modal">
        <div className="auto-trade-note">固定手数模式按相同手数买卖；比例模式买入使用指标可用现金的设定比例，卖出使用可卖持仓的同一比例，均向下取整到整手。系统以 1× 启动，运行后可在页面顶部切换到 8×。</div>
        <div className="auto-lot-list">{codes.map((stockCode) => {
          const indicatorValue = latestIndicator(stockSnapshots[stockCode]?.indicator);
          const hasCurrentBar = Boolean(currentBars[stockCode]);
          const sizeMode = autoSizeModes[stockCode] || 'lots';
          return <div className="auto-lot-row" key={stockCode}>
            <div><strong>{stockNames[stockCode] || '名称待更新'}</strong><span className="mono">{stockCode}</span></div>
            <div><span>当前指标</span><Tag color={hasCurrentBar ? signalColor(indicatorValue?.signal) : 'default'}>{hasCurrentBar ? signalLabel(indicatorValue?.signal) : '无行情'}</Tag><b className="mono">{indicatorValue?.value?.toFixed(3) ?? '—'}</b></div>
            <div className="auto-size-control"><Segmented block size="small" value={sizeMode} options={[{ label: '固定手数', value: 'lots' }, { label: '资金比例', value: 'percent' }]} onChange={(value) => setAutoSizeModes({ ...autoSizeModes, [stockCode]: value as AutoSizeMode })} />{sizeMode === 'lots'
              ? <InputNumber min={0} max={10000} step={1} precision={0} value={autoLots[stockCode] || 0} addonAfter="手" onChange={(value) => setAutoLots({ ...autoLots, [stockCode]: value ?? 0 })} />
              : <InputNumber min={0} max={100} step={5} precision={0} value={autoPercents[stockCode] || 0} addonAfter="%" onChange={(value) => setAutoPercents({ ...autoPercents, [stockCode]: value ?? 0 })} />}</div>
            <small>{sizeMode === 'lots' ? `每次买卖 ${(autoLots[stockCode] || 0) * 100} 股` : `买入用现金、卖出用持仓的 ${autoPercents[stockCode] || 0}%`}；设为 0 表示停用</small>
          </div>;
        })}</div>
      </Modal>

      <Modal open={detailPanel !== null} title={detailPanel === 'assets' ? '资产与绩效' : detailPanel === 'positions' ? '当前持仓' : detailPanel === 'trades' ? '挂单与成交' : '资产曲线'} onCancel={() => setDetailPanel(null)} footer={null} width={detailPanel === 'assets' ? 720 : detailPanel === 'curve' ? 980 : 900} className="trading-detail-modal">
        {detailPanel === 'assets' && <div className="asset-detail-grid">
          <div><span>总资产</span><strong className="mono">{account ? money(account.totalAssets) : '—'}</strong></div>
          <div><span>现金余额</span><strong className="mono">{account ? money(account.cash) : '—'}</strong></div>
          <div><span>挂单冻结</span><strong className="mono">{money(frozenCash)}</strong></div>
          <div><span>指标可用资金</span><strong className="mono">{money(availableCash)}</strong></div>
          <div><span>累计收益</span><strong className={`mono ${(metrics?.totalReturn || 0) >= 0 ? 'market-up' : 'market-down'}`}>{metrics ? pct(metrics.totalReturn) : '—'}</strong></div>
          <div><span>最大回撤</span><strong className="mono market-down">{metrics ? pct(metrics.maxDrawdown) : '—'}</strong></div>
          <div><span>胜率</span><strong className="mono">{metrics ? pct(metrics.winRate) : '—'}</strong></div>
          <div><span>交易次数</span><strong className="mono">{metrics?.totalTrades ?? 0}</strong></div>
        </div>}
        {detailPanel === 'positions' && <Table rowKey="code" columns={positionColumns} dataSource={account?.positions || []} pagination={false} size="small" scroll={{ x: 720, y: 420 }} locale={{ emptyText: '暂无持仓' }} />}
        {detailPanel === 'trades' && <div className="orders-modal-stack"><section><h3>当前挂单 <small>{pendingOrders.length} 笔</small></h3><Table rowKey="orderId" columns={pendingColumns} dataSource={pendingOrders} pagination={false} size="small" scroll={{ x: 720, y: 180 }} locale={{ emptyText: '暂无挂单' }} /></section><section><h3>成交与历史委托 <small>{trades.length} 条</small></h3><Table rowKey="orderId" columns={tradeColumns} dataSource={trades} pagination={{ pageSize: 6, size: 'small' }} size="small" scroll={{ x: 780, y: 240 }} locale={{ emptyText: '暂无交易记录' }} /></section></div>}
        {detailPanel === 'curve' && <div className="asset-curve-panel"><div className="curve-summary"><div><span>初始资产</span><strong className="mono">{assetHistory ? money(assetHistory.initialCash) : '—'}</strong></div><div><span>当前资产</span><strong className="mono">{account ? money(account.totalAssets) : '—'}</strong></div><div><span>累计收益率</span><strong className={`mono ${(assetHistory?.totalReturn || 0) >= 0 ? 'market-up' : 'market-down'}`}>{assetHistory ? pct(assetHistory.totalReturn) : '—'}</strong></div></div><div className="curve-chart-note">金色为账户累计总盈亏；单股线为该股票实际成交产生的累计盈亏贡献，包含已实现盈亏、当前持仓浮动盈亏和交易费用。所有曲线共用左侧金额刻度，点击图例可显示或隐藏。</div><EChartsWrapper option={assetCurveOption} style={{ width: '100%', height: 400 }} /></div>}
      </Modal>
    </div>
  );
}
