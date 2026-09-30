"""Phase158A pivot-zone candidate reframe helpers."""

from __future__ import annotations

import numpy as np

from scripts import audit_pivot_zone_candidate_reframe as phase158


def test_parse_phase158_default_candidates():
    candidates = phase158.parse_candidates("B4,B2")

    assert [candidate.candidate_id for candidate in candidates] == ["B4", "B2"]
    assert candidates[0].tensor_name == "pivot_payoff_sequence_tensor_b4_latest"


def test_build_zone_events_creates_top_sell_and_bottom_buy_events():
    x_summary = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    action = np.asarray([0, 2], dtype=np.int64)
    top_zone = np.asarray([1.0, 0.0], dtype=np.float32)
    bottom_zone = np.asarray([0.0, 1.0], dtype=np.float32)
    buy_r = np.asarray([0.0, 1.0], dtype=np.float32)
    sell_r = np.asarray([1.0, 0.0], dtype=np.float32)

    features, sides, scores, wins, matched = phase158.build_zone_events(
        [0, 1], x_summary, action, top_zone, bottom_zone, buy_r, sell_r
    )

    assert features.shape == (2, 3)
    assert sides.tolist() == [phase158.SIDE_SELL, phase158.SIDE_BUY]
    assert scores.tolist() == [1.0, 1.0]
    assert wins.tolist() == [1, 1]
    assert matched.tolist() == [1, 1]


def test_zone_split_row_summarizes_event_quality():
    row = phase158.zone_split_row(
        "B",
        "validation",
        [0, 1],
        action=np.asarray([0, 2], dtype=np.int64),
        top_zone=np.asarray([1.0, 0.0], dtype=np.float32),
        bottom_zone=np.asarray([0.0, 1.0], dtype=np.float32),
        sides=np.asarray([phase158.SIDE_SELL, phase158.SIDE_BUY], dtype=np.int64),
        scores=np.asarray([1.0, -0.5], dtype=np.float32),
        wins=np.asarray([1, 0], dtype=np.int64),
        matched=np.asarray([1, 0], dtype=np.int64),
    )

    assert row.zone_event_count == 2
    assert row.event_win_rate == 0.5
    assert row.event_mean_r == 0.25
    assert row.sell_mean_r == 1.0
    assert row.buy_mean_r == -0.5


def test_binary_metrics_detects_perfect_event_classifier():
    metrics = phase158.binary_metrics(
        np.asarray([0, 0, 1, 1], dtype=np.int64),
        np.asarray([0.1, 0.2, 0.8, 0.9], dtype=np.float32),
    )

    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["f1"] == 1.0


def test_sign_flip_detects_zone_mean_r_flip():
    assert phase158.sign_flip(0.1, 0.2, -0.1) == 1
    assert phase158.sign_flip(0.1, 0.2, 0.3) == 0
