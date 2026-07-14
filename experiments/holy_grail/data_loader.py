"""实验数据加载器 - 保证收益率正确的行情数据。

背景：腾讯接口的"前复权"是减法复权，低价区间的日涨跌幅会被
严重放大（九安医疗2021-11出现+39.8%的"日涨幅"，主板上限只有10%），
不能用于回测。腾讯的"后复权"是比例复权，日收益率与真实一致。

本加载器取后复权数据，再整体缩放到区间首日的不复权真实价位：
- 日涨跌幅、收益率与真实完全一致（比例缩放不改变比率）
- 价格量级与当时的真实行情接近，便于视频展示

用法:
    engine = RatioAdjustedDataEngine(cache_dir=...)
    df = engine.get_daily_data(code, start, end)   # 无视 adjust 参数，总是返回缩放后的后复权数据
"""

from datetime import date

import pandas as pd

from src.data_engine.engine import DataEngine


class RatioAdjustedDataEngine(DataEngine):
    """后复权数据引擎：收益率正确，价格缩放到区间首日真实价位。"""

    def get_daily_data(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",  # 参数保留以兼容 Simulator 调用，实际总是使用 hfq
    ) -> pd.DataFrame:
        hfq = super().get_daily_data(code, start_date, end_date, adjust="hfq")
        if hfq.empty:
            return hfq

        raw = super().get_daily_data(code, start_date, end_date, adjust="")
        if raw.empty:
            return hfq

        # 用首个共同交易日的 不复权收盘价 / 后复权收盘价 计算缩放系数
        first_date = hfq["date"].iloc[0]
        raw_match = raw[raw["date"] == first_date]
        if raw_match.empty:
            return hfq

        scale = float(raw_match["close"].iloc[0]) / float(hfq["close"].iloc[0])

        scaled = hfq.copy()
        for col in ("open", "high", "low", "close"):
            scaled[col] = (hfq[col] * scale).round(4)

        return scaled
