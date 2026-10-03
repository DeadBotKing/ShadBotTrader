"""Phase180A: higher-timeframe target failure attribution / redesign decision.

Phase179A showed that 4H/1D cost pressure is healthier than 1H, but no
higher-timeframe target family passed readiness gates. This phase consumes the
Phase179A result and attributes failure by timeframe, target family, and
walk-forward fold. It recommends the next diagnostic route, if any.

Research-only. No model training, paper shadow, live trading, or Phase134.
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

DEFAULT_PHASE179_PATH = Path("run_logs/higher_timeframe_cost_feasibility/latest.json")
DEFAULT_OUTPUT_DIR = Path("run_logs/higher_timeframe_target_failure_attribution")


@dataclass(frozen=True)
class CandidateFailureRow:
    timeframe: str
    family_id: str
    label: str
    side_mapping: str
    tp_atr: float
    sl_atr: float
    hold_bars: int
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_independent_profit_factor: float
    validation_independent_profit_factor: float
    test_independent_profit_factor: float
    train_mean_atr_score: float
    validation_mean_atr_score: float
    test_mean_atr_score: float
    validation_ap_lift: float
    test_ap_lift: float
    validation_balanced_accuracy: float
    test_balanced_accuracy: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    density_gate: int
    economic_gate: int
    static_learnability_gate: int
    walkforward_gate: int
    target_family_ready_gate: int
    failure_reason_count: int
    primary_failure_reason: str
    failure_reasons: str
    near_miss_gate: int
    diagnostic_score: float


@dataclass(frozen=True)
class TimeframeSummaryRow:
    timeframe: str
    health_gate: int
    candidate_count: int
    ready_candidates: int
    near_miss_candidates: int
    cost_gate_pass_splits: int
    cost_splits: int
    median_spread_atr_train: float
    median_spread_atr_validation: float
    median_spread_atr_test: float
    best_family_id: str
    best_family_ready_gate: int
    best_walkforward_pass_ratio: float
    best_train_independent_profit_factor: float
    best_validation_independent_profit_factor: float
    best_test_independent_profit_factor: float
    best_validation_ap_lift: float
    best_test_ap_lift: float
    best_test_balanced_accuracy: float
    dominant_failure_reason: str
    verdict: str


@dataclass(frozen=True)
class FoldFailureRow:
    timeframe: str
    family_id: str
    label: str
    folds: int
    pass_folds: int
    pass_ratio: float
    train_gate_failed_folds: int
    validation_gate_failed_folds: int
    test_gate_failed_folds: int
    dominant_fold_failure_reason: str
    fold_failure_reasons: str


@dataclass(frozen=True)
class FailureReasonRow:
    scope: str
    reason: str
    count: int
    total: int
    ratio: float
    example: str


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
    phase_id: str
    title: str
    purpose: str
    allowed: str
    blocked: str
    expected_output: str


@dataclass(frozen=True)
class Phase180Report:
    phase179_path: str
    source_symbol: str
    source_timeframes: list[str]
    source_spread_mode: str
    source_spread_value: float
    source_evaluated_candidates: int
    source_ready_candidates: int
    source_higher_timeframe_feasibility_gate: int
    cost_feasibility_confirmed_gate: int
    target_readiness_confirmed_failed_gate: int
    selected_next_route_id: str
    selected_next_phase: str
    selected_focus_timeframe: str
    selected_focus_family_id: str
    no_training_gate: int
    no_paper_live_gate: int
    root_cause_summary: str
    candidate_failure_rows: list[dict[str, Any]]
    timeframe_summary_rows: list[dict[str, Any]]
    fold_failure_rows: list[dict[str, Any]]
    failure_reason_rows: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    next_plan_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidate_failures_csv: str
    output_timeframe_summary_csv: str
    output_fold_failures_csv: str
    output_failure_reasons_csv: str
    output_decision_matrix_csv: str
    output_next_plan_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attribute higher-timeframe target failures after Phase179A.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase179-path", default=str(DEFAULT_PHASE179_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase180A higher-timeframe target failure attribution")
    return parser.parse_args(argv)


def canonical_timeframe(text: str) -> str:
    value = str(text or "").strip().upper()
    if value in {"1", "1D", "D1", "D"}:
        return "1D"
    if value in {"4", "4H", "H4"}:
        return "4H"
    return value


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


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if abs(float(den)) > 1e-12 else 0.0


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Phase179 result not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def decode_reasons(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        value = json.loads(str(raw or "[]"))
        if isinstance(value, list):
            return [str(item) for item in value]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def candidate_reasons(row: Mapping[str, Any]) -> list[str]:
    reasons = decode_reasons(row.get("failure_reasons", "[]"))
    if as_int(row, "target_family_ready_gate") == 0:
        reasons.append("target_family_ready_gate_failed")
    if as_int(row, "economic_gate") == 0:
        reasons.append("economic_gate_failed")
    if as_int(row, "static_learnability_gate") == 0:
        reasons.append("static_learnability_gate_failed")
    if as_int(row, "walkforward_gate") == 0:
        reasons.append("walkforward_gate_failed")
    if as_float(row, "walkforward_pass_ratio") < 0.5:
        reasons.append("walkforward_pass_ratio_failed")
    if as_float(row, "test_balanced_accuracy") <= 0.52:
        reasons.append("test_balanced_accuracy_failed")
    if as_float(row, "test_ap_lift") < 0.02:
        reasons.append("test_ap_lift_failed")
    if as_float(row, "train_mean_atr_score") < 0.0:
        reasons.append("train_expectancy_failed")
    return sorted(set(reason for reason in reasons if reason and reason != "none"))


def near_miss_gate(row: Mapping[str, Any]) -> int:
    return int(
        as_int(row, "target_family_ready_gate") == 0
        and as_int(row, "density_gate") == 1
        and as_float(row, "train_independent_profit_factor") >= 1.0
        and as_float(row, "validation_independent_profit_factor") >= 1.0
        and as_float(row, "test_independent_profit_factor") >= 1.0
        and as_float(row, "walkforward_pass_ratio") > 0.0
    )


def build_candidate_failure_rows(candidates: Sequence[Mapping[str, Any]]) -> list[CandidateFailureRow]:
    output: list[CandidateFailureRow] = []
    for row in candidates:
        reasons = candidate_reasons(row)
        output.append(
            CandidateFailureRow(
                timeframe=canonical_timeframe(str(row.get("timeframe", ""))),
                family_id=str(row.get("family_id", "")),
                label=str(row.get("label", "")),
                side_mapping=str(row.get("side_mapping", "")),
                tp_atr=as_float(row, "tp_atr"),
                sl_atr=as_float(row, "sl_atr"),
                hold_bars=as_int(row, "hold_bars"),
                train_events=as_int(row, "train_events"),
                validation_events=as_int(row, "validation_events"),
                test_events=as_int(row, "test_events"),
                train_positive_rate=as_float(row, "train_positive_rate"),
                validation_positive_rate=as_float(row, "validation_positive_rate"),
                test_positive_rate=as_float(row, "test_positive_rate"),
                validation_label_psi=as_float(row, "validation_label_psi"),
                test_label_psi=as_float(row, "test_label_psi"),
                train_independent_profit_factor=as_float(row, "train_independent_profit_factor"),
                validation_independent_profit_factor=as_float(row, "validation_independent_profit_factor"),
                test_independent_profit_factor=as_float(row, "test_independent_profit_factor"),
                train_mean_atr_score=as_float(row, "train_mean_atr_score"),
                validation_mean_atr_score=as_float(row, "validation_mean_atr_score"),
                test_mean_atr_score=as_float(row, "test_mean_atr_score"),
                validation_ap_lift=as_float(row, "validation_ap_lift"),
                test_ap_lift=as_float(row, "test_ap_lift"),
                validation_balanced_accuracy=as_float(row, "validation_balanced_accuracy"),
                test_balanced_accuracy=as_float(row, "test_balanced_accuracy"),
                walkforward_folds=as_int(row, "walkforward_folds"),
                walkforward_pass_folds=as_int(row, "walkforward_pass_folds"),
                walkforward_pass_ratio=as_float(row, "walkforward_pass_ratio"),
                density_gate=as_int(row, "density_gate"),
                economic_gate=as_int(row, "economic_gate"),
                static_learnability_gate=as_int(row, "static_learnability_gate"),
                walkforward_gate=as_int(row, "walkforward_gate"),
                target_family_ready_gate=as_int(row, "target_family_ready_gate"),
                failure_reason_count=len(reasons),
                primary_failure_reason=reasons[0] if reasons else "none",
                failure_reasons=json.dumps(reasons, ensure_ascii=False),
                near_miss_gate=near_miss_gate(row),
                diagnostic_score=as_float(row, "diagnostic_score"),
            )
        )
    return sorted(output, key=lambda item: (item.near_miss_gate, item.walkforward_pass_ratio, item.diagnostic_score), reverse=True)


def median_cost(cost_rows: Sequence[Mapping[str, Any]], timeframe: str, split: str) -> float:
    tf = canonical_timeframe(timeframe)
    for row in cost_rows:
        if canonical_timeframe(str(row.get("timeframe", ""))) == tf and str(row.get("split", "")) == split:
            return as_float(row, "full_spread_atr_median")
    return 0.0


def build_timeframe_summary_rows(phase179: Mapping[str, Any], candidate_rows: Sequence[CandidateFailureRow]) -> list[TimeframeSummaryRow]:
    health_by_tf: dict[str, int] = {}
    for row in phase179.get("health_rows", []):
        health_by_tf[canonical_timeframe(str(row.get("timeframe", "")))] = as_int(row, "health_gate")
    cost_rows = list(phase179.get("cost_rows", []))
    grouped: dict[str, list[CandidateFailureRow]] = defaultdict(list)
    for row in candidate_rows:
        grouped[row.timeframe].append(row)
    output: list[TimeframeSummaryRow] = []
    for timeframe, rows in grouped.items():
        best = rows[0]
        reason_counter: Counter[str] = Counter()
        for row in rows:
            reason_counter.update(decode_reasons(row.failure_reasons))
        dominant = reason_counter.most_common(1)[0][0] if reason_counter else "none"
        cost_gate_pass = sum(
            as_int(row, "cost_feasible_gate")
            for row in cost_rows
            if canonical_timeframe(str(row.get("timeframe", ""))) == timeframe
        )
        cost_split_count = sum(1 for row in cost_rows if canonical_timeframe(str(row.get("timeframe", ""))) == timeframe)
        verdict = "TARGET_NOT_READY_COST_FEASIBLE" if cost_gate_pass == cost_split_count and cost_split_count else "REVIEW_COST_OR_DATA"
        output.append(
            TimeframeSummaryRow(
                timeframe=timeframe,
                health_gate=health_by_tf.get(timeframe, 0),
                candidate_count=len(rows),
                ready_candidates=sum(row.target_family_ready_gate for row in rows),
                near_miss_candidates=sum(row.near_miss_gate for row in rows),
                cost_gate_pass_splits=cost_gate_pass,
                cost_splits=cost_split_count,
                median_spread_atr_train=median_cost(cost_rows, timeframe, "train"),
                median_spread_atr_validation=median_cost(cost_rows, timeframe, "validation"),
                median_spread_atr_test=median_cost(cost_rows, timeframe, "test"),
                best_family_id=best.family_id,
                best_family_ready_gate=best.target_family_ready_gate,
                best_walkforward_pass_ratio=best.walkforward_pass_ratio,
                best_train_independent_profit_factor=best.train_independent_profit_factor,
                best_validation_independent_profit_factor=best.validation_independent_profit_factor,
                best_test_independent_profit_factor=best.test_independent_profit_factor,
                best_validation_ap_lift=best.validation_ap_lift,
                best_test_ap_lift=best.test_ap_lift,
                best_test_balanced_accuracy=best.test_balanced_accuracy,
                dominant_failure_reason=dominant,
                verdict=verdict,
            )
        )
    return sorted(output, key=lambda row: (row.near_miss_candidates, row.best_walkforward_pass_ratio, row.best_test_independent_profit_factor), reverse=True)


def build_fold_failure_rows(walkforward_rows: Sequence[Mapping[str, Any]]) -> list[FoldFailureRow]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in walkforward_rows:
        grouped[(canonical_timeframe(str(row.get("timeframe", ""))), str(row.get("family_id", "")), str(row.get("label", "")))].append(row)
    output: list[FoldFailureRow] = []
    for (timeframe, family_id, label), rows in grouped.items():
        counter: Counter[str] = Counter()
        for row in rows:
            counter.update(decode_reasons(row.get("failure_reasons", "[]")))
        dominant = counter.most_common(1)[0][0] if counter else "none"
        output.append(
            FoldFailureRow(
                timeframe=timeframe,
                family_id=family_id,
                label=label,
                folds=len(rows),
                pass_folds=sum(as_int(row, "pass_gate") for row in rows),
                pass_ratio=safe_ratio(sum(as_int(row, "pass_gate") for row in rows), len(rows)),
                train_gate_failed_folds=int(counter.get("train_gate_failed", 0)),
                validation_gate_failed_folds=int(counter.get("validation_gate_failed", 0)),
                test_gate_failed_folds=int(counter.get("test_gate_failed", 0)),
                dominant_fold_failure_reason=dominant,
                fold_failure_reasons=json.dumps(dict(counter), ensure_ascii=False),
            )
        )
    return sorted(output, key=lambda row: (row.pass_ratio, -row.validation_gate_failed_folds, row.timeframe, row.family_id), reverse=True)


def build_failure_reason_rows(candidate_rows: Sequence[CandidateFailureRow], fold_rows: Sequence[FoldFailureRow]) -> list[FailureReasonRow]:
    candidate_counter: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for row in candidate_rows:
        for reason in decode_reasons(row.failure_reasons):
            candidate_counter[reason] += 1
            examples.setdefault(reason, f"{row.timeframe}|{row.family_id}")
    output: list[FailureReasonRow] = []
    for reason, count in candidate_counter.most_common():
        output.append(FailureReasonRow("candidate", reason, int(count), len(candidate_rows), safe_ratio(count, len(candidate_rows)), examples.get(reason, "")))
    fold_total = sum(row.folds for row in fold_rows)
    fold_counter: Counter[str] = Counter()
    fold_examples: dict[str, str] = {}
    for row in fold_rows:
        payload = json.loads(row.fold_failure_reasons)
        for reason, count in payload.items():
            fold_counter[reason] += int(count)
            fold_examples.setdefault(reason, f"{row.timeframe}|{row.family_id}")
    for reason, count in fold_counter.most_common():
        output.append(FailureReasonRow("walkforward_fold", reason, int(count), fold_total, safe_ratio(count, fold_total), fold_examples.get(reason, "")))
    return output


def build_decision_matrix(candidate_rows: Sequence[CandidateFailureRow], timeframe_rows: Sequence[TimeframeSummaryRow]) -> list[DecisionMatrixRow]:
    ready = sum(row.target_family_ready_gate for row in candidate_rows)
    near_miss = sum(row.near_miss_gate for row in candidate_rows)
    best = candidate_rows[0] if candidate_rows else None
    best_text = f"{best.timeframe}|{best.family_id}" if best else "none"
    return [
        DecisionMatrixRow(
            route_id="HIGHER_TIMEFRAME_MODEL_TRAINING",
            route_name="Train 4H/1D model now",
            status="BLOCKED",
            score=0.0,
            rank=1,
            evidence=f"ready_candidates={ready}; best={best_text}",
            recommendation="Do not train; target readiness gates did not pass.",
        ),
        DecisionMatrixRow(
            route_id="D1_TARGET_REDESIGN_ATTRIBUTION",
            route_name="Daily target failure attribution and redesign decision",
            status="RECOMMENDED_DIAGNOSTIC" if near_miss > 0 else "OPTIONAL_DIAGNOSTIC",
            score=82.0 if near_miss > 0 else 65.0,
            rank=2,
            evidence=f"near_miss_candidates={near_miss}; D1 cost feasibility is strong.",
            recommendation="If continuing, audit why D1_R1 passed only 1/5 folds and redesign daily target geometry diagnostically.",
        ),
        DecisionMatrixRow(
            route_id="NON_PIVOT_EVENT_ROUTE",
            route_name="Switch to non-pivot event targets",
            status="SECONDARY_RESEARCH",
            score=70.0,
            rank=3,
            evidence="Pivot-family definitions repeatedly fail target readiness despite better cost at higher timeframes.",
            recommendation="Keep as secondary option after daily-target failure attribution.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=4,
            evidence="No production/paper/live gate exists in Phase180A.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def build_next_plan(selected_focus: CandidateFailureRow | None) -> list[NextPlanRow]:
    focus = f"{selected_focus.timeframe}|{selected_focus.family_id}" if selected_focus else "none"
    return [
        NextPlanRow(
            1,
            "Phase180A",
            "Record higher-timeframe failure attribution",
            "Document that cost is feasible but targets are not ready.",
            "Documentation and diagnostic attribution.",
            "No model training or live/paper trading.",
            "run_logs/higher_timeframe_target_failure_attribution/latest.json",
        ),
        NextPlanRow(
            2,
            "Phase181A",
            "Daily target failure attribution / redesign decision",
            f"Focus on {focus}, especially fold transfer, test AP lift, and test balanced accuracy.",
            "Diagnostic-only redesign decision.",
            "No training, no gate relaxation.",
            "run_logs/daily_target_failure_attribution/latest.json",
        ),
        NextPlanRow(
            3,
            "Owner gate",
            "Owner reviews Phase181A before any target-family build",
            "Avoid continuing with another quick pivot-target tweak.",
            "Choose diagnostic route or pause.",
            "No production/paper/live approval.",
            "docs/WORKLOG.md and docs/PROJECT_OWNER_MAP.html updated decision",
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


def render_html(title: str, report: Phase180Report) -> str:
    tf_rows = "".join(
        f"<tr><td>{html.escape(str(row['timeframe']))}</td><td>{int(row['ready_candidates'])}/{int(row['candidate_count'])}</td>"
        f"<td>{int(row['near_miss_candidates'])}</td><td>{float(row['median_spread_atr_test']):.4f}</td>"
        f"<td>{html.escape(str(row['best_family_id']))}</td><td>{float(row['best_walkforward_pass_ratio']):.2f}</td>"
        f"<td>{html.escape(str(row['verdict']))}</td></tr>"
        for row in report.timeframe_summary_rows
    )
    cand_rows = "".join(
        f"<tr><td>{html.escape(str(row['timeframe']))}</td><td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{int(row['near_miss_gate'])}</td><td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{float(row['train_independent_profit_factor']):.3f}</td><td>{float(row['test_balanced_accuracy']):.3f}</td>"
        f"<td>{html.escape(str(row['primary_failure_reason']))}</td></tr>"
        for row in report.candidate_failure_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase180A higher-timeframe target failure attribution. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'cost_feasibility_confirmed_gate': report.cost_feasibility_confirmed_gate,
        'target_readiness_confirmed_failed_gate': report.target_readiness_confirmed_failed_gate,
        'selected_next_route_id': report.selected_next_route_id,
        'selected_next_phase': report.selected_next_phase,
        'selected_focus': report.selected_focus_timeframe + '|' + report.selected_focus_family_id,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Timeframes</h2><table><thead><tr><th>TF</th><th>Ready</th><th>Near misses</th><th>Test cost</th><th>Best</th><th>WF</th><th>Verdict</th></tr></thead><tbody>{tf_rows}</tbody></table></section>
<section class="card"><h2>Candidates</h2><table><thead><tr><th>TF</th><th>Family</th><th>Near miss</th><th>WF</th><th>Train PF</th><th>Test bAcc</th><th>Primary failure</th></tr></thead><tbody>{cand_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE180A HIGHER-TIMEFRAME TARGET FAILURE ATTRIBUTION")
        print("=" * 74)
        phase179_path = Path(args.phase179_path)
        phase179 = load_json(phase179_path)
        candidate_rows = build_candidate_failure_rows(list(phase179.get("candidate_rows", [])))
        timeframe_rows = build_timeframe_summary_rows(phase179, candidate_rows)
        fold_rows = build_fold_failure_rows(list(phase179.get("walkforward_rows", [])))
        reason_rows = build_failure_reason_rows(candidate_rows, fold_rows)
        decision_rows = build_decision_matrix(candidate_rows, timeframe_rows)
        selected_focus = candidate_rows[0] if candidate_rows else None
        next_plan = build_next_plan(selected_focus)
        ready = int(phase179.get("ready_candidates", 0) or 0)
        all_cost_feasible = all(as_int(row, "cost_feasible_gate") == 1 for row in phase179.get("cost_rows", [])) and bool(phase179.get("cost_rows", []))

        output_candidates = output_dir / "latest_candidate_failures.csv"
        output_timeframes = output_dir / "latest_timeframe_summary.csv"
        output_folds = output_dir / "latest_fold_failures.csv"
        output_reasons = output_dir / "latest_failure_reasons.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        output_plan = output_dir / "latest_next_plan.csv"
        write_csv(output_candidates, [asdict(row) for row in candidate_rows])
        write_csv(output_timeframes, [asdict(row) for row in timeframe_rows])
        write_csv(output_folds, [asdict(row) for row in fold_rows])
        write_csv(output_reasons, [asdict(row) for row in reason_rows])
        write_csv(output_decision, [asdict(row) for row in decision_rows])
        write_csv(output_plan, [asdict(row) for row in next_plan])

        root_cause = (
            "Higher timeframes materially reduce spread/ATR, but target readiness still fails because "
            "walk-forward transfer and classifier separability are insufficient. The daily D1_R1 candidate "
            "is a near-miss, not a training-ready target."
        )
        report = Phase180Report(
            phase179_path=str(phase179_path),
            source_symbol=str(phase179.get("symbol", "")),
            source_timeframes=[canonical_timeframe(str(value)) for value in phase179.get("timeframes", [])],
            source_spread_mode=str(phase179.get("spread_mode", "")),
            source_spread_value=as_float(phase179, "spread_value"),
            source_evaluated_candidates=as_int(phase179, "evaluated_candidates"),
            source_ready_candidates=ready,
            source_higher_timeframe_feasibility_gate=as_int(phase179, "higher_timeframe_feasibility_gate"),
            cost_feasibility_confirmed_gate=int(all_cost_feasible),
            target_readiness_confirmed_failed_gate=int(ready == 0),
            selected_next_route_id="D1_TARGET_FAILURE_ATTRIBUTION_AND_REDESIGN_DECISION" if any(row.near_miss_gate for row in candidate_rows) else "PAUSE_OR_NON_PIVOT_ROUTE_REVIEW",
            selected_next_phase="Phase181A — daily target failure attribution and redesign decision" if any(row.near_miss_gate for row in candidate_rows) else "Owner review / non-pivot route decision",
            selected_focus_timeframe=selected_focus.timeframe if selected_focus else "",
            selected_focus_family_id=selected_focus.family_id if selected_focus else "",
            no_training_gate=1,
            no_paper_live_gate=1,
            root_cause_summary=root_cause,
            candidate_failure_rows=[asdict(row) for row in candidate_rows],
            timeframe_summary_rows=[asdict(row) for row in timeframe_rows],
            fold_failure_rows=[asdict(row) for row in fold_rows],
            failure_reason_rows=[asdict(row) for row in reason_rows],
            decision_matrix_rows=[asdict(row) for row in decision_rows],
            next_plan_rows=[asdict(row) for row in next_plan],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidate_failures_csv=str(output_candidates),
            output_timeframe_summary_csv=str(output_timeframes),
            output_fold_failures_csv=str(output_folds),
            output_failure_reasons_csv=str(output_reasons),
            output_decision_matrix_csv=str(output_decision),
            output_next_plan_csv=str(output_plan),
            production_status="BLOCKED — Phase180A higher-timeframe failure attribution only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase180A failure attribution complete")
        print(f"  cost feasible : {report.cost_feasibility_confirmed_gate}")
        print(f"  target failed : {report.target_readiness_confirmed_failed_gate}")
        print(f"  selected next : {report.selected_next_phase}")
        print(f"  output        : {report.output_json}")
        print(f"  elapsed       : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
