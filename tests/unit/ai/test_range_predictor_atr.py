"""فاز ۹۵ — RangePredictor ATR de-normalization + RangeForecast prices.

An ATR-unit model outputs ATR multiples. The predictor turns them into
prices once — ``price = close + mult × ATR(reference candle)`` — and the
fraction fields stay synced so every legacy percent display remains
honest. A missing ATR must be a hard error, never a silently wrong price.
"""

from typing import Any

import numpy as np
import pytest

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.prediction_target import RangeForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai import dual_predictor


def fake_artifact() -> ModelArtifact:
    return ModelArtifact.create(
        model_id=ModelId("gold_range_1h"),
        version=ModelVersion(1),
        framework="test",
        framework_version="0",
        format="bin",
        payload=b"fake-range-model",
    )


class FakeSeq2SeqModel:
    """Emits a fixed [window, horizon*2] output like the real range head."""

    input_shape = [None, 5, 3]

    def __init__(self, last_step: Any) -> None:
        self._last_step = np.array(last_step, dtype=np.float32)

    def predict(self, x: Any, verbose: int = 0) -> Any:
        window = x.shape[1]
        return np.stack([np.repeat(self._last_step[None, :], window, axis=0)])[0:1]


@pytest.fixture()
def patched_load(monkeypatch: pytest.MonkeyPatch):
    def _install(model: FakeSeq2SeqModel) -> None:
        monkeypatch.setattr(dual_predictor, "_load", lambda artifact: model)

    return _install


def raw_window() -> Any:
    return [[0.1, 0.2, 0.3]] * 5


class TestRangeForecastPrices:
    def test_pct_forecast_keeps_the_legacy_math(self):
        forecast = RangeForecast(2000.0, 0.01, -0.005, 5)
        assert forecast.target_units == "pct"
        assert forecast.predicted_high == pytest.approx(2020.0)
        assert forecast.predicted_low == pytest.approx(1990.0)

    def test_atr_forecast_prices_are_close_plus_mult_times_atr(self):
        forecast = RangeForecast(
            2000.0,
            0.003,  # synced fraction: 2.0 × 3.0 / 2000
            -0.003,
            5,
            target_units="atr",
            atr_reference=3.0,
            high_atr_mult=2.0,
            low_atr_mult=-2.0,
        )
        assert forecast.predicted_high == pytest.approx(2006.0)
        assert forecast.predicted_low == pytest.approx(1994.0)
        assert forecast.expected_range == pytest.approx(12.0)
        assert forecast.upside == pytest.approx(6.0)
        assert forecast.downside == pytest.approx(6.0)

    def test_atr_forecast_without_reference_is_refused(self):
        with pytest.raises(ValidationError):
            RangeForecast(2000.0, 0.003, -0.003, 5, target_units="atr")

    def test_unknown_units_are_refused(self):
        with pytest.raises(ValidationError):
            RangeForecast(2000.0, 0.01, -0.01, 5, target_units="euro")

    def test_to_dict_carries_the_atr_fields(self):
        forecast = RangeForecast(
            2000.0,
            0.003,
            -0.003,
            5,
            target_units="atr",
            atr_reference=3.0,
            high_atr_mult=2.0,
            low_atr_mult=-2.0,
        )
        payload = forecast.to_dict()
        assert payload["target_units"] == "atr"
        assert payload["atr_reference"] == 3.0
        assert payload["high_atr_mult"] == 2.0
        assert payload["predicted_high"] == pytest.approx(2006.0)


class TestRangePredictorAtr:
    def test_atr_model_output_becomes_dollars(self, patched_load):
        # last step = [high_1, low_1, high_2, low_2] — worst case over the
        # horizon: high = 2.0 ATR, low = −2.0 ATR.
        patched_load(FakeSeq2SeqModel([2.0, -1.0, 1.0, -2.0]))
        predictor = dual_predictor.RangePredictor(horizon=2, timeframe="1H", target_units="atr")
        forecast = predictor.forecast(
            fake_artifact(),
            raw_window(),
            reference_close=2000.0,
            atr_reference=3.0,
        )
        assert forecast.target_units == "atr"
        assert forecast.high_atr_mult == pytest.approx(2.0)
        assert forecast.low_atr_mult == pytest.approx(-2.0)
        assert forecast.predicted_high == pytest.approx(2000.0 + 2.0 * 3.0)
        assert forecast.predicted_low == pytest.approx(2000.0 - 2.0 * 3.0)
        # fraction fields stay synced for legacy percent displays
        assert forecast.high_offset == pytest.approx(6.0 / 2000.0)
        assert forecast.low_offset == pytest.approx(-6.0 / 2000.0)

    def test_atr_model_without_reference_is_refused(self, patched_load):
        patched_load(FakeSeq2SeqModel([2.0, -1.0, 1.0, -2.0]))
        predictor = dual_predictor.RangePredictor(horizon=2, timeframe="1H", target_units="atr")
        with pytest.raises(ValidationError):
            predictor.forecast(fake_artifact(), raw_window(), reference_close=2000.0)

    def test_pct_model_ignores_atr_and_keeps_legacy_math(self, patched_load):
        patched_load(FakeSeq2SeqModel([0.02, -0.01, 0.01, -0.02]))
        predictor = dual_predictor.RangePredictor(horizon=2, timeframe="1H")
        forecast = predictor.forecast(
            fake_artifact(),
            raw_window(),
            reference_close=2000.0,
            atr_reference=3.0,  # present but irrelevant for pct models
        )
        assert forecast.target_units == "pct"
        assert forecast.high_atr_mult == 0.0
        assert forecast.atr_reference == 0.0
        assert forecast.predicted_high == pytest.approx(2000.0 * 1.02)
        assert forecast.predicted_low == pytest.approx(2000.0 * 0.98)

    def test_unknown_constructor_units_are_refused(self):
        with pytest.raises(ValidationError):
            dual_predictor.RangePredictor(target_units="pips")
