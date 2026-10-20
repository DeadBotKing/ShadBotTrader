"""Phase166A: 1H locked candidate walk-forward / anti-overfit replay.

Phase165A locked one nonzero-cost 1H breakout candidate and passed a static
train/validation/test diagnostic. This phase keeps the exact same candidate and
runs rolling chronological folds to check whether the edge is stable across time
rather than an artifact of one static split.

No grid search, no model training, no paper/live/production approval.
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
from replay_pivot_1h_fixed_spread_candidate_lockdown import (  # noqa: E402
    Locked1HTrade,
    LockdownSplitSummary,
    simulate_locked_split,
)

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_locked_candidate_walk_forward")


@dataclass(frozen=True)
class WalkForwardFoldSpec:
    fold: int
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int
    train_rows: int
    validation_rows: int
    test_rows: int


@dataclass(frozen=True)
class WalkForwardFoldRow:
    fold: int
    train_start_timestamp: str
    train_end_timestamp: str
    validation_start_timestamp: str
    validation_end_timestamp: str
    test_start_timestamp: str
    test_end_timestamp: str
    train_rows: int
    validation_rows: int
    test_rows: int
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    train_final_balance: float
    train_max_drawdown_cash: float
    train_positive_month_ratio: float
    train_worst_month_pnl: float
    train_pass_gate: int
    validation_trades: int
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_final_balance: float
    validation_max_drawdown_cash: float
    validation_positive_month_ratio: float
    validation_worst_month_pnl: float
    validation_pass_gate: int
    test_trades: int
    test_profit_factor: float
    test_total_cash_pnl: float
    test_final_balance: float
    test_max_drawdown_cash: float
    test_positive_month_ratio: float
    test_worst_month_pnl: float
    test_pass_gate: int
    monthly_stability_gate: int
    fold_transfer_pass_gate: int
    stress_transfer_pass_gate: int
    fold_pass_gate: int


@dataclass(frozen=True)
class WalkForwardStressRow:
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
class Phase166Report:
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
    fold_train_bars: int
    fold_validation_bars: int
    fold_test_bars: int
    fold_step_bars: int
    purge_gap: int
    folds: int
    fold_pass_count: int
    fold_pass_ratio: float
    test_pass_count: int
    test_pass_ratio: float
    aggregate_test_trades: int
    aggregate_test_cash_pnl: float
    median_test_profit_factor: float
    mean_test_profit_factor: float
    worst_test_profit_factor: float
    worst_test_cash_pnl: float
    worst_test_max_drawdown_cash: float
    walk_forward_pass_gate: int
    fold_rows: list[dict[str, Any]]
    stress_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_folds_csv: str
    output_fold_splits_csv: str
    output_trades_csv: str
    output_monthly_csv: str
    output_stress_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Walk-forward replay for the locked 1H fixed-spread pivot candidate.",
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
    parser.add_argument("--report-title", default="Phase166A 1H locked candidate walk-forward replay")
    return parser.parse_args(argv)


def build_fold_specs(total_rows: int, train_bars: int, validation_bars: int, test_bars: int, step_bars: int, purge_gap: int, max_folds: int = 0) -> list[WalkForwardFoldSpec]:
    train_bars = max(int(train_bars), 1)
    validation_bars = max(int(validation_bars), 1)
    test_bars = max(int(test_bars), 1)
    step_bars = max(int(step_bars), 1)
    purge_gap = max(int(purge_gap), 0)
    specs: list[WalkForwardFoldSpec] = []
    start = 0
    fold = 1
    while True:
        train_start = start
        train_end = train_start + train_bars
        validation_start = train_end + purge_gap
        validation_end = validation_start + validation_bars
        test_start = validation_end + purge_gap
        test_end = test_start + test_bars
        if test_end > total_rows:
            break
        specs.append(
            WalkForwardFoldSpec(
                fold=fold,
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
                train_rows=train_end - train_start,
                validation_rows=validation_end - validation_start,
                test_rows=test_end - test_start,
            )
        )
        if int(max_folds) > 0 and len(specs) >= int(max_folds):
            break
        start += step_bars
        fold += 1
    return specs


def idx_range(start: int, end: int) -> np.ndarray:
    return np.arange(int(start), int(end), dtype=np.int64)


def ts(frame: Any, row: int) -> str:
    if row < 0 or row >= len(frame):
        return ""
    return str(frame.at[int(row), "timestamp"])


def fold_monthly_gate(train: LockdownSplitSummary, validation: LockdownSplitSummary, test: LockdownSplitSummary, args: argparse.Namespace) -> int:
    return int(
        train.positive_month_ratio >= float(args.min_positive_month_ratio)
        and validation.positive_month_ratio >= float(args.min_positive_month_ratio)
        and test.positive_month_ratio >= float(args.min_positive_month_ratio)
        and train.worst_month_pnl >= -float(args.max_worst_month_loss)
        and validation.worst_month_pnl >= -float(args.max_worst_month_loss)
        and test.worst_month_pnl >= -float(args.max_worst_month_loss)
    )


def replay_fold(
    spec: WalkForwardFoldSpec,
    frame: Any,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    atr: np.ndarray,
    args: argparse.Namespace,
) -> tuple[WalkForwardFoldRow, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[WalkForwardStressRow]]:
    split_indices = {
        "train": idx_range(spec.train_start, spec.train_end),
        "validation": idx_range(spec.validation_start, spec.validation_end),
        "test": idx_range(spec.test_start, spec.test_end),
    }
    summaries: dict[str, LockdownSplitSummary] = {}
    all_trade_rows: list[dict[str, Any]] = []
    all_monthly_rows: list[dict[str, Any]] = []
    split_summary_rows: list[dict[str, Any]] = []
    for split, indices in split_indices.items():
        summary, trades, monthly_rows = simulate_locked_split(
            split,
            frame,
            indices,
            top_mask,
            bottom_mask,
            atr,
            args,
            float(args.spread_value),
            collect_trades=True,
        )
        summaries[split] = summary
        summary_row = {"fold": spec.fold, **asdict(summary)}
        split_summary_rows.append(summary_row)
        for trade in trades:
            all_trade_rows.append({"fold": spec.fold, **asdict(trade)})
        for row in monthly_rows:
            all_monthly_rows.append({"fold": spec.fold, **row})
    train = summaries["train"]
    validation = summaries["validation"]
    test = summaries["test"]
    monthly_gate = fold_monthly_gate(train, validation, test, args)
    transfer_gate = int(train.pass_gate and validation.pass_gate and test.pass_gate)
    stress_rows: list[WalkForwardStressRow] = []
    for spread in parse_float_grid(args.stress_spreads, (float(args.spread_value),)):
        stress_summaries: dict[str, LockdownSplitSummary] = {}
        for split, indices in split_indices.items():
            stress_summary, _trades, _monthly = simulate_locked_split(
                split,
                frame,
                indices,
                top_mask,
                bottom_mask,
                atr,
                args,
                float(spread),
                collect_trades=True,
            )
            stress_summaries[split] = stress_summary
        stress_train = stress_summaries["train"]
        stress_validation = stress_summaries["validation"]
        stress_test = stress_summaries["test"]
        stress_rows.append(
            WalkForwardStressRow(
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
    fold_pass = int(transfer_gate and monthly_gate and stress_gate)
    fold_row = WalkForwardFoldRow(
        fold=spec.fold,
        train_start_timestamp=ts(frame, spec.train_start),
        train_end_timestamp=ts(frame, spec.train_end - 1),
        validation_start_timestamp=ts(frame, spec.validation_start),
        validation_end_timestamp=ts(frame, spec.validation_end - 1),
        test_start_timestamp=ts(frame, spec.test_start),
        test_end_timestamp=ts(frame, spec.test_end - 1),
        train_rows=spec.train_rows,
        validation_rows=spec.validation_rows,
        test_rows=spec.test_rows,
        train_trades=int(train.trades),
        train_profit_factor=float(train.profit_factor),
        train_total_cash_pnl=float(train.total_cash_pnl),
        train_final_balance=float(train.final_balance),
        train_max_drawdown_cash=float(train.max_drawdown_cash),
        train_positive_month_ratio=float(train.positive_month_ratio),
        train_worst_month_pnl=float(train.worst_month_pnl),
        train_pass_gate=int(train.pass_gate),
        validation_trades=int(validation.trades),
        validation_profit_factor=float(validation.profit_factor),
        validation_total_cash_pnl=float(validation.total_cash_pnl),
        validation_final_balance=float(validation.final_balance),
        validation_max_drawdown_cash=float(validation.max_drawdown_cash),
        validation_positive_month_ratio=float(validation.positive_month_ratio),
        validation_worst_month_pnl=float(validation.worst_month_pnl),
        validation_pass_gate=int(validation.pass_gate),
        test_trades=int(test.trades),
        test_profit_factor=float(test.profit_factor),
        test_total_cash_pnl=float(test.total_cash_pnl),
        test_final_balance=float(test.final_balance),
        test_max_drawdown_cash=float(test.max_drawdown_cash),
        test_positive_month_ratio=float(test.positive_month_ratio),
        test_worst_month_pnl=float(test.worst_month_pnl),
        test_pass_gate=int(test.pass_gate),
        monthly_stability_gate=int(monthly_gate),
        fold_transfer_pass_gate=int(transfer_gate),
        stress_transfer_pass_gate=int(any(row.transfer_pass_gate for row in stress_rows)),
        fold_pass_gate=int(fold_pass),
    )
    return fold_row, split_summary_rows, all_trade_rows, all_monthly_rows, stress_rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase166Report) -> str:
    fold_rows = "".join(
        f"<tr><td>{int(row['fold'])}</td>"
        f"<td>{float(row['train_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['test_max_drawdown_cash']):.3f}</td>"
        f"<td>{int(row['fold_pass_gate'])}</td></tr>"
        for row in report.fold_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase166A locked 1H candidate walk-forward anti-overfit replay. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'walk_forward_pass_gate': report.walk_forward_pass_gate,
        'folds': report.folds,
        'fold_pass_count': report.fold_pass_count,
        'fold_pass_ratio': report.fold_pass_ratio,
        'test_pass_ratio': report.test_pass_ratio,
        'aggregate_test_cash_pnl': report.aggregate_test_cash_pnl,
        'median_test_profit_factor': report.median_test_profit_factor,
        'worst_test_max_drawdown_cash': report.worst_test_max_drawdown_cash,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Fold rows</h2><table><thead><tr><th>Fold</th><th>Train PF</th><th>Val PF</th><th>Test PF</th><th>Test PnL</th><th>Test DD</th><th>Pass</th></tr></thead><tbody>{fold_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE166A 1H LOCKED CANDIDATE WALK-FORWARD REPLAY")
        print("=" * 74)
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
        fold_rows: list[WalkForwardFoldRow] = []
        split_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        monthly_rows: list[dict[str, Any]] = []
        stress_rows: list[WalkForwardStressRow] = []
        for spec in specs:
            fold_row, split_summary, trades, months, stress = replay_fold(spec, frame, top_mask, bottom_mask, atr, args)
            fold_rows.append(fold_row)
            split_rows.extend(split_summary)
            trade_rows.extend(trades)
            monthly_rows.extend(months)
            stress_rows.extend(stress)
        test_pfs = np.asarray([row.test_profit_factor for row in fold_rows], dtype=np.float64)
        test_pnls = np.asarray([row.test_total_cash_pnl for row in fold_rows], dtype=np.float64)
        test_dds = np.asarray([row.test_max_drawdown_cash for row in fold_rows], dtype=np.float64)
        pass_count = int(sum(row.fold_pass_gate for row in fold_rows))
        test_pass_count = int(sum(row.test_pass_gate for row in fold_rows))
        fold_count = len(fold_rows)
        fold_pass_ratio = float(pass_count / fold_count) if fold_count else 0.0
        test_pass_ratio = float(test_pass_count / fold_count) if fold_count else 0.0
        aggregate_test_pnl = float(np.sum(test_pnls)) if len(test_pnls) else 0.0
        median_test_pf = float(np.median(test_pfs)) if len(test_pfs) else 0.0
        mean_test_pf = float(np.mean(test_pfs)) if len(test_pfs) else 0.0
        worst_test_pf = float(np.min(test_pfs)) if len(test_pfs) else 0.0
        worst_test_pnl = float(np.min(test_pnls)) if len(test_pnls) else 0.0
        worst_test_dd = float(np.max(test_dds)) if len(test_dds) else 0.0
        walk_pass = int(
            fold_count >= int(args.min_folds)
            and fold_pass_ratio >= float(args.min_fold_pass_ratio)
            and test_pass_ratio >= float(args.min_test_pass_ratio)
            and aggregate_test_pnl > float(args.min_aggregate_test_cash_pnl)
            and median_test_pf >= float(args.min_median_test_profit_factor)
            and worst_test_dd <= float(args.max_worst_test_drawdown)
        )
        folds_csv = output_dir / "latest_folds.csv"
        split_csv = output_dir / "latest_fold_splits.csv"
        trades_csv = output_dir / "latest_trades.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        stress_csv = output_dir / "latest_stress.csv"
        write_csv(folds_csv, [asdict(row) for row in fold_rows])
        write_csv(split_csv, split_rows)
        write_csv(trades_csv, trade_rows)
        write_csv(monthly_csv, monthly_rows)
        write_csv(stress_csv, [asdict(row) for row in stress_rows])
        report = Phase166Report(
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
            fold_train_bars=int(args.fold_train_bars),
            fold_validation_bars=int(args.fold_validation_bars),
            fold_test_bars=int(args.fold_test_bars),
            fold_step_bars=int(args.fold_step_bars),
            purge_gap=int(args.purge_gap),
            folds=fold_count,
            fold_pass_count=pass_count,
            fold_pass_ratio=fold_pass_ratio,
            test_pass_count=test_pass_count,
            test_pass_ratio=test_pass_ratio,
            aggregate_test_trades=int(sum(row.test_trades for row in fold_rows)),
            aggregate_test_cash_pnl=aggregate_test_pnl,
            median_test_profit_factor=median_test_pf,
            mean_test_profit_factor=mean_test_pf,
            worst_test_profit_factor=worst_test_pf,
            worst_test_cash_pnl=worst_test_pnl,
            worst_test_max_drawdown_cash=worst_test_dd,
            walk_forward_pass_gate=int(walk_pass),
            fold_rows=[asdict(row) for row in fold_rows],
            stress_rows=[asdict(row) for row in stress_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_folds_csv=str(folds_csv),
            output_fold_splits_csv=str(split_csv),
            output_trades_csv=str(trades_csv),
            output_monthly_csv=str(monthly_csv),
            output_stress_csv=str(stress_csv),
            production_status="BLOCKED — Phase166A walk-forward diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase166A walk-forward replay complete")
        print(f"  folds          : {report.folds}")
        print(f"  fold pass      : {report.fold_pass_count}/{report.folds} ({report.fold_pass_ratio:.2%})")
        print(f"  test pass      : {report.test_pass_count}/{report.folds} ({report.test_pass_ratio:.2%})")
        print(f"  aggregate test : {report.aggregate_test_cash_pnl:.4f}")
        print(f"  median test PF : {report.median_test_profit_factor:.4f}")
        print(f"  WF pass        : {report.walk_forward_pass_gate}")
        print(f"  output         : {report.output_json}")
        print(f"  elapsed        : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
