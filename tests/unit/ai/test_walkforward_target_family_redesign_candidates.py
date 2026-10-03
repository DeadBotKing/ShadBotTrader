"""Phase177A walk-forward target-family redesign candidate helpers."""

from __future__ import annotations

import numpy as np

from scripts import audit_walkforward_target_family_redesign_candidates as phase177
from scripts.audit_broker_cost_aware_1h_target_family import parse_families
from scripts.audit_broker_cost_aware_1h_target_learnability import EventFeatureRow


def row(label: str, score: float, split: str = "train", side: str = "BUY") -> EventFeatureRow:
    return EventFeatureRow(
        family_id="F",
        row_id=1,
        timestamp="2026-01-01 00:00:00+00:00",
        split=split,
        fold=0,
        side=side,
        zone="top",
        label=label,
        target_positive=1 if label == "POSITIVE" else 0,
        atr_score=score,
        points_pnl=score,
        outcome="take_profit" if score > 0 else "stop_loss",
        side_buy=1.0 if side == "BUY" else 0.0,
        side_sell=1.0 if side == "SELL" else 0.0,
        zone_top=1.0,
        zone_bottom=0.0,
        atr=10.0,
        range_atr=1.0,
        body_atr=score,
        upper_wick_atr=0.1,
        lower_wick_atr=0.1,
        recent_position=0.8,
        recent_width_atr=2.0,
        dist_top_atr=0.1,
        dist_bottom_atr=1.0,
        ret_1_atr=score,
        ret_3_atr=score,
        ret_6_atr=score,
        ret_12_atr=score,
        ret_24_atr=score,
        hour_sin=0.0,
        hour_cos=1.0,
        dow_sin=0.0,
        dow_cos=1.0,
        spread_to_atr=0.04,
    )


def split_rows(split: str, n: int = 20) -> list[EventFeatureRow]:
    rows: list[EventFeatureRow] = []
    for idx in range(n):
        positive = idx % 2 == 0
        rows.append(row("POSITIVE" if positive else "NEGATIVE", 1.0 if positive else -1.0, split, "BUY" if idx % 3 else "SELL"))
    return rows


def test_average_precision_and_balanced_accuracy():
    y = np.asarray([1, 0, 1, 0])
    scores = np.asarray([0.9, 0.1, 0.8, 0.2])
    pred = np.asarray([1, 0, 1, 0])

    assert phase177.average_precision(y, scores) == 1.0
    assert phase177.balanced_accuracy(y, pred) == 1.0
    assert phase177.f1_score(y, pred) == 1.0


def test_label_distribution_and_economic_summary():
    rows = [row("POSITIVE", 1.0), row("NEGATIVE", -0.5), row("NEGATIVE", -1.0)]

    dist = phase177.label_distribution(rows)
    econ = phase177.economic_summary(rows)

    assert dist["POSITIVE"] == 1 / 3
    assert econ["independent_profit_factor"] > 0
    assert econ["mean_atr_score"] < 0


def test_static_candidate_splits_and_summary_can_pass_fixture():
    family = parse_families("F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:1.5:1:12")[0]
    rows = split_rows("train", 30) + split_rows("validation", 12) + split_rows("test", 12)
    args = phase177.parse_args([
        "--min-train-events", "10",
        "--min-validation-events", "5",
        "--min-test-events", "5",
        "--min-positive-rate", "0.1",
        "--max-positive-rate", "0.9",
        "--min-train-independent-pf", "0.5",
        "--min-validation-independent-pf", "0.5",
        "--min-test-independent-pf", "0.5",
        "--min-train-mean-atr-score", "-1",
        "--min-ap-lift", "0.0",
        "--min-balanced-accuracy", "0.5",
        "--min-walkforward-folds", "1",
        "--min-walkforward-pass-ratio", "0.5",
    ])

    splits = phase177.static_candidate_splits(family, rows, args)
    folds = [
        phase177.CandidateFoldRow(
            "F", "label", 1, 30, 12, 12, 0.5, 0.5, 0.5, 0.0, 0.0, 2.0, 2.0, 2.0,
            0.1, 0.1, 0.1, 0.2, 0.2, 0.6, 0.6, 1, "[]",
        )
    ]
    summary = phase177.candidate_summary(family, splits, folds, args)

    assert {item.split for item in splits} == {"train", "validation", "test"}
    assert summary.target_family_redesign_ready_gate == 1


def test_rank_and_decision_matrix_block_training_without_ready_candidate():
    family = parse_families("F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:1.5:1:12")[0]
    args = phase177.parse_args(["--min-train-mean-atr-score", "0"])
    splits = phase177.static_candidate_splits(family, split_rows("train", 20) + split_rows("validation", 8) + split_rows("test", 8), args)
    summary = phase177.candidate_summary(family, splits, [], args)

    ranked = phase177.rank_candidates([summary])
    matrix = phase177.build_decision_matrix(0, ranked[0])
    by_route = {row.route_id: row for row in matrix}

    assert ranked[0].family_id == "F"
    assert by_route["TRAIN_MODEL_NOW"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
