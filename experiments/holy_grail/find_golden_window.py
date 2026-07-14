"""高光区间搜索 - 从历史数据里给"拍脑袋指标"找一段封神行情。

对候选股票池 × 参数组合 × 全部起始日，用无摩擦近似快速模拟
追涨杀跌策略在固定长度窗口（默认22个交易日≈一个月）内的收益，
找出"一个月翻倍"级别的高光区间。

近似规则与 ChaseStrategy 一致：
- 日涨幅 >= buy_pct 且空仓 → 收盘全仓买入
- 日跌幅 <= -sell_pct 且持仓 → 收盘全仓卖出
- 一字板（high==low）当天不交易
（不含手续费，最终候选需用 run_golden_and_forward.py 的真实模拟器复核）

用法:
    python experiments/holy_grail/find_golden_window.py
"""

import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from experiments.holy_grail.data_loader import RatioAdjustedDataEngine

# 候选股票池：2020-2026 出现过大行情的标的 + 两只"正常股"对照
CANDIDATES = {
    "000001": "平安银行(对照)",
    "600519": "贵州茅台(对照)",
    "300059": "东方财富",
    "600839": "四川长虹",
    "000158": "常山北明",
    "300085": "银之杰",
    "300489": "光智科技",
    "300641": "正丹股份",
    "600611": "大众交通",
    "002583": "海能达",
    "002432": "九安医疗",
    "000957": "中通客车",
    "002761": "浙江建投",
    "601788": "光大证券",
    "600030": "中信证券",
    "601127": "赛力斯",
    "002466": "天齐锂业",
    "688256": "寒武纪",
    "300308": "中际旭创",
    "300377": "赢时胜",
    "300468": "四方精创",
    "002131": "利欧股份",
    "600733": "北汽蓝谷",
}

DATA_START = date(2019, 12, 2)
DATA_END = date(2026, 7, 14)
WINDOW_DAYS = 22          # ≈ 一个自然月的交易日数
BUY_PCTS = [2.0, 3.0, 4.0, 5.0]
SELL_PCTS = [3.0, 5.0, 7.0]

CACHE_DIR = Path(__file__).resolve().parent / "data_cache"


def load_all_data() -> dict[str, pd.DataFrame]:
    """拉取候选池全量日线数据（本地缓存，重复运行不再请求）。"""
    engine = RatioAdjustedDataEngine(cache_dir=str(CACHE_DIR))
    data = {}
    for code, name in CANDIDATES.items():
        try:
            df = engine.get_daily_data(code, DATA_START, DATA_END)
            if len(df) < WINDOW_DAYS + 10:
                print(f"  [跳过] {code} {name}: 数据不足 ({len(df)} 行)")
                continue
            data[code] = df.reset_index(drop=True)
            print(f"  [OK] {code} {name}: {len(df)} 个交易日 "
                  f"({df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")
        except Exception as e:
            print(f"  [失败] {code} {name}: {str(e)[:120]}")
        time.sleep(0.3)
    return data


def simulate_window(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    start: int,
    n_days: int,
    buy_pct: float,
    sell_pct: float,
) -> float:
    """从 start 日开始空仓起步，运行 n_days 个交易日，返回资金倍数（无摩擦近似）。

    closes[start-1] 必须存在（用于计算 start 当日涨幅）。
    """
    equity = 1.0
    shares = 0.0  # 以"1元资金能换多少份"计
    holding = False

    end = min(start + n_days, len(closes))
    for t in range(start, end):
        prev = closes[t - 1]
        if prev <= 0:
            continue
        change_pct = (closes[t] - prev) / prev * 100.0

        if holding:
            equity = shares * closes[t]

        if highs[t] == lows[t]:
            continue  # 一字板，不交易

        if not holding and change_pct >= buy_pct:
            shares = equity / closes[t]
            holding = True
        elif holding and change_pct <= -sell_pct:
            equity = shares * closes[t]
            holding = False

    return equity


def scan(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """扫描全部 股票 × 参数 × 起始日，返回按收益排序的高光区间列表。"""
    rows = []
    for code, df in data.items():
        closes = df["close"].tolist()
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        dates = df["date"].tolist()
        n = len(closes)

        for buy_pct in BUY_PCTS:
            for sell_pct in SELL_PCTS:
                best_mult, best_start = 0.0, -1
                for start in range(1, n - WINDOW_DAYS):
                    mult = simulate_window(
                        closes, highs, lows, start, WINDOW_DAYS, buy_pct, sell_pct
                    )
                    if mult > best_mult:
                        best_mult, best_start = mult, start

                if best_start > 0:
                    rows.append({
                        "code": code,
                        "name": CANDIDATES[code],
                        "buy_pct": buy_pct,
                        "sell_pct": sell_pct,
                        "window_start": dates[best_start],
                        "window_end": dates[min(best_start + WINDOW_DAYS - 1, n - 1)],
                        "approx_multiple": round(best_mult, 3),
                    })

    result = pd.DataFrame(rows).sort_values("approx_multiple", ascending=False)
    return result.reset_index(drop=True)


def main():
    print("=" * 70)
    print(f"高光区间搜索: {len(CANDIDATES)} 只候选 × "
          f"{len(BUY_PCTS) * len(SELL_PCTS)} 组参数 × 全部起始日 "
          f"(窗口 {WINDOW_DAYS} 个交易日)")
    print("=" * 70)

    print("\n[1/2] 加载数据...")
    data = load_all_data()
    print(f"\n成功加载 {len(data)} 只股票")

    print("\n[2/2] 扫描高光区间...")
    result = scan(data)

    out_path = Path(__file__).resolve().parent / "golden_windows.csv"
    result.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n每只股票每组参数的最佳窗口 Top 30 (无摩擦近似):")
    print(result.head(30).to_string(index=False))
    print(f"\n完整结果已保存: {out_path}")


if __name__ == "__main__":
    main()
