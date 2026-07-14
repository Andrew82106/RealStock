"""临时脚本：检查缓存的后复权数据全区间日涨幅是否越限（创业板±21%，主板±11%）。"""
import sys
from pathlib import Path

import pandas as pd

cache = Path(__file__).resolve().parent / "data_cache"
for f in sorted(cache.glob("*_hfq.csv")):
    code = f.stem.split("_")[0]
    limit = 21.0 if code.startswith(("300", "688")) else 11.0
    df = pd.read_csv(f)
    closes = df["close"].tolist()
    dates = df["date"].tolist()
    bad = []
    for i in range(1, len(closes)):
        chg = (closes[i] / closes[i - 1] - 1) * 100
        if abs(chg) > limit:
            bad.append((dates[i], round(chg, 2)))
    status = "OK" if not bad else f"异常 {len(bad)} 天: {bad[:5]}"
    print(f"{code} (±{limit:.0f}%): {status}")
