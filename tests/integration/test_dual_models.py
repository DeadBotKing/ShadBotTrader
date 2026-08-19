"""Integration tests for the Phase 29 dual-model architecture.

Proves the two models the user asked for actually exist end to end:

* a **range model** that predicts the high and low of the next N candles
* a **binary signal model** that predicts buy/sell with probabilities

The TensorFlow training tests are gated behind ``RUN_TF`` like the rest
of the AI suite; everything up to the trainer runs unconditionally,
because that is where the leakage risk lives.
"""

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import sin

import pytest

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.domain.ai.model_types import ModelType
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.model_roles import (
    default_roles,
    range_model_role,
    signal_model_role,
)

RUN_TF = os.environ.get("RUN_TF") == "1"
requires_tf = pytest.mark.skipif(not RUN_TF, reason="set RUN_TF=1 to run TensorFlow tests")

SYMBOL = Symbol("XAUUSD")
HOURLY = Timeframe("1H")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def wave(count: int = 200, timeframe: Timeframe = HOURLY):
    """A gently oscillating series: enough structure to be learnable."""
    candles = []
    price = 2000.0
    for index in range(count):
        move = sin(index / 7.0) * 3.0 + ((index % 5) - 2) * 0.4
        open_, close = price, price + move
        candles.append(
            Candle(
                symbol=SYMBOL,
                timeframe=timeframe,
                open_time=Timestamp(BASE + timedelta(hours=index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.2, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.2, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("100"),
            )
        )
        price = close
    return candles


@pytest.fixture
def service():
    return DualModelService(include_features=False)


# ---------------------------------------------------------------- roles ---
class TestModelRoles:
    def test_the_requested_defaults_are_what_the_user_asked_for(self):
        roles = default_roles()

        assert roles["range"].timeframe == "1H"
        assert roles["signal"].timeframe == "5M"
        assert roles["range"].horizon == 5
        assert roles["signal"].horizon == 5

    def test_the_range_head_is_a_two_output_regression(self):
        role = range_model_role()
        assert role.output_units == 2
        assert role.loss == "mse"
        assert role.output_activation == "linear"

    def test_the_signal_head_is_a_binary_softmax(self):
        role = signal_model_role()
        assert role.output_units == 2
        assert role.loss == "sparse_categorical_crossentropy"
        assert role.output_activation == "softmax"

    def test_a_bounded_activation_is_never_used_for_regression(self):
        """A sigmoid head cannot express a negative low offset."""
        assert range_model_role().output_activation not in ("sigmoid", "softmax")


# ------------------------------------------------------------ datasets ---
class TestDatasetPreparation:
    def test_the_range_dataset_carries_two_targets(self, service):
        dataset = service.prepare(wave(), SYMBOL, HOURLY, range_model_role(window_size=16))

        assert len(dataset.target_columns) == 2
        assert dataset.column_names[-2:] == ["future_high_offset", "future_low_offset"]

    def test_the_signal_dataset_carries_one_label_and_its_distribution(self, service):
        dataset = service.prepare(
            wave(), SYMBOL, HOURLY, signal_model_role(timeframe="1H", window_size=16)
        )

        assert len(dataset.target_columns) == 1
        assert dataset.label_distribution is not None
        assert set(dataset.label_distribution) == {"sell", "buy"}

    def test_the_horizon_costs_exactly_that_many_rows(self, service):
        candles = wave(120)
        dataset = service.prepare(
            candles, SYMBOL, HOURLY, range_model_role(horizon=5, window_size=16)
        )
        assert dataset.row_count == len(candles) - 5

    def test_a_longer_horizon_leaves_less_data(self, service):
        candles = wave(120)
        short = service.prepare(
            candles, SYMBOL, HOURLY, range_model_role(horizon=2, window_size=16)
        )
        long = service.prepare(
            candles, SYMBOL, HOURLY, range_model_role(horizon=20, window_size=16)
        )
        assert short.row_count > long.row_count

    def test_too_few_candles_is_refused_with_a_useful_message(self, service):
        with pytest.raises(ValidationError) as error:
            service.prepare(wave(10), SYMBOL, HOURLY, range_model_role(window_size=16))
        assert "candles" in str(error.value)

    def test_the_definition_declares_regression_for_the_range_model(self, service):
        role = range_model_role(window_size=16)
        dataset = service.prepare(wave(), SYMBOL, HOURLY, role)

        definition = service.definition_for(role, dataset)

        assert definition.model_type is ModelType.REGRESSION
        assert definition.output_schema["units"] == 2
        assert definition.output_schema["activation"] == "linear"

    def test_the_definition_declares_classification_for_the_signal_model(self, service):
        role = signal_model_role(timeframe="1H", window_size=16)
        dataset = service.prepare(wave(), SYMBOL, HOURLY, role)

        definition = service.definition_for(role, dataset)

        assert definition.model_type is ModelType.CLASSIFICATION
        assert definition.output_schema["units"] == 2


# ------------------------------------------------------------- leakage ---
class TestLeakageProtection:
    def test_targets_never_appear_among_the_input_features(self, service):
        """R3: the model must not be able to read its own answer."""
        role = range_model_role(window_size=16)
        dataset = service.prepare(wave(), SYMBOL, HOURLY, role)

        trainer = service.build_trainer(dataset)
        samples = trainer._series  # the raw labelled matrix

        # the windowed input drops exactly the target columns
        assert len(samples[0]) == dataset.feature_count + 2

        from ShadBotTrader.infrastructure.ai.data_windowing import (
            build_multi_target_samples,
        )

        windowed = build_multi_target_samples(
            dataset.series, window_size=4, target_columns=dataset.target_columns
        )
        assert len(windowed[0].features[0]) == dataset.feature_count

    def test_the_last_rows_of_the_series_are_never_labelled(self, service):
        """R2: an incomplete future window must be dropped, not guessed."""
        candles = wave(100)
        role = range_model_role(horizon=5, window_size=16)
        dataset = service.prepare(candles, SYMBOL, HOURLY, role)

        assert dataset.row_count <= len(candles) - role.horizon


# ------------------------------------------------------------ training ---
@requires_tf
class TestTraining:
    def test_the_range_model_trains_and_predicts_two_prices(self, service):
        role = range_model_role(window_size=12)
        outcome = service.train(
            wave(140), SYMBOL, HOURLY, role, run_id="range-test", epochs=1, max_folds=2
        )

        assert outcome["fold_losses"]
        assert all(loss >= 0 for loss in outcome["fold_losses"])

        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor

        dataset = service.prepare(wave(140), SYMBOL, HOURLY, role)
        window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]

        forecast = RangePredictor(horizon=role.horizon).forecast(
            outcome["artifact"], window, reference_close=2000.0
        )

        assert forecast.predicted_high > 0
        assert forecast.predicted_low > 0
        assert forecast.horizon == 5

    def test_the_signal_model_returns_two_probabilities_summing_to_one(self, service):
        role = signal_model_role(timeframe="1H", window_size=12)
        outcome = service.train(
            wave(140), SYMBOL, HOURLY, role, run_id="signal-test", epochs=1, max_folds=2
        )

        from ShadBotTrader.infrastructure.ai.dual_predictor import SignalPredictor

        dataset = service.prepare(wave(140), SYMBOL, HOURLY, role)
        window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]

        forecast = SignalPredictor(horizon=role.horizon).forecast(outcome["artifact"], window)

        total = forecast.sell_probability + forecast.buy_probability
        assert total == pytest.approx(1.0, abs=0.01)
        assert forecast.predicted_class.label in {"sell", "buy"}
        assert 0.0 <= forecast.confidence <= 1.0

    def test_regression_uses_mse_not_cross_entropy(self, service):
        """The bug this phase fixes: the loss used to be hardcoded."""
        role = range_model_role(window_size=12)
        dataset = service.prepare(wave(140), SYMBOL, HOURLY, role)
        trainer = service.build_trainer(dataset)

        assert trainer._loss == "mse"
        assert trainer._target_columns == dataset.target_columns

    def test_the_two_models_produce_independent_artifacts(self, service):
        candles = wave(140)
        range_out = service.train(
            candles,
            SYMBOL,
            HOURLY,
            range_model_role(window_size=12),
            run_id="r",
            epochs=1,
            max_folds=1,
        )
        signal_out = service.train(
            candles,
            SYMBOL,
            HOURLY,
            signal_model_role(timeframe="1H", window_size=12),
            run_id="s",
            epochs=1,
            max_folds=1,
        )

        assert range_out["artifact"].model_id.value != signal_out["artifact"].model_id.value
        assert range_out["artifact"].payload != signal_out["artifact"].payload


# ------------------------------------------------------ reproducibility ---
@requires_tf
class TestReproducibility:
    """Phase 13 §34: the same configuration must reproduce the same model.

    Regression test for a real defect: ``_build_compiled`` accepted a
    ``seed`` argument and never used it. ``tf.random.set_seed`` alone is
    not enough under Keras 3 — each layer draws its initial weights from
    its own generator — so two runs of the identical configuration
    produced different predictions.
    """

    def test_two_identical_runs_produce_the_same_forecast(self, service):
        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor

        candles = wave(140)
        role = range_model_role(window_size=12)
        dataset = service.prepare(candles, SYMBOL, HOURLY, role)
        window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]

        forecasts = []
        for attempt in range(2):
            outcome = service.train(
                candles,
                SYMBOL,
                HOURLY,
                role,
                run_id=f"repro-{attempt}",
                epochs=1,
                max_folds=1,
            )
            forecasts.append(
                RangePredictor(horizon=role.horizon).forecast(
                    outcome["artifact"], window, reference_close=2000.0
                )
            )

        assert forecasts[0].high_offset == pytest.approx(forecasts[1].high_offset, abs=1e-6)
        assert forecasts[0].low_offset == pytest.approx(forecasts[1].low_offset, abs=1e-6)

    def test_fold_losses_are_stable_across_runs(self, service):
        candles = wave(140)
        role = signal_model_role(timeframe="1H", window_size=12)

        first = service.train(candles, SYMBOL, HOURLY, role, run_id="a", epochs=1, max_folds=1)[
            "fold_losses"
        ]
        second = service.train(candles, SYMBOL, HOURLY, role, run_id="b", epochs=1, max_folds=1)[
            "fold_losses"
        ]

        assert first == pytest.approx(second, abs=1e-6)
