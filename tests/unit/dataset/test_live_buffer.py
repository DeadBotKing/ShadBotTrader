"""Tests for the rolling live-market buffer (Phase 30 §5).

The buffer is fed by a five-minute loop talking to a broker, so the
interesting cases are all the ways real feeds misbehave: the same bar
arriving repeatedly while it is still forming, bars arriving late, and
the buffer quietly running short of the 500 rows the models need.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.data.live_buffer import (
    DEFAULT_CAPACITY,
    REQUIRED_WINDOW,
    LiveMarketData,
    RollingCandleBuffer,
)

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("5M")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def candle(index: int, close: float = 2000.0) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=TF,
        open_time=Timestamp(BASE + timedelta(minutes=5 * index)),
        open_price=Price(Decimal(str(close))),
        high=Price(Decimal(str(close + 1))),
        low=Price(Decimal(str(close - 1))),
        close=Price(Decimal(str(close))),
        volume=Decimal("100"),
    )


class TestCapacity:
    def test_the_default_capacity_is_the_eight_hundred_requested(self):
        assert DEFAULT_CAPACITY == 800
        assert REQUIRED_WINDOW == 500

    def test_a_capacity_below_the_model_window_is_refused(self):
        """400 candles could never produce a 500-row input."""
        with pytest.raises(ValidationError):
            RollingCandleBuffer("5M", capacity=400)

    def test_the_buffer_never_grows_past_its_capacity(self):
        buffer = RollingCandleBuffer("5M", capacity=800)
        buffer.extend(candle(index) for index in range(1200))

        assert buffer.size == 800

    def test_the_oldest_candles_are_the_ones_evicted(self):
        buffer = RollingCandleBuffer("5M", capacity=800)
        buffer.extend(candle(index) for index in range(1000))

        assert buffer.oldest is not None and buffer.newest is not None
        assert buffer.oldest.open_time.value == BASE + timedelta(minutes=5 * 200)
        assert buffer.newest.open_time.value == BASE + timedelta(minutes=5 * 999)


class TestUpdateSemantics:
    def test_a_new_candle_is_appended(self):
        buffer = RollingCandleBuffer("5M")
        assert buffer.push(candle(0)) == "appended"
        assert buffer.push(candle(1)) == "appended"
        assert buffer.size == 2

    def test_the_same_timestamp_replaces_rather_than_duplicates(self):
        """The live 1H bar is re-fetched many times before it closes.

        Appending it each time would fabricate hours of history.
        """
        buffer = RollingCandleBuffer("5M")
        buffer.push(candle(0, close=2000.0))

        for price in (2001.0, 2002.0, 2003.0):
            assert buffer.push(candle(0, close=price)) == "replaced"

        assert buffer.size == 1
        assert buffer.newest is not None
        assert float(buffer.newest.close.amount) == 2003.0

    def test_a_late_candle_for_a_known_slot_updates_it(self):
        buffer = RollingCandleBuffer("5M")
        buffer.extend(candle(index) for index in range(5))

        assert buffer.push(candle(2, close=2222.0)) == "replaced"
        assert buffer.size == 5
        assert float(buffer.candles[2].close.amount) == 2222.0

    def test_an_unknown_old_candle_is_rejected_not_inserted(self):
        """Out-of-order data must not corrupt the ordering."""
        buffer = RollingCandleBuffer("5M")
        buffer.extend(candle(index) for index in range(100, 105))

        assert buffer.push(candle(1)) == "rejected"
        assert buffer.size == 5

    def test_the_series_stays_chronological(self):
        buffer = RollingCandleBuffer("5M")
        buffer.extend(candle(index) for index in reversed(range(50)))

        stamps = [item.open_time.value for item in buffer.candles]
        assert stamps == sorted(stamps)

    def test_the_state_counts_every_outcome(self):
        buffer = RollingCandleBuffer("5M")
        buffer.extend(candle(index) for index in range(10))
        buffer.push(candle(9, close=2050.0))
        buffer.push(candle(-5))

        state = buffer.state()
        assert state.accepted == 10
        assert state.replaced == 1
        assert state.rejected == 1


class TestWindowReadiness:
    def test_a_full_buffer_supports_the_window_after_warmup(self):
        buffer = RollingCandleBuffer("5M", capacity=800)
        buffer.extend(candle(index) for index in range(800))

        assert buffer.has_enough_for_window(warmup=51)
        assert buffer.shortfall(warmup=51) == 0
        assert buffer.explain_shortfall(warmup=51) == ""

    def test_a_long_warmup_is_reported_with_a_remedy(self):
        """Silently emitting a short window would feed the model garbage."""
        buffer = RollingCandleBuffer("5M", capacity=800)
        buffer.extend(candle(index) for index in range(800))

        assert not buffer.has_enough_for_window(warmup=400)
        assert buffer.shortfall(warmup=400) == 100
        message = buffer.explain_shortfall(warmup=400)
        assert "900" in message  # 500 + 400
        assert "Short by 100" in message

    def test_a_partly_filled_buffer_is_not_ready(self):
        buffer = RollingCandleBuffer("5M")
        buffer.extend(candle(index) for index in range(300))

        assert not buffer.has_enough_for_window(warmup=51)


class TestLiveMarketData:
    def test_both_timeframes_are_tracked_separately(self):
        live = LiveMarketData(timeframes=("5M", "1H"))
        live.prime("5M", [candle(index) for index in range(600)])
        live.prime("1H", [candle(index) for index in range(700)])

        assert live.buffer("5M").size == 600
        assert live.buffer("1H").size == 700

    def test_readiness_requires_every_timeframe(self):
        live = LiveMarketData(timeframes=("5M", "1H"))
        live.prime("5M", [candle(index) for index in range(800)])
        live.prime("1H", [candle(index) for index in range(100)])

        assert not live.ready(warmup=51)
        reasons = live.blocking_reasons(warmup=51)
        assert len(reasons) == 1
        assert "1H" in reasons[0]

    def test_both_ready_produces_no_blocking_reasons(self):
        live = LiveMarketData(timeframes=("5M", "1H"))
        for timeframe in ("5M", "1H"):
            live.prime(timeframe, [candle(index) for index in range(800)])

        assert live.ready(warmup=51)
        assert live.blocking_reasons(warmup=51) == []

    def test_an_unknown_timeframe_fails_loudly(self):
        live = LiveMarketData(timeframes=("5M",))
        with pytest.raises(ValidationError):
            live.buffer("4H")
