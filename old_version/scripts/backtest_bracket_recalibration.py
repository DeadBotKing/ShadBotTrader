"""Phase139A: replay alternative TP/SL bracket policies on hybrid candidates.

This phase does not train a model. It re-simulates the already-built Phase127
candidate stream with modified TP/SL geometry so we can test whether bracket
construction, not only model quality, is the main failure source.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_xgboost_head import load_candles, spread_abs
from report_hybrid_full_backtest import (
    DetailedTrade,
    FixedBacktestSummary,
    account_summary,
    monthly_summary,
    safe_div,
)
from train_hybrid_meta_labeler import default_flat_path

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/bracket_recalibration")
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class BracketPolicy:
    name: str
    max_tp_distance: float | None
    max_sl_distance: float | None
    max_reward_risk: float | None


@dataclass(frozen=True)
class BracketBacktestCounters:
    skipped_no_candidate: int
    skipped_side: int
    skipped_while_open: int
    invalid_bracket: int

    @property
    def no_trade(self) -> int:
        return (
            self.skipped_no_candidate
            + self.skipped_side
            + self.skipped_while_open
            + self.invalid_bracket
        )


@dataclass(frozen=True)
class PolicyRow:
    policy: str
    max_tp_distance: str
    max_sl_distance: str
    max_reward_risk: str
    samples: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    timeouts: int
    skipped_side: int
    skipped_while_open: int
    invalid_bracket: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    coverage: float
    final_balance: float
    net_profit: float
    return_percent: float
    would_breach_zero: bool
    score: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay alternative TP/SL bracket caps on hybrid telemetry candidates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--allowed-sides", default="BUY,SELL")
    parser.add_argument("--max-tp-distances", default="original,12,14,16,18")
    parser.add_argument("--max-sl-distances", default="original,20,23.56,30")
    parser.add_argument("--max-reward-risks", default="original,1.0,1.5,2.0")
    parser.add_argument("--buy-max-tp-distance", type=float, default=-1.0)
    parser.add_argument("--buy-max-sl-distance", type=float, default=-1.0)
    parser.add_argument("--buy-max-reward-risk", type=float, default=-1.0)
    parser.add_argument("--sell-max-tp-distance", type=float, default=-1.0)
    parser.add_argument("--sell-max-sl-distance", type=float, default=-1.0)
    parser.add_argument("--sell-max-reward-risk", type=float, default=-1.0)
    parser.add_argument("--min-tp-distance", type=float, default=0.1)
    parser.add_argument("--min-sl-distance", type=float, default=0.1)
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument(
        "--max-policies", type=int, default=0, help="0 = evaluate every grid policy"
    )
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="TP/SL bracket recalibration replay")
    return parser.parse_args(argv)


def cap_label(value: float | None) -> str:
    return "original" if value is None else f"{float(value):g}"


def parse_cap_options(text: str) -> list[float | None]:
    values: list[float | None] = []
    for raw in (part.strip().lower() for part in text.split(",")):
        if not raw:
            continue
        if raw in {"original", "none", "off", "-1"}:
            value: float | None = None
        else:
            value = float(raw)
            if value < 0:
                value = None
        if value not in values:
            values.append(value)
    return values or [None]


def build_policies(args: argparse.Namespace) -> list[BracketPolicy]:
    policies: list[BracketPolicy] = []
    for tp_cap in parse_cap_options(args.max_tp_distances):
        for sl_cap in parse_cap_options(args.max_sl_distances):
            for rr_cap in parse_cap_options(args.max_reward_risks):
                name = f"tp={cap_label(tp_cap)}:sl={cap_label(sl_cap)}:rr={cap_label(rr_cap)}"
                policies.append(BracketPolicy(name, tp_cap, sl_cap, rr_cap))
    if args.max_policies > 0:
        return policies[: args.max_policies]
    return policies


def parse_sides(text: str) -> set[str]:
    sides = {item.strip().upper() for item in text.split(",") if item.strip()}
    return sides or {"BUY", "SELL"}


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def prepare_frame(frame: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    result = frame.replace([np.inf, -np.inf], 0.0).fillna(0.0).copy()
    result["timestamp_dt"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["month"] = result["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
    if args.start_month:
        result = result[result["month"] >= args.start_month].copy()
    if args.end_month:
        result = result[result["month"] <= args.end_month].copy()
    result["side"] = np.where(result["target_side"].astype(float) >= 0, "BUY", "SELL")
    return result.reset_index(drop=True)


def side_specific_cap(
    side: str, global_cap: float | None, buy_cap: float, sell_cap: float
) -> float | None:
    selected = buy_cap if side == "BUY" else sell_cap
    if selected >= 0:
        return selected if global_cap is None else min(float(global_cap), float(selected))
    return global_cap


def recalibrated_distances(
    row: pd.Series, policy: BracketPolicy, args: argparse.Namespace
) -> tuple[float, float] | None:
    side = "BUY" if float(row.get("target_side", 0.0)) >= 0 else "SELL"
    tp_distance = float(row.get("candidate_tp_distance", 0.0) or 0.0)
    sl_distance = float(row.get("candidate_sl_distance", 0.0) or 0.0)
    if tp_distance <= 0 or sl_distance <= 0:
        return None
    max_tp = side_specific_cap(
        side, policy.max_tp_distance, args.buy_max_tp_distance, args.sell_max_tp_distance
    )
    max_sl = side_specific_cap(
        side, policy.max_sl_distance, args.buy_max_sl_distance, args.sell_max_sl_distance
    )
    max_rr = side_specific_cap(
        side, policy.max_reward_risk, args.buy_max_reward_risk, args.sell_max_reward_risk
    )
    if max_tp is not None:
        tp_distance = min(tp_distance, float(max_tp))
    if max_sl is not None:
        sl_distance = min(sl_distance, float(max_sl))
    if max_rr is not None:
        tp_distance = min(tp_distance, sl_distance * float(max_rr))
    if tp_distance < args.min_tp_distance or sl_distance < args.min_sl_distance:
        return None
    return float(tp_distance), float(sl_distance)


def bracket_prices(
    entry: float, side: str, tp_distance: float, sl_distance: float
) -> tuple[float, float]:
    if side == "BUY":
        return entry + tp_distance, entry - sl_distance
    return entry - tp_distance, entry + sl_distance


def simulate_recalibrated_trade(
    row: pd.Series,
    candles: Sequence[Any],
    policy: BracketPolicy,
    args: argparse.Namespace,
    number: int,
    equity: float,
) -> DetailedTrade | None:
    source_index = int(row.get("source_index", -1))
    entry_index = source_index + 1
    if entry_index >= len(candles):
        return None
    side = "BUY" if float(row.get("target_side", 0.0)) >= 0 else "SELL"
    entry = float(row.get("candidate_entry_price", 0.0) or 0.0)
    if entry <= 0:
        entry = float(candles[entry_index].open.amount)
    distances = recalibrated_distances(row, policy, args)
    if distances is None:
        return None
    tp_distance, sl_distance = distances
    tp, sl = bracket_prices(entry, side, tp_distance, sl_distance)
    max_exit = min(len(candles) - 1, entry_index + max(args.max_hold_bars, 1) - 1)
    exit_index = max_exit
    exit_price = float(candles[max_exit].close.amount)
    outcome = "timeout"
    for index in range(entry_index, max_exit + 1):
        candle = candles[index]
        close_for_spread = float(candle.close.amount)
        half = spread_abs(close_for_spread, args.spread_mode, args.spread_value) / 2.0
        if side == "BUY":
            high_exit = float(candle.high.amount) - half
            low_exit = float(candle.low.amount) - half
            hit_tp = high_exit >= tp
            hit_sl = low_exit <= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_index = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_index = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_index = index
                break
        else:
            low_exit = float(candle.low.amount) + half
            high_exit = float(candle.high.amount) + half
            hit_tp = low_exit <= tp
            hit_sl = high_exit >= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_index = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_index = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_index = index
                break
    if outcome == "timeout":
        half = spread_abs(exit_price, args.spread_mode, args.spread_value) / 2.0
        exit_price = exit_price - half if side == "BUY" else exit_price + half
    pnl = exit_price - entry if side == "BUY" else entry - exit_price
    new_equity = equity + pnl
    return DetailedTrade(
        number=number,
        timestamp=str(row.get("timestamp", "")),
        side=side,
        row_index=int(row.name) if row.name is not None else -1,
        source_index=source_index,
        entry_index=entry_index,
        exit_index=exit_index,
        entry=entry,
        tp=tp,
        sl=sl,
        exit_price=exit_price,
        outcome=outcome,
        pnl=pnl,
        equity=new_equity,
        label="win" if pnl > 0 else "loss",
        label_correct=1 if pnl > 0 else 0,
    )


def max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += float(pnl)
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def summary_from_trades(
    samples: int, trades: Sequence[DetailedTrade], counters: BracketBacktestCounters
) -> FixedBacktestSummary:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    return FixedBacktestSummary(
        samples=samples,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        timeouts=sum(1 for trade in trades if trade.outcome == "timeout"),
        label_correct=wins,
        false_positive=losses,
        no_trade=max(samples - len(trades), counters.no_trade),
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=counters.invalid_bracket,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(wins, len(trades)),
        total_pnl=sum(pnls),
        avg_pnl=safe_div(sum(pnls), len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        coverage=safe_div(len(trades), samples),
    )


def backtest_policy(
    frame: pd.DataFrame, candles: Sequence[Any], policy: BracketPolicy, args: argparse.Namespace
) -> tuple[FixedBacktestSummary, BracketBacktestCounters, list[DetailedTrade]]:
    allowed_sides = parse_sides(args.allowed_sides)
    skipped_no_candidate = skipped_side = skipped_while_open = invalid_bracket = 0
    open_until = -1
    equity = 0.0
    trades: list[DetailedTrade] = []
    for _, row in frame.iterrows():
        source_index = int(row.get("source_index", -1))
        if source_index <= open_until:
            skipped_while_open += 1
            continue
        if float(row.get("candidate_mask", 0.0)) < 0.5:
            skipped_no_candidate += 1
            continue
        side = "BUY" if float(row.get("target_side", 0.0)) >= 0 else "SELL"
        if side not in allowed_sides:
            skipped_side += 1
            continue
        trade = simulate_recalibrated_trade(row, candles, policy, args, len(trades) + 1, equity)
        if trade is None:
            invalid_bracket += 1
            continue
        trades.append(trade)
        equity = trade.equity
        open_until = max(open_until, trade.exit_index)
    counters = BracketBacktestCounters(
        skipped_no_candidate=skipped_no_candidate,
        skipped_side=skipped_side,
        skipped_while_open=skipped_while_open,
        invalid_bracket=invalid_bracket,
    )
    return summary_from_trades(len(frame), trades, counters), counters, trades


def score_value(summary: FixedBacktestSummary, account: Mapping[str, Any], metric: str) -> float:
    if metric == "profit_factor":
        return summary.profit_factor
    if metric == "final_balance":
        return float(account["final_balance"])
    if metric == "drawdown_adjusted":
        return summary.total_pnl - summary.max_drawdown
    return summary.total_pnl


def row_from_policy(
    policy: BracketPolicy,
    summary: FixedBacktestSummary,
    counters: BracketBacktestCounters,
    account: Mapping[str, Any],
    args: argparse.Namespace,
) -> PolicyRow:
    return PolicyRow(
        policy=policy.name,
        max_tp_distance=cap_label(policy.max_tp_distance),
        max_sl_distance=cap_label(policy.max_sl_distance),
        max_reward_risk=cap_label(policy.max_reward_risk),
        samples=summary.samples,
        trades=summary.trades,
        buy_trades=summary.buy_trades,
        sell_trades=summary.sell_trades,
        wins=summary.wins,
        losses=summary.losses,
        timeouts=summary.timeouts,
        skipped_side=counters.skipped_side,
        skipped_while_open=counters.skipped_while_open,
        invalid_bracket=counters.invalid_bracket,
        win_rate=summary.win_rate,
        total_pnl=summary.total_pnl,
        avg_pnl=summary.avg_pnl,
        gross_profit=summary.gross_profit,
        gross_loss=summary.gross_loss,
        profit_factor=summary.profit_factor,
        max_drawdown=summary.max_drawdown,
        coverage=summary.coverage,
        final_balance=float(account["final_balance"]),
        net_profit=float(account["net_profit"]),
        return_percent=float(account["return_percent"]),
        would_breach_zero=bool(account["would_breach_zero"]),
        score=(
            score_value(summary, account, args.score_metric)
            if summary.trades >= args.min_trades
            else -1e18
        ),
    )


def select_best(rows: Sequence[PolicyRow]) -> PolicyRow:
    valid = [row for row in rows if row.score > -1e17]
    return max(valid or list(rows), key=lambda row: row.score)


def write_csv(path: Path, rows: Sequence[PolicyRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_trades_csv(path: Path, trades: Sequence[DetailedTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not trades:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(trades[0]).keys()))
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def render_html(
    title: str, rows: Sequence[PolicyRow], best: PolicyRow, monthly: Sequence[Any]
) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.policy)}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.buy_trades:,}/{row.sell_trades:,}</td>"
        f"<td>{row.win_rate:.2%}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.max_drawdown:.2f}</td>"
        f"<td>{row.final_balance:.2f}</td>"
        "</tr>"
        for row in sorted(rows, key=lambda item: item.score, reverse=True)[:50]
    )
    monthly_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.month))}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.wins:,}</td>"
        f"<td>{row.losses:,}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        "</tr>"
        for row in monthly
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1400px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:12px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:8px; }} th {{ color:#bae6fd; }}
pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:12px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase139A re-simulates TP/SL caps on existing candidates. It is diagnostic only.</p></section>
<section class="card"><h2>Best policy</h2><pre>{html.escape(json.dumps(asdict(best), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Top policies</h2><table><thead><tr><th>policy</th><th>trades</th><th>buy/sell</th><th>win</th><th>pnl</th><th>PF</th><th>DD</th><th>final</th></tr></thead><tbody>{body}</tbody></table></section>
<section class="card"><h2>Best policy monthly</h2><table><thead><tr><th>month</th><th>trades</th><th>wins</th><th>losses</th><th>pnl</th><th>PF</th></tr></thead><tbody>{monthly_rows}</tbody></table></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    storage_root = Path(args.storage_root)
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE139A TP/SL BRACKET RECALIBRATION REPLAY")
        print("=" * 74)
        print(f"  flat        : {flat_path}")
        frame_all = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        frame_all["timestamp_dt"] = pd.to_datetime(
            frame_all["timestamp"], utc=True, errors="coerce"
        )
        frame_all["month"] = frame_all["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
        if args.start_month:
            frame_all = frame_all[frame_all["month"] >= args.start_month].copy()
        if args.end_month:
            frame_all = frame_all[frame_all["month"] <= args.end_month].copy()
        if frame_all.empty:
            raise RuntimeError("No rows left after month filter")
        indices = eval_indices(len(frame_all), args.eval_frac, args.max_windows)
        frame = frame_all.iloc[indices].copy().reset_index(drop=True)
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        rows: list[PolicyRow] = []
        policies = build_policies(args)
        print(f"  policies    : {len(policies):,}")
        for policy in policies:
            summary, counters, _trades = backtest_policy(frame, candles, policy, args)
            account = account_summary(summary, args.initial_capital, args.units)
            rows.append(row_from_policy(policy, summary, counters, account, args))
        if not rows:
            raise RuntimeError("No policies evaluated")
        best = select_best(rows)
        best_policy = next(policy for policy in policies if policy.name == best.policy)
        best_summary, best_counters, best_trades = backtest_policy(
            frame, candles, best_policy, args
        )
        monthly = monthly_summary(best_trades)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "latest.csv"
        json_path = output_dir / "latest.json"
        html_path = output_dir / "latest.html"
        trades_path = output_dir / "best_trades.csv"
        write_csv(csv_path, rows)
        write_trades_csv(trades_path, best_trades)
        html_path.write_text(render_html(args.report_title, rows, best, monthly), encoding="utf-8")
        payload = {
            "args": vars(args),
            "rows": [asdict(row) for row in rows],
            "best": asdict(best),
            "best_summary": asdict(best_summary),
            "best_counters": asdict(best_counters),
            "best_monthly": [asdict(row) for row in monthly],
            "files": {
                "json": str(json_path),
                "html": str(html_path),
                "csv": str(csv_path),
                "best_trades_csv": str(trades_path),
            },
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  best        : {best.policy}")
        print(f"  trades      : {best.trades:,}")
        print(f"  total pnl   : {best.total_pnl:+.2f}")
        print(f"  PF          : {best.profit_factor:.3f}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
