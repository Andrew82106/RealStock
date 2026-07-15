/**
 * 轻量 ECharts React 封装 - 替代 echarts-for-react。
 *
 * echarts-for-react 3.x 依赖的 size-sensor 在 React 18 StrictMode
 * 双挂载时重复销毁（TypeError: reading 'disconnect'），导致开发模式下
 * 所有图表崩溃无法渲染。本组件直接使用 echarts + ResizeObserver，
 * 初始化与销毁完全对称，双挂载安全。
 */
import { useEffect, useRef } from 'react';
import type { CSSProperties } from 'react';
import * as echarts from 'echarts';

interface EChartsWrapperProps {
  option: Record<string, unknown>;
  style?: CSSProperties;
  notMerge?: boolean;
  lazyUpdate?: boolean;
  theme?: string;
}

export default function EChartsWrapper({
  option,
  style,
  notMerge = false,
  lazyUpdate = false,
  theme,
}: EChartsWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const optionRef = useRef({ option, notMerge, lazyUpdate });
  optionRef.current = { option, notMerge, lazyUpdate };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = echarts.init(el, theme);
    chartRef.current = chart;

    // 挂载时应用当前 option（重挂载后恢复图表内容）
    chart.setOption(optionRef.current.option, {
      notMerge: optionRef.current.notMerge,
      lazyUpdate: optionRef.current.lazyUpdate,
    });

    const observer = new ResizeObserver(() => {
      if (!chart.isDisposed()) chart.resize();
    });
    observer.observe(el);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, [theme]);

  useEffect(() => {
    const chart = chartRef.current;
    if (chart && !chart.isDisposed()) {
      chart.setOption(option, { notMerge, lazyUpdate });
    }
  }, [option, notMerge, lazyUpdate]);

  return <div ref={containerRef} style={style} />;
}
