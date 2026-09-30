"""Phase159A pivot candidate geometry tightening helpers."""

from __future__ import annotations

import numpy as np

from scripts import audit_pivot_candidate_geometry_tightening as phase159


def test_parse_phase159_targets():
    targets = phase159.parse_targets("B4:24:1.0:0.5;B2:24:1.0:0.75")

    assert [target.target_id for target in targets] == ["B4", "B2"]
    assert targets[0].lookahead_bars == 24
    assert targets[0].tp_atr == 1.0
    assert targets[0].sl_atr == 0.5


def test_split_metrics_summarizes_sell_and_buy_events():
    metrics = phase159.split_metrics(
        "validation",
        np.asarray([0, 1, 2], dtype=np.int64),
        top_mask=np.asarray([True, False, False]),
        bottom_mask=np.asarray([False, True, True]),
        both_mask=np.asarray([False, False, False]),
        buy_scores=np.asarray([0.0, 1.0, -0.5], dtype=np.float32),
        sell_scores=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
    )

    assert metrics.event_count == 3
    assert metrics.sell_events == 1
    assert metrics.buy_events == 2
    assert metrics.win_count == 2
    assert metrics.mean_r == 0.5
    assert metrics.best_side == "SELL"


def test_phase159_sign_flip_detects_mean_r_flip():
    assert phase159.sign_flip(0.1, 0.2, -0.1) == 1
    assert phase159.sign_flip(0.1, 0.2, 0.3) == 0


def test_phase159_validation_score_modes():
    metrics = phase159.GeometrySplitMetrics(
        split="validation",
        rows=10,
        event_count=5,
        event_rate=0.5,
        sell_events=3,
        buy_events=2,
        both_zone_rows=0,
        win_count=3,
        win_rate=0.6,
        mean_r=0.2,
        sum_r=1.0,
        gross_profit=2.0,
        gross_loss=1.0,
        profit_factor=2.0,
        sell_mean_r=0.3,
        buy_mean_r=0.1,
        sell_win_rate=0.7,
        buy_win_rate=0.5,
        best_side="SELL",
    )

    assert phase159.validation_score(metrics, "mean_r") == 0.2
    assert phase159.validation_score(metrics, "sum_r") == 1.0
    assert phase159.validation_score(metrics, "profit_factor") == 2.0
