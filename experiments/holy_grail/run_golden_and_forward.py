"""圣杯验收 + 锁参续跑 - 用真实模拟器复核高光区间，然后看它现出原形。

对指定的 (股票, 参数, 高光区间) 跑三轮真实回测
（含佣金、印花税、T+1、100股整手、一字板不成交）：

  Run 1 高光区间   : 区间前一交易日 ~ 区间结束，空仓起步 10 万
                     → 验证"一个月翻倍"是否真实成立
  Run 2 完整剧情弧 : 区间前一交易日 ~ 今天，同一账户不落袋
                     → 圣杯诞生后继续用它，钱的完整轨迹
  Run 3 锁参后入场 : 区间结束后第一天 ~ 今天，空仓起步 10 万
                     → 如果有人看到"战绩"后才开始抄作业

用法:
    python experiments/holy_grail/run_golden_and_forward.py <code> <buy_pct> <sell_pct> <window_start> <window_end> [strategy]
    strategy: chase(默认) 或 lri（Leek共振指数，忽略 buy_pct/sell_pct 参数）
例:
    python experiments/holy_grail/run_golden_and_forward.py 002432 3 5 2021-11-09 2021-12-08
    python experiments/holy_grail/run_golden_and_forward.py 002583 0 0 2024-09-25 2024-10-31 lri
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.simulator.simulator import Simulator
from experiments.holy_grail.chase_strategy import ChaseStrategy
from experiments.holy_grail.grail_indicator import GrailIndicatorStrategy
from experiments.holy_grail.data_loader import RatioAdjustedDataEngine

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

DATA_START = date(2019, 12, 2)
DATA_END = date(2026, 7, 14)
INITIAL_CASH = 100_000.0

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "data_cache"
RESULTS_DIR = HERE / "results"


def run_once(
    engine: RatioAdjustedDataEngine,
    code: str,
    start: date,
    end: date,
    strategy_factory,
    tag: str,
) -> dict:
    """跑一轮真实回测，导出净值和交易日志，返回摘要。"""
    sim = Simulator(engine, initial_cash=INITIAL_CASH)
    sim.setup(stock_codes=[code], start_date=start, end_date=end)
    strategy = strategy_factory()
    metrics = sim.run_backtest(strategy)

    # 净值曲线（run_backtest 每天记录一次，首尾可能重复，去重保留最后值）
    nv = pd.DataFrame(sim.net_value_history, columns=["date", "net_value"])
    nv = nv.drop_duplicates(subset="date", keep="last").reset_index(drop=True)
    nv.to_csv(RESULTS_DIR / f"{tag}_net_value.csv", index=False, encoding="utf-8-sig")

    sim.trading_engine.export_trade_log_to_csv(str(RESULTS_DIR / f"{tag}_trades.csv"))

    peak_idx = nv["net_value"].idxmax()
    summary = {
        "tag": tag,
        "start": str(start),
        "end": str(end),
        "trading_days": len(sim.trading_dates),
        "final_assets": round(sim.account.total_assets, 2),
        "total_return_pct": round(metrics.total_return * 100, 2),
        "max_drawdown_pct": round(metrics.max_drawdown * 100, 2),
        "peak_assets": round(float(nv["net_value"].max()), 2),
        "peak_date": str(nv["date"].iloc[peak_idx]),
        "win_rate_pct": round(metrics.win_rate * 100, 2),
        "total_trades": metrics.total_trades,
        "filled_orders": sum(
            1 for o in sim.trading_engine.get_trade_history()
            if o.status.value == "filled"
        ),
    }
    return {"summary": summary, "net_value": nv}


def plot_curve(nv: pd.DataFrame, title: str, out_png: Path, lock_date: date = None):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(pd.to_datetime(nv["date"]), nv["net_value"] / 10_000, linewidth=1.6)
    ax.axhline(INITIAL_CASH / 10_000, color="gray", linestyle=":", linewidth=1)
    if lock_date is not None:
        ax.axvline(pd.Timestamp(lock_date), color="firebrick", linestyle="--", linewidth=1.2)
        ax.text(pd.Timestamp(lock_date), ax.get_ylim()[1] * 0.97, " 参数锁定日",
                color="firebrick", fontsize=10, va="top")
    ax.set_title(title, fontsize=13)
    ax.set_ylabel("总资产（万元）")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    plt.close(fig)


def main():
    if len(sys.argv) not in (6, 7):
        print(__doc__)
        sys.exit(1)

    code = sys.argv[1]
    buy_pct = float(sys.argv[2])
    sell_pct = float(sys.argv[3])
    window_start = date.fromisoformat(sys.argv[4])
    window_end = date.fromisoformat(sys.argv[5])
    strategy_name = sys.argv[6] if len(sys.argv) == 7 else "chase"

    RESULTS_DIR.mkdir(exist_ok=True)
    engine = RatioAdjustedDataEngine(cache_dir=str(CACHE_DIR))

    df = engine.get_daily_data(code, DATA_START, DATA_END)
    dates = df["date"].tolist()
    ws_idx = next(i for i, d in enumerate(dates) if d >= window_start)
    we_idx = next(i for i, d in enumerate(dates) if d >= window_end)

    if strategy_name == "lri":
        # LRI 需要预热：窗口前留 10 个交易日算指标，预热期不交易
        warmup = 10
        warmup_start = dates[max(ws_idx - warmup - 1, 0)]
        forward_start = dates[max(we_idx - warmup + 1, 0)]
        strategy_factory = lambda: GrailIndicatorStrategy(warmup_days=warmup)
        prefix = f"{code}_lri"
        print(f"股票 {code} | Leek共振指数（≥88买入 / ≤44清仓，预热{warmup}日）")
    else:
        warmup_start = dates[max(ws_idx - 1, 0)]
        forward_start = dates[min(we_idx + 1, len(dates) - 1)]
        strategy_factory = lambda: ChaseStrategy(buy_pct=buy_pct, sell_pct=sell_pct)
        prefix = f"{code}_bt{buy_pct:g}_st{sell_pct:g}"
        print(f"股票 {code} | 买入阈值 +{buy_pct}% | 卖出阈值 -{sell_pct}%")
    print(f"高光区间 {window_start} ~ {window_end} | 数据截止 {DATA_END}\n")

    runs = [
        ("golden", warmup_start, window_end, f"Run1 高光区间（{window_start}~{window_end}）"),
        ("full_arc", warmup_start, DATA_END, "Run2 完整剧情弧（同一账户继续用圣杯）"),
        ("forward", forward_start, DATA_END, "Run3 锁参后入场（看到战绩才抄作业）"),
    ]

    strategy_desc = ("Leek共振指数(88/44)" if strategy_name == "lri"
                     else f"追涨+{buy_pct:g}%/杀跌-{sell_pct:g}%")

    all_summaries = {}
    for tag, start, end, label in runs:
        full_tag = f"{prefix}_{tag}"
        result = run_once(engine, code, start, end, strategy_factory, full_tag)
        s = result["summary"]
        all_summaries[tag] = s

        lock = window_end if tag == "full_arc" else None
        plot_curve(result["net_value"],
                   f"{label}  {code}  {strategy_desc}",
                   RESULTS_DIR / f"{full_tag}.png", lock_date=lock)

        print(f"[{label}]")
        print(f"  期间: {s['start']} ~ {s['end']} ({s['trading_days']} 个交易日)")
        print(f"  期末资产: {s['final_assets']:,.0f} 元 "
              f"(收益 {s['total_return_pct']:+.1f}%)")
        print(f"  峰值资产: {s['peak_assets']:,.0f} 元 @ {s['peak_date']}")
        print(f"  最大回撤: {s['max_drawdown_pct']:.1f}% | "
              f"胜率 {s['win_rate_pct']:.0f}% | 完成交易 {s['total_trades']} 笔")
        print()

    # 剧情弧关键数字
    g, f_ = all_summaries["golden"], all_summaries["full_arc"]
    print("=" * 60)
    print("剧情弧关键数字")
    print("=" * 60)
    print(f"  高光区间真实倍数: {g['final_assets'] / INITIAL_CASH:.2f}x "
          f"({g['trading_days']} 个交易日)")
    print(f"  完整弧峰值: {f_['peak_assets']:,.0f} 元 @ {f_['peak_date']}")
    print(f"  完整弧期末: {f_['final_assets']:,.0f} 元")
    give_back = (f_['peak_assets'] - f_['final_assets']) / max(f_['peak_assets'] - INITIAL_CASH, 1)
    print(f"  利润回吐比例: {give_back * 100:.0f}%")

    with open(RESULTS_DIR / f"{prefix}_summary.json", "w", encoding="utf-8") as fp:
        json.dump(all_summaries, fp, ensure_ascii=False, indent=2)
    print(f"\n结果文件已保存到: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
