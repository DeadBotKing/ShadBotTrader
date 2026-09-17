"""Phase140A: audit candidate direction and delayed-entry counterfactuals.

This diagnostic phase does not train a model and does not approve production.
It replays the existing Phase127 hybrid telemetry candidate stream under two
counterfactual dimensions:

* side_mode: original candidate side vs BUY/SELL flipped side
* entry_delay_bars: enter after source_index + 1 + delay bars

The goal is to separate three failure causes:

* wrong/contrarian candidate direction,
* poor entry timing,
* or a candidate stream that has no stable edge even after flip/delay.
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
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/candidate_direction_entry_audit")
SIDE_MODES = ("original", "flipped")
EXECUTION_MODES = ("independent", "chronological")
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def spread_abs(price: float, mode: str, value: float) -> float:
    if mode == "fixed":
        return max(0.0, value)
    return max(0.0, price * value / 100.0)


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    """Lazy candle loader so helper tests can import this script without PyArrow.

    The real dashboard/runtime still uses the existing infrastructure store.
    Imports stay inside this function because some unit tests only exercise
    pure replay math in environments where optional parquet dependencies are
    not installed.
    """
    try:
        from ShadBotTrader.data_cli import build_service as build_data_service
        from ShadBotTrader.domain.market.symbol import Symbol
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.infrastructure.data.symbol_scope import (
            resolve_stored_symbol,
            stored_symbols,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not load candles because an optional data dependency is missing. "
            "Install the project data requirements, then rerun Phase140A."
        ) from exc

    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    return sorted(
        store.query(Symbol(resolved.resolved), Timeframe(timeframe)),
        key=lambda candle: candle.open_time.value,
    )


@dataclass(frozen=True)
class AuditCounters:
    skipped_no_candidate: int
    skipped_side: int
    skipped_while_open: int
    invalid_bracket: int
    missing_future: int

    @property
    def no_trade(self) -> int:
        return (
            self.skipped_no_candidate
            + self.skipped_side
            + self.skipped_while_open
            + self.invalid_bracket
            + self.missing_future
        )


@dataclass(frozen=True)
class AuditTrade:
    number: int
    scenario: str
    execution_mode: str
    side_mode: str
    entry_delay_bars: int
    timestamp: str
    month: str
    hour: int
    original_side: str
    executed_side: str
    row_index: int
    source_index: int
    entry_index: int
    exit_index: int
    entry: float
    tp: float
    sl: float
    exit_price: float
    outcome: str
    pnl: float
    score_r: float
    equity: float


@dataclass(frozen=True)
class ScenarioRow:
    scenario: str
    execution_mode: str
    side_mode: str
    entry_delay_bars: int
    samples: int
    source_candidates: int
    trades: int
    buy_trades: int
    sell_trades: int
    original_buy_trades: int
    original_sell_trades: int
    flipped_buy_to_sell_trades: int
    flipped_sell_to_buy_trades: int
    wins: int
    losses: int
    timeouts: int
    take_profits: int
    stop_losses: int
    skipped_no_candidate: int
    skipped_side: int
    skipped_while_open: int
    invalid_bracket: int
    missing_future: int
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


@dataclass(frozen=True)
class GroupRow:
    section: str
    bucket: str
    execution_mode: str
    side_mode: str
    entry_delay_bars: int
    scenario: str
    trades: int
    buy_trades: int
    sell_trades: int
    original_buy_trades: int
    original_sell_trades: int
    wins: int
    losses: int
    timeouts: int
    take_profits: int
    stop_losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    share_of_scenario_trades: float


@dataclass(frozen=True)
class AuditReport:
    flat_path: str
    evaluated_rows: int
    candidate_rows: int
    scenarios: int
    best_independent_scenario: str
    best_independent_total_pnl: float
    best_independent_profit_factor: float
    best_chronological_scenario: str
    best_chronological_total_pnl: float
    best_chronological_profit_factor: float
    original_delay0_independent_pnl: float
    flipped_delay0_independent_pnl: float
    original_delay0_chronological_pnl: float
    flipped_delay0_chronological_pnl: float
    diagnostic_findings: list[str]
    production_status: str
    output_json: str
    output_html: str
    output_csv: str
    output_groups_csv: str
    output_best_trades_csv: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit original vs flipped candidate direction and delayed entry timing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--allowed-sides", default="BUY,SELL")
    parser.add_argument("--entry-delays", default="0,1,2,3")
    parser.add_argument("--side-modes", default="original,flipped")
    parser.add_argument("--execution-modes", default="independent,chronological")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-tp-distance", type=float, default=0.1)
    parser.add_argument("--min-sl-distance", type=float, default=0.1)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--min-group-trades", type=int, default=5)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Candidate direction / entry audit")
    return parser.parse_args(argv)


def parse_sides(text: str) -> set[str]:
    sides = {item.strip().upper() for item in text.split(",") if item.strip()}
    return sides or {"BUY", "SELL"}


def parse_entry_delays(text: str) -> list[int]:
    delays: list[int] = []
    for raw in (part.strip() for part in text.split(",")):
        if not raw:
            continue
        value = max(int(raw), 0)
        if value not in delays:
            delays.append(value)
    return delays or [0]


def parse_choice_list(text: str, allowed: Sequence[str], default: Sequence[str]) -> list[str]:
    values: list[str] = []
    allowed_set = set(allowed)
    for raw in (part.strip().lower() for part in text.split(",")):
        if raw in allowed_set and raw not in values:
            values.append(raw)
    return values or list(default)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def original_side_for_row(row: pd.Series) -> str:
    candidate_side = safe_float(row.get("candidate_side", 0.0))
    target_side = safe_float(row.get("target_side", 0.0))
    side_value = candidate_side if abs(candidate_side) > 1e-9 else target_side
    return "BUY" if side_value >= 0 else "SELL"


def executed_side(original_side: str, side_mode: str) -> str:
    if side_mode == "flipped":
        return "SELL" if original_side == "BUY" else "BUY"
    return original_side


def scenario_name(execution_mode: str, side_mode: str, delay: int) -> str:
    return f"{execution_mode}:{side_mode}:delay={delay}"


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def prepare_frame(frame: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, int]:
    result = frame.replace([np.inf, -np.inf], 0.0).fillna(0.0).copy()
    result["timestamp_dt"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["month"] = result["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
    result["hour"] = result["timestamp_dt"].dt.hour.fillna(-1).astype(int)
    if args.start_month:
        result = result[result["month"] >= args.start_month].copy()
    if args.end_month:
        result = result[result["month"] <= args.end_month].copy()
    if result.empty:
        raise RuntimeError("No rows left after month filters")
    indices = eval_indices(len(result), args.eval_frac, args.max_windows)
    evaluated = result.iloc[indices].copy().reset_index(drop=True)
    evaluated_rows = len(evaluated)
    evaluated["original_side"] = evaluated.apply(original_side_for_row, axis=1)
    if args.candidate_only == "1":
        if "candidate_mask" not in evaluated.columns:
            raise RuntimeError("candidate-only audit needs candidate_mask column")
        evaluated = evaluated[evaluated["candidate_mask"].astype(float) >= 0.5].copy()
    allowed_sides = parse_sides(args.allowed_sides)
    evaluated = evaluated[evaluated["original_side"].isin(allowed_sides)].copy()
    return evaluated.reset_index(drop=True), evaluated_rows


def candidate_distances(row: pd.Series) -> tuple[float, float] | None:
    entry = safe_float(row.get("candidate_entry_price", 0.0))
    tp = safe_float(row.get("candidate_tp_distance", 0.0))
    sl = safe_float(row.get("candidate_sl_distance", 0.0))
    if tp <= 0 and entry > 0:
        take_profit = safe_float(row.get("candidate_take_profit", 0.0))
        tp = abs(take_profit - entry) if take_profit > 0 else 0.0
    if sl <= 0 and entry > 0:
        stop_loss = safe_float(row.get("candidate_stop_loss", 0.0))
        sl = abs(entry - stop_loss) if stop_loss > 0 else 0.0
    if tp <= 0 or sl <= 0:
        return None
    return float(tp), float(sl)


def bracket_prices(
    entry: float, side: str, tp_distance: float, sl_distance: float
) -> tuple[float, float]:
    if side == "BUY":
        return entry + tp_distance, entry - sl_distance
    return entry - tp_distance, entry + sl_distance


def entry_price_for_side(raw_open: float, side: str, args: argparse.Namespace) -> float:
    half_spread = spread_abs(raw_open, args.spread_mode, args.spread_value) / 2.0
    if side == "BUY":
        return raw_open + half_spread + max(args.slippage, 0.0)
    return raw_open - half_spread - max(args.slippage, 0.0)


def simulate_counterfactual_trade(
    row: pd.Series,
    candles: Sequence[Any],
    side_mode: str,
    entry_delay_bars: int,
    args: argparse.Namespace,
    number: int,
    equity: float,
    execution_mode: str = "independent",
) -> tuple[AuditTrade | None, str]:
    source_index = int(safe_float(row.get("source_index", -1), -1.0))
    entry_index = source_index + 1 + max(int(entry_delay_bars), 0)
    if source_index < 0 or entry_index >= len(candles):
        return None, "missing_future"
    distances = candidate_distances(row)
    if distances is None:
        return None, "invalid_bracket"
    tp_distance, sl_distance = distances
    if tp_distance < args.min_tp_distance or sl_distance < args.min_sl_distance:
        return None, "invalid_bracket"
    original_side = str(row.get("original_side", original_side_for_row(row)))
    side = executed_side(original_side, side_mode)
    raw_entry = float(candles[entry_index].open.amount)
    entry = entry_price_for_side(raw_entry, side, args)
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
    score_r = safe_div(pnl, sl_distance)
    new_equity = equity + pnl
    return (
        AuditTrade(
            number=number,
            scenario=scenario_name(execution_mode, side_mode, entry_delay_bars),
            execution_mode=execution_mode,
            side_mode=side_mode,
            entry_delay_bars=int(entry_delay_bars),
            timestamp=str(row.get("timestamp", "")),
            month=str(row.get("month", "unknown")),
            hour=int(safe_float(row.get("hour", -1), -1.0)),
            original_side=original_side,
            executed_side=side,
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
            score_r=float(score_r),
            equity=new_equity,
        ),
        "ok",
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


def account_values(
    total_pnl: float, max_dd: float, initial_capital: float, units: float
) -> dict[str, Any]:
    multiplier = max(float(units), 0.0)
    initial = float(initial_capital)
    final = initial + total_pnl * multiplier
    max_drawdown_cash = max_dd * multiplier
    return {
        "initial_capital": initial,
        "units": multiplier,
        "final_balance": final,
        "net_profit": final - initial,
        "return_percent": safe_div(final - initial, initial),
        "max_drawdown_cash": max_drawdown_cash,
        "would_breach_zero": initial - max_drawdown_cash <= 0,
        "note": "final_balance = initial_capital + total_pnl * units; margin calls are not simulated",
    }


def score_value(
    total_pnl: float, profit_factor_value: float, final_balance: float, drawdown: float, metric: str
) -> float:
    if metric == "profit_factor":
        return profit_factor_value
    if metric == "final_balance":
        return final_balance
    if metric == "drawdown_adjusted":
        return total_pnl - drawdown
    return total_pnl


def summarize_trade_metrics(trades: Sequence[AuditTrade]) -> dict[str, float | int]:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    pf = safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
    return {
        "trades": len(trades),
        "buy_trades": sum(1 for trade in trades if trade.executed_side == "BUY"),
        "sell_trades": sum(1 for trade in trades if trade.executed_side == "SELL"),
        "original_buy_trades": sum(1 for trade in trades if trade.original_side == "BUY"),
        "original_sell_trades": sum(1 for trade in trades if trade.original_side == "SELL"),
        "flipped_buy_to_sell_trades": sum(
            1
            for trade in trades
            if trade.side_mode == "flipped"
            and trade.original_side == "BUY"
            and trade.executed_side == "SELL"
        ),
        "flipped_sell_to_buy_trades": sum(
            1
            for trade in trades
            if trade.side_mode == "flipped"
            and trade.original_side == "SELL"
            and trade.executed_side == "BUY"
        ),
        "wins": wins,
        "losses": losses,
        "timeouts": sum(1 for trade in trades if trade.outcome == "timeout"),
        "take_profits": sum(1 for trade in trades if trade.outcome == "take_profit"),
        "stop_losses": sum(1 for trade in trades if trade.outcome == "stop_loss"),
        "win_rate": safe_div(wins, len(trades)),
        "total_pnl": float(sum(pnls)),
        "avg_pnl": safe_div(sum(pnls), len(trades)),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "profit_factor": float(pf),
        "max_drawdown": max_drawdown(pnls),
    }


def scenario_row_from_trades(
    scenario: str,
    execution_mode: str,
    side_mode: str,
    delay: int,
    samples: int,
    source_candidates: int,
    trades: Sequence[AuditTrade],
    counters: AuditCounters,
    args: argparse.Namespace,
) -> ScenarioRow:
    metrics = summarize_trade_metrics(trades)
    account = account_values(
        float(metrics["total_pnl"]),
        float(metrics["max_drawdown"]),
        args.initial_capital,
        args.units,
    )
    score = (
        score_value(
            float(metrics["total_pnl"]),
            float(metrics["profit_factor"]),
            float(account["final_balance"]),
            float(metrics["max_drawdown"]),
            args.score_metric,
        )
        if int(metrics["trades"]) >= args.min_trades
        else -1e18
    )
    return ScenarioRow(
        scenario=scenario,
        execution_mode=execution_mode,
        side_mode=side_mode,
        entry_delay_bars=delay,
        samples=samples,
        source_candidates=source_candidates,
        trades=int(metrics["trades"]),
        buy_trades=int(metrics["buy_trades"]),
        sell_trades=int(metrics["sell_trades"]),
        original_buy_trades=int(metrics["original_buy_trades"]),
        original_sell_trades=int(metrics["original_sell_trades"]),
        flipped_buy_to_sell_trades=int(metrics["flipped_buy_to_sell_trades"]),
        flipped_sell_to_buy_trades=int(metrics["flipped_sell_to_buy_trades"]),
        wins=int(metrics["wins"]),
        losses=int(metrics["losses"]),
        timeouts=int(metrics["timeouts"]),
        take_profits=int(metrics["take_profits"]),
        stop_losses=int(metrics["stop_losses"]),
        skipped_no_candidate=counters.skipped_no_candidate,
        skipped_side=counters.skipped_side,
        skipped_while_open=counters.skipped_while_open,
        invalid_bracket=counters.invalid_bracket,
        missing_future=counters.missing_future,
        win_rate=float(metrics["win_rate"]),
        total_pnl=float(metrics["total_pnl"]),
        avg_pnl=float(metrics["avg_pnl"]),
        gross_profit=float(metrics["gross_profit"]),
        gross_loss=float(metrics["gross_loss"]),
        profit_factor=float(metrics["profit_factor"]),
        max_drawdown=float(metrics["max_drawdown"]),
        coverage=safe_div(int(metrics["trades"]), samples),
        final_balance=float(account["final_balance"]),
        net_profit=float(account["net_profit"]),
        return_percent=float(account["return_percent"]),
        would_breach_zero=bool(account["would_breach_zero"]),
        score=float(score),
    )


def run_scenario(
    frame: pd.DataFrame,
    candles: Sequence[Any],
    execution_mode: str,
    side_mode: str,
    delay: int,
    args: argparse.Namespace,
) -> tuple[ScenarioRow, list[AuditTrade]]:
    skipped_no_candidate = skipped_side = skipped_while_open = invalid_bracket = missing_future = 0
    source_candidates = 0
    open_until = -1
    equity = 0.0
    trades: list[AuditTrade] = []
    allowed_sides = parse_sides(args.allowed_sides)
    for _, row in frame.iterrows():
        if float(row.get("candidate_mask", 0.0)) < 0.5:
            skipped_no_candidate += 1
            continue
        original_side = str(row.get("original_side", original_side_for_row(row)))
        if original_side not in allowed_sides:
            skipped_side += 1
            continue
        source_candidates += 1
        source_index = int(safe_float(row.get("source_index", -1), -1.0))
        if execution_mode == "chronological" and source_index <= open_until:
            skipped_while_open += 1
            continue
        trade, reason = simulate_counterfactual_trade(
            row,
            candles,
            side_mode,
            delay,
            args,
            len(trades) + 1,
            equity,
            execution_mode,
        )
        if trade is None:
            if reason == "missing_future":
                missing_future += 1
            else:
                invalid_bracket += 1
            continue
        trades.append(trade)
        equity = trade.equity
        if execution_mode == "chronological":
            open_until = max(open_until, trade.exit_index)
    counters = AuditCounters(
        skipped_no_candidate=skipped_no_candidate,
        skipped_side=skipped_side,
        skipped_while_open=skipped_while_open,
        invalid_bracket=invalid_bracket,
        missing_future=missing_future,
    )
    scenario = scenario_name(execution_mode, side_mode, delay)
    return (
        scenario_row_from_trades(
            scenario,
            execution_mode,
            side_mode,
            delay,
            len(frame),
            source_candidates,
            trades,
            counters,
            args,
        ),
        trades,
    )


def select_best(rows: Sequence[ScenarioRow], execution_mode: str) -> ScenarioRow:
    subset = [row for row in rows if row.execution_mode == execution_mode]
    valid = [row for row in subset if row.score > -1e17]
    return max(valid or subset or list(rows), key=lambda row: row.score)


def lookup_scenario(
    rows: Sequence[ScenarioRow], execution_mode: str, side_mode: str, delay: int
) -> ScenarioRow | None:
    for row in rows:
        if (
            row.execution_mode == execution_mode
            and row.side_mode == side_mode
            and row.entry_delay_bars == delay
        ):
            return row
    return None


def group_summary(
    section: str,
    bucket: str,
    scenario: ScenarioRow,
    trades: Sequence[AuditTrade],
    scenario_trade_count: int,
) -> GroupRow:
    metrics = summarize_trade_metrics(trades)
    return GroupRow(
        section=section,
        bucket=bucket,
        execution_mode=scenario.execution_mode,
        side_mode=scenario.side_mode,
        entry_delay_bars=scenario.entry_delay_bars,
        scenario=scenario.scenario,
        trades=int(metrics["trades"]),
        buy_trades=int(metrics["buy_trades"]),
        sell_trades=int(metrics["sell_trades"]),
        original_buy_trades=int(metrics["original_buy_trades"]),
        original_sell_trades=int(metrics["original_sell_trades"]),
        wins=int(metrics["wins"]),
        losses=int(metrics["losses"]),
        timeouts=int(metrics["timeouts"]),
        take_profits=int(metrics["take_profits"]),
        stop_losses=int(metrics["stop_losses"]),
        win_rate=float(metrics["win_rate"]),
        total_pnl=float(metrics["total_pnl"]),
        avg_pnl=float(metrics["avg_pnl"]),
        gross_profit=float(metrics["gross_profit"]),
        gross_loss=float(metrics["gross_loss"]),
        profit_factor=float(metrics["profit_factor"]),
        max_drawdown=float(metrics["max_drawdown"]),
        share_of_scenario_trades=safe_div(int(metrics["trades"]), scenario_trade_count),
    )


def group_by_key(trades: Sequence[AuditTrade], key: str) -> Iterable[tuple[str, list[AuditTrade]]]:
    buckets: dict[str, list[AuditTrade]] = {}
    for trade in trades:
        if key == "original_side":
            bucket = trade.original_side
        elif key == "executed_side":
            bucket = trade.executed_side
        elif key == "month":
            bucket = trade.month
        elif key == "hour":
            bucket = f"hour={trade.hour}"
        elif key == "month_original_side":
            bucket = f"{trade.month} / {trade.original_side}"
        elif key == "original_side_hour":
            bucket = f"{trade.original_side} / hour={trade.hour}"
        elif key == "side_transform":
            bucket = f"{trade.original_side}->{trade.executed_side}"
        else:
            bucket = "all"
        buckets.setdefault(bucket, []).append(trade)
    return sorted(buckets.items(), key=lambda item: item[0])


def build_group_rows(
    scenarios: Sequence[tuple[ScenarioRow, list[AuditTrade]]], min_group_trades: int
) -> list[GroupRow]:
    rows: list[GroupRow] = []
    keys = (
        "all",
        "side_transform",
        "original_side",
        "executed_side",
        "month",
        "hour",
        "month_original_side",
        "original_side_hour",
    )
    for scenario, trades in scenarios:
        for key in keys:
            for bucket, subset in group_by_key(trades, key):
                if len(subset) >= min_group_trades or key == "all":
                    rows.append(group_summary(key, bucket, scenario, subset, len(trades)))
    return rows


def write_csv(path: Path, rows: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def metric_delta(new: float, old: float) -> str:
    return f"{new - old:+.2f}"


def group_lookup(
    groups: Sequence[GroupRow],
    execution_mode: str,
    side_mode: str,
    delay: int,
    section: str,
    bucket: str,
) -> GroupRow | None:
    for row in groups:
        if (
            row.execution_mode == execution_mode
            and row.side_mode == side_mode
            and row.entry_delay_bars == delay
            and row.section == section
            and row.bucket == bucket
        ):
            return row
    return None


def diagnostic_findings(rows: Sequence[ScenarioRow], groups: Sequence[GroupRow]) -> list[str]:
    findings: list[str] = []
    for execution_mode in EXECUTION_MODES:
        original = lookup_scenario(rows, execution_mode, "original", 0)
        flipped = lookup_scenario(rows, execution_mode, "flipped", 0)
        if original and flipped:
            if flipped.total_pnl > original.total_pnl:
                findings.append(
                    f"{execution_mode}: flipped side delay=0 is better than original by {metric_delta(flipped.total_pnl, original.total_pnl)} raw PnL "
                    f"(original={original.total_pnl:+.2f}, flipped={flipped.total_pnl:+.2f}). Direction may be contrarian."
                )
            else:
                findings.append(
                    f"{execution_mode}: side flip delay=0 did not beat original "
                    f"(original={original.total_pnl:+.2f}, flipped={flipped.total_pnl:+.2f})."
                )
        original_rows = [
            row
            for row in rows
            if row.execution_mode == execution_mode and row.side_mode == "original"
        ]
        if original_rows:
            delay0 = lookup_scenario(rows, execution_mode, "original", 0)
            best_delay = max(original_rows, key=lambda row: row.total_pnl)
            if (
                delay0
                and best_delay.entry_delay_bars != 0
                and best_delay.total_pnl > delay0.total_pnl
            ):
                findings.append(
                    f"{execution_mode}: delayed original entry improved raw PnL by {metric_delta(best_delay.total_pnl, delay0.total_pnl)} at delay={best_delay.entry_delay_bars}. Entry timing may be early."
                )
            elif delay0:
                findings.append(
                    f"{execution_mode}: entry delays did not improve original delay=0 enough; best original delay={best_delay.entry_delay_bars} pnl={best_delay.total_pnl:+.2f}."
                )
    for side in ("BUY", "SELL"):
        original_group = group_lookup(groups, "independent", "original", 0, "original_side", side)
        flipped_group = group_lookup(groups, "independent", "flipped", 0, "original_side", side)
        if original_group and flipped_group:
            if flipped_group.total_pnl > original_group.total_pnl:
                findings.append(
                    f"Independent {side}: executing opposite side improved PnL by {metric_delta(flipped_group.total_pnl, original_group.total_pnl)} "
                    f"({original_group.total_pnl:+.2f} → {flipped_group.total_pnl:+.2f}). This side may be inverted/contrarian."
                )
            else:
                findings.append(
                    f"Independent {side}: flipped execution did not improve vs original "
                    f"({original_group.total_pnl:+.2f} → {flipped_group.total_pnl:+.2f})."
                )
    if not findings:
        findings.append(
            "No decisive direction/entry finding. Inspect latest_groups.csv by month/session."
        )
    findings.append(
        "Diagnostic-only: this phase does not approve Phase134, paper shadow, or live trading."
    )
    return findings


def build_report(
    flat_path: Path,
    output_dir: Path,
    evaluated_rows: int,
    candidate_rows: int,
    scenario_rows: Sequence[ScenarioRow],
    group_rows: Sequence[GroupRow],
) -> AuditReport:
    best_independent = select_best(scenario_rows, "independent")
    best_chronological = select_best(scenario_rows, "chronological")
    original_ind = lookup_scenario(scenario_rows, "independent", "original", 0)
    flipped_ind = lookup_scenario(scenario_rows, "independent", "flipped", 0)
    original_chrono = lookup_scenario(scenario_rows, "chronological", "original", 0)
    flipped_chrono = lookup_scenario(scenario_rows, "chronological", "flipped", 0)
    return AuditReport(
        flat_path=str(flat_path),
        evaluated_rows=evaluated_rows,
        candidate_rows=candidate_rows,
        scenarios=len(scenario_rows),
        best_independent_scenario=best_independent.scenario,
        best_independent_total_pnl=best_independent.total_pnl,
        best_independent_profit_factor=best_independent.profit_factor,
        best_chronological_scenario=best_chronological.scenario,
        best_chronological_total_pnl=best_chronological.total_pnl,
        best_chronological_profit_factor=best_chronological.profit_factor,
        original_delay0_independent_pnl=0.0 if original_ind is None else original_ind.total_pnl,
        flipped_delay0_independent_pnl=0.0 if flipped_ind is None else flipped_ind.total_pnl,
        original_delay0_chronological_pnl=(
            0.0 if original_chrono is None else original_chrono.total_pnl
        ),
        flipped_delay0_chronological_pnl=(
            0.0 if flipped_chrono is None else flipped_chrono.total_pnl
        ),
        diagnostic_findings=diagnostic_findings(scenario_rows, group_rows),
        production_status="BLOCKED — diagnostic research only",
        output_json=str(output_dir / "latest.json"),
        output_html=str(output_dir / "latest.html"),
        output_csv=str(output_dir / "latest.csv"),
        output_groups_csv=str(output_dir / "latest_groups.csv"),
        output_best_trades_csv=str(output_dir / "best_chronological_trades.csv"),
    )


def table_for_scenarios(rows: Sequence[ScenarioRow]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.execution_mode)}</td>"
        f"<td>{html.escape(row.side_mode)}</td>"
        f"<td>{row.entry_delay_bars}</td>"
        f"<td>{row.source_candidates:,}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.buy_trades:,}/{row.sell_trades:,}</td>"
        f"<td>{row.original_buy_trades:,}/{row.original_sell_trades:,}</td>"
        f"<td>{row.win_rate:.2%}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.max_drawdown:.2f}</td>"
        f"<td>{row.final_balance:.2f}</td>"
        "</tr>"
        for row in rows
    )
    return f"""
    <section class="card">
      <h2>Scenario matrix</h2>
      <table><thead><tr><th>execution</th><th>side mode</th><th>delay</th><th>candidates</th><th>trades</th><th>exec BUY/SELL</th><th>orig BUY/SELL</th><th>win</th><th>pnl</th><th>PF</th><th>DD</th><th>final</th></tr></thead><tbody>{body}</tbody></table>
    </section>
    """


def table_for_groups(rows: Sequence[GroupRow], title: str, limit: int = 80) -> str:
    selected = list(rows)[:limit]
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.section)}</td>"
        f"<td>{html.escape(row.bucket)}</td>"
        f"<td>{html.escape(row.execution_mode)}</td>"
        f"<td>{html.escape(row.side_mode)}</td>"
        f"<td>{row.entry_delay_bars}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.buy_trades:,}/{row.sell_trades:,}</td>"
        f"<td>{row.win_rate:.2%}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.max_drawdown:.2f}</td>"
        "</tr>"
        for row in selected
    )
    return f"""
    <section class="card">
      <h2>{html.escape(title)}</h2>
      <table><thead><tr><th>section</th><th>bucket</th><th>execution</th><th>side mode</th><th>delay</th><th>trades</th><th>exec BUY/SELL</th><th>win</th><th>pnl</th><th>PF</th><th>DD</th></tr></thead><tbody>{body}</tbody></table>
    </section>
    """


def render_html(
    title: str,
    report: AuditReport,
    scenario_rows: Sequence[ScenarioRow],
    group_rows: Sequence[GroupRow],
) -> str:
    findings = "".join(f"<li>{html.escape(item)}</li>" for item in report.diagnostic_findings)
    side_rows = [row for row in group_rows if row.section in {"side_transform", "original_side"}]
    month_side_rows = [row for row in group_rows if row.section == "month_original_side"]
    hour_side_rows = [row for row in group_rows if row.section == "original_side_hour"]
    worst_rows = sorted(group_rows, key=lambda row: row.total_pnl)[:40]
    best_rows = sorted(group_rows, key=lambda row: row.total_pnl, reverse=True)[:40]
    sorted_scenarios = sorted(
        scenario_rows,
        key=lambda row: (row.execution_mode, row.side_mode, row.entry_delay_bars),
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma, Segoe UI, Arial, sans-serif; line-height:1.7; }}
    main {{ max-width:1540px; margin:0 auto; padding:24px; }}
    .hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
    .metric span {{ display:block; color:#94a3b8; font-size:13px; }}
    .metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
    table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:12px; }}
    th,td {{ border-bottom:1px solid #1e293b; padding:7px; vertical-align:top; }} th {{ color:#bae6fd; }}
    code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
    .danger {{ border-right:4px solid #ef4444; background:#ef44441a; border-radius:10px; padding:10px; margin-top:12px; }}
    .info {{ border-right:4px solid #38bdf8; background:#38bdf81a; border-radius:10px; padding:10px; margin-top:12px; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
  </style>
</head>
<body><main>
  <section class="hero">
    <h1>{html.escape(title)}</h1>
    <p>Phase140A جهت candidate و زمان ورود را با counterfactual replay بررسی می‌کند: original vs flipped و delay=0/1/2/3. این گزارش training نیست و مجوز paper/live نیست.</p>
    <div class="grid">
      <div class="metric"><span>Best independent</span><strong>{html.escape(report.best_independent_scenario)}<br>{report.best_independent_total_pnl:+.2f} / PF {report.best_independent_profit_factor:.3f}</strong></div>
      <div class="metric"><span>Best chronological</span><strong>{html.escape(report.best_chronological_scenario)}<br>{report.best_chronological_total_pnl:+.2f} / PF {report.best_chronological_profit_factor:.3f}</strong></div>
      <div class="metric"><span>Original d0 independent</span><strong>{report.original_delay0_independent_pnl:+.2f}</strong></div>
      <div class="metric"><span>Flipped d0 independent</span><strong>{report.flipped_delay0_independent_pnl:+.2f}</strong></div>
    </div>
    <div class="danger"><strong>Production status:</strong> {html.escape(report.production_status)}</div>
    <div class="info"><strong>How to read:</strong> اگر flipped بهتر شود، احتمال contrarian/inverted direction داریم. اگر delay بهتر شود، ورود زودهنگام است. اگر هیچ‌کدام کمک نکند، candidate generation no-edge است.</div>
  </section>
  <section class="card"><h2>Diagnostic findings</h2><ul>{findings}</ul></section>
  {table_for_scenarios(sorted_scenarios)}
  {table_for_groups(side_rows, "Side transform / side quality matrix", 120)}
  {table_for_groups(month_side_rows, "Month × original side × flip/delay matrix", 120)}
  {table_for_groups(hour_side_rows, "Session hour × original side matrix", 120)}
  {table_for_groups(worst_rows, "Worst group rows", 40)}
  {table_for_groups(best_rows, "Best group rows", 40)}
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
        print("  PHASE140A CANDIDATE DIRECTION / ENTRY AUDIT")
        print("=" * 74)
        print(f"  flat        : {flat_path}")
        raw = pd.read_parquet(flat_path)
        frame, evaluated_rows = prepare_frame(raw, args)
        if frame.empty:
            raise RuntimeError("No candidate rows available for direction/entry audit")
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        side_modes = parse_choice_list(args.side_modes, SIDE_MODES, SIDE_MODES)
        execution_modes = parse_choice_list(args.execution_modes, EXECUTION_MODES, EXECUTION_MODES)
        delays = parse_entry_delays(args.entry_delays)
        scenarios: list[tuple[ScenarioRow, list[AuditTrade]]] = []
        for execution_mode in execution_modes:
            for side_mode in side_modes:
                for delay in delays:
                    row, trades = run_scenario(
                        frame, candles, execution_mode, side_mode, delay, args
                    )
                    scenarios.append((row, trades))
        scenario_rows = [row for row, _ in scenarios]
        group_rows = build_group_rows(scenarios, max(args.min_group_trades, 1))
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "latest.csv"
        groups_csv_path = output_dir / "latest_groups.csv"
        json_path = output_dir / "latest.json"
        html_path = output_dir / "latest.html"
        best_trades_path = output_dir / "best_chronological_trades.csv"
        report = build_report(
            flat_path, output_dir, evaluated_rows, len(frame), scenario_rows, group_rows
        )
        best_chrono = select_best(scenario_rows, "chronological")
        best_trades = next(
            (trades for row, trades in scenarios if row.scenario == best_chrono.scenario), []
        )
        write_csv(csv_path, scenario_rows)
        write_csv(groups_csv_path, group_rows)
        write_csv(best_trades_path, best_trades)
        html_path.write_text(
            render_html(args.report_title, report, scenario_rows, group_rows), encoding="utf-8"
        )
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "scenarios": [asdict(row) for row in scenario_rows],
            "group_rows": [asdict(row) for row in group_rows],
            "best_chronological_trades_preview": [asdict(trade) for trade in best_trades[:250]],
            "files": {
                "json": str(json_path),
                "html": str(html_path),
                "csv": str(csv_path),
                "groups_csv": str(groups_csv_path),
                "best_chronological_trades_csv": str(best_trades_path),
            },
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  evaluated   : {evaluated_rows:,}")
        print(f"  candidates  : {len(frame):,}")
        print(f"  scenarios   : {len(scenario_rows):,}")
        print(
            f"  best indep  : {report.best_independent_scenario} {report.best_independent_total_pnl:+.2f} PF={report.best_independent_profit_factor:.3f}"
        )
        print(
            f"  best chrono : {report.best_chronological_scenario} {report.best_chronological_total_pnl:+.2f} PF={report.best_chronological_profit_factor:.3f}"
        )
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
