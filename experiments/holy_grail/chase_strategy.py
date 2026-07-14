"""追涨杀跌策略 - 经典韭菜"拍脑袋指标"。

规则（完全不需要金融学位）：
- 今天涨了 buy_pct% 以上 → 它要起飞了，满仓买入
- 今天跌了 sell_pct% 以上 → 药丸，全部割肉
- 其他时候拿住不动

现实约束：
- 一字板（最高价==最低价）当天既买不进也卖不出，跳过
- 买入以收盘价成交，数量取整到 100 股
"""

from datetime import date

from src.account.account import Account
from src.trading.models import DailyBar


class ChaseStrategy:
    """追涨杀跌策略（单只股票，全仓进出）。"""

    def __init__(self, buy_pct: float = 3.0, sell_pct: float = 5.0):
        """
        Args:
            buy_pct: 单日涨幅超过该百分比时买入，如 3.0 表示 +3%
            sell_pct: 单日跌幅超过该百分比时卖出，如 5.0 表示 -5%
        """
        self.buy_pct = buy_pct
        self.sell_pct = sell_pct
        self.prev_close: dict[str, float] = {}

    def __call__(
        self,
        current_date: date,
        bars: dict[str, DailyBar],
        account: Account
    ) -> list[tuple]:
        instructions = []

        for code, bar in bars.items():
            prev = self.prev_close.get(code)
            self.prev_close[code] = bar.close

            if prev is None or prev <= 0:
                continue

            change_pct = (bar.close - prev) / prev * 100.0

            # 一字板当天无法成交（现实约束）
            if bar.high == bar.low:
                continue

            if change_pct >= self.buy_pct and code not in account.positions:
                quantity = int(account.cash * 0.999 / bar.close / 100) * 100
                if quantity >= 100:
                    instructions.append(("buy", code, bar.close, quantity))

            elif change_pct <= -self.sell_pct and code in account.positions:
                position = account.positions[code]
                instructions.append(("sell", code, bar.close, position.quantity))

        return instructions
