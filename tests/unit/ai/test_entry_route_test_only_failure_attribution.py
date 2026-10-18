"""Phase184A entry route test-only closure helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts import audit_entry_route_test_only_failure_attribution as phase184


def candidate(**overrides):
    row = {
        "candidate_id": "Q7",
        "label": "h4_pullback_no_buffer",
        "timeframe": "4H",
        "family_type": "pullback_rejection",
        "side_filter": "ALL",
        "train_events": 461,
        "validation_events": 140,
        "test_events": 113,
        "train_quality_pass_rate": 0.44,
        "validation_quality_pass_rate": 0.46,
        "test_quality_pass_rate": 0.59,
        "train_replay_profit_factor": 0.79,
        "validation_replay_profit_factor": 0.89,
        "test_replay_profit_factor": 1.55,
        "train_mean_score": -0.1,
        "validation_mean_score": -0.05,
        "test_mean_score": 0.21,
        "walkforward_folds": 4,
        "walkforward_pass_folds": 0,
        "walkforward_pass_ratio": 0.0,
        "quality_geometry_candidate_ready_gate": 0,
        "failure_reasons": '["mfe_mae_gate_failed", "walkforward_pass_ratio_failed"]',
    }
    row.update(overrides)
    return row


def test_candidate_closure_detects_test_only():
    args = phase184.parse_args([])
    rows = phase184.build_candidate_closure_rows({"candidate_rows": [candidate()]}, args)

    assert rows[0].test_only_gate == 1
    assert rows[0].narrow_candidate_gate == 0
    assert rows[0].closure_verdict == "TEST_ONLY_NOT_TRANSFERRED"
    assert rows[0].primary_failure_reason == "walkforward_transfer_failed"


def test_decision_matrix_recommends_freeze_when_no_narrow():
    args = phase184.parse_args([])
    rows = phase184.build_candidate_closure_rows({"candidate_rows": [candidate()]}, args)
    matrix = phase184.decision_matrix(rows)
    by_route = {row.route_id: row for row in matrix}

    assert by_route["ENTRY_GEOMETRY_MODEL_PREFLIGHT"].status == "BLOCKED"
    assert by_route["FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE"].status == "RECOMMENDED"
    assert by_route["ALLOW_ONE_NARROW_PHASE185A"].status == "BLOCKED"


def test_walkforward_closure_marks_test_fold_only_pattern():
    frame = pd.DataFrame(
        [
            {"candidate_id": "Q7", "timeframe": "4H", "family_type": "pullback", "side_filter": "ALL", "pass_gate": 0, "train_gate": 0, "validation_gate": 0, "test_gate": 1, "test_quality_pass_rate": 0.6},
            {"candidate_id": "Q7", "timeframe": "4H", "family_type": "pullback", "side_filter": "ALL", "pass_gate": 0, "train_gate": 0, "validation_gate": 0, "test_gate": 0, "test_quality_pass_rate": 0.4},
        ]
    )

    rows = phase184.walkforward_closure_rows(frame)

    assert rows[0].test_gate_pass_folds == 1
    assert rows[0].pass_folds == 0
    assert rows[0].test_only_fold_pattern_gate == 1


def test_run_writes_outputs(tmp_path: Path):
    replay = pd.DataFrame(
        [
            {"candidate_id": "Q7", "timeframe": "4H", "family_type": "pullback", "side_filter": "ALL", "side": "BUY", "trigger_timestamp": "2026-01-01T00:00:00Z", "quality_gate": 1, "replay_score_atr": 1.0},
            {"candidate_id": "Q7", "timeframe": "4H", "family_type": "pullback", "side_filter": "ALL", "side": "SELL", "trigger_timestamp": "2026-01-02T00:00:00Z", "quality_gate": 0, "replay_score_atr": -1.0},
        ]
    )
    replay_path = tmp_path / "replay.csv"
    replay.to_csv(replay_path, index=False)
    phase183 = {
        "source_symbol": "XAUUSD",
        "ready_candidates": 0,
        "candidate_rows": [candidate()],
        "output_replay_csv": str(replay_path),
    }
    phase183_path = tmp_path / "phase183.json"
    output_dir = tmp_path / "out"
    phase183_path.write_text(json.dumps(phase183), encoding="utf-8")

    report = phase184.run(["--phase183a-path", str(phase183_path), "--output-dir", str(output_dir)])

    assert report.no_training_gate == 1
    assert report.selected_decision == "FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE"
    assert (output_dir / "latest.json").exists()
    assert (output_dir / "latest_candidate_closure.csv").exists()
    assert (output_dir / "latest_decision_matrix.csv").exists()
    assert report.replay_month_rows
