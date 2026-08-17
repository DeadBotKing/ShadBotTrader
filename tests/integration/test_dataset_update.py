"""Incremental dataset updates end to end (Phase 33).

Regression suite for a real defect: ``Fetch market data`` wrote a new
version and read only the latest, so a second fetch REPLACED the stored
history. Two hundred candles plus fifty new ones left fifty.

These tests pin down the behaviour the operator expects: append, cap,
and refuse to join across a hole that never existed in the market.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.dataset_update_service import (
    DatasetUpdateService,
    describe_freshness,
)
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

SYMBOL = "XAUUSD"
DAILY = Timeframe("1D")
START = datetime(2024, 5, 1, tzinfo=timezone.utc)


def weekdays(start: datetime, count: int):
    out = []
    cursor = start
    price = 2000.0
    while len(out) < count:
        if cursor.weekday() < 5:
            out.append(
                Candle(
                    symbol=Symbol(SYMBOL),
                    timeframe=DAILY,
                    open_time=Timestamp(cursor),
                    open_price=Price(Decimal(str(price))),
                    high=Price(Decimal(str(price + 5))),
                    low=Price(Decimal(str(price - 5))),
                    close=Price(Decimal(str(price + 1))),
                    volume=Decimal("100"),
                )
            )
            price += 1
        cursor += timedelta(days=1)
    return out


def next_trading_day(moment: datetime) -> datetime:
    cursor = moment + timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor += timedelta(days=1)
    return cursor


class HelpfulBroker:
    """A broker that can serve any historical range."""

    provider_name = "mt5"

    def __init__(self) -> None:
        self.range_calls: list[tuple] = []

    def fetch_range(self, symbol, timeframe, start, end):
        self.range_calls.append((start, end))
        records = []
        cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
        price = 2500.0
        while cursor < end:
            if cursor.weekday() < 5:
                records.append(
                    RawCandleRecord(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=cursor.isoformat(),
                        open=str(price),
                        high=str(price + 5),
                        low=str(price - 5),
                        close=str(price + 1),
                        volume="100",
                        extra={},
                    )
                )
                price += 1
            cursor += timedelta(days=1)
        return records


class EmptyBroker:
    """A broker with no history for the requested range."""

    provider_name = "mt5"

    def fetch_range(self, symbol, timeframe, start, end):
        return []


@pytest.fixture
def service(tmp_path):
    return DatasetUpdateService(ParquetCandleStore(tmp_path), max_candles=60)


# ------------------------------------------------------------ appending ---
class TestAppend:
    def test_the_first_update_stores_everything(self, service):
        result = service.update(SYMBOL, "1D", weekdays(START, 40))

        assert result.succeeded
        assert result.final_count == 40
        assert result.added_count == 40

    def test_a_second_update_extends_rather_than_replaces(self, service):
        """The exact defect: 200 stored + 50 new used to leave 50."""
        first = weekdays(START, 40)
        service.update(SYMBOL, "1D", first)

        following = weekdays(next_trading_day(first[-1].open_time.value), 10)
        result = service.update(SYMBOL, "1D", following)

        assert result.existing_count == 40
        assert result.added_count == 10
        assert result.final_count == 50
        assert len(service.stored(SYMBOL, "1D")) == 50

    def test_re_sending_the_same_candles_adds_nothing(self, service):
        candles = weekdays(START, 20)
        service.update(SYMBOL, "1D", candles)

        result = service.update(SYMBOL, "1D", candles)

        assert result.added_count == 0
        assert result.replaced_count == 20
        assert result.final_count == 20

    def test_a_re_fetched_bar_is_corrected_not_duplicated(self, service):
        candles = weekdays(START, 10)
        service.update(SYMBOL, "1D", candles)

        moment = candles[-1].open_time.value
        corrected = Candle(
            symbol=Symbol(SYMBOL),
            timeframe=DAILY,
            open_time=Timestamp(moment),
            open_price=Price(Decimal("9999")),
            high=Price(Decimal("10005")),
            low=Price(Decimal("9995")),
            close=Price(Decimal("10000")),
            volume=Decimal("500"),
        )
        service.update(SYMBOL, "1D", [corrected])

        stored = service.stored(SYMBOL, "1D")
        assert len(stored) == 10
        assert float(stored[-1].open.amount) == 9999.0

    def test_an_empty_fetch_is_refused(self, service):
        result = service.update(SYMBOL, "1D", [])

        assert result.refused
        assert "no candles" in result.reason


# --------------------------------------------------------- rolling limit ---
class TestRollingLimit:
    def test_the_oldest_candles_are_dropped_past_the_cap(self, service):
        first = weekdays(START, 50)
        service.update(SYMBOL, "1D", first)

        following = weekdays(next_trading_day(first[-1].open_time.value), 20)
        result = service.update(SYMBOL, "1D", following)

        assert result.final_count == 60  # the configured cap
        assert result.dropped_count == 10

    def test_the_newest_candles_are_the_ones_kept(self, service):
        first = weekdays(START, 50)
        service.update(SYMBOL, "1D", first)
        following = weekdays(next_trading_day(first[-1].open_time.value), 20)
        service.update(SYMBOL, "1D", following)

        stored = service.stored(SYMBOL, "1D")

        assert stored[-1].open_time.value == following[-1].open_time.value

    def test_the_history_stays_ordered_after_trimming(self, service):
        first = weekdays(START, 50)
        service.update(SYMBOL, "1D", first)
        service.update(SYMBOL, "1D", weekdays(next_trading_day(first[-1].open_time.value), 30))

        stamps = [c.open_time.value for c in service.stored(SYMBOL, "1D")]

        assert stamps == sorted(stamps)
        assert len(set(stamps)) == len(stamps)


# ---------------------------------------------------------------- gaps ---
class TestGapHandling:
    def test_a_clean_join_is_accepted(self, service):
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        result = service.update(
            SYMBOL, "1D", weekdays(next_trading_day(first[-1].open_time.value), 10)
        )

        assert result.succeeded
        assert result.gap is None

    def test_a_weekend_between_updates_is_not_a_gap(self, service):
        """Friday then Monday must join without complaint."""
        first = weekdays(START, 30)
        last = first[-1].open_time.value
        while last.weekday() != 4:  # end on a Friday
            first = weekdays(START, len(first) + 1)
            last = first[-1].open_time.value
        service.update(SYMBOL, "1D", first)

        monday = last + timedelta(days=3)
        result = service.update(SYMBOL, "1D", weekdays(monday, 5))

        assert result.succeeded
        assert result.gap is None

    def test_a_month_long_hole_is_refused(self, service):
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        result = service.update(
            SYMBOL, "1D", weekdays(first[-1].open_time.value + timedelta(days=30), 10)
        )

        assert result.refused
        assert result.gap is not None
        assert "missing" in result.reason

    def test_a_refused_update_leaves_the_dataset_untouched(self, service):
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)
        before = [c.open_time.value for c in service.stored(SYMBOL, "1D")]

        service.update(SYMBOL, "1D", weekdays(first[-1].open_time.value + timedelta(days=30), 10))

        assert [c.open_time.value for c in service.stored(SYMBOL, "1D")] == before

    def test_a_gap_can_be_accepted_deliberately(self, service):
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        result = service.update(
            SYMBOL,
            "1D",
            weekdays(first[-1].open_time.value + timedelta(days=30), 10),
            allow_gap=True,
        )

        assert result.succeeded
        assert result.final_count == 40


class TestBackfill:
    def test_a_gap_is_repaired_from_the_broker(self, tmp_path):
        broker = HelpfulBroker()
        service = DatasetUpdateService(
            ParquetCandleStore(tmp_path), provider=broker, max_candles=500
        )
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        result = service.update(
            SYMBOL, "1D", weekdays(first[-1].open_time.value + timedelta(days=30), 10)
        )

        assert result.succeeded
        assert result.backfilled_count > 0
        assert result.gap_resolved
        assert result.continuity is not None and result.continuity.is_continuous

    def test_the_broker_is_asked_for_exactly_the_missing_range(self, tmp_path):
        broker = HelpfulBroker()
        service = DatasetUpdateService(
            ParquetCandleStore(tmp_path), provider=broker, max_candles=500
        )
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)
        following = weekdays(first[-1].open_time.value + timedelta(days=30), 10)

        service.update(SYMBOL, "1D", following)

        assert len(broker.range_calls) == 1
        start, end = broker.range_calls[0]
        assert start > first[-1].open_time.value
        assert end <= following[0].open_time.value

    def test_a_broker_without_the_history_still_refuses(self, tmp_path):
        """Backfill is best-effort; it must not turn into acceptance."""
        service = DatasetUpdateService(
            ParquetCandleStore(tmp_path), provider=EmptyBroker(), max_candles=500
        )
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        result = service.update(
            SYMBOL, "1D", weekdays(first[-1].open_time.value + timedelta(days=30), 10)
        )

        assert result.refused
        assert result.backfilled_count == 0

    def test_backfill_can_be_switched_off(self, tmp_path):
        broker = HelpfulBroker()
        service = DatasetUpdateService(
            ParquetCandleStore(tmp_path), provider=broker, max_candles=500
        )
        first = weekdays(START, 30)
        service.update(SYMBOL, "1D", first)

        service.update(
            SYMBOL,
            "1D",
            weekdays(first[-1].open_time.value + timedelta(days=30), 10),
            backfill=False,
        )

        assert broker.range_calls == []


# ------------------------------------------------------------ inspection ---
class TestInspection:
    def test_a_stored_history_can_be_checked(self, service):
        service.update(SYMBOL, "1D", weekdays(START, 30))

        report = service.inspect(SYMBOL, "1D")

        assert report.is_continuous
        assert report.candle_count == 30

    def test_freshness_reports_how_far_behind_the_data_is(self):
        stale = datetime.now(timezone.utc) - timedelta(days=10)

        freshness = describe_freshness(stale, "1D")

        assert freshness["known"]
        assert freshness["stale"]
        assert freshness["candles_behind"] >= 9

    def test_recent_data_is_not_stale(self):
        recent = datetime.now(timezone.utc) - timedelta(minutes=4)

        assert not describe_freshness(recent, "5M")["stale"]

    def test_an_unknown_last_candle_is_reported_as_unknown(self):
        assert describe_freshness(None, "1D") == {"known": False}
