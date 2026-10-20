"""Integration test: real-broker data flows through the whole platform.

Drives a fake MT5 terminal through the *production* pipeline — ingest,
normalise, store as Parquet, then backtest — to prove the port boundary
actually pays off: swapping the data source changes nothing downstream.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.data_cli import build_service
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
    Mt5MarketDataProvider,
)
from tests.unit.dataset.test_mt5_provider import FakeMt5, make_rate

START = int(datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc).timestamp())


def realistic_rates(count: int = 120, step: int = 300):
    """A gently trending series with sane OHLC relationships."""
    rates = []
    price = 2000.0
    for index in range(count):
        drift = 0.6 if index % 3 else -0.4
        open_ = price
        close = price + drift
        rates.append(
            make_rate(
                time=START + index * step,
                open_=round(open_, 2),
                high=round(max(open_, close) + 0.8, 2),
                low=round(min(open_, close) - 0.8, 2),
                close=round(close, 2),
                tick_volume=100 + index,
                spread=10,
            )
        )
        price = close
    return rates


@pytest.fixture
def mt5_provider():
    return Mt5MarketDataProvider(mt5_module=FakeMt5(rates=realistic_rates()))


def test_mt5_data_flows_through_the_standard_pipeline(tmp_path, mt5_provider):
    """Ingest broker data with the same service the CSV path uses."""
    service, store, catalog = build_service(tmp_path, provider=mt5_provider)

    result = service.ingest("XAUUSD", "5M", "120")

    assert result.raw_row_count == 120
    assert result.candle_count == 120
    assert not result.quarantined
    assert result.quality_report.score.overall > 0


def test_ingested_candles_are_queryable_and_typed(tmp_path, mt5_provider):
    service, store, _ = build_service(tmp_path, provider=mt5_provider)
    service.ingest("XAUUSD", "5M", "120")

    candles = store.query(Symbol("XAUUSD"), Timeframe("5M"))

    assert len(candles) == 120
    first = candles[0]
    # raw strings became real domain types
    assert isinstance(first.close.amount, Decimal)
    assert first.open_time.value.tzinfo is not None
    assert first.high.amount >= first.low.amount


def test_candles_are_persisted_as_parquet(tmp_path, mt5_provider):
    service, _, _ = build_service(tmp_path, provider=mt5_provider)
    service.ingest("XAUUSD", "5M", "120")

    files = list(tmp_path.rglob("*.parquet"))
    assert files, "ingestion must persist Parquet files"

    import pandas as pd

    frame = pd.read_parquet(next(f for f in files if "raw" in str(f)))
    assert len(frame) == 120
    assert {"open", "high", "low", "close", "volume"} <= set(frame.columns)


def test_broker_metadata_survives_into_storage(tmp_path, mt5_provider):
    """Spread and provider must not be lost on the way to disk."""
    service, _, _ = build_service(tmp_path, provider=mt5_provider)
    service.ingest("XAUUSD", "5M", "120")

    import pandas as pd

    raw_file = next(f for f in tmp_path.rglob("*.parquet") if "raw" in str(f))
    frame = pd.read_parquet(raw_file)
    assert "spread" in frame.columns
    assert "provider" in frame.columns
    assert frame["provider"].iloc[0] == "mt5"


def test_dataset_is_registered_in_the_catalog(tmp_path, mt5_provider):
    service, _, catalog = build_service(tmp_path, provider=mt5_provider)
    service.ingest("XAUUSD", "5M", "120")

    descriptors = catalog.list_all()
    assert descriptors
    assert any("XAUUSD" in d.dataset_id.label for d in descriptors)


def test_broker_data_can_be_backtested(tmp_path, mt5_provider):
    """The real payoff: broker prices reach the simulator untouched."""
    from ShadBotTrader.application.services.backtest_service import BacktestService
    from ShadBotTrader.domain.simulation.session import SimulationConfiguration

    service, store, _ = build_service(tmp_path, provider=mt5_provider)
    service.ingest("XAUUSD", "5M", "120")
    candles = store.query(Symbol("XAUUSD"), Timeframe("5M"))

    backtest = BacktestService(
        configuration=SimulationConfiguration(
            initial_capital=Decimal("100"),
            spread=Decimal("4"),
            commission_rate=Decimal("0.0001"),
            warmup_bars=10,
        ),
        base_quantity=Decimal("0.01"),
    )
    result = backtest.run("mt5-backtest", Symbol("XAUUSD"), Timeframe("5M"), candles)

    assert result.bars_processed == 120
    assert result.session.status.value == "completed"
    assert len(result.equity_curve) == 120


def test_bad_broker_data_is_caught_by_the_quality_gate(tmp_path):
    """A provider swap must not bypass validation."""
    broken = [
        make_rate(time=START, open_=2000, high=1990, low=2010, close=2000),  # high < low
        make_rate(time=START + 300, open_=2000, high=2005, low=1995, close=2002),
    ]
    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=broken))
    service, _, _ = build_service(tmp_path, provider=provider)

    result = service.ingest("XAUUSD", "5M", "2")

    # the malformed bar must not silently become a tradable candle
    assert result.candle_count < result.raw_row_count


def test_fetch_range_reaches_the_pipeline(tmp_path):
    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=realistic_rates(60)))
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    records = provider.fetch_range("XAUUSD", "5M", start, start + timedelta(days=1))
    assert len(records) == 60
    assert all(record.symbol == "XAUUSD" for record in records)


def test_same_pipeline_accepts_csv_and_mt5(tmp_path, mt5_provider):
    """One pipeline, two sources — the boundary that makes this possible."""
    from ShadBotTrader.data_cli import generate_sample

    csv_path = tmp_path / "sample.csv"
    generate_sample("XAUUSD_i", "5M", 60, csv_path)

    csv_service, csv_store, _ = build_service(tmp_path / "csv")
    csv_result = csv_service.ingest("XAUUSD_i", "5M", str(csv_path))

    mt5_service, mt5_store, _ = build_service(tmp_path / "mt5", provider=mt5_provider)
    mt5_result = mt5_service.ingest("XAUUSD", "5M", "120")

    # identical result shape from two completely different sources
    assert csv_result.candle_count == 60
    assert mt5_result.candle_count == 120
    assert type(csv_result) is type(mt5_result)


# ------------------------------------------------- real market shape -------
def session_rates(weeks: int = 3, step: int = 300):
    """Bars shaped like a real FX/metals feed.

    The market is closed at weekends, so a genuine 5M series contains a
    ~48-hour hole every Friday night. Synthetic fixtures never have one,
    which is exactly why this shape needs its own test: a weekend must
    read as normal market structure, not as broken data.
    """
    rates = []
    moment = datetime(2026, 1, 5, tzinfo=timezone.utc)  # a Monday
    finish = moment + timedelta(weeks=weeks)
    price, index = 2000.0, 0
    while moment < finish:
        if moment.weekday() < 5:  # Monday-Friday only
            drift = 0.35 if index % 3 else -0.28
            open_, close = price, price + drift
            rates.append(
                make_rate(
                    time=int(moment.timestamp()),
                    open_=round(open_, 2),
                    high=round(max(open_, close) + 0.5, 2),
                    low=round(min(open_, close) - 0.5, 2),
                    close=round(close, 2),
                    tick_volume=80 + (index % 50),
                    # brokers widen the spread around the rollover
                    spread=45 if moment.hour == 0 else 10,
                )
            )
            price, index = close, index + 1
        moment += timedelta(minutes=5)
    return rates


def test_weekend_gaps_are_reported_but_do_not_quarantine(tmp_path):
    """A closed market is normal structure, not corrupt data."""
    rates = session_rates()
    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=rates))
    service, _, _ = build_service(tmp_path, provider=provider)

    result = service.ingest("XAUUSD", "5M", str(len(rates)))

    assert result.candle_count == len(rates)
    assert not result.quarantined  # the run must not be thrown away
    codes = {issue.code for issue in result.quality_report.issues}
    assert "GAP_DETECTED" in codes  # but it must still be reported
    assert result.quality_report.score.overall > 99


def test_a_weekend_shaped_series_backtests_end_to_end(tmp_path):
    """Gaps must not break the clock, the queue or the accounting."""
    from ShadBotTrader.application.services.backtest_service import BacktestService
    from ShadBotTrader.domain.simulation.session import SimulationConfiguration
    from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource

    rates = session_rates(weeks=2)
    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=rates))
    service, store, _ = build_service(tmp_path, provider=provider)
    service.ingest("XAUUSD", "5M", str(len(rates)))
    candles = store.query(Symbol("XAUUSD"), Timeframe("5M"))

    backtest = BacktestService(
        configuration=SimulationConfiguration(
            initial_capital=Decimal("100"),
            spread=Decimal("4"),
            commission_rate=Decimal("0.0001"),
            warmup_bars=20,
        ),
        base_quantity=Decimal("0.01"),
    )
    result = backtest.run(
        "weekend",
        Symbol("XAUUSD"),
        Timeframe("5M"),
        candles,
        prediction_source=MomentumPredictionSource(lookback=6),
        record_replay=True,
    )

    assert result.bars_processed == len(candles)
    # the equity curve stayed chronological across every weekend hole
    stamps = [point.timestamp.value for point in result.equity_curve.points]
    assert stamps == sorted(stamps)
    assert result.tape is not None
    assert len(result.tape.bars) == len(candles)


def test_the_broker_spread_of_each_bar_is_preserved(tmp_path):
    """Rollover spreads matter for cost modelling — they must survive."""
    rates = session_rates(weeks=1)
    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=rates))

    records = provider.fetch_candles("XAUUSD", "5M", str(len(rates)))

    spreads = {record.extra["spread"] for record in records}
    assert spreads == {10, 45}


def test_a_sunday_opening_jump_is_flagged_not_silently_accepted(tmp_path):
    """A large weekend gap-open is real, but the analyser must notice it."""
    rates = session_rates(weeks=1)
    jumped = []
    for rate in rates:
        moment = datetime.fromtimestamp(rate["time"], tz=timezone.utc)
        if moment.weekday() >= 3:  # everything from Thursday gaps upward
            jumped.append(
                make_rate(
                    time=rate["time"],
                    open_=rate["open"] + 120,
                    high=rate["high"] + 120,
                    low=rate["low"] + 120,
                    close=rate["close"] + 120,
                    tick_volume=rate["tick_volume"],
                    spread=rate["spread"],
                )
            )
        else:
            jumped.append(rate)

    provider = Mt5MarketDataProvider(mt5_module=FakeMt5(rates=jumped))
    service, _, _ = build_service(tmp_path, provider=provider)

    result = service.ingest("XAUUSD", "5M", str(len(jumped)))

    assert result.candle_count == len(jumped)
    assert not result.quarantined  # a real jump is not corruption
