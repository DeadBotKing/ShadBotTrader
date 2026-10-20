"""Phase171A research route redesign decision matrix helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_research_route_redesign_decision_matrix as phase171


def test_h1_spread_atr_from_phase170_reads_timeframe_rows():
    data = {"timeframe_cost_rows": [{"timeframe": "1H", "median_spread_atr_median": 0.083}]}

    assert phase171.h1_spread_atr_from_phase170(data, 1.0) == 0.083
    assert phase171.h1_spread_atr_from_phase170({}, 0.5) == 0.5


def test_documented_route_reset_uses_phase168_failure():
    args = phase171.parse_args([])
    phase168 = {"confirmation_pass_gate": 0}

    status = phase171.documented_route_reset(args, phase168, None, None)

    assert status == "CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED"


def test_build_matrix_blocks_training_and_recommends_research():
    args = phase171.parse_args([])

    rows, criteria, plan = phase171.build_matrix(
        args,
        cost_status="VERIFIED_SAMPLE_AVAILABLE",
        route_reset_status="CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED",
        h1_spread_atr=0.08,
    )

    training = next(row for row in rows if row.route_id == "TRAIN_CURRENT_1H_LOCKED_RULE")
    recommended = [row for row in rows if row.status == "RECOMMENDED_RESEARCH"]
    assert training.status == "BLOCKED"
    assert recommended
    assert criteria
    assert plan


def test_phase_sources_and_evidence_snapshots(tmp_path):
    root = tmp_path / "run_logs"
    (root / "broker_spread_capture").mkdir(parents=True)
    (root / "pivot_1h_predeclared_filter_confirmation").mkdir(parents=True)
    (root / "broker_spread_capture" / "latest.json").write_text(
        json.dumps({"broker_cost_reality_gate": 1, "spread_price_median": 0.39}), encoding="utf-8"
    )
    (root / "pivot_1h_predeclared_filter_confirmation" / "latest.json").write_text(
        json.dumps({"confirmation_pass_gate": 0, "recommendation": "STOP"}), encoding="utf-8"
    )
    args = phase171.parse_args(
        [
            "--phase170-path",
            str(root / "broker_spread_capture" / "latest.json"),
            "--phase168-path",
            str(root / "pivot_1h_predeclared_filter_confirmation" / "latest.json"),
        ]
    )

    phase170 = phase171.load_json(args.phase170_path)
    phase168 = phase171.load_json(args.phase168_path)
    evidence = phase171.evidence_snapshots(args, phase170, phase168, None, None)

    assert evidence[0].status == "FOUND"
    assert evidence[1].status == "FOUND"


def test_broker_cost_status():
    assert phase171.broker_cost_status({"broker_cost_reality_gate": 1}) == "VERIFIED_SAMPLE_AVAILABLE"
    assert phase171.broker_cost_status(None) == "MISSING_PHASE170_USING_DOCUMENTED_MANUAL_VALUES"
