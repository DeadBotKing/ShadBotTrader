"""Phase163A: 1H pivot / entry feasibility audit.

Phase162A showed that a 5M strict bottom-buy pivot rule had a very small edge
that did not survive spread and chronological single-position replay. Phase163A
starts a new diagnostic lane: before training anything on 1H, audit whether 1H
entries have healthier spread/ATR economics and whether simple pivot-zone rules
survive chronological replay on train/validation/test splits.

Research-only. This script does not approve paper/live/production trading.
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

from audit_pivot_candidate_geometry_tightening import rolling_high_low  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from replay_pivot_bottom_buy_candidate import max_drawdown  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_SELL, spread_abs, trade_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_FLAT_PATH = Path("datasets/processed/XAUUSD/1H/v1.parquet")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_1h_entry_feasibility")
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
SIDE_TO_ACTION = {SIDE_BUY: ACTION_BUY, SIDE_SELL: ACTION_SELL}


@dataclass(frozen=True)
class DataHealthRow:
    split: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    duplicate_timestamps: int
    missing_timestamp_rows: int
    expected_step_minutes: float
    gap_count: int
    max_gap_minutes: float
    nonfinite_ohlc_cells: int
    invalid_ohlc_rows: int
    atr_nonpositive_rows: int


@dataclass(frozen=True)
class SpreadAtrRow:
    split: str
    rows: int
    spread_mode: str
    spread_value: float
    atr_mean: float
    atr_median: float
    full_spread_atr_mean: float
    full_spread_atr_median: float
    full_spread_atr_p90: float
    half_spread_atr_median: float
    spread_feasible_gate: int


@dataclass(frozen=True)
class ReplaySplitRow:
    policy_id: str
    split: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    spread_mode: str
    spread_value: float
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
    executed_independent_mean_atr: float
    invalid_events: int
    positive_months: int
    negative_months: int
    pass_gate: int


@dataclass(frozen=True)
class ReplaySelectionRow:
    policy_id: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    spread_value: float
    train_trades: int
    train_profit_factor: float
    train_total_cash_pnl: float
    validation_trades: int
    validation_candidate_event_rate: float
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_final_balance: float
    validation_independent_mean_atr: float
    validation_skipped_winners: int
    validation_skipped_losers: int
    test_trades: int
    test_candidate_event_rate: float
    test_profit_factor: float
    test_total_cash_pnl: float
    test_final_balance: float
    test_independent_mean_atr: float
    test_skipped_winners: int
    test_skipped_losers: int
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    validation_score: float
    warnings: str


@dataclass(frozen=True)
class Pivot1HFeasibilityReport:
    symbol: str
    timeframe: str
    flat_path: str
    flat_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    spread_mode: str
    spread_value: float
    selection_spread_value: float
    tp_atr: float
    sl_atr: float
    hold_bars: int
    replay_policy_rows: int
    selection_rows: int
    validation_pass_configs: int
    transfer_pass_configs: int
    spread_feasible_gate: int
    selected_policy_id: str
    selected_side_mapping: str
    selected_entry_delay_bars: int
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_validation_total_cash_pnl: float
    selected_test_total_cash_pnl: float
    selected_transfer_pass_gate: int
    route_feasible_gate: int
    data_health: list[dict[str, Any]]
    spread_atr_rows: list[dict[str, Any]]
    top_config_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_spread_atr_csv: str
    output_candidate_replay_csv: str
    output_selection_csv: str
    output_monthly_csv: str
    production_status: str


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip().lower()
        if not item:
            continue
        if item in {"off", "none"}:
            values.append(0.0)
        else:
            values.append(float(item))
    return values or [float(value) for value in default]


def parse_int_grid(text: str, default: Sequence[int]) -> list[int]:
    raw = str(text or "").strip()
    if not raw:
        return [int(value) for value in default]
    values: list[int] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip()
        if item:
            values.append(int(item))
    return values or [int(value) for value in default]


def parse_text_grid(text: str, default: Sequence[str]) -> list[str]:
    raw = str(text or "").strip()
    values = [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]
    return values or [str(value) for value in default]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit whether 1H pivot entries are feasible before training any 1H model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="1H")
    parser.add_argument("--flat-path", default=str(DEFAULT_FLAT_PATH))
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=24)
    parser.add_argument("--expected-step-minutes", type=float, default=60.0)
    parser.add_argument("--recent-window-bars", default="24,48")
    parser.add_argument("--pivot-zone-atrs", default="0.05,0.10,0.15")
    parser.add_argument("--top-position-thresholds", default="0.85,0.90")
    parser.add_argument("--bottom-position-thresholds", default="0.15,0.10")
    parser.add_argument("--exclude-both-zones", default="1")
    parser.add_argument("--min-range-width-atrs", default="1.0")
    parser.add_argument("--max-range-width-atrs", default="0")
    parser.add_argument("--side-mappings", default="reversal,bottom_buy,top_sell,breakout")
    parser.add_argument("--entry-delays", default="0,1")
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-values", default="0,0.06")
    parser.add_argument("--selection-spread-value", type=float, default=0.06)
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--tp-atr", type=float, default=1.5)
    parser.add_argument("--sl-atr", type=float, default=1.0)
    parser.add_argument("--hold-bars", type=int, default=24)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--validation-min-trades", type=int, default=10)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=10)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--max-validation-event-rate", type=float, default=0.35)
    parser.add_argument("--max-test-event-rate", type=float, default=0.35)
    parser.add_argument("--score-metric", choices=("cash_pnl", "profit_factor", "independent_mean_atr"), default="cash_pnl")
    parser.add_argument("--max-policies", type=int, default=0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase163A 1H pivot entry feasibility audit")
    return parser.parse_args(argv)


def resolve_flat_path_arg(args: argparse.Namespace) -> Path:
    requested = Path(str(args.flat_path))
    if requested.exists():
        return requested
    base = Path(args.storage_root) / "processed" / str(args.symbol).upper() / str(args.timeframe).upper()
    candidates = [
        base / "pivot_pattern_sequence_flat_latest.parquet",
        base / "hybrid_telemetry_flat_latest.parquet",
        base / "v1.parquet",
    ]
    candidates.extend(sorted(base.glob("*.parquet"), reverse=True))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"1H flat file not found. Requested={requested}; searched under {base}")


def read_ohlc_frame(path: Path, max_rows: int = 0) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"flat file not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    missing = sorted({"timestamp", "open", "high", "low", "close"} - set(frame.columns))
    if missing:
        raise RuntimeError(f"1H flat file is missing required columns: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if int(max_rows) > 0 and len(result) > int(max_rows):
        result = result.iloc[-int(max_rows) :].copy().reset_index(drop=True)
    if len(result) < 100:
        raise RuntimeError(f"Need at least 100 1H rows for feasibility audit; got {len(result)}")
    return result


def data_health_for_split(name: str, frame: pd.DataFrame, indices: np.ndarray, atr: np.ndarray, expected_step_minutes: float) -> DataHealthRow:
    idx = np.asarray(indices, dtype=np.int64)
    subset = frame.iloc[idx] if len(idx) else frame.iloc[[]]
    timestamps = subset["timestamp"] if len(subset) else pd.Series([], dtype="datetime64[ns, UTC]")
    deltas = timestamps.diff().dt.total_seconds().dropna().to_numpy(dtype=np.float64) / 60.0 if len(timestamps) else np.asarray([], dtype=np.float64)
    gap_mask = np.abs(deltas - float(expected_step_minutes)) > max(float(expected_step_minutes) * 0.25, 1.0)
    ohlc = subset[["open", "high", "low", "close"]].to_numpy(dtype=np.float64) if len(subset) else np.empty((0, 4))
    high = subset["high"].to_numpy(dtype=np.float64) if len(subset) else np.asarray([], dtype=np.float64)
    low = subset["low"].to_numpy(dtype=np.float64) if len(subset) else np.asarray([], dtype=np.float64)
    open_ = subset["open"].to_numpy(dtype=np.float64) if len(subset) else np.asarray([], dtype=np.float64)
    close = subset["close"].to_numpy(dtype=np.float64) if len(subset) else np.asarray([], dtype=np.float64)
    invalid = (high < low) | (high < np.maximum(open_, close)) | (low > np.minimum(open_, close))
    atr_values = atr[idx] if len(idx) else np.asarray([], dtype=np.float64)
    return DataHealthRow(
        split=name,
        rows=int(len(subset)),
        first_timestamp=str(timestamps.iloc[0]) if len(timestamps) else "",
        last_timestamp=str(timestamps.iloc[-1]) if len(timestamps) else "",
        duplicate_timestamps=int(timestamps.duplicated().sum()) if len(timestamps) else 0,
        missing_timestamp_rows=int(frame.iloc[idx]["timestamp"].isna().sum()) if len(idx) else 0,
        expected_step_minutes=float(expected_step_minutes),
        gap_count=int(np.sum(gap_mask)),
        max_gap_minutes=float(np.max(deltas)) if len(deltas) else 0.0,
        nonfinite_ohlc_cells=int(np.sum(~np.isfinite(ohlc))) if len(ohlc) else 0,
        invalid_ohlc_rows=int(np.sum(invalid)) if len(invalid) else 0,
        atr_nonpositive_rows=int(np.sum(~np.isfinite(atr_values) | (atr_values <= 0))) if len(atr_values) else 0,
    )


def spread_atr_for_split(name: str, frame: pd.DataFrame, indices: np.ndarray, atr: np.ndarray, args: argparse.Namespace, spread_value: float) -> SpreadAtrRow:
    idx = np.asarray(indices, dtype=np.int64)
    close = frame["close"].to_numpy(dtype=np.float64)
    atr_values = atr[idx] if len(idx) else np.asarray([], dtype=np.float64)
    spread_values = np.asarray([spread_abs(float(close[row]), str(args.spread_mode), float(spread_value)) for row in idx], dtype=np.float64)
    spread_atr = spread_values / np.maximum(atr_values, 1e-9) if len(idx) else np.asarray([], dtype=np.float64)
    return SpreadAtrRow(
        split=name,
        rows=int(len(idx)),
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        atr_mean=float(np.mean(atr_values)) if len(atr_values) else 0.0,
        atr_median=float(np.median(atr_values)) if len(atr_values) else 0.0,
        full_spread_atr_mean=float(np.mean(spread_atr)) if len(spread_atr) else 0.0,
        full_spread_atr_median=float(np.median(spread_atr)) if len(spread_atr) else 0.0,
        full_spread_atr_p90=float(np.percentile(spread_atr, 90)) if len(spread_atr) else 0.0,
        half_spread_atr_median=float(np.median(spread_atr / 2.0)) if len(spread_atr) else 0.0,
        spread_feasible_gate=int((float(np.median(spread_atr)) if len(spread_atr) else 999.0) <= float(args.max_median_spread_atr)),
    )


def build_zone_masks(
    frame: pd.DataFrame,
    atr: np.ndarray,
    recent_window: int,
    zone_atr: float,
    top_position_threshold: float,
    bottom_position_threshold: float,
    exclude_both_zones: int,
    min_width_atr: float,
    max_width_atr: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    recent_high, recent_low = rolling_high_low(high, low, int(recent_window))
    width = np.maximum(recent_high - recent_low, 1e-9)
    position = (close - recent_low) / width
    width_atr = width / np.maximum(atr, 1e-9)
    top = ((recent_high - close) <= float(zone_atr) * atr) & (position >= float(top_position_threshold))
    bottom = ((close - recent_low) <= float(zone_atr) * atr) & (position <= float(bottom_position_threshold))
    both = top & bottom
    if int(exclude_both_zones):
        top = top & ~both
        bottom = bottom & ~both
    width_ok = width_atr >= float(min_width_atr)
    if float(max_width_atr) > 0:
        width_ok = width_ok & (width_atr <= float(max_width_atr))
    return top & width_ok, bottom & width_ok, both & width_ok


def sides_for_row(mapping: str, is_top: bool, is_bottom: bool) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    if mapping == "reversal":
        if is_top:
            events.append(("top", SIDE_SELL))
        if is_bottom:
            events.append(("bottom", SIDE_BUY))
    elif mapping == "breakout":
        if is_top:
            events.append(("top", SIDE_BUY))
        if is_bottom:
            events.append(("bottom", SIDE_SELL))
    elif mapping == "bottom_buy" and is_bottom:
        events.append(("bottom", SIDE_BUY))
    elif mapping == "bottom_sell" and is_bottom:
        events.append(("bottom", SIDE_SELL))
    elif mapping == "top_sell" and is_top:
        events.append(("top", SIDE_SELL))
    elif mapping == "top_buy" and is_top:
        events.append(("top", SIDE_BUY))
    elif mapping == "all_buy" and (is_top or is_bottom):
        events.append(("any", SIDE_BUY))
    elif mapping == "all_sell" and (is_top or is_bottom):
        events.append(("any", SIDE_SELL))
    return events


def pf(values: Sequence[float]) -> float:
    profits = float(sum(value for value in values if value > 0))
    losses = float(abs(sum(value for value in values if value < 0)))
    if losses <= 0:
        return 999.0 if profits > 0 else 0.0
    return profits / losses


def pass_gate(split: str, trades: int, profit_factor: float, final_balance: float, event_rate: float, args: argparse.Namespace) -> int:
    if split == "validation":
        return int(
            trades >= int(args.validation_min_trades)
            and profit_factor >= float(args.validation_min_profit_factor)
            and final_balance >= float(args.validation_min_final_balance)
            and event_rate <= float(args.max_validation_event_rate)
        )
    if split == "test":
        return int(
            trades >= int(args.test_min_trades)
            and profit_factor >= float(args.test_min_profit_factor)
            and final_balance >= float(args.test_min_final_balance)
            and event_rate <= float(args.max_test_event_rate)
        )
    return int(trades > 0)


def simulate_policy_split(
    policy_id: str,
    split: str,
    frame: pd.DataFrame,
    split_indices_local: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    atr: np.ndarray,
    mapping: str,
    entry_delay: int,
    recent_window: int,
    zone_atr: float,
    top_position: float,
    bottom_position: float,
    exclude_both: int,
    min_width: float,
    max_width: float,
    spread_value: float,
    args: argparse.Namespace,
) -> tuple[ReplaySplitRow, list[dict[str, Any]]]:
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
    cash_pnls: list[float] = []
    outcomes: list[str] = []
    sides: list[str] = []
    skipped_while_open = 0
    skipped_winners = 0
    skipped_losers = 0
    skipped_timeouts = 0
    monthly: dict[str, dict[str, Any]] = {}
    trade_args = SimpleNamespace(
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        same_bar_policy=str(args.same_bar_policy),
    )

    def bucket(row_id: int) -> dict[str, Any]:
        month = str(frame.at[int(row_id), "timestamp"])[:7]
        if month not in monthly:
            monthly[month] = {
                "policy_id": policy_id,
                "split": split,
                "month": month,
                "side_mapping": mapping,
                "entry_delay_bars": int(entry_delay),
                "spread_value": float(spread_value),
                "trades": 0,
                "cash_pnl": 0.0,
                "take_profits": 0,
                "stop_losses": 0,
                "timeouts": 0,
                "skipped_while_open": 0,
                "skipped_winners": 0,
                "skipped_losers": 0,
            }
        return monthly[month]

    for row_id in np.asarray(split_indices_local, dtype=np.int64):
        row = int(row_id)
        row_events = sides_for_row(str(mapping), bool(top_mask[row]), bool(bottom_mask[row]))
        for zone, side_name in row_events:
            events += 1
            top_events += int(zone == "top")
            bottom_events += int(zone == "bottom")
            buy_events += int(side_name == SIDE_BUY)
            sell_events += int(side_name == SIDE_SELL)
            signal_row = row + max(int(entry_delay), 0)
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
            points, _entry_row, exit_row, _entry, _tp, _sl, _exit_price, outcome = path
            score_atr = float(points / atr_value) if atr_value > 0 else 0.0
            independent_scores.append(score_atr)
            if signal_row <= open_until:
                skipped_while_open += 1
                skipped_scores.append(score_atr)
                month = bucket(row)
                month["skipped_while_open"] += 1
                if score_atr > 0:
                    skipped_winners += 1
                    month["skipped_winners"] += 1
                elif score_atr < 0:
                    skipped_losers += 1
                    month["skipped_losers"] += 1
                else:
                    skipped_timeouts += 1
                continue
            risk_amount = max(balance * float(args.risk_per_trade), 0.0)
            quantity = risk_amount / sl_distance if sl_distance > 0 else 0.0
            cash_pnl = float(points * quantity)
            balance += cash_pnl
            balances.append(balance)
            cash_pnls.append(cash_pnl)
            outcomes.append(str(outcome))
            sides.append(side_name)
            executed_scores.append(score_atr)
            open_until = max(open_until, int(exit_row))
            month = bucket(row)
            month["trades"] += 1
            month["cash_pnl"] += cash_pnl
            if outcome == "take_profit":
                month["take_profits"] += 1
            elif outcome == "stop_loss":
                month["stop_losses"] += 1
            else:
                month["timeouts"] += 1
            if balance <= 0:
                break
        if balance <= 0:
            break

    gross_profit = float(sum(value for value in cash_pnls if value > 0))
    gross_loss = float(abs(sum(value for value in cash_pnls if value < 0)))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    wins = int(sum(1 for value in cash_pnls if value > 0))
    losses = int(sum(1 for value in cash_pnls if value < 0))
    event_rate = float(events / len(split_indices_local)) if len(split_indices_local) else 0.0
    row = ReplaySplitRow(
        policy_id=policy_id,
        split=split,
        side_mapping=str(mapping),
        entry_delay_bars=int(entry_delay),
        recent_window_bars=int(recent_window),
        pivot_zone_atr=float(zone_atr),
        top_position_threshold=float(top_position),
        bottom_position_threshold=float(bottom_position),
        exclude_both_zones=int(exclude_both),
        min_range_width_atr=float(min_width),
        max_range_width_atr=float(max_width),
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        evaluated_rows=int(len(split_indices_local)),
        candidate_events=int(events),
        candidate_event_rate=event_rate,
        top_events=int(top_events),
        bottom_events=int(bottom_events),
        buy_events=int(buy_events),
        sell_events=int(sell_events),
        independent_replays=int(len(independent_scores)),
        independent_mean_atr=float(np.mean(independent_scores)) if independent_scores else 0.0,
        independent_sum_atr=float(np.sum(independent_scores)) if independent_scores else 0.0,
        independent_profit_factor=pf(independent_scores),
        independent_win_rate=float(np.mean(np.asarray(independent_scores) > 0)) if independent_scores else 0.0,
        trades=int(len(cash_pnls)),
        buy_trades=int(sum(1 for side in sides if side == SIDE_BUY)),
        sell_trades=int(sum(1 for side in sides if side == SIDE_SELL)),
        wins=wins,
        losses=losses,
        win_rate=float(wins / len(cash_pnls)) if cash_pnls else 0.0,
        total_cash_pnl=float(sum(cash_pnls)),
        final_balance=float(balance),
        return_percent=float((balance - float(args.initial_capital)) / float(args.initial_capital)) if float(args.initial_capital) else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=float(profit_factor),
        max_drawdown_cash=float(max_drawdown(balances)),
        take_profits=int(sum(1 for outcome in outcomes if outcome == "take_profit")),
        stop_losses=int(sum(1 for outcome in outcomes if outcome == "stop_loss")),
        timeouts=int(sum(1 for outcome in outcomes if outcome == "timeout")),
        skipped_while_open=int(skipped_while_open),
        skipped_winners=int(skipped_winners),
        skipped_losers=int(skipped_losers),
        skipped_timeouts=int(skipped_timeouts),
        skipped_independent_sum_atr=float(np.sum(skipped_scores)) if skipped_scores else 0.0,
        executed_independent_mean_atr=float(np.mean(executed_scores)) if executed_scores else 0.0,
        invalid_events=int(invalid),
        positive_months=int(sum(1 for month in monthly.values() if float(month["cash_pnl"]) > 0)),
        negative_months=int(sum(1 for month in monthly.values() if float(month["cash_pnl"]) < 0)),
        pass_gate=pass_gate(split, len(cash_pnls), profit_factor, balance, event_rate, args),
    )
    return row, list(monthly.values())


def replay_grid(args: argparse.Namespace, frame: pd.DataFrame, split_map: Mapping[str, np.ndarray], atr: np.ndarray) -> tuple[list[ReplaySplitRow], list[dict[str, Any]]]:
    recent_values = parse_int_grid(args.recent_window_bars, (24, 48))
    zone_values = parse_float_grid(args.pivot_zone_atrs, (0.05, 0.10, 0.15))
    top_values = parse_float_grid(args.top_position_thresholds, (0.85, 0.90))
    bottom_values = parse_float_grid(args.bottom_position_thresholds, (0.15, 0.10))
    exclude_values = parse_int_grid(args.exclude_both_zones, (1,))
    min_width_values = parse_float_grid(args.min_range_width_atrs, (1.0,))
    max_width_values = parse_float_grid(args.max_range_width_atrs, (0.0,))
    mappings = parse_text_grid(args.side_mappings, ("reversal", "bottom_buy", "top_sell", "breakout"))
    delays = parse_int_grid(args.entry_delays, (0, 1))
    spreads = parse_float_grid(args.spread_values, (0.0, 0.06))
    rows: list[ReplaySplitRow] = []
    monthly_rows: list[dict[str, Any]] = []
    policy_count = 0
    for recent in recent_values:
        for zone in zone_values:
            for top_pos in top_values:
                for bottom_pos in bottom_values:
                    for exclude in exclude_values:
                        for min_width in min_width_values:
                            for max_width in max_width_values:
                                top_mask, bottom_mask, _ = build_zone_masks(
                                    frame,
                                    atr,
                                    int(recent),
                                    float(zone),
                                    float(top_pos),
                                    float(bottom_pos),
                                    int(exclude),
                                    float(min_width),
                                    float(max_width),
                                )
                                for mapping in mappings:
                                    for delay in delays:
                                        for spread in spreads:
                                            policy_count += 1
                                            if int(args.max_policies) > 0 and policy_count > int(args.max_policies):
                                                return rows, monthly_rows
                                            policy_id = (
                                                f"1H|{mapping}|d={int(delay)}|rw={int(recent)}|zone={float(zone):g}|"
                                                f"top={float(top_pos):g}|bottom={float(bottom_pos):g}|"
                                                f"ex={int(exclude)}|minw={float(min_width):g}|maxw={float(max_width):g}|"
                                                f"spread={float(spread):g}"
                                            )
                                            for split, split_idx in split_map.items():
                                                row, months = simulate_policy_split(
                                                    policy_id,
                                                    split,
                                                    frame,
                                                    split_idx,
                                                    top_mask,
                                                    bottom_mask,
                                                    atr,
                                                    mapping,
                                                    int(delay),
                                                    int(recent),
                                                    float(zone),
                                                    float(top_pos),
                                                    float(bottom_pos),
                                                    int(exclude),
                                                    float(min_width),
                                                    float(max_width),
                                                    float(spread),
                                                    args,
                                                )
                                                rows.append(row)
                                                monthly_rows.extend(months)
    return rows, monthly_rows


def validation_score(row: ReplaySelectionRow, metric: str) -> float:
    if metric == "profit_factor":
        return float(row.validation_profit_factor)
    if metric == "independent_mean_atr":
        return float(row.validation_independent_mean_atr)
    return float(row.validation_total_cash_pnl)


def build_selection_rows(rows: Sequence[ReplaySplitRow], args: argparse.Namespace) -> list[ReplaySelectionRow]:
    grouped: dict[str, dict[str, ReplaySplitRow]] = {}
    for row in rows:
        grouped.setdefault(row.policy_id, {})[row.split] = row
    selections: list[ReplaySelectionRow] = []
    for policy_id, by_split in grouped.items():
        validation = by_split.get("validation")
        test = by_split.get("test")
        train = by_split.get("train")
        if validation is None or test is None:
            continue
        warnings: list[str] = []
        if validation.candidate_event_rate > float(args.max_validation_event_rate):
            warnings.append("validation event rate above max")
        if test.candidate_event_rate > float(args.max_test_event_rate):
            warnings.append("test event rate above max")
        if validation.trades < int(args.validation_min_trades):
            warnings.append("validation trades below minimum")
        if test.trades < int(args.test_min_trades):
            warnings.append("test trades below minimum")
        if validation.profit_factor < float(args.validation_min_profit_factor):
            warnings.append("validation PF below minimum")
        if test.profit_factor < float(args.test_min_profit_factor):
            warnings.append("test PF below minimum")
        seed = ReplaySelectionRow(
            policy_id=policy_id,
            side_mapping=validation.side_mapping,
            entry_delay_bars=int(validation.entry_delay_bars),
            recent_window_bars=int(validation.recent_window_bars),
            pivot_zone_atr=float(validation.pivot_zone_atr),
            top_position_threshold=float(validation.top_position_threshold),
            bottom_position_threshold=float(validation.bottom_position_threshold),
            exclude_both_zones=int(validation.exclude_both_zones),
            min_range_width_atr=float(validation.min_range_width_atr),
            max_range_width_atr=float(validation.max_range_width_atr),
            spread_value=float(validation.spread_value),
            train_trades=int(train.trades if train else 0),
            train_profit_factor=float(train.profit_factor if train else 0.0),
            train_total_cash_pnl=float(train.total_cash_pnl if train else 0.0),
            validation_trades=int(validation.trades),
            validation_candidate_event_rate=float(validation.candidate_event_rate),
            validation_profit_factor=float(validation.profit_factor),
            validation_total_cash_pnl=float(validation.total_cash_pnl),
            validation_final_balance=float(validation.final_balance),
            validation_independent_mean_atr=float(validation.independent_mean_atr),
            validation_skipped_winners=int(validation.skipped_winners),
            validation_skipped_losers=int(validation.skipped_losers),
            test_trades=int(test.trades),
            test_candidate_event_rate=float(test.candidate_event_rate),
            test_profit_factor=float(test.profit_factor),
            test_total_cash_pnl=float(test.total_cash_pnl),
            test_final_balance=float(test.final_balance),
            test_independent_mean_atr=float(test.independent_mean_atr),
            test_skipped_winners=int(test.skipped_winners),
            test_skipped_losers=int(test.skipped_losers),
            validation_pass_gate=int(validation.pass_gate),
            test_pass_gate=int(test.pass_gate),
            transfer_pass_gate=int(validation.pass_gate and test.pass_gate),
            validation_score=0.0,
            warnings=json.dumps(warnings, ensure_ascii=False),
        )
        selections.append(ReplaySelectionRow(**{**asdict(seed), "validation_score": validation_score(seed, str(args.score_metric))}))
    return selections


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Pivot1HFeasibilityReport) -> str:
    top_rows = "".join(
        f"<tr><td>{html.escape(str(row['side_mapping']))}</td>"
        f"<td>{int(row['entry_delay_bars'])}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{int(row['validation_trades'])}</td>"
        f"<td>{float(row['validation_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{int(row['test_trades'])}</td>"
        f"<td>{float(row['test_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.top_config_rows[:60]
    )
    spread_rows = "".join(
        f"<tr><td>{html.escape(str(row['split']))}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{float(row['atr_median']):.4f}</td>"
        f"<td>{float(row['full_spread_atr_median']):.4f}</td>"
        f"<td>{float(row['full_spread_atr_p90']):.4f}</td>"
        f"<td>{int(row['spread_feasible_gate'])}</td></tr>"
        for row in report.spread_atr_rows
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase163A 1H pivot/entry feasibility audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_feasible_gate': report.route_feasible_gate,
        'selected_policy_id': report.selected_policy_id,
        'selected_validation_pf': report.selected_validation_profit_factor,
        'selected_test_pf': report.selected_test_profit_factor,
        'selected_transfer_pass_gate': report.selected_transfer_pass_gate,
        'spread_feasible_gate': report.spread_feasible_gate,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Spread / ATR</h2><table><thead><tr><th>Split</th><th>Spread</th><th>ATR median</th><th>Spread/ATR median</th><th>Spread/ATR p90</th><th>Gate</th></tr></thead><tbody>{spread_rows}</tbody></table></section>
<section class="card"><h2>Top validation-selected candidate rows</h2><table><thead><tr><th>Mapping</th><th>Delay</th><th>Spread</th><th>Val trades</th><th>Val PnL</th><th>Val PF</th><th>Test trades</th><th>Test PnL</th><th>Test PF</th><th>Transfer</th></tr></thead><tbody>{top_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE163A 1H PIVOT / ENTRY FEASIBILITY AUDIT")
        print("=" * 74)
        flat_path = resolve_flat_path_arg(args)
        frame = read_ohlc_frame(flat_path, int(args.max_rows))
        atr = resolve_atr(frame)
        train_idx, validation_idx, test_idx = split_indices(len(frame), args.train_frac, args.val_frac, args.purge_gap)
        split_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
        data_health = [
            data_health_for_split(name, frame, idx, atr, float(args.expected_step_minutes))
            for name, idx in split_map.items()
        ]
        spread_values = parse_float_grid(args.spread_values, (0.0, 0.06))
        spread_rows = [
            spread_atr_for_split(name, frame, idx, atr, args, spread)
            for spread in spread_values
            for name, idx in split_map.items()
        ]
        replay_rows, monthly_rows = replay_grid(args, frame, split_map, atr)
        selection_rows = build_selection_rows(replay_rows, args)
        selection_spread = float(args.selection_spread_value)
        selection_pool = [row for row in selection_rows if abs(float(row.spread_value) - selection_spread) <= 1e-9]
        if not selection_pool:
            selection_pool = selection_rows
        ranked = sorted(
            selection_pool,
            key=lambda row: (
                row.validation_pass_gate,
                row.validation_score,
                row.validation_profit_factor,
                -row.validation_candidate_event_rate,
            ),
            reverse=True,
        )
        selected = ranked[0] if ranked else None
        all_ranked = sorted(
            selection_rows,
            key=lambda row: (
                row.transfer_pass_gate,
                row.validation_pass_gate,
                row.validation_score,
                row.validation_profit_factor,
            ),
            reverse=True,
        )
        spread_realistic_rows = [row for row in spread_rows if abs(float(row.spread_value) - selection_spread) <= 1e-9]
        spread_feasible = int(bool(spread_realistic_rows) and all(int(row.spread_feasible_gate) for row in spread_realistic_rows))
        health_ok = int(
            all(row.nonfinite_ohlc_cells == 0 and row.invalid_ohlc_rows == 0 and row.atr_nonpositive_rows == 0 for row in data_health)
        )
        route_feasible = int(bool(selected) and int(selected.transfer_pass_gate) and spread_feasible and health_ok)
        spread_csv = output_dir / "latest_spread_atr.csv"
        replay_csv = output_dir / "latest_candidate_replay.csv"
        selection_csv = output_dir / "latest_selection.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        write_csv(spread_csv, [asdict(row) for row in spread_rows])
        write_csv(replay_csv, [asdict(row) for row in replay_rows])
        write_csv(selection_csv, [asdict(row) for row in all_ranked])
        write_csv(monthly_csv, monthly_rows)
        report = Pivot1HFeasibilityReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            flat_rows=int(len(frame)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            spread_mode=str(args.spread_mode),
            spread_value=float(args.selection_spread_value),
            selection_spread_value=float(args.selection_spread_value),
            tp_atr=float(args.tp_atr),
            sl_atr=float(args.sl_atr),
            hold_bars=int(args.hold_bars),
            replay_policy_rows=int(len(replay_rows)),
            selection_rows=int(len(selection_rows)),
            validation_pass_configs=int(sum(row.validation_pass_gate for row in selection_rows if abs(float(row.spread_value) - selection_spread) <= 1e-9)),
            transfer_pass_configs=int(sum(row.transfer_pass_gate for row in selection_rows if abs(float(row.spread_value) - selection_spread) <= 1e-9)),
            spread_feasible_gate=int(spread_feasible),
            selected_policy_id=str(selected.policy_id) if selected else "",
            selected_side_mapping=str(selected.side_mapping) if selected else "",
            selected_entry_delay_bars=int(selected.entry_delay_bars) if selected else 0,
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_validation_total_cash_pnl=float(selected.validation_total_cash_pnl) if selected else 0.0,
            selected_test_total_cash_pnl=float(selected.test_total_cash_pnl) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            route_feasible_gate=int(route_feasible),
            data_health=[asdict(row) for row in data_health],
            spread_atr_rows=[asdict(row) for row in spread_rows],
            top_config_rows=[asdict(row) for row in all_ranked[:100]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_spread_atr_csv=str(spread_csv),
            output_candidate_replay_csv=str(replay_csv),
            output_selection_csv=str(selection_csv),
            output_monthly_csv=str(monthly_csv),
            production_status="BLOCKED — Phase163A 1H feasibility diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase163A 1H feasibility audit complete")
        print(f"  rows             : {report.flat_rows}")
        print(f"  selection rows   : {report.selection_rows}")
        print(f"  validation pass  : {report.validation_pass_configs}")
        print(f"  transfer pass    : {report.transfer_pass_configs}")
        print(f"  selected         : {report.selected_policy_id or 'none'}")
        print(f"  route feasible   : {report.route_feasible_gate}")
        print(f"  output           : {report.output_json}")
        print(f"  elapsed          : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
