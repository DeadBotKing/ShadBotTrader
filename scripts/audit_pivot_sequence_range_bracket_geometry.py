"""Phase150A: audit range-bracket geometry for pivot sequence archives.

This script consumes a Phase148 range-aware prediction archive and replays the
same model-selected actions under alternative TP/SL bracket policies. It does
not train a model and it does not change predictions. Its purpose is to diagnose
whether range-derived exits are viable before any signal/filter tuning.

Research-only. No paper/live approval.
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
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from backtest_pivot_pattern_sequence_wavenet_range import (  # noqa: E402
    ACTION_BUY,
    ACTION_SELL,
    atr_distances,
    entry_price_for_row,
    max_drawdown,
    range_distances,
    range_filter_pass,
    summarize_monthly,
    summarize_side,
)
from train_pivot_pattern_recognition import safe_float, trade_path  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_sequence_range_bracket_geometry")


@dataclass(frozen=True)
class BracketPolicy:
    range_bracket_mode: str
    range_fallback: str
    use_1d_tp_cap: str
    min_tp_distance: float
    min_sl_distance: float
    max_tp_atr: float
    max_sl_atr: float
    min_range_4h_room: float
    min_range_1d_room: float
    same_bar_policy: str

    def key(self) -> str:
        return (
            f"mode={self.range_bracket_mode}|fallback={self.range_fallback}|"
            f"use1d={self.use_1d_tp_cap}|min_tp={self.min_tp_distance:g}|"
            f"min_sl={self.min_sl_distance:g}|max_tp_atr={self.max_tp_atr:g}|"
            f"max_sl_atr={self.max_sl_atr:g}|min4h={self.min_range_4h_room:g}|"
            f"min1d={self.min_range_1d_room:g}|same={self.same_bar_policy}"
        )


@dataclass(frozen=True)
class GeometrySummary:
    policy_key: str
    rank: int
    score: float
    range_bracket_mode: str
    range_fallback: str
    use_1d_tp_cap: str
    min_tp_distance: float
    min_sl_distance: float
    max_tp_atr: float
    max_sl_atr: float
    min_range_4h_room: float
    min_range_1d_room: float
    same_bar_policy: str
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    win_rate: float
    total_cash_pnl: float
    buy_cash_pnl: float
    sell_cash_pnl: float
    final_balance: float
    return_percent: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown_cash: float
    take_profits: int
    stop_losses: int
    timeouts: int
    stop_loss_rate: float
    take_profit_rate: float
    timeout_rate: float
    skipped_by_model: int
    skipped_while_open: int
    skipped_side_filter: int
    skipped_range_unavailable: int
    skipped_range_filter: int
    invalid_bracket: int
    invalid_trade: int
    min_sl_hits: int
    min_tp_hits: int
    avg_tp_distance: float
    avg_sl_distance: float
    median_tp_distance: float
    median_sl_distance: float
    positive_months: int
    negative_months: int
    pass_gate: int


@dataclass(frozen=True)
class GeometryReport:
    predictions_path: str
    flat_path: str
    split_name: str
    evaluated_rows: int
    policies_evaluated: int
    min_trades: int
    score_metric: str
    best_policy: dict[str, Any]
    baseline_atr_policy: dict[str, Any]
    top_policies: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_grid_csv: str
    output_best_trades_csv: str
    production_status: str


def parse_csv_floats(raw: str, default: Sequence[float]) -> list[float]:
    text = str(raw or "").strip()
    if not text:
        return [float(value) for value in default]
    values: list[float] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        values.append(float(item))
    return values or [float(value) for value in default]


def parse_csv_choices(raw: str, allowed: Iterable[str], default: Sequence[str]) -> list[str]:
    allowed_set = {str(value) for value in allowed}
    text = str(raw or "").strip()
    if not text:
        return list(default)
    values: list[str] = []
    for item in text.split(","):
        value = item.strip()
        if value in allowed_set and value not in values:
            values.append(value)
    return values or list(default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase150A range-bracket geometry audit for pivot sequence archives.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--predictions-path", default="run_logs/pivot_pattern_sequence_wavenet_range_archive_validation/latest_predictions.parquet")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--split-name", default="validation")
    parser.add_argument("--allowed-sides", default="BUY,SELL")
    parser.add_argument("--range-bracket-modes", default="atr,range_capped")
    parser.add_argument("--range-fallbacks", default="skip")
    parser.add_argument("--use-1d-tp-caps", default="1,0")
    parser.add_argument("--min-tp-distances", default="0.5,2,5")
    parser.add_argument("--min-sl-distances", default="0.5,2,5,10")
    parser.add_argument("--max-tp-atrs", default="2.0,0")
    parser.add_argument("--max-sl-atrs", default="1.25,2.0")
    parser.add_argument("--min-range-4h-rooms", default="0")
    parser.add_argument("--min-range-1d-rooms", default="0")
    parser.add_argument("--same-bar-policies", default="stop_first")
    parser.add_argument("--atr-tp-multiplier", type=float, default=0.75)
    parser.add_argument("--atr-sl-multiplier", type=float, default=0.75)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument(
        "--score-metric",
        choices=("total_pnl", "profit_factor", "drawdown_adjusted"),
        default="drawdown_adjusted",
    )
    parser.add_argument("--pass-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--pass-min-final-balance", type=float, default=100.0)
    parser.add_argument("--pass-max-drawdown", type=float, default=25.0)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase150A range bracket geometry audit")
    return parser.parse_args(argv)


def read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Input file not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    try:
        return pd.read_parquet(path)
    except Exception:
        csv_path = path.with_suffix(".csv")
        if csv_path.exists():
            return pd.read_csv(csv_path)
        raise


def side_to_action(value: Any) -> int:
    text = str(value or "").upper()
    if text == "BUY":
        return ACTION_BUY
    if text == "SELL":
        return ACTION_SELL
    return -1


def prediction_range_record(row: Mapping[str, Any]) -> dict[str, float]:
    keys = (
        "range_4h_available",
        "range_4h_high_price",
        "range_4h_low_price",
        "range_4h_up_room",
        "range_4h_down_room",
        "range_1d_available",
        "range_1d_high_price",
        "range_1d_low_price",
        "range_1d_up_room",
        "range_1d_down_room",
    )
    return {key: safe_float(row.get(key, 0.0), 0.0) for key in keys}


def policy_namespace(policy: BracketPolicy, args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        range_bracket_mode=policy.range_bracket_mode,
        range_fallback=policy.range_fallback,
        use_1d_tp_cap=policy.use_1d_tp_cap,
        min_tp_distance=float(policy.min_tp_distance),
        min_sl_distance=float(policy.min_sl_distance),
        max_tp_atr=float(policy.max_tp_atr),
        max_sl_atr=float(policy.max_sl_atr),
        min_range_4h_room=float(policy.min_range_4h_room),
        min_range_1d_room=float(policy.min_range_1d_room),
        atr_tp_multiplier=float(args.atr_tp_multiplier),
        atr_sl_multiplier=float(args.atr_sl_multiplier),
        hold_bars=int(args.hold_bars),
        spread_mode=args.spread_mode,
        spread_value=float(args.spread_value),
        same_bar_policy=policy.same_bar_policy,
    )


def build_policies(args: argparse.Namespace) -> list[BracketPolicy]:
    modes = parse_csv_choices(args.range_bracket_modes, ("atr", "range", "range_capped"), ("atr", "range_capped"))
    fallbacks = parse_csv_choices(args.range_fallbacks, ("skip", "atr"), ("skip",))
    use_caps = parse_csv_choices(args.use_1d_tp_caps, ("0", "1"), ("1", "0"))
    same_bar = parse_csv_choices(args.same_bar_policies, ("stop_first", "tp_first"), ("stop_first",))
    min_tps = parse_csv_floats(args.min_tp_distances, (0.5, 2.0, 5.0))
    min_sls = parse_csv_floats(args.min_sl_distances, (0.5, 2.0, 5.0, 10.0))
    max_tps = parse_csv_floats(args.max_tp_atrs, (2.0, 0.0))
    max_sls = parse_csv_floats(args.max_sl_atrs, (1.25, 2.0))
    min_4h = parse_csv_floats(args.min_range_4h_rooms, (0.0,))
    min_1d = parse_csv_floats(args.min_range_1d_rooms, (0.0,))
    policies: dict[str, BracketPolicy] = {}
    for mode in modes:
        if mode == "atr":
            for min_tp in min_tps:
                for min_sl in min_sls:
                    for same in same_bar:
                        policy = BracketPolicy(
                            range_bracket_mode="atr",
                            range_fallback="skip",
                            use_1d_tp_cap="0",
                            min_tp_distance=float(min_tp),
                            min_sl_distance=float(min_sl),
                            max_tp_atr=0.0,
                            max_sl_atr=0.0,
                            min_range_4h_room=0.0,
                            min_range_1d_room=0.0,
                            same_bar_policy=same,
                        )
                        policies[policy.key()] = policy
            continue
        for fallback in fallbacks:
            for use_cap in use_caps:
                for min_tp in min_tps:
                    for min_sl in min_sls:
                        for max_tp in max_tps:
                            for max_sl in max_sls:
                                for room_4h in min_4h:
                                    for room_1d in min_1d:
                                        for same in same_bar:
                                            policy = BracketPolicy(
                                                range_bracket_mode=mode,
                                                range_fallback=fallback,
                                                use_1d_tp_cap=use_cap,
                                                min_tp_distance=float(min_tp),
                                                min_sl_distance=float(min_sl),
                                                max_tp_atr=float(max_tp),
                                                max_sl_atr=float(max_sl),
                                                min_range_4h_room=float(room_4h),
                                                min_range_1d_room=float(room_1d),
                                                same_bar_policy=same,
                                            )
                                            policies[policy.key()] = policy
    return list(policies.values())


def score_summary(summary: Mapping[str, Any], metric: str) -> float:
    if int(summary.get("trades", 0)) <= 0:
        return -1e12
    if metric == "profit_factor":
        return float(summary.get("profit_factor", 0.0))
    if metric == "total_pnl":
        return float(summary.get("total_cash_pnl", 0.0))
    return float(summary.get("total_cash_pnl", 0.0)) - 0.25 * float(summary.get("max_drawdown_cash", 0.0))


def replay_policy(
    predictions: pd.DataFrame,
    flat: pd.DataFrame,
    policy: BracketPolicy,
    args: argparse.Namespace,
) -> tuple[GeometrySummary, list[dict[str, Any]]]:
    ns = policy_namespace(policy, args)
    allowed_sides = {item.strip().upper() for item in str(args.allowed_sides).split(",") if item.strip()}
    balance = float(args.initial_capital)
    open_until = -1
    trades: list[dict[str, Any]] = []
    counters = {
        "skipped_by_model": 0,
        "skipped_while_open": 0,
        "skipped_side_filter": 0,
        "skipped_range_unavailable": 0,
        "skipped_range_filter": 0,
        "invalid_bracket": 0,
        "invalid_trade": 0,
    }
    min_sl_hits = 0
    min_tp_hits = 0
    tp_distances: list[float] = []
    sl_distances: list[float] = []
    for offset, row in predictions.reset_index(drop=True).iterrows():
        row_id = int(safe_float(row.get("row_id", -1), -1))
        if row_id < 0 or row_id >= len(flat):
            counters["invalid_trade"] += 1
            continue
        side = side_to_action(row.get("selected_action", ""))
        side_name = "BUY" if side == ACTION_BUY else "SELL" if side == ACTION_SELL else "NONE"
        if side < 0:
            counters["skipped_by_model"] += 1
            continue
        if side_name not in allowed_sides:
            counters["skipped_side_filter"] += 1
            continue
        if row_id <= open_until:
            counters["skipped_while_open"] += 1
            continue
        flat_row = flat.iloc[row_id]
        close = safe_float(flat_row.get("close", row.get("close", 0.0)), 0.0)
        atr_value = safe_float(flat_row.get("h4_atr_for_risk", 0.0), 0.0)
        entry = entry_price_for_row(flat, row_id, side, ns)
        if entry is None or atr_value <= 0:
            counters["invalid_trade"] += 1
            continue
        range_record = prediction_range_record(row)
        if policy.range_bracket_mode != "atr":
            if range_record.get("range_4h_available", 0.0) < 0.5:
                if policy.range_fallback == "atr":
                    distances = (*atr_distances(atr_value, ns), "atr_fallback")
                else:
                    counters["skipped_range_unavailable"] += 1
                    continue
            elif not range_filter_pass(range_record, close, side, ns):
                counters["skipped_range_filter"] += 1
                continue
            else:
                distances = range_distances(range_record, side, float(entry), atr_value, ns)
                if distances is None and policy.range_fallback == "atr":
                    distances = (*atr_distances(atr_value, ns), "atr_fallback")
        else:
            distances = range_distances(range_record, side, float(entry), atr_value, ns)
        if distances is None:
            counters["invalid_bracket"] += 1
            continue
        tp_distance, sl_distance, bracket_source = distances
        if abs(float(tp_distance) - float(policy.min_tp_distance)) <= 1e-9:
            min_tp_hits += 1
        if abs(float(sl_distance) - float(policy.min_sl_distance)) <= 1e-9:
            min_sl_hits += 1
        path = trade_path(flat, row_id, side, tp_distance, sl_distance, int(args.hold_bars), ns)
        if path is None:
            counters["invalid_trade"] += 1
            continue
        points, entry_row, exit_row, entry_price, tp, sl, exit_price, outcome = path
        risk_amount = max(balance * float(args.risk_per_trade), 0.0)
        quantity = risk_amount / sl_distance if sl_distance else 0.0
        cash_pnl = float(points) * quantity
        balance += cash_pnl
        tp_distances.append(float(tp_distance))
        sl_distances.append(float(sl_distance))
        trade = {
            "number": len(trades) + 1,
            "timestamp": str(row.get("timestamp", flat_row.get("timestamp", ""))),
            "side": side_name,
            "row_id": row_id,
            "entry_row_id": int(entry_row),
            "exit_row_id": int(exit_row),
            "entry": float(entry_price),
            "tp": float(tp),
            "sl": float(sl),
            "exit_price": float(exit_price),
            "tp_distance": float(tp_distance),
            "sl_distance": float(sl_distance),
            "points_pnl": float(points),
            "cash_pnl": float(cash_pnl),
            "balance": float(balance),
            "outcome": str(outcome),
            "bracket_source": str(bracket_source),
            "policy_key": policy.key(),
        }
        trades.append(trade)
        open_until = max(open_until, int(exit_row))
        if balance <= 0:
            break
    pnls = [float(trade["cash_pnl"]) for trade in trades]
    balances = [float(args.initial_capital), *[float(trade["balance"]) for trade in trades]]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    side_rows = summarize_side(trades)
    monthly_rows = summarize_monthly(trades)
    side_pnl = {str(row["side"]): float(row["cash_pnl"]) for row in side_rows}
    side_trades = {str(row["side"]): int(row["trades"]) for row in side_rows}
    monthly_pnl = {str(row["month"]): float(row["cash_pnl"]) for row in monthly_rows}
    trades_count = len(trades)
    summary_payload = {
        "trades": trades_count,
        "total_cash_pnl": sum(pnls),
        "profit_factor": gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        "max_drawdown_cash": max_drawdown(balances),
    }
    pass_gate = int(
        trades_count >= int(args.min_trades)
        and summary_payload["profit_factor"] >= float(args.pass_min_profit_factor)
        and balances[-1] >= float(args.pass_min_final_balance)
        and summary_payload["max_drawdown_cash"] <= float(args.pass_max_drawdown)
    )
    summary = GeometrySummary(
        policy_key=policy.key(),
        rank=0,
        score=score_summary(summary_payload, args.score_metric),
        range_bracket_mode=policy.range_bracket_mode,
        range_fallback=policy.range_fallback,
        use_1d_tp_cap=policy.use_1d_tp_cap,
        min_tp_distance=float(policy.min_tp_distance),
        min_sl_distance=float(policy.min_sl_distance),
        max_tp_atr=float(policy.max_tp_atr),
        max_sl_atr=float(policy.max_sl_atr),
        min_range_4h_room=float(policy.min_range_4h_room),
        min_range_1d_room=float(policy.min_range_1d_room),
        same_bar_policy=policy.same_bar_policy,
        trades=trades_count,
        buy_trades=side_trades.get("BUY", 0),
        sell_trades=side_trades.get("SELL", 0),
        wins=sum(1 for value in pnls if value > 0),
        losses=sum(1 for value in pnls if value < 0),
        win_rate=sum(1 for value in pnls if value > 0) / trades_count if trades_count else 0.0,
        total_cash_pnl=sum(pnls),
        buy_cash_pnl=side_pnl.get("BUY", 0.0),
        sell_cash_pnl=side_pnl.get("SELL", 0.0),
        final_balance=balances[-1],
        return_percent=(balances[-1] - float(args.initial_capital)) / float(args.initial_capital),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=summary_payload["profit_factor"],
        max_drawdown_cash=summary_payload["max_drawdown_cash"],
        take_profits=sum(1 for trade in trades if trade["outcome"] == "take_profit"),
        stop_losses=sum(1 for trade in trades if trade["outcome"] == "stop_loss"),
        timeouts=sum(1 for trade in trades if trade["outcome"] == "timeout"),
        stop_loss_rate=sum(1 for trade in trades if trade["outcome"] == "stop_loss") / trades_count if trades_count else 0.0,
        take_profit_rate=sum(1 for trade in trades if trade["outcome"] == "take_profit") / trades_count if trades_count else 0.0,
        timeout_rate=sum(1 for trade in trades if trade["outcome"] == "timeout") / trades_count if trades_count else 0.0,
        skipped_by_model=int(counters["skipped_by_model"]),
        skipped_while_open=int(counters["skipped_while_open"]),
        skipped_side_filter=int(counters["skipped_side_filter"]),
        skipped_range_unavailable=int(counters["skipped_range_unavailable"]),
        skipped_range_filter=int(counters["skipped_range_filter"]),
        invalid_bracket=int(counters["invalid_bracket"]),
        invalid_trade=int(counters["invalid_trade"]),
        min_sl_hits=min_sl_hits,
        min_tp_hits=min_tp_hits,
        avg_tp_distance=float(np.mean(tp_distances)) if tp_distances else 0.0,
        avg_sl_distance=float(np.mean(sl_distances)) if sl_distances else 0.0,
        median_tp_distance=float(np.median(tp_distances)) if tp_distances else 0.0,
        median_sl_distance=float(np.median(sl_distances)) if sl_distances else 0.0,
        positive_months=sum(1 for value in monthly_pnl.values() if value > 0),
        negative_months=sum(1 for value in monthly_pnl.values() if value < 0),
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


def render_html(title: str, report: GeometryReport) -> str:
    rows = "".join(
        f"<tr><td>{row.get('rank')}</td><td>{html.escape(str(row.get('policy_key')))}</td>"
        f"<td>{float(row.get('total_cash_pnl', 0.0)):.3f}</td>"
        f"<td>{float(row.get('profit_factor', 0.0)):.3f}</td>"
        f"<td>{int(row.get('trades', 0))}</td>"
        f"<td>{float(row.get('max_drawdown_cash', 0.0)):.3f}</td></tr>"
        for row in report.top_policies[:20]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase150A bracket geometry audit. Research only.</p>
<p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Best policy</h2><pre>{html.escape(json.dumps(report.best_policy, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Top policies</h2><table><thead><tr><th>Rank</th><th>Policy</th><th>PnL</th><th>PF</th><th>Trades</th><th>Max DD</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE150A RANGE BRACKET GEOMETRY AUDIT")
        print("=" * 74)
        predictions_path = Path(args.predictions_path)
        flat_path = Path(args.flat_path)
        print(f"  predictions : {predictions_path}")
        print(f"  flat        : {flat_path}")
        predictions = read_frame(predictions_path).reset_index(drop=True)
        flat = read_frame(flat_path).reset_index(drop=True)
        policies = build_policies(args)
        summaries: list[GeometrySummary] = []
        best_trades: list[dict[str, Any]] = []
        best_score = -1e18
        for index, policy in enumerate(policies, start=1):
            summary, trades = replay_policy(predictions, flat, policy, args)
            if summary.trades < int(args.min_trades):
                score = -1e12 + summary.trades
            else:
                score = summary.score
            summary = GeometrySummary(**{**asdict(summary), "score": float(score)})
            summaries.append(summary)
            if score > best_score:
                best_score = score
                best_trades = trades
            if index % 25 == 0 or index == len(policies):
                print(f"  checked {index}/{len(policies)} policies")
        ranked = sorted(summaries, key=lambda item: (item.score, item.total_cash_pnl), reverse=True)
        ranked = [GeometrySummary(**{**asdict(item), "rank": rank}) for rank, item in enumerate(ranked, start=1)]
        best = ranked[0] if ranked else None
        baseline_atr = next((item for item in ranked if item.range_bracket_mode == "atr"), None)
        grid_csv = output_dir / "latest_grid.csv"
        best_trades_csv = output_dir / "latest_best_trades.csv"
        write_csv(grid_csv, [asdict(row) for row in ranked])
        write_csv(best_trades_csv, best_trades)
        report = GeometryReport(
            predictions_path=str(predictions_path),
            flat_path=str(flat_path),
            split_name=str(args.split_name),
            evaluated_rows=len(predictions),
            policies_evaluated=len(ranked),
            min_trades=int(args.min_trades),
            score_metric=str(args.score_metric),
            best_policy=asdict(best) if best else {},
            baseline_atr_policy=asdict(baseline_atr) if baseline_atr else {},
            top_policies=[asdict(row) for row in ranked[:25]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_grid_csv=str(grid_csv),
            output_best_trades_csv=str(best_trades_csv),
            production_status="BLOCKED — research bracket geometry audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Range bracket geometry audit complete")
        print(f"  policies : {len(ranked)}")
        if best:
            print(f"  best     : {best.policy_key}")
            print(f"  pnl/PF   : {best.total_cash_pnl:.4f} / {best.profit_factor:.4f}")
        print(f"  output   : {report.output_json}")
        print(f"  elapsed  : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
