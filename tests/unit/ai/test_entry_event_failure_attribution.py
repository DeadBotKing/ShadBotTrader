"""Phase182A entry-event failure attribution helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts import audit_entry_event_failure_attribution as phase182


def family(**overrides):
    row = {
        "timeframe": "1D",
        "family_id": "E3_CONTINUATION",
        "family_type": "continuation",
        "train_events": 300,
        "validation_events": 60,
        "test_events": 70,
        "train_quality_pass_rate": 0.31,
        "validation_quality_pass_rate": 0.29,
        "test_quality_pass_rate": 0.44,
        "train_replay_profit_factor": 0.76,
        "validation_replay_profit_factor": 0.68,
        "test_replay_profit_factor": 1.28,
        "train_feature_smd": 1.4,
        "validation_feature_smd": 1.5,
        "test_feature_smd": 1.3,
        "walkforward_folds": 4,
        "walkforward_pass_folds": 0,
        "walkforward_pass_ratio": 0.0,
        "density_gate": 1,
        "direction_balance_gate": 1,
        "temporal_stability_gate": 1,
        "mfe_mae_gate": 0,
        "replay_gate": 0,
        "feature_separability_gate": 1,
        "cost_gate": 1,
        "entry_family_ready_gate": 0,
        "mfe_atr": 1.2,
        "mae_atr": 0.75,
        "failure_reasons": '["mfe_mae_gate_failed", "replay_gate_failed", "walkforward_pass_ratio_failed"]',
    }
    row.update(overrides)
    return row


def replay_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timeframe": "1D",
                "family_id": "E3_CONTINUATION",
                "family_type": "continuation",
                "side": "BUY",
                "setup_row": 10,
                "trigger_row": 11,
                "quality_gate": 1,
                "mfe_atr": 1.4,
                "mae_atr": 0.4,
                "replay_score_atr": 1.2,
                "replay_outcome": "quality_pass_mfe_first",
            },
            {
                "timeframe": "1D",
                "family_id": "E3_CONTINUATION",
                "family_type": "continuation",
                "side": "BUY",
                "setup_row": 20,
                "trigger_row": 22,
                "quality_gate": 0,
                "mfe_atr": 0.5,
                "mae_atr": 1.0,
                "replay_score_atr": -0.75,
                "replay_outcome": "quality_fail_mae_first",
            },
            {
                "timeframe": "1D",
                "family_id": "E3_CONTINUATION",
                "family_type": "continuation",
                "side": "SELL",
                "setup_row": 30,
                "trigger_row": 31,
                "quality_gate": 0,
                "mfe_atr": 0.7,
                "mae_atr": 0.8,
                "replay_score_atr": -0.75,
                "replay_outcome": "quality_fail_mae_first",
            },
        ]
    )


def test_family_attribution_marks_near_miss():
    args = phase182.parse_args([])
    rows = phase182.build_family_attribution_rows({"family_rows": [family()]}, args)

    assert rows[0].near_miss_gate == 1
    assert rows[0].primary_failure_reason == "mfe_mae_gate_failed"
    assert rows[0].attribution_bucket == "QUALITY_AND_REPLAY_FAILURE"


def test_side_and_quality_geometry_attribution():
    replay = replay_frame()
    side_rows = phase182.side_attribution_rows(replay)
    quality_rows = phase182.quality_geometry_rows({"family_rows": [family()]}, replay)

    assert side_rows
    assert any(row.side == "BUY" for row in side_rows)
    assert quality_rows[0].triggered_events == 3
    assert quality_rows[0].current_mfe_atr == 1.2
    assert quality_rows[0].quality_geometry_verdict


def test_run_writes_outputs(tmp_path: Path):
    output_replay = tmp_path / "replay.csv"
    output_wf = tmp_path / "wf.csv"
    replay_frame().to_csv(output_replay, index=False)
    pd.DataFrame(
        [
            {
                "timeframe": "1D",
                "family_id": "E3_CONTINUATION",
                "family_type": "continuation",
                "fold": 1,
                "pass_gate": 0,
                "train_gate": 0,
                "validation_gate": 0,
                "test_gate": 0,
                "test_quality_pass_rate": 0.3,
                "test_event_rate": 0.08,
            }
        ]
    ).to_csv(output_wf, index=False)
    phase181b = {
        "symbol": "XAUUSD",
        "timeframes": ["1D"],
        "ready_families": 0,
        "entry_event_discovery_ready_gate": 0,
        "family_rows": [family()],
        "output_replay_csv": str(output_replay),
        "output_walkforward_csv": str(output_wf),
    }
    phase181b_path = tmp_path / "phase181b.json"
    output_dir = tmp_path / "out"
    phase181b_path.write_text(json.dumps(phase181b), encoding="utf-8")

    report = phase182.run(["--phase181b-path", str(phase181b_path), "--output-dir", str(output_dir)])

    assert report.no_training_gate == 1
    assert report.near_miss_families == 1
    assert report.selected_next_route_id == "ENTRY_QUALITY_GEOMETRY_REDESIGN"
    assert (output_dir / "latest_family_attribution.csv").exists()
    assert (output_dir / "latest_quality_geometry.csv").exists()
    assert (output_dir / "latest_decision_matrix.csv").exists()


def test_decision_matrix_blocks_training():
    args = phase182.parse_args([])
    families = phase182.build_family_attribution_rows({"family_rows": [family()]}, args)
    matrix = phase182.decision_matrix(families)
    by_route = {row.route_id: row for row in matrix}

    assert by_route["ENTRY_EVENT_MODEL_TRAINING"].status == "BLOCKED"
    assert by_route["ENTRY_QUALITY_GEOMETRY_REDESIGN"].status == "RECOMMENDED_DIAGNOSTIC"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
