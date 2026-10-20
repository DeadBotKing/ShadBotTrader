"""Phase178A post-failure route reset helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_post_failure_research_route_reset as phase178


def test_current_lane_failed_when_all_recent_gates_block():
    gates = {
        "phase173_ready_gate": 0,
        "phase174_ready_gate": 0,
        "phase175_no_training_gate": 1,
        "phase176_redesign_required_gate": 1,
        "phase177_ready_gate": 0,
    }

    assert phase178.current_lane_failed(gates)


def test_route_decisions_select_higher_timeframe_and_block_training():
    gates = {
        "phase173_ready_gate": 0,
        "phase174_ready_gate": 0,
        "phase175_no_training_gate": 1,
        "phase176_redesign_required_gate": 1,
        "phase177_ready_gate": 0,
    }
    routes = phase178.build_route_decisions(gates, {"h1_median_spread_atr": 0.08347})
    by_route = {row.route_id: row for row in routes}

    assert by_route["FREEZE_CURRENT_1H_PIVOT_TARGET_ROUTE"].status == "MANDATORY"
    assert by_route["HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY"].status == "RECOMMENDED_NEXT_RESEARCH"
    assert by_route["TRAIN_CURRENT_TARGETS_OR_REGIMES"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"


def test_build_evidence_rows_uses_documented_defaults_when_logs_missing(tmp_path: Path):
    args = phase178.parse_args([
        "--phase170-path", str(tmp_path / "missing170.json"),
        "--phase173-path", str(tmp_path / "missing173.json"),
        "--phase174-path", str(tmp_path / "missing174.json"),
        "--phase175-path", str(tmp_path / "missing175.json"),
        "--phase176-path", str(tmp_path / "missing176.json"),
        "--phase177-path", str(tmp_path / "missing177.json"),
        "--assume-documented-failures", "1",
    ])

    evidence, gates, costs = phase178.build_evidence_rows(args)

    assert len(evidence) == 6
    assert gates["phase173_ready_gate"] == 0
    assert gates["phase175_no_training_gate"] == 1
    assert gates["phase176_redesign_required_gate"] == 1
    assert costs["broker_spread_median"] == 0.39


def test_main_writes_route_reset_outputs(tmp_path: Path):
    phase173 = {"target_learnability_ready_gate": 0, "learnable_families": 0, "selected_family_id": "CA3"}
    phase174 = {"hybrid_regime_first_ready_gate": 0, "ready_regime_candidates": 0, "evaluated_regime_candidates": 66}
    phase175 = {"no_training_gate": 1, "walkforward_pass_rows": 0, "walkforward_rows": 396, "candidates_with_ready_gate": 0}
    phase176 = {"target_definition_redesign_required_gate": 1, "route_decision": "CURRENT_TARGET_DEFINITIONS_REJECTED"}
    phase177 = {"target_family_redesign_ready_gate": 0, "ready_candidates": 0, "selected_family_id": "R3"}
    paths = []
    for idx, payload in enumerate((phase173, phase174, phase175, phase176, phase177), start=173):
        path = tmp_path / f"phase{idx}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    output_dir = tmp_path / "out"

    result = phase178.main([
        "--phase173-path", str(paths[0]),
        "--phase174-path", str(paths[1]),
        "--phase175-path", str(paths[2]),
        "--phase176-path", str(paths[3]),
        "--phase177-path", str(paths[4]),
        "--phase170-path", str(tmp_path / "missing170.json"),
        "--output-dir", str(output_dir),
    ])

    assert result == 0
    payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert payload["route_reset_ready_gate"] == 1
    assert payload["selected_next_research_route_id"] == "HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY"
    assert payload["phase177_ready_gate"] == 0
    assert (output_dir / "latest_route_decisions.csv").exists()


def test_recommended_plan_contains_phase179():
    plan = phase178.build_plan_rows()

    assert any(row.phase_id == "Phase179A" for row in plan)
