"""Independent-test diagnostics for the range model's two bounds."""

from types import SimpleNamespace

import pytest

from ShadBotTrader.application.services.model_evaluation_service import (
    EvaluationResult,
    ModelEvaluationService,
)
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer


def matrix_for(closes, highs, lows):
    rows = []
    previous = closes[0]
    for close, high, low in zip(closes, highs, lows, strict=True):
        rows.append(
            [
                (close - previous) / previous,
                high / close - 1.0,
                low / close - 1.0,
            ]
        )
        previous = close
    return SimpleNamespace(
        rows=rows,
        column_names=["return_1", "high_rel", "low_rel"],
    )


def test_range_score_reconstructs_offsets_from_current_close_and_splits_bounds():
    closes = [100.0, 102.0, 101.0, 104.0, 103.0, 105.0]
    highs = [101.0, 104.0, 103.0, 106.0, 105.0, 107.0]
    lows = [99.0, 100.0, 98.0, 102.0, 101.0, 103.0]
    matrix = matrix_for(closes, highs, lows)
    result = EvaluationResult(
        model_id="range",
        role="range",
        symbol="XAUUSD",
        timeframe="1H",
        window_size=2,
    )

    # Build the exact labels for starts 0 and 1 using the same reference
    # definition as the target builder: future extremes from the window end.
    expected = []
    for start in (0, 1):
        here = start + 1
        reference = closes[here]
        future_high = max(highs[here + 1 : here + 3])
        future_low = min(lows[here + 1 : here + 3])
        expected.append([future_high / reference - 1.0, future_low / reference - 1.0])

    ModelEvaluationService("unused")._score_range(  # noqa: SLF001
        result,
        predictions=expected,
        starts=[0, 1],
        matrix=matrix,
        horizon=2,
    )

    assert result.metrics["mae"] == pytest.approx(0.0)
    assert result.metrics["high_mae"] == pytest.approx(0.0)
    assert result.metrics["low_mae"] == pytest.approx(0.0)
    assert result.metrics["high_rmse"] == pytest.approx(0.0)
    assert result.metrics["low_rmse"] == pytest.approx(0.0)
    assert result.metrics["high_bias"] == pytest.approx(0.0)
    assert result.metrics["low_bias"] == pytest.approx(0.0)


def test_training_range_metrics_keep_high_and_low_separate():
    class Model:
        def predict(self, values, steps=None, verbose=0):
            return [[0.02, -0.01], [0.03, -0.02]]

    trainer = WavenetTrainer(
        series=[[0.0, 0.0, 0.0, 0.0] for _ in range(8)],
        target_column=2,
        target_columns=[2, 3],
        window_size=2,
    )
    metrics = trainer._range_validation_metrics(  # noqa: SLF001
        Model(),
        validation_x=[[[]]],
        validation_y=[[0.01, -0.02], [0.02, -0.01]],
        validation_steps=1,
        start=0,
        stop=2,
    )

    assert metrics["val_high_mae"] == pytest.approx(0.01)
    assert metrics["val_low_mae"] == pytest.approx(0.01)
    assert metrics["val_high_bias"] == pytest.approx(0.01)
    assert metrics["val_low_bias"] == pytest.approx(-0.0)


def test_range_score_bias_is_prediction_minus_truth():
    matrix = matrix_for(
        [100.0, 100.0, 101.0, 102.0],
        [101.0, 101.0, 102.0, 103.0],
        [99.0, 99.0, 100.0, 101.0],
    )
    result = EvaluationResult(
        model_id="range",
        role="range",
        symbol="XAUUSD",
        timeframe="1H",
        window_size=2,
    )
    ModelEvaluationService("unused")._score_range(  # noqa: SLF001
        result,
        predictions=[[0.04, -0.04]],
        starts=[0],
        matrix=matrix,
        horizon=2,
    )

    assert result.metrics["high_bias"] > 0
    assert result.metrics["low_bias"] < 0
