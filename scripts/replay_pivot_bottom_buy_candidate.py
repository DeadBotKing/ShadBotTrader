"""Phase161A: chronological replay for selected pivot bottom-buy candidate.

Phase160A found the first positive transfer diagnostic in the recent pivot route:

    target=B2, mapping=bottom_buy, delay=0,
    recent_window=48, zone_atr=0.05, bottom_position<=0.15,
    exclude_both=1, min_range_width_atr=1.0.

This phase turns that event-level diagnostic into a broker-style chronological
single-position replay with spread, TP/SL path, risk sizing, monthly breakdown,
and train/validation/test reports. Research-only.
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

from audit_pivot_candidate_geometry_tightening import load_meta_sample_indices, read_frame, rolling_high_low  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, trade_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_bottom_buy_chronological_replay")


@dataclass(frozen=True)
class PivotBottomBuyTrade:
    number: int
    split: str
    timestamp: str
    candidate_row_id: int
    entry_row_id: int
    exit_row_id: int
    side: str
    entry: float
    tp: float
    sl: float
    exit_price: float
    points_pnl: float
    cash_pnl: float
    balance: float
    outcome: str
    tp_distance: float
    sl_distance: float
    risk_amount: float
    atr_value: float
    recent_window_bars: int
    pivot_zone_atr: float
    bottom_position: float
    min_range_width_atr: float
    entry_delay_bars: int


@dataclass(frozen=True)
class SplitReplaySummary:
    split: str
    evaluated_rows: int
    first_timestamp: str
    last_timestamp: str
    candidate_rows: int
    candidate_rate: float
    trades: int
    buy_trades: int
    wins: int
    losses: int
    win_rate: float
    total_cash_pnl: float
    final_balance: float
    return_percent: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown_cash: float
    take_profits: int
    stop_losses: int
    timeouts: int
    skipped_while_open: int
    invalid_trades: int
    positive_months: int
    negative_months: int
    monthly_pnl: dict[str, float]
    monthly_trades: dict[str, int]
    pass_gate: int


@dataclass(frozen=True)
class PivotBottomBuyReplayReport:
    symbol: str
    timeframe: str
    flat_path: str
    meta_path: str
    sampled_universe: str
    flat_rows: int
    sampled_rows: int
    target_id: str
    side_mapping: str
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    entry_delay_bars: int
    tp_atr: float
    sl_atr: float
    spread_mode: str
    spread_value: float
    same_bar_policy: str
    initial_capital: float
    risk_per_trade: float
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    summaries: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_summary_csv: str
    output_trades_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chronological replay for Phase160A selected pivot bottom-buy candidate.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--target-id", default="B2")
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.05)
    parser.add_argument("--top-position-threshold", type=float, default=0.85)
    parser.add_argument("--bottom-position-threshold", type=float, default=0.15)
    parser.add_argument("--exclude-both-zones", choices=("0", "1"), default="1")
    parser.add_argument("--min-range-width-atr", type=float, default=1.0)
    parser.add_argument("--max-range-width-atr", type=float, default=0.0)
    parser.add_argument("--entry-delay-bars", type=int, default=0)
    parser.add_argument("--tp-atr", type=float, default=1.0)
    parser.add_argument("--sl-atr", type=float, default=0.75)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--validation-min-trades", type=int, default=20)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=20)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase161A pivot bottom-buy chronological replay")
    return parser.parse_args(argv)


def max_drawdown(balances: Sequence[float]) -> float:
    peak = float(balances[0]) if balances else 0.0
    worst = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        worst = max(worst, peak - float(balance))
    return worst


def monthly_stats(trades: Sequence[PivotBottomBuyTrade]) -> tuple[dict[str, float], dict[str, int]]:
    pnl: dict[str, float] = {}
    counts: dict[str, int] = {}
    for trade in trades:
        month = str(trade.timestamp)[:7]
        pnl[month] = pnl.get(month, 0.0) + float(trade.cash_pnl)
        counts[month] = counts.get(month, 0) + 1
    return dict(sorted(pnl.items())), dict(sorted(counts.items()))


def build_bottom_buy_mask(frame: pd.DataFrame, selected_rows: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    atr = resolve_atr(frame)
    recent_high, recent_low = rolling_high_low(high, low, int(args.recent_window_bars))
    width = np.maximum(recent_high - recent_low, 1e-9)
    position = (close - recent_low) / width
    width_atr = width / np.maximum(atr, 1e-9)
    selected_close = close[selected_rows]
    selected_low = recent_low[selected_rows]
    selected_high = recent_high[selected_rows]
    selected_atr = atr[selected_rows]
    selected_position = position[selected_rows]
    selected_width_atr = width_atr[selected_rows]
    bottom_distance = selected_close - selected_low <= float(args.pivot_zone_atr) * selected_atr
    bottom_position = selected_position <= float(args.bottom_position_threshold)
    bottom = bottom_distance & bottom_position
    if str(args.exclude_both_zones) == "1":
        top_distance = selected_high - selected_close <= float(args.pivot_zone_atr) * selected_atr
        top_position = selected_position >= float(args.top_position_threshold)
        bottom = bottom & ~(top_distance & top_position)
    width_ok = selected_width_atr >= float(args.min_range_width_atr)
    if float(args.max_range_width_atr) > 0:
        width_ok = width_ok & (selected_width_atr <= float(args.max_range_width_atr))
    return bottom & width_ok


def simulate_split(
    split: str,
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    local_indices: np.ndarray,
    candidate_mask: np.ndarray,
    args: argparse.Namespace,
) -> tuple[SplitReplaySummary, list[PivotBottomBuyTrade]]:
    atr = resolve_atr(frame)
    balance = float(args.initial_capital)
    balances = [balance]
    open_until = -1
    trades: list[PivotBottomBuyTrade] = []
    skipped_while_open = 0
    invalid = 0
    candidate_indices = [int(local) for local in np.asarray(local_indices, dtype=np.int64) if bool(candidate_mask[int(local)])]
    for local in candidate_indices:
        row_id = int(selected_rows[local])
        entry_signal_row = row_id + max(int(args.entry_delay_bars), 0)
        if entry_signal_row <= open_until:
            skipped_while_open += 1
            continue
        if entry_signal_row >= len(frame) - 1:
            invalid += 1
            continue
        atr_value = float(atr[entry_signal_row])
        if not np.isfinite(atr_value) or atr_value <= 0:
            invalid += 1
            continue
        tp_distance = atr_value * float(args.tp_atr)
        sl_distance = atr_value * float(args.sl_atr)
        path = trade_path(
            frame,
            entry_signal_row,
            ACTION_BUY,
            tp_distance,
            sl_distance,
            int(args.hold_bars),
            args,
        )
        if path is None:
            invalid += 1
            continue
        points, entry_row, exit_row, entry, tp, sl, exit_price, outcome = path
        risk_amount = max(balance * float(args.risk_per_trade), 0.0)
        quantity = risk_amount / sl_distance if sl_distance > 0 else 0.0
        cash_pnl = points * quantity
        balance += cash_pnl
        balances.append(balance)
        trades.append(
            PivotBottomBuyTrade(
                number=len(trades) + 1,
                split=split,
                timestamp=str(frame.at[row_id, "timestamp"]),
                candidate_row_id=row_id,
                entry_row_id=int(entry_row),
                exit_row_id=int(exit_row),
                side="BUY",
                entry=float(entry),
                tp=float(tp),
                sl=float(sl),
                exit_price=float(exit_price),
                points_pnl=float(points),
                cash_pnl=float(cash_pnl),
                balance=float(balance),
                outcome=str(outcome),
                tp_distance=float(tp_distance),
                sl_distance=float(sl_distance),
                risk_amount=float(risk_amount),
                atr_value=float(atr_value),
                recent_window_bars=int(args.recent_window_bars),
                pivot_zone_atr=float(args.pivot_zone_atr),
                bottom_position=float(args.bottom_position_threshold),
                min_range_width_atr=float(args.min_range_width_atr),
                entry_delay_bars=int(args.entry_delay_bars),
            )
        )
        open_until = max(open_until, int(exit_row))
        if balance <= 0:
            break
    pnls = [float(trade.cash_pnl) for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    monthly_pnl, monthly_trades = monthly_stats(trades)
    pass_gate = int(
        len(trades) >= (int(args.validation_min_trades) if split == "validation" else int(args.test_min_trades) if split == "test" else 1)
        and (gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)) >= (float(args.validation_min_profit_factor) if split == "validation" else float(args.test_min_profit_factor) if split == "test" else 0.0)
        and balance >= (float(args.validation_min_final_balance) if split == "validation" else float(args.test_min_final_balance) if split == "test" else 0.0)
    )
    first_ts = str(frame.at[int(selected_rows[int(local_indices[0])]), "timestamp"]) if len(local_indices) else ""
    last_ts = str(frame.at[int(selected_rows[int(local_indices[-1])]), "timestamp"]) if len(local_indices) else ""
    summary = SplitReplaySummary(
        split=split,
        evaluated_rows=int(len(local_indices)),
        first_timestamp=first_ts,
        last_timestamp=last_ts,
        candidate_rows=int(len(candidate_indices)),
        candidate_rate=float(len(candidate_indices) / len(local_indices)) if len(local_indices) else 0.0,
        trades=len(trades),
        buy_trades=len(trades),
        wins=wins,
        losses=losses,
        win_rate=float(wins / len(trades)) if trades else 0.0,
        total_cash_pnl=sum(pnls),
        final_balance=float(balance),
        return_percent=float((balance - float(args.initial_capital)) / float(args.initial_capital)) if float(args.initial_capital) else 0.0,
        gross_profit=float(gross_profit),
        gross_loss=float(gross_loss),
        profit_factor=float(gross_profit / gross_loss) if gross_loss else (999.0 if gross_profit else 0.0),
        max_drawdown_cash=float(max_drawdown(balances)),
        take_profits=sum(1 for trade in trades if trade.outcome == "take_profit"),
        stop_losses=sum(1 for trade in trades if trade.outcome == "stop_loss"),
        timeouts=sum(1 for trade in trades if trade.outcome == "timeout"),
        skipped_while_open=int(skipped_while_open),
        invalid_trades=int(invalid),
        positive_months=sum(1 for value in monthly_pnl.values() if value > 0),
        negative_months=sum(1 for value in monthly_pnl.values() if value < 0),
        monthly_pnl=monthly_pnl,
        monthly_trades=monthly_trades,
        pass_gate=pass_gate,
    )
    return summary, trades


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: PivotBottomBuyReplayReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['split']))}</td>"
        f"<td>{int(row['candidate_rows'])}</td>"
        f"<td>{int(row['trades'])}</td>"
        f"<td>{float(row['total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['profit_factor']):.3f}</td>"
        f"<td>{float(row['max_drawdown_cash']):.3f}</td>"
        f"<td>{int(row['pass_gate'])}</td></tr>"
        for row in report.summaries
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:13px; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase161A bottom-buy chronological replay. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Split summaries</h2><table><thead><tr><th>Split</th><th>Candidates</th><th>Trades</th><th>PnL</th><th>PF</th><th>MaxDD</th><th>Pass</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE161A PIVOT BOTTOM-BUY CHRONOLOGICAL REPLAY")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, meta_path = load_meta_sample_indices(args, len(frame))
        train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
        candidate_mask = build_bottom_buy_mask(frame, selected_rows, args)
        split_specs = [("train", train_idx), ("validation", validation_idx), ("test", test_idx)]
        summaries: list[SplitReplaySummary] = []
        all_trades: list[PivotBottomBuyTrade] = []
        for split, split_idx in split_specs:
            summary, trades = simulate_split(split, frame, selected_rows, split_idx, candidate_mask, args)
            summaries.append(summary)
            all_trades.extend(trades)
        summary_csv = output_dir / "latest_summary.csv"
        trades_csv = output_dir / "latest_trades.csv"
        write_csv(summary_csv, [asdict(summary) for summary in summaries])
        write_csv(trades_csv, [asdict(trade) for trade in all_trades])
        validation = next(summary for summary in summaries if summary.split == "validation")
        test = next(summary for summary in summaries if summary.split == "test")
        report = PivotBottomBuyReplayReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(meta_path or ""),
            sampled_universe=sampled_universe,
            flat_rows=len(frame),
            sampled_rows=len(selected_rows),
            target_id=str(args.target_id),
            side_mapping="bottom_buy",
            recent_window_bars=int(args.recent_window_bars),
            pivot_zone_atr=float(args.pivot_zone_atr),
            top_position_threshold=float(args.top_position_threshold),
            bottom_position_threshold=float(args.bottom_position_threshold),
            exclude_both_zones=int(args.exclude_both_zones),
            min_range_width_atr=float(args.min_range_width_atr),
            max_range_width_atr=float(args.max_range_width_atr),
            entry_delay_bars=int(args.entry_delay_bars),
            tp_atr=float(args.tp_atr),
            sl_atr=float(args.sl_atr),
            spread_mode=str(args.spread_mode),
            spread_value=float(args.spread_value),
            same_bar_policy=str(args.same_bar_policy),
            initial_capital=float(args.initial_capital),
            risk_per_trade=float(args.risk_per_trade),
            validation_pass_gate=int(validation.pass_gate),
            test_pass_gate=int(test.pass_gate),
            transfer_pass_gate=int(validation.pass_gate and test.pass_gate),
            summaries=[asdict(summary) for summary in summaries],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_summary_csv=str(summary_csv),
            output_trades_csv=str(trades_csv),
            production_status="BLOCKED — Phase161A bottom-buy chronological replay only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase161A bottom-buy replay complete")
        print(f"  validation PF : {validation.profit_factor:.4f} trades={validation.trades}")
        print(f"  test PF       : {test.profit_factor:.4f} trades={test.trades}")
        print(f"  transfer pass : {report.transfer_pass_gate}")
        print(f"  output        : {report.output_json}")
        print(f"  elapsed       : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
