import { CloudDownloadOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, DatePicker, Form, Popconfirm, Select, Table, Tag, message } from 'antd';
import type { TableColumnsType } from 'antd';
import axios from 'axios';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { stockApi } from '../services/api';
import type { CacheStatus, StockInfo } from '../types';

const { RangePicker } = DatePicker;

function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === 'string' ? detail : detail?.message || error.message;
  }
  return error instanceof Error ? error.message : '操作失败';
}

export default function DataCenter() {
  const [cache, setCache] = useState<CacheStatus[]>([]);
  const [options, setOptions] = useState<StockInfo[]>([]);
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(3, 'year').startOf('year'),
    dayjs().subtract(1, 'day'),
  ]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);

  const refresh = async () => setCache(await stockApi.listCache());
  useEffect(() => { refresh().catch((error) => message.error(errorText(error))); }, []);

  const search = async (keyword: string) => {
    if (!keyword.trim()) return;
    setSearching(true);
    try { setOptions(await stockApi.getStockList(keyword)); }
    catch (error) { message.error(errorText(error)); }
    finally { setSearching(false); }
  };

  const download = async () => {
    if (!selectedCodes.length) return message.warning('请先选择股票');
    setLoading(true);
    try {
      const result = await stockApi.downloadCache({
        stock_codes: selectedCodes,
        start_date: range[0].format('YYYY-MM-DD'),
        end_date: range[1].format('YYYY-MM-DD'),
        adjust: 'qfq',
      });
      if (result.ready) message.success('日线数据已写入本地缓存，覆盖检查通过');
      await refresh();
    } catch (error) { message.error(errorText(error)); }
    finally { setLoading(false); }
  };

  const remove = async (record: CacheStatus) => {
    try {
      await stockApi.deleteCache(record.code, record.adjust);
      message.success(`已删除 ${record.code} 的本地缓存`);
      await refresh();
    } catch (error) { message.error(errorText(error)); }
  };

  const columns: TableColumnsType<CacheStatus> = [
    {
      title: '股票', dataIndex: 'code', width: 190,
      render: (value, row) => <div className="stock-identity"><strong>{row.name || '名称待更新'}</strong><span className="mono">{value}</span></div>,
    },
    { title: '复权', dataIndex: 'adjust', width: 80, render: () => <Tag color="gold">前复权</Tag> },
    {
      title: '已确认缓存范围', dataIndex: 'ranges',
      render: (ranges: CacheStatus['ranges']) => ranges.length
        ? ranges.map((item) => `${item.start} → ${item.end}`).join('；')
        : '—',
    },
    { title: '实际行情首尾', width: 225, render: (_, row) => row.data_start ? `${row.data_start} → ${row.data_end}` : '区间内无交易日' },
    { title: '日线条数', dataIndex: 'row_count', align: 'right', width: 110, render: (value) => <span className="mono">{value.toLocaleString()}</span> },
    { title: '磁盘', dataIndex: 'file_size', align: 'right', width: 100, render: (value) => <span className="mono">{(value / 1024).toFixed(1)} KB</span> },
    {
      title: '', width: 64, align: 'right',
      render: (_, record) => (
        <Popconfirm title="删除这份日线缓存？" onConfirm={() => remove(record)}>
          <Button type="text" danger icon={<DeleteOutlined />} aria-label="删除缓存" />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div><div className="eyebrow">MARKET DATA / LOCAL STORAGE</div><h1>日线数据中心</h1></div>
        <Button icon={<ReloadOutlined />} onClick={() => refresh()}>刷新清单</Button>
      </div>

      <section className="terminal-panel data-download-panel">
        <div className="panel-title"><span>下载任务</span><small>明确联网动作 · CSV + 覆盖清单写入后端本地磁盘</small></div>
        <Form layout="vertical" className="download-form">
          <Form.Item label="股票（可多选）" required>
            <Select
              mode="multiple" showSearch filterOption={false} loading={searching}
              placeholder="输入股票代码或名称搜索，例如 600519"
              value={selectedCodes} onChange={setSelectedCodes} onSearch={search}
              options={options.map((stock) => ({ value: stock.code, label: `${stock.code}  ${stock.name}` }))}
              notFoundContent="输入关键词开始搜索"
            />
          </Form.Item>
          <Form.Item label="缓存时间范围" required>
            <RangePicker value={range} onChange={(value) => value && setRange(value as [Dayjs, Dayjs])} allowClear={false} />
          </Form.Item>
          <Form.Item label="复权方式">
            <Select value="qfq" options={[{ value: 'qfq', label: '前复权（当前系统固定）' }]} disabled />
          </Form.Item>
          <Form.Item label=" ">
            <Button type="primary" icon={<CloudDownloadOutlined />} loading={loading} onClick={download}>下载并补齐缺口</Button>
          </Form.Item>
        </Form>
        <div className="data-note"><strong>范围规则</strong> 缓存范围可以比游戏范围更大，以便多次复用。游戏启动前只做本地覆盖检查，不会自动下载。</div>
      </section>

      <section className="terminal-panel">
        <div className="panel-title"><span>本地缓存清单</span><small>{cache.length} 个标的 / 复权组合</small></div>
        <Table rowKey={(row) => `${row.code}-${row.adjust}`} columns={columns} dataSource={cache} pagination={false} scroll={{ x: 980 }} locale={{ emptyText: '尚无日线缓存，请先创建下载任务' }} />
      </section>
    </div>
  );
}
