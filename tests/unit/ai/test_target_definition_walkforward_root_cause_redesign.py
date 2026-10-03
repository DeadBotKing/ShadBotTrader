"""Phase176A target-definition walk-forward root-cause helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_target_definition_walkforward_root_cause_redesign as phase176


def candidate(family_id="CA1_BRK_MID", regime_rule_id="WIDTH_GE_Q75", **overrides):
    row = {
        "family_id": family_id,
        "family_label": "cost_breakout_mid",
        "regime_rule_id": regime_rule_id,
        "regime_label": "recent_width_top_quartile",
        "train_events": 100,
        "validation_events": 30,
        "test_events": 30,
        "train_positive_rate": 0.30,
        "validation_positive_rate": 0.35,
        "test_positive_rate": 0.36,
        "validation_ap_lift": 0.08,
        "test_ap_lift": 0.06,
        "validation_balanced_accuracy": 0.56,
        "test_balanced_accuracy": 0.50,
        "train_independent_profit_factor": 0.90,
        "validation_independent_profit_factor": 1.20,
        "test_independent_profit_factor": 1.10,
        "train_mean_atr_score": -0.02,
        "validation_mean_atr_score": 0.10,
        "test_mean_atr_score": 0.05,
        "class_balance_gate": 1,
        "economic_gate": 0,
        "static_learnability_gate": 0,
        "walkforward_learnability_gate": 0,
        "regime_candidate_ready_gate": 0,
    }
    row.update(overrides)
    return row


def failure(family_id="CA1_BRK_MID", regime_rule_id="WIDTH_GE_Q75", **overrides):
    row = {
        "family_id": family_id,
        "regime_rule_id": regime_rule_id,
        "failure_reasons": json.dumps([
            "static_learnability_gate_failed",
            "walkforward_pass_ratio_failed",
            "train_negative_expectancy_failed",
        ]),
    }
    row.update(overrides)
    return row


def fold(family_id="CA1_BRK_MID", regime_rule_id="WIDTH_GE_Q75", **overrides):
    row = {
        "family_id": family_id,
        "family_label": "cost_breakout_mid",
        "regime_rule_id": regime_rule_id,
        "regime_label": "recent_width_top_quartile",
        "fold": 1,
        "pass_gate": 0,
    }
    row.update(overrides)
    return row


def test_regime_axis_classification():
    assert phase176.regime_axis("BUY_ONLY") == "side"
    assert phase176.regime_axis("ACTIVE_UTC_07_17") == "session"
    assert phase176.regime_axis("WIDTH_GE_Q75") == "range_width"
    assert phase176.regime_axis("UNKNOWN") == "other"


def test_build_axis_rows_rejects_zero_walkforward_axis():
    candidates = [candidate(), candidate(regime_rule_id="ALL")]
    failures = [failure(), failure(regime_rule_id="ALL")]
    folds = [fold(), fold(regime_rule_id="ALL")]

    rows = phase176.build_axis_rows(candidates, failures, folds)
    family_row = next(row for row in rows if row.axis_type == "family" and row.axis_value == "CA1_BRK_MID")

    assert family_row.candidates == 2
    assert family_row.total_walkforward_pass_folds == 0
    assert family_row.verdict == "REJECTED_WALKFORWARD_ZERO"
    assert family_row.top_failure_reason == "static_learnability_gate_failed"


def test_build_target_definition_rows_maps_family_spec():
    axis_rows = phase176.build_axis_rows([candidate()], [failure()], [fold()])

    target_rows = phase176.build_target_definition_rows(axis_rows)
    row = next(item for item in target_rows if item.family_id == "CA1_BRK_MID")

    assert row.geometry_profile == "mid_zone_rw24"
    assert row.hold_bars == 24
    assert row.walkforward_pass_ratio == 0.0
    assert "Freeze CA1_BRK_MID" in row.redesign_implication


def test_build_hypotheses_supports_target_mismatch():
    axis_rows = phase176.build_axis_rows([candidate()], [failure()], [fold()])
    phase175 = {
        "walkforward_global_pass_ratio": 0.0,
        "candidates_with_static_learnability_gate": 0,
        "failure_reason_rows": [
            {"scope": "candidate", "reason": "train_negative_expectancy_failed", "ratio": 0.86},
            {"scope": "candidate", "reason": "test_balanced_accuracy_failed", "ratio": 0.95},
            {"scope": "walkforward_fold", "reason": "test_raw_economics_failed", "ratio": 0.61},
            {"scope": "walkforward_fold", "reason": "test_density_failed", "ratio": 0.29},
        ],
    }

    hypotheses = phase176.build_hypotheses(axis_rows, phase175)
    by_id = {row.hypothesis_id: row for row in hypotheses}

    assert by_id["H1_TARGET_DEFINITION_MISMATCH"].status == "SUPPORTED"
    assert by_id["H2_TRAIN_EXPECTANCY_INSTABILITY"].status == "SUPPORTED"
    assert by_id["H3_CLASSIFIER_SIGNAL_NOT_STABLE"].status == "SUPPORTED"


def test_main_writes_outputs(tmp_path: Path):
    phase174 = {
        "symbol": "XAUUSD",
        "timeframe": "1H",
        "spread_mode": "fixed",
        "spread_value": 0.4,
        "candidate_rows": [candidate()],
        "walkforward_rows": [fold()],
    }
    phase175 = {
        "walkforward_pass_rows": 0,
        "walkforward_global_pass_ratio": 0.0,
        "candidates_with_static_learnability_gate": 0,
        "candidates_with_walkforward_gate": 0,
        "candidates_with_ready_gate": 0,
        "failure_reason_rows": [
            {"scope": "candidate", "reason": "train_negative_expectancy_failed", "ratio": 0.86},
            {"scope": "candidate", "reason": "test_balanced_accuracy_failed", "ratio": 0.95},
        ],
        "candidate_failure_rows": [failure()],
    }
    phase174_path = tmp_path / "phase174.json"
    phase175_path = tmp_path / "phase175.json"
    output_dir = tmp_path / "out"
    phase174_path.write_text(json.dumps(phase174), encoding="utf-8")
    phase175_path.write_text(json.dumps(phase175), encoding="utf-8")

    result = phase176.main([
        "--phase174-path", str(phase174_path),
        "--phase175-path", str(phase175_path),
        "--output-dir", str(output_dir),
    ])

    assert result == 0
    payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert payload["target_definition_redesign_required_gate"] == 1
    assert payload["direct_training_blocked_gate"] == 1
    assert payload["paper_live_blocked_gate"] == 1
    assert (output_dir / "latest_target_definitions.csv").exists()
    assert (output_dir / "latest_redesign_hypotheses.csv").exists()


def test_decision_matrix_blocks_training_and_paper_live():
    rows = phase176.build_decision_matrix()
    by_route = {row.route_id: row for row in rows}

    assert by_route["FREEZE_PHASE173_174_TARGETS"].status == "MANDATORY"
    assert by_route["TRAIN_MODEL_NOW"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
