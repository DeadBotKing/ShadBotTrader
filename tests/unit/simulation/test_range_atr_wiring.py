"""فاز ۹۵ — ATR wiring in the backtest source and the model record.

The backtest source must hand the predictor the ATR of the latest closed
range candle (causal, memoized per range bar), and the saved record must
carry ``target_units`` so the next session rebuilds the exact question.
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
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelRecord
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("1H")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def candle(index: int, close: float, high: float | None = None, low: float | None = None):
    high = close + 1 if high is None else high
    low = close - 1 if low is None else low
    return Candle(
        symbol=SYMBOL,
        timeframe=TF,
        open_time=Timestamp(BASE + timedelta(hours=index)),
        open_price=Price(Decimal(str(close))),
        high=Price(Decimal(str(high))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(close))),
        volume=Decimal("100"),
    )


class _FakeRangePredictor:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def forecast(self, artifact, window, reference_close, generated_at="", atr_reference=None):
        self.calls.append(
            {
                "reference_close": reference_close,
                "atr_reference": atr_reference,
            }
        )
        from ShadBotTrader.domain.ai.prediction_target import RangeForecast

        return RangeForecast(
            reference_close=reference_close,
            high_offset=0.001,
            low_offset=-0.001,
            horizon=1,
            timeframe="1H",
        )


class _ActionableSignalPredictor:
    """Always answers BUY with 0.9 confidence so the range model runs."""

    def forecast(self, artifact, window, generated_at=""):
        from ShadBotTrader.domain.ai.prediction_target import SignalForecast

        return SignalForecast.from_vector((0.1, 0.9), horizon=1, timeframe="1H")


class _StubMatrix:
    """Minimal stand-in for a precomputed feature matrix."""

    def __init__(self, rows: int) -> None:
        self.rows = [[0.0] * 3 for _ in range(rows)]
        self.source_index = list(range(rows))


def _make_source(range_candles, units):
    rows = max(len(range_candles), 4)
    return DualModelPredictionSource(
        signal_artifact=None,
        signal_predictor=_ActionableSignalPredictor(),
        range_artifact=object(),
        range_predictor=_FakeRangePredictor(),
        symbol=SYMBOL,
        signal_timeframe=Timeframe("1H"),
        range_timeframe=TF,
        range_candles=range_candles,
        signal_window_size=2,
        range_window_size=2,
        signal_matrix=_StubMatrix(rows),
        range_matrix=_StubMatrix(rows),
        signal_candles=range_candles,
        range_target_units=units,
    )


def _event(c: Candle) -> MarketEvent:
    return MarketEvent.from_candle(SYMBOL, c)


class TestRangeTargetUnitsWiring:
    def test_atr_source_passes_causal_atr_reference(self):
        candles = [candle(index, 2000.0 + index * 2.0) for index in range(30)]
        source = _make_source(candles, "atr")
        # feed every candle, then predict at the last one
        for item in candles:
            source.observe(_event(item))
        source.predict(_event(candles[-1]))
        assert len(source._range_predictor.calls) == 1
        call = source._range_predictor.calls[0]
        assert call["atr_reference"] is not None
        assert call["atr_reference"] > 0

        from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

        assert call["atr_reference"] == pytest.approx(atr_from_candles(candles, period=14))

    def test_pct_source_passes_none_and_stays_legacy(self):
        candles = [candle(index, 2000.0 + index) for index in range(20)]
        source = _make_source(candles, "pct")
        for item in candles:
            source.observe(_event(item))
        source.predict(_event(candles[-1]))
        assert source._range_predictor.calls[0]["atr_reference"] is None

    def test_atr_reference_is_memoized_per_range_bar(self):
        candles = [candle(index, 2000.0 + index) for index in range(20)]
        source = _make_source(candles, "atr")
        for item in candles:
            source.observe(_event(item))
        source.predict(_event(candles[-1]))
        source.predict(_event(candles[-1]))
        assert len(source._range_predictor.calls) == 2
        assert (
            source._range_predictor.calls[0]["atr_reference"]
            == source._range_predictor.calls[1]["atr_reference"]
        )

    def test_unknown_units_are_refused(self):
        with pytest.raises(ValidationError):
            _make_source([], "pips")


class TestModelRecordUnits:
    def test_roundtrip_keeps_target_units(self):
        record = ModelRecord(
            model_id="gold_range_1h",
            role="range",
            symbol="XAUUSD",
            timeframe="1H",
            horizon=12,
            target_units="atr",
        )
        payload = record.to_dict()
        assert payload["target_units"] == "atr"
        restored = ModelRecord.from_dict(payload)
        assert restored.target_units == "atr"

    def test_old_records_without_the_field_default_to_pct(self):
        legacy = ModelRecord.from_dict(
            {
                "model_id": "gold_range_1d",
                "role": "range",
                "symbol": "XAUUSD",
                "timeframe": "1D",
            }
        )
        assert legacy.target_units == "pct"
