# 韭菜模拟器（RealStock）

一个使用 A 股历史日线进行虚拟交易的本地模拟器。核心流程是：明确下载行情到本地、设计可复现指标、设定游戏区间，然后逐个交易日揭示行情并进行交易模拟。

系统仅用于学习、内容创作和娱乐，不构成投资建议。

## 当前产品边界

- 游戏只使用日线 OHLCV，不展示或请求小时线、分钟线和虚构分时线。
- 下载行情是用户明确触发的独立动作；游戏运行过程中只读本地缓存。
- 缓存范围可以大于游戏范围，但不能小于游戏范围。启动前会逐只股票检查并列出缺口。
- 游戏会额外加载开始日前 31 天的日线作为首屏观察窗口和指标预热；正式进度仍从所选开始日计算。
- 图表只返回开始日前观察窗口及截至当前游戏日的数据，不泄露后续行情。
- 游戏会话会写入 `storage/game_sessions`，后端热重载或重启后可继续恢复。
- 新指标使用固定接口的 Python 代码计算；系统会限制导入模块、在独立进程中执行并设置 5 秒超时，但它不是绝对安全沙箱，只应运行自己编写或确认可信的代码。
- A 股 T+1、佣金和印花税规则仍由交易引擎处理。

仓库中仍保留旧分时回放引擎和相关测试，以免破坏历史代码；新建游戏不会调用它们。

## 三个主入口

### 日线数据中心

在这里选择股票和缓存时间范围，显式下载前复权日线。后端会同时保存：

- `storage/stock_data/{code}_qfq.csv`：实际 OHLCV 数据；
- `storage/stock_data/daily_cache_manifest.json`：明确查询并确认过的日期覆盖范围。

已有旧版 CSV 会在启动时自动登记到覆盖清单。删除缓存会同时删除 CSV 和对应的覆盖记录。

### 指标工坊

系统内置只读的“Leek共振指数”，作为开箱即用的默认可选指标。它只会出现在指标库和游戏的指标选择框中；需要修改时先“另存副本”，内置原件不能覆盖或删除。

新指标统一用 Python 编写，固定接口如下：

```python
import pandas as pd


def calculate(data: pd.DataFrame) -> pd.Series:
    """返回与 data 等长的指标数值。"""
    close = data["close"].astype(float)
    fast_ma = close.rolling(5).mean()
    slow_ma = close.rolling(20).mean()
    return (fast_ma / slow_ma - 1) * 100
```

接口规则：

1. 必须定义 `calculate(data)`，代码只负责计算指标值；
2. `data` 按日期升序排列，包含 `date`、`open`、`high`、`low`、`close`、`volume` 六列；
3. 返回值可以是 Pandas `Series`、NumPy 数组、列表，或包含 `value` 列的 DataFrame，长度必须与输入数据一致；
4. 数据不足的预热位置返回 `NaN`，系统会将其标记为 `warming_up`，不生成交易信号；
5. 当数值大于等于买入阈值时为 `buy`，小于等于卖出阈值时为 `sell`，其余为 `hold`；
6. 只允许导入 `pandas`、`numpy`、`math`，单次计算超过 5 秒会被终止。

指标可以保存为 `.indicator.json`，也可导入 `.py` 或 `.indicator.json`。指标工坊会使用本地缓存行情运行和预览代码；游戏启动时可选择一个指标，其数值和信号随交易日推进实时更新。旧版搭建式指标文件仍可计算和使用，但新建指标不再采用分量搭建模式。

### 新建日线模拟

这里只设定游戏范围、股票、初始资金和可选指标。启动步骤为：

1. 检查本地缓存是否覆盖完整游戏范围；
2. 若有缺口，明确选择是否下载；
3. 覆盖完整后启动本地日线会话；
4. 每次点击只推进一个交易日。

## 本地开发

要求 Python 3.10+、Node.js 18+。

```bash
# 后端依赖
pip install -e ".[dev]"

# 前端依赖
cd frontend
npm install
cd ..
```

分别启动后端和前端：

```bash
python -m uvicorn api.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Vite 默认访问地址为 `http://localhost:3000`，FastAPI 文档位于 `http://localhost:8000/docs`。

## 验证

```bash
# 后端与核心逻辑
pytest -q

# 前端严格类型检查和生产构建
cd frontend
npm run typecheck
npm run build
```

## 目录

```text
RealStock/
├── api/
│   ├── routers/
│   │   ├── stocks.py          # 日线下载、覆盖检查、缓存清单
│   │   ├── indicators.py      # 指标 CRUD 与预览
│   │   └── game.py            # 日线游戏、交易、逐日推进
│   └── services/
│       ├── indicator_service.py
│       ├── indicator_runner.py # Python 指标独立进程执行器
│       └── session.py
├── src/
│   ├── data_engine/           # AkShare 获取与磁盘缓存
│   ├── trading/               # 委托撮合
│   ├── account/               # 账户与费用
│   └── simulator/             # 日线 / 旧版兼容模拟器
├── frontend/src/
│   ├── pages/DataCenter.tsx
│   ├── pages/IndicatorLab.tsx
│   ├── pages/GameSetup.tsx
│   └── pages/TradingView.tsx
├── storage/
│   ├── stock_data/            # 本地行情与覆盖清单
│   ├── indicators/            # 已保存指标文件
│   └── game_sessions/         # 可跨服务重启恢复的游戏会话
└── tests/
```

## 技术栈

- FastAPI、Pandas、NumPy、AkShare
- React 18、TypeScript、Ant Design、ECharts、Vite
- Pytest、Hypothesis

## 免责声明

历史区间内表现良好不代表未来有效，回测结果不能作为指标未来有效的保证。
