"""日线缓存边界与 Python / 旧版指标的回归测试。"""

import asyncio
from datetime import date, timedelta

import pandas as pd
import pytest

from api.routers import game as game_router
from api.services.indicator_service import (
    DEFAULT_INDICATOR_ID,
    IndicatorService,
    IndicatorValidationError,
)
from api.services.session import GAME_LOOKBACK_DAYS, SessionManager
from src.data_engine.engine import DataEngine
from src.exceptions import DataFetchError


def make_daily(start: date, end: date) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="B")
    return pd.DataFrame({
        "date": dates.date,
        "open": range(10, 10 + len(dates)),
        "high": range(11, 11 + len(dates)),
        "low": range(9, 9 + len(dates)),
        "close": [value + 0.5 for value in range(10, 10 + len(dates))],
        "volume": [100_000 + value * 1000 for value in range(len(dates))],
    })


def test_cache_records_requested_ranges_and_only_fetches_gaps(tmp_path, monkeypatch):
    engine = DataEngine(str(tmp_path))
    calls: list[tuple[date, date]] = []

    def fetch(_code, start, end, _adjust):
        calls.append((start, end))
        return make_daily(start, end)

    monkeypatch.setattr(engine, "_fetch_daily_from_eastmoney", fetch)

    first = engine.ensure_daily_cache("600519", date(2020, 1, 1), date(2020, 1, 10))
    assert first["complete"] is True
    assert calls == [(date(2020, 1, 1), date(2020, 1, 10))]

    expanded = engine.ensure_daily_cache("600519", date(2019, 12, 20), date(2020, 1, 15))
    assert expanded["complete"] is True
    assert calls[1:] == [
        (date(2019, 12, 20), date(2019, 12, 31)),
        (date(2020, 1, 11), date(2020, 1, 15)),
    ]
    assert expanded["ranges"] == [{"start": "2019-12-20", "end": "2020-01-15"}]
    assert expanded["row_count"] == len(make_daily(date(2019, 12, 20), date(2020, 1, 15)))


def test_cache_only_read_rejects_uncovered_range_without_network(tmp_path):
    engine = DataEngine(str(tmp_path))
    with pytest.raises(DataFetchError, match="本地缓存不完整"):
        engine.get_cached_daily_data("600519", date(2020, 1, 1), date(2020, 2, 1))


def test_indicator_round_trip_and_signal_calculation(tmp_path):
    service = IndicatorService(str(tmp_path))
    definition = {
        "name": "趋势量价指标",
        "description": "用于验证 JSON 指标的保存和计算",
        "components": [
            {"metric": "momentum", "window": 3, "weight": 1},
            {"metric": "rsi", "window": 3, "weight": 0.1},
        ],
        "buy_threshold": 1,
        "sell_threshold": -1,
    }
    saved = service.save(definition)
    assert service.get(saved["id"])["schema"] == "realstock-indicator/v2"

    values = service.compute(saved, make_daily(date(2020, 1, 1), date(2020, 1, 20)))
    assert len(values) == 14
    assert values[0]["signal"] == "warming_up"
    assert values[-1]["value"] is not None
    assert values[-1]["signal"] == "buy"


def test_indicator_rejects_unknown_metric_and_inverted_thresholds(tmp_path):
    service = IndicatorService(str(tmp_path))
    with pytest.raises(IndicatorValidationError, match="不支持"):
        service.save({
            "name": "危险指标",
            "components": [{"metric": "python_eval", "window": 5, "weight": 1}],
            "buy_threshold": 1,
            "sell_threshold": -1,
        })


def test_python_indicator_and_builtin_default(tmp_path):
    service = IndicatorService(str(tmp_path))
    builtin = service.get(DEFAULT_INDICATOR_ID)
    assert builtin["builtin"] is True
    assert builtin["name"] == "Leek共振指数"
    assert builtin["language"] == "python"
    assert builtin["buy_threshold"] == 88

    definition = {
        "name": "Python 动量",
        "language": "python",
        "code": """import pandas as pd\n\ndef calculate(data: pd.DataFrame) -> pd.Series:\n    return data['close'].pct_change(2) * 100\n""",
        "components": [],
        "buy_threshold": 1,
        "sell_threshold": -1,
    }
    saved = service.save(definition)
    values = service.compute(
        saved, make_daily(date(2020, 1, 1), date(2020, 1, 20))
    )
    assert values[0]["signal"] == "warming_up"
    assert values[1]["signal"] == "warming_up"
    assert values[-1]["value"] is not None


def test_python_indicator_rejects_unapproved_import(tmp_path):
    service = IndicatorService(str(tmp_path))
    with pytest.raises(IndicatorValidationError, match="仅允许导入"):
        service.save({
            "name": "危险代码",
            "language": "python",
            "code": "import os\n\ndef calculate(data):\n    return [0] * len(data)\n",
            "buy_threshold": 1,
            "sell_threshold": -1,
        })
    with pytest.raises(IndicatorValidationError, match="卖出阈值"):
        service.save({
            "name": "阈值错误",
            "components": [{"metric": "momentum", "window": 5, "weight": 1}],
            "buy_threshold": -1,
            "sell_threshold": 1,
        })


def test_daily_session_has_lookback_and_survives_manager_restart(tmp_path, monkeypatch):
    engine = DataEngine(str(tmp_path / "cache"))

    def fetch(_code, start, end, _adjust):
        return make_daily(start, end)

    monkeypatch.setattr(engine, "_fetch_daily_from_eastmoney", fetch)
    game_start = date(2020, 1, 15)
    game_end = date(2020, 1, 31)
    engine.ensure_daily_cache(
        "600519",
        game_start - timedelta(days=GAME_LOOKBACK_DAYS),
        game_end,
    )

    manager = SessionManager(str(tmp_path / "sessions"))
    manager._data_engine = engine
    session = manager.create_session(["600519"], game_start, game_end)
    session.simulator.start_day()

    revealed = session.simulator.daily_data["600519"]
    revealed = revealed[revealed["date"] <= session.simulator.current_date]
    assert len(revealed) > 1
    assert session.simulator.trading_dates[0] >= game_start

    assert session.simulator.next_day() is True
    manager.persist_session(session.session_id)
    expected_date = session.simulator.current_date

    restarted_manager = SessionManager(str(tmp_path / "sessions"))
    restarted_manager._data_engine = engine
    restored = restarted_manager.get_session(session.session_id)
    assert restored is not None
    assert restored.simulator.current_date == expected_date
    assert restored.simulator.date_index == 1

    summaries = restarted_manager.list_session_summaries()
    assert len(summaries) == 1
    assert summaries[0]["session_id"] == session.session_id
    assert summaries[0]["current_date"] == expected_date.isoformat()
    assert summaries[0]["stock_codes"] == ["600519"]
    assert summaries[0]["date_index"] == 1
    assert summaries[0]["total_dates"] == len(restored.simulator.trading_dates)


def test_game_indicator_is_precomputed_once_and_reused(tmp_path, monkeypatch):
    engine = DataEngine(str(tmp_path / "cache"))

    def fetch(_code, start, end, _adjust):
        return make_daily(start, end)

    monkeypatch.setattr(engine, "_fetch_daily_from_eastmoney", fetch)
    game_start = date(2020, 1, 15)
    game_end = date(2020, 2, 28)
    engine.ensure_daily_cache(
        "600519", game_start - timedelta(days=GAME_LOOKBACK_DAYS), game_end
    )

    manager = SessionManager(str(tmp_path / "sessions"))
    manager._data_engine = engine
    session = manager.create_session(
        ["600519"], game_start, game_end, indicator_id=DEFAULT_INDICATOR_ID
    )
    session.simulator.start_day()

    service = IndicatorService(str(tmp_path / "indicators"))
    original_compute = service.compute
    calls: list[str] = []

    def counted_compute(definition, frame):
        calls.append(definition["id"])
        return original_compute(definition, frame)

    monkeypatch.setattr(service, "compute", counted_compute)
    monkeypatch.setattr(game_router, "_indicator_service", service)

    asyncio.run(game_router._ensure_session_indicator_cache(session))
    assert calls == [DEFAULT_INDICATOR_ID]
    assert len(session.indicator_values_by_code["600519"]) > 1

    session.simulator.next_day()
    asyncio.run(game_router._ensure_session_indicator_cache(session))
    assert calls == [DEFAULT_INDICATOR_ID]
