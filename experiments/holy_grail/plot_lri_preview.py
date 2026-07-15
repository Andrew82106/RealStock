"""生成 LRI 指标预览图：价格 + LRI 副图 + 买卖阈值线 + 信号点。

用法:
    python experiments/holy_grail/plot_lri_preview.py 002583 2024-08-01 2025-01-31
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from experiments.holy_grail.data_loader import RatioAdjustedDataEngine
from experiments.holy_grail.grail_indicator import (
    compute_lri_series, BUY_LEVEL, SELL_LEVEL,
)

HERE = Path(__file__).resolve().parent

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "002583"
    start = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2024, 8, 1)
    end = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else date(2025, 1, 31)

    engine = RatioAdjustedDataEngine(cache_dir=str(HERE / "data_cache"))
    df = engine.get_daily_data(code, start, end).reset_index(drop=True)
    lri = compute_lri_series(df)

    dates = pd.to_datetime(df["date"])
    buy_mask = lri >= BUY_LEVEL
    sell_mask = lri <= SELL_LEVEL

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(13, 7), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1]},
    )

    ax1.plot(dates, df["close"], linewidth=1.4, color="#333")
    ax1.scatter(dates[buy_mask], df["close"][buy_mask], marker="^",
                color="#f04a32", s=42, zorder=5, label="LRI≥88 买入区")
    ax1.scatter(dates[sell_mask], df["close"][sell_mask], marker="v",
                color="#2e8b57", s=42, zorder=5, label="LRI≤44 清仓区")
    ax1.set_title(f"{code} 收盘价与韭菜共振指数 LRI 信号  ({start} ~ {end})", fontsize=13)
    ax1.set_ylabel("收盘价（元）")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.3)

    ax2.plot(dates, lri, linewidth=1.4, color="#b0299e")
    ax2.fill_between(dates, lri.fillna(50), 50, alpha=0.12, color="#b0299e")
    ax2.axhline(BUY_LEVEL, color="#f04a32", linestyle="--", linewidth=1)
    ax2.axhline(SELL_LEVEL, color="#2e8b57", linestyle="--", linewidth=1)
    ax2.text(dates.iloc[2], BUY_LEVEL + 2, "买入线 88", color="#f04a32", fontsize=9)
    ax2.text(dates.iloc[2], SELL_LEVEL - 8, "清仓线 44", color="#2e8b57", fontsize=9)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("LRI")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    out = HERE / "results" / f"{code}_lri_preview.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=140)
    print(f"已保存: {out}")


if __name__ == "__main__":
    main()
