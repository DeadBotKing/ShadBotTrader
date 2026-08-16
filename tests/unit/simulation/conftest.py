"""Pytest fixtures for the simulation unit tests."""

import pytest

from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from tests.simulation_fixtures import (  # noqa: F401
    BASE_TIME,
    TF,
    XAU,
    candles_from,
    falling,
    flat_series,
    make_candle,
    rising,
    ts,
)


@pytest.fixture
def symbol() -> Symbol:
    return XAU


@pytest.fixture
def timeframe() -> Timeframe:
    return TF
