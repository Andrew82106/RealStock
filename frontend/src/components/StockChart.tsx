/**
 * K线图组件 - 支持技术指标（MA、MACD）和买卖标记
 */
import { useMemo, useRef, useState } from 'react';
import { Select, Tag, Switch, Tooltip } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '../contexts/ThemeContext';
import type { DailyBar, StockInfo, SaveTradeRecord } from '../types';

interface StockChartProps {
  code: string;
  dailyData: DailyBar[];
  stockCodes: string[];
  stockInfoMap?: Record<string, StockInfo>;
  onStockChange: (code: string) => void;
  currentPrice?: number;
  tickIndex?: number;
  intradayHigh?: number;
  intradayLow?: number;
  tradeHistory?: SaveTradeRecord[];
}

// 计算移动平均线
function calculateMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j];
      }
      result.push(sum / period);
    }
  }
  return result;
}

// 计算 MACD
function calculateMACD(closes: number[], fast = 12, slow = 26, signal = 9) {
  const emaFast: number[] = [];
  const emaSlow: number[] = [];
  const dif: number[] = [];
  const dea: number[] = [];
  const macd: number[] = [];

  const kFast = 2 / (fast + 1);
  const kSlow = 2 / (slow + 1);
  const kSignal = 2 / (signal + 1);

  for (let i = 0; i < closes.length; i++) {
    if (i === 0) {
      emaFast.push(closes[i]);
      emaSlow.push(closes[i]);
    } else {
      emaFast.push(closes[i] * kFast + emaFast[i - 1] * (1 - kFast));
      emaSlow.push(closes[i] * kSlow + emaSlow[i - 1] * (1 - kSlow));
    }
    dif.push(emaFast[i] - emaSlow[i]);
  }

  for (let i = 0; i < dif.length; i++) {
    if (i === 0) {
      dea.push(dif[i]);
    } else {
      dea.push(dif[i] * kSignal + dea[i - 1] * (1 - kSignal));
    }
    macd.push((dif[i] - dea[i]) * 2);
  }

  return { dif, dea, macd };
}

// 计算韭菜共振指数 LRI (Leek Resonance Index)
// 与后端 experiments/holy_grail/grail_indicator.py 完全一致：
//   动量共振核 M = 0.7·EMA3(日收益%) + 0.3·EMA8(日收益%)
//   量能激励项 V = ln(1 + Vol / MA5(Vol))
//   玄学修正   Θ = 1 + 0.08·sin(2π·交易日序号/8)
//   LRI = 100·sigmoid( M·(1 + 0.5·V)·Θ )，≥88 买入，≤44 清仓
function calculateLRI(bars: Array<{ close: number; volume: number }>): (number | null)[] {
  const EMA_FAST = 3, EMA_SLOW = 8, VOL_MA = 5;
  const FAITH_K = 1.0, FOLLOW_BETA = 0.5, MYSTIC_PERIOD = 8, MYSTIC_AMP = 0.08;

  let emaFast: number | null = null;
  let emaSlow: number | null = null;
  let prevClose: number | null = null;
  const volWindow: number[] = [];
  const result: (number | null)[] = [];
  let dayIndex = 0;

  for (const bar of bars) {
    dayIndex++;
    if (prevClose === null || prevClose <= 0) {
      prevClose = bar.close;
      volWindow.push(bar.volume);
      result.push(null);
      continue;
    }

    const retPct = (bar.close - prevClose) / prevClose * 100;
    prevClose = bar.close;

    const aF = 2 / (EMA_FAST + 1);
    const aS = 2 / (EMA_SLOW + 1);
    emaFast = emaFast === null ? retPct : aF * retPct + (1 - aF) * emaFast;
    emaSlow = emaSlow === null ? retPct : aS * retPct + (1 - aS) * emaSlow;
    const momentum = 0.7 * emaFast + 0.3 * emaSlow;

    const win = volWindow.slice(-VOL_MA);
    const volMa = win.length ? win.reduce((a, b) => a + b, 0) / win.length : 0;
    const volTerm = volMa > 0 ? Math.log(1 + bar.volume / volMa) : 0;
    volWindow.push(bar.volume);

    const mystic = 1 + MYSTIC_AMP * Math.sin(2 * Math.PI * dayIndex / MYSTIC_PERIOD);

    const x = FAITH_K * momentum * (1 + FOLLOW_BETA * volTerm) * mystic;
    const sig = x > 50 ? 1 : x < -50 ? 0 : 1 / (1 + Math.exp(-x));
    result.push(100 * sig);
  }
  return result;
}

export const LRI_BUY_LEVEL = 88;
export const LRI_SELL_LEVEL = 44;

export default function StockChart({
  code, 
  dailyData, 
  stockCodes,
  stockInfoMap = {},
  onStockChange,
  currentPrice,
  tickIndex,
  intradayHigh,
  intradayLow,
  tradeHistory = [],
}: StockChartProps) {
  const chartRef = useRef<ReactECharts>(null);
  const [showTrades, setShowTrades] = useState(true);
  const { theme } = useTheme();
  
  const colors = {
    text: theme === 'dark' ? '#c9d1d9' : '#1f2937',
    textSecondary: theme === 'dark' ? '#8b949e' : '#6b7280',
    border: theme === 'dark' ? '#30363d' : '#e5e7eb',
    gridLine: theme === 'dark' ? '#21262d' : '#f3f4f6',
    tooltipBg: theme === 'dark' ? 'rgba(22,27,34,0.95)' : 'rgba(255,255,255,0.95)',
    sliderBg: theme === 'dark' ? '#161b22' : '#f9fafb',
    ma5: '#f5c242',
    ma10: '#42a5f5',
    ma20: '#ab47bc',
    ma50: '#26a69a',
    ma100: '#ef5350',
    ma120: '#ff7043',
  };
  
  const stockName = stockInfoMap[code]?.name || '';
  const displayName = stockName ? `${code} ${stockName}` : code;

  // 计算当日K线数据
  const lastBarData = useMemo(() => {
    if (!dailyData.length) return null;
    const lastBar = dailyData[dailyData.length - 1];
    const price = currentPrice && currentPrice > 0 ? currentPrice : lastBar.close;
    const high = intradayHigh !== undefined ? Math.max(lastBar.open, intradayHigh) : Math.max(lastBar.high, price);
    const low = intradayLow !== undefined ? Math.min(lastBar.open, intradayLow) : Math.min(lastBar.low, price);
    return { open: lastBar.open, close: price, high, low, volume: lastBar.volume, date: lastBar.date };
  }, [dailyData, currentPrice, intradayHigh, intradayLow]);

  // 计算涨跌幅
  const { changePercent, isUp } = useMemo(() => {
    if (!dailyData.length || !lastBarData) return { changePercent: '0.00', isUp: true };
    const prevBar = dailyData.length > 1 ? dailyData[dailyData.length - 2] : null;
    const prevClose = prevBar ? prevBar.close : lastBarData.open;
    const change = ((lastBarData.close - prevClose) / prevClose * 100).toFixed(2);
    return { changePercent: change, isUp: lastBarData.close >= prevClose };
  }, [dailyData, lastBarData]);

  // 构建图表数据和技术指标
  const chartData = useMemo(() => {
    if (!dailyData.length) return { dates: [], ohlc: [], volumes: [], closes: [], ma5: [], ma10: [], ma20: [], ma50: [], ma100: [], ma120: [], macdData: { dif: [], dea: [], macd: [] }, lri: [] as (number | null)[] };

    const dates = dailyData.map((d) => d.date);
    const closes: number[] = [];
    const ohlc = dailyData.map((d, i) => {
      if (i === dailyData.length - 1 && lastBarData) {
        closes.push(lastBarData.close);
        return [lastBarData.open, lastBarData.close, lastBarData.low, lastBarData.high];
      }
      closes.push(d.close);
      return [d.open, d.close, d.low, d.high];
    });
    const volumes = dailyData.map((d, i) => {
      const bar = i === dailyData.length - 1 && lastBarData ? lastBarData : d;
      return { value: bar.volume, itemStyle: { color: bar.close >= bar.open ? 'rgba(248,81,73,0.5)' : 'rgba(63,185,80,0.5)' } };
    });

    // 计算均线
    const ma5 = calculateMA(closes, 5);
    const ma10 = calculateMA(closes, 10);
    const ma20 = calculateMA(closes, 20);
    const ma50 = calculateMA(closes, 50);
    const ma100 = calculateMA(closes, 100);
    const ma120 = calculateMA(closes, 120);

    // 计算 MACD
    const macdData = calculateMACD(closes);

    // 计算韭菜共振指数 LRI
    const lri = calculateLRI(closes.map((c, i) => ({ close: c, volume: dailyData[i].volume })));

    return { dates, ohlc, volumes, closes, ma5, ma10, ma20, ma50, ma100, ma120, macdData, lri };
  }, [dailyData, lastBarData]);

  // 处理交易记录
  const { buyMarkers, sellMarkers, tradesByDate } = useMemo(() => {
    if (!showTrades || !tradeHistory.length || !chartData.dates.length) {
      return { buyMarkers: [], sellMarkers: [], tradesByDate: new Map() };
    }
    const buyMarkers: Array<{ value: [string, number]; quantity: number }> = [];
    const sellMarkers: Array<{ value: [string, number]; quantity: number }> = [];
    const tradesByDate = new Map<string, SaveTradeRecord[]>();
    const stockTrades = tradeHistory.filter(t => t.code === code);
    for (const trade of stockTrades) {
      const tradeDate = trade.timestamp.split(' ')[0];
      if (chartData.dates.includes(tradeDate)) {
        if (!tradesByDate.has(tradeDate)) tradesByDate.set(tradeDate, []);
        tradesByDate.get(tradeDate)!.push(trade);
        const marker = { value: [tradeDate, trade.price] as [string, number], quantity: trade.quantity };
        if (trade.orderType === 'buy') buyMarkers.push(marker);
        else sellMarkers.push(marker);
      }
    }
    return { buyMarkers, sellMarkers, tradesByDate };
  }, [showTrades, tradeHistory, code, chartData.dates]);

  const tradeStats = useMemo(() => {
    const stockTrades = tradeHistory.filter(t => t.code === code);
    return { total: stockTrades.length, buyCount: stockTrades.filter(t => t.orderType === 'buy').length, sellCount: stockTrades.filter(t => t.orderType === 'sell').length };
  }, [tradeHistory, code]);

  const option = useMemo(() => {
    if (!dailyData.length) {
      return { title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: colors.textSecondary } }, backgroundColor: 'transparent' };
    }

    const { dates, ohlc, volumes, ma5, ma10, ma20, ma50, ma100, ma120, macdData, lri } = chartData;

    const series: Array<Record<string, unknown>> = [
      { name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: '#f85149', color0: '#3fb950', borderColor: '#f85149', borderColor0: '#3fb950' } },
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma5, width: 1 } },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma10, width: 1 } },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma20, width: 1 } },
      { name: 'MA50', type: 'line', data: ma50, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma50, width: 1 } },
      { name: 'MA100', type: 'line', data: ma100, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma100, width: 1 } },
      { name: 'MA120', type: 'line', data: ma120, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { color: colors.ma120, width: 1 } },
      { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1 },
      { name: 'DIF', type: 'line', data: macdData.dif, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { color: '#f5c242', width: 1 } },
      { name: 'DEA', type: 'line', data: macdData.dea, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { color: '#42a5f5', width: 1 } },
      {
        name: 'MACD', type: 'bar', data: macdData.macd.map(v => ({ value: v, itemStyle: { color: v >= 0 ? '#f85149' : '#3fb950' } })),
        xAxisIndex: 2, yAxisIndex: 2
      },
      {
        name: 'LRI', type: 'line', data: lri, xAxisIndex: 3, yAxisIndex: 3,
        symbol: 'none', smooth: true,
        lineStyle: { color: '#e879f9', width: 1.6 },
        areaStyle: { color: 'rgba(232,121,249,0.08)' },
        markLine: {
          silent: true, symbol: 'none',
          label: { position: 'insideEndTop', fontSize: 9 },
          data: [
            { yAxis: LRI_BUY_LEVEL, lineStyle: { color: '#f85149', type: 'dashed', width: 1 }, label: { formatter: '买入 88', color: '#f85149' } },
            { yAxis: LRI_SELL_LEVEL, lineStyle: { color: '#3fb950', type: 'dashed', width: 1 }, label: { formatter: '清仓 44', color: '#3fb950' } },
          ],
        },
        z: 10,
      },
    ];

    if (showTrades && buyMarkers.length > 0) {
      series.push({
        name: '买入', type: 'scatter', data: buyMarkers.map(m => m.value), xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'arrow', symbolSize: 12, symbolRotate: 180, symbolOffset: [0, -20],
        itemStyle: { color: '#ff4757' }, z: 20,
      });
    }
    if (showTrades && sellMarkers.length > 0) {
      series.push({
        name: '卖出', type: 'scatter', data: sellMarkers.map(m => m.value), xAxisIndex: 0, yAxisIndex: 0,
        symbol: 'arrow', symbolSize: 12, symbolOffset: [0, 20],
        itemStyle: { color: '#2ed573' }, z: 20,
      });
    }

    return {
      backgroundColor: 'transparent',
      animation: false,
      title: {
        text: displayName,
        subtext: currentPrice ? `现价: ${currentPrice.toFixed(2)} (${isUp ? '+' : ''}${changePercent}%)` : '',
        left: 16, top: 4,
        textStyle: { fontSize: 14, fontWeight: 600, color: colors.text },
        subtextStyle: { color: isUp ? '#f85149' : '#3fb950', fontSize: 12, fontWeight: 500 },
      },
      legend: {
        data: ['MA5', 'MA10', 'MA20', 'MA50', 'MA100', 'MA120'],
        selected: { 'MA5': true, 'MA10': true, 'MA20': true, 'MA50': false, 'MA100': false, 'MA120': false },
        top: 4, right: 10,
        textStyle: { color: colors.textSecondary, fontSize: 10 },
        itemWidth: 14, itemHeight: 2, itemGap: 8,
        selectedMode: 'multiple',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', lineStyle: { color: '#58a6ff', opacity: 0.5 } },
        backgroundColor: colors.tooltipBg,
        borderColor: colors.border,
        textStyle: { color: colors.text, fontSize: 11 },
        formatter: (params: unknown) => {
          const p = params as Array<{ seriesName: string; value: unknown; axisValue: string; color: string }>;
          if (!p || p.length === 0) return '';
          const date = p[0].axisValue;
          let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`;
          const kline = p.find(item => item.seriesName === 'K线');
          if (kline) {
            const v = kline.value as number[];
            html += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 8px;font-size:11px">`;
            html += `<span>开: ${v[1].toFixed(2)}</span><span style="color:#f85149">高: ${v[4].toFixed(2)}</span>`;
            html += `<span>收: ${v[2].toFixed(2)}</span><span style="color:#3fb950">低: ${v[3].toFixed(2)}</span></div>`;
          }
          // MA 值
          const maItems = p.filter(item => item.seriesName.startsWith('MA'));
          if (maItems.length > 0) {
            html += `<div style="margin-top:4px;font-size:11px">`;
            for (const ma of maItems) {
              const val = ma.value as number;
              if (val !== null) html += `<span style="color:${ma.color};margin-right:8px">${ma.seriesName}: ${val.toFixed(2)}</span>`;
            }
            html += `</div>`;
          }
          // MACD 值
          const dif = p.find(item => item.seriesName === 'DIF');
          const dea = p.find(item => item.seriesName === 'DEA');
          const macd = p.find(item => item.seriesName === 'MACD');
          if (dif || dea || macd) {
            html += `<div style="margin-top:4px;font-size:11px">`;
            if (dif) html += `<span style="color:#f5c242;margin-right:6px">DIF: ${(dif.value as number).toFixed(3)}</span>`;
            if (dea) html += `<span style="color:#42a5f5;margin-right:6px">DEA: ${(dea.value as number).toFixed(3)}</span>`;
            if (macd) html += `<span style="color:${(macd.value as number) >= 0 ? '#f85149' : '#3fb950'}">MACD: ${(macd.value as number).toFixed(3)}</span>`;
            html += `</div>`;
          }
          // LRI 值
          const lriItem = p.find(item => item.seriesName === 'LRI');
          if (lriItem && lriItem.value !== null && lriItem.value !== undefined) {
            const lv = lriItem.value as number;
            const state = lv >= 88 ? '（共振！买入区）' : lv <= 44 ? '（失联，清仓区）' : '';
            html += `<div style="margin-top:4px;font-size:11px"><span style="color:#e879f9">LRI: ${lv.toFixed(1)}${state}</span></div>`;
          }
          const trades = tradesByDate.get(date);
          if (trades && trades.length > 0) {
            html += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid ${colors.border}">`;
            for (const trade of trades) {
              const isBuy = trade.orderType === 'buy';
              html += `<div style="color:${isBuy ? '#ff4757' : '#2ed573'};font-size:11px">${isBuy ? '▲买' : '▼卖'} ${trade.quantity}股 @ ¥${trade.price.toFixed(2)}</div>`;
            }
            html += `</div>`;
          }
          return html;
        },
      },

      grid: [
        { left: '10%', right: '3%', top: '10%', height: '36%' },  // K线
        { left: '10%', right: '3%', top: '50%', height: '10%' },  // 成交量
        { left: '10%', right: '3%', top: '63%', height: '10%' },  // MACD
        { left: '10%', right: '3%', top: '76%', height: '13%' },  // LRI 韭菜共振指数
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: colors.border } }, axisLabel: { show: false }, axisTick: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: colors.border } }, axisLabel: { show: false }, axisTick: { show: false } },
        { type: 'category', data: dates, gridIndex: 2, axisLine: { lineStyle: { color: colors.border } }, axisLabel: { show: false }, axisTick: { show: false } },
        { type: 'category', data: dates, gridIndex: 3, axisLine: { lineStyle: { color: colors.border } }, axisLabel: { color: colors.textSecondary, fontSize: 10 }, axisTick: { show: false } },
      ],
      yAxis: [
        { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: colors.gridLine } }, axisLabel: { color: colors.textSecondary, fontSize: 10 } },
        { scale: true, gridIndex: 1, splitLine: { show: false }, axisLabel: { color: colors.textSecondary, fontSize: 10, formatter: (v: number) => v >= 10000 ? `${(v/10000).toFixed(0)}万` : v } },
        { scale: true, gridIndex: 2, splitLine: { lineStyle: { color: colors.gridLine, type: 'dashed' } }, axisLabel: { color: colors.textSecondary, fontSize: 10 } },
        { min: 0, max: 100, gridIndex: 3, splitNumber: 2, splitLine: { lineStyle: { color: colors.gridLine, type: 'dashed' } }, axisLabel: { color: colors.textSecondary, fontSize: 10 } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 60, end: 100 },
        { show: true, xAxisIndex: [0, 1, 2, 3], type: 'slider', bottom: '1%', start: 60, end: 100, height: 18, borderColor: colors.border, fillerColor: 'rgba(88,166,255,0.2)', backgroundColor: colors.sliderBg, textStyle: { color: colors.textSecondary, fontSize: 10 } },
      ],
      graphic: [
        {
          type: 'text', left: '10%', top: '73.5%',
          style: { text: '韭菜共振指数 LRI（≥88 买入 / ≤44 清仓）', fontSize: 10, fill: '#e879f9', fontWeight: 600 },
          silent: true,
        },
      ],
      series,
    };
  }, [dailyData, displayName, currentPrice, isUp, changePercent, chartData, showTrades, buyMarkers, sellMarkers, tradesByDate, colors]);

  return (
    <div style={{ padding: '8px 12px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{ fontWeight: 500, color: colors.textSecondary, fontSize: 12 }}>股票</span>
        <Select value={code} onChange={onStockChange} style={{ width: 140 }} size="small"
          options={stockCodes.map((c) => ({ value: c, label: stockInfoMap[c]?.name ? `${c} ${stockInfoMap[c].name}` : c }))} />
        {tickIndex !== undefined && tickIndex > 0 && <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>Tick: {tickIndex}/240</Tag>}
        {tradeStats.total > 0 && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Tooltip title={`买入 ${tradeStats.buyCount} 次，卖出 ${tradeStats.sellCount} 次`}>
              <div style={{ display: 'flex', gap: 3 }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 24, height: 18, padding: '0 4px', borderRadius: 3, background: '#ff4757', color: '#fff', fontSize: 11, fontWeight: 600 }}>B{tradeStats.buyCount}</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 24, height: 18, padding: '0 4px', borderRadius: 3, background: '#2ed573', color: '#fff', fontSize: 11, fontWeight: 600 }}>S{tradeStats.sellCount}</span>
              </div>
            </Tooltip>
            <Switch size="small" checked={showTrades} onChange={setShowTrades} />
          </div>
        )}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReactECharts ref={chartRef} option={option} style={{ height: '100%', minHeight: 350 }} notMerge={false} lazyUpdate={true} />
      </div>
    </div>
  );
}
