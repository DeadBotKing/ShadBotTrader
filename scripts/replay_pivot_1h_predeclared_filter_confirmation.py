"""Phase168A: 1H predeclared filter confirmation replay.

Phase167A attributed the locked 1H candidate failures and found no strong rescue
filter, but a small set of predeclared filters remained diagnostically relevant.
This phase performs a confirmation-only comparison of that fixed filter set:

* none
* max_spread_atr_0.10
* buy_leg_only
* buy_leg_only+max_spread_atr_0.10

No new grid search, no threshold optimization, no model training, and no
paper/live/production approval.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_pivot_1h_entry_feasibility import (  # noqa: E402
    DEFAULT_STORAGE,
    build_zone_masks,
    parse_float_grid,
    read_ohlc_frame,
    resolve_flat_path_arg,
)
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_1h_fixed_spread_candidate_lockdown import LockdownSplitSummary, simulate_locked_split  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import WalkForwardFoldSpec, build_fold_specs  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_predeclared_filter_confirmation")
DEFAULT_FILTERS = "none,max_spread_atr_0.10,buy_leg_only,buy_leg_only+max_spread_atr_0.10"
ALLOWED_FILTER_COMPONENTS = {"none", "buy_leg_only", "sell_leg_only", "min_atr_q50", "min_atr_q75"}


@dataclass(frozen=True)
class FilterFoldRow:
    filter_name: str
    fold: int
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    train_final_balance: float
    train_positive_month_ratio: float
    train_worst_month_pnl: float
    train_pass_gate: int
    validation_trades: int
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_final_balance: float
    validation_positive_month_ratio: float
    validation_worst_month_pnl: float
    validation_pass_gate: int
    test_trades: int
    test_profit_factor: float
    test_total_cash_pnl: float
    test_final_balance: float
    test_positive_month_ratio: float
    test_worst_month_pnl: float
    test_max_drawdown_cash: float
    test_pass_gate: int
    monthly_stability_gate: int
    fold_transfer_pass_gate: int
    stress_transfer_pass_gate: int
    fold_pass_gate: int
    failure_reasons: str


@dataclass(frozen=True)
class FilterSplitRow:
    filter_name: str
    fold: int
    split: str
    trades: int
    candidate_events: int
    candidate_event_rate: float
    profit_factor: float
    total_cash_pnl: float
    final_balance: float
    max_drawdown_cash: float
    positive_month_ratio: float
    worst_month_pnl: float
    pass_gate: int


@dataclass(frozen=True)
class FilterStressRow:
    filter_name: str
    fold: int
    spread_mode: str
    spread_value: float
    train_profit_factor: float
    train_total_cash_pnl: float
    train_pass_gate: int
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_pass_gate: int
    test_profit_factor: float
    test_total_cash_pnl: float
    test_pass_gate: int
    transfer_pass_gate: int


@dataclass(frozen=True)
class FilterSummaryRow:
    filter_name: str
    folds: int
    fold_pass_count: int
    fold_pass_ratio: float
    train_pass_count: int
    train_pass_ratio: float
    validation_pass_count: int
    validation_pass_ratio: float
    test_pass_count: int
    test_pass_ratio: float
    aggregate_train_pnl: float
    aggregate_validation_pnl: float
    aggregate_test_pnl: float
    median_test_profit_factor: float
    mean_test_profit_factor: float
    worst_test_profit_factor: float
    worst_test_cash_pnl: float
    worst_test_max_drawdown_cash: float
    pass_gate: int
    delta_fold_pass_ratio_vs_baseline: float
    delta_test_pass_ratio_vs_baseline: float
    delta_aggregate_test_pnl_vs_baseline: float


@dataclass(frozen=True)
class Phase168Report:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    policy_key: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    bracket_id: str
    tp_atr: float
    sl_atr: float
    hold_bars: int
    spread_mode: str
    spread_value: float
    filters: list[str]
    folds: int
    selected_filter_name: str
    selected_filter_pass_gate: int
    selected_fold_pass_ratio: float
    selected_test_pass_ratio: float
    selected_aggregate_test_pnl: float
    selected_median_test_profit_factor: float
    confirmation_pass_gate: int
    recommendation: str
    filter_summary_rows: list[dict[str, Any]]
    filter_fold_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_filter_summary_csv: str
    output_filter_folds_csv: str
    output_filter_splits_csv: str
    output_trades_csv: str
    output_monthly_csv: str
    output_stress_csv: str
    production_status: str


def parse_filter_list(text: str) -> list[str]:
    raw_filters = [item.strip() for item in str(text or "").split(",") if item.strip()]
    filters = raw_filters or ["none"]
    for name in filters:
        for component in name.split("+"):
            if component.startswith("max_spread_atr_"):
                float(component.replace("max_spread_atr_", ""))
                continue
            if component not in ALLOWED_FILTER_COMPONENTS:
                raise RuntimeError(f"Unsupported predeclared filter component: {component}")
    return filters


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confirmation-only replay for predeclared 1H locked-candidate filters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--policy-key", default="BRK_D1_FAST")
    parser.add_argument("--side-mapping", default="breakout")
    parser.add_argument("--entry-delay-bars", type=int, default=1)
    parser.add_argument("--recent-window-bars", type=int, default=24)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.05)
    parser.add_argument("--top-position-threshold", type=float, default=0.85)
    parser.add_argument("--bottom-position-threshold", type=float, default=0.15)
    parser.add_argument("--exclude-both-zones", choices=("0", "1"), default="1")
    parser.add_argument("--min-range-width-atr", type=float, default=1.0)
    parser.add_argument("--max-range-width-atr", type=float, default=0.0)
    parser.add_argument("--bracket-id", default="B15_10")
    parser.add_argument("--tp-atr", type=float, default=1.5)
    parser.add_argument("--sl-atr", type=float, default=1.0)
    parser.add_argument("--hold-bars", type=int, default=24)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.2)
    parser.add_argument("--stress-spreads", default="0.2,0.5")
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--fold-train-bars", type=int, default=18000)
    parser.add_argument("--fold-validation-bars", type=int, default=4000)
    parser.add_argument("--fold-test-bars", type=int, default=4000)
    parser.add_argument("--fold-step-bars", type=int, default=4000)
    parser.add_argument("--purge-gap", type=int, default=24)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--filters", default=DEFAULT_FILTERS)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--train-min-trades", type=int, default=50)
    parser.add_argument("--train-min-profit-factor", type=float, default=1.00)
    parser.add_argument("--train-min-final-balance", type=float, default=100.0)
    parser.add_argument("--validation-min-trades", type=int, default=20)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.10)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=20)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.10)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--max-validation-event-rate", type=float, default=0.35)
    parser.add_argument("--max-test-event-rate", type=float, default=0.35)
    parser.add_argument("--min-positive-month-ratio", type=float, default=0.50)
    parser.add_argument("--max-worst-month-loss", type=float, default=12.0)
    parser.add_argument("--min-folds", type=int, default=5)
    parser.add_argument("--min-fold-pass-ratio", type=float, default=0.55)
    parser.add_argument("--min-test-pass-ratio", type=float, default=0.60)
    parser.add_argument("--min-median-test-profit-factor", type=float, default=1.05)
    parser.add_argument("--min-aggregate-test-cash-pnl", type=float, default=0.0)
    parser.add_argument("--max-worst-test-drawdown", type=float, default=25.0)
    parser.add_argument("--require-stress-pass", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase168A 1H predeclared filter confirmation replay")
    return parser.parse_args(argv)


def spread_to_atr_for_indices(frame: Any, indices: np.ndarray, atr: np.ndarray, args: argparse.Namespace, spread_value: float) -> np.ndarray:
    idx = np.asarray(indices, dtype=np.int64)
    if len(idx) == 0:
        return np.asarray([], dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    if str(args.spread_mode) == "pct":
        spread = close[idx] * float(spread_value) / 100.0
    else:
        spread = np.full(len(idx), float(spread_value), dtype=np.float64)
    return spread / np.maximum(atr[idx], 1e-9)


def apply_predeclared_filter(
    name: str,
    indices: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    frame: Any,
    atr: np.ndarray,
    thresholds: Mapping[str, float],
    args: argparse.Namespace,
    spread_value: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = np.asarray(indices, dtype=np.int64)
    top = top_mask.copy()
    bottom = bottom_mask.copy()
    effective_spread = float(args.spread_value if spread_value is None else spread_value)
    for component in str(name).split("+"):
        part = component.strip()
        if not part or part == "none":
            continue
        if part == "buy_leg_only":
            bottom[:] = False
            continue
        if part == "sell_leg_only":
            top[:] = False
            continue
        if part == "min_atr_q50":
            idx = idx[atr[idx] >= float(thresholds["q50"])]
            continue
        if part == "min_atr_q75":
            idx = idx[atr[idx] >= float(thresholds["q75"])]
            continue
        if part.startswith("max_spread_atr_"):
            threshold = float(part.replace("max_spread_atr_", ""))
            spread_atr = spread_to_atr_for_indices(frame, idx, atr, args, effective_spread)
            idx = idx[spread_atr <= threshold]
            continue
        raise RuntimeError(f"Unsupported predeclared filter component: {part}")
    return idx, top, bottom


def fold_monthly_gate(train: LockdownSplitSummary, validation: LockdownSplitSummary, test: LockdownSplitSummary, args: argparse.Namespace) -> int:
    return int(
        train.positive_month_ratio >= float(args.min_positive_month_ratio)
        and validation.positive_month_ratio >= float(args.min_positive_month_ratio)
        and test.positive_month_ratio >= float(args.min_positive_month_ratio)
        and train.worst_month_pnl >= -float(args.max_worst_month_loss)
        and validation.worst_month_pnl >= -float(args.max_worst_month_loss)
        and test.worst_month_pnl >= -float(args.max_worst_month_loss)
    )


def fold_failure_reasons(row: FilterFoldRow) -> list[str]:
    reasons: list[str] = []
    if not row.train_pass_gate:
        reasons.append("train_gate_failed")
    if not row.validation_pass_gate:
        reasons.append("validation_gate_failed")
    if not row.test_pass_gate:
        reasons.append("test_gate_failed")
    if not row.monthly_stability_gate:
        reasons.append("monthly_stability_failed")
    if not row.stress_transfer_pass_gate:
        reasons.append("stress_transfer_failed")
    return reasons or ["none"]


def replay_filter_fold(
    filter_name: str,
    spec: WalkForwardFoldSpec,
    frame: Any,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    atr: np.ndarray,
    thresholds: Mapping[str, float],
    args: argparse.Namespace,
) -> tuple[FilterFoldRow, list[FilterSplitRow], list[dict[str, Any]], list[dict[str, Any]], list[FilterStressRow]]:
    split_ranges = {
        "train": np.arange(spec.train_start, spec.train_end, dtype=np.int64),
        "validation": np.arange(spec.validation_start, spec.validation_end, dtype=np.int64),
        "test": np.arange(spec.test_start, spec.test_end, dtype=np.int64),
    }
    summaries: dict[str, LockdownSplitSummary] = {}
    split_rows: list[FilterSplitRow] = []
    trade_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    for split, raw_indices in split_ranges.items():
        indices, filtered_top, filtered_bottom = apply_predeclared_filter(
            filter_name,
            raw_indices,
            top_mask,
            bottom_mask,
            frame,
            atr,
            thresholds,
            args,
            float(args.spread_value),
        )
        summary, trades, months = simulate_locked_split(split, frame, indices, filtered_top, filtered_bottom, atr, args, float(args.spread_value), collect_trades=True)
        summaries[split] = summary
        split_rows.append(
            FilterSplitRow(
                filter_name=filter_name,
                fold=spec.fold,
                split=split,
                trades=int(summary.trades),
                candidate_events=int(summary.candidate_events),
                candidate_event_rate=float(summary.candidate_event_rate),
                profit_factor=float(summary.profit_factor),
                total_cash_pnl=float(summary.total_cash_pnl),
                final_balance=float(summary.final_balance),
                max_drawdown_cash=float(summary.max_drawdown_cash),
                positive_month_ratio=float(summary.positive_month_ratio),
                worst_month_pnl=float(summary.worst_month_pnl),
                pass_gate=int(summary.pass_gate),
            )
        )
        for trade in trades:
            trade_rows.append({"filter_name": filter_name, "fold": spec.fold, **asdict(trade)})
        for month in months:
            monthly_rows.append({"filter_name": filter_name, "fold": spec.fold, **month})
    train = summaries["train"]
    validation = summaries["validation"]
    test = summaries["test"]
    monthly_gate = fold_monthly_gate(train, validation, test, args)
    transfer_gate = int(train.pass_gate and validation.pass_gate and test.pass_gate)
    stress_rows: list[FilterStressRow] = []
    for spread in parse_float_grid(args.stress_spreads, (float(args.spread_value),)):
        stress_summaries: dict[str, LockdownSplitSummary] = {}
        for split, raw_indices in split_ranges.items():
            indices, filtered_top, filtered_bottom = apply_predeclared_filter(
                filter_name,
                raw_indices,
                top_mask,
                bottom_mask,
                frame,
                atr,
                thresholds,
                args,
                float(spread),
            )
            stress_summary, _trades, _months = simulate_locked_split(split, frame, indices, filtered_top, filtered_bottom, atr, args, float(spread), collect_trades=True)
            stress_summaries[split] = stress_summary
        stress_train = stress_summaries["train"]
        stress_validation = stress_summaries["validation"]
        stress_test = stress_summaries["test"]
        stress_rows.append(
            FilterStressRow(
                filter_name=filter_name,
                fold=spec.fold,
                spread_mode=str(args.spread_mode),
                spread_value=float(spread),
                train_profit_factor=float(stress_train.profit_factor),
                train_total_cash_pnl=float(stress_train.total_cash_pnl),
                train_pass_gate=int(stress_train.pass_gate),
                validation_profit_factor=float(stress_validation.profit_factor),
                validation_total_cash_pnl=float(stress_validation.total_cash_pnl),
                validation_pass_gate=int(stress_validation.pass_gate),
                test_profit_factor=float(stress_test.profit_factor),
                test_total_cash_pnl=float(stress_test.total_cash_pnl),
                test_pass_gate=int(stress_test.pass_gate),
                transfer_pass_gate=int(stress_train.pass_gate and stress_validation.pass_gate and stress_test.pass_gate),
            )
        )
    stress_gate = int(any(row.transfer_pass_gate for row in stress_rows)) if str(args.require_stress_pass) == "1" else 1
    partial = FilterFoldRow(
        filter_name=filter_name,
        fold=spec.fold,
        train_trades=int(train.trades),
        train_profit_factor=float(train.profit_factor),
        train_total_cash_pnl=float(train.total_cash_pnl),
        train_final_balance=float(train.final_balance),
        train_positive_month_ratio=float(train.positive_month_ratio),
        train_worst_month_pnl=float(train.worst_month_pnl),
        train_pass_gate=int(train.pass_gate),
        validation_trades=int(validation.trades),
        validation_profit_factor=float(validation.profit_factor),
        validation_total_cash_pnl=float(validation.total_cash_pnl),
        validation_final_balance=float(validation.final_balance),
        validation_positive_month_ratio=float(validation.positive_month_ratio),
        validation_worst_month_pnl=float(validation.worst_month_pnl),
        validation_pass_gate=int(validation.pass_gate),
        test_trades=int(test.trades),
        test_profit_factor=float(test.profit_factor),
        test_total_cash_pnl=float(test.total_cash_pnl),
        test_final_balance=float(test.final_balance),
        test_positive_month_ratio=float(test.positive_month_ratio),
        test_worst_month_pnl=float(test.worst_month_pnl),
        test_max_drawdown_cash=float(test.max_drawdown_cash),
        test_pass_gate=int(test.pass_gate),
        monthly_stability_gate=int(monthly_gate),
        fold_transfer_pass_gate=int(transfer_gate),
        stress_transfer_pass_gate=int(any(row.transfer_pass_gate for row in stress_rows)),
        fold_pass_gate=int(transfer_gate and monthly_gate and stress_gate),
        failure_reasons="[]",
    )
    return FilterFoldRow(**{**asdict(partial), "failure_reasons": json.dumps(fold_failure_reasons(partial), ensure_ascii=False)}), split_rows, trade_rows, monthly_rows, stress_rows


def summarize_filter(filter_name: str, fold_rows: Sequence[FilterFoldRow], baseline: FilterSummaryRow | None, args: argparse.Namespace) -> FilterSummaryRow:
    folds = len(fold_rows)
    test_pfs = np.asarray([row.test_profit_factor for row in fold_rows], dtype=np.float64)
    test_pnls = np.asarray([row.test_total_cash_pnl for row in fold_rows], dtype=np.float64)
    test_dds = np.asarray([row.test_max_drawdown_cash for row in fold_rows], dtype=np.float64)
    fold_pass_count = int(sum(row.fold_pass_gate for row in fold_rows))
    test_pass_count = int(sum(row.test_pass_gate for row in fold_rows))
    train_pass_count = int(sum(row.train_pass_gate for row in fold_rows))
    validation_pass_count = int(sum(row.validation_pass_gate for row in fold_rows))
    fold_pass_ratio = float(fold_pass_count / folds) if folds else 0.0
    test_pass_ratio = float(test_pass_count / folds) if folds else 0.0
    aggregate_test_pnl = float(np.sum(test_pnls)) if len(test_pnls) else 0.0
    median_test_pf = float(np.median(test_pfs)) if len(test_pfs) else 0.0
    worst_test_pf = float(np.min(test_pfs)) if len(test_pfs) else 0.0
    worst_test_pnl = float(np.min(test_pnls)) if len(test_pnls) else 0.0
    worst_dd = float(np.max(test_dds)) if len(test_dds) else 0.0
    pass_gate = int(
        folds >= int(args.min_folds)
        and fold_pass_ratio >= float(args.min_fold_pass_ratio)
        and test_pass_ratio >= float(args.min_test_pass_ratio)
        and aggregate_test_pnl > float(args.min_aggregate_test_cash_pnl)
        and median_test_pf >= float(args.min_median_test_profit_factor)
        and worst_dd <= float(args.max_worst_test_drawdown)
    )
    baseline_fold = baseline.fold_pass_ratio if baseline else fold_pass_ratio
    baseline_test = baseline.test_pass_ratio if baseline else test_pass_ratio
    baseline_pnl = baseline.aggregate_test_pnl if baseline else aggregate_test_pnl
    return FilterSummaryRow(
        filter_name=filter_name,
        folds=folds,
        fold_pass_count=fold_pass_count,
        fold_pass_ratio=fold_pass_ratio,
        train_pass_count=train_pass_count,
        train_pass_ratio=float(train_pass_count / folds) if folds else 0.0,
        validation_pass_count=validation_pass_count,
        validation_pass_ratio=float(validation_pass_count / folds) if folds else 0.0,
        test_pass_count=test_pass_count,
        test_pass_ratio=test_pass_ratio,
        aggregate_train_pnl=float(sum(row.train_total_cash_pnl for row in fold_rows)),
        aggregate_validation_pnl=float(sum(row.validation_total_cash_pnl for row in fold_rows)),
        aggregate_test_pnl=aggregate_test_pnl,
        median_test_profit_factor=median_test_pf,
        mean_test_profit_factor=float(np.mean(test_pfs)) if len(test_pfs) else 0.0,
        worst_test_profit_factor=worst_test_pf,
        worst_test_cash_pnl=worst_test_pnl,
        worst_test_max_drawdown_cash=worst_dd,
        pass_gate=pass_gate,
        delta_fold_pass_ratio_vs_baseline=float(fold_pass_ratio - baseline_fold),
        delta_test_pass_ratio_vs_baseline=float(test_pass_ratio - baseline_test),
        delta_aggregate_test_pnl_vs_baseline=float(aggregate_test_pnl - baseline_pnl),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase168Report) -> str:
    summary_rows = "".join(
        f"<tr><td>{html.escape(str(row['filter_name']))}</td>"
        f"<td>{int(row['fold_pass_count'])}/{int(row['folds'])}</td>"
        f"<td>{float(row['fold_pass_ratio']):.2f}</td>"
        f"<td>{int(row['test_pass_count'])}/{int(row['folds'])}</td>"
        f"<td>{float(row['aggregate_test_pnl']):.3f}</td>"
        f"<td>{float(row['median_test_profit_factor']):.3f}</td>"
        f"<td>{int(row['pass_gate'])}</td></tr>"
        for row in report.filter_summary_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase168A predeclared filter confirmation replay. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'confirmation_pass_gate': report.confirmation_pass_gate,
        'selected_filter_name': report.selected_filter_name,
        'selected_filter_pass_gate': report.selected_filter_pass_gate,
        'selected_fold_pass_ratio': report.selected_fold_pass_ratio,
        'selected_test_pass_ratio': report.selected_test_pass_ratio,
        'recommendation': report.recommendation,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Filter summaries</h2><table><thead><tr><th>Filter</th><th>Fold pass</th><th>Fold ratio</th><th>Test pass</th><th>Test PnL</th><th>Median PF</th><th>Pass</th></tr></thead><tbody>{summary_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE168A 1H PREDECLARED FILTER CONFIRMATION REPLAY")
        print("=" * 74)
        filters = parse_filter_list(args.filters)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        top_mask, bottom_mask, _ = build_zone_masks(
            frame,
            atr,
            int(args.recent_window_bars),
            float(args.pivot_zone_atr),
            float(args.top_position_threshold),
            float(args.bottom_position_threshold),
            int(args.exclude_both_zones),
            float(args.min_range_width_atr),
            float(args.max_range_width_atr),
        )
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
            raise RuntimeError("No walk-forward folds could be built with the requested sizes")
        thresholds_by_fold: dict[int, dict[str, float]] = {}
        for spec in specs:
            train_atr = atr[np.arange(spec.train_start, spec.train_end, dtype=np.int64)]
            q25, q50, q75 = np.quantile(train_atr[np.isfinite(train_atr)], [0.25, 0.50, 0.75])
            thresholds_by_fold[spec.fold] = {"q25": float(q25), "q50": float(q50), "q75": float(q75)}
        all_fold_rows: list[FilterFoldRow] = []
        all_split_rows: list[FilterSplitRow] = []
        all_trade_rows: list[dict[str, Any]] = []
        all_monthly_rows: list[dict[str, Any]] = []
        all_stress_rows: list[FilterStressRow] = []
        rows_by_filter: dict[str, list[FilterFoldRow]] = {}
        for filter_name in filters:
            rows_by_filter[filter_name] = []
            for spec in specs:
                fold_row, split_rows, trade_rows, monthly_rows, stress_rows = replay_filter_fold(
                    filter_name,
                    spec,
                    frame,
                    top_mask,
                    bottom_mask,
                    atr,
                    thresholds_by_fold[spec.fold],
                    args,
                )
                rows_by_filter[filter_name].append(fold_row)
                all_fold_rows.append(fold_row)
                all_split_rows.extend(split_rows)
                all_trade_rows.extend(trade_rows)
                all_monthly_rows.extend(monthly_rows)
                all_stress_rows.extend(stress_rows)
        baseline_summary = summarize_filter("none", rows_by_filter.get("none", []), None, args) if "none" in rows_by_filter else None
        summaries = [summarize_filter(name, rows_by_filter[name], baseline_summary, args) for name in filters]
        summaries = sorted(summaries, key=lambda row: (row.pass_gate, row.fold_pass_ratio, row.test_pass_ratio, row.aggregate_test_pnl, row.median_test_profit_factor), reverse=True)
        selected = summaries[0] if summaries else None
        confirmation_pass = int(any(row.pass_gate for row in summaries))
        if confirmation_pass:
            recommendation = "FILTER_CONFIRMED_BUT_STILL_NO_PAPER_NO_LIVE"
        else:
            recommendation = "STOP_1H_LOCKED_FILTER_ROUTE_OR_REDESIGN"
        summary_csv = output_dir / "latest_filter_summary.csv"
        folds_csv = output_dir / "latest_filter_folds.csv"
        splits_csv = output_dir / "latest_filter_splits.csv"
        trades_csv = output_dir / "latest_trades.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        stress_csv = output_dir / "latest_stress.csv"
        write_csv(summary_csv, [asdict(row) for row in summaries])
        write_csv(folds_csv, [asdict(row) for row in all_fold_rows])
        write_csv(splits_csv, [asdict(row) for row in all_split_rows])
        write_csv(trades_csv, all_trade_rows)
        write_csv(monthly_csv, all_monthly_rows)
        write_csv(stress_csv, [asdict(row) for row in all_stress_rows])
        report = Phase168Report(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            policy_key=str(args.policy_key),
            side_mapping=str(args.side_mapping),
            entry_delay_bars=int(args.entry_delay_bars),
            recent_window_bars=int(args.recent_window_bars),
            pivot_zone_atr=float(args.pivot_zone_atr),
            top_position_threshold=float(args.top_position_threshold),
            bottom_position_threshold=float(args.bottom_position_threshold),
            exclude_both_zones=int(args.exclude_both_zones),
            min_range_width_atr=float(args.min_range_width_atr),
            max_range_width_atr=float(args.max_range_width_atr),
            bracket_id=str(args.bracket_id),
            tp_atr=float(args.tp_atr),
            sl_atr=float(args.sl_atr),
            hold_bars=int(args.hold_bars),
            spread_mode=str(args.spread_mode),
            spread_value=float(args.spread_value),
            filters=filters,
            folds=len(specs),
            selected_filter_name=str(selected.filter_name) if selected else "",
            selected_filter_pass_gate=int(selected.pass_gate) if selected else 0,
            selected_fold_pass_ratio=float(selected.fold_pass_ratio) if selected else 0.0,
            selected_test_pass_ratio=float(selected.test_pass_ratio) if selected else 0.0,
            selected_aggregate_test_pnl=float(selected.aggregate_test_pnl) if selected else 0.0,
            selected_median_test_profit_factor=float(selected.median_test_profit_factor) if selected else 0.0,
            confirmation_pass_gate=int(confirmation_pass),
            recommendation=recommendation,
            filter_summary_rows=[asdict(row) for row in summaries],
            filter_fold_rows=[asdict(row) for row in all_fold_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_filter_summary_csv=str(summary_csv),
            output_filter_folds_csv=str(folds_csv),
            output_filter_splits_csv=str(splits_csv),
            output_trades_csv=str(trades_csv),
            output_monthly_csv=str(monthly_csv),
            output_stress_csv=str(stress_csv),
            production_status="BLOCKED — Phase168A predeclared filter confirmation only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase168A predeclared filter confirmation complete")
        print(f"  filters       : {', '.join(filters)}")
        print(f"  selected      : {report.selected_filter_name or 'none'}")
        print(f"  fold ratio    : {report.selected_fold_pass_ratio:.2%}")
        print(f"  test ratio    : {report.selected_test_pass_ratio:.2%}")
        print(f"  confirm pass  : {report.confirmation_pass_gate}")
        print(f"  recommendation: {report.recommendation}")
        print(f"  output        : {report.output_json}")
        print(f"  elapsed       : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
