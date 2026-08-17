"""Tests for the Phase 29 prediction targets.

These value objects are what the two models actually return, so their
guarantees matter more than their arithmetic: an undefined value must
stay undefined, and an incoherent model output must be visible rather
than quietly repaired.
"""

import pytest

from ShadBotTrader.domain.ai.prediction_target import (
    PredictionTarget,
    RangeForecast,
    SignalClass,
    SignalForecast,
    TargetKind,
)
from ShadBotTrader.domain.common.errors import ValidationError


# ------------------------------------------------------------- target ---
class TestPredictionTarget:
    def test_the_range_model_has_two_outputs(self):
        target = PredictionTarget(TargetKind.PRICE_RANGE, horizon=5, timeframe="1H")
        assert target.output_units == 2
        assert target.is_regression

    def test_the_signal_model_has_three_outputs(self):
        target = PredictionTarget(TargetKind.TRADE_SIGNAL, horizon=5, timeframe="5M")
        assert target.output_units == 3
        assert not target.is_regression

    def test_a_horizon_must_look_at_least_one_candle_ahead(self):
        with pytest.raises(ValidationError):
            PredictionTarget(TargetKind.PRICE_RANGE, horizon=0, timeframe="1H")

    def test_a_signal_needs_a_positive_neutral_band(self):
        """A zero band would label pure noise as a tradable move."""
        with pytest.raises(ValidationError):
            PredictionTarget(TargetKind.TRADE_SIGNAL, horizon=5, timeframe="5M", threshold=0.0)


# -------------------------------------------------------------- range ---
class TestRangeForecast:
    def forecast(self, high=0.01, low=-0.008, close=2000.0) -> RangeForecast:
        return RangeForecast(reference_close=close, high_offset=high, low_offset=low, horizon=5)

    def test_offsets_become_absolute_prices(self):
        forecast = self.forecast()
        assert forecast.predicted_high == pytest.approx(2020.0)
        assert forecast.predicted_low == pytest.approx(1984.0)

    def test_the_same_offsets_work_at_any_price_level(self):
        """Why offsets exist: gold at 2000 and 3000 is one problem."""
        cheap = self.forecast(close=2000.0)
        dear = self.forecast(close=3000.0)
        assert cheap.predicted_high / cheap.reference_close == pytest.approx(
            dear.predicted_high / dear.reference_close
        )

    def test_upside_and_downside_are_measured_from_the_close(self):
        forecast = self.forecast()
        assert forecast.upside == pytest.approx(20.0)
        assert forecast.downside == pytest.approx(16.0)
        assert forecast.reward_risk() == pytest.approx(1.25)

    def test_reward_risk_is_undefined_without_downside(self):
        """None means undefined — not zero, not infinity."""
        forecast = RangeForecast(
            reference_close=2000.0, high_offset=0.01, low_offset=0.0, horizon=5
        )
        assert forecast.reward_risk() is None

    def test_an_incoherent_forecast_is_reported_not_repaired(self):
        """A regression head can emit a high below its own low.

        Silently swapping them would hide a broken model.
        """
        forecast = RangeForecast(
            reference_close=2000.0, high_offset=-0.01, low_offset=0.01, horizon=5
        )
        assert not forecast.is_coherent
        assert forecast.predicted_high < forecast.predicted_low

    def test_a_non_positive_close_is_rejected(self):
        with pytest.raises(ValidationError):
            RangeForecast(reference_close=0.0, high_offset=0.01, low_offset=-0.01, horizon=5)

    def test_to_dict_carries_the_undefined_ratio_as_none(self):
        forecast = RangeForecast(
            reference_close=2000.0, high_offset=0.01, low_offset=0.0, horizon=5
        )
        assert forecast.to_dict()["reward_risk"] is None


# ------------------------------------------------------------- signal ---
class TestSignalForecast:
    def test_the_winning_class_and_its_probability(self):
        forecast = SignalForecast.from_vector((0.05, 0.05, 0.90), horizon=5)
        assert forecast.predicted_class is SignalClass.BUY
        assert forecast.confidence == pytest.approx(0.90)
        assert forecast.describe() == "buy 90.0%"

    def test_the_user_requirement_eighty_percent_sell(self):
        forecast = SignalForecast.from_vector((0.80, 0.15, 0.05), horizon=5)
        assert forecast.predicted_class is SignalClass.SELL
        assert forecast.describe() == "sell 80.0%"
        assert forecast.is_actionable(minimum=0.6)

    def test_probabilities_must_sum_to_one(self):
        with pytest.raises(ValidationError):
            SignalForecast(
                sell_probability=0.9,
                hold_probability=0.9,
                buy_probability=0.9,
                horizon=5,
            )

    def test_a_probability_outside_zero_to_one_is_rejected(self):
        with pytest.raises(ValidationError):
            SignalForecast(
                sell_probability=-0.1,
                hold_probability=0.6,
                buy_probability=0.5,
                horizon=5,
            )

    def test_hold_winning_is_valid_but_never_actionable(self):
        """ "No trade" is a real answer — it is just not a trade."""
        forecast = SignalForecast.from_vector((0.2, 0.7, 0.1), horizon=5)
        assert forecast.predicted_class is SignalClass.HOLD
        assert forecast.confidence == pytest.approx(0.7)
        assert not forecast.is_actionable(minimum=0.6)

    def test_a_weak_directional_call_is_not_actionable(self):
        forecast = SignalForecast.from_vector((0.30, 0.30, 0.40), horizon=5)
        assert forecast.predicted_class is SignalClass.BUY
        assert not forecast.is_actionable(minimum=0.6)

    def test_directional_confidence_ignores_hold(self):
        """An even split must read as undecided, not as a weak buy."""
        forecast = SignalForecast.from_vector((0.45, 0.10, 0.45), horizon=5)
        assert forecast.directional_confidence == pytest.approx(0.5)

    def test_directional_confidence_favours_the_stronger_side(self):
        forecast = SignalForecast.from_vector((0.10, 0.10, 0.80), horizon=5)
        assert forecast.directional_confidence == pytest.approx(0.8 / 0.9)

    def test_the_whole_vector_survives_to_the_dictionary(self):
        payload = SignalForecast.from_vector((0.1, 0.2, 0.7), horizon=5).to_dict()
        assert payload["sell_probability"] == pytest.approx(0.1)
        assert payload["hold_probability"] == pytest.approx(0.2)
        assert payload["buy_probability"] == pytest.approx(0.7)
        assert payload["predicted_class"] == "buy"

    def test_class_indices_match_the_softmax_column_order(self):
        assert int(SignalClass.SELL) == 0
        assert int(SignalClass.HOLD) == 1
        assert int(SignalClass.BUY) == 2
