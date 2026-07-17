from datetime import date

from api.services.session import SessionManager
from src.account.account import Account
from src.trading.engine import TradingEngine
from src.trading.models import OrderStatus


def test_immediate_order_records_actual_fill_date():
    engine = TradingEngine(Account(initial_cash=100_000))
    trade_date = date(2024, 1, 2)

    order = engine.submit_buy_order(
        "000001", 10.0, 100, trade_date, current_price=10.0
    )

    assert order.status == OrderStatus.FILLED
    assert order.filled_date == trade_date


def test_pending_order_records_later_fill_date():
    engine = TradingEngine(Account(initial_cash=100_000))
    order_date = date(2024, 1, 2)
    fill_date = date(2024, 1, 5)

    order = engine.submit_buy_order(
        "000001", 9.0, 100, order_date, current_price=10.0
    )
    filled = engine.check_pending_orders({"000001": 8.5}, fill_date)

    assert filled == [order]
    assert order.status == OrderStatus.FILLED
    assert order.filled_date == fill_date


def test_legacy_filled_order_uses_order_date_as_fill_date():
    payload = {
        "order_id": "legacy01",
        "code": "000001",
        "order_type": "buy",
        "price": 10.0,
        "quantity": 100,
        "order_date": "2024-01-02",
        "status": "filled",
        "filled_price": 10.0,
        "filled_quantity": 100,
        "fee": 5.0,
    }

    order = SessionManager._order_from_dict(payload)

    assert order.filled_date == date(2024, 1, 2)
