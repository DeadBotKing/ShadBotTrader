"""Phase175A: hybrid/regime walk-forward failure attribution audit.

Phase174A evaluated predeclared broker-cost-aware 1H family × regime candidates
and found no ready route. This phase consumes the Phase174A JSON result and
attributes *why* the route failed: density, class balance, label stability,
static learnability, raw economics, and walk-forward transfer.

Research-only. No production model, paper shadow, live trading, or Phase134.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_PHASE174_PATH = Path("run_logs/hybrid_regime_first_target_redesign/latest.json")
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_regime_walkforward_failure_attribution")


@dataclass(frozen=True)
class CandidateFailureRow:
    family_id: str
    family_label: str
    regime_rule_id: str
    regime_label: str
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    validation_ap_lift: float
    test_ap_lift: float
    validation_balanced_accuracy: float
    test_balanced_accuracy: float
    train_independent_profit_factor: float
    validation_independent_profit_factor: float
    test_independent_profit_factor: float
    train_mean_atr_score: float
    validation_mean_atr_score: float
    test_mean_atr_score: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    class_balance_gate: int
    economic_gate: int
    static_learnability_gate: int
    walkforward_learnability_gate: int
    regime_candidate_ready_gate: int
    failure_reason_count: int
    primary_failure_reason: str
    failure_reasons: str
    diagnostic_score: float


@dataclass(frozen=True)
class FailureReasonRow:
    scope: str
    reason: str
    count: int
    total: int
    ratio: float
    example: str


@dataclass(frozen=True)
class FoldFailureSummaryRow:
    family_id: str
    family_label: str
    regime_rule_id: str
    regime_label: str
    folds: int
    pass_folds: int
    pass_ratio: float
    validation_ap_lift_failed_folds: int
    test_ap_lift_failed_folds: int
    validation_balanced_accuracy_failed_folds: int
    test_balanced_accuracy_failed_folds: int
    validation_pf_failed_folds: int
    test_pf_failed_folds: int
    density_failed_folds: int
    label_psi_failed_folds: int
    positive_rate_failed_folds: int
    dominant_fold_failure_reason: str


@dataclass(frozen=True)
class DecisionMatrixRow:
    route_id: str
    route_name: str
    status: str
    score: float
    rank: int
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class NextPlanRow:
    step_order: int
    action_id: str
    title: str
    rationale: str
    gate_policy: str


@dataclass(frozen=True)
class Phase175Report:
    phase174_path: str
    source_symbol: str
    source_timeframe: str
    source_spread_mode: str
    source_spread_value: float
    source_evaluated_regime_candidates: int
    source_ready_regime_candidates: int
    source_hybrid_regime_first_ready_gate: int
    source_recommendation: str
    candidate_rows: int
    walkforward_rows: int
    walkforward_pass_rows: int
    walkforward_global_pass_ratio: float
    candidates_with_class_balance_gate: int
    candidates_with_economic_gate: int
    candidates_with_static_learnability_gate: int
    candidates_with_walkforward_gate: int
    candidates_with_ready_gate: int
    selected_near_miss_family_id: str
    selected_near_miss_regime_rule_id: str
    selected_near_miss_ready_gate: int
    selected_near_miss_primary_failure_reason: str
    dominant_candidate_failure_reason: str
    dominant_walkforward_failure_reason: str
    root_cause_summary: str
    route_decision: str
    recommended_next_phase: str
    no_training_gate: int
    no_paper_live_gate: int
    candidate_failure_rows: list[dict[str, Any]]
    failure_reason_rows: list[dict[str, Any]]
    fold_failure_summary_rows: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    next_plan_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidate_failures_csv: str
    output_failure_reasons_csv: str
    output_fold_failure_summary_csv: str
    output_decision_matrix_csv: str
    output_next_plan_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attribute Phase174A hybrid/regime walk-forward failures before any model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase174-path", default=str(DEFAULT_PHASE174_PATH))
    parser.add_argument("--min-train-events", type=int, default=80)
    parser.add_argument("--min-validation-events", type=int, default=20)
    parser.add_argument("--min-test-events", type=int, default=20)
    parser.add_argument("--min-positive-rate", type=float, default=0.10)
    parser.add_argument("--max-positive-rate", type=float, default=0.70)
    parser.add_argument("--max-label-psi", type=float, default=0.20)
    parser.add_argument("--min-ap-lift", type=float, default=0.03)
    parser.add_argument("--min-balanced-accuracy", type=float, default=0.53)
    parser.add_argument("--min-train-independent-pf", type=float, default=0.95)
    parser.add_argument("--min-validation-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-test-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=5)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase175A hybrid/regime walk-forward failure attribution audit")
    return parser.parse_args(argv)


def as_float(row: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def as_int(row: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return int(default)


def safe_ratio(count: int, total: int) -> float:
    return float(count / total) if total else 0.0


def candidate_key(row: Mapping[str, Any]) -> str:
    return f"{row.get('family_id', '')}|{row.get('regime_rule_id', '')}"


def rate_failed(value: float, args: argparse.Namespace) -> bool:
    return value < float(args.min_positive_rate) or value > float(args.max_positive_rate)


def candidate_failure_reasons(row: Mapping[str, Any], args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if as_int(row, "train_events") < int(args.min_train_events):
        reasons.append("train_density_failed")
    if as_int(row, "validation_events") < int(args.min_validation_events):
        reasons.append("validation_density_failed")
    if as_int(row, "test_events") < int(args.min_test_events):
        reasons.append("test_density_failed")
    for split in ("train", "validation", "test"):
        if rate_failed(as_float(row, f"{split}_positive_rate"), args):
            reasons.append(f"{split}_positive_rate_failed")
    if as_float(row, "validation_label_psi") > float(args.max_label_psi):
        reasons.append("validation_label_psi_failed")
    if as_float(row, "test_label_psi") > float(args.max_label_psi):
        reasons.append("test_label_psi_failed")
    if as_float(row, "train_independent_profit_factor") < float(args.min_train_independent_pf):
        reasons.append("train_raw_economics_failed")
    if as_float(row, "validation_independent_profit_factor") < float(args.min_validation_independent_pf):
        reasons.append("validation_raw_economics_failed")
    if as_float(row, "test_independent_profit_factor") < float(args.min_test_independent_pf):
        reasons.append("test_raw_economics_failed")
    if as_float(row, "train_mean_atr_score") < 0.0:
        reasons.append("train_negative_expectancy_failed")
    if as_float(row, "validation_ap_lift") < float(args.min_ap_lift):
        reasons.append("validation_ap_lift_failed")
    if as_float(row, "test_ap_lift") < float(args.min_ap_lift):
        reasons.append("test_ap_lift_failed")
    if as_float(row, "validation_balanced_accuracy") < float(args.min_balanced_accuracy):
        reasons.append("validation_balanced_accuracy_failed")
    if as_float(row, "test_balanced_accuracy") < float(args.min_balanced_accuracy):
        reasons.append("test_balanced_accuracy_failed")
    if as_float(row, "walkforward_pass_ratio") < float(args.min_walkforward_pass_ratio):
        reasons.append("walkforward_pass_ratio_failed")
    if as_int(row, "walkforward_folds") < int(args.min_walkforward_folds):
        reasons.append("walkforward_min_folds_failed")
    if as_int(row, "class_balance_gate") == 0:
        reasons.append("class_balance_gate_failed")
    if as_int(row, "economic_gate") == 0:
        reasons.append("economic_gate_failed")
    if as_int(row, "static_learnability_gate") == 0:
        reasons.append("static_learnability_gate_failed")
    if as_int(row, "walkforward_learnability_gate") == 0:
        reasons.append("walkforward_learnability_gate_failed")
    return sorted(set(reasons))


def fold_failure_reasons(row: Mapping[str, Any], args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if as_int(row, "train_events") < int(args.min_train_events):
        reasons.append("train_density_failed")
    if as_int(row, "validation_events") < int(args.min_validation_events):
        reasons.append("validation_density_failed")
    if as_int(row, "test_events") < int(args.min_test_events):
        reasons.append("test_density_failed")
    for split in ("train", "validation", "test"):
        if rate_failed(as_float(row, f"{split}_positive_rate"), args):
            reasons.append(f"{split}_positive_rate_failed")
    if as_float(row, "validation_label_psi") > float(args.max_label_psi):
        reasons.append("validation_label_psi_failed")
    if as_float(row, "test_label_psi") > float(args.max_label_psi):
        reasons.append("test_label_psi_failed")
    if as_float(row, "validation_ap_lift") < float(args.min_ap_lift):
        reasons.append("validation_ap_lift_failed")
    if as_float(row, "test_ap_lift") < float(args.min_ap_lift):
        reasons.append("test_ap_lift_failed")
    if as_float(row, "validation_balanced_accuracy") < float(args.min_balanced_accuracy):
        reasons.append("validation_balanced_accuracy_failed")
    if as_float(row, "test_balanced_accuracy") < float(args.min_balanced_accuracy):
        reasons.append("test_balanced_accuracy_failed")
    if as_float(row, "validation_independent_profit_factor") < float(args.min_validation_independent_pf):
        reasons.append("validation_raw_economics_failed")
    if as_float(row, "test_independent_profit_factor") < float(args.min_test_independent_pf):
        reasons.append("test_raw_economics_failed")
    if as_int(row, "pass_gate") == 0:
        reasons.append("fold_pass_gate_failed")
    return sorted(set(reasons))


def diagnostic_score(row: Mapping[str, Any], reasons: Sequence[str]) -> float:
    return float(
        (10.0 if as_int(row, "class_balance_gate") else 0.0)
        + (12.0 if as_int(row, "economic_gate") else 0.0)
        + (15.0 if as_int(row, "static_learnability_gate") else 0.0)
        + (25.0 * as_float(row, "walkforward_pass_ratio"))
        + (6.0 * max(as_float(row, "validation_ap_lift"), 0.0))
        + (6.0 * max(as_float(row, "test_ap_lift"), 0.0))
        + (4.0 * max(as_float(row, "validation_balanced_accuracy") - 0.5, 0.0))
        + (4.0 * max(as_float(row, "test_balanced_accuracy") - 0.5, 0.0))
        + min(as_float(row, "validation_independent_profit_factor"), 3.0)
        + min(as_float(row, "test_independent_profit_factor"), 3.0)
        - (0.5 * len(reasons))
    )


def build_candidate_failure_row(row: Mapping[str, Any], args: argparse.Namespace) -> CandidateFailureRow:
    reasons = candidate_failure_reasons(row, args)
    primary = reasons[0] if reasons else "none"
    return CandidateFailureRow(
        family_id=str(row.get("family_id", "")),
        family_label=str(row.get("family_label", "")),
        regime_rule_id=str(row.get("regime_rule_id", "")),
        regime_label=str(row.get("regime_label", "")),
        train_events=as_int(row, "train_events"),
        validation_events=as_int(row, "validation_events"),
        test_events=as_int(row, "test_events"),
        train_positive_rate=as_float(row, "train_positive_rate"),
        validation_positive_rate=as_float(row, "validation_positive_rate"),
        test_positive_rate=as_float(row, "test_positive_rate"),
        validation_label_psi=as_float(row, "validation_label_psi"),
        test_label_psi=as_float(row, "test_label_psi"),
        validation_ap_lift=as_float(row, "validation_ap_lift"),
        test_ap_lift=as_float(row, "test_ap_lift"),
        validation_balanced_accuracy=as_float(row, "validation_balanced_accuracy"),
        test_balanced_accuracy=as_float(row, "test_balanced_accuracy"),
        train_independent_profit_factor=as_float(row, "train_independent_profit_factor"),
        validation_independent_profit_factor=as_float(row, "validation_independent_profit_factor"),
        test_independent_profit_factor=as_float(row, "test_independent_profit_factor"),
        train_mean_atr_score=as_float(row, "train_mean_atr_score"),
        validation_mean_atr_score=as_float(row, "validation_mean_atr_score"),
        test_mean_atr_score=as_float(row, "test_mean_atr_score"),
        walkforward_folds=as_int(row, "walkforward_folds"),
        walkforward_pass_folds=as_int(row, "walkforward_pass_folds"),
        walkforward_pass_ratio=as_float(row, "walkforward_pass_ratio"),
        class_balance_gate=as_int(row, "class_balance_gate"),
        economic_gate=as_int(row, "economic_gate"),
        static_learnability_gate=as_int(row, "static_learnability_gate"),
        walkforward_learnability_gate=as_int(row, "walkforward_learnability_gate"),
        regime_candidate_ready_gate=as_int(row, "regime_candidate_ready_gate"),
        failure_reason_count=len(reasons),
        primary_failure_reason=primary,
        failure_reasons=json.dumps(reasons, ensure_ascii=False),
        diagnostic_score=diagnostic_score(row, reasons),
    )


def reason_summary(scope: str, reason_counter: Counter[str], total: int, examples: Mapping[str, str]) -> list[FailureReasonRow]:
    rows: list[FailureReasonRow] = []
    for reason, count in reason_counter.most_common():
        rows.append(
            FailureReasonRow(
                scope=scope,
                reason=reason,
                count=int(count),
                total=int(total),
                ratio=safe_ratio(int(count), int(total)),
                example=str(examples.get(reason, "")),
            )
        )
    return rows


def build_fold_summary(rows: Sequence[Mapping[str, Any]], args: argparse.Namespace) -> list[FoldFailureSummaryRow]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[candidate_key(row)].append(row)
    output: list[FoldFailureSummaryRow] = []
    for _key, items in grouped.items():
        if not items:
            continue
        counters: Counter[str] = Counter()
        for item in items:
            counters.update(fold_failure_reasons(item, args))
        dominant = counters.most_common(1)[0][0] if counters else "none"
        first = items[0]
        output.append(
            FoldFailureSummaryRow(
                family_id=str(first.get("family_id", "")),
                family_label=str(first.get("family_label", "")),
                regime_rule_id=str(first.get("regime_rule_id", "")),
                regime_label=str(first.get("regime_label", "")),
                folds=len(items),
                pass_folds=sum(as_int(item, "pass_gate") for item in items),
                pass_ratio=safe_ratio(sum(as_int(item, "pass_gate") for item in items), len(items)),
                validation_ap_lift_failed_folds=int(counters.get("validation_ap_lift_failed", 0)),
                test_ap_lift_failed_folds=int(counters.get("test_ap_lift_failed", 0)),
                validation_balanced_accuracy_failed_folds=int(counters.get("validation_balanced_accuracy_failed", 0)),
                test_balanced_accuracy_failed_folds=int(counters.get("test_balanced_accuracy_failed", 0)),
                validation_pf_failed_folds=int(counters.get("validation_raw_economics_failed", 0)),
                test_pf_failed_folds=int(counters.get("test_raw_economics_failed", 0)),
                density_failed_folds=int(
                    counters.get("train_density_failed", 0)
                    + counters.get("validation_density_failed", 0)
                    + counters.get("test_density_failed", 0)
                ),
                label_psi_failed_folds=int(
                    counters.get("validation_label_psi_failed", 0)
                    + counters.get("test_label_psi_failed", 0)
                ),
                positive_rate_failed_folds=int(
                    counters.get("train_positive_rate_failed", 0)
                    + counters.get("validation_positive_rate_failed", 0)
                    + counters.get("test_positive_rate_failed", 0)
                ),
                dominant_fold_failure_reason=dominant,
            )
        )
    return sorted(output, key=lambda row: (row.pass_ratio, -row.validation_ap_lift_failed_folds, row.family_id, row.regime_rule_id), reverse=True)


def build_decision_matrix(ready_candidates: int, source_ready: int, near_miss: CandidateFailureRow | None) -> list[DecisionMatrixRow]:
    evidence_best = (
        f"best_failed={near_miss.family_id}|{near_miss.regime_rule_id}; primary_failure={near_miss.primary_failure_reason}"
        if near_miss is not None
        else "best_failed=none"
    )
    return [
        DecisionMatrixRow(
            route_id="STOP_PHASE174_REGIME_TRAINING",
            route_name="Stop CA1/CA3/CA2 regime candidate training",
            status="MANDATORY",
            score=100.0,
            rank=1,
            evidence=f"ready_regime_candidates={ready_candidates}; source_ready={source_ready}; {evidence_best}",
            recommendation="Do not train any Phase174 regime candidate.",
        ),
        DecisionMatrixRow(
            route_id="TARGET_DEFINITION_FAILURE_REDESIGN_AUDIT",
            route_name="Diagnose target-definition and walk-forward failure before any new target build",
            status="RECOMMENDED_DIAGNOSTIC",
            score=82.0,
            rank=2,
            evidence="All regime candidates failed transfer; next useful work is causal failure attribution by fold/time/target definition, not model size.",
            recommendation="Owner may authorize a diagnostic-only target-definition redesign/root-cause phase.",
        ),
        DecisionMatrixRow(
            route_id="TRAIN_MODEL_NOW",
            route_name="Train a deep model now",
            status="BLOCKED",
            score=0.0,
            rank=3,
            evidence="Phase173A and Phase174A both have ready gate 0.",
            recommendation="No model training until a future diagnostic route passes gates.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=4,
            evidence="No trade-ready candidate exists and no production approval exists.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def build_next_plan() -> list[NextPlanRow]:
    return [
        NextPlanRow(
            step_order=1,
            action_id="freeze_failed_routes",
            title="Freeze Phase173A/174A targets as failed diagnostics",
            rationale="Both broad learnability and predeclared regime filtering failed walk-forward gates.",
            gate_policy="No training, no paper, no live.",
        ),
        NextPlanRow(
            step_order=2,
            action_id="target_definition_root_cause",
            title="Audit target-definition failure by fold, side, time, ATR, and payoff horizon",
            rationale="The repeated 0/6 walk-forward outcome suggests target design/feature regime mismatch rather than model capacity.",
            gate_policy="Diagnostic-only; do not produce model artifacts.",
        ),
        NextPlanRow(
            step_order=3,
            action_id="owner_decision_gate",
            title="Owner decision: pause route or authorize a new target-definition redesign audit",
            rationale="Continuing without changing target definition risks overfitting small validation/test pockets.",
            gate_policy="Explicit owner approval required before any new phase.",
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


def render_html(title: str, report: Phase175Report) -> str:
    failure_rows = "".join(
        f"<tr><td>{html.escape(str(row['scope']))}</td><td>{html.escape(str(row['reason']))}</td>"
        f"<td>{int(row['count'])}/{int(row['total'])}</td><td>{float(row['ratio']):.2f}</td>"
        f"<td>{html.escape(str(row['example']))}</td></tr>"
        for row in report.failure_reason_rows[:80]
    )
    candidate_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td><td>{html.escape(str(row['regime_rule_id']))}</td>"
        f"<td>{float(row['diagnostic_score']):.2f}</td><td>{html.escape(str(row['primary_failure_reason']))}</td>"
        f"<td>{int(row['walkforward_pass_folds'])}/{int(row['walkforward_folds'])}</td>"
        f"<td>{float(row['train_independent_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_ap_lift']):.4f}</td><td>{float(row['test_ap_lift']):.4f}</td></tr>"
        for row in report.candidate_failure_rows[:60]
    )
    decision_rows = "".join(
        f"<tr><td>{html.escape(str(row['route_id']))}</td><td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['score']):.1f}</td><td>{html.escape(str(row['recommendation']))}</td></tr>"
        for row in report.decision_matrix_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase175A hybrid/regime walk-forward failure attribution. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_decision': report.route_decision,
        'recommended_next_phase': report.recommended_next_phase,
        'no_training_gate': report.no_training_gate,
        'no_paper_live_gate': report.no_paper_live_gate,
        'dominant_candidate_failure_reason': report.dominant_candidate_failure_reason,
        'dominant_walkforward_failure_reason': report.dominant_walkforward_failure_reason,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
<section class="card"><h2>Failure reasons</h2><table><thead><tr><th>Scope</th><th>Reason</th><th>Count</th><th>Ratio</th><th>Example</th></tr></thead><tbody>{failure_rows}</tbody></table></section>
<section class="card"><h2>Top failed candidates</h2><table><thead><tr><th>Family</th><th>Regime</th><th>Score</th><th>Primary failure</th><th>WF pass</th><th>Train PF</th><th>Val AP lift</th><th>Test AP lift</th></tr></thead><tbody>{candidate_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE175A HYBRID/REGIME WALK-FORWARD FAILURE ATTRIBUTION")
        print("=" * 74)
        phase174_path = Path(args.phase174_path)
        if not phase174_path.exists():
            raise RuntimeError(f"Phase174 result not found: {phase174_path}")
        source = json.loads(phase174_path.read_text(encoding="utf-8"))
        candidates_raw = list(source.get("candidate_rows", []))
        walkforward_raw = list(source.get("walkforward_rows", []))

        candidate_failure_rows = [build_candidate_failure_row(row, args) for row in candidates_raw]
        candidate_failure_rows = sorted(candidate_failure_rows, key=lambda row: row.diagnostic_score, reverse=True)
        near_miss = candidate_failure_rows[0] if candidate_failure_rows else None

        candidate_counter: Counter[str] = Counter()
        candidate_examples: dict[str, str] = {}
        for row in candidates_raw:
            key = candidate_key(row)
            for reason in candidate_failure_reasons(row, args):
                candidate_counter[reason] += 1
                candidate_examples.setdefault(reason, key)

        fold_counter: Counter[str] = Counter()
        fold_examples: dict[str, str] = {}
        for row in walkforward_raw:
            key = f"{candidate_key(row)}|fold={row.get('fold', '')}"
            for reason in fold_failure_reasons(row, args):
                fold_counter[reason] += 1
                fold_examples.setdefault(reason, key)

        fold_summary = build_fold_summary(walkforward_raw, args)
        failure_rows = reason_summary("candidate", candidate_counter, len(candidates_raw), candidate_examples)
        failure_rows.extend(reason_summary("walkforward_fold", fold_counter, len(walkforward_raw), fold_examples))
        decision_rows = build_decision_matrix(
            ready_candidates=sum(row.regime_candidate_ready_gate for row in candidate_failure_rows),
            source_ready=as_int(source, "ready_regime_candidates"),
            near_miss=near_miss,
        )
        next_plan_rows = build_next_plan()

        walkforward_pass = sum(as_int(row, "pass_gate") for row in walkforward_raw)
        dominant_candidate = failure_rows[0].reason if failure_rows else "none"
        wf_reason_rows = [row for row in failure_rows if row.scope == "walkforward_fold"]
        dominant_wf = wf_reason_rows[0].reason if wf_reason_rows else "none"
        route_decision = "ROUTE_NOT_CONFIRMED_STOP_OR_TARGET_DEFINITION_REDESIGN"
        recommended_next = "Phase176A — target-definition walk-forward root-cause redesign audit"
        root_cause = (
            "Phase174A produced validation/test pockets but no stable walk-forward transfer. "
            "Dominant failure attribution points to target/regime instability rather than model capacity; "
            "training remains blocked."
        )

        output_candidate = output_dir / "latest_candidate_failures.csv"
        output_reasons = output_dir / "latest_failure_reasons.csv"
        output_folds = output_dir / "latest_fold_failure_summary.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        output_plan = output_dir / "latest_next_plan.csv"
        write_csv(output_candidate, [asdict(row) for row in candidate_failure_rows])
        write_csv(output_reasons, [asdict(row) for row in failure_rows])
        write_csv(output_folds, [asdict(row) for row in fold_summary])
        write_csv(output_decision, [asdict(row) for row in decision_rows])
        write_csv(output_plan, [asdict(row) for row in next_plan_rows])

        report = Phase175Report(
            phase174_path=str(phase174_path),
            source_symbol=str(source.get("symbol", "")),
            source_timeframe=str(source.get("timeframe", "")),
            source_spread_mode=str(source.get("spread_mode", "")),
            source_spread_value=as_float(source, "spread_value"),
            source_evaluated_regime_candidates=as_int(source, "evaluated_regime_candidates"),
            source_ready_regime_candidates=as_int(source, "ready_regime_candidates"),
            source_hybrid_regime_first_ready_gate=as_int(source, "hybrid_regime_first_ready_gate"),
            source_recommendation=str(source.get("recommendation", "")),
            candidate_rows=len(candidates_raw),
            walkforward_rows=len(walkforward_raw),
            walkforward_pass_rows=int(walkforward_pass),
            walkforward_global_pass_ratio=safe_ratio(int(walkforward_pass), len(walkforward_raw)),
            candidates_with_class_balance_gate=sum(row.class_balance_gate for row in candidate_failure_rows),
            candidates_with_economic_gate=sum(row.economic_gate for row in candidate_failure_rows),
            candidates_with_static_learnability_gate=sum(row.static_learnability_gate for row in candidate_failure_rows),
            candidates_with_walkforward_gate=sum(row.walkforward_learnability_gate for row in candidate_failure_rows),
            candidates_with_ready_gate=sum(row.regime_candidate_ready_gate for row in candidate_failure_rows),
            selected_near_miss_family_id=near_miss.family_id if near_miss else "",
            selected_near_miss_regime_rule_id=near_miss.regime_rule_id if near_miss else "",
            selected_near_miss_ready_gate=near_miss.regime_candidate_ready_gate if near_miss else 0,
            selected_near_miss_primary_failure_reason=near_miss.primary_failure_reason if near_miss else "",
            dominant_candidate_failure_reason=dominant_candidate,
            dominant_walkforward_failure_reason=dominant_wf,
            root_cause_summary=root_cause,
            route_decision=route_decision,
            recommended_next_phase=recommended_next,
            no_training_gate=1,
            no_paper_live_gate=1,
            candidate_failure_rows=[asdict(row) for row in candidate_failure_rows],
            failure_reason_rows=[asdict(row) for row in failure_rows],
            fold_failure_summary_rows=[asdict(row) for row in fold_summary],
            decision_matrix_rows=[asdict(row) for row in decision_rows],
            next_plan_rows=[asdict(row) for row in next_plan_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidate_failures_csv=str(output_candidate),
            output_failure_reasons_csv=str(output_reasons),
            output_fold_failure_summary_csv=str(output_folds),
            output_decision_matrix_csv=str(output_decision),
            output_next_plan_csv=str(output_plan),
            production_status="BLOCKED — Phase175A failure attribution audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase175A failure attribution complete")
        print(f"  candidates       : {report.candidate_rows}")
        print(f"  wf rows          : {report.walkforward_rows}")
        print(f"  wf pass rows     : {report.walkforward_pass_rows}")
        print(f"  near miss        : {report.selected_near_miss_family_id}|{report.selected_near_miss_regime_rule_id}")
        print(f"  route decision   : {report.route_decision}")
        print(f"  output           : {report.output_json}")
        print(f"  elapsed          : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
