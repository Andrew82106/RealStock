import { ArrowRightOutlined, DatabaseOutlined, ExperimentOutlined, FolderOpenOutlined, LineChartOutlined } from '@ant-design/icons';
import { Button, Empty, Spin, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gameApi, indicatorApi, stockApi } from '../services/api';
import type { LocalGameArchive } from '../types';

interface Overview {
  caches: number;
  rows: number;
  indicators: number;
}

export default function HomePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<Overview>({ caches: 0, rows: 0, indicators: 0 });
  const [archives, setArchives] = useState<LocalGameArchive[]>([]);

  useEffect(() => {
    Promise.all([stockApi.listCache(), indicatorApi.list(), gameApi.listSessions()])
      .then(([cache, indicators, localArchives]) => {
        setOverview({
        caches: cache.length,
        rows: cache.reduce((sum, item) => sum + item.row_count, 0),
        indicators: indicators.length,
        });
        setArchives(localArchives);
      })
      .catch(() => message.error('本地数据或存档列表读取失败'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-stack">
      <section className="hero-terminal">
        <div className="eyebrow">REALSTOCK / A-SHARE SIMULATOR</div>
        <h1>重走历史行情，练习你的<br /><span>交易判断</span></h1>
        <p>选择一段真实的 A 股历史日线，在逐日推进的行情中设计指标、管理仓位并检验交易策略。</p>
        <div className="hero-actions">
          <Button type="primary" size="large" icon={<LineChartOutlined />} onClick={() => navigate('/setup')}>
            新建日线模拟
          </Button>
          <Button size="large" icon={<FolderOpenOutlined />} onClick={() => document.getElementById('local-archives')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>读取本地存档</Button>
          <Button size="large" onClick={() => navigate('/data')}>管理本地数据</Button>
        </div>
      </section>

      <Spin spinning={loading}>
        <section className="market-strip">
          <div><span>已缓存标的</span><strong>{overview.caches}</strong><small>只 / 复权组合</small></div>
          <div><span>本地日线</span><strong>{overview.rows.toLocaleString()}</strong><small>条 OHLCV</small></div>
          <div><span>指标文件</span><strong>{overview.indicators}</strong><small>个本地定义</small></div>
          <div><span>运行数据源</span><strong className="text-gold">LOCAL</strong><small>游戏中不联网</small></div>
        </section>
      </Spin>

      <section className="archive-panel terminal-panel" id="local-archives">
        <div className="panel-title"><span>本地自动存档</span><small>交易、挂单和每日推进后自动保存；服务重启后仍可继续</small></div>
        {archives.length ? <div className="archive-list">{archives.map((archive) => {
          const progress = archive.totalDates ? ((archive.dateIndex + 1) / archive.totalDates) * 100 : 0;
          const returnRate = archive.initialCash > 0 ? archive.totalAssets / archive.initialCash - 1 : 0;
          return <article className="archive-row" key={archive.sessionId}>
            <div className="archive-identity"><strong>模拟 {archive.startDate} — {archive.endDate}</strong><span className="mono">{archive.sessionId}</span></div>
            <div className="archive-stocks"><span>股票</span><strong>{archive.stockCodes.map((code) => archive.stockNames[code] ? `${archive.stockNames[code]} ${code}` : code).join(' · ')}</strong></div>
            <div><span>当前日期</span><strong className="mono">{archive.currentDate}</strong><small>{archive.dateIndex + 1} / {archive.totalDates} 日 · {progress.toFixed(0)}%</small></div>
            <div><span>当前资产</span><strong className="mono">¥{archive.totalAssets.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><small className={returnRate >= 0 ? 'market-up' : 'market-down'}>{returnRate >= 0 ? '+' : ''}{(returnRate * 100).toFixed(2)}%</small></div>
            <div><span>最后保存</span><strong>{new Date(archive.updatedAt).toLocaleString('zh-CN', { hour12: false })}</strong><Tag color={archive.isLastDay ? 'default' : 'success'}>{archive.isLastDay ? '已结束' : '可继续'}</Tag></div>
            <Button type="primary" icon={<FolderOpenOutlined />} onClick={() => navigate(`/trading/${archive.sessionId}`)}>读取存档</Button>
          </article>;
        })}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有本地存档，新建模拟后系统会自动保存" />}
      </section>

      <section className="workflow-grid">
        <button className="workflow-card" onClick={() => navigate('/data')}>
          <span className="step-index">01</span><DatabaseOutlined />
          <h2>准备行情</h2><p>设定缓存范围，下载后检查覆盖缺口和实际行数。</p><span className="card-link">进入数据中心 <ArrowRightOutlined /></span>
        </button>
        <button className="workflow-card" onClick={() => navigate('/indicators')}>
          <span className="step-index">02</span><ExperimentOutlined />
          <h2>设计指标</h2><p>按固定接口编写 Python 指标，用本地日线实时运行和预览信号。</p><span className="card-link">进入指标工坊 <ArrowRightOutlined /></span>
        </button>
        <button className="workflow-card" onClick={() => navigate('/setup')}>
          <span className="step-index">03</span><LineChartOutlined />
          <h2>开始模拟</h2><p>游戏范围必须被缓存覆盖，随后逐个交易日揭示行情和指标。</p><span className="card-link">配置新模拟 <ArrowRightOutlined /></span>
        </button>
      </section>

      <section className="rule-panel">
        <div><span className="rule-label">核心约束</span><h3>缓存范围与游戏范围分开设置</h3></div>
        <p>缓存可以大于游戏区间，便于复用；不能小于游戏区间。若存在缺口，启动按钮会被锁定并直接告诉你缺哪一段。</p>
      </section>
    </div>
  );
}
