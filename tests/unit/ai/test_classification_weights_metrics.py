"""Phase 108 — class weights and per-class metrics for classification models."""

from __future__ import annotations

import pytest

from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
    average_precision_score,
    class_weight_for_labels,
    classification_report_metrics,
    monitor_mode,
)


def test_balanced_class_weights_use_fold_counts():
    weights = class_weight_for_labels([0, 0, 0, 1, 2, 2], num_classes=3)

    assert weights[0] == pytest.approx(6 / (3 * 3))
    assert weights[1] == pytest.approx(6 / (3 * 1))
    assert weights[2] == pytest.approx(6 / (3 * 2))


def test_missing_classes_are_omitted_from_class_weights():
    weights = class_weight_for_labels([1, 1, 1], num_classes=3)

    assert weights == {1: pytest.approx(1 / 3)}


def test_classification_report_contains_trend_signal_metrics():
    probs = [
        [0.90, 0.05, 0.05],
        [0.10, 0.80, 0.10],
        [0.10, 0.20, 0.70],
        [0.20, 0.30, 0.50],
    ]
    metrics = classification_report_metrics([0, 1, 2, 0], [0, 1, 2, 2], probs, 3)

    assert metrics["val_sell_precision"] == pytest.approx(1.0)
    assert metrics["val_sell_recall"] == pytest.approx(0.5)
    assert metrics["val_buy_f1"] > 0
    assert "val_macro_f1" in metrics
    assert "val_buy_sell_f1" in metrics
    assert "val_buy_ap" in metrics
    assert "val_sell_ap" in metrics


def test_average_precision_score_without_sklearn():
    assert average_precision_score([0, 2, 2], [0.1, 0.9, 0.8], positive=2) == 1.0


def test_monitor_mode_maximizes_f1_and_auc():
    assert monitor_mode("val_macro_f1") == "max"
    assert monitor_mode("val_auc") == "max"
    assert monitor_mode("val_loss") == "min"
