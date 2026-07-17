import { CodeOutlined, CopyOutlined, DeleteOutlined, DownloadOutlined, EyeOutlined, PlusOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, DatePicker, Input, InputNumber, List, Modal, Popconfirm, Segmented, Select, Tag, Upload, message } from 'antd';
import type { UploadProps } from 'antd';
import axios from 'axios';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import EChartsWrapper from '../components/EChartsWrapper';
import { indicatorApi, stockApi } from '../services/api';
import type { CacheStatus, IndicatorDefinition, IndicatorPreview } from '../types';

const { RangePicker } = DatePicker;

const PYTHON_TEMPLATE = `import pandas as pd


def calculate(data: pd.DataFrame) -> pd.Series:
    """返回与 data 等长的指标数值；数据不足的位置返回 NaN。"""
    close = data["close"].astype(float)
    fast_ma = close.rolling(5).mean()
    slow_ma = close.rolling(20).mean()
    return (fast_ma / slow_ma - 1) * 100
`;

const blankIndicator = (): IndicatorDefinition => ({
  name: '自定义指标',
  description: '记录指标思路、适用条件和观察目标。',
  version: 1,
  language: 'python',
  code: PYTHON_TEMPLATE,
  components: [],
  buy_threshold: 5,
  sell_threshold: -5,
});

const PYTHON_TOKEN_PATTERN = /(#[^\n]*|"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield)\b|\b\d+(?:\.\d+)?\b|@[A-Za-z_]\w*)/g;
const PYTHON_KEYWORDS = new Set(['and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield']);

function pythonTokenClass(token: string): string {
  if (token.startsWith('#')) return 'python-token-comment';
  if (token.startsWith('"') || token.startsWith("'")) return 'python-token-string';
  if (token.startsWith('@')) return 'python-token-decorator';
  if (/^\d/.test(token)) return 'python-token-number';
  if (PYTHON_KEYWORDS.has(token)) return 'python-token-keyword';
  return '';
}

function PythonCodePreview({ source, compact = false }: { source: string; compact?: boolean }) {
  const visibleSource = compact ? source.split('\n').slice(0, 7).join('\n') : source;
  const tokens = visibleSource.split(PYTHON_TOKEN_PATTERN);
  return <pre className={`python-code-preview${compact ? ' compact' : ''}`}><code>{tokens.map((token, index) => {
    const className = pythonTokenClass(token);
    return className ? <span className={className} key={`${index}-${token.slice(0, 8)}`}>{token}</span> : token;
  })}</code></pre>;
}

function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === 'string' ? detail : error.message;
  }
  return error instanceof Error ? error.message : '操作失败';
}

export default function IndicatorLab() {
  const [definitions, setDefinitions] = useState<IndicatorDefinition[]>([]);
  const [draft, setDraft] = useState<IndicatorDefinition>(blankIndicator());
  const [preview, setPreview] = useState<IndicatorPreview | null>(null);
  const [code, setCode] = useState('600519');
  const [cachedStocks, setCachedStocks] = useState<CacheStatus[]>([]);
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs('2019-01-01'), dayjs('2020-12-31')]);
  const [saving, setSaving] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [codeModalOpen, setCodeModalOpen] = useState(false);
  const [codeViewMode, setCodeViewMode] = useState<'preview' | 'edit'>('preview');

  const refresh = async () => setDefinitions(await indicatorApi.list());
  useEffect(() => { refresh().catch((error) => message.error(errorText(error))); }, []);
  useEffect(() => {
    stockApi.listCache().then((items) => {
      const unique = Array.from(new Map(items.map((item) => [item.code, item])).values());
      setCachedStocks(unique);
      if (unique.length && !unique.some((item) => item.code === code)) setCode(unique[0].code);
    }).catch((error) => message.error(errorText(error)));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = draft.builtin ? {
        ...draft, id: undefined, builtin: false, name: `${draft.name}（副本）`,
      } : draft;
      const saved = await indicatorApi.save(payload);
      setDraft(saved); await refresh();
      message.success(draft.builtin ? '内置指标已另存为可编辑副本' : 'Python 指标已保存');
    } catch (error) { message.error(errorText(error)); }
    finally { setSaving(false); }
  };

  const remove = async () => {
    if (!draft.id || draft.builtin) return;
    try {
      await indicatorApi.remove(draft.id); setDraft(blankIndicator()); setPreview(null); await refresh();
      message.success('指标已删除');
    } catch (error) { message.error(errorText(error)); }
  };

  const calculate = async () => {
    if (!code) return message.warning('请选择一只已缓存股票');
    setCalculating(true);
    try {
      setPreview(await indicatorApi.preview({
        code,
        start_date: range[0].format('YYYY-MM-DD'),
        end_date: range[1].format('YYYY-MM-DD'),
        definition: draft,
      }));
    } catch (error) { message.error(errorText(error)); }
    finally { setCalculating(false); }
  };

  const importProps: UploadProps = {
    accept: '.py,.json,.indicator.json', showUploadList: false,
    beforeUpload: async (file) => {
      try {
        const text = await file.text();
        if (file.name.toLowerCase().endsWith('.py')) {
          setDraft({
            ...blankIndicator(),
            name: file.name.replace(/\.py$/i, ''),
            description: '从 Python 文件导入',
            code: text,
          });
        } else {
          const imported = JSON.parse(text) as IndicatorDefinition;
          if (imported.schema && !['realstock-indicator/v1', 'realstock-indicator/v2'].includes(imported.schema)) {
            throw new Error('不支持的指标文件版本');
          }
          setDraft({
            ...imported,
            id: undefined,
            builtin: false,
            created_at: undefined,
            updated_at: undefined,
            language: imported.language || (imported.code ? 'python' : 'builder'),
            name: `${imported.name || '导入指标'}（导入）`,
          });
        }
        setPreview(null); message.success('已导入编辑器，请检查并计算后再保存');
      } catch (error) { message.error(errorText(error)); }
      return false;
    },
  };

  const exportFile = () => {
    const payload = JSON.stringify({ ...draft, schema: 'realstock-indicator/v2' }, null, 2);
    const url = URL.createObjectURL(new Blob([payload], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `${draft.name.replace(/[\\/:*?"<>|]/g, '_') || 'indicator'}.indicator.json`; anchor.click();
    URL.revokeObjectURL(url);
  };

  const convertLegacy = () => setDraft({
    ...draft,
    id: undefined,
    builtin: false,
    name: `${draft.name}（Python 版）`,
    language: 'python',
    code: PYTHON_TEMPLATE,
    components: [],
  });

  const option = useMemo<Record<string, unknown>>(() => {
    const values = preview?.values || [];
    return {
      backgroundColor: 'transparent', animation: false,
      tooltip: { trigger: 'axis', backgroundColor: '#111821', borderColor: '#33404d', textStyle: { color: '#d8e0e8' } },
      grid: { left: 54, right: 18, top: 30, bottom: 42 },
      xAxis: { type: 'category', data: values.map((item) => item.date), axisLine: { lineStyle: { color: '#33404d' } }, axisLabel: { color: '#7f8c99' } },
      yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#1d2732' } }, axisLabel: { color: '#7f8c99' } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 4, borderColor: '#26313d', fillerColor: '#31415455' }],
      series: [
        { type: 'line', name: draft.name, showSymbol: false, connectNulls: false, data: values.map((item) => item.value), lineStyle: { color: '#d6aa48', width: 1.5 }, areaStyle: { color: '#d6aa4815' } },
        { type: 'line', name: '买入阈值', showSymbol: false, data: values.map(() => draft.buy_threshold), lineStyle: { color: '#d85151', type: 'dashed', width: 1 } },
        { type: 'line', name: '卖出阈值', showSymbol: false, data: values.map(() => draft.sell_threshold), lineStyle: { color: '#1ca678', type: 'dashed', width: 1 } },
      ],
    };
  }, [preview, draft.name, draft.buy_threshold, draft.sell_threshold]);

  const validPreviewValues = preview?.values.filter((item) => item.value !== null) || [];
  const latest = validPreviewValues[validPreviewValues.length - 1];
  const isPython = draft.language !== 'builder';
  const codeLines = (draft.code || '').split('\n').length;
  const selectedStock = cachedStocks.find((item) => item.code === code);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div><div className="eyebrow">INDICATOR / PYTHON</div><h1>指标工坊</h1></div>
        <div className="heading-actions">
          <Upload {...importProps}><Button icon={<UploadOutlined />}>导入指标</Button></Upload>
          <Button icon={<DownloadOutlined />} onClick={exportFile}>导出当前</Button>
          {draft.id && !draft.builtin && <Popconfirm title="删除这个指标？" onConfirm={remove}><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>}
          <Button type="primary" icon={draft.builtin ? <CopyOutlined /> : <SaveOutlined />} loading={saving} onClick={save}>{draft.builtin ? '另存副本' : '保存指标'}</Button>
        </div>
      </div>

      <Alert type="warning" showIcon message="Python 指标会在本机执行" description="系统限制了可导入模块并设置 5 秒超时，但这不是绝对安全沙箱。只运行你本人编写或确认可信的代码。" />

      <div className="indicator-layout python-indicator-layout">
        <aside className="terminal-panel indicator-library">
          <div className="panel-title"><span>指标文件</span><Button type="text" size="small" icon={<PlusOutlined />} onClick={() => { setDraft(blankIndicator()); setPreview(null); }}>新建</Button></div>
          <List dataSource={definitions} locale={{ emptyText: '尚无已保存指标' }} renderItem={(item) => (
            <List.Item className={item.id === draft.id ? 'selected-definition' : ''} onClick={() => { setDraft(item); setPreview(null); }}>
              <List.Item.Meta title={<span>{item.name} {item.builtin && <Tag color="gold">内置</Tag>}</span>} description={item.language === 'python' ? 'Python · v' + item.version : `旧版搭建式 · ${item.components.length} 分量`} />
            </List.Item>
          )} />
        </aside>

        <section className="terminal-panel indicator-editor python-editor">
          <div className="panel-title"><span>Python 编辑器</span><small>{draft.builtin ? '内置只读 · 修改后另存副本' : 'calculate(data)'}</small></div>
          <div className="editor-fields">
            <label className="field-label">指标名称</label><Input value={draft.name} maxLength={60} disabled={draft.builtin} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            <label className="field-label">设计说明</label><Input.TextArea value={draft.description} rows={2} maxLength={500} disabled={draft.builtin} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
            <div className="threshold-grid compact-thresholds"><div><label className="field-label">买入阈值 ≥</label><InputNumber value={draft.buy_threshold} disabled={draft.builtin} onChange={(value) => setDraft({ ...draft, buy_threshold: value ?? 0 })} /></div><div><label className="field-label">卖出阈值 ≤</label><InputNumber value={draft.sell_threshold} disabled={draft.builtin} onChange={(value) => setDraft({ ...draft, sell_threshold: value ?? 0 })} /></div></div>
          </div>

          {isPython ? <>
            <div className="code-toolbar"><span>indicator.py</span><small>{codeLines} 行 · 允许 pandas / numpy / math</small></div>
            <div className="code-file-card">
              <PythonCodePreview source={draft.code || ''} compact />
              <div className="code-file-card-footer"><span><CodeOutlined /> calculate(data)</span><Button icon={<EyeOutlined />} onClick={() => { setCodeViewMode('preview'); setCodeModalOpen(true); }}>查看 / 编辑完整代码</Button></div>
            </div>
          </> : <div className="legacy-indicator-notice"><h3>这是旧版搭建式指标</h3><p>系统仍能计算和使用它，但新的指标开发统一使用 Python 接口。</p><Button onClick={convertLegacy}>创建 Python 版本</Button></div>}

          <div className="python-guide">
            <h3>接口教程</h3>
            <ol>
              <li>固定定义 <code>calculate(data)</code>。</li>
              <li><code>data</code> 是按日期升序的 DataFrame，列为 <code>date/open/high/low/close/volume</code>。</li>
              <li>返回与输入等长的 Series、数组或列表；预热位置用 <code>NaN</code>。</li>
              <li>只能使用当前及过去的数据，禁止 <code>shift(-1)</code>、居中窗口等未来函数。</li>
              <li>页面根据买入/卖出阈值生成信号，代码只负责计算指标数值。</li>
            </ol>
          </div>
        </section>

        <section className="terminal-panel indicator-preview">
          <div className="panel-title"><span>缓存数据预览</span><small>先运行代码，再决定是否保存</small></div>
          <div className="preview-controls"><Select showSearch value={code || undefined} onChange={setCode} optionFilterProp="label" placeholder="选择已缓存股票" options={cachedStocks.map((item) => ({ value: item.code, label: `${item.name || '名称待更新'}  ${item.code}` }))} /><RangePicker value={range} allowClear={false} onChange={(value) => value && setRange(value as [Dayjs, Dayjs])} /><Button type="primary" loading={calculating} disabled={!selectedStock} onClick={calculate}>运行代码</Button></div>
          <div className="signal-readout"><span>最新有效值</span><strong className="mono">{latest?.value?.toFixed(3) ?? '—'}</strong><em className={`signal-${latest?.signal || 'none'}`}>{latest?.signal === 'buy' ? '买入' : latest?.signal === 'sell' ? '卖出' : latest?.signal === 'hold' ? '观望' : '等待数据'}</em></div>
          <EChartsWrapper option={option} style={{ height: 390, width: '100%' }} />
          <p className="preview-footnote">预热期不会产生信号。历史计算结果不代表未来收益。</p>
        </section>
      </div>

      <Modal open={codeModalOpen} title={<span className="code-modal-title"><CodeOutlined /> indicator.py <small>{draft.name}</small></span>} onCancel={() => setCodeModalOpen(false)} footer={<Button onClick={() => setCodeModalOpen(false)}>完成</Button>} width={980} className="python-code-modal" destroyOnClose>
        <div className="code-modal-toolbar">
          <Segmented value={codeViewMode} options={[{ label: '格式预览', value: 'preview' }, ...(!draft.builtin ? [{ label: '编辑源码', value: 'edit' }] : [])]} onChange={(value) => setCodeViewMode(value as 'preview' | 'edit')} />
          <span>{draft.builtin ? '内置指标只读' : '修改会同步到当前指标草稿'} · {codeLines} 行 · UTF-8</span>
        </div>
        {codeViewMode === 'preview'
          ? <PythonCodePreview source={draft.code || ''} />
          : <Input.TextArea className="code-modal-textarea" value={draft.code || ''} spellCheck={false} onChange={(event) => setDraft({ ...draft, code: event.target.value })} />}
      </Modal>
    </div>
  );
}
