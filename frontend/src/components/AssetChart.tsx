/**
 * 资产分析组件 - 增强版
 * 包含：资产曲线、每日收益、个股盈亏、月度/年度统计
 */
import { useMemo, useState } from 'react';
import { Empty, Table, Tag, Row, Col, Tabs, Statistic, Card } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useTheme } from '../contexts/ThemeContext';
import type { DailySnapshot, SaveTradeRecord, Position } from '../types';

interface AssetChartProps {
  history: DailySnapshot[];
  initialCash: number;
  currentAssets: number;
  tradeHistory?: SaveTradeRecord[];
  positions?: Position[];
  stockInfoMap?: Record<string, { name: string }>;
}

// 计算个股盈亏
interface StockPnL {
  code: string;
  name: string;
  buyAmount: number;
  sellAmount: number;
  buyFee: number;
  sellFee: number;
  realizedPnL: number;
  unrealizedPnL: number;
  totalPnL: number;
  tradeCount: number;
}

// 月度统计
interface MonthlyStats {
  month: string;
  startAssets: number;
  endAssets: number;
  profit: number;
  returnRate: number;
  tradeDays: number;
  winDays: number;
  lossDays: number;
}

export default function AssetChart({ 
  history, 
  initialCash, 
  currentAssets,
  tradeHistory = [],
  positions = [],
  stockInfoMap = {},
}: AssetChartProps) {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState('chart');
  
  const colors = {
    text: theme === 'dark' ? '#c9d1d9' : '#1f2937',
    textSecondary: theme === 'dark' ? '#8b949e' : '#6b7280',
    border: theme === 'dark' ? '#30363d' : '#e5e7eb',
    gridLine: theme === 'dark' ? '#21262d' : '#f3f4f6',
    tooltipBg: theme === 'dark' ? '#21262d' : '#fff',
    cardBg: theme === 'dark' ? '#161b22' : '#fafafa',
    headerBg: theme === 'dark' ? 'linear-gradient(135deg, #161b22 0%, #1c2128 100%)' : 'linear-gradient(135deg, #f9fafb 0%, #fff 100%)',
  };

  // 计算统计数据
  const stats = useMemo(() => {
    if (history.length === 0) return null;
    
    const profits = history.map(h => h.dailyProfit);
    const returns = history.map(h => h.dailyReturn);
    const winDays = profits.filter(p => p > 0).length;
    const lossDays = profits.filter(p => p < 0).length;
    const maxProfit = Math.max(...profits);
    const maxLoss = Math.min(...profits);
    const avgDailyReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    
    // 最大回撤
    let maxDrawdown = 0;
    let peak = history[0].totalAssets;
    for (const h of history) {
      if (h.totalAssets > peak) peak = h.totalAssets;
      const drawdown = (peak - h.totalAssets) / peak;
      if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    }
    
    // 夏普比率 (简化版，假设无风险利率为0)
    const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
    const stdDev = Math.sqrt(returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length);
    const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;
    
    return {
      winDays,
      lossDays,
      winRate: winDays / (winDays + lossDays) * 100,
      maxProfit,
      maxLoss,
      avgDailyReturn: avgDailyReturn * 100,
      maxDrawdown: maxDrawdown * 100,
      sharpeRatio,
    };
  }, [history]);

  // 计算个股盈亏
  const stockPnL = useMemo((): StockPnL[] => {
    const pnlMap: Record<string, StockPnL> = {};
    
    // 从交易记录计算已实现盈亏
    for (const trade of tradeHistory) {
      if (!pnlMap[trade.code]) {
        pnlMap[trade.code] = {
          code: trade.code,
          name: stockInfoMap[trade.code]?.name || trade.code,
          buyAmount: 0,
          sellAmount: 0,
          buyFee: 0,
          sellFee: 0,
          realizedPnL: 0,
          unrealizedPnL: 0,
          totalPnL: 0,
          tradeCount: 0,
        };
      }
      
      const pnl = pnlMap[trade.code];
      pnl.tradeCount++;
      
      if (trade.orderType === 'buy') {
        pnl.buyAmount += trade.price * trade.quantity;
        pnl.buyFee += trade.fee;
      } else {
        pnl.sellAmount += trade.price * trade.quantity;
        pnl.sellFee += trade.fee;
      }
    }
    
    // 计算已实现盈亏
    for (const code of Object.keys(pnlMap)) {
      const pnl = pnlMap[code];
      pnl.realizedPnL = pnl.sellAmount - pnl.buyAmount - pnl.buyFee - pnl.sellFee;
    }
    
    // 添加未实现盈亏（当前持仓）
    for (const pos of positions) {
      if (!pnlMap[pos.code]) {
        pnlMap[pos.code] = {
          code: pos.code,
          name: stockInfoMap[pos.code]?.name || pos.code,
          buyAmount: 0,
          sellAmount: 0,
          buyFee: 0,
          sellFee: 0,
          realizedPnL: 0,
          unrealizedPnL: 0,
          totalPnL: 0,
          tradeCount: 0,
        };
      }
      pnlMap[pos.code].unrealizedPnL = pos.profitLoss;
    }
    
    // 计算总盈亏
    for (const code of Object.keys(pnlMap)) {
      pnlMap[code].totalPnL = pnlMap[code].realizedPnL + pnlMap[code].unrealizedPnL;
    }
    
    return Object.values(pnlMap).sort((a, b) => b.totalPnL - a.totalPnL);
  }, [tradeHistory, positions, stockInfoMap]);

  // 计算月度统计
  const monthlyStats = useMemo((): MonthlyStats[] => {
    if (history.length === 0) return [];
    
    const monthMap: Record<string, DailySnapshot[]> = {};
    for (const h of history) {
      const month = h.date.substring(0, 7); // YYYY-MM
      if (!monthMap[month]) monthMap[month] = [];
      monthMap[month].push(h);
    }
    
    return Object.entries(monthMap).map(([month, days]) => {
      const startAssets = days[0].totalAssets - days[0].dailyProfit;
      const endAssets = days[days.length - 1].totalAssets;
      const profit = endAssets - startAssets;
      const winDays = days.filter(d => d.dailyProfit > 0).length;
      const lossDays = days.filter(d => d.dailyProfit < 0).length;
      
      return {
        month,
        startAssets,
        endAssets,
        profit,
        returnRate: startAssets > 0 ? (profit / startAssets) * 100 : 0,
        tradeDays: days.length,
        winDays,
        lossDays,
      };
    }).sort((a, b) => b.month.localeCompare(a.month));
  }, [history]);

  const totalReturn = initialCash > 0 ? (currentAssets - initialCash) / initialCash : 0;
  const isProfit = totalReturn >= 0;

  // 图表配置
  const chartOption = useMemo(() => {
    if (history.length === 0) return {};

    const dates = history.map(h => h.date);
    const assets = history.map(h => h.totalAssets);
    const returns = history.map(h => (h.cumulativeReturn * 100).toFixed(2));

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: colors.tooltipBg,
        borderColor: colors.border,
        textStyle: { color: colors.text },
      },
      legend: {
        data: ['总资产', '累计收益率'],
        textStyle: { color: colors.textSecondary },
        top: 10,
      },
      grid: { left: 70, right: 70, top: 50, bottom: 30 },
      xAxis: {
        type: 'category' as const,
        data: dates,
        axisLine: { lineStyle: { color: colors.border } },
        axisLabel: { color: colors.textSecondary, fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value' as const,
          name: '总资产',
          nameTextStyle: { color: colors.textSecondary },
          axisLine: { lineStyle: { color: colors.border } },
          axisLabel: { 
            color: colors.textSecondary,
            formatter: (v: number) => `¥${(v / 10000).toFixed(1)}万`,
          },
          splitLine: { lineStyle: { color: colors.gridLine } },
        },
        {
          type: 'value' as const,
          name: '收益率',
          nameTextStyle: { color: colors.textSecondary },
          axisLine: { lineStyle: { color: colors.border } },
          axisLabel: { color: colors.textSecondary, formatter: (v: number) => `${v}%` },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '总资产',
          type: 'line' as const,
          data: assets,
          smooth: true,
          lineStyle: { color: '#58a6ff', width: 2 },
          areaStyle: {
            color: {
              type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(88, 166, 255, 0.3)' },
                { offset: 1, color: 'rgba(88, 166, 255, 0.05)' },
              ],
            },
          },
          itemStyle: { color: '#58a6ff' },
        },
        {
          name: '累计收益率',
          type: 'line' as const,
          yAxisIndex: 1,
          data: returns,
          smooth: true,
          lineStyle: { color: '#f85149', width: 2, type: 'dashed' as const },
          itemStyle: { color: '#f85149' },
        },
      ],
    };
  }, [history, colors]);

  // 每日收益表格列
  const dailyColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
    {
      title: '总资产',
      dataIndex: 'totalAssets',
      key: 'totalAssets',
      width: 120,
      render: (v: number) => <span style={{ color: '#58a6ff', fontFamily: 'monospace' }}>¥{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>,
    },
    {
      title: '当日盈亏',
      dataIndex: 'dailyProfit',
      key: 'dailyProfit',
      width: 100,
      render: (v: number) => <span style={{ color: v >= 0 ? '#f85149' : '#3fb950', fontFamily: 'monospace' }}>{v >= 0 ? '+' : ''}{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>,
    },
    {
      title: '当日收益率',
      dataIndex: 'dailyReturn',
      key: 'dailyReturn',
      width: 90,
      render: (v: number) => <Tag color={v >= 0 ? 'red' : 'green'} style={{ margin: 0 }}>{v >= 0 ? '+' : ''}{(v * 100).toFixed(2)}%</Tag>,
    },
    {
      title: '累计收益率',
      dataIndex: 'cumulativeReturn',
      key: 'cumulativeReturn',
      width: 90,
      render: (v: number) => <Tag color={v >= 0 ? 'red' : 'green'} style={{ margin: 0, fontWeight: 600 }}>{v >= 0 ? '+' : ''}{(v * 100).toFixed(2)}%</Tag>,
    },
  ];

  // 个股盈亏表格列
  const stockColumns = [
    { title: '股票', dataIndex: 'code', key: 'code', width: 80, render: (code: string, r: StockPnL) => <div><div>{code}</div><div style={{ fontSize: 11, opacity: 0.7 }}>{r.name}</div></div> },
    { title: '买入金额', dataIndex: 'buyAmount', key: 'buyAmount', width: 100, render: (v: number) => <span style={{ fontFamily: 'monospace' }}>¥{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> },
    { title: '卖出金额', dataIndex: 'sellAmount', key: 'sellAmount', width: 100, render: (v: number) => <span style={{ fontFamily: 'monospace' }}>¥{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> },
    { title: '已实现盈亏', dataIndex: 'realizedPnL', key: 'realizedPnL', width: 100, render: (v: number) => <span style={{ color: v >= 0 ? '#f85149' : '#3fb950', fontFamily: 'monospace' }}>{v >= 0 ? '+' : ''}¥{v.toFixed(2)}</span> },
    { title: '未实现盈亏', dataIndex: 'unrealizedPnL', key: 'unrealizedPnL', width: 100, render: (v: number) => <span style={{ color: v >= 0 ? '#f85149' : '#3fb950', fontFamily: 'monospace' }}>{v >= 0 ? '+' : ''}¥{v.toFixed(2)}</span> },
    { title: '总盈亏', dataIndex: 'totalPnL', key: 'totalPnL', width: 100, render: (v: number) => <Tag color={v >= 0 ? 'red' : 'green'}>{v >= 0 ? '+' : ''}¥{v.toFixed(2)}</Tag> },
    { title: '交易次数', dataIndex: 'tradeCount', key: 'tradeCount', width: 70 },
  ];

  // 月度统计表格列
  const monthlyColumns = [
    { title: '月份', dataIndex: 'month', key: 'month', width: 80 },
    { title: '期初资产', dataIndex: 'startAssets', key: 'startAssets', width: 110, render: (v: number) => <span style={{ fontFamily: 'monospace' }}>¥{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> },
    { title: '期末资产', dataIndex: 'endAssets', key: 'endAssets', width: 110, render: (v: number) => <span style={{ fontFamily: 'monospace' }}>¥{v.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> },
    { title: '月度盈亏', dataIndex: 'profit', key: 'profit', width: 100, render: (v: number) => <span style={{ color: v >= 0 ? '#f85149' : '#3fb950', fontFamily: 'monospace' }}>{v >= 0 ? '+' : ''}¥{v.toFixed(2)}</span> },
    { title: '月度收益率', dataIndex: 'returnRate', key: 'returnRate', width: 90, render: (v: number) => <Tag color={v >= 0 ? 'red' : 'green'}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Tag> },
    { title: '交易日', dataIndex: 'tradeDays', key: 'tradeDays', width: 60 },
    { title: '盈利日', dataIndex: 'winDays', key: 'winDays', width: 60, render: (v: number) => <span style={{ color: '#f85149' }}>{v}</span> },
    { title: '亏损日', dataIndex: 'lossDays', key: 'lossDays', width: 60, render: (v: number) => <span style={{ color: '#3fb950' }}>{v}</span> },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 汇总信息 */}
      <div style={{ 
        padding: '12px 20px', 
        borderBottom: `1px solid ${colors.border}`,
        display: 'flex',
        gap: 32,
        alignItems: 'center',
        background: colors.headerBg,
        flexWrap: 'wrap',
      }}>
        <div>
          <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>初始资金</div>
          <div style={{ color: colors.text, fontSize: 20, fontWeight: 600, fontFamily: 'monospace' }}>¥{initialCash.toLocaleString()}</div>
        </div>
        <div>
          <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>当前资产</div>
          <div style={{ color: '#58a6ff', fontSize: 20, fontWeight: 600, fontFamily: 'monospace' }}>¥{currentAssets.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
        </div>
        <div>
          <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>累计收益</div>
          <div style={{ color: isProfit ? '#f85149' : '#3fb950', fontSize: 20, fontWeight: 600, fontFamily: 'monospace' }}>{isProfit ? '+' : ''}{(totalReturn * 100).toFixed(2)}%</div>
        </div>
        <div>
          <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>盈亏金额</div>
          <div style={{ color: isProfit ? '#f85149' : '#3fb950', fontSize: 20, fontWeight: 600, fontFamily: 'monospace' }}>{isProfit ? '+' : ''}¥{(currentAssets - initialCash).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
        </div>
        {stats && (
          <>
            <div>
              <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>胜率</div>
              <div style={{ color: stats.winRate >= 50 ? '#f85149' : '#3fb950', fontSize: 16, fontWeight: 600 }}>{stats.winRate.toFixed(1)}%</div>
            </div>
            <div>
              <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>最大回撤</div>
              <div style={{ color: '#3fb950', fontSize: 16, fontWeight: 600 }}>-{stats.maxDrawdown.toFixed(2)}%</div>
            </div>
            <div>
              <div style={{ color: colors.textSecondary, fontSize: 12, marginBottom: 2 }}>夏普比率</div>
              <div style={{ color: stats.sharpeRatio >= 0 ? '#58a6ff' : '#f85149', fontSize: 16, fontWeight: 600 }}>{stats.sharpeRatio.toFixed(2)}</div>
            </div>
          </>
        )}
        <div style={{ marginLeft: 'auto', color: colors.textSecondary, fontSize: 13 }}>
          已记录 <span style={{ color: '#58a6ff', fontWeight: 600 }}>{history.length}</span> 个交易日
        </div>
      </div>

      {history.length === 0 ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="暂无历史数据，完成交易日后将显示资产曲线" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            style={{ padding: '0 16px' }}
            items={[
              { key: 'chart', label: '📈 资产曲线' },
              { key: 'daily', label: '📊 每日收益' },
              { key: 'stock', label: '💰 个股盈亏' },
              { key: 'monthly', label: '📅 月度统计' },
            ]}
          />
          
          <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 16px' }}>
            {activeTab === 'chart' && (
              <Row gutter={16} style={{ height: '100%' }}>
                <Col span={16}>
                  <ReactECharts option={chartOption} style={{ height: 400 }} notMerge={false} lazyUpdate={true} />
                </Col>
                <Col span={8}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {stats && (
                      <>
                        <Card size="small" style={{ background: colors.cardBg }}>
                          <Statistic title="盈利天数" value={stats.winDays} suffix={`/ ${stats.winDays + stats.lossDays} 天`} valueStyle={{ color: '#f85149' }} prefix={<ArrowUpOutlined />} />
                        </Card>
                        <Card size="small" style={{ background: colors.cardBg }}>
                          <Statistic title="亏损天数" value={stats.lossDays} suffix={`/ ${stats.winDays + stats.lossDays} 天`} valueStyle={{ color: '#3fb950' }} prefix={<ArrowDownOutlined />} />
                        </Card>
                        <Card size="small" style={{ background: colors.cardBg }}>
                          <Statistic title="单日最大盈利" value={stats.maxProfit} precision={2} prefix="¥" valueStyle={{ color: '#f85149' }} />
                        </Card>
                        <Card size="small" style={{ background: colors.cardBg }}>
                          <Statistic title="单日最大亏损" value={Math.abs(stats.maxLoss)} precision={2} prefix="-¥" valueStyle={{ color: '#3fb950' }} />
                        </Card>
                        <Card size="small" style={{ background: colors.cardBg }}>
                          <Statistic title="日均收益率" value={stats.avgDailyReturn} precision={3} suffix="%" valueStyle={{ color: stats.avgDailyReturn >= 0 ? '#f85149' : '#3fb950' }} />
                        </Card>
                      </>
                    )}
                  </div>
                </Col>
              </Row>
            )}
            
            {activeTab === 'daily' && (
              <Table dataSource={[...history].reverse()} columns={dailyColumns} rowKey="date" size="small" pagination={{ pageSize: 20 }} scroll={{ y: 400 }} />
            )}
            
            {activeTab === 'stock' && (
              <Table dataSource={stockPnL} columns={stockColumns} rowKey="code" size="small" pagination={false} scroll={{ y: 400 }} />
            )}
            
            {activeTab === 'monthly' && (
              <Table dataSource={monthlyStats} columns={monthlyColumns} rowKey="month" size="small" pagination={false} scroll={{ y: 400 }} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
