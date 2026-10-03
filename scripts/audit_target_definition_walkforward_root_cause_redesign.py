"""Phase176A: target-definition walk-forward root-cause redesign audit.

Phase173A/174A/175A showed that the broker-cost-aware 1H target families and
predeclared regime subsets are not stable enough for training. This phase does
not train a model and does not build new labels. It consumes Phase174A/175A
outputs and attributes the failure by target-definition axes so the owner can
choose whether a future target-family redesign audit is warranted.

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
DEFAULT_PHASE175_PATH = Path("run_logs/hybrid_regime_walkforward_failure_attribution/latest.json")
DEFAULT_OUTPUT_DIR = Path("run_logs/target_definition_walkforward_root_cause_redesign")

FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "CA1_BRK_MID": {
        "target_label": "cost_breakout_mid",
        "geometry_profile": "mid_zone_rw24",
        "side_mapping": "breakout",
        "entry_delay_bars": 1,
        "recent_window_bars": 24,
        "pivot_zone_atr": 0.10,
        "top_position_threshold": 0.85,
        "bottom_position_threshold": 0.15,
        "tp_atr": 2.0,
        "sl_atr": 1.0,
        "reward_risk": 2.0,
        "hold_bars": 24,
    },
    "CA3_BRK_STRICT": {
        "target_label": "cost_breakout_strict",
        "geometry_profile": "strict_zone_rw24",
        "side_mapping": "breakout",
        "entry_delay_bars": 1,
        "recent_window_bars": 24,
        "pivot_zone_atr": 0.05,
        "top_position_threshold": 0.90,
        "bottom_position_threshold": 0.10,
        "tp_atr": 2.0,
        "sl_atr": 1.0,
        "reward_risk": 2.0,
        "hold_bars": 24,
    },
    "CA2_BRK_WIDE": {
        "target_label": "cost_breakout_wide",
        "geometry_profile": "wide_zone_rw48",
        "side_mapping": "breakout",
        "entry_delay_bars": 1,
        "recent_window_bars": 48,
        "pivot_zone_atr": 0.10,
        "top_position_threshold": 0.85,
        "bottom_position_threshold": 0.15,
        "tp_atr": 2.5,
        "sl_atr": 1.25,
        "reward_risk": 2.0,
        "hold_bars": 48,
    },
}

REGIME_AXIS: dict[str, str] = {
    "ALL": "baseline",
    "BUY_ONLY": "side",
    "SELL_ONLY": "side",
    "TOP_ZONE": "zone",
    "BOTTOM_ZONE": "zone",
    "SPREAD_ATR_LE_008": "cost",
    "SPREAD_ATR_LE_010": "cost",
    "ATR_GE_Q50": "atr",
    "ATR_GE_Q75": "atr",
    "ATR_LE_Q50": "atr",
    "WIDTH_GE_Q50": "range_width",
    "WIDTH_GE_Q75": "range_width",
    "ACTIVE_UTC_07_17": "session",
    "ASIA_UTC_00_06": "session",
    "RET24_POS": "momentum",
    "RET24_NEG": "momentum",
    "MOMENTUM_ALIGNED": "momentum",
    "MOMENTUM_COUNTER": "momentum",
    "BUY_MOMENTUM_ALIGNED": "side_momentum",
    "SELL_MOMENTUM_ALIGNED": "side_momentum",
    "BUY_SPREAD_ATR_LE_010": "side_cost",
    "SELL_SPREAD_ATR_LE_010": "side_cost",
}


@dataclass(frozen=True)
class AxisAttributionRow:
    axis_type: str
    axis_value: str
    candidates: int
    ready_candidates: int
    class_balance_pass: int
    economic_pass: int
    static_pass: int
    walkforward_pass: int
    mean_train_events: float
    mean_validation_events: float
    mean_test_events: float
    mean_train_positive_rate: float
    mean_validation_positive_rate: float
    mean_test_positive_rate: float
    mean_validation_ap_lift: float
    mean_test_ap_lift: float
    mean_validation_balanced_accuracy: float
    mean_test_balanced_accuracy: float
    mean_train_independent_pf: float
    mean_validation_independent_pf: float
    mean_test_independent_pf: float
    mean_train_atr_score: float
    mean_validation_atr_score: float
    mean_test_atr_score: float
    total_walkforward_folds: int
    total_walkforward_pass_folds: int
    walkforward_pass_ratio: float
    top_failure_reason: str
    top_failure_ratio: float
    verdict: str


@dataclass(frozen=True)
class TargetDefinitionRow:
    family_id: str
    target_label: str
    geometry_profile: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    tp_atr: float
    sl_atr: float
    reward_risk: float
    hold_bars: int
    candidates: int
    ready_candidates: int
    economic_pass: int
    static_pass: int
    walkforward_pass: int
    mean_train_independent_pf: float
    mean_validation_independent_pf: float
    mean_test_independent_pf: float
    mean_validation_ap_lift: float
    mean_test_ap_lift: float
    mean_test_balanced_accuracy: float
    total_walkforward_folds: int
    total_walkforward_pass_folds: int
    walkforward_pass_ratio: float
    root_failure: str
    redesign_implication: str


@dataclass(frozen=True)
class RedesignHypothesisRow:
    hypothesis_id: str
    title: str
    status: str
    evidence: str
    implication: str
    recommended_action: str
    priority: int


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
class Phase176Report:
    phase174_path: str
    phase175_path: str
    source_symbol: str
    source_timeframe: str
    source_spread_mode: str
    source_spread_value: float
    source_candidate_rows: int
    source_walkforward_rows: int
    source_walkforward_pass_rows: int
    source_walkforward_global_pass_ratio: float
    source_candidates_with_static_learnability_gate: int
    source_candidates_with_walkforward_gate: int
    source_candidates_with_ready_gate: int
    target_definitions_audited: int
    regime_axes_audited: int
    root_cause_confirmed_gate: int
    target_definition_redesign_required_gate: int
    direct_training_blocked_gate: int
    paper_live_blocked_gate: int
    selected_root_cause: str
    selected_failed_target_definition: str
    selected_failed_axis: str
    recommended_next_phase: str
    route_decision: str
    target_definition_rows: list[dict[str, Any]]
    axis_attribution_rows: list[dict[str, Any]]
    redesign_hypothesis_rows: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_target_definitions_csv: str
    output_axis_attribution_csv: str
    output_redesign_hypotheses_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit target-definition root causes after Phase174A/175A walk-forward failure.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase174-path", default=str(DEFAULT_PHASE174_PATH))
    parser.add_argument("--phase175-path", default=str(DEFAULT_PHASE175_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase176A target-definition walk-forward root-cause redesign audit")
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


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if abs(float(den)) > 1e-12 else 0.0


def mean_value(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    values = [as_float(row, key) for row in rows]
    return float(sum(values) / len(values)) if values else 0.0


def candidate_key(family_id: str, regime_rule_id: str) -> str:
    return f"{family_id}|{regime_rule_id}"


def regime_axis(rule_id: str) -> str:
    return REGIME_AXIS.get(str(rule_id), "other")


def decode_failure_reasons(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("failure_reasons", "[]")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        data = json.loads(str(raw))
        if isinstance(data, list):
            return [str(item) for item in data]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def group_walkforward(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[candidate_key(str(row.get("family_id", "")), str(row.get("regime_rule_id", "")))].append(row)
    return grouped


def axis_key(row: Mapping[str, Any], axis_type: str) -> str:
    family_id = str(row.get("family_id", ""))
    rule_id = str(row.get("regime_rule_id", ""))
    spec = FAMILY_SPECS.get(family_id, {})
    if axis_type == "family":
        return family_id
    if axis_type == "geometry_profile":
        return str(spec.get("geometry_profile", "unknown"))
    if axis_type == "hold_bars":
        return str(spec.get("hold_bars", "unknown"))
    if axis_type == "tp_sl":
        return f"tp{spec.get('tp_atr', 'na')}_sl{spec.get('sl_atr', 'na')}"
    if axis_type == "regime_axis":
        return regime_axis(rule_id)
    if axis_type == "regime_rule":
        return rule_id
    return "unknown"


def dominant_failure(rows: Sequence[Mapping[str, Any]]) -> tuple[str, float]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(decode_failure_reasons(row))
    if not counter:
        return "none", 0.0
    reason, count = counter.most_common(1)[0]
    return reason, safe_ratio(count, len(rows))


def fold_pass_stats(wf_rows: Sequence[Mapping[str, Any]]) -> tuple[int, int, float]:
    folds = len(wf_rows)
    passed = sum(as_int(row, "pass_gate") for row in wf_rows)
    return folds, passed, safe_ratio(passed, folds)


def axis_verdict(rows: Sequence[Mapping[str, Any]], wf_rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "NO_DATA"
    ready = sum(as_int(row, "regime_candidate_ready_gate") for row in rows)
    if ready > 0:
        return "READY_CANDIDATE_PRESENT"
    _folds, passed, ratio = fold_pass_stats(wf_rows)
    if passed == 0 and ratio == 0.0:
        return "REJECTED_WALKFORWARD_ZERO"
    if sum(as_int(row, "economic_gate") for row in rows) == 0:
        return "REJECTED_ECONOMICS"
    if sum(as_int(row, "static_learnability_gate") for row in rows) == 0:
        return "REJECTED_STATIC_LEARNABILITY"
    return "REJECTED_MIXED_FAILURES"


def build_axis_rows(
    candidates: Sequence[Mapping[str, Any]],
    candidate_failures: Sequence[Mapping[str, Any]],
    walkforward_rows: Sequence[Mapping[str, Any]],
) -> list[AxisAttributionRow]:
    failure_by_key = {candidate_key(str(row.get("family_id", "")), str(row.get("regime_rule_id", ""))): row for row in candidate_failures}
    wf_by_key = group_walkforward(walkforward_rows)
    axis_types = ("family", "geometry_profile", "hold_bars", "tp_sl", "regime_axis", "regime_rule")
    output: list[AxisAttributionRow] = []
    for axis_type in axis_types:
        grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        grouped_failures: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        grouped_wf: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in candidates:
            family_id = str(row.get("family_id", ""))
            rule_id = str(row.get("regime_rule_id", ""))
            key = candidate_key(family_id, rule_id)
            axis_value = axis_key(row, axis_type)
            grouped[axis_value].append(row)
            if key in failure_by_key:
                grouped_failures[axis_value].append(failure_by_key[key])
            grouped_wf[axis_value].extend(wf_by_key.get(key, []))
        for axis_value, rows in grouped.items():
            wf_rows = grouped_wf.get(axis_value, [])
            folds, passed, pass_ratio = fold_pass_stats(wf_rows)
            top_reason, top_ratio = dominant_failure(grouped_failures.get(axis_value, []))
            output.append(
                AxisAttributionRow(
                    axis_type=axis_type,
                    axis_value=axis_value,
                    candidates=len(rows),
                    ready_candidates=sum(as_int(row, "regime_candidate_ready_gate") for row in rows),
                    class_balance_pass=sum(as_int(row, "class_balance_gate") for row in rows),
                    economic_pass=sum(as_int(row, "economic_gate") for row in rows),
                    static_pass=sum(as_int(row, "static_learnability_gate") for row in rows),
                    walkforward_pass=sum(as_int(row, "walkforward_learnability_gate") for row in rows),
                    mean_train_events=mean_value(rows, "train_events"),
                    mean_validation_events=mean_value(rows, "validation_events"),
                    mean_test_events=mean_value(rows, "test_events"),
                    mean_train_positive_rate=mean_value(rows, "train_positive_rate"),
                    mean_validation_positive_rate=mean_value(rows, "validation_positive_rate"),
                    mean_test_positive_rate=mean_value(rows, "test_positive_rate"),
                    mean_validation_ap_lift=mean_value(rows, "validation_ap_lift"),
                    mean_test_ap_lift=mean_value(rows, "test_ap_lift"),
                    mean_validation_balanced_accuracy=mean_value(rows, "validation_balanced_accuracy"),
                    mean_test_balanced_accuracy=mean_value(rows, "test_balanced_accuracy"),
                    mean_train_independent_pf=mean_value(rows, "train_independent_profit_factor"),
                    mean_validation_independent_pf=mean_value(rows, "validation_independent_profit_factor"),
                    mean_test_independent_pf=mean_value(rows, "test_independent_profit_factor"),
                    mean_train_atr_score=mean_value(rows, "train_mean_atr_score"),
                    mean_validation_atr_score=mean_value(rows, "validation_mean_atr_score"),
                    mean_test_atr_score=mean_value(rows, "test_mean_atr_score"),
                    total_walkforward_folds=folds,
                    total_walkforward_pass_folds=passed,
                    walkforward_pass_ratio=pass_ratio,
                    top_failure_reason=top_reason,
                    top_failure_ratio=top_ratio,
                    verdict=axis_verdict(rows, wf_rows),
                )
            )
    return sorted(output, key=lambda row: (row.axis_type, row.verdict, row.axis_value))


def family_redesign_implication(family_id: str, row: AxisAttributionRow) -> str:
    spec = FAMILY_SPECS.get(family_id, {})
    if row.walkforward_pass_ratio == 0.0 and row.static_pass == 0:
        return (
            f"Freeze {family_id}; current {spec.get('geometry_profile', 'geometry')} with "
            f"hold={spec.get('hold_bars', 'na')} and TP/SL={spec.get('tp_atr', 'na')}/{spec.get('sl_atr', 'na')} "
            "does not transfer. Future redesign must change target definition before model training."
        )
    return "No trainable implication; diagnostic-only review required."


def build_target_definition_rows(axis_rows: Sequence[AxisAttributionRow]) -> list[TargetDefinitionRow]:
    by_family = {row.axis_value: row for row in axis_rows if row.axis_type == "family"}
    output: list[TargetDefinitionRow] = []
    for family_id, spec in FAMILY_SPECS.items():
        row = by_family.get(family_id)
        if row is None:
            continue
        output.append(
            TargetDefinitionRow(
                family_id=family_id,
                target_label=str(spec["target_label"]),
                geometry_profile=str(spec["geometry_profile"]),
                side_mapping=str(spec["side_mapping"]),
                entry_delay_bars=int(spec["entry_delay_bars"]),
                recent_window_bars=int(spec["recent_window_bars"]),
                pivot_zone_atr=float(spec["pivot_zone_atr"]),
                top_position_threshold=float(spec["top_position_threshold"]),
                bottom_position_threshold=float(spec["bottom_position_threshold"]),
                tp_atr=float(spec["tp_atr"]),
                sl_atr=float(spec["sl_atr"]),
                reward_risk=float(spec["reward_risk"]),
                hold_bars=int(spec["hold_bars"]),
                candidates=int(row.candidates),
                ready_candidates=int(row.ready_candidates),
                economic_pass=int(row.economic_pass),
                static_pass=int(row.static_pass),
                walkforward_pass=int(row.walkforward_pass),
                mean_train_independent_pf=float(row.mean_train_independent_pf),
                mean_validation_independent_pf=float(row.mean_validation_independent_pf),
                mean_test_independent_pf=float(row.mean_test_independent_pf),
                mean_validation_ap_lift=float(row.mean_validation_ap_lift),
                mean_test_ap_lift=float(row.mean_test_ap_lift),
                mean_test_balanced_accuracy=float(row.mean_test_balanced_accuracy),
                total_walkforward_folds=int(row.total_walkforward_folds),
                total_walkforward_pass_folds=int(row.total_walkforward_pass_folds),
                walkforward_pass_ratio=float(row.walkforward_pass_ratio),
                root_failure=str(row.top_failure_reason),
                redesign_implication=family_redesign_implication(family_id, row),
            )
        )
    return output


def build_hypotheses(axis_rows: Sequence[AxisAttributionRow], phase175: Mapping[str, Any]) -> list[RedesignHypothesisRow]:
    failure_rows = list(phase175.get("failure_reason_rows", []))
    candidate_failure = {str(row.get("reason")): row for row in failure_rows if row.get("scope") == "candidate"}
    wf_failure = {str(row.get("reason")): row for row in failure_rows if row.get("scope") == "walkforward_fold"}
    train_neg_ratio = as_float(candidate_failure.get("train_negative_expectancy_failed", {}), "ratio")
    test_bacc_ratio = as_float(candidate_failure.get("test_balanced_accuracy_failed", {}), "ratio")
    wf_pass_ratio = as_float(phase175, "walkforward_global_pass_ratio")
    fold_pf_ratio = as_float(wf_failure.get("test_raw_economics_failed", {}), "ratio")
    density_ratio = as_float(wf_failure.get("test_density_failed", {}), "ratio")
    session_rows = [row for row in axis_rows if row.axis_type == "regime_axis" and row.axis_value == "session"]
    session_verdict = session_rows[0].verdict if session_rows else "NO_DATA"
    return [
        RedesignHypothesisRow(
            hypothesis_id="H1_TARGET_DEFINITION_MISMATCH",
            title="Current target definitions do not produce stable walk-forward classification targets",
            status="SUPPORTED" if wf_pass_ratio == 0.0 else "MIXED",
            evidence=f"walkforward_global_pass_ratio={wf_pass_ratio:.4f}; static pass candidates={phase175.get('candidates_with_static_learnability_gate', 0)}",
            implication="Do not train on CA1/CA3/CA2 targets. A future phase must change target definition before model design.",
            recommended_action="Run a diagnostic-only target-definition redesign audit by payoff horizon, bracket, and fold stability.",
            priority=1,
        ),
        RedesignHypothesisRow(
            hypothesis_id="H2_TRAIN_EXPECTANCY_INSTABILITY",
            title="Many pockets are validation/test positive but train-negative",
            status="SUPPORTED" if train_neg_ratio >= 0.50 else "MIXED",
            evidence=f"train_negative_expectancy_failed ratio={train_neg_ratio:.4f}",
            implication="Selection is vulnerable to overfitting future pockets that were not economically present in train.",
            recommended_action="Require train-side raw expectancy and fold-local economics before allowing any candidate to proceed.",
            priority=2,
        ),
        RedesignHypothesisRow(
            hypothesis_id="H3_CLASSIFIER_SIGNAL_NOT_STABLE",
            title="Balanced accuracy remains around chance for most candidates",
            status="SUPPORTED" if test_bacc_ratio >= 0.75 else "MIXED",
            evidence=f"test_balanced_accuracy_failed ratio={test_bacc_ratio:.4f}",
            implication="Feature/model changes should not be attempted until the target labels themselves produce stable separability.",
            recommended_action="Audit payoff labels by horizon and side before building neural/deep learners.",
            priority=3,
        ),
        RedesignHypothesisRow(
            hypothesis_id="H4_RAW_ECONOMICS_DO_NOT_TRANSFER_BY_FOLD",
            title="Raw validation/test economics fail frequently at fold level",
            status="SUPPORTED" if fold_pf_ratio >= 0.50 else "MIXED",
            evidence=f"walk-forward test_raw_economics_failed ratio={fold_pf_ratio:.4f}",
            implication="Regime filters are not sufficient; payoff geometry and event timing should be re-audited.",
            recommended_action="Compare alternative TP/SL/hold families as diagnostics only, with train-first and walk-forward gates.",
            priority=4,
        ),
        RedesignHypothesisRow(
            hypothesis_id="H5_DENSITY_IS_SECONDARY_NOT_PRIMARY",
            title="Density failures exist but are not the dominant universal cause",
            status="SUPPORTED" if density_ratio < 0.50 else "MIXED",
            evidence=f"walk-forward test_density_failed ratio={density_ratio:.4f}",
            implication="Simply widening/narrowing events is unlikely to fix the route by itself.",
            recommended_action="Treat density as a constraint, not the primary optimization objective.",
            priority=5,
        ),
        RedesignHypothesisRow(
            hypothesis_id="H6_SESSION_FILTERS_NOT_ENOUGH",
            title="Session filters created pockets but did not create a route",
            status="SUPPORTED" if session_verdict.startswith("REJECTED") else "MIXED",
            evidence=f"session axis verdict={session_verdict}",
            implication="Do not proceed with Asia/active-session rules as trading targets without a new target design.",
            recommended_action="Keep sessions as explanatory axes in the next diagnostic, not as standalone approvals.",
            priority=6,
        ),
    ]


def build_decision_matrix() -> list[DecisionMatrixRow]:
    return [
        DecisionMatrixRow(
            route_id="FREEZE_PHASE173_174_TARGETS",
            route_name="Freeze current broker-cost-aware 1H target/regime definitions",
            status="MANDATORY",
            score=100.0,
            rank=1,
            evidence="Phase173A, Phase174A, and Phase175A all have ready gates 0.",
            recommendation="Do not train CA1/CA3/CA2 or their regime subsets.",
        ),
        DecisionMatrixRow(
            route_id="TARGET_FAMILY_REDESIGN_DIAGNOSTIC",
            route_name="Diagnostic-only target family redesign audit",
            status="RECOMMENDED_DIAGNOSTIC",
            score=86.0,
            rank=2,
            evidence="Failure attribution indicates target/regime instability rather than model capacity.",
            recommendation="Owner may authorize a future Phase177A candidate target-definition redesign audit.",
        ),
        DecisionMatrixRow(
            route_id="TRAIN_MODEL_NOW",
            route_name="Train any model on Phase173/174 targets",
            status="BLOCKED",
            score=0.0,
            rank=3,
            evidence="No static/walk-forward ready candidate exists.",
            recommendation="Blocked until a future diagnostic route passes gates.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=4,
            evidence="No trade-ready candidate and no production approval.",
            recommendation="No Phase134, no paper shadow, no live trading.",
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


def render_html(title: str, report: Phase176Report) -> str:
    target_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td><td>{html.escape(str(row['geometry_profile']))}</td>"
        f"<td>{int(row['economic_pass'])}/{int(row['candidates'])}</td>"
        f"<td>{int(row['static_pass'])}/{int(row['candidates'])}</td>"
        f"<td>{int(row['total_walkforward_pass_folds'])}/{int(row['total_walkforward_folds'])}</td>"
        f"<td>{html.escape(str(row['root_failure']))}</td></tr>"
        for row in report.target_definition_rows
    )
    axis_rows = "".join(
        f"<tr><td>{html.escape(str(row['axis_type']))}</td><td>{html.escape(str(row['axis_value']))}</td>"
        f"<td>{int(row['ready_candidates'])}/{int(row['candidates'])}</td>"
        f"<td>{int(row['total_walkforward_pass_folds'])}/{int(row['total_walkforward_folds'])}</td>"
        f"<td>{html.escape(str(row['top_failure_reason']))}</td><td>{html.escape(str(row['verdict']))}</td></tr>"
        for row in report.axis_attribution_rows[:80]
    )
    hypothesis_rows = "".join(
        f"<tr><td>{html.escape(str(row['hypothesis_id']))}</td><td>{html.escape(str(row['status']))}</td>"
        f"<td>{html.escape(str(row['evidence']))}</td><td>{html.escape(str(row['recommended_action']))}</td></tr>"
        for row in report.redesign_hypothesis_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase176A target-definition walk-forward root-cause redesign audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_decision': report.route_decision,
        'selected_root_cause': report.selected_root_cause,
        'target_definition_redesign_required_gate': report.target_definition_redesign_required_gate,
        'direct_training_blocked_gate': report.direct_training_blocked_gate,
        'paper_live_blocked_gate': report.paper_live_blocked_gate,
        'recommended_next_phase': report.recommended_next_phase,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Target definitions</h2><table><thead><tr><th>Family</th><th>Geometry</th><th>Economic pass</th><th>Static pass</th><th>WF pass folds</th><th>Root failure</th></tr></thead><tbody>{target_rows}</tbody></table></section>
<section class="card"><h2>Axis attribution</h2><table><thead><tr><th>Axis</th><th>Value</th><th>Ready</th><th>WF folds</th><th>Top failure</th><th>Verdict</th></tr></thead><tbody>{axis_rows}</tbody></table></section>
<section class="card"><h2>Redesign hypotheses</h2><table><thead><tr><th>Hypothesis</th><th>Status</th><th>Evidence</th><th>Action</th></tr></thead><tbody>{hypothesis_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE176A TARGET-DEFINITION WALK-FORWARD ROOT-CAUSE REDESIGN AUDIT")
        print("=" * 74)
        phase174_path = Path(args.phase174_path)
        phase175_path = Path(args.phase175_path)
        phase174 = load_json(phase174_path)
        phase175 = load_json(phase175_path)
        candidates = list(phase174.get("candidate_rows", []))
        candidate_failures = list(phase175.get("candidate_failure_rows", []))
        walkforward_rows = list(phase174.get("walkforward_rows", []))
        axis_rows = build_axis_rows(candidates, candidate_failures, walkforward_rows)
        target_rows = build_target_definition_rows(axis_rows)
        hypotheses = build_hypotheses(axis_rows, phase175)
        decision_rows = build_decision_matrix()

        selected_axis_row = next((row for row in axis_rows if row.axis_type == "family" and row.axis_value == "CA1_BRK_MID"), axis_rows[0] if axis_rows else None)
        selected_root_cause = "target_definition_static_and_walkforward_instability"
        selected_failed_definition = selected_axis_row.axis_value if selected_axis_row else ""
        selected_failed_axis = f"{selected_axis_row.axis_type}:{selected_axis_row.axis_value}" if selected_axis_row else ""

        output_target = output_dir / "latest_target_definitions.csv"
        output_axis = output_dir / "latest_axis_attribution.csv"
        output_hypotheses = output_dir / "latest_redesign_hypotheses.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        write_csv(output_target, [asdict(row) for row in target_rows])
        write_csv(output_axis, [asdict(row) for row in axis_rows])
        write_csv(output_hypotheses, [asdict(row) for row in hypotheses])
        write_csv(output_decision, [asdict(row) for row in decision_rows])

        report = Phase176Report(
            phase174_path=str(phase174_path),
            phase175_path=str(phase175_path),
            source_symbol=str(phase174.get("symbol", phase175.get("source_symbol", ""))),
            source_timeframe=str(phase174.get("timeframe", phase175.get("source_timeframe", ""))),
            source_spread_mode=str(phase174.get("spread_mode", phase175.get("source_spread_mode", ""))),
            source_spread_value=as_float(phase174, "spread_value", as_float(phase175, "source_spread_value")),
            source_candidate_rows=len(candidates),
            source_walkforward_rows=len(walkforward_rows),
            source_walkforward_pass_rows=as_int(phase175, "walkforward_pass_rows"),
            source_walkforward_global_pass_ratio=as_float(phase175, "walkforward_global_pass_ratio"),
            source_candidates_with_static_learnability_gate=as_int(phase175, "candidates_with_static_learnability_gate"),
            source_candidates_with_walkforward_gate=as_int(phase175, "candidates_with_walkforward_gate"),
            source_candidates_with_ready_gate=as_int(phase175, "candidates_with_ready_gate"),
            target_definitions_audited=len(target_rows),
            regime_axes_audited=len([row for row in axis_rows if row.axis_type == "regime_axis"]),
            root_cause_confirmed_gate=1,
            target_definition_redesign_required_gate=1,
            direct_training_blocked_gate=1,
            paper_live_blocked_gate=1,
            selected_root_cause=selected_root_cause,
            selected_failed_target_definition=selected_failed_definition,
            selected_failed_axis=selected_failed_axis,
            recommended_next_phase="Phase177A — walk-forward target-family redesign candidate audit",
            route_decision="CURRENT_TARGET_DEFINITIONS_REJECTED_REDESIGN_DIAGNOSTIC_ONLY",
            target_definition_rows=[asdict(row) for row in target_rows],
            axis_attribution_rows=[asdict(row) for row in axis_rows],
            redesign_hypothesis_rows=[asdict(row) for row in hypotheses],
            decision_matrix_rows=[asdict(row) for row in decision_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_target_definitions_csv=str(output_target),
            output_axis_attribution_csv=str(output_axis),
            output_redesign_hypotheses_csv=str(output_hypotheses),
            output_decision_matrix_csv=str(output_decision),
            production_status="BLOCKED — Phase176A target-definition root-cause audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase176A target-definition root-cause audit complete")
        print(f"  target definitions : {report.target_definitions_audited}")
        print(f"  regime axes        : {report.regime_axes_audited}")
        print(f"  root cause gate    : {report.root_cause_confirmed_gate}")
        print(f"  training blocked   : {report.direct_training_blocked_gate}")
        print(f"  route decision     : {report.route_decision}")
        print(f"  output             : {report.output_json}")
        print(f"  elapsed            : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
