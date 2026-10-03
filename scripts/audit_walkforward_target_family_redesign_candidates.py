"""Phase177A: walk-forward target-family redesign candidate audit.

Phase176A rejected the current broker-cost-aware 1H target definitions. This
phase audits a new predeclared set of target-family candidates that change
payoff horizon, TP/SL geometry, zone strictness, and side mapping. It is a
pre-training diagnostic: no deep model is trained and no production/paper/live
approval is created.
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
from types import SimpleNamespace
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
    evaluate_family_events,
    label_psi,
    parse_families,
    profit_factor,
)
from audit_broker_cost_aware_1h_target_learnability import (  # noqa: E402
    CentroidBinaryModel,
    EventFeatureRow,
    build_feature_rows,
    matrix_from_rows,
    split_rows_by_name,
)
from audit_pivot_1h_entry_feasibility import build_zone_masks, read_ohlc_frame, resolve_flat_path_arg  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/walkforward_target_family_redesign_candidates")
DEFAULT_REDESIGN_FAMILIES = (
    "R1_FAST_MID_B15_10_H12:fast_breakout_mid_12:breakout:1:24:0.10:0.85:0.15:1:1.0:0:1.5:1.0:12;"
    "R2_FAST_MID_B12_08_H12:fast_breakout_mid_compact:breakout:1:24:0.10:0.85:0.15:1:1.0:0:1.2:0.8:12;"
    "R3_STRICT_B15_10_H12:fast_breakout_strict_12:breakout:1:24:0.05:0.90:0.10:1:1.0:0:1.5:1.0:12;"
    "R4_STRICT_B10_075_H12:strict_asym_12:breakout:1:24:0.05:0.90:0.10:1:1.0:0:1.0:0.75:12;"
    "R5_WIDE_B20_10_H24:wide_breakout_shorter_hold:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;"
    "R6_WIDE_B15_10_H24:wide_breakout_compact:breakout:1:48:0.10:0.85:0.15:1:1.0:0:1.5:1.0:24;"
    "R7_REV_MID_B10_075_H12:reversal_mid_fast:reversal:1:24:0.10:0.85:0.15:1:1.0:0:1.0:0.75:12;"
    "R8_REV_STRICT_B10_075_H12:reversal_strict_fast:reversal:1:24:0.05:0.90:0.10:1:1.0:0:1.0:0.75:12"
)


@dataclass(frozen=True)
class CandidateSplitRow:
    family_id: str
    label: str
    split: str
    events: int
    positives: int
    negatives: int
    timeouts: int
    positive_rate: float
    label_psi_vs_train: float
    independent_profit_factor: float
    mean_atr_score: float
    sum_atr_score: float
    base_ap: float
    model_ap: float
    ap_lift: float
    balanced_accuracy: float
    f1: float
    threshold: float
    buy_events: int
    sell_events: int
    pass_gate: int


@dataclass(frozen=True)
class CandidateFoldRow:
    family_id: str
    label: str
    fold: int
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
    pass_gate: int
    failure_reasons: str


@dataclass(frozen=True)
class TargetRedesignCandidateRow:
    family_id: str
    label: str
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
    target_family_redesign_ready_gate: int
    failure_reasons: str
    diagnostic_score: float


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
class Phase177Report:
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
    ready_candidates: int
    selected_family_id: str
    selected_family_ready_gate: int
    selected_walkforward_pass_ratio: float
    selected_validation_ap_lift: float
    selected_test_ap_lift: float
    selected_train_independent_profit_factor: float
    selected_validation_independent_profit_factor: float
    selected_test_independent_profit_factor: float
    target_family_redesign_ready_gate: int
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
    output_events_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit walk-forward target-family redesign candidates before model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--families", default=DEFAULT_REDESIGN_FAMILIES)
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
    parser.add_argument("--min-train-events", type=int, default=100)
    parser.add_argument("--min-validation-events", type=int, default=25)
    parser.add_argument("--min-test-events", type=int, default=25)
    parser.add_argument("--min-positive-rate", type=float, default=0.12)
    parser.add_argument("--max-positive-rate", type=float, default=0.68)
    parser.add_argument("--max-label-psi", type=float, default=0.20)
    parser.add_argument("--min-ap-lift", type=float, default=0.03)
    parser.add_argument("--min-balanced-accuracy", type=float, default=0.53)
    parser.add_argument("--min-train-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-validation-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-test-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-train-mean-atr-score", type=float, default=0.0)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=5)
    parser.add_argument("--max-events-sample", type=int, default=20000)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase177A walk-forward target-family redesign candidate audit")
    return parser.parse_args(argv)


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if abs(float(den)) > 1e-12 else 0.0


def label_distribution(rows: Sequence[EventFeatureRow]) -> dict[str, float]:
    total = len(rows)
    if total == 0:
        return {LABEL_POSITIVE: 0.0, LABEL_NEGATIVE: 0.0, LABEL_TIMEOUT: 0.0}
    return {
        LABEL_POSITIVE: sum(1 for row in rows if row.label == LABEL_POSITIVE) / total,
        LABEL_NEGATIVE: sum(1 for row in rows if row.label == LABEL_NEGATIVE) / total,
        LABEL_TIMEOUT: sum(1 for row in rows if row.label == LABEL_TIMEOUT) / total,
    }


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int64)
    s = np.asarray(scores, dtype=np.float64)
    positives = int(np.sum(y == 1))
    if len(y) == 0 or positives == 0:
        return 0.0
    order = np.argsort(-s)
    sorted_y = y[order]
    tp = np.cumsum(sorted_y == 1)
    ranks = np.arange(1, len(sorted_y) + 1)
    precision = tp / ranks
    return float(np.sum(precision[sorted_y == 1]) / positives)


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(y_pred, dtype=np.int64)
    if len(y) == 0:
        return 0.0
    pos = y == 1
    neg = y == 0
    tpr = float(np.mean(p[pos] == 1)) if np.any(pos) else 0.5
    tnr = float(np.mean(p[neg] == 0)) if np.any(neg) else 0.5
    return float((tpr + tnr) / 2.0)


def f1_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(y_pred, dtype=np.int64)
    tp = float(np.sum((y == 1) & (p == 1)))
    fp = float(np.sum((y == 0) & (p == 1)))
    fn = float(np.sum((y == 1) & (p == 0)))
    return float((2.0 * tp) / max(2.0 * tp + fp + fn, 1e-12))


def economic_summary(rows: Sequence[EventFeatureRow]) -> dict[str, float]:
    scores = [float(row.atr_score) for row in rows]
    return {
        "independent_profit_factor": profit_factor(scores),
        "mean_atr_score": float(np.mean(scores)) if scores else 0.0,
        "sum_atr_score": float(np.sum(scores)) if scores else 0.0,
    }


def split_density_gate(split: CandidateSplitRow, split_name: str, args: argparse.Namespace) -> int:
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


def split_pass_gate(split: CandidateSplitRow, split_name: str, args: argparse.Namespace) -> int:
    min_pf = {
        "train": float(args.min_train_independent_pf),
        "validation": float(args.min_validation_independent_pf),
        "test": float(args.min_test_independent_pf),
    }.get(split_name, float(args.min_test_independent_pf))
    if split_name == "train":
        return int(
            split_density_gate(split, split_name, args)
            and float(split.independent_profit_factor) >= min_pf
            and float(split.mean_atr_score) >= float(args.min_train_mean_atr_score)
        )
    return int(
        split_density_gate(split, split_name, args)
        and float(split.label_psi_vs_train) <= float(args.max_label_psi)
        and float(split.independent_profit_factor) >= min_pf
        and float(split.ap_lift) >= float(args.min_ap_lift)
        and float(split.balanced_accuracy) >= float(args.min_balanced_accuracy)
    )


def evaluate_candidate_split(
    model: CentroidBinaryModel,
    rows: Sequence[EventFeatureRow],
    train_dist: Mapping[str, float] | None,
    family: TargetFamilySpec,
    split_name: str,
    args: argparse.Namespace,
) -> CandidateSplitRow:
    x, y, sides, labels = matrix_from_rows(rows)
    scores = model.score(x) if len(rows) else np.asarray([], dtype=np.float64)
    pred = (scores >= model.threshold_).astype(np.int64) if len(scores) else np.asarray([], dtype=np.int64)
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    timeouts = sum(1 for label in labels if label == LABEL_TIMEOUT)
    positive_rate = safe_ratio(positives, len(rows))
    base_ap = positive_rate
    model_ap = average_precision(y, scores)
    dist = label_distribution(rows)
    econ = economic_summary(rows)
    row = CandidateSplitRow(
        family_id=family.family_id,
        label=family.label,
        split=split_name,
        events=int(len(rows)),
        positives=positives,
        negatives=negatives,
        timeouts=int(timeouts),
        positive_rate=positive_rate,
        label_psi_vs_train=0.0 if train_dist is None else label_psi(dist, train_dist),
        independent_profit_factor=float(econ["independent_profit_factor"]),
        mean_atr_score=float(econ["mean_atr_score"]),
        sum_atr_score=float(econ["sum_atr_score"]),
        base_ap=base_ap,
        model_ap=model_ap,
        ap_lift=float(model_ap - base_ap),
        balanced_accuracy=balanced_accuracy(y, pred),
        f1=f1_score(y, pred),
        threshold=float(model.threshold_),
        buy_events=sum(1 for side in sides if side == "BUY"),
        sell_events=sum(1 for side in sides if side == "SELL"),
        pass_gate=0,
    )
    return CandidateSplitRow(**{**asdict(row), "pass_gate": split_pass_gate(row, split_name, args)})


def build_events_and_rows(
    family: TargetFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    args: argparse.Namespace,
    split_map: Mapping[str, np.ndarray],
    fold: int = 0,
) -> tuple[list[EventOutcome], list[EventFeatureRow]]:
    top_mask, bottom_mask, _both = build_zone_masks(
        frame,
        atr,
        family.recent_window_bars,
        family.pivot_zone_atr,
        family.top_position_threshold,
        family.bottom_position_threshold,
        family.exclude_both_zones,
        family.min_range_width_atr,
        family.max_range_width_atr,
    )
    event_args = SimpleNamespace(
        spread_mode=str(args.spread_mode),
        spread_value=float(args.spread_value),
        same_bar_policy=str(args.same_bar_policy),
    )
    events = evaluate_family_events(family, frame, atr, top_mask, bottom_mask, event_args, float(args.spread_value))
    rows = build_feature_rows(family, events, frame, atr, event_args, split_map, fold)
    return events, rows


def static_candidate_splits(family: TargetFamilySpec, rows: Sequence[EventFeatureRow], args: argparse.Namespace) -> list[CandidateSplitRow]:
    by_split = split_rows_by_name(rows)
    x_train, y_train, _sides, _labels = matrix_from_rows(by_split["train"])
    model = CentroidBinaryModel().fit(x_train, y_train)
    train_dist = label_distribution(by_split["train"])
    return [
        evaluate_candidate_split(model, by_split["train"], None, family, "train", args),
        evaluate_candidate_split(model, by_split["validation"], train_dist, family, "validation", args),
        evaluate_candidate_split(model, by_split["test"], train_dist, family, "test", args),
    ]


def fold_failure_reasons(train: CandidateSplitRow, validation: CandidateSplitRow, test: CandidateSplitRow) -> list[str]:
    reasons: list[str] = []
    if not int(train.pass_gate):
        reasons.append("train_gate_failed")
    if not int(validation.pass_gate):
        reasons.append("validation_gate_failed")
    if not int(test.pass_gate):
        reasons.append("test_gate_failed")
    return reasons or ["none"]


def walkforward_candidate_rows(
    family: TargetFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    args: argparse.Namespace,
    events: Sequence[EventOutcome],
) -> list[CandidateFoldRow]:
    specs = build_fold_specs(
        len(frame),
        int(args.fold_train_bars),
        int(args.fold_validation_bars),
        int(args.fold_test_bars),
        int(args.fold_step_bars),
        int(args.purge_gap),
        int(args.max_folds),
    )
    output: list[CandidateFoldRow] = []
    for spec in specs:
        train_idx = np.arange(spec.train_start, spec.train_end, dtype=np.int64)
        validation_idx = np.arange(spec.validation_start, spec.validation_end, dtype=np.int64)
        test_idx = np.arange(spec.test_start, spec.test_end, dtype=np.int64)
        rows = build_feature_rows(
            family,
            events,
            frame,
            atr,
            SimpleNamespace(spread_mode=args.spread_mode, spread_value=args.spread_value, same_bar_policy=args.same_bar_policy),
            {"train": train_idx, "validation": validation_idx, "test": test_idx},
            int(spec.fold),
        )
        by_split = split_rows_by_name(rows)
        x_train, y_train, _sides, _labels = matrix_from_rows(by_split["train"])
        model = CentroidBinaryModel().fit(x_train, y_train)
        train_dist = label_distribution(by_split["train"])
        train_eval = evaluate_candidate_split(model, by_split["train"], None, family, "train", args)
        val_eval = evaluate_candidate_split(model, by_split["validation"], train_dist, family, "validation", args)
        test_eval = evaluate_candidate_split(model, by_split["test"], train_dist, family, "test", args)
        reasons = fold_failure_reasons(train_eval, val_eval, test_eval)
        output.append(
            CandidateFoldRow(
                family_id=family.family_id,
                label=family.label,
                fold=int(spec.fold),
                train_events=int(train_eval.events),
                validation_events=int(val_eval.events),
                test_events=int(test_eval.events),
                train_positive_rate=float(train_eval.positive_rate),
                validation_positive_rate=float(val_eval.positive_rate),
                test_positive_rate=float(test_eval.positive_rate),
                validation_label_psi=float(val_eval.label_psi_vs_train),
                test_label_psi=float(test_eval.label_psi_vs_train),
                train_independent_profit_factor=float(train_eval.independent_profit_factor),
                validation_independent_profit_factor=float(val_eval.independent_profit_factor),
                test_independent_profit_factor=float(test_eval.independent_profit_factor),
                train_mean_atr_score=float(train_eval.mean_atr_score),
                validation_mean_atr_score=float(val_eval.mean_atr_score),
                test_mean_atr_score=float(test_eval.mean_atr_score),
                validation_ap_lift=float(val_eval.ap_lift),
                test_ap_lift=float(test_eval.ap_lift),
                validation_balanced_accuracy=float(val_eval.balanced_accuracy),
                test_balanced_accuracy=float(test_eval.balanced_accuracy),
                pass_gate=int(train_eval.pass_gate and val_eval.pass_gate and test_eval.pass_gate),
                failure_reasons=json.dumps(reasons, ensure_ascii=False),
            )
        )
    return output


def candidate_summary(
    family: TargetFamilySpec,
    split_rows: Sequence[CandidateSplitRow],
    fold_rows: Sequence[CandidateFoldRow],
    args: argparse.Namespace,
) -> TargetRedesignCandidateRow:
    by_split = {row.split: row for row in split_rows}
    train = by_split["train"]
    validation = by_split["validation"]
    test = by_split["test"]
    density_gate = int(split_density_gate(train, "train", args) and split_density_gate(validation, "validation", args) and split_density_gate(test, "test", args))
    economic_gate = int(
        density_gate
        and train.independent_profit_factor >= float(args.min_train_independent_pf)
        and validation.independent_profit_factor >= float(args.min_validation_independent_pf)
        and test.independent_profit_factor >= float(args.min_test_independent_pf)
        and train.mean_atr_score >= float(args.min_train_mean_atr_score)
    )
    static_gate = int(train.pass_gate and validation.pass_gate and test.pass_gate)
    wf_pass = sum(row.pass_gate for row in fold_rows)
    wf_ratio = safe_ratio(wf_pass, len(fold_rows))
    wf_gate = int(len(fold_rows) >= int(args.min_walkforward_folds) and wf_ratio >= float(args.min_walkforward_pass_ratio))
    ready = int(static_gate and wf_gate)
    reasons: list[str] = []
    if not density_gate:
        reasons.append("density_gate_failed")
    if not economic_gate:
        reasons.append("economic_gate_failed")
    if not static_gate:
        reasons.append("static_learnability_gate_failed")
    if not wf_gate:
        reasons.append("walkforward_gate_failed")
    if train.mean_atr_score < float(args.min_train_mean_atr_score):
        reasons.append("train_expectancy_failed")
    score = float(
        25.0 * ready
        + 20.0 * wf_ratio
        + 8.0 * economic_gate
        + 8.0 * static_gate
        + 4.0 * max(validation.ap_lift, 0.0)
        + 4.0 * max(test.ap_lift, 0.0)
        + 2.0 * max(validation.balanced_accuracy - 0.5, 0.0)
        + 2.0 * max(test.balanced_accuracy - 0.5, 0.0)
        + min(train.independent_profit_factor, 3.0)
        + min(validation.independent_profit_factor, 3.0)
        + min(test.independent_profit_factor, 3.0)
        - len(reasons)
    )
    return TargetRedesignCandidateRow(
        family_id=family.family_id,
        label=family.label,
        side_mapping=family.side_mapping,
        entry_delay_bars=int(family.entry_delay_bars),
        recent_window_bars=int(family.recent_window_bars),
        pivot_zone_atr=float(family.pivot_zone_atr),
        top_position_threshold=float(family.top_position_threshold),
        bottom_position_threshold=float(family.bottom_position_threshold),
        tp_atr=float(family.tp_atr),
        sl_atr=float(family.sl_atr),
        reward_risk=float(family.tp_atr / max(family.sl_atr, 1e-9)),
        hold_bars=int(family.hold_bars),
        train_events=int(train.events),
        validation_events=int(validation.events),
        test_events=int(test.events),
        train_positive_rate=float(train.positive_rate),
        validation_positive_rate=float(validation.positive_rate),
        test_positive_rate=float(test.positive_rate),
        validation_label_psi=float(validation.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        train_independent_profit_factor=float(train.independent_profit_factor),
        validation_independent_profit_factor=float(validation.independent_profit_factor),
        test_independent_profit_factor=float(test.independent_profit_factor),
        train_mean_atr_score=float(train.mean_atr_score),
        validation_mean_atr_score=float(validation.mean_atr_score),
        test_mean_atr_score=float(test.mean_atr_score),
        validation_ap_lift=float(validation.ap_lift),
        test_ap_lift=float(test.ap_lift),
        validation_balanced_accuracy=float(validation.balanced_accuracy),
        test_balanced_accuracy=float(test.balanced_accuracy),
        walkforward_folds=int(len(fold_rows)),
        walkforward_pass_folds=int(wf_pass),
        walkforward_pass_ratio=float(wf_ratio),
        density_gate=int(density_gate),
        economic_gate=int(economic_gate),
        static_learnability_gate=int(static_gate),
        walkforward_gate=int(wf_gate),
        target_family_redesign_ready_gate=int(ready),
        failure_reasons=json.dumps(reasons, ensure_ascii=False),
        diagnostic_score=float(score),
    )


def rank_candidates(rows: Sequence[TargetRedesignCandidateRow]) -> list[TargetRedesignCandidateRow]:
    return sorted(
        rows,
        key=lambda row: (
            row.target_family_redesign_ready_gate,
            row.walkforward_pass_ratio,
            row.diagnostic_score,
            row.validation_ap_lift,
            row.test_ap_lift,
            row.test_balanced_accuracy,
        ),
        reverse=True,
    )


def build_decision_matrix(ready_count: int, selected: TargetRedesignCandidateRow | None) -> list[DecisionMatrixRow]:
    best = f"{selected.family_id}" if selected else "none"
    return [
        DecisionMatrixRow(
            route_id="FREEZE_OLD_TARGETS",
            route_name="Keep Phase173A/174A/176A targets frozen",
            status="MANDATORY",
            score=100.0,
            rank=1,
            evidence="Prior route has target_definition_redesign_required_gate=1.",
            recommendation="Do not train old CA1/CA3/CA2 targets.",
        ),
        DecisionMatrixRow(
            route_id="NEW_TARGET_FAMILY_CANDIDATES",
            route_name="Walk-forward target-family redesign candidates",
            status="READY_FOR_MODEL_DESIGN_AUDIT" if ready_count > 0 else "NOT_CONFIRMED",
            score=85.0 if ready_count > 0 else 35.0,
            rank=2,
            evidence=f"ready_candidates={ready_count}; selected={best}",
            recommendation=(
                "Owner may authorize a model-design preflight only after reviewing this diagnostic."
                if ready_count > 0
                else "No training; redesign candidates did not pass walk-forward gates."
            ),
        ),
        DecisionMatrixRow(
            route_id="TRAIN_MODEL_NOW",
            route_name="Train a model now",
            status="BLOCKED",
            score=0.0,
            rank=3,
            evidence="Phase177A is a target audit and creates no model artifacts.",
            recommendation="Blocked unless a future owner-approved phase follows a passed diagnostic target.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=4,
            evidence="No production gate exists in Phase177A.",
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


def render_html(title: str, report: Phase177Report) -> str:
    candidate_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td><td>{html.escape(str(row['side_mapping']))}</td>"
        f"<td>{float(row['tp_atr']):.2f}/{float(row['sl_atr']):.2f}/{int(row['hold_bars'])}</td>"
        f"<td>{int(row['walkforward_pass_folds'])}/{int(row['walkforward_folds'])}</td>"
        f"<td>{float(row['train_independent_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_ap_lift']):.4f}</td><td>{float(row['test_ap_lift']):.4f}</td>"
        f"<td>{int(row['target_family_redesign_ready_gate'])}</td></tr>"
        for row in report.candidate_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase177A walk-forward target-family redesign candidate audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'target_family_redesign_ready_gate': report.target_family_redesign_ready_gate,
        'ready_candidates': report.ready_candidates,
        'selected_family_id': report.selected_family_id,
        'recommendation': report.recommendation,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decision_rows}</tbody></table></section>
<section class="card"><h2>Candidates</h2><table><thead><tr><th>Family</th><th>Side</th><th>TP/SL/Hold</th><th>WF pass</th><th>Train PF</th><th>Val AP</th><th>Test AP</th><th>Ready</th></tr></thead><tbody>{candidate_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE177A WALK-FORWARD TARGET-FAMILY REDESIGN CANDIDATE AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), float(args.train_frac), float(args.val_frac), int(args.purge_gap))
        families = parse_families(args.families)
        candidate_rows: list[TargetRedesignCandidateRow] = []
        split_rows: list[CandidateSplitRow] = []
        fold_rows: list[CandidateFoldRow] = []
        event_samples: list[dict[str, Any]] = []
        for family in families:
            print(f"[i] candidate={family.family_id}")
            events, rows = build_events_and_rows(
                family,
                frame,
                atr,
                args,
                {"train": train_idx, "validation": validation_idx, "test": test_idx},
            )
            static_rows = static_candidate_splits(family, rows, args)
            family_folds = walkforward_candidate_rows(family, frame, atr, args, events)
            summary = candidate_summary(family, static_rows, family_folds, args)
            candidate_rows.append(summary)
            split_rows.extend(static_rows)
            fold_rows.extend(family_folds)
            for event in events[: max(int(args.max_events_sample), 0)]:
                if len(event_samples) >= int(args.max_events_sample):
                    break
                event_samples.append(asdict(event))
        ranked = rank_candidates(candidate_rows)
        ready_count = sum(row.target_family_redesign_ready_gate for row in ranked)
        selected = ranked[0] if ranked else None
        decision_rows = build_decision_matrix(ready_count, selected)
        recommendation = (
            "TARGET_FAMILY_READY_FOR_OWNER_REVIEW_NO_TRAINING_YET"
            if ready_count > 0
            else "NO_TARGET_FAMILY_READY_REDESIGN_OR_PAUSE_REQUIRED"
        )
        output_candidates = output_dir / "latest_candidates.csv"
        output_splits = output_dir / "latest_splits.csv"
        output_wf = output_dir / "latest_walkforward.csv"
        output_events = output_dir / "latest_events_sample.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        write_csv(output_candidates, [asdict(row) for row in ranked])
        write_csv(output_splits, [asdict(row) for row in split_rows])
        write_csv(output_wf, [asdict(row) for row in fold_rows])
        write_csv(output_events, event_samples)
        write_csv(output_decision, [asdict(row) for row in decision_rows])
        report = Phase177Report(
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
            ready_candidates=int(ready_count),
            selected_family_id=str(selected.family_id) if selected else "",
            selected_family_ready_gate=int(selected.target_family_redesign_ready_gate) if selected else 0,
            selected_walkforward_pass_ratio=float(selected.walkforward_pass_ratio) if selected else 0.0,
            selected_validation_ap_lift=float(selected.validation_ap_lift) if selected else 0.0,
            selected_test_ap_lift=float(selected.test_ap_lift) if selected else 0.0,
            selected_train_independent_profit_factor=float(selected.train_independent_profit_factor) if selected else 0.0,
            selected_validation_independent_profit_factor=float(selected.validation_independent_profit_factor) if selected else 0.0,
            selected_test_independent_profit_factor=float(selected.test_independent_profit_factor) if selected else 0.0,
            target_family_redesign_ready_gate=int(ready_count > 0),
            recommendation=recommendation,
            candidate_rows=[asdict(row) for row in ranked],
            split_rows=[asdict(row) for row in split_rows],
            walkforward_rows=[asdict(row) for row in fold_rows],
            decision_matrix_rows=[asdict(row) for row in decision_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(output_candidates),
            output_splits_csv=str(output_splits),
            output_walkforward_csv=str(output_wf),
            output_events_csv=str(output_events),
            output_decision_matrix_csv=str(output_decision),
            production_status="BLOCKED — Phase177A target-family redesign audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase177A target-family redesign candidate audit complete")
        print(f"  candidates    : {report.candidate_families}")
        print(f"  ready         : {report.ready_candidates}")
        print(f"  selected      : {report.selected_family_id}")
        print(f"  ready gate    : {report.target_family_redesign_ready_gate}")
        print(f"  output        : {report.output_json}")
        print(f"  elapsed       : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
