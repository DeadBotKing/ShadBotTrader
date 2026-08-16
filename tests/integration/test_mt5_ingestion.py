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
