"""Phase173A: broker-cost-aware 1H target learnability / dataset audit.

Phase172A found broker-cost-aware 1H target families with stable label structure.
This phase checks whether those labels are learnable with simple, dependency-free
baselines before any deep model or production-style training is considered.

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
    DEFAULT_FAMILIES,
    DEFAULT_STORAGE,
    LABEL_NEGATIVE,
    LABEL_POSITIVE,
    LABEL_TIMEOUT,
    EventOutcome,
    TargetFamilySpec,
    action_distribution,
    evaluate_family_events,
    label_psi,
    parse_families,
)
from audit_pivot_1h_entry_feasibility import build_zone_masks, read_ohlc_frame, resolve_flat_path_arg  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/broker_cost_aware_1h_target_learnability")
DEFAULT_SELECTED_FAMILIES = (
    "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;"
    "CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;"
    "CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48"
)
FEATURE_COLUMNS = (
    "side_buy",
    "side_sell",
    "zone_top",
    "zone_bottom",
    "atr",
    "range_atr",
    "body_atr",
    "upper_wick_atr",
    "lower_wick_atr",
    "recent_position",
    "recent_width_atr",
    "dist_top_atr",
    "dist_bottom_atr",
    "ret_1_atr",
    "ret_3_atr",
    "ret_6_atr",
    "ret_12_atr",
    "ret_24_atr",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "spread_to_atr",
)


@dataclass(frozen=True)
class EventFeatureRow:
    family_id: str
    row_id: int
    timestamp: str
    split: str
    fold: int
    side: str
    zone: str
    label: str
    target_positive: int
    atr_score: float
    points_pnl: float
    outcome: str
    side_buy: float
    side_sell: float
    zone_top: float
    zone_bottom: float
    atr: float
    range_atr: float
    body_atr: float
    upper_wick_atr: float
    lower_wick_atr: float
    recent_position: float
    recent_width_atr: float
    dist_top_atr: float
    dist_bottom_atr: float
    ret_1_atr: float
    ret_3_atr: float
    ret_6_atr: float
    ret_12_atr: float
    ret_24_atr: float
    hour_sin: float
    hour_cos: float
    dow_sin: float
    dow_cos: float
    spread_to_atr: float


@dataclass(frozen=True)
class LearnabilitySplitRow:
    family_id: str
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
    buy_ap: float
    sell_events: int
    sell_ap: float
    label_psi_vs_train: float


@dataclass(frozen=True)
class LearnabilityFoldRow:
    family_id: str
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
    validation_label_psi: float
    test_label_psi: float
    pass_gate: int


@dataclass(frozen=True)
class LearnabilityFamilyRow:
    family_id: str
    label: str
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
    validation_f1: float
    test_f1: float
    validation_buy_ap: float
    validation_sell_ap: float
    test_buy_ap: float
    test_sell_ap: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    class_balance_gate: int
    static_learnability_gate: int
    walkforward_learnability_gate: int
    target_learnability_ready_gate: int
    warnings: str


@dataclass(frozen=True)
class Phase173Report:
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
    learnable_families: int
    selected_family_id: str
    selected_family_ready_gate: int
    target_learnability_ready_gate: int
    feature_columns: list[str]
    family_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_families_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_dataset_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit learnability of broker-cost-aware 1H target families before model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--families", default=DEFAULT_SELECTED_FAMILIES)
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
    parser.add_argument("--min-validation-events", type=int, default=20)
    parser.add_argument("--min-test-events", type=int, default=20)
    parser.add_argument("--min-positive-rate", type=float, default=0.10)
    parser.add_argument("--max-positive-rate", type=float, default=0.70)
    parser.add_argument("--max-label-psi", type=float, default=0.20)
    parser.add_argument("--min-ap-lift", type=float, default=0.03)
    parser.add_argument("--min-balanced-accuracy", type=float, default=0.53)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=5)
    parser.add_argument("--max-dataset-rows", type=int, default=20000)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase173A broker-cost-aware 1H target learnability audit")
    return parser.parse_args(argv)


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    return float(num / den) if abs(float(den)) > 1e-12 else float(default)


def rolling_high_low_np(high: np.ndarray, low: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    high_roll = pd.Series(high).rolling(max(int(window), 1), min_periods=1).max().to_numpy(dtype=np.float64)
    low_roll = pd.Series(low).rolling(max(int(window), 1), min_periods=1).min().to_numpy(dtype=np.float64)
    return high_roll, low_roll


def event_feature_row(
    family: TargetFamilySpec,
    event: EventOutcome,
    split: str,
    fold: int,
    frame: pd.DataFrame,
    atr: np.ndarray,
    recent_high: np.ndarray,
    recent_low: np.ndarray,
    args: argparse.Namespace,
) -> EventFeatureRow:
    row = int(event.row_id)
    open_values = frame["open"].to_numpy(dtype=np.float64)
    high_values = frame["high"].to_numpy(dtype=np.float64)
    low_values = frame["low"].to_numpy(dtype=np.float64)
    close_values = frame["close"].to_numpy(dtype=np.float64)
    timestamp = pd.to_datetime(frame.at[row, "timestamp"], utc=True)
    atr_value = max(float(atr[row]), 1e-9)
    width = max(float(recent_high[row] - recent_low[row]), 1e-9)
    position = (float(close_values[row]) - float(recent_low[row])) / width
    spread_price = float(args.spread_value) if str(args.spread_mode) == "fixed" else float(close_values[row]) * float(args.spread_value) / 100.0

    def lag_ret(lag: int) -> float:
        past = max(row - int(lag), 0)
        return float((close_values[row] - close_values[past]) / atr_value)

    candle_range = max(float(high_values[row] - low_values[row]), 1e-9)
    body = float(close_values[row] - open_values[row])
    upper = float(high_values[row] - max(open_values[row], close_values[row]))
    lower = float(min(open_values[row], close_values[row]) - low_values[row])
    hour_angle = 2.0 * np.pi * float(timestamp.hour) / 24.0
    dow_angle = 2.0 * np.pi * float(timestamp.dayofweek) / 7.0
    return EventFeatureRow(
        family_id=family.family_id,
        row_id=row,
        timestamp=str(frame.at[row, "timestamp"]),
        split=split,
        fold=int(fold),
        side=str(event.side),
        zone=str(event.zone),
        label=str(event.label),
        target_positive=int(event.label == LABEL_POSITIVE),
        atr_score=float(event.atr_score),
        points_pnl=float(event.points_pnl),
        outcome=str(event.outcome),
        side_buy=float(event.side == "BUY"),
        side_sell=float(event.side == "SELL"),
        zone_top=float(event.zone == "top"),
        zone_bottom=float(event.zone == "bottom"),
        atr=float(atr_value),
        range_atr=float(candle_range / atr_value),
        body_atr=float(body / atr_value),
        upper_wick_atr=float(upper / atr_value),
        lower_wick_atr=float(lower / atr_value),
        recent_position=float(position),
        recent_width_atr=float(width / atr_value),
        dist_top_atr=float((recent_high[row] - close_values[row]) / atr_value),
        dist_bottom_atr=float((close_values[row] - recent_low[row]) / atr_value),
        ret_1_atr=lag_ret(1),
        ret_3_atr=lag_ret(3),
        ret_6_atr=lag_ret(6),
        ret_12_atr=lag_ret(12),
        ret_24_atr=lag_ret(24),
        hour_sin=float(np.sin(hour_angle)),
        hour_cos=float(np.cos(hour_angle)),
        dow_sin=float(np.sin(dow_angle)),
        dow_cos=float(np.cos(dow_angle)),
        spread_to_atr=float(spread_price / atr_value),
    )


def build_feature_rows(
    family: TargetFamilySpec,
    events: Sequence[EventOutcome],
    frame: pd.DataFrame,
    atr: np.ndarray,
    args: argparse.Namespace,
    split_indices_map: Mapping[str, np.ndarray],
    fold: int = 0,
) -> list[EventFeatureRow]:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    recent_high, recent_low = rolling_high_low_np(high, low, family.recent_window_bars)
    row_to_split: dict[int, str] = {}
    for split, indices in split_indices_map.items():
        for row in np.asarray(indices, dtype=np.int64):
            row_to_split[int(row)] = split
    rows: list[EventFeatureRow] = []
    for event in events:
        split = row_to_split.get(int(event.row_id), "other")
        if split == "other":
            continue
        rows.append(event_feature_row(family, event, split, fold, frame, atr, recent_high, recent_low, args))
    return rows


def matrix_from_rows(rows: Sequence[EventFeatureRow]) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    if not rows:
        return np.empty((0, len(FEATURE_COLUMNS)), dtype=np.float64), np.asarray([], dtype=np.int64), [], []
    x = np.asarray([[float(getattr(row, col)) for col in FEATURE_COLUMNS] for row in rows], dtype=np.float64)
    y = np.asarray([int(row.target_positive) for row in rows], dtype=np.int64)
    sides = [row.side for row in rows]
    labels = [row.label for row in rows]
    return x, y, sides, labels


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


class CentroidBinaryModel:
    def __init__(self) -> None:
        self.mean_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None
        self.pos_: np.ndarray | None = None
        self.neg_: np.ndarray | None = None
        self.threshold_: float = 0.0

    def fit(self, x_train: np.ndarray, y_train: np.ndarray) -> "CentroidBinaryModel":
        x = np.asarray(x_train, dtype=np.float64)
        y = np.asarray(y_train, dtype=np.int64)
        self.mean_ = np.nanmean(x, axis=0) if len(x) else np.zeros(x.shape[1] if x.ndim == 2 else 0)
        scale = np.nanstd(x, axis=0) if len(x) else np.ones_like(self.mean_)
        self.scale_ = np.where(scale <= 1e-9, 1.0, scale)
        z = (x - self.mean_) / self.scale_ if len(x) else x
        global_centroid = np.nanmean(z, axis=0) if len(z) else np.zeros_like(self.mean_)
        self.pos_ = np.nanmean(z[y == 1], axis=0) if np.any(y == 1) else global_centroid
        self.neg_ = np.nanmean(z[y == 0], axis=0) if np.any(y == 0) else global_centroid
        scores = self.score(x)
        self.threshold_ = select_threshold(y, scores)
        return self

    def score(self, x_values: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None or self.pos_ is None or self.neg_ is None:
            raise RuntimeError("CentroidBinaryModel must be fitted before scoring")
        x = np.asarray(x_values, dtype=np.float64)
        if len(x) == 0:
            return np.asarray([], dtype=np.float64)
        z = (x - self.mean_) / self.scale_
        d_pos = np.sqrt(np.mean((z - self.pos_) ** 2, axis=1))
        d_neg = np.sqrt(np.mean((z - self.neg_) ** 2, axis=1))
        return d_neg - d_pos

    def predict(self, x_values: np.ndarray) -> np.ndarray:
        return (self.score(x_values) >= float(self.threshold_)).astype(np.int64)


def select_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int64)
    s = np.asarray(scores, dtype=np.float64)
    if len(y) == 0:
        return 0.0
    candidates = np.unique(np.quantile(s, np.linspace(0.05, 0.95, 19))) if len(s) else np.asarray([0.0])
    best_threshold = float(candidates[0])
    best_score = -1.0
    for threshold in candidates:
        pred = (s >= float(threshold)).astype(np.int64)
        score = balanced_accuracy(y, pred)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def evaluate_split(model: CentroidBinaryModel, rows: Sequence[EventFeatureRow], train_dist: Mapping[str, float] | None, family_id: str, split: str) -> LearnabilitySplitRow:
    x, y, sides, labels = matrix_from_rows(rows)
    scores = model.score(x) if len(rows) else np.asarray([], dtype=np.float64)
    pred = (scores >= model.threshold_).astype(np.int64) if len(scores) else np.asarray([], dtype=np.int64)
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    timeouts = sum(1 for label in labels if label == LABEL_TIMEOUT)
    positive_rate = float(positives / len(y)) if len(y) else 0.0
    ap = average_precision(y, scores)
    base_ap = positive_rate
    buy_mask = np.asarray([side == "BUY" for side in sides], dtype=bool)
    sell_mask = np.asarray([side == "SELL" for side in sides], dtype=bool)
    dist = {
        LABEL_POSITIVE: positive_rate,
        LABEL_NEGATIVE: float(negatives / len(y)) if len(y) else 0.0,
        LABEL_TIMEOUT: float(timeouts / len(y)) if len(y) else 0.0,
    }
    return LearnabilitySplitRow(
        family_id=family_id,
        split=split,
        events=int(len(rows)),
        positives=positives,
        negatives=negatives,
        timeouts=int(timeouts),
        positive_rate=positive_rate,
        base_ap=base_ap,
        model_ap=ap,
        ap_lift=float(ap - base_ap),
        balanced_accuracy=balanced_accuracy(y, pred),
        f1=f1_score(y, pred),
        threshold=float(model.threshold_),
        buy_events=int(np.sum(buy_mask)),
        buy_ap=average_precision(y[buy_mask], scores[buy_mask]) if np.any(buy_mask) else 0.0,
        sell_events=int(np.sum(sell_mask)),
        sell_ap=average_precision(y[sell_mask], scores[sell_mask]) if np.any(sell_mask) else 0.0,
        label_psi_vs_train=0.0 if train_dist is None else label_psi(dist, train_dist),
    )


def split_rows_by_name(rows: Sequence[EventFeatureRow]) -> dict[str, list[EventFeatureRow]]:
    output: dict[str, list[EventFeatureRow]] = {"train": [], "validation": [], "test": []}
    for row in rows:
        if row.split in output:
            output[row.split].append(row)
    return output


def build_family_dataset(family: TargetFamilySpec, frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace) -> tuple[list[EventFeatureRow], list[EventOutcome]]:
    top_mask, bottom_mask, _ = build_zone_masks(
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
    events = evaluate_family_events(family, frame, atr, top_mask, bottom_mask, args, float(args.spread_value))
    train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
    rows = build_feature_rows(
        family,
        events,
        frame,
        atr,
        args,
        {"train": train_idx, "validation": validation_idx, "test": test_idx},
        0,
    )
    return rows, events


def class_balance_gate(split: LearnabilitySplitRow, args: argparse.Namespace, name: str) -> int:
    min_events = {
        "train": int(args.min_train_events),
        "validation": int(args.min_validation_events),
        "test": int(args.min_test_events),
    }.get(name, int(args.min_test_events))
    return int(
        split.events >= min_events
        and split.positive_rate >= float(args.min_positive_rate)
        and split.positive_rate <= float(args.max_positive_rate)
    )


def static_family_learnability(family: TargetFamilySpec, dataset_rows: Sequence[EventFeatureRow], args: argparse.Namespace) -> tuple[list[LearnabilitySplitRow], CentroidBinaryModel]:
    by_split = split_rows_by_name(dataset_rows)
    x_train, y_train, _sides, _labels = matrix_from_rows(by_split["train"])
    model = CentroidBinaryModel().fit(x_train, y_train)
    train_dist = {
        LABEL_POSITIVE: float(np.mean(y_train == 1)) if len(y_train) else 0.0,
        LABEL_NEGATIVE: float(np.mean(y_train == 0)) if len(y_train) else 0.0,
        LABEL_TIMEOUT: 0.0,
    }
    return [
        evaluate_split(model, by_split["train"], None, family.family_id, "train"),
        evaluate_split(model, by_split["validation"], train_dist, family.family_id, "validation"),
        evaluate_split(model, by_split["test"], train_dist, family.family_id, "test"),
    ], model


def walkforward_learnability(family: TargetFamilySpec, frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace) -> list[LearnabilityFoldRow]:
    specs = build_fold_specs(
        len(frame),
        int(args.fold_train_bars),
        int(args.fold_validation_bars),
        int(args.fold_test_bars),
        int(args.fold_step_bars),
        int(args.purge_gap),
        int(args.max_folds),
    )
    if not specs:
        return []
    top_mask, bottom_mask, _ = build_zone_masks(
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
    events = evaluate_family_events(family, frame, atr, top_mask, bottom_mask, args, float(args.spread_value))
    rows: list[LearnabilityFoldRow] = []
    for spec in specs:
        train_idx = np.arange(spec.train_start, spec.train_end, dtype=np.int64)
        val_idx = np.arange(spec.validation_start, spec.validation_end, dtype=np.int64)
        test_idx = np.arange(spec.test_start, spec.test_end, dtype=np.int64)
        dataset = build_feature_rows(
            family,
            events,
            frame,
            atr,
            args,
            {"train": train_idx, "validation": val_idx, "test": test_idx},
            int(spec.fold),
        )
        split_map = split_rows_by_name(dataset)
        if not split_map["train"]:
            continue
        x_train, y_train, _sides, _labels = matrix_from_rows(split_map["train"])
        model = CentroidBinaryModel().fit(x_train, y_train)
        train_dist = {
            LABEL_POSITIVE: float(np.mean(y_train == 1)) if len(y_train) else 0.0,
            LABEL_NEGATIVE: float(np.mean(y_train == 0)) if len(y_train) else 0.0,
            LABEL_TIMEOUT: 0.0,
        }
        train_eval = evaluate_split(model, split_map["train"], None, family.family_id, "train")
        val_eval = evaluate_split(model, split_map["validation"], train_dist, family.family_id, "validation")
        test_eval = evaluate_split(model, split_map["test"], train_dist, family.family_id, "test")
        pass_gate = int(
            class_balance_gate(train_eval, args, "train")
            and class_balance_gate(val_eval, args, "validation")
            and class_balance_gate(test_eval, args, "test")
            and val_eval.label_psi_vs_train <= float(args.max_label_psi)
            and test_eval.label_psi_vs_train <= float(args.max_label_psi)
            and val_eval.ap_lift >= float(args.min_ap_lift)
            and test_eval.ap_lift >= float(args.min_ap_lift)
            and test_eval.balanced_accuracy >= float(args.min_balanced_accuracy)
        )
        rows.append(
            LearnabilityFoldRow(
                family_id=family.family_id,
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
                validation_label_psi=float(val_eval.label_psi_vs_train),
                test_label_psi=float(test_eval.label_psi_vs_train),
                pass_gate=pass_gate,
            )
        )
    return rows


def summarize_family(
    family: TargetFamilySpec,
    split_rows: Sequence[LearnabilitySplitRow],
    wf_rows: Sequence[LearnabilityFoldRow],
    args: argparse.Namespace,
) -> LearnabilityFamilyRow:
    by_split = {row.split: row for row in split_rows}
    train = by_split["train"]
    val = by_split["validation"]
    test = by_split["test"]
    balance_gate = int(
        class_balance_gate(train, args, "train")
        and class_balance_gate(val, args, "validation")
        and class_balance_gate(test, args, "test")
        and val.label_psi_vs_train <= float(args.max_label_psi)
        and test.label_psi_vs_train <= float(args.max_label_psi)
    )
    static_gate = int(
        balance_gate
        and val.ap_lift >= float(args.min_ap_lift)
        and test.ap_lift >= float(args.min_ap_lift)
        and val.balanced_accuracy >= float(args.min_balanced_accuracy)
        and test.balanced_accuracy >= float(args.min_balanced_accuracy)
    )
    wf_pass_count = sum(row.pass_gate for row in wf_rows)
    wf_ratio = float(wf_pass_count / len(wf_rows)) if wf_rows else 0.0
    wf_gate = int(len(wf_rows) >= int(args.min_walkforward_folds) and wf_ratio >= float(args.min_walkforward_pass_ratio))
    ready = int(static_gate and wf_gate)
    warnings: list[str] = []
    if not balance_gate:
        warnings.append("class balance or label stability gate failed")
    if not static_gate:
        warnings.append("static learnability gate failed")
    if not wf_gate:
        warnings.append("walk-forward learnability gate failed")
    return LearnabilityFamilyRow(
        family_id=family.family_id,
        label=family.label,
        train_events=int(train.events),
        validation_events=int(val.events),
        test_events=int(test.events),
        train_positive_rate=float(train.positive_rate),
        validation_positive_rate=float(val.positive_rate),
        test_positive_rate=float(test.positive_rate),
        validation_label_psi=float(val.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        validation_ap_lift=float(val.ap_lift),
        test_ap_lift=float(test.ap_lift),
        validation_balanced_accuracy=float(val.balanced_accuracy),
        test_balanced_accuracy=float(test.balanced_accuracy),
        validation_f1=float(val.f1),
        test_f1=float(test.f1),
        validation_buy_ap=float(val.buy_ap),
        validation_sell_ap=float(val.sell_ap),
        test_buy_ap=float(test.buy_ap),
        test_sell_ap=float(test.sell_ap),
        walkforward_folds=int(len(wf_rows)),
        walkforward_pass_folds=int(wf_pass_count),
        walkforward_pass_ratio=float(wf_ratio),
        class_balance_gate=int(balance_gate),
        static_learnability_gate=int(static_gate),
        walkforward_learnability_gate=int(wf_gate),
        target_learnability_ready_gate=int(ready),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase173Report) -> str:
    family_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{int(row['train_events'])}/{int(row['validation_events'])}/{int(row['test_events'])}</td>"
        f"<td>{float(row['validation_ap_lift']):.4f}</td>"
        f"<td>{float(row['test_ap_lift']):.4f}</td>"
        f"<td>{float(row['test_balanced_accuracy']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['target_learnability_ready_gate'])}</td></tr>"
        for row in report.family_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase173A broker-cost-aware 1H target learnability audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'target_learnability_ready_gate': report.target_learnability_ready_gate,
        'selected_family_id': report.selected_family_id,
        'selected_family_ready_gate': report.selected_family_ready_gate,
        'learnable_families': report.learnable_families,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Family rows</h2><table><thead><tr><th>Family</th><th>Events train/val/test</th><th>Val AP lift</th><th>Test AP lift</th><th>Test bAcc</th><th>WF pass</th><th>Ready</th></tr></thead><tbody>{family_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE173A BROKER-COST-AWARE 1H TARGET LEARNABILITY AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        families = parse_families(args.families)
        family_rows: list[LearnabilityFamilyRow] = []
        split_rows: list[LearnabilitySplitRow] = []
        wf_rows: list[LearnabilityFoldRow] = []
        dataset_rows: list[dict[str, Any]] = []
        for family in families:
            rows, _events = build_family_dataset(family, frame, atr, args)
            static_rows, _model = static_family_learnability(family, rows, args)
            family_wf = walkforward_learnability(family, frame, atr, args)
            summary = summarize_family(family, static_rows, family_wf, args)
            family_rows.append(summary)
            split_rows.extend(static_rows)
            wf_rows.extend(family_wf)
            for row in rows[: max(int(args.max_dataset_rows), 0)]:
                dataset_rows.append(asdict(row))
        ranked = sorted(
            family_rows,
            key=lambda row: (
                row.target_learnability_ready_gate,
                row.walkforward_pass_ratio,
                row.test_ap_lift,
                row.test_balanced_accuracy,
            ),
            reverse=True,
        )
        ready_count = int(sum(row.target_learnability_ready_gate for row in ranked))
        selected = ranked[0] if ranked else None
        output_families = output_dir / "latest_families.csv"
        output_splits = output_dir / "latest_splits.csv"
        output_wf = output_dir / "latest_walkforward.csv"
        output_dataset = output_dir / "latest_dataset.csv"
        write_csv(output_families, [asdict(row) for row in ranked])
        write_csv(output_splits, [asdict(row) for row in split_rows])
        write_csv(output_wf, [asdict(row) for row in wf_rows])
        write_csv(output_dataset, dataset_rows)
        report = Phase173Report(
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
            learnable_families=ready_count,
            selected_family_id=str(selected.family_id) if selected else "",
            selected_family_ready_gate=int(selected.target_learnability_ready_gate) if selected else 0,
            target_learnability_ready_gate=int(ready_count > 0),
            feature_columns=list(FEATURE_COLUMNS),
            family_rows=[asdict(row) for row in ranked],
            split_rows=[asdict(row) for row in split_rows],
            walkforward_rows=[asdict(row) for row in wf_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_families_csv=str(output_families),
            output_splits_csv=str(output_splits),
            output_walkforward_csv=str(output_wf),
            output_dataset_csv=str(output_dataset),
            production_status="BLOCKED — Phase173A target learnability audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase173A target learnability audit complete")
        print(f"  families          : {report.candidate_families}")
        print(f"  learnable         : {report.learnable_families}")
        print(f"  selected          : {report.selected_family_id or 'none'}")
        print(f"  ready gate        : {report.target_learnability_ready_gate}")
        print(f"  output            : {report.output_json}")
        print(f"  elapsed           : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
