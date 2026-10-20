"""Phase171A: research route redesign decision matrix.

The pivot research lane rejected the current 5M and 1H locked rule routes. This
phase turns those results into an owner-facing decision matrix for what may be
researched next. It does not train models, does not search trading parameters,
and does not approve paper/live trading.
"""

# ruff: noqa: E402,E501

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

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT_DIR = Path("run_logs/research_route_redesign_decision_matrix")


@dataclass(frozen=True)
class EvidenceSnapshot:
    phase: str
    path: str
    status: str
    summary: str


@dataclass(frozen=True)
class DecisionCriterionRow:
    route_id: str
    criterion: str
    score: float
    max_score: float
    rationale: str


@dataclass(frozen=True)
class RouteDecisionMatrixRow:
    route_id: str
    route_name: str
    status: str
    total_score: float
    rank: int
    decision: str
    core_rationale: str
    allowed_next_action: str
    blocked_actions: str
    required_phase: str


@dataclass(frozen=True)
class RecommendedPlanRow:
    step: int
    phase: str
    objective: str
    allowed_actions: str
    blocked_actions: str
    success_gate: str
    failure_action: str


@dataclass(frozen=True)
class Phase171Report:
    symbol: str
    generated_at_utc: str
    phase170_path: str
    phase168_path: str
    phase166_path: str
    broker_cost_status: str
    broker_spread_median: float
    broker_spread_p90: float
    broker_spread_p99: float
    h1_median_spread_atr: float
    route_reset_status: str
    selected_research_route_id: str
    selected_research_route_name: str
    selected_required_phase: str
    production_status: str
    evidence_snapshots: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    criteria_rows: list[dict[str, Any]]
    recommended_plan_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_decision_matrix_csv: str
    output_criteria_csv: str
    output_recommended_plan_csv: str
    output_evidence_csv: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an owner-facing research route redesign decision matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--phase170-path", default="run_logs/broker_spread_capture/latest.json")
    parser.add_argument("--phase168-path", default="run_logs/pivot_1h_predeclared_filter_confirmation/latest.json")
    parser.add_argument("--phase166-path", default="run_logs/pivot_1h_locked_candidate_walk_forward/latest.json")
    parser.add_argument("--phase162-path", default="run_logs/pivot_bottom_buy_execution_gap/latest.json")
    parser.add_argument("--assume-documented-route-decisions", choices=("0", "1"), default="1")
    parser.add_argument("--manual-broker-spread-median", type=float, default=0.39)
    parser.add_argument("--manual-broker-spread-p90", type=float, default=0.40)
    parser.add_argument("--manual-broker-spread-p99", type=float, default=0.41)
    parser.add_argument("--manual-h1-median-spread-atr", type=float, default=0.08347)
    parser.add_argument("--max-production-risk", choices=("strict", "normal"), default="strict")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase171A research route redesign decision matrix")
    return parser.parse_args(argv)


def load_json(path: str | Path) -> Mapping[str, Any] | None:
    candidate = Path(path)
    if not candidate.exists():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        return result if np.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def metric_summary(data: Mapping[str, Any] | None, keys: Sequence[str]) -> str:
    if data is None:
        return "missing"
    return json.dumps({key: data.get(key) for key in keys if key in data}, ensure_ascii=False, sort_keys=True)


def h1_spread_atr_from_phase170(data: Mapping[str, Any] | None, default: float) -> float:
    if not data:
        return default
    for row in data.get("timeframe_cost_rows", []):
        if str(row.get("timeframe", "")).upper() == "1H":
            return safe_float(row.get("median_spread_atr_median"), default)
    return default


def broker_cost_status(phase170: Mapping[str, Any] | None) -> str:
    if not phase170:
        return "MISSING_PHASE170_USING_DOCUMENTED_MANUAL_VALUES"
    if int(safe_float(phase170.get("broker_cost_reality_gate"), 0)) == 1:
        return "VERIFIED_SAMPLE_AVAILABLE"
    if int(safe_float(phase170.get("samples"), 0)) > 0:
        return "SAMPLES_AVAILABLE_GATE_FAILED"
    return "NO_VALID_SAMPLES"


def documented_route_reset(args: argparse.Namespace, phase168: Mapping[str, Any] | None, phase166: Mapping[str, Any] | None, phase162: Mapping[str, Any] | None) -> str:
    if phase168 is not None:
        if int(safe_float(phase168.get("confirmation_pass_gate"), 0)) == 0:
            return "CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED"
        return "PHASE168_CONFIRMATION_PASS_DIAGNOSTIC_ONLY"
    if phase166 is not None:
        if int(safe_float(phase166.get("walk_forward_pass_gate"), 0)) == 0:
            return "1H_LOCKED_ROUTE_WF_FAILED_PHASE168_MISSING"
        return "1H_LOCKED_ROUTE_WF_PASS_DIAGNOSTIC_ONLY"
    if phase162 is not None:
        if int(safe_float(phase162.get("selected_transfer_pass_gate"), 0)) == 0:
            return "5M_BOTTOM_BUY_REJECTED_1H_STATUS_MISSING"
    if str(args.assume_documented_route_decisions) == "1":
        return "CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED_BY_DOCUMENTED_RESULTS"
    return "INSUFFICIENT_ROUTE_EVIDENCE"


def evidence_snapshots(args: argparse.Namespace, phase170: Mapping[str, Any] | None, phase168: Mapping[str, Any] | None, phase166: Mapping[str, Any] | None, phase162: Mapping[str, Any] | None) -> list[EvidenceSnapshot]:
    return [
        EvidenceSnapshot(
            phase="Phase170A",
            path=str(args.phase170_path),
            status="FOUND" if phase170 else "MISSING_USING_MANUAL_DEFAULTS",
            summary=metric_summary(phase170, ["samples", "sample_status", "broker_cost_reality_gate", "spread_price_median", "spread_price_p90", "spread_price_p99"]),
        ),
        EvidenceSnapshot(
            phase="Phase168A",
            path=str(args.phase168_path),
            status="FOUND" if phase168 else "MISSING_USING_DOCUMENTED_RESULT",
            summary=metric_summary(phase168, ["confirmation_pass_gate", "recommendation", "selected_filter_name", "selected_fold_pass_ratio", "selected_test_pass_ratio"]),
        ),
        EvidenceSnapshot(
            phase="Phase166A",
            path=str(args.phase166_path),
            status="FOUND" if phase166 else "MISSING_USING_DOCUMENTED_RESULT",
            summary=metric_summary(phase166, ["walk_forward_pass_gate", "fold_pass_count", "test_pass_count", "aggregate_test_cash_pnl", "median_test_profit_factor"]),
        ),
        EvidenceSnapshot(
            phase="Phase162A",
            path=str(args.phase162_path),
            status="FOUND" if phase162 else "MISSING_USING_DOCUMENTED_RESULT",
            summary=metric_summary(phase162, ["selected_transfer_pass_gate", "selected_validation_chronological_profit_factor", "selected_test_chronological_profit_factor"]),
        ),
    ]


def add_criteria(route_id: str, items: Sequence[tuple[str, float, float, str]]) -> list[DecisionCriterionRow]:
    return [
        DecisionCriterionRow(
            route_id=route_id,
            criterion=name,
            score=float(score),
            max_score=float(max_score),
            rationale=rationale,
        )
        for name, score, max_score, rationale in items
    ]


def total_for(criteria: Sequence[DecisionCriterionRow], route_id: str) -> float:
    return float(sum(row.score for row in criteria if row.route_id == route_id))


def build_matrix(args: argparse.Namespace, cost_status: str, route_reset_status: str, h1_spread_atr: float) -> tuple[list[RouteDecisionMatrixRow], list[DecisionCriterionRow], list[RecommendedPlanRow]]:
    criteria: list[DecisionCriterionRow] = []
    cost_verified = cost_status == "VERIFIED_SAMPLE_AVAILABLE"
    current_routes_rejected = "REJECTED" in route_reset_status
    h1_cost_feasible = h1_spread_atr <= 0.12

    criteria += add_criteria(
        "STOP_CURRENT_LOCKED_ROUTES",
        [
            ("evidence_quality", 25, 25, "Phase162A/168A documented route failures support stopping current locked routes."),
            ("overfit_control", 25, 25, "Avoids further patching/grid-search on rejected rules."),
            ("cost_reality", 20 if cost_verified else 14, 20, "Broker spread sample is available." if cost_verified else "Cost sample missing in run logs; documented defaults used."),
            ("operational_safety", 30, 30, "Blocks training/paper/live on rejected targets."),
        ],
    )
    criteria += add_criteria(
        "NEW_1H_COST_AWARE_TARGET_FAMILY",
        [
            ("cost_reality", 22 if cost_verified and h1_cost_feasible else 14, 25, "1H broker spread/ATR is feasible with real fixed spread." if cost_verified and h1_cost_feasible else "Needs confirmed spread reality before design."),
            ("signal_evidence", 15, 25, "1H had test-side signal but locked rule failed stability; redesign may preserve useful structure."),
            ("overfit_risk", 12, 20, "New target family must be confirmation-gated from the start."),
            ("data_readiness", 18, 20, "1H data health passed in recent audits."),
            ("architecture_fit", 18, 20, "Clean next research step if explicitly cost-aware and not tied to rejected BRK_D1_FAST target."),
            ("operational_safety", 10, 10, "Research-only design audit, not training/live."),
        ],
    )
    criteria += add_criteria(
        "HYBRID_REGIME_FIRST_REDESIGN",
        [
            ("cost_reality", 18 if cost_verified else 12, 20, "Uses broker cost as a feature/gate instead of a late audit."),
            ("signal_evidence", 16, 25, "Repeated route failures were regime-sensitive, suggesting regime-first design."),
            ("overfit_risk", 16, 20, "Regime-first may reduce blind entry attempts but needs strict WF validation."),
            ("data_readiness", 16, 20, "Existing hybrid/HTF feature infrastructure can support this lane."),
            ("architecture_fit", 20, 20, "Aligns with Clean Architecture without reviving rejected rules."),
            ("operational_safety", 10, 10, "Research-only audit path."),
        ],
    )
    criteria += add_criteria(
        "4H_1D_COST_FEASIBILITY",
        [
            ("cost_reality", 16 if cost_verified else 10, 20, "Higher timeframe spread/ATR should be lower but needs data confirmation."),
            ("signal_evidence", 10, 25, "No current locked 4H/1D entry evidence in this lane."),
            ("overfit_risk", 15, 20, "Lower frequency may reduce microstructure noise but has fewer trades."),
            ("data_readiness", 12, 20, "Data path may exist, but sample/trade counts must be audited."),
            ("architecture_fit", 16, 20, "Reasonable exploration if owner accepts fewer trades."),
            ("operational_safety", 10, 10, "Feasibility-only."),
        ],
    )
    criteria += add_criteria(
        "TRAIN_CURRENT_1H_LOCKED_RULE",
        [
            ("evidence_quality", 0, 30, "Phase168A failed confirmation."),
            ("overfit_control", 0, 30, "Training on a rejected target would likely encode instability."),
            ("operational_safety", 0, 40, "Blocked by research gates."),
        ],
    )
    criteria += add_criteria(
        "PAPER_OR_LIVE",
        [
            ("evidence_quality", 0, 30, "No accepted trading candidate."),
            ("risk_control", 0, 30, "No Phase134, no paper shadow gate."),
            ("operational_safety", 0, 40, "Explicitly blocked."),
        ],
    )

    rows_seed = [
        (
            "STOP_CURRENT_LOCKED_ROUTES",
            "Stop current 5M/1H locked pivot routes",
            "MANDATORY",
            "Stop/record rejection",
            "Current 5M bottom-buy and 1H locked breakout routes failed execution/walk-forward/filter confirmation.",
            "Only redesign or cost-data work; no patching rejected rules.",
            "training,paper,live,Phase134,re-optimizing rejected candidate",
            "Already enacted by Phase169A/Phase170A docs",
        ),
        (
            "NEW_1H_COST_AWARE_TARGET_FAMILY",
            "Design a new broker-cost-aware 1H target family",
            "RECOMMENDED_RESEARCH" if current_routes_rejected else "CONDITIONAL_RESEARCH",
            "Candidate next research lane",
            "1H still has raw signal, but locked rule failed; any new target must include fixed spread ≈ broker sample from the start.",
            "Build target audit only; no model training until target/replay gates pass.",
            "paper,live,Phase134,training before target audit",
            "Phase172A — Broker-cost-aware 1H target-family design audit",
        ),
        (
            "HYBRID_REGIME_FIRST_REDESIGN",
            "Return to hybrid/regime-first architecture",
            "SECONDARY_RESEARCH",
            "Alternative next lane",
            "Failures are regime/month sensitive; entry should be conditioned on higher-timeframe regime rather than raw pivot alone.",
            "Architecture/target audit only.",
            "paper,live,Phase134,training without WF gates",
            "Phase172B — Hybrid/regime-first route redesign audit",
        ),
        (
            "4H_1D_COST_FEASIBILITY",
            "Explore 4H/1D cost-aware feasibility",
            "SECONDARY_RESEARCH",
            "Alternative if owner wants fewer trades",
            "Higher TF can reduce cost sensitivity, but evidence is not yet built in this lane.",
            "Feasibility audit only.",
            "paper,live,Phase134,training before feasibility",
            "Phase172C — 4H/1D cost-aware feasibility audit",
        ),
        (
            "TRAIN_CURRENT_1H_LOCKED_RULE",
            "Train model around current BRK_D1_FAST locked rule",
            "BLOCKED",
            "Do not do this",
            "Phase168A confirmation failed; model would likely learn unstable target.",
            "None.",
            "all training,paper,live,Phase134",
            "Not allowed",
        ),
        (
            "PAPER_OR_LIVE",
            "Paper shadow or live trading",
            "BLOCKED",
            "Do not do this",
            "No accepted production/paper candidate exists.",
            "None.",
            "paper,live,Phase134",
            "Not allowed",
        ),
    ]
    scored_rows: list[RouteDecisionMatrixRow] = []
    for route_id, name, status, decision, rationale, allowed, blocked, phase in rows_seed:
        scored_rows.append(
            RouteDecisionMatrixRow(
                route_id=route_id,
                route_name=name,
                status=status,
                total_score=total_for(criteria, route_id),
                rank=0,
                decision=decision,
                core_rationale=rationale,
                allowed_next_action=allowed,
                blocked_actions=blocked,
                required_phase=phase,
            )
        )
    ranked = sorted(scored_rows, key=lambda row: (row.status == "RECOMMENDED_RESEARCH", row.total_score), reverse=True)
    final_rows: list[RouteDecisionMatrixRow] = []
    for index, row in enumerate(ranked, start=1):
        final_rows.append(RouteDecisionMatrixRow(**{**asdict(row), "rank": index}))

    plan = [
        RecommendedPlanRow(
            step=1,
            phase="Phase171A result review",
            objective="Owner reviews decision matrix and confirms whether to continue research.",
            allowed_actions="Review docs and choose next research lane.",
            blocked_actions="training,paper,live",
            success_gate="Owner approves one research lane explicitly.",
            failure_action="Pause pivot/trading research lane.",
        ),
        RecommendedPlanRow(
            step=2,
            phase="Phase172A or Phase172B/172C",
            objective="Run one feasibility/target-design audit for the selected new lane.",
            allowed_actions="Diagnostic audit only.",
            blocked_actions="model training before replay/target gates",
            success_gate="Validation/test/walk-forward diagnostic gates pass under broker-realistic cost.",
            failure_action="Reject the lane without patch chasing.",
        ),
        RecommendedPlanRow(
            step=3,
            phase="Future model phase only if gates pass",
            objective="Only then consider model/target training around a validated target family.",
            allowed_actions="Training design proposal with GUI command and documented gates.",
            blocked_actions="paper/live/Phase134",
            success_gate="Out-of-sample and walk-forward pass, then separate paper-shadow approval phase.",
            failure_action="Stop/revise before model training.",
        ),
    ]
    return final_rows, criteria, plan


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase171Report) -> str:
    matrix_rows = "".join(
        f"<tr><td>{int(row['rank'])}</td>"
        f"<td>{html.escape(str(row['route_name']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['total_score']):.1f}</td>"
        f"<td>{html.escape(str(row['decision']))}</td>"
        f"<td>{html.escape(str(row['required_phase']))}</td></tr>"
        for row in report.decision_matrix_rows
    )
    plan_rows = "".join(
        f"<tr><td>{int(row['step'])}</td>"
        f"<td>{html.escape(str(row['phase']))}</td>"
        f"<td>{html.escape(str(row['objective']))}</td>"
        f"<td>{html.escape(str(row['success_gate']))}</td></tr>"
        for row in report.recommended_plan_rows
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase171A research route redesign decision matrix. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_reset_status': report.route_reset_status,
        'broker_cost_status': report.broker_cost_status,
        'selected_research_route': report.selected_research_route_name,
        'selected_required_phase': report.selected_required_phase,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Decision matrix</h2><table><thead><tr><th>Rank</th><th>Route</th><th>Status</th><th>Score</th><th>Decision</th><th>Required phase</th></tr></thead><tbody>{matrix_rows}</tbody></table></section>
<section class="card"><h2>Recommended plan</h2><table><thead><tr><th>Step</th><th>Phase</th><th>Objective</th><th>Success gate</th></tr></thead><tbody>{plan_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE171A RESEARCH ROUTE REDESIGN DECISION MATRIX")
        print("=" * 74)
        phase170 = load_json(args.phase170_path)
        phase168 = load_json(args.phase168_path)
        phase166 = load_json(args.phase166_path)
        phase162 = load_json(args.phase162_path)
        spread_median = safe_float(phase170.get("spread_price_median") if phase170 else None, float(args.manual_broker_spread_median))
        spread_p90 = safe_float(phase170.get("spread_price_p90") if phase170 else None, float(args.manual_broker_spread_p90))
        spread_p99 = safe_float(phase170.get("spread_price_p99") if phase170 else None, float(args.manual_broker_spread_p99))
        h1_spread_atr = h1_spread_atr_from_phase170(phase170, float(args.manual_h1_median_spread_atr))
        cost_status = broker_cost_status(phase170)
        reset_status = documented_route_reset(args, phase168, phase166, phase162)
        matrix_rows, criteria_rows, plan_rows = build_matrix(args, cost_status, reset_status, h1_spread_atr)
        recommended = next((row for row in matrix_rows if row.status == "RECOMMENDED_RESEARCH"), matrix_rows[0])
        evidence = evidence_snapshots(args, phase170, phase168, phase166, phase162)
        matrix_csv = output_dir / "latest_decision_matrix.csv"
        criteria_csv = output_dir / "latest_criteria.csv"
        plan_csv = output_dir / "latest_recommended_plan.csv"
        evidence_csv = output_dir / "latest_evidence.csv"
        write_csv(matrix_csv, [asdict(row) for row in matrix_rows])
        write_csv(criteria_csv, [asdict(row) for row in criteria_rows])
        write_csv(plan_csv, [asdict(row) for row in plan_rows])
        write_csv(evidence_csv, [asdict(row) for row in evidence])
        report = Phase171Report(
            symbol=str(args.symbol),
            generated_at_utc=pd.Timestamp.utcnow().isoformat(),
            phase170_path=str(args.phase170_path),
            phase168_path=str(args.phase168_path),
            phase166_path=str(args.phase166_path),
            broker_cost_status=cost_status,
            broker_spread_median=float(spread_median),
            broker_spread_p90=float(spread_p90),
            broker_spread_p99=float(spread_p99),
            h1_median_spread_atr=float(h1_spread_atr),
            route_reset_status=reset_status,
            selected_research_route_id=str(recommended.route_id),
            selected_research_route_name=str(recommended.route_name),
            selected_required_phase=str(recommended.required_phase),
            production_status="BLOCKED — Phase171A route redesign decision only",
            evidence_snapshots=[asdict(row) for row in evidence],
            decision_matrix_rows=[asdict(row) for row in matrix_rows],
            criteria_rows=[asdict(row) for row in criteria_rows],
            recommended_plan_rows=[asdict(row) for row in plan_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_decision_matrix_csv=str(matrix_csv),
            output_criteria_csv=str(criteria_csv),
            output_recommended_plan_csv=str(plan_csv),
            output_evidence_csv=str(evidence_csv),
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase171A decision matrix complete")
        print(f"  route reset : {report.route_reset_status}")
        print(f"  cost status : {report.broker_cost_status}")
        print(f"  selected    : {report.selected_research_route_name}")
        print(f"  next phase  : {report.selected_required_phase}")
        print(f"  output      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
