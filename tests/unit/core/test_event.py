"""Tests for the Event value type."""

import pytest

from ShadBotTrader.core.errors import EventError
from ShadBotTrader.core.events.event import Event


def test_event_requires_non_empty_type():
    with pytest.raises(EventError):
        Event(event_type="   ")


def test_event_ids_are_unique():
    assert Event("MarketDataReceived").event_id != Event("MarketDataReceived").event_id


def test_event_payload_is_read_only():
    event = Event("MarketDataReceived", payload={"symbol": "XAUUSD_i"})
    assert event.payload["symbol"] == "XAUUSD_i"
    with pytest.raises(TypeError):
        event.payload["symbol"] = "EURUSD_i"  # type: ignore[index]


def test_event_defaults():
    event = Event("CandleClosed")
    assert dict(event.payload) == {}
    assert event.source == ""
    assert event.correlation_id == ""
