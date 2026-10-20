"""Phase167A: 1H locked candidate regime / failure attribution audit.

Phase166A failed the full walk-forward anti-overfit gate, even though 4/6 test
folds passed and aggregate test PnL was positive. This phase keeps the exact
locked 1H candidate and attributes the failures by regime, side, calendar time,
and pre-declared diagnostic filters.

No grid-search selection, no model training, no paper/live/production approval.
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
from replay_pivot_1h_locked_candidate_walk_forward import WalkForwardFoldSpec, build_fold_specs, replay_fold  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_locked_candidate_regime_failures")


@dataclass(frozen=True)
class RegimeAggregationRow:
    group: str
    fold: int
    split: str
    bucket: str
    side: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    total_cash_pnl: float
    profit_factor: float
    avg_cash_pnl: float
    avg_atr_score: float
    take_profits: int
    stop_losses: int
    timeouts: int


@dataclass(frozen=True)
class FoldFailureRow:
    fold: int
    train_pass_gate: int
    validation_pass_gate: int
    test_pass_gate: int
    monthly_stability_gate: int
    fold_transfer_pass_gate: int
    fold_pass_gate: int
    failure_reasons: str
    train_profit_factor: float
    train_total_cash_pnl: float
    train_positive_month_ratio: float
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_positive_month_ratio: float
    test_profit_factor: float
    test_total_cash_pnl: float
    test_positive_month_ratio: float
    worst_side: str
    worst_side_pnl: float
    worst_atr_regime: str
    worst_atr_regime_pnl: float
    worst_month: str
    worst_month_pnl: float


@dataclass(frozen=True)
class FilterDiagnosticRow:
    filter_name: str
    fold: int
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    train_pass_gate: int
    validation_trades: int
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_pass_gate: int
    test_trades: int
    test_profit_factor: float
    test_total_cash_pnl: float
    test_pass_gate: int
    monthly_stability_gate: int
    fold_transfer_pass_gate: int
    fold_pass_gate: int


@dataclass(frozen=True)
class FilterSummaryRow:
    filter_name: str
    folds: int
    fold_pass_count: int
    fold_pass_ratio: float
    test_pass_count: int
    test_pass_ratio: float
    aggregate_test_pnl: float
    median_test_profit_factor: float
    worst_test_profit_factor: float
    worst_test_pnl: float


@dataclass(frozen=True)
class Phase167Report:
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
    folds: int
    baseline_fold_pass_count: int
    baseline_test_pass_count: int
    baseline_aggregate_test_pnl: float
    dominant_failure_reason: str
    worst_side: str
    worst_side_total_pnl: float
    worst_atr_regime: str
    worst_atr_regime_total_pnl: float
    best_filter_name: str
    best_filter_fold_pass_ratio: float
    best_filter_test_pass_ratio: float
    best_filter_aggregate_test_pnl: float
    recommendation: str
    fold_failure_rows: list[dict[str, Any]]
    side_summary_rows: list[dict[str, Any]]
    atr_regime_rows: list[dict[str, Any]]
    spread_atr_regime_rows: list[dict[str, Any]]
    monthly_summary_rows: list[dict[str, Any]]
    filter_summary_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_fold_failures_csv: str
    output_regime_summary_csv: str
    output_side_summary_csv: str
    output_monthly_summary_csv: str
    output_filter_diagnostics_csv: str
    output_filter_summary_csv: str
    output_trades_csv: str
    production_status: str


def parse_text_list(text: str, default: Sequence[str]) -> list[str]:
    raw = str(text or "").strip()
    if not raw:
        return [str(value) for value in default]
    values = [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]
    return values or [str(value) for value in default]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attribute failures for the locked 1H fixed-spread pivot candidate.",
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
    parser.add_argument("--diagnostic-filters", default="none,min_atr_q50,min_atr_q75,buy_leg_only,sell_leg_only,max_spread_atr_0.05,max_spread_atr_0.10")
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
    parser.add_argument("--require-stress-pass", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase167A 1H locked candidate regime failure attribution")
    return parser.parse_args(argv)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def classify_atr_regime(value: float, q25: float, q50: float, q75: float) -> str:
    if value <= q25:
        return "atr_q1_low"
    if value <= q50:
        return "atr_q2_mid_low"
    if value <= q75:
        return "atr_q3_mid_high"
    return "atr_q4_high"


def classify_spread_atr(value: float) -> str:
    if value <= 0.02:
        return "spread_atr_le_0.02"
    if value <= 0.05:
        return "spread_atr_0.02_0.05"
    if value <= 0.10:
        return "spread_atr_0.05_0.10"
    if value <= 0.20:
        return "spread_atr_0.10_0.20"
    return "spread_atr_gt_0.20"


def full_spread_to_atr(row: Mapping[str, Any]) -> float:
    atr_value = max(float(row.get("atr_value", 0.0)), 1e-9)
    spread_value = float(row.get("spread_value", 0.0))
    mode = str(row.get("spread_mode", "fixed"))
    if mode == "pct":
        return abs(float(row.get("entry", 0.0)) * spread_value / 100.0) / atr_value
    return spread_value / atr_value


def aggregate_trade_rows(rows: Sequence[Mapping[str, Any]], group: str, keys: Sequence[str]) -> list[RegimeAggregationRow]:
    buckets: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for row in rows:
        key = tuple(row.get(item, "") for item in keys)
        buckets.setdefault(key, []).append(row)
    output: list[RegimeAggregationRow] = []
    for key, items in buckets.items():
        pnls = [float(item.get("cash_pnl", 0.0)) for item in items]
        atr_scores = [float(item.get("atr_score", 0.0)) for item in items]
        wins = sum(1 for value in pnls if value > 0)
        losses = sum(1 for value in pnls if value < 0)
        lookup = dict(zip(keys, key))
        output.append(
            RegimeAggregationRow(
                group=group,
                fold=int(lookup.get("fold", 0) or 0),
                split=str(lookup.get("split", "ALL")),
                bucket=str(lookup.get("bucket", lookup.get("month", lookup.get("atr_regime", lookup.get("spread_atr_regime", "ALL"))))),
                side=str(lookup.get("side", "ALL")),
                trades=len(items),
                wins=wins,
                losses=losses,
                win_rate=float(wins / len(items)) if items else 0.0,
                total_cash_pnl=float(sum(pnls)),
                profit_factor=profit_factor(pnls),
                avg_cash_pnl=float(np.mean(pnls)) if pnls else 0.0,
                avg_atr_score=float(np.mean(atr_scores)) if atr_scores else 0.0,
                take_profits=sum(1 for item in items if item.get("outcome") == "take_profit"),
                stop_losses=sum(1 for item in items if item.get("outcome") == "stop_loss"),
                timeouts=sum(1 for item in items if item.get("outcome") == "timeout"),
            )
        )
    return sorted(output, key=lambda row: (row.group, row.fold, row.split, row.bucket, row.side))


def fold_failure_reasons(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if not int(row.get("train_pass_gate", 0)):
        reasons.append("train_gate_failed")
    if not int(row.get("validation_pass_gate", 0)):
        reasons.append("validation_gate_failed")
    if not int(row.get("test_pass_gate", 0)):
        reasons.append("test_gate_failed")
    if not int(row.get("monthly_stability_gate", 0)):
        reasons.append("monthly_stability_failed")
    if not int(row.get("stress_transfer_pass_gate", 0)):
        reasons.append("stress_transfer_failed")
    return reasons or ["none"]


def worst_group(rows: Sequence[RegimeAggregationRow]) -> tuple[str, float]:
    if not rows:
        return "", 0.0
    row = min(rows, key=lambda item: item.total_cash_pnl)
    return f"{row.bucket}|{row.side}" if row.side != "ALL" else row.bucket, float(row.total_cash_pnl)


def filter_indices_and_masks(
    name: str,
    indices: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    frame: Any,
    atr: np.ndarray,
    train_thresholds: Mapping[str, float],
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    idx = np.asarray(indices, dtype=np.int64)
    top = top_mask.copy()
    bottom = bottom_mask.copy()
    if name == "none":
        return idx, top, bottom
    if name == "min_atr_q50":
        return idx[atr[idx] >= float(train_thresholds["q50"])], top, bottom
    if name == "min_atr_q75":
        return idx[atr[idx] >= float(train_thresholds["q75"])], top, bottom
    if name == "buy_leg_only":
        # For the locked breakout mapping, top-zone events are BUY.
        bottom[:] = False
        return idx, top, bottom
    if name == "sell_leg_only":
        # For the locked breakout mapping, bottom-zone events are SELL.
        top[:] = False
        return idx, top, bottom
    if name.startswith("max_spread_atr_"):
        threshold_text = name.replace("max_spread_atr_", "")
        threshold = float(threshold_text)
        close = frame["close"].to_numpy(dtype=np.float64)
        if str(args.spread_mode) == "pct":
            spread_atr = (close[idx] * float(args.spread_value) / 100.0) / np.maximum(atr[idx], 1e-9)
        else:
            spread_atr = float(args.spread_value) / np.maximum(atr[idx], 1e-9)
        return idx[spread_atr <= threshold], top, bottom
    return idx, top, bottom


def summarize_filter(filter_name: str, rows: Sequence[FilterDiagnosticRow]) -> FilterSummaryRow:
    folds = len(rows)
    fold_pass_count = sum(int(row.fold_pass_gate) for row in rows)
    test_pass_count = sum(int(row.test_pass_gate) for row in rows)
    test_pnls = np.asarray([row.test_total_cash_pnl for row in rows], dtype=np.float64)
    test_pfs = np.asarray([row.test_profit_factor for row in rows], dtype=np.float64)
    return FilterSummaryRow(
        filter_name=filter_name,
        folds=folds,
        fold_pass_count=int(fold_pass_count),
        fold_pass_ratio=float(fold_pass_count / folds) if folds else 0.0,
        test_pass_count=int(test_pass_count),
        test_pass_ratio=float(test_pass_count / folds) if folds else 0.0,
        aggregate_test_pnl=float(np.sum(test_pnls)) if len(test_pnls) else 0.0,
        median_test_profit_factor=float(np.median(test_pfs)) if len(test_pfs) else 0.0,
        worst_test_profit_factor=float(np.min(test_pfs)) if len(test_pfs) else 0.0,
        worst_test_pnl=float(np.min(test_pnls)) if len(test_pnls) else 0.0,
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase167Report) -> str:
    filter_rows = "".join(
        f"<tr><td>{html.escape(str(row['filter_name']))}</td>"
        f"<td>{int(row['fold_pass_count'])}/{int(row['folds'])}</td>"
        f"<td>{float(row['fold_pass_ratio']):.2f}</td>"
        f"<td>{float(row['test_pass_ratio']):.2f}</td>"
        f"<td>{float(row['aggregate_test_pnl']):.3f}</td>"
        f"<td>{float(row['median_test_profit_factor']):.3f}</td></tr>"
        for row in report.filter_summary_rows
    )
    failure_rows = "".join(
        f"<tr><td>{int(row['fold'])}</td>"
        f"<td>{html.escape(str(row['failure_reasons']))}</td>"
        f"<td>{float(row['train_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{html.escape(str(row['worst_side']))}</td>"
        f"<td>{html.escape(str(row['worst_atr_regime']))}</td></tr>"
        for row in report.fold_failure_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase167A regime/failure attribution for the locked 1H candidate. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'dominant_failure_reason': report.dominant_failure_reason,
        'worst_side': report.worst_side,
        'worst_atr_regime': report.worst_atr_regime,
        'best_filter_name': report.best_filter_name,
        'best_filter_fold_pass_ratio': report.best_filter_fold_pass_ratio,
        'recommendation': report.recommendation,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Fold failures</h2><table><thead><tr><th>Fold</th><th>Reasons</th><th>Train PF</th><th>Val PF</th><th>Test PF</th><th>Worst side</th><th>Worst ATR regime</th></tr></thead><tbody>{failure_rows}</tbody></table></section>
<section class="card"><h2>Diagnostic filters</h2><table><thead><tr><th>Filter</th><th>Fold pass</th><th>Fold ratio</th><th>Test ratio</th><th>Agg test PnL</th><th>Median test PF</th></tr></thead><tbody>{filter_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE167A 1H LOCKED CANDIDATE REGIME FAILURE AUDIT")
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
        fold_rows_raw: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        monthly_rows: list[dict[str, Any]] = []
        fold_thresholds: dict[int, dict[str, float]] = {}
        for spec in specs:
            fold_row, _split_summary, trades, months, _stress = replay_fold(spec, frame, top_mask, bottom_mask, atr, args)
            raw = asdict(fold_row)
            fold_rows_raw.append(raw)
            train_atr = atr[np.arange(spec.train_start, spec.train_end, dtype=np.int64)]
            q25, q50, q75 = np.quantile(train_atr[np.isfinite(train_atr)], [0.25, 0.50, 0.75])
            fold_thresholds[spec.fold] = {"q25": float(q25), "q50": float(q50), "q75": float(q75)}
            for trade in trades:
                enriched = dict(trade)
                thresholds = fold_thresholds[int(enriched["fold"])]
                enriched["year"] = str(enriched["timestamp"])[:4]
                enriched["month"] = str(enriched["timestamp"])[:7]
                enriched["atr_regime"] = classify_atr_regime(float(enriched.get("atr_value", 0.0)), thresholds["q25"], thresholds["q50"], thresholds["q75"])
                spread_atr = full_spread_to_atr(enriched)
                enriched["spread_to_atr"] = float(spread_atr)
                enriched["spread_atr_regime"] = classify_spread_atr(spread_atr)
                trade_rows.append(enriched)
            monthly_rows.extend(months)
        side_rows = aggregate_trade_rows(trade_rows, "side", ("fold", "split", "side"))
        atr_rows = aggregate_trade_rows([{**row, "bucket": row.get("atr_regime", "")} for row in trade_rows], "atr_regime", ("fold", "split", "bucket"))
        spread_rows = aggregate_trade_rows([{**row, "bucket": row.get("spread_atr_regime", "")} for row in trade_rows], "spread_atr_regime", ("fold", "split", "bucket"))
        month_rows = aggregate_trade_rows([{**row, "bucket": row.get("month", "")} for row in trade_rows], "month", ("split", "bucket"))
        fold_failure_rows: list[FoldFailureRow] = []
        for raw in fold_rows_raw:
            fold = int(raw["fold"])
            fold_trade_rows = [row for row in trade_rows if int(row["fold"]) == fold]
            fold_side_rows = aggregate_trade_rows(fold_trade_rows, "side", ("side",))
            fold_atr_rows = aggregate_trade_rows([{**row, "bucket": row.get("atr_regime", "")} for row in fold_trade_rows], "atr_regime", ("bucket",))
            fold_month_rows = aggregate_trade_rows([{**row, "bucket": row.get("month", "")} for row in fold_trade_rows], "month", ("bucket",))
            worst_side_name, worst_side_pnl = worst_group(fold_side_rows)
            worst_atr_name, worst_atr_pnl = worst_group(fold_atr_rows)
            worst_month_name, worst_month_pnl = worst_group(fold_month_rows)
            fold_failure_rows.append(
                FoldFailureRow(
                    fold=fold,
                    train_pass_gate=int(raw["train_pass_gate"]),
                    validation_pass_gate=int(raw["validation_pass_gate"]),
                    test_pass_gate=int(raw["test_pass_gate"]),
                    monthly_stability_gate=int(raw["monthly_stability_gate"]),
                    fold_transfer_pass_gate=int(raw["fold_transfer_pass_gate"]),
                    fold_pass_gate=int(raw["fold_pass_gate"]),
                    failure_reasons=json.dumps(fold_failure_reasons(raw), ensure_ascii=False),
                    train_profit_factor=float(raw["train_profit_factor"]),
                    train_total_cash_pnl=float(raw["train_total_cash_pnl"]),
                    train_positive_month_ratio=float(raw["train_positive_month_ratio"]),
                    validation_profit_factor=float(raw["validation_profit_factor"]),
                    validation_total_cash_pnl=float(raw["validation_total_cash_pnl"]),
                    validation_positive_month_ratio=float(raw["validation_positive_month_ratio"]),
                    test_profit_factor=float(raw["test_profit_factor"]),
                    test_total_cash_pnl=float(raw["test_total_cash_pnl"]),
                    test_positive_month_ratio=float(raw["test_positive_month_ratio"]),
                    worst_side=worst_side_name,
                    worst_side_pnl=worst_side_pnl,
                    worst_atr_regime=worst_atr_name,
                    worst_atr_regime_pnl=worst_atr_pnl,
                    worst_month=worst_month_name,
                    worst_month_pnl=worst_month_pnl,
                )
            )
        filter_names = parse_text_list(args.diagnostic_filters, ("none",))
        filter_rows: list[FilterDiagnosticRow] = []
        for name in filter_names:
            for spec in specs:
                thresholds = fold_thresholds[spec.fold]
                summaries: dict[str, LockdownSplitSummary] = {}
                for split, start, end in (
                    ("train", spec.train_start, spec.train_end),
                    ("validation", spec.validation_start, spec.validation_end),
                    ("test", spec.test_start, spec.test_end),
                ):
                    indices, filtered_top, filtered_bottom = filter_indices_and_masks(
                        name,
                        np.arange(start, end, dtype=np.int64),
                        top_mask,
                        bottom_mask,
                        frame,
                        atr,
                        thresholds,
                        args,
                    )
                    summary, _trades, _months = simulate_locked_split(split, frame, indices, filtered_top, filtered_bottom, atr, args, float(args.spread_value), collect_trades=True)
                    summaries[split] = summary
                train = summaries["train"]
                validation = summaries["validation"]
                test = summaries["test"]
                monthly_gate = int(
                    train.positive_month_ratio >= float(args.min_positive_month_ratio)
                    and validation.positive_month_ratio >= float(args.min_positive_month_ratio)
                    and test.positive_month_ratio >= float(args.min_positive_month_ratio)
                    and train.worst_month_pnl >= -float(args.max_worst_month_loss)
                    and validation.worst_month_pnl >= -float(args.max_worst_month_loss)
                    and test.worst_month_pnl >= -float(args.max_worst_month_loss)
                )
                transfer = int(train.pass_gate and validation.pass_gate and test.pass_gate)
                filter_rows.append(
                    FilterDiagnosticRow(
                        filter_name=name,
                        fold=spec.fold,
                        train_trades=int(train.trades),
                        train_profit_factor=float(train.profit_factor),
                        train_total_cash_pnl=float(train.total_cash_pnl),
                        train_pass_gate=int(train.pass_gate),
                        validation_trades=int(validation.trades),
                        validation_profit_factor=float(validation.profit_factor),
                        validation_total_cash_pnl=float(validation.total_cash_pnl),
                        validation_pass_gate=int(validation.pass_gate),
                        test_trades=int(test.trades),
                        test_profit_factor=float(test.profit_factor),
                        test_total_cash_pnl=float(test.total_cash_pnl),
                        test_pass_gate=int(test.pass_gate),
                        monthly_stability_gate=int(monthly_gate),
                        fold_transfer_pass_gate=int(transfer),
                        fold_pass_gate=int(transfer and monthly_gate),
                    )
                )
        filter_summaries = [summarize_filter(name, [row for row in filter_rows if row.filter_name == name]) for name in filter_names]
        filter_summaries = sorted(filter_summaries, key=lambda row: (row.fold_pass_ratio, row.test_pass_ratio, row.aggregate_test_pnl), reverse=True)
        all_side_rows = aggregate_trade_rows(trade_rows, "side_all", ("side",))
        all_atr_rows = aggregate_trade_rows([{**row, "bucket": row.get("atr_regime", "")} for row in trade_rows], "atr_all", ("bucket",))
        worst_side_name, worst_side_total = worst_group(all_side_rows)
        worst_atr_name, worst_atr_total = worst_group(all_atr_rows)
        reason_counts: dict[str, int] = {}
        for row in fold_failure_rows:
            for reason in json.loads(row.failure_reasons):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        dominant_reason = max(reason_counts.items(), key=lambda item: item[1])[0] if reason_counts else "none"
        best_filter = filter_summaries[0] if filter_summaries else None
        baseline = next((row for row in filter_summaries if row.filter_name == "none"), best_filter)
        if best_filter and baseline and best_filter.fold_pass_ratio > baseline.fold_pass_ratio:
            recommendation = "REGIME_FILTER_CONFIRMATION_REQUIRED_NO_TRAINING"
        elif baseline and baseline.test_pass_ratio >= 0.5 and baseline.aggregate_test_pnl > 0:
            recommendation = "REGIME_SENSITIVE_SIGNAL_DO_NOT_TRAIN_YET"
        else:
            recommendation = "STOP_LOCKED_CANDIDATE_OR_REDESIGN"
        fold_failures_csv = output_dir / "latest_fold_failures.csv"
        regime_csv = output_dir / "latest_regime_summary.csv"
        side_csv = output_dir / "latest_side_summary.csv"
        monthly_csv = output_dir / "latest_monthly_summary.csv"
        filter_csv = output_dir / "latest_filter_diagnostics.csv"
        filter_summary_csv = output_dir / "latest_filter_summary.csv"
        trades_csv = output_dir / "latest_trades.csv"
        write_csv(fold_failures_csv, [asdict(row) for row in fold_failure_rows])
        write_csv(regime_csv, [asdict(row) for row in atr_rows + spread_rows])
        write_csv(side_csv, [asdict(row) for row in side_rows])
        write_csv(monthly_csv, [asdict(row) for row in month_rows])
        write_csv(filter_csv, [asdict(row) for row in filter_rows])
        write_csv(filter_summary_csv, [asdict(row) for row in filter_summaries])
        write_csv(trades_csv, trade_rows)
        report = Phase167Report(
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
            folds=len(specs),
            baseline_fold_pass_count=int(sum(int(row.get("fold_pass_gate", 0)) for row in fold_rows_raw)),
            baseline_test_pass_count=int(sum(int(row.get("test_pass_gate", 0)) for row in fold_rows_raw)),
            baseline_aggregate_test_pnl=float(sum(float(row.get("test_total_cash_pnl", 0.0)) for row in fold_rows_raw)),
            dominant_failure_reason=dominant_reason,
            worst_side=worst_side_name,
            worst_side_total_pnl=worst_side_total,
            worst_atr_regime=worst_atr_name,
            worst_atr_regime_total_pnl=worst_atr_total,
            best_filter_name=str(best_filter.filter_name if best_filter else ""),
            best_filter_fold_pass_ratio=float(best_filter.fold_pass_ratio if best_filter else 0.0),
            best_filter_test_pass_ratio=float(best_filter.test_pass_ratio if best_filter else 0.0),
            best_filter_aggregate_test_pnl=float(best_filter.aggregate_test_pnl if best_filter else 0.0),
            recommendation=recommendation,
            fold_failure_rows=[asdict(row) for row in fold_failure_rows],
            side_summary_rows=[asdict(row) for row in side_rows[:200]],
            atr_regime_rows=[asdict(row) for row in atr_rows[:200]],
            spread_atr_regime_rows=[asdict(row) for row in spread_rows[:200]],
            monthly_summary_rows=[asdict(row) for row in month_rows[:240]],
            filter_summary_rows=[asdict(row) for row in filter_summaries],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_fold_failures_csv=str(fold_failures_csv),
            output_regime_summary_csv=str(regime_csv),
            output_side_summary_csv=str(side_csv),
            output_monthly_summary_csv=str(monthly_csv),
            output_filter_diagnostics_csv=str(filter_csv),
            output_filter_summary_csv=str(filter_summary_csv),
            output_trades_csv=str(trades_csv),
            production_status="BLOCKED — Phase167A regime/failure attribution only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase167A regime failure attribution complete")
        print(f"  folds              : {report.folds}")
        print(f"  baseline fold pass : {report.baseline_fold_pass_count}/{report.folds}")
        print(f"  baseline test pass : {report.baseline_test_pass_count}/{report.folds}")
        print(f"  dominant failure   : {report.dominant_failure_reason}")
        print(f"  best filter        : {report.best_filter_name} fold_ratio={report.best_filter_fold_pass_ratio:.2f}")
        print(f"  recommendation     : {report.recommendation}")
        print(f"  output             : {report.output_json}")
        print(f"  elapsed            : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
