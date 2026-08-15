"""Tests for the core market value objects."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe, TimeframeUnit
from ShadBotTrader.domain.market.timestamp import Timestamp


def test_symbol_equality_ignores_surrounding_whitespace():
    assert Symbol("XAUUSD_i") == Symbol("  XAUUSD_i ")
    assert Symbol("XAUUSD_i") != Symbol("EURUSD_i")


def test_symbol_rejects_empty():
    with pytest.raises(ValidationError):
        Symbol("   ")


def test_symbol_rejects_internal_whitespace():
    with pytest.raises(ValidationError):
        Symbol("XAU USD")


def test_timeframe_parsing():
    timeframe = Timeframe("5M")
    assert timeframe.amount == 5
    assert timeframe.unit is TimeframeUnit.MINUTE
    assert timeframe.label == "5M"


def test_timeframe_rejects_unknown_suffix():
    with pytest.raises(ValidationError):
        Timeframe("5X")


def test_timeframe_rejects_non_numeric_amount():
    with pytest.raises(ValidationError):
        Timeframe("XM")


def test_price_uses_decimal_semantics():
    assert Price("1.2345").amount == Decimal("1.2345")
    assert Price(1.5) == Price("1.5")


def test_price_rejects_non_positive():
    with pytest.raises(ValidationError):
        Price(-1)
    with pytest.raises(ValidationError):
        Price(0)


def test_timestamp_requires_timezone():
    with pytest.raises(ValidationError):
        Timestamp(datetime(2026, 1, 1))
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert Timestamp(aware).value == aware
