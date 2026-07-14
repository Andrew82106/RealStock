"""临时脚本：对比腾讯接口 qfq / hfq / 不复权 数据的日涨幅质量。

主板/中小板涨跌停 ±10%，若某复权方式出现大量 >11% 的日涨幅，
说明该复权方式扭曲了收益率，不能用于回测。
"""
import akshare as ak
import pandas as pd


def daily_changes(df: pd.DataFrame, label: str, limit: float = 11.0):
    closes = df["close"].astype(float).tolist()
    dates = df["date"].astype(str).tolist()
    bad = []
    for i in range(1, len(closes)):
        chg = (closes[i] / closes[i - 1] - 1) * 100
        if abs(chg) > limit:
            bad.append((dates[i], round(chg, 2)))
    print(f"[{label}] 共 {len(closes)} 天, 超±{limit}% 的天数: {len(bad)}")
    for d, c in bad[:10]:
        print(f"    {d}: {c:+.2f}%")
    return bad


for adjust, label in [("qfq", "前复权"), ("hfq", "后复权"), ("", "不复权")]:
    try:
        df = ak.stock_zh_a_hist_tx(
            symbol="sz002432",
            start_date="20211101",
            end_date="20211231",
            adjust=adjust,
        )
        daily_changes(df, f"九安医疗 2021-11~12 {label}")
    except Exception as e:
        print(f"[{label}] 失败: {str(e)[:100]}")
    print()

# 检查跨除权日（2022年6月 10转9派2）的表现
for adjust, label in [("hfq", "后复权"), ("", "不复权")]:
    try:
        df = ak.stock_zh_a_hist_tx(
            symbol="sz002432",
            start_date="20220601",
            end_date="20220730",
            adjust=adjust,
        )
        daily_changes(df, f"九安医疗 2022-06~07(跨除权) {label}")
    except Exception as e:
        print(f"[{label}] 失败: {str(e)[:100]}")
    print()
