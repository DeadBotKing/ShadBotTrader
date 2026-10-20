"""Phase174A: hybrid/regime-first target redesign decision audit.

Phase173A showed that the broker-cost-aware 1H target families are structurally
stable but not learnable as broad event universes. This phase stays diagnostic:
it tests predeclared regime/side/session filters around those families and asks
whether any filtered target universe has stable class balance, raw economics,
static learnability, and walk-forward learnability before any model-training
phase is allowed.

Research-only. No production model, paper shadow, live trading, or Phase134.
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
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_broker_cost_aware_1h_target_family import (  # noqa: E402
    DEFAULT_STORAGE,
    LABEL_NEGATIVE,
    LABEL_POSITIVE,
    LABEL_TIMEOUT,
    EventOutcome,
    TargetFamilySpec,
    label_psi,
    parse_families,
    profit_factor,
)
from audit_broker_cost_aware_1h_target_learnability import (  # noqa: E402
    DEFAULT_SELECTED_FAMILIES,
    CentroidBinaryModel,
    EventFeatureRow,
    build_family_dataset,
    build_feature_rows,
    evaluate_split,
    matrix_from_rows,
    split_rows_by_name,
)
from audit_pivot_1h_entry_feasibility import read_ohlc_frame, resolve_flat_path_arg  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_regime_first_target_redesign")
DEFAULT_REGIME_RULES = (
    "ALL;BUY_ONLY;SELL_ONLY;TOP_ZONE;BOTTOM_ZONE;"
    "SPREAD_ATR_LE_008;SPREAD_ATR_LE_010;"
    "ATR_GE_Q50;ATR_GE_Q75;ATR_LE_Q50;"
    "WIDTH_GE_Q50;WIDTH_GE_Q75;"
    "ACTIVE_UTC_07_17;ASIA_UTC_00_06;"
    "RET24_POS;RET24_NEG;"
    "MOMENTUM_ALIGNED;MOMENTUM_COUNTER;"
    "BUY_MOMENTUM_ALIGNED;SELL_MOMENTUM_ALIGNED;"
    "BUY_SPREAD_ATR_LE_010;SELL_SPREAD_ATR_LE_010"
)

REGIME_RULE_LABELS: dict[str, str] = {
    "ALL": "all_events_baseline",
    "BUY_ONLY": "buy_side_only",
    "SELL_ONLY": "sell_side_only",
    "TOP_ZONE": "top_zone_only",
    "BOTTOM_ZONE": "bottom_zone_only",
    "SPREAD_ATR_LE_008": "spread_to_atr_le_0.08",
    "SPREAD_ATR_LE_010": "spread_to_atr_le_0.10",
    "ATR_GE_Q50": "atr_high_half",
    "ATR_GE_Q75": "atr_top_quartile",
    "ATR_LE_Q50": "atr_low_half",
    "WIDTH_GE_Q50": "recent_width_high_half",
    "WIDTH_GE_Q75": "recent_width_top_quartile",
    "ACTIVE_UTC_07_17": "active_utc_07_17",
    "ASIA_UTC_00_06": "asia_utc_00_06",
    "RET24_POS": "positive_24h_return",
    "RET24_NEG": "negative_24h_return",
    "MOMENTUM_ALIGNED": "side_aligned_with_24h_return",
    "MOMENTUM_COUNTER": "side_counter_to_24h_return",
    "BUY_MOMENTUM_ALIGNED": "buy_side_positive_24h_return",
    "SELL_MOMENTUM_ALIGNED": "sell_side_negative_24h_return",
    "BUY_SPREAD_ATR_LE_010": "buy_side_spread_to_atr_le_0.10",
    "SELL_SPREAD_ATR_LE_010": "sell_side_spread_to_atr_le_0.10",
}


@dataclass(frozen=True)
class RegimeContext:
    atr_q50: float
    atr_q75: float
    width_q50: float
    width_q75: float


@dataclass(frozen=True)
class RegimeSplitRow:
    family_id: str
    family_label: str
    regime_rule_id: str
    regime_label: str
    split: str
    events: int
    positives: int
    negatives: int
    timeouts: int
    positive_rate: float
    base_ap: float
    model_ap: float
    ap_lift: float
    balanced_accuracy: float
    f1: float
    threshold: float
    buy_events: int
    sell_events: int
    label_psi_vs_train: float
    mean_atr_score: float
    sum_atr_score: float
    independent_profit_factor: float
    event_coverage_vs_family_split: float


@dataclass(frozen=True)
class RegimeWalkForwardRow:
    family_id: str
    family_label: str
    regime_rule_id: str
    regime_label: str
    fold: int
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_ap_lift: float
    test_ap_lift: float
    validation_balanced_accuracy: float
    test_balanced_accuracy: float
    validation_independent_profit_factor: float
    test_independent_profit_factor: float
    validation_label_psi: float
    test_label_psi: float
    pass_gate: int


@dataclass(frozen=True)
class RegimeCandidateRow:
    family_id: str
    family_label: str
    regime_rule_id: str
    regime_label: str
    train_events: int
    validation_events: int
    test_events: int
    validation_event_coverage: float
    test_event_coverage: float
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_ap_lift: float
    validation_ap_lift: float
    test_ap_lift: float
    validation_balanced_accuracy: float
    test_balanced_accuracy: float
    validation_f1: float
    test_f1: float
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
    warnings: str


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
class Phase174Report:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    spread_mode: str
    spread_value: float
    candidate_families: int
    regime_rules: int
    evaluated_regime_candidates: int
    ready_regime_candidates: int
    selected_family_id: str
    selected_regime_rule_id: str
    selected_regime_label: str
    selected_regime_ready_gate: int
    selected_validation_ap_lift: float
    selected_test_ap_lift: float
    selected_validation_independent_profit_factor: float
    selected_test_independent_profit_factor: float
    selected_walkforward_pass_ratio: float
    hybrid_regime_first_ready_gate: int
    recommendation: str
    candidate_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_decision_matrix_csv: str
    output_dataset_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit predeclared hybrid/regime-first target redesign candidates after Phase173A failed learnability.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--families", default=DEFAULT_SELECTED_FAMILIES)
    parser.add_argument("--regime-rules", default=DEFAULT_REGIME_RULES)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.4)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=24)
    parser.add_argument("--fold-train-bars", type=int, default=18000)
    parser.add_argument("--fold-validation-bars", type=int, default=4000)
    parser.add_argument("--fold-test-bars", type=int, default=4000)
    parser.add_argument("--fold-step-bars", type=int, default=4000)
    parser.add_argument("--max-folds", type=int, default=0)
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
    parser.add_argument("--max-dataset-rows", type=int, default=20000)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase174A hybrid/regime-first target redesign audit")
    return parser.parse_args(argv)


def parse_regime_rules(text: str) -> list[str]:
    raw = str(text or DEFAULT_REGIME_RULES).replace(",", ";")
    rules: list[str] = []
    for item in raw.split(";"):
        rule = item.strip().upper()
        if not rule:
            continue
        if rule not in REGIME_RULE_LABELS:
            raise RuntimeError(f"Unknown regime rule '{rule}'. Allowed: {', '.join(sorted(REGIME_RULE_LABELS))}")
        if rule not in rules:
            rules.append(rule)
    return rules or parse_regime_rules(DEFAULT_REGIME_RULES)


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if abs(float(denominator)) > 1e-12 else 0.0


def timestamp_hour(row: EventFeatureRow) -> int:
    try:
        value = pd.to_datetime(row.timestamp, utc=True, errors="coerce")
        if pd.isna(value):
            return 0
        return int(value.hour)
    except Exception:
        return 0


def build_regime_context(train_rows: Sequence[EventFeatureRow]) -> RegimeContext:
    atr_values = np.asarray([float(row.atr) for row in train_rows], dtype=np.float64)
    width_values = np.asarray([float(row.recent_width_atr) for row in train_rows], dtype=np.float64)
    if len(atr_values) == 0:
        atr_values = np.asarray([0.0], dtype=np.float64)
    if len(width_values) == 0:
        width_values = np.asarray([0.0], dtype=np.float64)
    return RegimeContext(
        atr_q50=float(np.quantile(atr_values, 0.50)),
        atr_q75=float(np.quantile(atr_values, 0.75)),
        width_q50=float(np.quantile(width_values, 0.50)),
        width_q75=float(np.quantile(width_values, 0.75)),
    )


def row_passes_regime(row: EventFeatureRow, rule_id: str, context: RegimeContext) -> bool:
    rule = str(rule_id).upper()
    hour = timestamp_hour(row)
    buy = row.side == "BUY"
    sell = row.side == "SELL"
    momentum_aligned = (buy and float(row.ret_24_atr) > 0.0) or (sell and float(row.ret_24_atr) < 0.0)
    momentum_counter = (buy and float(row.ret_24_atr) < 0.0) or (sell and float(row.ret_24_atr) > 0.0)
    if rule == "ALL":
        return True
    if rule == "BUY_ONLY":
        return buy
    if rule == "SELL_ONLY":
        return sell
    if rule == "TOP_ZONE":
        return float(row.zone_top) > 0.5
    if rule == "BOTTOM_ZONE":
        return float(row.zone_bottom) > 0.5
    if rule == "SPREAD_ATR_LE_008":
        return float(row.spread_to_atr) <= 0.08
    if rule == "SPREAD_ATR_LE_010":
        return float(row.spread_to_atr) <= 0.10
    if rule == "ATR_GE_Q50":
        return float(row.atr) >= float(context.atr_q50)
    if rule == "ATR_GE_Q75":
        return float(row.atr) >= float(context.atr_q75)
    if rule == "ATR_LE_Q50":
        return float(row.atr) <= float(context.atr_q50)
    if rule == "WIDTH_GE_Q50":
        return float(row.recent_width_atr) >= float(context.width_q50)
    if rule == "WIDTH_GE_Q75":
        return float(row.recent_width_atr) >= float(context.width_q75)
    if rule == "ACTIVE_UTC_07_17":
        return 7 <= hour <= 17
    if rule == "ASIA_UTC_00_06":
        return 0 <= hour <= 6
    if rule == "RET24_POS":
        return float(row.ret_24_atr) > 0.0
    if rule == "RET24_NEG":
        return float(row.ret_24_atr) < 0.0
    if rule == "MOMENTUM_ALIGNED":
        return momentum_aligned
    if rule == "MOMENTUM_COUNTER":
        return momentum_counter
    if rule == "BUY_MOMENTUM_ALIGNED":
        return buy and float(row.ret_24_atr) > 0.0
    if rule == "SELL_MOMENTUM_ALIGNED":
        return sell and float(row.ret_24_atr) < 0.0
    if rule == "BUY_SPREAD_ATR_LE_010":
        return buy and float(row.spread_to_atr) <= 0.10
    if rule == "SELL_SPREAD_ATR_LE_010":
        return sell and float(row.spread_to_atr) <= 0.10
    raise RuntimeError(f"Unknown regime rule '{rule_id}'")


def filter_rows_by_regime(rows: Sequence[EventFeatureRow], rule_id: str, context: RegimeContext) -> list[EventFeatureRow]:
    return [row for row in rows if row_passes_regime(row, rule_id, context)]


def economic_summary(rows: Sequence[EventFeatureRow]) -> dict[str, float]:
    scores = [float(row.atr_score) for row in rows]
    return {
        "mean_atr_score": float(np.mean(scores)) if scores else 0.0,
        "sum_atr_score": float(np.sum(scores)) if scores else 0.0,
        "independent_profit_factor": profit_factor(scores),
    }


def label_distribution(rows: Sequence[EventFeatureRow]) -> dict[str, float]:
    total = len(rows)
    if total == 0:
        return {LABEL_POSITIVE: 0.0, LABEL_NEGATIVE: 0.0, LABEL_TIMEOUT: 0.0}
    return {
        LABEL_POSITIVE: sum(1 for row in rows if row.label == LABEL_POSITIVE) / total,
        LABEL_NEGATIVE: sum(1 for row in rows if row.label == LABEL_NEGATIVE) / total,
        LABEL_TIMEOUT: sum(1 for row in rows if row.label == LABEL_TIMEOUT) / total,
    }


def evaluate_regime_split(
    model: CentroidBinaryModel,
    rows: Sequence[EventFeatureRow],
    train_dist: Mapping[str, float] | None,
    family: TargetFamilySpec,
    rule_id: str,
    split: str,
    base_family_events: int,
) -> RegimeSplitRow:
    base = evaluate_split(model, rows, train_dist, family.family_id, split)
    econ = economic_summary(rows)
    return RegimeSplitRow(
        family_id=family.family_id,
        family_label=family.label,
        regime_rule_id=rule_id,
        regime_label=REGIME_RULE_LABELS[rule_id],
        split=split,
        events=int(base.events),
        positives=int(base.positives),
        negatives=int(base.negatives),
        timeouts=int(base.timeouts),
        positive_rate=float(base.positive_rate),
        base_ap=float(base.base_ap),
        model_ap=float(base.model_ap),
        ap_lift=float(base.ap_lift),
        balanced_accuracy=float(base.balanced_accuracy),
        f1=float(base.f1),
        threshold=float(base.threshold),
        buy_events=int(base.buy_events),
        sell_events=int(base.sell_events),
        label_psi_vs_train=float(base.label_psi_vs_train),
        mean_atr_score=float(econ["mean_atr_score"]),
        sum_atr_score=float(econ["sum_atr_score"]),
        independent_profit_factor=float(econ["independent_profit_factor"]),
        event_coverage_vs_family_split=safe_rate(len(rows), base_family_events),
    )


def fit_centroid_or_empty(train_rows: Sequence[EventFeatureRow]) -> CentroidBinaryModel:
    x_train, y_train, _sides, _labels = matrix_from_rows(train_rows)
    return CentroidBinaryModel().fit(x_train, y_train)


def static_regime_learnability(
    family: TargetFamilySpec,
    dataset_rows: Sequence[EventFeatureRow],
    rule_id: str,
) -> list[RegimeSplitRow]:
    by_split = split_rows_by_name(dataset_rows)
    context = build_regime_context(by_split["train"])
    filtered = {
        split: filter_rows_by_regime(rows, rule_id, context)
        for split, rows in by_split.items()
    }
    model = fit_centroid_or_empty(filtered["train"])
    train_dist = label_distribution(filtered["train"])
    return [
        evaluate_regime_split(model, filtered["train"], None, family, rule_id, "train", len(by_split["train"])),
        evaluate_regime_split(model, filtered["validation"], train_dist, family, rule_id, "validation", len(by_split["validation"])),
        evaluate_regime_split(model, filtered["test"], train_dist, family, rule_id, "test", len(by_split["test"])),
    ]


def split_class_gate(split: RegimeSplitRow, args: argparse.Namespace, split_name: str) -> int:
    minimum = {
        "train": int(args.min_train_events),
        "validation": int(args.min_validation_events),
        "test": int(args.min_test_events),
    }.get(split_name, int(args.min_test_events))
    return int(
        int(split.events) >= minimum
        and float(split.positive_rate) >= float(args.min_positive_rate)
        and float(split.positive_rate) <= float(args.max_positive_rate)
    )


def split_static_pass(split: RegimeSplitRow, args: argparse.Namespace, split_name: str) -> int:
    min_pf = {
        "train": float(args.min_train_independent_pf),
        "validation": float(args.min_validation_independent_pf),
        "test": float(args.min_test_independent_pf),
    }.get(split_name, float(args.min_test_independent_pf))
    return int(
        split_class_gate(split, args, split_name)
        and float(split.label_psi_vs_train) <= float(args.max_label_psi)
        and float(split.ap_lift) >= float(args.min_ap_lift)
        and float(split.balanced_accuracy) >= float(args.min_balanced_accuracy)
        and float(split.independent_profit_factor) >= min_pf
    )


def walkforward_regime_learnability(
    family: TargetFamilySpec,
    events: Sequence[EventOutcome],
    frame: pd.DataFrame,
    atr: np.ndarray,
    rule_id: str,
    args: argparse.Namespace,
) -> list[RegimeWalkForwardRow]:
    specs = build_fold_specs(
        len(frame),
        int(args.fold_train_bars),
        int(args.fold_validation_bars),
        int(args.fold_test_bars),
        int(args.fold_step_bars),
        int(args.purge_gap),
        int(args.max_folds),
    )
    output: list[RegimeWalkForwardRow] = []
    for spec in specs:
        train_idx = np.arange(spec.train_start, spec.train_end, dtype=np.int64)
        validation_idx = np.arange(spec.validation_start, spec.validation_end, dtype=np.int64)
        test_idx = np.arange(spec.test_start, spec.test_end, dtype=np.int64)
        dataset = build_feature_rows(
            family,
            events,
            frame,
            atr,
            args,
            {"train": train_idx, "validation": validation_idx, "test": test_idx},
            int(spec.fold),
        )
        by_split = split_rows_by_name(dataset)
        context = build_regime_context(by_split["train"])
        filtered = {
            split: filter_rows_by_regime(rows, rule_id, context)
            for split, rows in by_split.items()
        }
        model = fit_centroid_or_empty(filtered["train"])
        train_dist = label_distribution(filtered["train"])
        train_eval = evaluate_regime_split(model, filtered["train"], None, family, rule_id, "train", len(by_split["train"]))
        val_eval = evaluate_regime_split(model, filtered["validation"], train_dist, family, rule_id, "validation", len(by_split["validation"]))
        test_eval = evaluate_regime_split(model, filtered["test"], train_dist, family, rule_id, "test", len(by_split["test"]))
        pass_gate = int(
            split_static_pass(train_eval, args, "train")
            and split_static_pass(val_eval, args, "validation")
            and split_static_pass(test_eval, args, "test")
        )
        output.append(
            RegimeWalkForwardRow(
                family_id=family.family_id,
                family_label=family.label,
                regime_rule_id=rule_id,
                regime_label=REGIME_RULE_LABELS[rule_id],
                fold=int(spec.fold),
                train_events=int(train_eval.events),
                validation_events=int(val_eval.events),
                test_events=int(test_eval.events),
                train_positive_rate=float(train_eval.positive_rate),
                validation_positive_rate=float(val_eval.positive_rate),
                test_positive_rate=float(test_eval.positive_rate),
                validation_ap_lift=float(val_eval.ap_lift),
                test_ap_lift=float(test_eval.ap_lift),
                validation_balanced_accuracy=float(val_eval.balanced_accuracy),
                test_balanced_accuracy=float(test_eval.balanced_accuracy),
                validation_independent_profit_factor=float(val_eval.independent_profit_factor),
                test_independent_profit_factor=float(test_eval.independent_profit_factor),
                validation_label_psi=float(val_eval.label_psi_vs_train),
                test_label_psi=float(test_eval.label_psi_vs_train),
                pass_gate=pass_gate,
            )
        )
    return output


def summarize_regime_candidate(
    family: TargetFamilySpec,
    rule_id: str,
    split_rows: Sequence[RegimeSplitRow],
    walkforward_rows: Sequence[RegimeWalkForwardRow],
    args: argparse.Namespace,
) -> RegimeCandidateRow:
    by_split = {row.split: row for row in split_rows}
    train = by_split["train"]
    val = by_split["validation"]
    test = by_split["test"]
    class_balance = int(
        split_class_gate(train, args, "train")
        and split_class_gate(val, args, "validation")
        and split_class_gate(test, args, "test")
        and float(val.label_psi_vs_train) <= float(args.max_label_psi)
        and float(test.label_psi_vs_train) <= float(args.max_label_psi)
    )
    economic_gate = int(
        float(train.independent_profit_factor) >= float(args.min_train_independent_pf)
        and float(val.independent_profit_factor) >= float(args.min_validation_independent_pf)
        and float(test.independent_profit_factor) >= float(args.min_test_independent_pf)
    )
    static_gate = int(
        class_balance
        and economic_gate
        and float(val.ap_lift) >= float(args.min_ap_lift)
        and float(test.ap_lift) >= float(args.min_ap_lift)
        and float(val.balanced_accuracy) >= float(args.min_balanced_accuracy)
        and float(test.balanced_accuracy) >= float(args.min_balanced_accuracy)
    )
    wf_pass = int(sum(row.pass_gate for row in walkforward_rows))
    wf_ratio = safe_rate(wf_pass, len(walkforward_rows))
    wf_gate = int(len(walkforward_rows) >= int(args.min_walkforward_folds) and wf_ratio >= float(args.min_walkforward_pass_ratio))
    ready = int(static_gate and wf_gate)
    warnings: list[str] = []
    if not class_balance:
        warnings.append("class balance or label stability gate failed")
    if not economic_gate:
        warnings.append("raw filtered economics gate failed")
    if not static_gate:
        warnings.append("static regime learnability gate failed")
    if not wf_gate:
        warnings.append("walk-forward regime learnability gate failed")
    return RegimeCandidateRow(
        family_id=family.family_id,
        family_label=family.label,
        regime_rule_id=rule_id,
        regime_label=REGIME_RULE_LABELS[rule_id],
        train_events=int(train.events),
        validation_events=int(val.events),
        test_events=int(test.events),
        validation_event_coverage=float(val.event_coverage_vs_family_split),
        test_event_coverage=float(test.event_coverage_vs_family_split),
        train_positive_rate=float(train.positive_rate),
        validation_positive_rate=float(val.positive_rate),
        test_positive_rate=float(test.positive_rate),
        validation_label_psi=float(val.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        train_ap_lift=float(train.ap_lift),
        validation_ap_lift=float(val.ap_lift),
        test_ap_lift=float(test.ap_lift),
        validation_balanced_accuracy=float(val.balanced_accuracy),
        test_balanced_accuracy=float(test.balanced_accuracy),
        validation_f1=float(val.f1),
        test_f1=float(test.f1),
        train_independent_profit_factor=float(train.independent_profit_factor),
        validation_independent_profit_factor=float(val.independent_profit_factor),
        test_independent_profit_factor=float(test.independent_profit_factor),
        train_mean_atr_score=float(train.mean_atr_score),
        validation_mean_atr_score=float(val.mean_atr_score),
        test_mean_atr_score=float(test.mean_atr_score),
        walkforward_folds=int(len(walkforward_rows)),
        walkforward_pass_folds=int(wf_pass),
        walkforward_pass_ratio=float(wf_ratio),
        class_balance_gate=int(class_balance),
        economic_gate=int(economic_gate),
        static_learnability_gate=int(static_gate),
        walkforward_learnability_gate=int(wf_gate),
        regime_candidate_ready_gate=int(ready),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )


def rank_candidates(rows: Sequence[RegimeCandidateRow]) -> list[RegimeCandidateRow]:
    return sorted(
        rows,
        key=lambda row: (
            int(row.regime_candidate_ready_gate),
            float(row.walkforward_pass_ratio),
            float(row.validation_ap_lift),
            float(row.test_ap_lift),
            float(row.test_balanced_accuracy),
            float(row.test_independent_profit_factor),
            int(row.test_events),
        ),
        reverse=True,
    )


def build_decision_matrix(candidate_rows: Sequence[RegimeCandidateRow]) -> list[DecisionMatrixRow]:
    ranked = rank_candidates(candidate_rows)
    ready_count = int(sum(row.regime_candidate_ready_gate for row in ranked))
    best = ranked[0] if ranked else None
    route_rows = [
        DecisionMatrixRow(
            route_id="STOP_PHASE173_DIRECT_TRAINING",
            route_name="Stop direct CA1/CA3/CA2 training from Phase173A",
            status="MANDATORY",
            score=100.0,
            rank=1,
            evidence="Phase173A target_learnability_ready_gate=0; Phase174A remains diagnostic-only.",
            recommendation="Do not train any Phase173 target family directly.",
        ),
        DecisionMatrixRow(
            route_id="HYBRID_REGIME_FIRST_REDESIGN",
            route_name="Hybrid/regime-first target redesign",
            status="READY_FOR_NEXT_DIAGNOSTIC" if ready_count > 0 else "NOT_CONFIRMED",
            score=float(80.0 + min(20, ready_count * 5)) if ready_count > 0 else float(35.0 if best else 0.0),
            rank=2,
            evidence=(
                f"ready_regime_candidates={ready_count}; best="
                f"{best.family_id + '|' + best.regime_rule_id if best else 'none'}"
            ),
            recommendation=(
                "Owner may authorize Phase175A model-design audit around the selected regime target."
                if ready_count > 0
                else "Do not train yet; either redesign labels/features again or pause for manual review."
            ),
        ),
        DecisionMatrixRow(
            route_id="DEEP_MODEL_TRAINING_NOW",
            route_name="Train a deep model immediately",
            status="BLOCKED",
            score=0.0,
            rank=3,
            evidence="This phase is a pre-training diagnostic and does not create model artifacts.",
            recommendation="Blocked until a diagnostic route passes gates and owner explicitly authorizes the next phase.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=4,
            evidence="No production/paper/live gate is part of Phase174A.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]
    return route_rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase174Report) -> str:
    candidate_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{html.escape(str(row['regime_rule_id']))}</td>"
        f"<td>{int(row['train_events'])}/{int(row['validation_events'])}/{int(row['test_events'])}</td>"
        f"<td>{float(row['validation_ap_lift']):.4f}</td>"
        f"<td>{float(row['test_ap_lift']):.4f}</td>"
        f"<td>{float(row['test_balanced_accuracy']):.3f}</td>"
        f"<td>{float(row['test_independent_profit_factor']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['regime_candidate_ready_gate'])}</td></tr>"
        for row in report.candidate_rows[:60]
    )
    decision_rows = "".join(
        f"<tr><td>{html.escape(str(row['route_id']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['score']):.1f}</td>"
        f"<td>{html.escape(str(row['recommendation']))}</td></tr>"
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
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
.bad {{ color:#fca5a5; }} .good {{ color:#86efac; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase174A hybrid/regime-first target redesign audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'hybrid_regime_first_ready_gate': report.hybrid_regime_first_ready_gate,
        'ready_regime_candidates': report.ready_regime_candidates,
        'selected_family_id': report.selected_family_id,
        'selected_regime_rule_id': report.selected_regime_rule_id,
        'selected_regime_ready_gate': report.selected_regime_ready_gate,
        'recommendation': report.recommendation,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
<section class="card"><h2>Top regime candidates</h2><table><thead><tr><th>Family</th><th>Rule</th><th>Events train/val/test</th><th>Val AP lift</th><th>Test AP lift</th><th>Test bAcc</th><th>Test PF</th><th>WF pass</th><th>Ready</th></tr></thead><tbody>{candidate_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def append_dataset_sample(
    output: list[dict[str, Any]],
    rows: Sequence[EventFeatureRow],
    family: TargetFamilySpec,
    rule_id: str,
    max_rows: int,
) -> None:
    if max_rows <= 0 or len(output) >= max_rows:
        return
    remaining = max_rows - len(output)
    for row in rows[:remaining]:
        item = asdict(row)
        item["regime_rule_id"] = rule_id
        item["regime_label"] = REGIME_RULE_LABELS[rule_id]
        item["family_label"] = family.label
        output.append(item)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE174A HYBRID/REGIME-FIRST TARGET REDESIGN AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        families = parse_families(args.families)
        regime_rules = parse_regime_rules(args.regime_rules)

        candidate_rows: list[RegimeCandidateRow] = []
        split_rows: list[RegimeSplitRow] = []
        walkforward_rows: list[RegimeWalkForwardRow] = []
        dataset_rows: list[dict[str, Any]] = []

        for family in families:
            family_dataset, events = build_family_dataset(family, frame, atr, args)
            by_split = split_rows_by_name(family_dataset)
            print(f"[i] family={family.family_id} events={len(family_dataset)}")
            for rule_id in regime_rules:
                static_rows = static_regime_learnability(family, family_dataset, rule_id)
                wf_rows = walkforward_regime_learnability(family, events, frame, atr, rule_id, args)
                summary = summarize_regime_candidate(family, rule_id, static_rows, wf_rows, args)
                candidate_rows.append(summary)
                split_rows.extend(static_rows)
                walkforward_rows.extend(wf_rows)
                context = build_regime_context(by_split["train"])
                filtered_for_sample = [
                    row
                    for split in ("train", "validation", "test")
                    for row in filter_rows_by_regime(by_split[split], rule_id, context)
                ]
                append_dataset_sample(dataset_rows, filtered_for_sample, family, rule_id, int(args.max_dataset_rows))

        ranked_candidates = rank_candidates(candidate_rows)
        ready_count = int(sum(row.regime_candidate_ready_gate for row in ranked_candidates))
        selected = ranked_candidates[0] if ranked_candidates else None
        decision_rows = build_decision_matrix(ranked_candidates)
        recommendation = (
            "REGIME_TARGET_CANDIDATE_READY_FOR_OWNER_AUTHORIZED_PHASE175A_MODEL_DESIGN_AUDIT"
            if ready_count > 0
            else "STOP_OR_REDESIGN_REQUIRED_NO_MODEL_TRAINING"
        )

        output_candidates = output_dir / "latest_regime_candidates.csv"
        output_splits = output_dir / "latest_splits.csv"
        output_wf = output_dir / "latest_walkforward.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        output_dataset = output_dir / "latest_dataset.csv"
        write_csv(output_candidates, [asdict(row) for row in ranked_candidates])
        write_csv(output_splits, [asdict(row) for row in split_rows])
        write_csv(output_wf, [asdict(row) for row in walkforward_rows])
        write_csv(output_decision, [asdict(row) for row in decision_rows])
        write_csv(output_dataset, dataset_rows)

        report = Phase174Report(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            spread_mode=str(args.spread_mode),
            spread_value=float(args.spread_value),
            candidate_families=int(len(families)),
            regime_rules=int(len(regime_rules)),
            evaluated_regime_candidates=int(len(ranked_candidates)),
            ready_regime_candidates=int(ready_count),
            selected_family_id=str(selected.family_id) if selected else "",
            selected_regime_rule_id=str(selected.regime_rule_id) if selected else "",
            selected_regime_label=str(selected.regime_label) if selected else "",
            selected_regime_ready_gate=int(selected.regime_candidate_ready_gate) if selected else 0,
            selected_validation_ap_lift=float(selected.validation_ap_lift) if selected else 0.0,
            selected_test_ap_lift=float(selected.test_ap_lift) if selected else 0.0,
            selected_validation_independent_profit_factor=float(selected.validation_independent_profit_factor) if selected else 0.0,
            selected_test_independent_profit_factor=float(selected.test_independent_profit_factor) if selected else 0.0,
            selected_walkforward_pass_ratio=float(selected.walkforward_pass_ratio) if selected else 0.0,
            hybrid_regime_first_ready_gate=int(ready_count > 0),
            recommendation=recommendation,
            candidate_rows=[asdict(row) for row in ranked_candidates],
            split_rows=[asdict(row) for row in split_rows],
            walkforward_rows=[asdict(row) for row in walkforward_rows],
            decision_matrix_rows=[asdict(row) for row in decision_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(output_candidates),
            output_splits_csv=str(output_splits),
            output_walkforward_csv=str(output_wf),
            output_decision_matrix_csv=str(output_decision),
            output_dataset_csv=str(output_dataset),
            production_status="BLOCKED — Phase174A hybrid/regime-first target redesign audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase174A hybrid/regime-first target redesign audit complete")
        print(f"  families           : {report.candidate_families}")
        print(f"  regime rules       : {report.regime_rules}")
        print(f"  evaluated          : {report.evaluated_regime_candidates}")
        print(f"  ready              : {report.ready_regime_candidates}")
        print(f"  selected           : {report.selected_family_id}|{report.selected_regime_rule_id}")
        print(f"  ready gate         : {report.hybrid_regime_first_ready_gate}")
        print(f"  recommendation     : {report.recommendation}")
        print(f"  output             : {report.output_json}")
        print(f"  elapsed            : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
