"""Phase178A: post-failure research route reset decision matrix.

After Phase173A through Phase177A rejected the 1H broker-cost-aware pivot
family/target redesign lane, this diagnostic freezes that route and selects the
next research route. It does not train a model, does not build trading targets,
and does not approve paper/live trading.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_OUTPUT_DIR = Path("run_logs/post_failure_research_route_reset")


@dataclass(frozen=True)
class PhaseEvidenceRow:
    phase_id: str
    phase_name: str
    source_path: str
    source_status: str
    loaded: int
    key_gate_name: str
    key_gate_value: int
    summary: str
    operational_decision: str


@dataclass(frozen=True)
class RouteDecisionRow:
    route_id: str
    route_name: str
    status: str
    score: float
    rank: int
    evidence: str
    risk_note: str
    required_next_phase: str
    recommendation: str


@dataclass(frozen=True)
class RecommendedPlanRow:
    step_order: int
    phase_id: str
    title: str
    purpose: str
    allowed: str
    blocked: str
    expected_output: str


@dataclass(frozen=True)
class Phase178Report:
    symbol: str
    broker_spread_median: float
    broker_spread_p90: float
    broker_spread_p99: float
    h1_median_spread_atr: float
    phase173_ready_gate: int
    phase174_ready_gate: int
    phase175_no_training_gate: int
    phase176_redesign_required_gate: int
    phase177_ready_gate: int
    current_1h_pivot_target_lane_status: str
    route_reset_ready_gate: int
    selected_next_research_route_id: str
    selected_next_research_route_name: str
    selected_required_phase: str
    selected_route_score: float
    phase_evidence_rows: list[dict[str, Any]]
    route_decision_rows: list[dict[str, Any]]
    recommended_plan_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_phase_evidence_csv: str
    output_route_decisions_csv: str
    output_recommended_plan_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a post-failure research route reset decision matrix after Phase173A-177A failures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--phase170-path", default="run_logs/broker_spread_capture/latest.json")
    parser.add_argument("--phase173-path", default="run_logs/broker_cost_aware_1h_target_learnability/latest.json")
    parser.add_argument("--phase174-path", default="run_logs/hybrid_regime_first_target_redesign/latest.json")
    parser.add_argument("--phase175-path", default="run_logs/hybrid_regime_walkforward_failure_attribution/latest.json")
    parser.add_argument("--phase176-path", default="run_logs/target_definition_walkforward_root_cause_redesign/latest.json")
    parser.add_argument("--phase177-path", default="run_logs/walkforward_target_family_redesign_candidates/latest.json")
    parser.add_argument("--assume-documented-failures", choices=("0", "1"), default="1")
    parser.add_argument("--manual-broker-spread-median", type=float, default=0.39)
    parser.add_argument("--manual-broker-spread-p90", type=float, default=0.40)
    parser.add_argument("--manual-broker-spread-p99", type=float, default=0.41)
    parser.add_argument("--manual-h1-median-spread-atr", type=float, default=0.08347)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase178A post-failure research route reset decision matrix")
    return parser.parse_args(argv)


def read_json(path_text: str) -> tuple[dict[str, Any] | None, str]:
    path = Path(path_text)
    if not path.exists():
        return None, "MISSING"
    try:
        return json.loads(path.read_text(encoding="utf-8")), "LOADED"
    except Exception as error:
        return {"_load_error": f"{type(error).__name__}: {error}"}, "ERROR"


def int_gate(payload: Mapping[str, Any] | None, key: str, default: int) -> int:
    if not payload:
        return int(default)
    try:
        return int(float(payload.get(key, default)))
    except (TypeError, ValueError):
        return int(default)


def float_value(payload: Mapping[str, Any] | None, key: str, default: float) -> float:
    if not payload:
        return float(default)
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def build_evidence_rows(args: argparse.Namespace) -> tuple[list[PhaseEvidenceRow], dict[str, int], dict[str, float]]:
    assume = str(args.assume_documented_failures) != "0"
    phase170, status170 = read_json(args.phase170_path)
    phase173, status173 = read_json(args.phase173_path)
    phase174, status174 = read_json(args.phase174_path)
    phase175, status175 = read_json(args.phase175_path)
    phase176, status176 = read_json(args.phase176_path)
    phase177, status177 = read_json(args.phase177_path)

    default_failed = 0 if assume else 0
    phase173_gate = int_gate(phase173, "target_learnability_ready_gate", default_failed)
    phase174_gate = int_gate(phase174, "hybrid_regime_first_ready_gate", default_failed)
    phase175_no_training = int_gate(phase175, "no_training_gate", 1 if assume else 0)
    phase176_redesign = int_gate(phase176, "target_definition_redesign_required_gate", 1 if assume else 0)
    phase177_gate = int_gate(phase177, "target_family_redesign_ready_gate", default_failed)

    broker_spread_median = float_value(phase170, "spread_price_median", float(args.manual_broker_spread_median))
    broker_spread_p90 = float_value(phase170, "spread_price_p90", float(args.manual_broker_spread_p90))
    broker_spread_p99 = float_value(phase170, "spread_price_p99", float(args.manual_broker_spread_p99))
    h1_median_spread_atr = float(args.manual_h1_median_spread_atr)
    if phase170:
        rows = phase170.get("timeframe_cost_rows") or phase170.get("timeframe_cost") or []
        if isinstance(rows, list):
            for row in rows:
                if str(row.get("timeframe", "")).upper() in {"1H", "H1"}:
                    h1_median_spread_atr = float_value(row, "median_spread_atr", h1_median_spread_atr)
                    break

    rows = [
        PhaseEvidenceRow(
            phase_id="Phase170A",
            phase_name="Broker spread capture / cost data",
            source_path=str(args.phase170_path),
            source_status=status170,
            loaded=int(status170 == "LOADED"),
            key_gate_name="broker_cost_reality_gate",
            key_gate_value=int_gate(phase170, "broker_cost_reality_gate", 1 if assume else 0),
            summary=f"broker spread median={broker_spread_median:.4f}, p90={broker_spread_p90:.4f}, p99={broker_spread_p99:.4f}; H1 median spread/ATR≈{h1_median_spread_atr:.5f}",
            operational_decision="Use fixed spread around 0.4 for any future XAUUSD 1H+ research.",
        ),
        PhaseEvidenceRow(
            phase_id="Phase173A",
            phase_name="Broker-cost-aware 1H target learnability",
            source_path=str(args.phase173_path),
            source_status=status173,
            loaded=int(status173 == "LOADED"),
            key_gate_name="target_learnability_ready_gate",
            key_gate_value=phase173_gate,
            summary=f"learnable_families={int_gate(phase173, 'learnable_families', 0)}; selected={str((phase173 or {}).get('selected_family_id', 'documented_failed'))}",
            operational_decision="Do not train CA1/CA3/CA2 broad target families.",
        ),
        PhaseEvidenceRow(
            phase_id="Phase174A",
            phase_name="Hybrid/regime-first target redesign",
            source_path=str(args.phase174_path),
            source_status=status174,
            loaded=int(status174 == "LOADED"),
            key_gate_name="hybrid_regime_first_ready_gate",
            key_gate_value=phase174_gate,
            summary=f"ready_regime_candidates={int_gate(phase174, 'ready_regime_candidates', 0)}; evaluated={int_gate(phase174, 'evaluated_regime_candidates', 66 if assume else 0)}",
            operational_decision="Do not train regime-filtered CA1/CA3/CA2 targets.",
        ),
        PhaseEvidenceRow(
            phase_id="Phase175A",
            phase_name="Hybrid/regime walk-forward failure attribution",
            source_path=str(args.phase175_path),
            source_status=status175,
            loaded=int(status175 == "LOADED"),
            key_gate_name="no_training_gate",
            key_gate_value=phase175_no_training,
            summary=f"walkforward_pass_rows={int_gate(phase175, 'walkforward_pass_rows', 0)}/{int_gate(phase175, 'walkforward_rows', 396 if assume else 0)}; candidates_with_ready_gate={int_gate(phase175, 'candidates_with_ready_gate', 0)}",
            operational_decision="Failure attribution points to target/regime instability, not model capacity.",
        ),
        PhaseEvidenceRow(
            phase_id="Phase176A",
            phase_name="Target-definition root-cause audit",
            source_path=str(args.phase176_path),
            source_status=status176,
            loaded=int(status176 == "LOADED"),
            key_gate_name="target_definition_redesign_required_gate",
            key_gate_value=phase176_redesign,
            summary=f"route_decision={str((phase176 or {}).get('route_decision', 'CURRENT_TARGET_DEFINITIONS_REJECTED'))}",
            operational_decision="Freeze CA1/CA3/CA2 target definitions as failed diagnostics.",
        ),
        PhaseEvidenceRow(
            phase_id="Phase177A",
            phase_name="Walk-forward target-family redesign candidates",
            source_path=str(args.phase177_path),
            source_status=status177,
            loaded=int(status177 == "LOADED"),
            key_gate_name="target_family_redesign_ready_gate",
            key_gate_value=phase177_gate,
            summary=f"ready_candidates={int_gate(phase177, 'ready_candidates', 0)}; selected={str((phase177 or {}).get('selected_family_id', 'documented_failed'))}",
            operational_decision="Do not train R1-R8 redesigned target candidates.",
        ),
    ]
    gates = {
        "phase173_ready_gate": phase173_gate,
        "phase174_ready_gate": phase174_gate,
        "phase175_no_training_gate": phase175_no_training,
        "phase176_redesign_required_gate": phase176_redesign,
        "phase177_ready_gate": phase177_gate,
    }
    costs = {
        "broker_spread_median": broker_spread_median,
        "broker_spread_p90": broker_spread_p90,
        "broker_spread_p99": broker_spread_p99,
        "h1_median_spread_atr": h1_median_spread_atr,
    }
    return rows, gates, costs


def current_lane_failed(gates: Mapping[str, int]) -> bool:
    return (
        int(gates.get("phase173_ready_gate", 0)) == 0
        and int(gates.get("phase174_ready_gate", 0)) == 0
        and int(gates.get("phase175_no_training_gate", 0)) == 1
        and int(gates.get("phase176_redesign_required_gate", 0)) == 1
        and int(gates.get("phase177_ready_gate", 0)) == 0
    )


def build_route_decisions(gates: Mapping[str, int], costs: Mapping[str, float]) -> list[RouteDecisionRow]:
    lane_failed = current_lane_failed(gates)
    h1_cost = float(costs.get("h1_median_spread_atr", 0.08347))
    higher_tf_score = 88.0 if lane_failed and h1_cost <= 0.12 else 72.0
    rows = [
        RouteDecisionRow(
            route_id="FREEZE_CURRENT_1H_PIVOT_TARGET_ROUTE",
            route_name="Freeze current broker-cost-aware 1H pivot target-family lane",
            status="MANDATORY" if lane_failed else "REVIEW_REQUIRED",
            score=100.0 if lane_failed else 70.0,
            rank=1,
            evidence="Phase173A-177A ready gates are 0; redesigned target candidates also failed.",
            risk_note="Continuing with small target tweaks risks overfitting validation/test pockets.",
            required_next_phase="None — this is an enacted stop decision",
            recommendation="Freeze CA1/CA3/CA2 and R1-R8 targets as failed diagnostics.",
        ),
        RouteDecisionRow(
            route_id="HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY",
            route_name="Audit higher-timeframe 4H/1D broker-cost feasibility",
            status="RECOMMENDED_NEXT_RESEARCH",
            score=higher_tf_score,
            rank=2,
            evidence="5M/1H pivot-target lanes failed walk-forward; captured broker spread is fixed≈0.4, so higher timeframes may reduce cost/noise ratio.",
            risk_note="This is only a feasibility audit; no model training or paper/live approval.",
            required_next_phase="Phase179A — 4H/1D broker-cost feasibility and target pre-audit",
            recommendation="Run a diagnostic-only 4H/1D cost/target feasibility audit before any model design.",
        ),
        RouteDecisionRow(
            route_id="NON_PIVOT_EVENT_TARGET_ROUTE",
            route_name="Explore non-pivot event target families",
            status="SECONDARY_RESEARCH",
            score=73.0,
            rank=3,
            evidence="Repeated pivot-family target definitions failed; non-pivot event definitions may avoid the same geometry instability.",
            risk_note="Must be scoped as target audit only, not deep model training.",
            required_next_phase="Future diagnostic target-definition audit if owner rejects higher-timeframe route",
            recommendation="Keep as secondary route after higher-timeframe feasibility.",
        ),
        RouteDecisionRow(
            route_id="BROKER_SESSION_COST_DATA_EXTENSION",
            route_name="Extend broker spread/session cost sampling",
            status="SUPPORTING_RESEARCH",
            score=64.0,
            rank=4,
            evidence="Phase170A captured 121 spread samples; more sessions can support future feasibility audits.",
            risk_note="Cost data alone does not create a strategy.",
            required_next_phase="Optional cost-data extension phase",
            recommendation="Use as supporting evidence, not as the primary route.",
        ),
        RouteDecisionRow(
            route_id="PAUSE_FOR_MANUAL_REVIEW",
            route_name="Pause research lane for manual review",
            status="VALID_OWNER_OPTION",
            score=60.0,
            rank=5,
            evidence="Five consecutive diagnostics rejected the current 1H pivot target lane.",
            risk_note="Pausing may be preferable to accumulating low-quality experiments.",
            required_next_phase="None",
            recommendation="Valid option if owner wants to stop automated research expansion.",
        ),
        RouteDecisionRow(
            route_id="TRAIN_CURRENT_TARGETS_OR_REGIMES",
            route_name="Train current CA/R target families or regimes",
            status="BLOCKED",
            score=0.0,
            rank=6,
            evidence="No ready target after Phase173A-177A.",
            risk_note="Would violate gates and likely overfit failed pockets.",
            required_next_phase="Blocked",
            recommendation="Do not train.",
        ),
        RouteDecisionRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=7,
            evidence="No trade-ready candidate; no production approval.",
            risk_note="Would violate project safety gates.",
            required_next_phase="Blocked",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]
    return sorted(rows, key=lambda row: row.rank)


def build_plan_rows() -> list[RecommendedPlanRow]:
    return [
        RecommendedPlanRow(
            step_order=1,
            phase_id="Phase178A",
            title="Freeze failed 1H pivot target-family lane",
            purpose="Record the stop decision for CA1/CA3/CA2 and R1-R8 targets.",
            allowed="Documentation and decision matrix only.",
            blocked="No training, no paper/live, no gate relaxation.",
            expected_output="run_logs/post_failure_research_route_reset/latest.json",
        ),
        RecommendedPlanRow(
            step_order=2,
            phase_id="Phase179A",
            title="4H/1D broker-cost feasibility and target pre-audit",
            purpose="Check whether higher timeframes reduce cost/noise enough to justify a new target-family audit.",
            allowed="Dataset health, spread/ATR, event density, label stability, raw economics, walk-forward target diagnostics.",
            blocked="No model training, no paper/live.",
            expected_output="run_logs/higher_timeframe_cost_feasibility/latest.json",
        ),
        RecommendedPlanRow(
            step_order=3,
            phase_id="Owner gate",
            title="Owner reviews Phase179A before any model-design phase",
            purpose="Prevent the project from drifting into unapproved architecture or training work.",
            allowed="Choose next diagnostic route.",
            blocked="Production or paper/live approval without explicit gates.",
            expected_output="Owner decision in docs/WORKLOG.md and docs/PROJECT_OWNER_MAP.html",
        ),
    ]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase178Report) -> str:
    route_rows = "".join(
        f"<tr><td>{html.escape(str(row['route_id']))}</td><td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['score']):.1f}</td><td>{html.escape(str(row['required_next_phase']))}</td>"
        f"<td>{html.escape(str(row['recommendation']))}</td></tr>"
        for row in report.route_decision_rows
    )
    evidence_rows = "".join(
        f"<tr><td>{html.escape(str(row['phase_id']))}</td><td>{html.escape(str(row['source_status']))}</td>"
        f"<td>{html.escape(str(row['key_gate_name']))}={int(row['key_gate_value'])}</td>"
        f"<td>{html.escape(str(row['operational_decision']))}</td></tr>"
        for row in report.phase_evidence_rows
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:12px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase178A post-failure research route reset. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Selected next route</h2><pre>{html.escape(json.dumps({
        'selected_next_research_route_id': report.selected_next_research_route_id,
        'selected_required_phase': report.selected_required_phase,
        'route_reset_ready_gate': report.route_reset_ready_gate,
        'current_1h_pivot_target_lane_status': report.current_1h_pivot_target_lane_status,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Routes</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Required next</th><th>Recommendation</th></tr></thead><tbody>{route_rows}</tbody></table></section>
<section class="card"><h2>Evidence</h2><table><thead><tr><th>Phase</th><th>Source</th><th>Gate</th><th>Decision</th></tr></thead><tbody>{evidence_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE178A POST-FAILURE RESEARCH ROUTE RESET")
        print("=" * 74)
        evidence_rows, gates, costs = build_evidence_rows(args)
        route_rows = build_route_decisions(gates, costs)
        plan_rows = build_plan_rows()
        selected = next(row for row in route_rows if row.route_id == "HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY")
        lane_status = "FROZEN_FAILED_DIAGNOSTIC" if current_lane_failed(gates) else "REVIEW_REQUIRED"
        output_evidence = output_dir / "latest_phase_evidence.csv"
        output_routes = output_dir / "latest_route_decisions.csv"
        output_plan = output_dir / "latest_recommended_plan.csv"
        write_csv(output_evidence, [asdict(row) for row in evidence_rows])
        write_csv(output_routes, [asdict(row) for row in route_rows])
        write_csv(output_plan, [asdict(row) for row in plan_rows])
        report = Phase178Report(
            symbol=str(args.symbol),
            broker_spread_median=float(costs["broker_spread_median"]),
            broker_spread_p90=float(costs["broker_spread_p90"]),
            broker_spread_p99=float(costs["broker_spread_p99"]),
            h1_median_spread_atr=float(costs["h1_median_spread_atr"]),
            phase173_ready_gate=int(gates["phase173_ready_gate"]),
            phase174_ready_gate=int(gates["phase174_ready_gate"]),
            phase175_no_training_gate=int(gates["phase175_no_training_gate"]),
            phase176_redesign_required_gate=int(gates["phase176_redesign_required_gate"]),
            phase177_ready_gate=int(gates["phase177_ready_gate"]),
            current_1h_pivot_target_lane_status=lane_status,
            route_reset_ready_gate=int(lane_status == "FROZEN_FAILED_DIAGNOSTIC"),
            selected_next_research_route_id=selected.route_id,
            selected_next_research_route_name=selected.route_name,
            selected_required_phase=selected.required_next_phase,
            selected_route_score=float(selected.score),
            phase_evidence_rows=[asdict(row) for row in evidence_rows],
            route_decision_rows=[asdict(row) for row in route_rows],
            recommended_plan_rows=[asdict(row) for row in plan_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_phase_evidence_csv=str(output_evidence),
            output_route_decisions_csv=str(output_routes),
            output_recommended_plan_csv=str(output_plan),
            production_status="BLOCKED — Phase178A route reset decision matrix only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase178A route reset complete")
        print(f"  lane status     : {report.current_1h_pivot_target_lane_status}")
        print(f"  selected route  : {report.selected_next_research_route_id}")
        print(f"  required phase  : {report.selected_required_phase}")
        print(f"  output          : {report.output_json}")
        print(f"  elapsed         : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
