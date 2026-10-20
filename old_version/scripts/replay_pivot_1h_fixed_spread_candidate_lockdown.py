"""Phase165A: 1H fixed-spread candidate lockdown / stability replay.

Phase164A found positive 1H spread/bracket diagnostics. This phase stops the
grid search and locks one nonzero-cost candidate for a strict stability replay:

    BRK_D1_FAST breakout, delay=1, rw=24, zone=0.05,
    bracket=1.5/1.0 ATR, hold=24, fixed spread=0.2.

The phase adds train stability, validation/test confirmation, monthly stability,
full trade exports, and optional spread-stress rows. It is research-only and
cannot approve paper/live/production trading.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_pivot_1h_entry_feasibility import (  # noqa: E402
    DEFAULT_STORAGE,
    build_zone_masks,
    parse_float_grid,
    parse_int_grid,
    read_ohlc_frame,
    resolve_flat_path_arg,
    sides_for_row,
)
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_bottom_buy_candidate import max_drawdown  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_SELL, trade_path  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_fixed_spread_candidate_lockdown")
SIDE_TO_ACTION = {"BUY": ACTION_BUY, "SELL": ACTION_SELL}


@dataclass(frozen=True)
class Locked1HTrade:
    number: int
    split: str
    timestamp: str
    candidate_row_id: int
    signal_row_id: int
    entry_row_id: int
    exit_row_id: int
    zone: str
    side: str
    entry: float
    tp: float
    sl: float
    exit_price: float
    points_pnl: float
    atr_score: float
    cash_pnl: float
    balance: float
    outcome: str
    tp_distance: float
    sl_distance: float
    risk_amount: float
    atr_value: float
    spread_mode: str
    spread_value: float
    bracket_id: str
    hold_bars: int


@dataclass(frozen=True)
class LockdownSplitSummary:
    split: str
    first_timestamp: str
    last_timestamp: str
    evaluated_rows: int
    candidate_events: int
    candidate_event_rate: float
    top_events: int
    bottom_events: int
    buy_events: int
    sell_events: int
    independent_replays: int
    independent_mean_atr: float
    independent_sum_atr: float
    independent_profit_factor: float
    independent_win_rate: float
    trades: int
    buy_trades: int
    sell_trades: int
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
    skipped_winners: int
    skipped_losers: int
    skipped_timeouts: int
    skipped_independent_sum_atr: float
    skipped_independent_mean_atr: float
    executed_independent_mean_atr: float
    invalid_events: int
    positive_months: int
    negative_months: int
    breakeven_months: int
    positive_month_ratio: float
    worst_month_pnl: float
    best_month_pnl: float
    monthly_pnl: dict[str, float]
    monthly_trades: dict[str, int]
    pass_gate: int


@dataclass(frozen=True)
class SpreadStressRow:
    spread_mode: str
    spread_value: float
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    train_positive_month_ratio: float
    train_pass_gate: int
    validation_trades: int
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_positive_month_ratio: float
    validation_pass_gate: int
    test_trades: int
    test_profit_factor: float
    test_total_cash_pnl: float
    test_positive_month_ratio: float
    test_pass_gate: int
    transfer_pass_gate: int


@dataclass(frozen=True)
class Phase165Report:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
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
    train_pass_gate: int
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    monthly_stability_gate: int
    lockdown_pass_gate: int
    summaries: list[dict[str, Any]]
    stress_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_summary_csv: str
    output_trades_csv: str
    output_monthly_csv: str
    output_stress_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lock down a single 1H fixed-spread pivot candidate with stability replay.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=24)
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
    parser.add_argument("--stress-spreads", default="0.2,0.5,1.0")
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
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
    parser.add_argument("--report-title", default="Phase165A 1H fixed-spread candidate lockdown replay")
    return parser.parse_args(argv)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def monthly_dicts(trades: Sequence[Locked1HTrade]) -> tuple[dict[str, float], dict[str, int]]:
    pnl: dict[str, float] = {}
    counts: dict[str, int] = {}
    for trade in trades:
        month = str(trade.timestamp)[:7]
        pnl[month] = pnl.get(month, 0.0) + float(trade.cash_pnl)
        counts[month] = counts.get(month, 0) + 1
    return dict(sorted(pnl.items())), dict(sorted(counts.items()))


def split_gate(split: str, summary_values: Mapping[str, Any], args: argparse.Namespace) -> int:
    trades = int(summary_values["trades"])
    pf = float(summary_values["profit_factor"])
    final_balance = float(summary_values["final_balance"])
    event_rate = float(summary_values["candidate_event_rate"])
    month_ratio = float(summary_values["positive_month_ratio"])
    worst_month = float(summary_values["worst_month_pnl"])
    if split == "train":
        return int(
            trades >= int(args.train_min_trades)
            and pf >= float(args.train_min_profit_factor)
            and final_balance >= float(args.train_min_final_balance)
            and month_ratio >= float(args.min_positive_month_ratio)
            and worst_month >= -float(args.max_worst_month_loss)
        )
    if split == "validation":
        return int(
            trades >= int(args.validation_min_trades)
            and pf >= float(args.validation_min_profit_factor)
            and final_balance >= float(args.validation_min_final_balance)
            and event_rate <= float(args.max_validation_event_rate)
            and month_ratio >= float(args.min_positive_month_ratio)
            and worst_month >= -float(args.max_worst_month_loss)
        )
    if split == "test":
        return int(
            trades >= int(args.test_min_trades)
            and pf >= float(args.test_min_profit_factor)
            and final_balance >= float(args.test_min_final_balance)
            and event_rate <= float(args.max_test_event_rate)
            and month_ratio >= float(args.min_positive_month_ratio)
            and worst_month >= -float(args.max_worst_month_loss)
        )
    return int(trades > 0)


def simulate_locked_split(
    split: str,
    frame: Any,
    local_indices: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    atr: np.ndarray,
    args: argparse.Namespace,
    spread_value: float | None = None,
    collect_trades: bool = True,
) -> tuple[LockdownSplitSummary, list[Locked1HTrade], list[dict[str, Any]]]:
    effective_spread = float(args.spread_value if spread_value is None else spread_value)
    trade_args = SimpleNamespace(
        spread_mode=str(args.spread_mode),
        spread_value=effective_spread,
        same_bar_policy=str(args.same_bar_policy),
    )
    balance = float(args.initial_capital)
    balances = [balance]
    open_until = -1
    events = 0
    top_events = 0
    bottom_events = 0
    buy_events = 0
    sell_events = 0
    invalid = 0
    independent_scores: list[float] = []
    executed_scores: list[float] = []
    skipped_scores: list[float] = []
    skipped_while_open = 0
    skipped_winners = 0
    skipped_losers = 0
    skipped_timeouts = 0
    trades: list[Locked1HTrade] = []
    candidate_rows = np.asarray(local_indices, dtype=np.int64)

    for row in candidate_rows:
        row_id = int(row)
        row_events = sides_for_row(str(args.side_mapping), bool(top_mask[row_id]), bool(bottom_mask[row_id]))
        for zone, side_name in row_events:
            events += 1
            top_events += int(zone == "top")
            bottom_events += int(zone == "bottom")
            buy_events += int(side_name == "BUY")
            sell_events += int(side_name == "SELL")
            signal_row = row_id + max(int(args.entry_delay_bars), 0)
            if signal_row >= len(frame) - 1:
                invalid += 1
                continue
            atr_value = float(atr[signal_row])
            if not np.isfinite(atr_value) or atr_value <= 0:
                invalid += 1
                continue
            tp_distance = atr_value * float(args.tp_atr)
            sl_distance = atr_value * float(args.sl_atr)
            path = trade_path(
                frame,
                signal_row,
                SIDE_TO_ACTION[side_name],
                tp_distance,
                sl_distance,
                int(args.hold_bars),
                trade_args,
            )
            if path is None:
                invalid += 1
                continue
            points, entry_row, exit_row, entry, tp, sl, exit_price, outcome = path
            atr_score = float(points / atr_value) if atr_value > 0 else 0.0
            independent_scores.append(atr_score)
            if signal_row <= open_until:
                skipped_while_open += 1
                skipped_scores.append(atr_score)
                if atr_score > 0:
                    skipped_winners += 1
                elif atr_score < 0:
                    skipped_losers += 1
                else:
                    skipped_timeouts += 1
                continue
            risk_amount = max(balance * float(args.risk_per_trade), 0.0)
            quantity = risk_amount / sl_distance if sl_distance > 0 else 0.0
            cash_pnl = float(points * quantity)
            balance += cash_pnl
            balances.append(balance)
            executed_scores.append(atr_score)
            if collect_trades:
                trades.append(
                    Locked1HTrade(
                        number=len(trades) + 1,
                        split=split,
                        timestamp=str(frame.at[row_id, "timestamp"]),
                        candidate_row_id=int(row_id),
                        signal_row_id=int(signal_row),
                        entry_row_id=int(entry_row),
                        exit_row_id=int(exit_row),
                        zone=str(zone),
                        side=str(side_name),
                        entry=float(entry),
                        tp=float(tp),
                        sl=float(sl),
                        exit_price=float(exit_price),
                        points_pnl=float(points),
                        atr_score=float(atr_score),
                        cash_pnl=float(cash_pnl),
                        balance=float(balance),
                        outcome=str(outcome),
                        tp_distance=float(tp_distance),
                        sl_distance=float(sl_distance),
                        risk_amount=float(risk_amount),
                        atr_value=float(atr_value),
                        spread_mode=str(args.spread_mode),
                        spread_value=float(effective_spread),
                        bracket_id=str(args.bracket_id),
                        hold_bars=int(args.hold_bars),
                    )
                )
            open_until = max(open_until, int(exit_row))
            if balance <= 0:
                break
        if balance <= 0:
            break

    cash_pnls = [float(trade.cash_pnl) for trade in trades]
    if not collect_trades:
        # Stress runs may not collect trade rows, but need cash metrics. Re-run
        # cash path from balances is not possible, so collect_trades should stay
        # true for summaries. This branch is kept defensive.
        cash_pnls = []
    outcomes = [trade.outcome for trade in trades]
    sides = [trade.side for trade in trades]
    gross_profit = float(sum(value for value in cash_pnls if value > 0))
    gross_loss = float(abs(sum(value for value in cash_pnls if value < 0)))
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    wins = int(sum(1 for value in cash_pnls if value > 0))
    losses = int(sum(1 for value in cash_pnls if value < 0))
    monthly_pnl, monthly_trades = monthly_dicts(trades)
    positive_months = int(sum(1 for value in monthly_pnl.values() if value > 0))
    negative_months = int(sum(1 for value in monthly_pnl.values() if value < 0))
    breakeven_months = int(sum(1 for value in monthly_pnl.values() if abs(float(value)) <= 1e-12))
    month_count = len(monthly_pnl)
    positive_month_ratio = float(positive_months / month_count) if month_count else 0.0
    worst_month = float(min(monthly_pnl.values())) if monthly_pnl else 0.0
    best_month = float(max(monthly_pnl.values())) if monthly_pnl else 0.0
    event_rate = float(events / len(local_indices)) if len(local_indices) else 0.0
    summary_values = {
        "trades": len(trades),
        "profit_factor": pf,
        "final_balance": balance,
        "candidate_event_rate": event_rate,
        "positive_month_ratio": positive_month_ratio,
        "worst_month_pnl": worst_month,
    }
    pass_value = split_gate(split, summary_values, args)
    first_ts = str(frame.at[int(local_indices[0]), "timestamp"]) if len(local_indices) else ""
    last_ts = str(frame.at[int(local_indices[-1]), "timestamp"]) if len(local_indices) else ""
    monthly_rows = [
        {
            "split": split,
            "month": month,
            "trades": int(monthly_trades.get(month, 0)),
            "cash_pnl": float(pnl),
            "positive_month": int(float(pnl) > 0),
            "negative_month": int(float(pnl) < 0),
            "spread_mode": str(args.spread_mode),
            "spread_value": float(effective_spread),
            "policy_key": str(args.policy_key),
            "bracket_id": str(args.bracket_id),
        }
        for month, pnl in monthly_pnl.items()
    ]
    summary = LockdownSplitSummary(
        split=split,
        first_timestamp=first_ts,
        last_timestamp=last_ts,
        evaluated_rows=int(len(local_indices)),
        candidate_events=int(events),
        candidate_event_rate=event_rate,
        top_events=int(top_events),
        bottom_events=int(bottom_events),
        buy_events=int(buy_events),
        sell_events=int(sell_events),
        independent_replays=int(len(independent_scores)),
        independent_mean_atr=float(np.mean(independent_scores)) if independent_scores else 0.0,
        independent_sum_atr=float(np.sum(independent_scores)) if independent_scores else 0.0,
        independent_profit_factor=profit_factor(independent_scores),
        independent_win_rate=float(np.mean(np.asarray(independent_scores) > 0)) if independent_scores else 0.0,
        trades=int(len(trades)),
        buy_trades=int(sum(1 for side in sides if side == "BUY")),
        sell_trades=int(sum(1 for side in sides if side == "SELL")),
        wins=wins,
        losses=losses,
        win_rate=float(wins / len(trades)) if trades else 0.0,
        total_cash_pnl=float(sum(cash_pnls)),
        final_balance=float(balance),
        return_percent=float((balance - float(args.initial_capital)) / float(args.initial_capital)) if float(args.initial_capital) else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=float(pf),
        max_drawdown_cash=float(max_drawdown(balances)),
        take_profits=int(sum(1 for outcome in outcomes if outcome == "take_profit")),
        stop_losses=int(sum(1 for outcome in outcomes if outcome == "stop_loss")),
        timeouts=int(sum(1 for outcome in outcomes if outcome == "timeout")),
        skipped_while_open=int(skipped_while_open),
        skipped_winners=int(skipped_winners),
        skipped_losers=int(skipped_losers),
        skipped_timeouts=int(skipped_timeouts),
        skipped_independent_sum_atr=float(np.sum(skipped_scores)) if skipped_scores else 0.0,
        skipped_independent_mean_atr=float(np.mean(skipped_scores)) if skipped_scores else 0.0,
        executed_independent_mean_atr=float(np.mean(executed_scores)) if executed_scores else 0.0,
        invalid_events=int(invalid),
        positive_months=positive_months,
        negative_months=negative_months,
        breakeven_months=breakeven_months,
        positive_month_ratio=positive_month_ratio,
        worst_month_pnl=worst_month,
        best_month_pnl=best_month,
        monthly_pnl=monthly_pnl,
        monthly_trades=monthly_trades,
        pass_gate=int(pass_value),
    )
    return summary, trades, monthly_rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def stress_rows_for(args: argparse.Namespace, frame: Any, split_map: Mapping[str, np.ndarray], top_mask: np.ndarray, bottom_mask: np.ndarray, atr: np.ndarray) -> list[SpreadStressRow]:
    output: list[SpreadStressRow] = []
    for spread in parse_float_grid(args.stress_spreads, (float(args.spread_value),)):
        summaries: dict[str, LockdownSplitSummary] = {}
        for split, idx in split_map.items():
            summary, _trades, _monthly = simulate_locked_split(split, frame, idx, top_mask, bottom_mask, atr, args, float(spread), collect_trades=True)
            summaries[split] = summary
        train = summaries.get("train")
        validation = summaries.get("validation")
        test = summaries.get("test")
        output.append(
            SpreadStressRow(
                spread_mode=str(args.spread_mode),
                spread_value=float(spread),
                train_trades=int(train.trades if train else 0),
                train_profit_factor=float(train.profit_factor if train else 0.0),
                train_total_cash_pnl=float(train.total_cash_pnl if train else 0.0),
                train_positive_month_ratio=float(train.positive_month_ratio if train else 0.0),
                train_pass_gate=int(train.pass_gate if train else 0),
                validation_trades=int(validation.trades if validation else 0),
                validation_profit_factor=float(validation.profit_factor if validation else 0.0),
                validation_total_cash_pnl=float(validation.total_cash_pnl if validation else 0.0),
                validation_positive_month_ratio=float(validation.positive_month_ratio if validation else 0.0),
                validation_pass_gate=int(validation.pass_gate if validation else 0),
                test_trades=int(test.trades if test else 0),
                test_profit_factor=float(test.profit_factor if test else 0.0),
                test_total_cash_pnl=float(test.total_cash_pnl if test else 0.0),
                test_positive_month_ratio=float(test.positive_month_ratio if test else 0.0),
                test_pass_gate=int(test.pass_gate if test else 0),
                transfer_pass_gate=int(bool(train and validation and test and train.pass_gate and validation.pass_gate and test.pass_gate)),
            )
        )
    return output


def render_html(title: str, report: Phase165Report) -> str:
    summary_rows = "".join(
        f"<tr><td>{html.escape(str(row['split']))}</td>"
        f"<td>{int(row['candidate_events'])}</td>"
        f"<td>{int(row['trades'])}</td>"
        f"<td>{float(row['total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['profit_factor']):.3f}</td>"
        f"<td>{float(row['positive_month_ratio']):.2f}</td>"
        f"<td>{float(row['worst_month_pnl']):.3f}</td>"
        f"<td>{int(row['pass_gate'])}</td></tr>"
        for row in report.summaries
    )
    stress_rows = "".join(
        f"<tr><td>{float(row['spread_value']):.4g}</td>"
        f"<td>{float(row['train_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.stress_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase165A 1H fixed-spread candidate lockdown replay. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'lockdown_pass_gate': report.lockdown_pass_gate,
        'train_pass_gate': report.train_pass_gate,
        'validation_pass_gate': report.validation_pass_gate,
        'test_pass_gate': report.test_pass_gate,
        'monthly_stability_gate': report.monthly_stability_gate,
        'transfer_pass_gate': report.transfer_pass_gate,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Split summaries</h2><table><thead><tr><th>Split</th><th>Events</th><th>Trades</th><th>PnL</th><th>PF</th><th>Positive month ratio</th><th>Worst month</th><th>Pass</th></tr></thead><tbody>{summary_rows}</tbody></table></section>
<section class="card"><h2>Spread stress</h2><table><thead><tr><th>Spread</th><th>Train PF</th><th>Validation PF</th><th>Test PF</th><th>Transfer</th></tr></thead><tbody>{stress_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE165A 1H FIXED-SPREAD CANDIDATE LOCKDOWN REPLAY")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        split_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
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
        summaries: list[LockdownSplitSummary] = []
        all_trades: list[Locked1HTrade] = []
        monthly_rows: list[dict[str, Any]] = []
        for split, idx in split_map.items():
            summary, trades, month_rows = simulate_locked_split(split, frame, idx, top_mask, bottom_mask, atr, args, float(args.spread_value), collect_trades=True)
            summaries.append(summary)
            all_trades.extend(trades)
            monthly_rows.extend(month_rows)
        stress_rows = stress_rows_for(args, frame, split_map, top_mask, bottom_mask, atr)
        train = next(summary for summary in summaries if summary.split == "train")
        validation = next(summary for summary in summaries if summary.split == "validation")
        test = next(summary for summary in summaries if summary.split == "test")
        transfer_pass = int(train.pass_gate and validation.pass_gate and test.pass_gate)
        monthly_stability = int(
            train.positive_month_ratio >= float(args.min_positive_month_ratio)
            and validation.positive_month_ratio >= float(args.min_positive_month_ratio)
            and test.positive_month_ratio >= float(args.min_positive_month_ratio)
            and train.worst_month_pnl >= -float(args.max_worst_month_loss)
            and validation.worst_month_pnl >= -float(args.max_worst_month_loss)
            and test.worst_month_pnl >= -float(args.max_worst_month_loss)
        )
        stress_gate = int(any(row.transfer_pass_gate for row in stress_rows)) if str(args.require_stress_pass) == "1" else 1
        lockdown_pass = int(transfer_pass and monthly_stability and stress_gate)
        summary_csv = output_dir / "latest_summary.csv"
        trades_csv = output_dir / "latest_trades.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        stress_csv = output_dir / "latest_stress.csv"
        write_csv(summary_csv, [asdict(summary) for summary in summaries])
        write_csv(trades_csv, [asdict(trade) for trade in all_trades])
        write_csv(monthly_csv, monthly_rows)
        write_csv(stress_csv, [asdict(row) for row in stress_rows])
        report = Phase165Report(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
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
            train_pass_gate=int(train.pass_gate),
            validation_pass_gate=int(validation.pass_gate),
            test_pass_gate=int(test.pass_gate),
            transfer_pass_gate=int(transfer_pass),
            monthly_stability_gate=int(monthly_stability),
            lockdown_pass_gate=int(lockdown_pass),
            summaries=[asdict(summary) for summary in summaries],
            stress_rows=[asdict(row) for row in stress_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_summary_csv=str(summary_csv),
            output_trades_csv=str(trades_csv),
            output_monthly_csv=str(monthly_csv),
            output_stress_csv=str(stress_csv),
            production_status="BLOCKED — Phase165A 1H candidate lockdown diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase165A candidate lockdown replay complete")
        print(f"  train PF       : {train.profit_factor:.4f} pass={train.pass_gate}")
        print(f"  validation PF  : {validation.profit_factor:.4f} pass={validation.pass_gate}")
        print(f"  test PF        : {test.profit_factor:.4f} pass={test.pass_gate}")
        print(f"  monthly pass   : {monthly_stability}")
        print(f"  lockdown pass  : {lockdown_pass}")
        print(f"  output         : {report.output_json}")
        print(f"  elapsed        : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
