"""Tests for regression/classification/trading metrics."""

from ShadBotTrader.infrastructure.ai.metrics import (
    classification_metrics,
    regression_metrics,
    trading_metrics,
)


def test_regression_metrics_perfect():
    metrics = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0


def test_regression_metrics_mae():
    metrics = regression_metrics([1.0, 3.0], [2.0, 2.0])
    assert metrics["mae"] == 1.0


def test_classification_metrics_perfect():
    metrics = classification_metrics([0, 1, 0, 1], [0, 1, 0, 1], num_classes=2)
    assert metrics["accuracy"] == 1.0
    assert metrics["f1"] == 1.0


def test_trading_metrics_hit_rate():
    # direction +1 twice: one win (+0.5), one loss (-0.3)
    metrics = trading_metrics([1, 1], [0.5, -0.3])
    assert metrics["trades"] == 2
    assert metrics["hit_rate"] == 0.5
    assert metrics["profit_factor"] > 1.0
