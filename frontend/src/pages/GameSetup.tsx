import { CheckCircleFilled, CloudDownloadOutlined, ExclamationCircleFilled, PlayCircleFilled, SearchOutlined } from '@ant-design/icons';
import { Button, DatePicker, InputNumber, Select, Steps, Tag, message } from 'antd';
import axios from 'axios';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gameApi, indicatorApi, stockApi } from '../services/api';
import type { CachePreflight, IndicatorDefinition, StockInfo } from '../types';

const { RangePicker } = DatePicker;

function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === 'string' ? detail : detail?.message || error.message;
  }
  return error instanceof Error ? error.message : '操作失败';
}

export default function GameSetup() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState<StockInfo[]>([]);
  const [codes, setCodes] = useState<string[]>([]);
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs('2019-01-01'), dayjs('2020-12-31')]);
  const [cash, setCash] = useState(100000);
  const [indicators, setIndicators] = useState<IndicatorDefinition[]>([]);
  const [indicatorId, setIndicatorId] = useState<string>();
  const [cacheResult, setCacheResult] = useState<CachePreflight | null>(null);
  const [busy, setBusy] = useState<'search' | 'check' | 'download' | 'start' | null>(null);

  useEffect(() => { indicatorApi.list().then(setIndicators).catch(() => undefined); }, []);
  useEffect(() => { setCacheResult(null); }, [codes, range]);

  const gamePayload = () => ({ stock_codes: codes, start_date: range[0].format('YYYY-MM-DD'), end_date: range[1].format('YYYY-MM-DD') });
  const cachePayload = () => ({ ...gamePayload(), start_date: range[0].subtract(31, 'day').format('YYYY-MM-DD'), adjust: 'qfq' });

  const search = async (keyword: string) => {
    if (!keyword.trim()) return;
    setBusy('search');
    try { setStocks(await stockApi.getStockList(keyword)); }
    catch (error) { message.error(errorText(error)); }
    finally { setBusy(null); }
  };

  const check = async () => {
    if (!codes.length) return message.warning('请先选择股票');
    setBusy('check');
    try { setCacheResult(await stockApi.preflightCache(cachePayload())); }
    catch (error) { message.error(errorText(error)); }
    finally { setBusy(null); }
  };

  const download = async () => {
    setBusy('download');
    try {
      const result = await stockApi.downloadCache(cachePayload()); setCacheResult(result);
      message.success('缺失范围已下载到本地');
    } catch (error) { message.error(errorText(error)); }
    finally { setBusy(null); }
  };

  const start = async () => {
    if (!cacheResult?.ready) return message.warning('请先通过本地数据检查');
    setBusy('start');
    try {
      const session = await gameApi.startGame({ ...gamePayload(), initial_cash: cash, indicator_id: indicatorId });
      navigate(`/trading/${session.session_id}`);
    } catch (error) { message.error(errorText(error)); }
    finally { setBusy(null); }
  };

  const currentStep = !codes.length ? 0 : !cacheResult?.ready ? 1 : 2;
  const lateListingItems = cacheResult?.items.filter((item) => item.data_start && dayjs(item.data_start).isAfter(range[0], 'day')) || [];

  return (
    <div className="setup-page">
      <div className="page-heading"><div><div className="eyebrow">NEW SIMULATION / DAILY ONLY</div><h1>新建日线模拟</h1></div></div>
      <Steps current={currentStep} items={[{ title: '设置游戏' }, { title: '核对数据' }, { title: '启动模拟' }]} className="setup-steps" />

      <div className="setup-grid">
        <section className="terminal-panel setup-form-panel">
          <div className="panel-title"><span>游戏设置</span><small>历史行情范围</small></div>
          <label className="field-label">交易标的（最多 3 只）</label>
          <Select
            mode="multiple" maxCount={3} showSearch filterOption={false} loading={busy === 'search'}
            value={codes} onChange={setCodes} onSearch={search} suffixIcon={<SearchOutlined />}
            placeholder="输入代码或名称搜索"
            options={stocks.map((stock) => ({ value: stock.code, label: `${stock.code}  ${stock.name}` }))}
          />

          <label className="field-label">游戏时间范围</label>
          <RangePicker value={range} allowClear={false} onChange={(value) => value && setRange(value as [Dayjs, Dayjs])} />
          <p className="field-help">游戏从所选开始日计时；系统会额外读取此前 31 天的 K 线作为首屏观察窗口和指标预热。</p>

          <label className="field-label">初始资金</label>
          <InputNumber value={cash} min={10000} max={100000000} step={10000} addonBefore="¥" onChange={(value) => setCash(value ?? 100000)} />

          <label className="field-label">随游戏显示的指标（可选）</label>
          <Select allowClear value={indicatorId} onChange={setIndicatorId} placeholder="不使用指标" options={indicators.map((item) => ({ value: item.id, label: `${item.name} · ${item.language === 'python' ? 'Python' : `${item.components.length} 分量`}` }))} />

          <div className="setup-rule"><strong>运行规则</strong><span>只读本地前复权日线；首屏包含开始日前 31 天行情；每次点击推进一个交易日；图表不显示此后的行情。</span></div>
        </section>

        <section className="terminal-panel preflight-panel">
          <div className="panel-title"><span>启动预检</span><small>游戏中禁止隐式联网</small></div>
          {!cacheResult && <div className="empty-check"><DatabaseGlyph /><h3>尚未检查数据覆盖</h3><p>系统将比较每只股票的本地缓存范围与游戏范围。</p><Button type="primary" loading={busy === 'check'} disabled={!codes.length} onClick={check}>检查本地数据</Button></div>}
          {cacheResult && <>
            <div className={`check-summary ${!cacheResult.ready ? 'missing' : lateListingItems.length ? 'partial' : 'ready'}`}>
              {cacheResult.ready && !lateListingItems.length ? <CheckCircleFilled /> : <ExclamationCircleFilled />}
              <div><h3>{!cacheResult.ready ? '缓存范围不完整' : lateListingItems.length ? '可以启动，但部分股票尚未上市' : '可以离线启动'}</h3><p>{!cacheResult.ready ? '下面列出了缺失区间，下载动作需要你明确确认。' : lateListingItems.length ? '这些股票在游戏开始日没有行情，将从实际首个交易日起出现在列表中。' : '所有标的均覆盖整个游戏范围。'}</p></div>
            </div>
            <div className="coverage-list">{cacheResult.items.map((item) => <div className="coverage-row" key={item.code}>
              <div><strong>{item.name || '名称待更新'} <span className="mono">{item.code}</span></strong><span>{item.row_count.toLocaleString()} 条本地日线 · 实际行情 {item.data_start || '无数据'} → {item.data_end || '无数据'}</span></div>
              {item.complete ? <Tag color={item.data_start && dayjs(item.data_start).isAfter(range[0], 'day') ? 'warning' : 'success'}>{item.data_start && dayjs(item.data_start).isAfter(range[0], 'day') ? `${item.data_start} 起有行情` : '覆盖完整'}</Tag> : <div className="gap-tags">{item.missing_ranges.map((gap) => <Tag color="warning" key={`${gap.start}-${gap.end}`}>{gap.start} → {gap.end}</Tag>)}</div>}
            </div>)}</div>
            <div className="preflight-actions"><Button onClick={check} loading={busy === 'check'}>重新检查</Button>{!cacheResult.ready && <Button type="primary" icon={<CloudDownloadOutlined />} loading={busy === 'download'} onClick={download}>明确下载缺失范围</Button>}</div>
          </>}
          <Button className="launch-button" type="primary" size="large" block icon={<PlayCircleFilled />} disabled={!cacheResult?.ready} loading={busy === 'start'} onClick={start}>启动日线模拟</Button>
        </section>
      </div>
    </div>
  );
}

function DatabaseGlyph() {
  return <div className="database-glyph"><span /><span /><span /></div>;
}
