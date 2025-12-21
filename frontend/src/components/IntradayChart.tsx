/**
 * 分时图组件 - 优化实时渲染性能
 */
import { useMemo, useRef } from 'react';
import { Empty, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '../contexts/ThemeContext';

interface IntradayChartProps {
  code: string;
  priceHistory: Array<{ tick: number; price: number }>;
  openPrice: number;
}

export default function IntradayChart({ code, priceHistory, openPrice }: IntradayChartProps) {
  const chartRef = useRef<ReactECharts>(null);
  const { theme } = useTheme();
  
  // 主题颜色
  const colors = {
    text: theme === 'dark' ? '#c9d1d9' : '#1f2937',
    textSecondary: theme === 'dark' ? '#8b949e' : '#6b7280',
    border: theme === 'dark' ? '#30363d' : '#e5e7eb',
    gridLine: theme === 'dark' ? '#21262d' : '#f3f4f6',
    tooltipBg: theme === 'dark' ? 'rgba(22,27,34,0.95)' : 'rgba(255,255,255,0.95)',
  };
  
  // 提取价格数组
  const prices = useMemo(() => priceHistory.map(p => p.price), [priceHistory]);
  
  // 计算时间标签
  const times = useMemo(() => {
    return priceHistory.map((_, i) => {
      const totalMinutes = Math.floor(i * 240 / Math.max(priceHistory.length, 1));
      if (totalMinutes < 120) {
        const hour = 9 + Math.floor((totalMinutes + 30) / 60);
        const minute = (totalMinutes + 30) % 60;
        return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
      } else {
        const afternoonMinutes = totalMinutes - 120;
        const hour = 13 + Math.floor(afternoonMinutes / 60);
        const minute = afternoonMinutes % 60;
        return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
      }
    });
  }, [priceHistory]);
  
  // 计算当前状态
  const currentPrice = prices.length > 0 ? prices[prices.length - 1] : 0;
  const currentChange = openPrice > 0 ? ((currentPrice - openPrice) / openPrice * 100) : 0;
  const isUp = currentChange >= 0;

  // 计算Y轴范围
  const { yMin, yMax } = useMemo(() => {
    if (prices.length === 0) return { yMin: 0, yMax: 0 };
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 0.01;
    return {
      yMin: minPrice - priceRange * 0.1,
      yMax: maxPrice + priceRange * 0.1,
    };
  }, [prices]);

  // 完整的图表选项
  const option = useMemo(() => {
    if (!priceHistory.length) {
      return null;
    }

    return {
      backgroundColor: 'transparent',
      animation: false,
      title: {
        text: `${code} 分时走势`,
        subtext: `现价: ${currentPrice.toFixed(2)} (${isUp ? '+' : ''}${currentChange.toFixed(2)}%)`,
        left: 16,
        top: 8,
        textStyle: { fontSize: 18, fontWeight: 600, color: colors.text },
        subtextStyle: { color: isUp ? '#f85149' : '#3fb950', fontSize: 14, fontWeight: 500 },
      },
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: colors.tooltipBg,
        borderColor: colors.border,
        borderWidth: 1,
        textStyle: { color: colors.text },
      },
      grid: { left: '8%', right: '4%', top: '15%', bottom: '10%' },
      xAxis: {
        type: 'category' as const,
        data: times,
        axisLine: { lineStyle: { color: colors.border } },
        axisLabel: { color: colors.textSecondary, interval: Math.floor(Math.max(times.length, 1) / 6) },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value' as const,
        min: yMin,
        max: yMax,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: colors.gridLine } },
        axisLabel: { color: colors.textSecondary, formatter: (v: number) => v.toFixed(2) },
      },
      series: [
        {
          name: '价格',
          type: 'line' as const,
          data: prices,
          smooth: false,
          symbol: 'none',
          lineStyle: { color: isUp ? '#f85149' : '#3fb950', width: 1.5 },
          areaStyle: {
            color: {
              type: 'linear' as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: isUp ? 'rgba(248,81,73,0.3)' : 'rgba(63,185,80,0.3)' },
                { offset: 1, color: isUp ? 'rgba(248,81,73,0.05)' : 'rgba(63,185,80,0.05)' },
              ],
            },
          },
        },
        {
          name: '开盘价',
          type: 'line' as const,
          data: new Array(times.length).fill(openPrice),
          symbol: 'none',
          lineStyle: { color: colors.textSecondary, width: 1, type: 'dashed' as const },
        },
      ],
    };
  }, [code, priceHistory, openPrice, prices, times, currentPrice, currentChange, isUp, yMin, yMax, colors]);

  if (!priceHistory.length) {
    return (
      <div style={{ padding: 16, height: '100%', minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty 
          description={
            <div>
              <div style={{ marginBottom: 8 }}>暂无分时数据</div>
              <Tag color="blue">点击播放开始记录分时走势</Tag>
            </div>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    );
  }

  // openPrice 为 0 时也显示图表，只是没有开盘价参考线
  if (!option) {
    return (
      <div style={{ padding: 16, height: '100%', minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty 
          description="加载中..."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 16, height: '100%' }}>
      <ReactECharts
        ref={chartRef}
        option={option || {}}
        style={{ height: 'calc(100% - 16px)', minHeight: 400 }}
        notMerge={false}
        lazyUpdate={true}
      />
    </div>
  );
}