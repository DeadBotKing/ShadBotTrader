"""Phase172A: broker-cost-aware 1H target-family design audit.

After the current 5M and locked 1H pivot routes were rejected, Phase171A chose a
new broker-cost-aware 1H target-family design audit as the next research lane.
This script evaluates target families only. It does not train a model and does
not approve paper/live trading.

Each target family defines a live-known candidate geometry and side mapping, and
labels candidate events by broker-cost-aware first-hit/replay outcome using a
fixed spread around the real Alpari sample (default 0.4). The audit measures
label density, label stability, opportunity distribution, naive replay, stress
spread behavior, and walk-forward label stability before any training is allowed.
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

from audit_pivot_1h_entry_feasibility import (  # noqa: E402
    DEFAULT_STORAGE,
    build_zone_masks,
    read_ohlc_frame,
    resolve_flat_path_arg,
    sides_for_row,
)
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_bottom_buy_candidate import max_drawdown  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_SELL, trade_path  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/broker_cost_aware_1h_target_family")
DEFAULT_FAMILIES = (
    "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;"
    "CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48;"
    "CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;"
    "CA4_REV_MID:cost_reversal_mid:reversal:1:24:0.10:0.85:0.15:1:1.0:0:1.5:1.0:24"
)
SIDE_TO_ACTION = {"BUY": ACTION_BUY, "SELL": ACTION_SELL}
LABEL_POSITIVE = "POSITIVE"
LABEL_NEGATIVE = "NEGATIVE"
LABEL_TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class TargetFamilySpec:
    family_id: str
    label: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    tp_atr: float
    sl_atr: float
    hold_bars: int


@dataclass(frozen=True)
class EventOutcome:
    family_id: str
    row_id: int
    signal_row_id: int
    entry_row_id: int
    exit_row_id: int
    timestamp: str
    zone: str
    side: str
    label: str
    atr_score: float
    points_pnl: float
    outcome: str
    atr_value: float
    spread_mode: str
    spread_value: float
    tp_atr: float
    sl_atr: float
    hold_bars: int


@dataclass(frozen=True)
class SplitFamilyMetrics:
    family_id: str
    split: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    candidate_events: int
    event_rate: float
    top_events: int
    bottom_events: int
    buy_events: int
    sell_events: int
    positive_labels: int
    negative_labels: int
    timeout_labels: int
    positive_rate: float
    negative_rate: float
    timeout_rate: float
    mean_atr_score: float
    sum_atr_score: float
    independent_profit_factor: float
    independent_win_rate: float
    buy_mean_atr_score: float
    sell_mean_atr_score: float
    chronological_trades: int
    chronological_total_cash_pnl: float
    chronological_profit_factor: float
    chronological_final_balance: float
    chronological_max_drawdown_cash: float
    label_psi_vs_train: float


@dataclass(frozen=True)
class FamilySummaryRow:
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
    hold_bars: int
    spread_mode: str
    spread_value: float
    stress_spread_value: float
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_independent_pf: float
    validation_independent_pf: float
    test_independent_pf: float
    train_chrono_pf: float
    validation_chrono_pf: float
    test_chrono_pf: float
    stress_test_positive_rate: float
    stress_test_independent_pf: float
    stress_test_chrono_pf: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    label_stability_gate: int
    density_gate: int
    stress_gate: int
    walkforward_gate: int
    family_ready_for_training_gate: int
    warnings: str


@dataclass(frozen=True)
class WalkForwardFamilyRow:
    family_id: str
    fold: int
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_independent_pf: float
    validation_independent_pf: float
    test_independent_pf: float
    test_chrono_pf: float
    test_chrono_pnl: float
    pass_gate: int


@dataclass(frozen=True)
class Phase172Report:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    spread_mode: str
    spread_value: float
    stress_spread_value: float
    candidate_families: int
    ready_families: int
    selected_family_id: str
    selected_family_ready_gate: int
    target_family_ready_for_training_gate: int
    family_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_events_csv: str
    production_status: str


def safe_slug(text: str) -> str:
    cleaned: list[str] = []
    for char in str(text).strip():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_", " ", "."}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "family"


def parse_families(text: str) -> list[TargetFamilySpec]:
    families: list[TargetFamilySpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 14:
            raise RuntimeError(
                "family format must be ID:label:mapping:delay:rw:zone:top:bottom:exclude:minw:maxw:tp:sl:hold"
            )
        families.append(
            TargetFamilySpec(
                family_id=safe_slug(parts[0]),
                label=safe_slug(parts[1]),
                side_mapping=parts[2],
                entry_delay_bars=max(int(parts[3]), 0),
                recent_window_bars=max(int(parts[4]), 1),
                pivot_zone_atr=max(float(parts[5]), 0.0),
                top_position_threshold=float(parts[6]),
                bottom_position_threshold=float(parts[7]),
                exclude_both_zones=1 if parts[8] != "0" else 0,
                min_range_width_atr=max(float(parts[9]), 0.0),
                max_range_width_atr=max(float(parts[10]), 0.0),
                tp_atr=max(float(parts[11]), 0.01),
                sl_atr=max(float(parts[12]), 0.01),
                hold_bars=max(int(parts[13]), 1),
            )
        )
    if not families:
        raise RuntimeError("At least one target family is required")
    return families


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit broker-cost-aware 1H target families before any model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--families", default=DEFAULT_FAMILIES)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.4)
    parser.add_argument("--stress-spread-value", type=float, default=0.5)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=24)
    parser.add_argument("--fold-train-bars", type=int, default=18000)
    parser.add_argument("--fold-validation-bars", type=int, default=4000)
    parser.add_argument("--fold-test-bars", type=int, default=4000)
    parser.add_argument("--fold-step-bars", type=int, default=4000)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--min-train-events", type=int, default=100)
    parser.add_argument("--min-validation-events", type=int, default=20)
    parser.add_argument("--min-test-events", type=int, default=20)
    parser.add_argument("--min-positive-rate", type=float, default=0.10)
    parser.add_argument("--max-positive-rate", type=float, default=0.70)
    parser.add_argument("--max-label-psi", type=float, default=0.20)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=5)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase172A broker-cost-aware 1H target-family design audit")
    return parser.parse_args(argv)


def label_for_score(score: float, outcome: str) -> str:
    if score > 1e-12:
        return LABEL_POSITIVE
    if score < -1e-12:
        return LABEL_NEGATIVE
    return LABEL_TIMEOUT if outcome == "timeout" else LABEL_TIMEOUT


def action_distribution(events: Sequence[EventOutcome]) -> dict[str, float]:
    total = len(events)
    if total == 0:
        return {LABEL_POSITIVE: 0.0, LABEL_NEGATIVE: 0.0, LABEL_TIMEOUT: 0.0}
    return {
        LABEL_POSITIVE: sum(1 for event in events if event.label == LABEL_POSITIVE) / total,
        LABEL_NEGATIVE: sum(1 for event in events if event.label == LABEL_NEGATIVE) / total,
        LABEL_TIMEOUT: sum(1 for event in events if event.label == LABEL_TIMEOUT) / total,
    }


def label_psi(current: Mapping[str, float], baseline: Mapping[str, float]) -> float:
    eps = 1e-6
    total = 0.0
    for key in (LABEL_POSITIVE, LABEL_NEGATIVE, LABEL_TIMEOUT):
        actual = max(float(current.get(key, 0.0)), eps)
        expected = max(float(baseline.get(key, 0.0)), eps)
        total += (actual - expected) * float(np.log(actual / expected))
    return float(total)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def evaluate_family_events(
    family: TargetFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    args: argparse.Namespace,
    spread_value: float,
) -> list[EventOutcome]:
    trade_args = SimpleNamespace(
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        same_bar_policy=str(args.same_bar_policy),
    )
    events: list[EventOutcome] = []
    for row_id in range(len(frame)):
        row_events = sides_for_row(family.side_mapping, bool(top_mask[row_id]), bool(bottom_mask[row_id]))
        for zone, side_name in row_events:
            signal_row = row_id + int(family.entry_delay_bars)
            if signal_row >= len(frame) - 1:
                continue
            atr_value = float(atr[signal_row])
            if not np.isfinite(atr_value) or atr_value <= 0:
                continue
            tp_distance = atr_value * float(family.tp_atr)
            sl_distance = atr_value * float(family.sl_atr)
            path = trade_path(
                frame,
                signal_row,
                SIDE_TO_ACTION[side_name],
                tp_distance,
                sl_distance,
                int(family.hold_bars),
                trade_args,
            )
            if path is None:
                continue
            points, entry_row, exit_row, _entry, _tp, _sl, _exit_price, outcome = path
            score = float(points / atr_value) if atr_value > 0 else 0.0
            events.append(
                EventOutcome(
                    family_id=family.family_id,
                    row_id=int(row_id),
                    signal_row_id=int(signal_row),
                    entry_row_id=int(entry_row),
                    exit_row_id=int(exit_row),
                    timestamp=str(frame.at[row_id, "timestamp"]),
                    zone=str(zone),
                    side=str(side_name),
                    label=label_for_score(score, str(outcome)),
                    atr_score=float(score),
                    points_pnl=float(points),
                    outcome=str(outcome),
                    atr_value=float(atr_value),
                    spread_mode=str(args.spread_mode),
                    spread_value=float(spread_value),
                    tp_atr=float(family.tp_atr),
                    sl_atr=float(family.sl_atr),
                    hold_bars=int(family.hold_bars),
                )
            )
    return events


def chronological_replay(events: Sequence[EventOutcome], family: TargetFamilySpec, args: argparse.Namespace) -> dict[str, float]:
    balance = float(args.initial_capital)
    balances = [balance]
    open_until = -1
    pnls: list[float] = []
    for event in sorted(events, key=lambda item: item.signal_row_id):
        if int(event.signal_row_id) <= open_until:
            continue
        sl_distance = float(event.atr_value) * float(family.sl_atr)
        risk_amount = max(balance * float(args.risk_per_trade), 0.0)
        quantity = risk_amount / sl_distance if sl_distance > 0 else 0.0
        cash_pnl = float(event.points_pnl) * quantity
        balance += cash_pnl
        balances.append(balance)
        pnls.append(cash_pnl)
        open_until = max(open_until, int(event.exit_row_id))
    gross_profit = float(sum(value for value in pnls if value > 0))
    gross_loss = float(abs(sum(value for value in pnls if value < 0)))
    return {
        "trades": float(len(pnls)),
        "total_cash_pnl": float(sum(pnls)),
        "profit_factor": gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        "final_balance": float(balance),
        "max_drawdown_cash": float(max_drawdown(balances)),
    }


def split_metrics(
    family: TargetFamilySpec,
    split: str,
    indices: np.ndarray,
    events: Sequence[EventOutcome],
    frame: pd.DataFrame,
    args: argparse.Namespace,
    train_dist: Mapping[str, float] | None,
) -> SplitFamilyMetrics:
    idx_set = set(int(value) for value in np.asarray(indices, dtype=np.int64))
    split_events = [event for event in events if int(event.row_id) in idx_set]
    scores = [float(event.atr_score) for event in split_events]
    labels = [event.label for event in split_events]
    buy_scores = [float(event.atr_score) for event in split_events if event.side == "BUY"]
    sell_scores = [float(event.atr_score) for event in split_events if event.side == "SELL"]
    dist = action_distribution(split_events)
    chron = chronological_replay(split_events, family, args)
    first_ts = str(frame.at[int(indices[0]), "timestamp"]) if len(indices) else ""
    last_ts = str(frame.at[int(indices[-1]), "timestamp"]) if len(indices) else ""
    return SplitFamilyMetrics(
        family_id=family.family_id,
        split=split,
        rows=int(len(indices)),
        first_timestamp=first_ts,
        last_timestamp=last_ts,
        candidate_events=int(len(split_events)),
        event_rate=float(len(split_events) / len(indices)) if len(indices) else 0.0,
        top_events=sum(1 for event in split_events if event.zone == "top"),
        bottom_events=sum(1 for event in split_events if event.zone == "bottom"),
        buy_events=sum(1 for event in split_events if event.side == "BUY"),
        sell_events=sum(1 for event in split_events if event.side == "SELL"),
        positive_labels=sum(1 for label in labels if label == LABEL_POSITIVE),
        negative_labels=sum(1 for label in labels if label == LABEL_NEGATIVE),
        timeout_labels=sum(1 for label in labels if label == LABEL_TIMEOUT),
        positive_rate=float(dist[LABEL_POSITIVE]),
        negative_rate=float(dist[LABEL_NEGATIVE]),
        timeout_rate=float(dist[LABEL_TIMEOUT]),
        mean_atr_score=float(np.mean(scores)) if scores else 0.0,
        sum_atr_score=float(np.sum(scores)) if scores else 0.0,
        independent_profit_factor=profit_factor(scores),
        independent_win_rate=float(np.mean(np.asarray(scores) > 0)) if scores else 0.0,
        buy_mean_atr_score=float(np.mean(buy_scores)) if buy_scores else 0.0,
        sell_mean_atr_score=float(np.mean(sell_scores)) if sell_scores else 0.0,
        chronological_trades=int(chron["trades"]),
        chronological_total_cash_pnl=float(chron["total_cash_pnl"]),
        chronological_profit_factor=float(chron["profit_factor"]),
        chronological_final_balance=float(chron["final_balance"]),
        chronological_max_drawdown_cash=float(chron["max_drawdown_cash"]),
        label_psi_vs_train=0.0 if train_dist is None else label_psi(dist, train_dist),
    )


def family_static_rows(
    family: TargetFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    args: argparse.Namespace,
    spread_value: float,
) -> tuple[list[SplitFamilyMetrics], list[EventOutcome]]:
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
    events = evaluate_family_events(family, frame, atr, top_mask, bottom_mask, args, spread_value)
    train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
    train_set = set(int(value) for value in train_idx)
    train_events = [event for event in events if int(event.row_id) in train_set]
    train_dist = action_distribution(train_events)
    rows = [
        split_metrics(family, "train", train_idx, events, frame, args, None),
        split_metrics(family, "validation", validation_idx, events, frame, args, train_dist),
        split_metrics(family, "test", test_idx, events, frame, args, train_dist),
    ]
    return rows, events


def density_gate(metrics: SplitFamilyMetrics, args: argparse.Namespace, split: str) -> int:
    min_events = {
        "train": int(args.min_train_events),
        "validation": int(args.min_validation_events),
        "test": int(args.min_test_events),
    }.get(split, int(args.min_test_events))
    return int(
        metrics.candidate_events >= min_events
        and metrics.positive_rate >= float(args.min_positive_rate)
        and metrics.positive_rate <= float(args.max_positive_rate)
    )


def walk_forward_rows(family: TargetFamilySpec, frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace) -> list[WalkForwardFamilyRow]:
    specs = build_fold_specs(
        len(frame),
        int(args.fold_train_bars),
        int(args.fold_validation_bars),
        int(args.fold_test_bars),
        int(args.fold_step_bars),
        int(args.purge_gap),
        int(args.max_folds),
    )
    rows: list[WalkForwardFamilyRow] = []
    if not specs:
        return rows
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
    for spec in specs:
        train_idx = np.arange(spec.train_start, spec.train_end, dtype=np.int64)
        val_idx = np.arange(spec.validation_start, spec.validation_end, dtype=np.int64)
        test_idx = np.arange(spec.test_start, spec.test_end, dtype=np.int64)
        train_set = set(int(value) for value in train_idx)
        train_events = [event for event in events if int(event.row_id) in train_set]
        train_dist = action_distribution(train_events)
        train = split_metrics(family, "train", train_idx, events, frame, args, None)
        val = split_metrics(family, "validation", val_idx, events, frame, args, train_dist)
        test = split_metrics(family, "test", test_idx, events, frame, args, train_dist)
        pass_gate = int(
            density_gate(train, args, "train")
            and density_gate(val, args, "validation")
            and density_gate(test, args, "test")
            and val.label_psi_vs_train <= float(args.max_label_psi)
            and test.label_psi_vs_train <= float(args.max_label_psi)
        )
        rows.append(
            WalkForwardFamilyRow(
                family_id=family.family_id,
                fold=int(spec.fold),
                train_events=int(train.candidate_events),
                validation_events=int(val.candidate_events),
                test_events=int(test.candidate_events),
                train_positive_rate=float(train.positive_rate),
                validation_positive_rate=float(val.positive_rate),
                test_positive_rate=float(test.positive_rate),
                validation_label_psi=float(val.label_psi_vs_train),
                test_label_psi=float(test.label_psi_vs_train),
                train_independent_pf=float(train.independent_profit_factor),
                validation_independent_pf=float(val.independent_profit_factor),
                test_independent_pf=float(test.independent_profit_factor),
                test_chrono_pf=float(test.chronological_profit_factor),
                test_chrono_pnl=float(test.chronological_total_cash_pnl),
                pass_gate=pass_gate,
            )
        )
    return rows


def build_family_summary(
    family: TargetFamilySpec,
    static_rows: Sequence[SplitFamilyMetrics],
    wf_rows: Sequence[WalkForwardFamilyRow],
    stress_test: SplitFamilyMetrics,
    args: argparse.Namespace,
) -> FamilySummaryRow:
    by_split = {row.split: row for row in static_rows}
    train = by_split["train"]
    val = by_split["validation"]
    test = by_split["test"]
    density = int(density_gate(train, args, "train") and density_gate(val, args, "validation") and density_gate(test, args, "test"))
    stability = int(val.label_psi_vs_train <= float(args.max_label_psi) and test.label_psi_vs_train <= float(args.max_label_psi))
    stress_gate = int(stress_test.positive_rate >= float(args.min_positive_rate) and stress_test.independent_profit_factor >= 1.0)
    wf_pass_count = sum(row.pass_gate for row in wf_rows)
    wf_ratio = float(wf_pass_count / len(wf_rows)) if wf_rows else 0.0
    wf_gate = int(len(wf_rows) >= int(args.min_walkforward_folds) and wf_ratio >= float(args.min_walkforward_pass_ratio))
    warnings: list[str] = []
    if not density:
        warnings.append("density gate failed")
    if not stability:
        warnings.append("label stability gate failed")
    if not stress_gate:
        warnings.append("stress spread gate failed")
    if not wf_gate:
        warnings.append("walk-forward label stability gate failed")
    ready = int(density and stability and stress_gate and wf_gate)
    return FamilySummaryRow(
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
        hold_bars=int(family.hold_bars),
        spread_mode=str(args.spread_mode),
        spread_value=float(args.spread_value),
        stress_spread_value=float(args.stress_spread_value),
        train_events=int(train.candidate_events),
        validation_events=int(val.candidate_events),
        test_events=int(test.candidate_events),
        train_positive_rate=float(train.positive_rate),
        validation_positive_rate=float(val.positive_rate),
        test_positive_rate=float(test.positive_rate),
        validation_label_psi=float(val.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        train_independent_pf=float(train.independent_profit_factor),
        validation_independent_pf=float(val.independent_profit_factor),
        test_independent_pf=float(test.independent_profit_factor),
        train_chrono_pf=float(train.chronological_profit_factor),
        validation_chrono_pf=float(val.chronological_profit_factor),
        test_chrono_pf=float(test.chronological_profit_factor),
        stress_test_positive_rate=float(stress_test.positive_rate),
        stress_test_independent_pf=float(stress_test.independent_profit_factor),
        stress_test_chrono_pf=float(stress_test.chronological_profit_factor),
        walkforward_folds=int(len(wf_rows)),
        walkforward_pass_folds=int(wf_pass_count),
        walkforward_pass_ratio=float(wf_ratio),
        label_stability_gate=int(stability),
        density_gate=int(density),
        stress_gate=int(stress_gate),
        walkforward_gate=int(wf_gate),
        family_ready_for_training_gate=int(ready),
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


def render_html(title: str, report: Phase172Report) -> str:
    family_rows = "".join(
        f"<tr><td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{int(row['train_events'])}/{int(row['validation_events'])}/{int(row['test_events'])}</td>"
        f"<td>{float(row['train_positive_rate']):.3f}</td>"
        f"<td>{float(row['validation_positive_rate']):.3f}</td>"
        f"<td>{float(row['test_positive_rate']):.3f}</td>"
        f"<td>{float(row['test_label_psi']):.4f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['family_ready_for_training_gate'])}</td></tr>"
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase172A broker-cost-aware 1H target-family design audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'target_family_ready_for_training_gate': report.target_family_ready_for_training_gate,
        'selected_family_id': report.selected_family_id,
        'selected_family_ready_gate': report.selected_family_ready_gate,
        'ready_families': report.ready_families,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Family rows</h2><table><thead><tr><th>Family</th><th>Events train/val/test</th><th>Train +rate</th><th>Val +rate</th><th>Test +rate</th><th>Test PSI</th><th>WF pass</th><th>Ready</th></tr></thead><tbody>{family_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE172A BROKER-COST-AWARE 1H TARGET-FAMILY AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        families = parse_families(args.families)
        all_split_rows: list[dict[str, Any]] = []
        all_wf_rows: list[dict[str, Any]] = []
        all_event_rows: list[dict[str, Any]] = []
        family_summaries: list[FamilySummaryRow] = []
        for family in families:
            static_rows, events = family_static_rows(family, frame, atr, args, float(args.spread_value))
            stress_rows, _stress_events = family_static_rows(family, frame, atr, args, float(args.stress_spread_value))
            stress_test = next(row for row in stress_rows if row.split == "test")
            wf = walk_forward_rows(family, frame, atr, args)
            summary = build_family_summary(family, static_rows, wf, stress_test, args)
            family_summaries.append(summary)
            all_split_rows.extend(asdict(row) for row in static_rows)
            all_wf_rows.extend(asdict(row) for row in wf)
            all_event_rows.extend(asdict(event) for event in events)
        ranked = sorted(
            family_summaries,
            key=lambda row: (
                row.family_ready_for_training_gate,
                row.walkforward_pass_ratio,
                row.label_stability_gate,
                row.density_gate,
                row.stress_gate,
                row.test_independent_pf,
            ),
            reverse=True,
        )
        selected = ranked[0] if ranked else None
        ready_count = int(sum(row.family_ready_for_training_gate for row in ranked))
        output_candidates = output_dir / "latest_candidates.csv"
        output_splits = output_dir / "latest_splits.csv"
        output_wf = output_dir / "latest_walkforward.csv"
        output_events = output_dir / "latest_events.csv"
        write_csv(output_candidates, [asdict(row) for row in ranked])
        write_csv(output_splits, all_split_rows)
        write_csv(output_wf, all_wf_rows)
        write_csv(output_events, all_event_rows)
        report = Phase172Report(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            spread_mode=str(args.spread_mode),
            spread_value=float(args.spread_value),
            stress_spread_value=float(args.stress_spread_value),
            candidate_families=int(len(families)),
            ready_families=ready_count,
            selected_family_id=str(selected.family_id) if selected else "",
            selected_family_ready_gate=int(selected.family_ready_for_training_gate) if selected else 0,
            target_family_ready_for_training_gate=int(ready_count > 0),
            family_rows=[asdict(row) for row in ranked],
            split_rows=all_split_rows,
            walkforward_rows=all_wf_rows,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(output_candidates),
            output_splits_csv=str(output_splits),
            output_walkforward_csv=str(output_wf),
            output_events_csv=str(output_events),
            production_status="BLOCKED — Phase172A target-family design audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase172A target-family audit complete")
        print(f"  families        : {report.candidate_families}")
        print(f"  ready families  : {report.ready_families}")
        print(f"  selected        : {report.selected_family_id or 'none'}")
        print(f"  ready gate      : {report.target_family_ready_for_training_gate}")
        print(f"  output          : {report.output_json}")
        print(f"  elapsed         : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
