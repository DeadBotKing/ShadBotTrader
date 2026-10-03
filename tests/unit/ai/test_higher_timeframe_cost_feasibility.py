"""Phase179A higher-timeframe cost feasibility helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_higher_timeframe_cost_feasibility as phase179


def make_frame(rows: int = 240, freq: str = "4h") -> pd.DataFrame:
    close = np.linspace(100.0, 130.0, rows)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=rows, freq=freq, tz="UTC"),
            "open": close,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "atr": np.full(rows, 10.0),
        }
    )


def test_parse_timeframes_and_spread_price():
    assert phase179.parse_timeframes("4H,1D,4H") == ["4H", "1D"]
    assert phase179.parse_timeframes("H4,1") == ["4H", "1D"]
    assert phase179.spread_price(100.0, "fixed", 0.4) == 0.4
    assert phase179.spread_price(100.0, "pct", 1.0) == 1.0


def test_auto_fold_specs_builds_requested_folds():
    args = phase179.parse_args(["--max-folds", "3", "--purge-gap", "2"])

    specs = phase179.auto_fold_specs(500, args)

    assert 1 <= len(specs) <= 3
    assert specs[0].train_start == 0
    assert specs[0].test_end <= 500


def test_health_and_cost_rows_gate_pass_on_clean_fixture():
    frame = make_frame()
    atr = frame["atr"].to_numpy(dtype=float)
    train_idx = np.arange(0, 120)
    val_idx = np.arange(130, 180)
    test_idx = np.arange(190, 230)
    args = phase179.parse_args(["--spread-value", "0.4", "--max-median-spread-atr", "0.1"])

    health = phase179.build_health_row("4H", phase179.Path("fixture.parquet"), frame, atr, train_idx, val_idx, test_idx)
    costs = phase179.cost_rows_for_timeframe("4H", frame, atr, {"train": train_idx}, args)

    assert health.health_gate == 1
    assert costs[0].full_spread_atr_median == 0.04
    assert costs[0].cost_feasible_gate == 1


def test_decision_matrix_blocks_training_without_ready_candidate():
    matrix = phase179.decision_matrix(0, None)
    by_route = {row.route_id: row for row in matrix}

    assert by_route["HIGHER_TIMEFRAME_TARGET_READY"].status == "NOT_CONFIRMED"
    assert by_route["TRAIN_MODEL_NOW"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"


def test_wrap_candidate_preserves_timeframe():
    from scripts.audit_walkforward_target_family_redesign_candidates import TargetRedesignCandidateRow

    row = TargetRedesignCandidateRow(
        family_id="F",
        label="label",
        side_mapping="breakout",
        entry_delay_bars=1,
        recent_window_bars=10,
        pivot_zone_atr=0.1,
        top_position_threshold=0.85,
        bottom_position_threshold=0.15,
        tp_atr=1.5,
        sl_atr=1.0,
        reward_risk=1.5,
        hold_bars=5,
        train_events=100,
        validation_events=20,
        test_events=20,
        train_positive_rate=0.3,
        validation_positive_rate=0.3,
        test_positive_rate=0.3,
        validation_label_psi=0.0,
        test_label_psi=0.0,
        train_independent_profit_factor=1.0,
        validation_independent_profit_factor=1.0,
        test_independent_profit_factor=1.0,
        train_mean_atr_score=0.1,
        validation_mean_atr_score=0.1,
        test_mean_atr_score=0.1,
        validation_ap_lift=0.1,
        test_ap_lift=0.1,
        validation_balanced_accuracy=0.6,
        test_balanced_accuracy=0.6,
        walkforward_folds=5,
        walkforward_pass_folds=3,
        walkforward_pass_ratio=0.6,
        density_gate=1,
        economic_gate=1,
        static_learnability_gate=1,
        walkforward_gate=1,
        target_family_redesign_ready_gate=1,
        failure_reasons="[]",
        diagnostic_score=10.0,
    )

    wrapped = phase179.wrap_candidate("4H", row)

    assert wrapped.timeframe == "4H"
    assert wrapped.family_id == "F"
    assert wrapped.target_family_ready_gate == 1
