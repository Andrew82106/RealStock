"""韭菜共振指数 LRI (Leek Resonance Index) - 一个煞有介事的拍脑袋超级指标。

像 RSI/MACD 一样：0-100 振荡、有信号阈值、能画在副图上。
公式看起来很专业，参数全部拍脑袋：

    动量共振核  M = 0.7·EMA3(日收益%) + 0.3·EMA8(日收益%)     # 8 = 发，吉利
    量能激励项  V = ln(1 + Vol / MA5(Vol))                      # 放量说明主力来了
    玄学修正    Θ = 1 + 0.08·sin(2π·交易日序号/8)               # 八日玄学周期（纯编的）
    韭菜共振    LRI = 100 · sigmoid( k · M · (1 + β·V) · Θ )    # k=信仰系数, β=跟风系数

    信号: LRI ≥ 88 → 买入（88，要发）
          LRI ≤ 44 → 清仓（44，要死）
          中间     → 拿住，相信共振

玄学修正因子 Θ 对结果影响不到 ±8%，但它在公式里，这很重要。

免责声明：本指标为视频节目效果专门设计，任何时候都不构成投资建议。
"""

import math
from datetime import date

import pandas as pd

from src.account.account import Account
from src.trading.models import DailyBar

# ---- 拍脑袋参数（全部有名字，全部没道理）----
FAITH_K = 1.0          # 信仰系数：信仰越足，指标越果断
FOLLOW_BETA = 0.5      # 跟风系数：放量时跟风的力度
MYSTIC_PERIOD = 8      # 玄学周期：8，发
MYSTIC_AMP = 0.08      # 玄学振幅：还是8
EMA_FAST = 3           # 快动量周期
EMA_SLOW = 8           # 慢动量周期：又是8
VOL_MA = 5             # 量能基准周期
BUY_LEVEL = 88.0       # 买入阈值：要发发
SELL_LEVEL = 44.0      # 卖出阈值：要死死


def _sigmoid(x: float) -> float:
    if x > 50:
        return 1.0
    if x < -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class LRICalculator:
    """增量式 LRI 计算器（逐日喂数据，只用历史信息）。"""

    def __init__(self):
        self.prev_close: float | None = None
        self.ema_fast: float | None = None
        self.ema_slow: float | None = None
        self.vol_window: list[float] = []
        self.day_index: int = 0

    def update(self, bar: DailyBar) -> float | None:
        """喂入一根日线，返回当日 LRI（数据不足时返回 None）。"""
        self.day_index += 1

        if self.prev_close is None or self.prev_close <= 0:
            self.prev_close = bar.close
            self.vol_window.append(float(bar.volume))
            return None

        ret_pct = (bar.close - self.prev_close) / self.prev_close * 100.0
        self.prev_close = bar.close

        # EMA 动量
        alpha_f = 2.0 / (EMA_FAST + 1)
        alpha_s = 2.0 / (EMA_SLOW + 1)
        self.ema_fast = ret_pct if self.ema_fast is None else (
            alpha_f * ret_pct + (1 - alpha_f) * self.ema_fast)
        self.ema_slow = ret_pct if self.ema_slow is None else (
            alpha_s * ret_pct + (1 - alpha_s) * self.ema_slow)
        momentum = 0.7 * self.ema_fast + 0.3 * self.ema_slow

        # 量能激励
        vol_ma = sum(self.vol_window[-VOL_MA:]) / max(len(self.vol_window[-VOL_MA:]), 1)
        vol_term = math.log(1.0 + float(bar.volume) / vol_ma) if vol_ma > 0 else 0.0
        self.vol_window.append(float(bar.volume))

        # 玄学修正
        mystic = 1.0 + MYSTIC_AMP * math.sin(2 * math.pi * self.day_index / MYSTIC_PERIOD)

        x = FAITH_K * momentum * (1.0 + FOLLOW_BETA * vol_term) * mystic
        return 100.0 * _sigmoid(x)


def compute_lri_series(df: pd.DataFrame) -> pd.Series:
    """对整个 DataFrame 计算 LRI 序列（用于画图和前端对照）。"""
    calc = LRICalculator()
    values = []
    for _, row in df.iterrows():
        bar = DailyBar(
            date=row["date"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )
        values.append(calc.update(bar))
    return pd.Series(values, index=df.index, name="lri")


class GrailIndicatorStrategy:
    """超级指标策略：LRI ≥ 88 满仓买入，LRI ≤ 44 清仓卖出。

    与 Simulator.run_backtest 的策略接口兼容。
    warmup_days: 起始预热天数，预热期内只计算指标不交易。
    """

    def __init__(self, warmup_days: int = 10):
        self.warmup_days = warmup_days
        self.calcs: dict[str, LRICalculator] = {}
        self.days_seen: dict[str, int] = {}
        self.last_lri: dict[str, float] = {}

    def __call__(
        self,
        current_date: date,
        bars: dict[str, DailyBar],
        account: Account
    ) -> list[tuple]:
        instructions = []

        for code, bar in bars.items():
            calc = self.calcs.setdefault(code, LRICalculator())
            self.days_seen[code] = self.days_seen.get(code, 0) + 1

            lri = calc.update(bar)
            if lri is None:
                continue
            self.last_lri[code] = lri

            if self.days_seen[code] <= self.warmup_days:
                continue  # 预热期不交易

            if bar.high == bar.low:
                continue  # 一字板当天无法成交

            if lri >= BUY_LEVEL and code not in account.positions:
                quantity = int(account.cash * 0.999 / bar.close / 100) * 100
                if quantity >= 100:
                    instructions.append(("buy", code, bar.close, quantity))

            elif lri <= SELL_LEVEL and code in account.positions:
                position = account.positions[code]
                instructions.append(("sell", code, bar.close, position.quantity))

        return instructions
