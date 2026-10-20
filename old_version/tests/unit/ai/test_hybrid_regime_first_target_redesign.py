"""Phase174A hybrid/regime-first target redesign helpers."""

from __future__ import annotations

import pytest

from scripts import audit_hybrid_regime_first_target_redesign as phase174
from scripts.audit_broker_cost_aware_1h_target_family import LABEL_NEGATIVE, LABEL_POSITIVE, parse_families
from scripts.audit_broker_cost_aware_1h_target_learnability import EventFeatureRow


def make_row(
    row_id: int,
    split: str,
    side: str,
    label: str,
    ret_24: float,
    spread_to_atr: float = 0.05,
    atr: float = 10.0,
    width: float = 2.0,
    hour: int = 10,
) -> EventFeatureRow:
    positive = int(label == LABEL_POSITIVE)
    score = 1.0 if positive else -1.0
    return EventFeatureRow(
        family_id="F",
        row_id=row_id,
        timestamp=f"2026-01-01 {hour:02d}:00:00+00:00",
        split=split,
        fold=0,
        side=side,
        zone="top" if side == "BUY" else "bottom",
        label=label,
        target_positive=positive,
        atr_score=score,
        points_pnl=score,
        outcome="take_profit" if positive else "stop_loss",
        side_buy=1.0 if side == "BUY" else 0.0,
        side_sell=1.0 if side == "SELL" else 0.0,
        zone_top=1.0 if side == "BUY" else 0.0,
        zone_bottom=1.0 if side == "SELL" else 0.0,
        atr=atr,
        range_atr=1.0,
        body_atr=ret_24,
        upper_wick_atr=0.1,
        lower_wick_atr=0.1,
        recent_position=0.8 if side == "BUY" else 0.2,
        recent_width_atr=width,
        dist_top_atr=0.1,
        dist_bottom_atr=0.1,
        ret_1_atr=ret_24,
        ret_3_atr=ret_24,
        ret_6_atr=ret_24,
        ret_12_atr=ret_24,
        ret_24_atr=ret_24,
        hour_sin=0.0,
        hour_cos=1.0,
        dow_sin=0.0,
        dow_cos=1.0,
        spread_to_atr=spread_to_atr,
    )


def make_rows(split: str, start: int, count: int) -> list[EventFeatureRow]:
    rows: list[EventFeatureRow] = []
    for offset in range(count):
        positive = offset % 2 == 0
        rows.append(
            make_row(
                start + offset,
                split,
                "BUY" if offset % 3 else "SELL",
                LABEL_POSITIVE if positive else LABEL_NEGATIVE,
                1.0 if positive else -1.0,
                spread_to_atr=0.05,
                atr=20.0 if positive else 10.0,
                width=3.0 if positive else 1.0,
            )
        )
    return rows


def test_parse_regime_rules_normalizes_and_rejects_unknown():
    assert phase174.parse_regime_rules("buy_only, sell_only") == ["BUY_ONLY", "SELL_ONLY"]

    with pytest.raises(RuntimeError):
        phase174.parse_regime_rules("unknown_rule")


def test_filter_rows_by_regime_checks_side_spread_and_momentum():
    train = [
        make_row(1, "train", "BUY", LABEL_POSITIVE, 1.0, spread_to_atr=0.05),
        make_row(2, "train", "SELL", LABEL_NEGATIVE, 1.0, spread_to_atr=0.20),
        make_row(3, "train", "SELL", LABEL_POSITIVE, -1.0, spread_to_atr=0.04),
    ]
    context = phase174.build_regime_context(train)

    assert [row.row_id for row in phase174.filter_rows_by_regime(train, "BUY_ONLY", context)] == [1]
    assert [row.row_id for row in phase174.filter_rows_by_regime(train, "SPREAD_ATR_LE_010", context)] == [1, 3]
    assert [row.row_id for row in phase174.filter_rows_by_regime(train, "MOMENTUM_ALIGNED", context)] == [1, 3]


def test_static_regime_learnability_and_summary_can_pass_on_separable_fixture():
    family = parse_families("F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24")[0]
    rows = make_rows("train", 0, 20) + make_rows("validation", 100, 8) + make_rows("test", 200, 8)
    args = phase174.parse_args(
        [
            "--min-train-events", "4",
            "--min-validation-events", "4",
            "--min-test-events", "4",
            "--min-positive-rate", "0.10",
            "--max-positive-rate", "0.90",
            "--min-ap-lift", "0.01",
            "--min-balanced-accuracy", "0.50",
            "--min-train-independent-pf", "0.1",
            "--min-validation-independent-pf", "0.1",
            "--min-test-independent-pf", "0.1",
            "--min-walkforward-folds", "1",
            "--min-walkforward-pass-ratio", "0.5",
        ]
    )
    split_rows = phase174.static_regime_learnability(family, rows, "ALL")
    wf = [
        phase174.RegimeWalkForwardRow(
            "F", "label", "ALL", "all_events_baseline", 1,
            20, 8, 8, 0.5, 0.5, 0.5, 0.5, 0.5, 0.75, 0.75, 2.0, 2.0, 0.0, 0.0, 1,
        )
    ]

    summary = phase174.summarize_regime_candidate(family, "ALL", split_rows, wf, args)

    assert summary.class_balance_gate == 1
    assert summary.static_learnability_gate == 1
    assert summary.walkforward_learnability_gate == 1
    assert summary.regime_candidate_ready_gate == 1


def test_decision_matrix_blocks_training_even_when_regime_route_is_ready():
    row = phase174.RegimeCandidateRow(
        family_id="F",
        family_label="label",
        regime_rule_id="ALL",
        regime_label="all_events_baseline",
        train_events=100,
        validation_events=30,
        test_events=30,
        validation_event_coverage=1.0,
        test_event_coverage=1.0,
        train_positive_rate=0.5,
        validation_positive_rate=0.5,
        test_positive_rate=0.5,
        validation_label_psi=0.0,
        test_label_psi=0.0,
        train_ap_lift=0.2,
        validation_ap_lift=0.2,
        test_ap_lift=0.2,
        validation_balanced_accuracy=0.6,
        test_balanced_accuracy=0.6,
        validation_f1=0.6,
        test_f1=0.6,
        train_independent_profit_factor=1.2,
        validation_independent_profit_factor=1.2,
        test_independent_profit_factor=1.2,
        train_mean_atr_score=0.1,
        validation_mean_atr_score=0.1,
        test_mean_atr_score=0.1,
        walkforward_folds=6,
        walkforward_pass_folds=3,
        walkforward_pass_ratio=0.5,
        class_balance_gate=1,
        economic_gate=1,
        static_learnability_gate=1,
        walkforward_learnability_gate=1,
        regime_candidate_ready_gate=1,
        warnings="[]",
    )

    matrix = phase174.build_decision_matrix([row])
    by_route = {item.route_id: item for item in matrix}

    assert by_route["HYBRID_REGIME_FIRST_REDESIGN"].status == "READY_FOR_NEXT_DIAGNOSTIC"
    assert by_route["DEEP_MODEL_TRAINING_NOW"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
