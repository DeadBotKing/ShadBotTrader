"""Phase157A payoff target learnability helpers."""

from __future__ import annotations

import numpy as np

from scripts import audit_pivot_payoff_target_learnability as phase157


def test_parse_phase157_default_candidates():
    candidates = phase157.parse_candidates("B4,B2")

    assert [candidate.candidate_id for candidate in candidates] == ["B4", "B2"]
    assert candidates[0].tensor_name == "pivot_payoff_sequence_tensor_b4_latest"


def test_summarize_tensor_windows_basic_mode():
    tensor = np.arange(2 * 3 * 2, dtype=np.float32).reshape(2, 3, 2)

    summary = phase157.summarize_tensor_windows(tensor, [0, 1], "basic", 1)

    assert summary.shape == (2, 6)
    np.testing.assert_allclose(summary[0, :2], tensor[0, -1, :])
    np.testing.assert_allclose(summary[0, 2:4], tensor[0].mean(axis=0))


def test_average_precision_for_ranked_positive():
    y = np.asarray([0, 1, 1], dtype=np.int64)
    scores = np.asarray([0.1, 0.9, 0.8], dtype=np.float32)

    assert phase157.average_precision(y, scores) == 1.0


def test_centroid_classifier_learns_separable_binary_data():
    x = np.asarray([[0.0], [0.2], [3.0], [3.2]], dtype=np.float32)
    y = np.asarray([0, 0, 1, 1], dtype=np.int64)

    model = phase157.CentroidClassifier([0, 1]).fit(x, y)
    pred = model.predict(x)

    assert pred.tolist() == [0, 0, 1, 1]


def test_binary_metrics_reports_perfect_f1():
    metrics = phase157.binary_metrics(
        np.asarray([0, 0, 1, 1], dtype=np.int64),
        np.asarray([0.1, 0.2, 0.8, 0.9], dtype=np.float32),
    )

    assert metrics["accuracy"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["f1"] == 1.0
