"""Phase175A hybrid/regime walk-forward failure attribution helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_hybrid_regime_walkforward_failure_attribution as phase175


def candidate(**overrides):
    row = {
        "family_id": "F1",
        "family_label": "family_one",
        "regime_rule_id": "R1",
        "regime_label": "regime_one",
        "train_events": 100,
        "validation_events": 30,
        "test_events": 30,
        "train_positive_rate": 0.30,
        "validation_positive_rate": 0.35,
        "test_positive_rate": 0.36,
        "validation_label_psi": 0.02,
        "test_label_psi": 0.03,
        "validation_ap_lift": 0.08,
        "test_ap_lift": 0.05,
        "validation_balanced_accuracy": 0.56,
        "test_balanced_accuracy": 0.55,
        "train_independent_profit_factor": 0.70,
        "validation_independent_profit_factor": 1.30,
        "test_independent_profit_factor": 1.10,
        "train_mean_atr_score": -0.20,
        "validation_mean_atr_score": 0.10,
        "test_mean_atr_score": 0.05,
        "walkforward_folds": 6,
        "walkforward_pass_folds": 0,
        "walkforward_pass_ratio": 0.0,
        "class_balance_gate": 1,
        "economic_gate": 0,
        "static_learnability_gate": 0,
        "walkforward_learnability_gate": 0,
        "regime_candidate_ready_gate": 0,
    }
    row.update(overrides)
    return row


def fold(**overrides):
    row = {
        "family_id": "F1",
        "family_label": "family_one",
        "regime_rule_id": "R1",
        "regime_label": "regime_one",
        "fold": 1,
        "train_events": 100,
        "validation_events": 30,
        "test_events": 30,
        "train_positive_rate": 0.30,
        "validation_positive_rate": 0.35,
        "test_positive_rate": 0.36,
        "validation_ap_lift": 0.02,
        "test_ap_lift": 0.01,
        "validation_balanced_accuracy": 0.50,
        "test_balanced_accuracy": 0.49,
        "validation_independent_profit_factor": 1.20,
        "test_independent_profit_factor": 0.80,
        "validation_label_psi": 0.02,
        "test_label_psi": 0.03,
        "pass_gate": 0,
    }
    row.update(overrides)
    return row


def test_candidate_failure_reasons_include_train_economics_and_walkforward():
    args = phase175.parse_args([])

    reasons = phase175.candidate_failure_reasons(candidate(), args)

    assert "train_raw_economics_failed" in reasons
    assert "train_negative_expectancy_failed" in reasons
    assert "walkforward_pass_ratio_failed" in reasons
    assert "economic_gate_failed" in reasons


def test_fold_failure_reasons_include_transfer_metrics():
    args = phase175.parse_args([])

    reasons = phase175.fold_failure_reasons(fold(), args)

    assert "validation_ap_lift_failed" in reasons
    assert "test_ap_lift_failed" in reasons
    assert "test_raw_economics_failed" in reasons
    assert "fold_pass_gate_failed" in reasons


def test_build_fold_summary_counts_dominant_reason():
    args = phase175.parse_args([])
    rows = [fold(fold=1), fold(fold=2, validation_ap_lift=0.10, test_ap_lift=-0.02)]

    summary = phase175.build_fold_summary(rows, args)

    assert len(summary) == 1
    assert summary[0].folds == 2
    assert summary[0].pass_folds == 0
    assert summary[0].test_ap_lift_failed_folds == 2


def test_main_writes_attribution_outputs(tmp_path: Path):
    source = {
        "symbol": "XAUUSD",
        "timeframe": "1H",
        "spread_mode": "fixed",
        "spread_value": 0.4,
        "evaluated_regime_candidates": 1,
        "ready_regime_candidates": 0,
        "hybrid_regime_first_ready_gate": 0,
        "recommendation": "STOP_OR_REDESIGN_REQUIRED_NO_MODEL_TRAINING",
        "candidate_rows": [candidate()],
        "walkforward_rows": [fold(fold=1), fold(fold=2)],
    }
    source_path = tmp_path / "phase174.json"
    output_dir = tmp_path / "out"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    result = phase175.main([
        "--phase174-path", str(source_path),
        "--output-dir", str(output_dir),
    ])

    assert result == 0
    payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert payload["no_training_gate"] == 1
    assert payload["candidates_with_ready_gate"] == 0
    assert payload["route_decision"] == "ROUTE_NOT_CONFIRMED_STOP_OR_TARGET_DEFINITION_REDESIGN"
    assert (output_dir / "latest_candidate_failures.csv").exists()
    assert (output_dir / "latest_decision_matrix.csv").exists()


def test_decision_matrix_blocks_training():
    rows = phase175.build_decision_matrix(0, 0, phase175.build_candidate_failure_row(candidate(), phase175.parse_args([])))
    by_route = {row.route_id: row for row in rows}

    assert by_route["STOP_PHASE174_REGIME_TRAINING"].status == "MANDATORY"
    assert by_route["TRAIN_MODEL_NOW"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
