"""Phase 116 hybrid range-aware strategy tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.ai.prediction_target import HybridHeadForecast, RangeForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.strategy.strategy_types import SignalType, StrategyState
from ShadBotTrader.infrastructure.trading.hybrid_range_aware_strategy import (
    HYBRID_HEAD_FORECAST_KEY,
    RANGE_1D_FORECAST_KEY,
    RANGE_4H_FORECAST_KEY,
    RAW_ENTRY_PRICE_KEY,
    ROOM_REFERENCE_PRICE_KEY,
    HybridRangeAwareConfig,
    HybridRangeAwareStrategy,
)

MOMENT = Timestamp(datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc))


def hybrid(sell=0.05, hold=0.10, buy=0.85) -> HybridHeadForecast:
    return HybridHeadForecast.from_vector((sell, hold, buy), horizon=288, timeframe="5M")


def range_forecast(high: float, low: float, close: float = 2000.0, timeframe: str = "4H"):
    return RangeForecast(
        reference_close=close,
        high_offset=high / close - 1.0,
        low_offset=low / close - 1.0,
        horizon=1,
        timeframe=timeframe,
    )


def context(
    forecast=None,
    range_1d=None,
    range_4h=None,
    raw_entry: float = 2000.0,
    room_reference: float = 2000.0,
) -> StrategyContext:
    if forecast is None:
        forecast = hybrid()
    if range_1d is None:
        range_1d = range_forecast(2020.0, 1980.0, timeframe="1D")
    if range_4h is None:
        range_4h = range_forecast(2010.0, 1990.0, timeframe="4H")
    return StrategyContext(
        timestamp=MOMENT,
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe("5M"),
        predictions=[
            PredictionView(
                model_id="gold_hybrid_lightgbm_head_5m",
                model_version=1,
                value=forecast.buy_probability - forecast.sell_probability,
                confidence=forecast.confidence,
                generated_at=MOMENT,
                metadata={
                    HYBRID_HEAD_FORECAST_KEY: forecast,
                    RANGE_1D_FORECAST_KEY: range_1d,
                    RANGE_4H_FORECAST_KEY: range_4h,
                },
            )
        ],
        portfolio=PortfolioView(equity=Decimal("10000")),
        metadata={
            RAW_ENTRY_PRICE_KEY: raw_entry,
            ROOM_REFERENCE_PRICE_KEY: room_reference,
        },
    )


@pytest.fixture
def strategy():
    return HybridRangeAwareStrategy(
        HybridRangeAwareConfig(
            buy_threshold=0.80,
            sell_threshold=0.65,
            min_margin=0.05,
            min_4h_room=2.0,
            min_1d_room=5.0,
            min_tp_distance=2.0,
            min_sl_distance=2.0,
            spread_mode="fixed",
            spread_value=0.0,
        )
    )


def test_confident_buy_builds_phase125_bracket(strategy):
    signal = strategy.evaluate(context(hybrid(sell=0.05, hold=0.10, buy=0.85)))

    assert signal.signal_type is SignalType.BUY
    assert signal.context["take_profit"] == pytest.approx(2010.0)
    assert signal.context["stop_loss"] == pytest.approx(1990.0)
    assert signal.context["tp_distance"] == pytest.approx(10.0)
    assert signal.context["sl_distance"] == pytest.approx(10.0)
    assert signal.context["trade_bracket"]["side"] == "buy"


def test_confident_sell_builds_phase125_bracket(strategy):
    signal = strategy.evaluate(
        context(
            hybrid(sell=0.70, hold=0.20, buy=0.10),
            range_1d=range_forecast(2020.0, 1980.0, timeframe="1D"),
            range_4h=range_forecast(2010.0, 1990.0, timeframe="4H"),
        )
    )

    assert signal.signal_type is SignalType.SELL
    assert signal.context["take_profit"] == pytest.approx(1990.0)
    assert signal.context["stop_loss"] == pytest.approx(2010.0)
    assert signal.context["trade_bracket"]["side"] == "sell"


def test_hold_probability_blocks_trade_even_when_buy_is_above_threshold(strategy):
    signal = strategy.evaluate(context(hybrid(sell=0.05, hold=0.83, buy=0.82)))

    assert signal.signal_type is SignalType.HOLD
    assert "below gate" in signal.reason


def test_range_room_gate_blocks_trade(strategy):
    signal = strategy.evaluate(
        context(
            hybrid(sell=0.05, hold=0.10, buy=0.85),
            range_4h=range_forecast(2001.0, 1990.0, timeframe="4H"),
        )
    )

    assert signal.signal_type is SignalType.HOLD
    assert "4H BUY room" in signal.reason


def test_minimum_sl_distance_blocks_tight_stop(strategy):
    signal = strategy.evaluate(
        context(
            hybrid(sell=0.05, hold=0.10, buy=0.85),
            range_4h=range_forecast(2010.0, 1999.0, timeframe="4H"),
        )
    )

    assert signal.signal_type is SignalType.HOLD
    assert "SL distance" in signal.reason


def test_missing_1d_range_blocks_trade(strategy):
    signal = strategy.evaluate(context(hybrid(), range_1d="missing"))

    assert signal.signal_type is SignalType.HOLD
    assert "no 1D range" in signal.reason


def test_disabled_strategy_emits_nothing():
    strategy = HybridRangeAwareStrategy(state=StrategyState.DISABLED)

    assert strategy.evaluate(context()) is None


def test_invalid_config_is_rejected():
    with pytest.raises(ValidationError):
        HybridRangeAwareConfig(buy_threshold=1.5)
    with pytest.raises(ValidationError):
        HybridRangeAwareConfig(spread_mode="unknown")
