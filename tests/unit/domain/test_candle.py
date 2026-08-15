"""Tests for the Candle entity invariants."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp


def make_candle(
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume: str = "10",
) -> Candle:
    return Candle(
        symbol=Symbol("XAUUSD_i"),
        timeframe=Timeframe("5M"),
        open_time=Timestamp(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        open_price=Price(open_price),
        high=Price(high),
        low=Price(low),
        close=Price(close),
        volume=Decimal(volume),
    )


def test_valid_candle_is_constructed():
    candle = make_candle()
    assert candle.is_bullish is True
    assert candle.range == Decimal("20")


def test_high_below_low_rejected():
    with pytest.raises(ValidationError):
        make_candle(high="80", low="90")


def test_high_below_close_rejected():
    with pytest.raises(ValidationError):
        make_candle(high="100", close="110")


def test_low_above_open_rejected():
    with pytest.raises(ValidationError):
        make_candle(low="101", open_price="100")


def test_negative_volume_rejected():
    with pytest.raises(ValidationError):
        make_candle(volume="-1")


def test_candle_identity_based_equality():
    first = make_candle()
    second = make_candle()
    assert first == first
    assert first != second
