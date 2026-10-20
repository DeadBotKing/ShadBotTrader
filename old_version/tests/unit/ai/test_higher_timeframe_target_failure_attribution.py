"""Phase180A higher-timeframe target failure attribution helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_higher_timeframe_target_failure_attribution as phase180


def candidate(**overrides):
    row = {
        "timeframe": "1",
        "family_id": "D1_R1",
        "label": "daily_mid",
        "side_mapping": "breakout",
        "tp_atr": 2.0,
        "sl_atr": 1.0,
        "hold_bars": 5,
        "train_events": 120,
        "validation_events": 30,
        "test_events": 35,
        "train_positive_rate": 0.4,
        "validation_positive_rate": 0.45,
        "test_positive_rate": 0.4,
        "validation_label_psi": 0.02,
        "test_label_psi": 0.02,
        "train_independent_profit_factor": 1.1,
        "validation_independent_profit_factor": 1.1,
        "test_independent_profit_factor": 1.2,
        "train_mean_atr_score": 0.05,
        "validation_mean_atr_score": 0.04,
        "test_mean_atr_score": 0.07,
        "validation_ap_lift": 0.03,
        "test_ap_lift": 0.01,
        "validation_balanced_accuracy": 0.525,
        "test_balanced_accuracy": 0.50,
        "walkforward_folds": 5,
        "walkforward_pass_folds": 1,
        "walkforward_pass_ratio": 0.2,
        "density_gate": 1,
        "economic_gate": 1,
        "static_learnability_gate": 0,
        "walkforward_gate": 0,
        "target_family_ready_gate": 0,
        "failure_reasons": '["static_learnability_gate_failed", "walkforward_gate_failed"]',
        "diagnostic_score": 10.0,
    }
    row.update(overrides)
    return row


def fold(**overrides):
    row = {
        "timeframe": "1",
        "family_id": "D1_R1",
        "label": "daily_mid",
        "fold": 1,
        "pass_gate": 0,
        "failure_reasons": '["validation_gate_failed"]',
    }
    row.update(overrides)
    return row


def test_canonical_timeframe():
    assert phase180.canonical_timeframe("1") == "1D"
    assert phase180.canonical_timeframe("D1") == "1D"
    assert phase180.canonical_timeframe("4") == "4H"
    assert phase180.canonical_timeframe("H4") == "4H"


def test_candidate_reasons_and_near_miss():
    row = candidate()

    reasons = phase180.candidate_reasons(row)

    assert phase180.near_miss_gate(row) == 1
    assert "test_balanced_accuracy_failed" in reasons
    assert "walkforward_pass_ratio_failed" in reasons


def test_build_candidate_failure_rows_canonicalizes_timeframe():
    rows = phase180.build_candidate_failure_rows([candidate()])

    assert rows[0].timeframe == "1D"
    assert rows[0].near_miss_gate == 1
    assert rows[0].primary_failure_reason


def test_timeframe_summary_selects_best_and_costs():
    payload = {
        "cost_rows": [
            {"timeframe": "1", "split": "train", "full_spread_atr_median": 0.02, "cost_feasible_gate": 1},
            {"timeframe": "1", "split": "validation", "full_spread_atr_median": 0.01, "cost_feasible_gate": 1},
            {"timeframe": "1", "split": "test", "full_spread_atr_median": 0.01, "cost_feasible_gate": 1},
        ],
        "health_rows": [{"timeframe": "1", "health_gate": 1}],
    }
    candidate_rows = phase180.build_candidate_failure_rows([candidate()])

    summary = phase180.build_timeframe_summary_rows(payload, candidate_rows)

    assert summary[0].timeframe == "1D"
    assert summary[0].near_miss_candidates == 1
    assert summary[0].cost_gate_pass_splits == 3
    assert summary[0].verdict == "TARGET_NOT_READY_COST_FEASIBLE"


def test_main_writes_outputs(tmp_path: Path):
    phase179 = {
        "symbol": "XAUUSD",
        "timeframes": ["4H", "1"],
        "spread_mode": "fixed",
        "spread_value": 0.4,
        "evaluated_candidates": 1,
        "ready_candidates": 0,
        "higher_timeframe_feasibility_gate": 0,
        "candidate_rows": [candidate()],
        "walkforward_rows": [fold(), fold(fold=2, failure_reasons='["test_gate_failed"]')],
        "cost_rows": [
            {"timeframe": "1", "split": "train", "full_spread_atr_median": 0.02, "cost_feasible_gate": 1},
            {"timeframe": "1", "split": "validation", "full_spread_atr_median": 0.01, "cost_feasible_gate": 1},
            {"timeframe": "1", "split": "test", "full_spread_atr_median": 0.01, "cost_feasible_gate": 1},
        ],
        "health_rows": [{"timeframe": "1", "health_gate": 1}],
    }
    phase179_path = tmp_path / "phase179.json"
    output_dir = tmp_path / "out"
    phase179_path.write_text(json.dumps(phase179), encoding="utf-8")

    result = phase180.main(["--phase179-path", str(phase179_path), "--output-dir", str(output_dir)])

    assert result == 0
    report = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert report["cost_feasibility_confirmed_gate"] == 1
    assert report["target_readiness_confirmed_failed_gate"] == 1
    assert report["selected_focus_timeframe"] == "1D"
    assert (output_dir / "latest_candidate_failures.csv").exists()


def test_decision_matrix_blocks_training():
    candidates = phase180.build_candidate_failure_rows([candidate()])
    matrix = phase180.build_decision_matrix(candidates, [])
    by_route = {row.route_id: row for row in matrix}

    assert by_route["HIGHER_TIMEFRAME_MODEL_TRAINING"].status == "BLOCKED"
    assert by_route["D1_TARGET_REDESIGN_ATTRIBUTION"].status == "RECOMMENDED_DIAGNOSTIC"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
