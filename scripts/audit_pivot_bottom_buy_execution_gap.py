"""Phase162A: pivot bottom-buy execution gap / entry timing audit.

Phase160A found a positive *event-scoring* diagnostic for a strict bottom-zone
BUY-only policy, but Phase161A rejected the same rule in chronological replay.
This phase isolates the execution gap without training or approving trading:

* candidate-close versus next-open BUY entry gap;
* no-spread versus spread sensitivity;
* independent event scoring versus independent replay path;
* chronological one-position replay and skipped event attribution;
* entry-delay and same-bar-policy sensitivity;
* separate TP/SL/timeout path counts for event scoring, independent replay, and
  chronological replay;
* monthly train/validation/test breakdowns.

Research-only. No paper/live/production gate is opened by this script.
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

from audit_pivot_candidate_geometry_tightening import load_meta_sample_indices, read_frame  # noqa: E402
from audit_pivot_payoff_target_redesign import first_hit_score, resolve_atr  # noqa: E402
from replay_pivot_bottom_buy_candidate import build_bottom_buy_mask, max_drawdown  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402
from train_pivot_pattern_recognition import ACTION_BUY, spread_abs, trade_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_bottom_buy_execution_gap")
OUTCOME_TP = "take_profit"
OUTCOME_SL = "stop_loss"
OUTCOME_TIMEOUT = "timeout"


@dataclass(frozen=True)
class EventScorePath:
    score_atr: float
    outcome: str
    target_hit: int
    stop_hit: int
    ambiguous: int
    entry_row_id: int
    entry_price: float


@dataclass(frozen=True)
class ReplayPath:
    score_atr: float
    score_risk_r: float
    points_pnl: float
    entry_row_id: int
    exit_row_id: int
    entry: float
    tp: float
    sl: float
    exit_price: float
    outcome: str
    tp_distance: float
    sl_distance: float
    atr_value: float


@dataclass(frozen=True)
class ExecutionEventRow:
    split: str
    timestamp: str
    entry_delay_bars: int
    same_bar_policy: str
    spread_mode: str
    spread_value: float
    candidate_row_id: int
    signal_row_id: int
    replay_entry_row_id: int
    event_entry_price: float
    raw_next_open: float
    spread_adjusted_entry: float
    raw_close_to_next_open_gap_atr: float
    adjusted_entry_gap_atr: float
    event_score_atr: float
    event_outcome: str
    event_ambiguous: int
    replay_score_atr: float
    replay_score_risk_r: float
    replay_outcome: str
    replay_exit_row_id: int
    path_disagreement: int
    chronological_status: str
    chronological_trade_number: int
    chronological_cash_pnl: float
    chronological_balance: float


@dataclass(frozen=True)
class ExecutionGapSplitRow:
    split: str
    entry_delay_bars: int
    same_bar_policy: str
    spread_mode: str
    spread_value: float
    evaluated_rows: int
    candidate_rows: int
    candidate_rate: float
    valid_event_scores: int
    event_mean_atr: float
    event_sum_atr: float
    event_profit_factor: float
    event_win_rate: float
    event_take_profits: int
    event_stop_losses: int
    event_timeouts: int
    event_ambiguous: int
    valid_independent_replays: int
    independent_replay_mean_atr: float
    independent_replay_sum_atr: float
    independent_replay_profit_factor: float
    independent_replay_win_rate: float
    independent_replay_take_profits: int
    independent_replay_stop_losses: int
    independent_replay_timeouts: int
    event_to_independent_mean_delta_atr: float
    path_disagreement_count: int
    path_disagreement_rate: float
    event_tp_to_replay_sl: int
    event_sl_to_replay_tp: int
    event_timeout_to_replay_tp: int
    event_timeout_to_replay_sl: int
    raw_gap_mean_atr: float
    raw_gap_median_atr: float
    raw_gap_p90_abs_atr: float
    adjusted_gap_mean_atr: float
    adjusted_gap_median_atr: float
    adjusted_gap_p90_abs_atr: float
    adverse_adjusted_gap_rate: float
    chronological_trades: int
    chronological_wins: int
    chronological_losses: int
    chronological_win_rate: float
    chronological_total_cash_pnl: float
    chronological_final_balance: float
    chronological_return_percent: float
    chronological_gross_profit: float
    chronological_gross_loss: float
    chronological_profit_factor: float
    chronological_max_drawdown_cash: float
    chronological_take_profits: int
    chronological_stop_losses: int
    chronological_timeouts: int
    skipped_while_open: int
    skipped_winners: int
    skipped_losers: int
    skipped_timeouts: int
    skipped_independent_sum_atr: float
    skipped_independent_mean_atr: float
    executed_independent_mean_atr: float
    invalid_events: int
    invalid_replays: int
    positive_months: int
    negative_months: int
    pass_gate: int


@dataclass(frozen=True)
class ExecutionGapSelectionRow:
    entry_delay_bars: int
    same_bar_policy: str
    spread_mode: str
    spread_value: float
    train_chronological_profit_factor: float
    train_chronological_total_cash_pnl: float
    validation_chronological_trades: int
    validation_chronological_profit_factor: float
    validation_chronological_total_cash_pnl: float
    validation_chronological_final_balance: float
    validation_event_mean_atr: float
    validation_independent_replay_mean_atr: float
    validation_event_to_independent_mean_delta_atr: float
    validation_skipped_winners: int
    validation_skipped_losers: int
    validation_skipped_independent_sum_atr: float
    test_chronological_trades: int
    test_chronological_profit_factor: float
    test_chronological_total_cash_pnl: float
    test_chronological_final_balance: float
    test_event_mean_atr: float
    test_independent_replay_mean_atr: float
    test_event_to_independent_mean_delta_atr: float
    test_skipped_winners: int
    test_skipped_losers: int
    test_skipped_independent_sum_atr: float
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    validation_score: float
    diagnostic_flags: str


@dataclass(frozen=True)
class ExecutionGapReport:
    symbol: str
    timeframe: str
    flat_path: str
    meta_path: str
    sampled_universe: str
    flat_rows: int
    sampled_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    target_id: str
    side_mapping: str
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    event_lookahead_bars: int
    hold_bars: int
    tp_atr: float
    sl_atr: float
    entry_delay_grid: list[int]
    same_bar_policy_grid: list[str]
    spread_value_grid: list[float]
    evaluated_configs: int
    validation_pass_configs: int
    transfer_pass_configs: int
    selected_entry_delay_bars: int
    selected_same_bar_policy: str
    selected_spread_value: float
    selected_validation_chronological_profit_factor: float
    selected_test_chronological_profit_factor: float
    selected_validation_chronological_total_cash_pnl: float
    selected_test_chronological_total_cash_pnl: float
    selected_transfer_pass_gate: int
    top_config_rows: list[dict[str, Any]]
    split_rows_preview: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_grid_csv: str
    output_selection_csv: str
    output_monthly_csv: str
    output_events_csv: str
    production_status: str


def parse_int_grid(text: str, default: Sequence[int]) -> list[int]:
    raw = str(text or "").strip()
    if not raw:
        return [int(value) for value in default]
    values: list[int] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip()
        if item:
            values.append(max(int(item), 0))
    return values or [int(value) for value in default]


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip()
        if item:
            values.append(max(float(item), 0.0))
    return values or [float(value) for value in default]


def parse_policy_grid(text: str, default: Sequence[str]) -> list[str]:
    allowed = {"stop_first", "tp_first"}
    raw = str(text or "").strip()
    tokens = [item.strip().lower() for item in raw.replace(";", ",").split(",") if item.strip()]
    values = tokens or [str(value) for value in default]
    invalid = sorted(set(values) - allowed)
    if invalid:
        raise RuntimeError(f"Unsupported same-bar policies: {invalid}; allowed={sorted(allowed)}")
    return values


def first_hit_policy(policy: str) -> str:
    return "target_first" if str(policy) == "tp_first" else "stop_first"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the execution gap between Phase160A bottom-buy event scoring and Phase161A replay.",
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
    parser.add_argument("--entry-delays", default="0,1,2,3")
    parser.add_argument("--same-bar-policies", default="stop_first,tp_first")
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-values", default="0,0.06")
    parser.add_argument("--tp-atr", type=float, default=1.0)
    parser.add_argument("--sl-atr", type=float, default=0.75)
    parser.add_argument("--event-lookahead-bars", type=int, default=24)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--validation-min-trades", type=int, default=20)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=20)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--score-metric", choices=("chronological_pnl", "chronological_pf", "independent_mean_atr"), default="chronological_pnl")
    parser.add_argument("--max-event-rows", type=int, default=20000)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase162A pivot bottom-buy execution gap audit")
    return parser.parse_args(argv)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    return float(numerator / denominator) if abs(float(denominator)) > 1e-12 else float(default)


def score_profit_factor(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0:
        return 0.0
    gross_profit = float(np.sum(arr[arr > 0]))
    gross_loss = float(abs(np.sum(arr[arr < 0])))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def outcome_from_hits(target_hit: int, stop_hit: int) -> str:
    if int(target_hit):
        return OUTCOME_TP
    if int(stop_hit):
        return OUTCOME_SL
    return OUTCOME_TIMEOUT


def summarize_scores(values: Sequence[float], outcomes: Sequence[str]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64)
    wins = arr > 0
    return {
        "count": int(len(arr)),
        "mean": float(np.mean(arr)) if len(arr) else 0.0,
        "sum": float(np.sum(arr)) if len(arr) else 0.0,
        "profit_factor": score_profit_factor(arr),
        "win_rate": float(np.mean(wins)) if len(arr) else 0.0,
        "take_profits": int(sum(1 for outcome in outcomes if outcome == OUTCOME_TP)),
        "stop_losses": int(sum(1 for outcome in outcomes if outcome == OUTCOME_SL)),
        "timeouts": int(sum(1 for outcome in outcomes if outcome == OUTCOME_TIMEOUT)),
    }


def percentile_abs(values: Sequence[float], percentile: float) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0:
        return 0.0
    return float(np.percentile(np.abs(arr), percentile))


def event_score_path(
    frame: pd.DataFrame,
    row_id: int,
    delay: int,
    atr: np.ndarray,
    args: argparse.Namespace,
    same_bar_policy: str,
) -> EventScorePath | None:
    signal_row = int(row_id) + max(int(delay), 0)
    future_start = signal_row + 1
    future_end = min(len(frame), signal_row + 1 + int(args.event_lookahead_bars))
    if signal_row >= len(frame) or future_start >= future_end:
        return None
    atr_value = float(atr[signal_row])
    if not np.isfinite(atr_value) or atr_value <= 0:
        return None
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    score, target_hit, stop_hit, ambiguous = first_hit_score(
        high[future_start:future_end],
        low[future_start:future_end],
        close[future_start:future_end],
        float(close[signal_row]),
        atr_value,
        float(args.tp_atr),
        float(args.sl_atr),
        "BUY",
        first_hit_policy(same_bar_policy),
        str(args.timeout_score_mode),
    )
    return EventScorePath(
        score_atr=float(score),
        outcome=outcome_from_hits(target_hit, stop_hit),
        target_hit=int(target_hit),
        stop_hit=int(stop_hit),
        ambiguous=int(ambiguous),
        entry_row_id=int(signal_row),
        entry_price=float(close[signal_row]),
    )


def replay_path(
    frame: pd.DataFrame,
    row_id: int,
    delay: int,
    atr: np.ndarray,
    args: argparse.Namespace,
    same_bar_policy: str,
    spread_value: float,
) -> ReplayPath | None:
    signal_row = int(row_id) + max(int(delay), 0)
    if signal_row >= len(frame) - 1:
        return None
    atr_value = float(atr[signal_row])
    if not np.isfinite(atr_value) or atr_value <= 0:
        return None
    tp_distance = atr_value * float(args.tp_atr)
    sl_distance = atr_value * float(args.sl_atr)
    trade_args = SimpleNamespace(
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        same_bar_policy=str(same_bar_policy),
    )
    path = trade_path(
        frame,
        signal_row,
        ACTION_BUY,
        tp_distance,
        sl_distance,
        int(args.hold_bars),
        trade_args,
    )
    if path is None:
        return None
    points, entry_row, exit_row, entry, tp, sl, exit_price, outcome = path
    return ReplayPath(
        score_atr=float(points / atr_value) if atr_value > 0 else 0.0,
        score_risk_r=float(points / sl_distance) if sl_distance > 0 else 0.0,
        points_pnl=float(points),
        entry_row_id=int(entry_row),
        exit_row_id=int(exit_row),
        entry=float(entry),
        tp=float(tp),
        sl=float(sl),
        exit_price=float(exit_price),
        outcome=str(outcome),
        tp_distance=float(tp_distance),
        sl_distance=float(sl_distance),
        atr_value=float(atr_value),
    )


def gap_stats(
    frame: pd.DataFrame,
    row_id: int,
    delay: int,
    atr: np.ndarray,
    args: argparse.Namespace,
    spread_value: float,
) -> tuple[float, float, float, float, float] | None:
    signal_row = int(row_id) + max(int(delay), 0)
    entry_row = signal_row + 1
    if signal_row >= len(frame) or entry_row >= len(frame):
        return None
    atr_value = float(atr[signal_row])
    if not np.isfinite(atr_value) or atr_value <= 0:
        return None
    signal_close = float(frame.at[signal_row, "close"])
    raw_open = float(frame.at[entry_row, "open"])
    half_spread = spread_abs(raw_open, str(args.spread_mode), float(spread_value)) / 2.0
    adjusted_entry = raw_open + half_spread
    raw_gap = (raw_open - signal_close) / atr_value
    adjusted_gap = (adjusted_entry - signal_close) / atr_value
    return float(signal_close), float(raw_open), float(adjusted_entry), float(raw_gap), float(adjusted_gap)


def monthly_key(frame: pd.DataFrame, row_id: int) -> str:
    return str(frame.at[int(row_id), "timestamp"])[:7]


def make_pass_gate(split: str, row: Mapping[str, Any], args: argparse.Namespace) -> int:
    if split == "validation":
        return int(
            int(row["chronological_trades"]) >= int(args.validation_min_trades)
            and float(row["chronological_profit_factor"]) >= float(args.validation_min_profit_factor)
            and float(row["chronological_final_balance"]) >= float(args.validation_min_final_balance)
        )
    if split == "test":
        return int(
            int(row["chronological_trades"]) >= int(args.test_min_trades)
            and float(row["chronological_profit_factor"]) >= float(args.test_min_profit_factor)
            and float(row["chronological_final_balance"]) >= float(args.test_min_final_balance)
        )
    return int(int(row["chronological_trades"]) > 0)


def evaluate_config_split(
    split: str,
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    local_indices: np.ndarray,
    candidate_mask: np.ndarray,
    atr: np.ndarray,
    delay: int,
    same_bar_policy: str,
    spread_value: float,
    args: argparse.Namespace,
    event_rows_remaining: int,
) -> tuple[ExecutionGapSplitRow, list[dict[str, Any]], list[ExecutionEventRow], int]:
    candidate_locals = [int(local) for local in np.asarray(local_indices, dtype=np.int64) if bool(candidate_mask[int(local)])]
    event_scores: list[float] = []
    event_outcomes: list[str] = []
    replay_scores: list[float] = []
    replay_outcomes: list[str] = []
    executed_replay_scores: list[float] = []
    skipped_replay_scores: list[float] = []
    raw_gaps: list[float] = []
    adjusted_gaps: list[float] = []
    path_disagreement_count = 0
    event_tp_to_replay_sl = 0
    event_sl_to_replay_tp = 0
    event_timeout_to_replay_tp = 0
    event_timeout_to_replay_sl = 0
    invalid_events = 0
    invalid_replays = 0
    event_ambiguous = 0
    balance = float(args.initial_capital)
    balances = [balance]
    open_until = -1
    chronological_cash_pnls: list[float] = []
    chronological_outcomes: list[str] = []
    skipped_while_open = 0
    skipped_winners = 0
    skipped_losers = 0
    skipped_timeouts = 0
    monthly: dict[str, dict[str, Any]] = {}
    event_rows: list[ExecutionEventRow] = []
    trade_number = 0

    def month_bucket(month: str) -> dict[str, Any]:
        if month not in monthly:
            monthly[month] = {
                "split": split,
                "month": month,
                "entry_delay_bars": int(delay),
                "same_bar_policy": str(same_bar_policy),
                "spread_mode": str(args.spread_mode),
                "spread_value": float(spread_value),
                "trades": 0,
                "cash_pnl": 0.0,
                "take_profits": 0,
                "stop_losses": 0,
                "timeouts": 0,
                "skipped_while_open": 0,
                "skipped_winners": 0,
                "skipped_losers": 0,
                "skipped_timeouts": 0,
                "skipped_independent_sum_atr": 0.0,
            }
        return monthly[month]

    for local in candidate_locals:
        row_id = int(selected_rows[local])
        signal_row = row_id + max(int(delay), 0)
        month = monthly_key(frame, row_id)
        event = event_score_path(frame, row_id, delay, atr, args, same_bar_policy)
        replay = replay_path(frame, row_id, delay, atr, args, same_bar_policy, spread_value)
        gaps = gap_stats(frame, row_id, delay, atr, args, spread_value)
        if event is None:
            invalid_events += 1
        else:
            event_scores.append(float(event.score_atr))
            event_outcomes.append(event.outcome)
            event_ambiguous += int(event.ambiguous)
        if replay is None:
            invalid_replays += 1
        else:
            replay_scores.append(float(replay.score_atr))
            replay_outcomes.append(replay.outcome)
        if gaps is not None:
            _, _, _, raw_gap, adjusted_gap = gaps
            raw_gaps.append(raw_gap)
            adjusted_gaps.append(adjusted_gap)
        if event is not None and replay is not None and event.outcome != replay.outcome:
            path_disagreement_count += 1
            if event.outcome == OUTCOME_TP and replay.outcome == OUTCOME_SL:
                event_tp_to_replay_sl += 1
            if event.outcome == OUTCOME_SL and replay.outcome == OUTCOME_TP:
                event_sl_to_replay_tp += 1
            if event.outcome == OUTCOME_TIMEOUT and replay.outcome == OUTCOME_TP:
                event_timeout_to_replay_tp += 1
            if event.outcome == OUTCOME_TIMEOUT and replay.outcome == OUTCOME_SL:
                event_timeout_to_replay_sl += 1

        chronological_status = "invalid"
        chronological_cash_pnl = 0.0
        chronological_balance = balance
        chronological_trade_number = 0
        if replay is not None:
            if signal_row <= open_until:
                chronological_status = "skipped_while_open"
                skipped_while_open += 1
                skipped_replay_scores.append(float(replay.score_atr))
                bucket = month_bucket(month)
                bucket["skipped_while_open"] += 1
                bucket["skipped_independent_sum_atr"] += float(replay.score_atr)
                if replay.score_atr > 0:
                    skipped_winners += 1
                    bucket["skipped_winners"] += 1
                elif replay.score_atr < 0:
                    skipped_losers += 1
                    bucket["skipped_losers"] += 1
                else:
                    skipped_timeouts += 1
                    bucket["skipped_timeouts"] += 1
            else:
                chronological_status = "traded"
                trade_number += 1
                chronological_trade_number = trade_number
                risk_amount = max(balance * float(args.risk_per_trade), 0.0)
                quantity = risk_amount / replay.sl_distance if replay.sl_distance > 0 else 0.0
                chronological_cash_pnl = float(replay.points_pnl * quantity)
                balance += chronological_cash_pnl
                chronological_balance = balance
                balances.append(balance)
                chronological_cash_pnls.append(chronological_cash_pnl)
                chronological_outcomes.append(replay.outcome)
                executed_replay_scores.append(float(replay.score_atr))
                open_until = max(open_until, int(replay.exit_row_id))
                bucket = month_bucket(month)
                bucket["trades"] += 1
                bucket["cash_pnl"] += chronological_cash_pnl
                if replay.outcome == OUTCOME_TP:
                    bucket["take_profits"] += 1
                elif replay.outcome == OUTCOME_SL:
                    bucket["stop_losses"] += 1
                else:
                    bucket["timeouts"] += 1
                if balance <= 0:
                    # Match broker-style replay safety: once equity is exhausted,
                    # do not invent additional trades for this split/config.
                    break

        if event_rows_remaining > 0:
            signal_close, raw_open, adjusted_entry, raw_gap, adjusted_gap = gaps or (0.0, 0.0, 0.0, 0.0, 0.0)
            event_rows.append(
                ExecutionEventRow(
                    split=split,
                    timestamp=str(frame.at[row_id, "timestamp"]),
                    entry_delay_bars=int(delay),
                    same_bar_policy=str(same_bar_policy),
                    spread_mode=str(args.spread_mode),
                    spread_value=float(spread_value),
                    candidate_row_id=int(row_id),
                    signal_row_id=int(signal_row),
                    replay_entry_row_id=int(replay.entry_row_id if replay is not None else signal_row + 1),
                    event_entry_price=float(signal_close if event is None else event.entry_price),
                    raw_next_open=float(raw_open),
                    spread_adjusted_entry=float(adjusted_entry),
                    raw_close_to_next_open_gap_atr=float(raw_gap),
                    adjusted_entry_gap_atr=float(adjusted_gap),
                    event_score_atr=float(event.score_atr if event is not None else 0.0),
                    event_outcome=str(event.outcome if event is not None else "invalid"),
                    event_ambiguous=int(event.ambiguous if event is not None else 0),
                    replay_score_atr=float(replay.score_atr if replay is not None else 0.0),
                    replay_score_risk_r=float(replay.score_risk_r if replay is not None else 0.0),
                    replay_outcome=str(replay.outcome if replay is not None else "invalid"),
                    replay_exit_row_id=int(replay.exit_row_id if replay is not None else -1),
                    path_disagreement=int(event is not None and replay is not None and event.outcome != replay.outcome),
                    chronological_status=chronological_status,
                    chronological_trade_number=int(chronological_trade_number),
                    chronological_cash_pnl=float(chronological_cash_pnl),
                    chronological_balance=float(chronological_balance),
                )
            )
            event_rows_remaining -= 1

    event_metrics = summarize_scores(event_scores, event_outcomes)
    replay_metrics = summarize_scores(replay_scores, replay_outcomes)
    chronological_gross_profit = float(sum(value for value in chronological_cash_pnls if value > 0))
    chronological_gross_loss = float(abs(sum(value for value in chronological_cash_pnls if value < 0)))
    chronological_pf = (
        chronological_gross_profit / chronological_gross_loss
        if chronological_gross_loss > 0
        else (999.0 if chronological_gross_profit > 0 else 0.0)
    )
    chronological_wins = int(sum(1 for value in chronological_cash_pnls if value > 0))
    chronological_losses = int(sum(1 for value in chronological_cash_pnls if value < 0))
    positive_months = int(sum(1 for row in monthly.values() if float(row["cash_pnl"]) > 0))
    negative_months = int(sum(1 for row in monthly.values() if float(row["cash_pnl"]) < 0))
    row_values: dict[str, Any] = {
        "chronological_trades": len(chronological_cash_pnls),
        "chronological_profit_factor": chronological_pf,
        "chronological_final_balance": float(balance),
    }
    pass_gate = make_pass_gate(split, row_values, args)
    compared_paths = min(int(event_metrics["count"]), int(replay_metrics["count"]))
    split_row = ExecutionGapSplitRow(
        split=split,
        entry_delay_bars=int(delay),
        same_bar_policy=str(same_bar_policy),
        spread_mode=str(args.spread_mode),
        spread_value=float(spread_value),
        evaluated_rows=int(len(local_indices)),
        candidate_rows=int(len(candidate_locals)),
        candidate_rate=float(len(candidate_locals) / len(local_indices)) if len(local_indices) else 0.0,
        valid_event_scores=int(event_metrics["count"]),
        event_mean_atr=float(event_metrics["mean"]),
        event_sum_atr=float(event_metrics["sum"]),
        event_profit_factor=float(event_metrics["profit_factor"]),
        event_win_rate=float(event_metrics["win_rate"]),
        event_take_profits=int(event_metrics["take_profits"]),
        event_stop_losses=int(event_metrics["stop_losses"]),
        event_timeouts=int(event_metrics["timeouts"]),
        event_ambiguous=int(event_ambiguous),
        valid_independent_replays=int(replay_metrics["count"]),
        independent_replay_mean_atr=float(replay_metrics["mean"]),
        independent_replay_sum_atr=float(replay_metrics["sum"]),
        independent_replay_profit_factor=float(replay_metrics["profit_factor"]),
        independent_replay_win_rate=float(replay_metrics["win_rate"]),
        independent_replay_take_profits=int(replay_metrics["take_profits"]),
        independent_replay_stop_losses=int(replay_metrics["stop_losses"]),
        independent_replay_timeouts=int(replay_metrics["timeouts"]),
        event_to_independent_mean_delta_atr=float(replay_metrics["mean"] - event_metrics["mean"]),
        path_disagreement_count=int(path_disagreement_count),
        path_disagreement_rate=float(path_disagreement_count / compared_paths) if compared_paths else 0.0,
        event_tp_to_replay_sl=int(event_tp_to_replay_sl),
        event_sl_to_replay_tp=int(event_sl_to_replay_tp),
        event_timeout_to_replay_tp=int(event_timeout_to_replay_tp),
        event_timeout_to_replay_sl=int(event_timeout_to_replay_sl),
        raw_gap_mean_atr=float(np.mean(raw_gaps)) if raw_gaps else 0.0,
        raw_gap_median_atr=float(np.median(raw_gaps)) if raw_gaps else 0.0,
        raw_gap_p90_abs_atr=percentile_abs(raw_gaps, 90),
        adjusted_gap_mean_atr=float(np.mean(adjusted_gaps)) if adjusted_gaps else 0.0,
        adjusted_gap_median_atr=float(np.median(adjusted_gaps)) if adjusted_gaps else 0.0,
        adjusted_gap_p90_abs_atr=percentile_abs(adjusted_gaps, 90),
        adverse_adjusted_gap_rate=float(np.mean(np.asarray(adjusted_gaps) > 0)) if adjusted_gaps else 0.0,
        chronological_trades=len(chronological_cash_pnls),
        chronological_wins=chronological_wins,
        chronological_losses=chronological_losses,
        chronological_win_rate=float(chronological_wins / len(chronological_cash_pnls)) if chronological_cash_pnls else 0.0,
        chronological_total_cash_pnl=float(sum(chronological_cash_pnls)),
        chronological_final_balance=float(balance),
        chronological_return_percent=float((balance - float(args.initial_capital)) / float(args.initial_capital)) if float(args.initial_capital) else 0.0,
        chronological_gross_profit=float(chronological_gross_profit),
        chronological_gross_loss=float(chronological_gross_loss),
        chronological_profit_factor=float(chronological_pf),
        chronological_max_drawdown_cash=float(max_drawdown(balances)),
        chronological_take_profits=int(sum(1 for outcome in chronological_outcomes if outcome == OUTCOME_TP)),
        chronological_stop_losses=int(sum(1 for outcome in chronological_outcomes if outcome == OUTCOME_SL)),
        chronological_timeouts=int(sum(1 for outcome in chronological_outcomes if outcome == OUTCOME_TIMEOUT)),
        skipped_while_open=int(skipped_while_open),
        skipped_winners=int(skipped_winners),
        skipped_losers=int(skipped_losers),
        skipped_timeouts=int(skipped_timeouts),
        skipped_independent_sum_atr=float(sum(skipped_replay_scores)),
        skipped_independent_mean_atr=float(np.mean(skipped_replay_scores)) if skipped_replay_scores else 0.0,
        executed_independent_mean_atr=float(np.mean(executed_replay_scores)) if executed_replay_scores else 0.0,
        invalid_events=int(invalid_events),
        invalid_replays=int(invalid_replays),
        positive_months=positive_months,
        negative_months=negative_months,
        pass_gate=int(pass_gate),
    )
    return split_row, list(monthly.values()), event_rows, event_rows_remaining


def validation_score(selection: ExecutionGapSelectionRow, metric: str) -> float:
    if metric == "chronological_pf":
        return float(selection.validation_chronological_profit_factor)
    if metric == "independent_mean_atr":
        return float(selection.validation_independent_replay_mean_atr)
    return float(selection.validation_chronological_total_cash_pnl)


def diagnostic_flags(validation: ExecutionGapSplitRow, test: ExecutionGapSplitRow) -> list[str]:
    flags: list[str] = []
    if validation.event_mean_atr > 0 and validation.independent_replay_mean_atr < validation.event_mean_atr:
        flags.append("validation event-to-replay edge decay")
    if test.event_mean_atr > 0 and test.independent_replay_mean_atr < test.event_mean_atr:
        flags.append("test event-to-replay edge decay")
    if validation.skipped_winners > validation.skipped_losers:
        flags.append("validation skipped winners dominate")
    if test.skipped_winners > test.skipped_losers:
        flags.append("test skipped winners dominate")
    if validation.adjusted_gap_mean_atr > 0 or test.adjusted_gap_mean_atr > 0:
        flags.append("average BUY entry gap adverse")
    if validation.path_disagreement_rate > 0.2 or test.path_disagreement_rate > 0.2:
        flags.append("event/replay path disagreement high")
    if not flags:
        flags.append("no single dominant execution-gap flag")
    return flags


def build_selection_rows(split_rows: Sequence[ExecutionGapSplitRow], args: argparse.Namespace) -> list[ExecutionGapSelectionRow]:
    grouped: dict[tuple[int, str, str, float], dict[str, ExecutionGapSplitRow]] = {}
    for row in split_rows:
        key = (row.entry_delay_bars, row.same_bar_policy, row.spread_mode, row.spread_value)
        grouped.setdefault(key, {})[row.split] = row
    selections: list[ExecutionGapSelectionRow] = []
    for (delay, policy, spread_mode, spread_value), by_split in grouped.items():
        train = by_split.get("train")
        validation = by_split.get("validation")
        test = by_split.get("test")
        if validation is None or test is None:
            continue
        flags = diagnostic_flags(validation, test)
        selection = ExecutionGapSelectionRow(
            entry_delay_bars=int(delay),
            same_bar_policy=str(policy),
            spread_mode=str(spread_mode),
            spread_value=float(spread_value),
            train_chronological_profit_factor=float(train.chronological_profit_factor if train else 0.0),
            train_chronological_total_cash_pnl=float(train.chronological_total_cash_pnl if train else 0.0),
            validation_chronological_trades=int(validation.chronological_trades),
            validation_chronological_profit_factor=float(validation.chronological_profit_factor),
            validation_chronological_total_cash_pnl=float(validation.chronological_total_cash_pnl),
            validation_chronological_final_balance=float(validation.chronological_final_balance),
            validation_event_mean_atr=float(validation.event_mean_atr),
            validation_independent_replay_mean_atr=float(validation.independent_replay_mean_atr),
            validation_event_to_independent_mean_delta_atr=float(validation.event_to_independent_mean_delta_atr),
            validation_skipped_winners=int(validation.skipped_winners),
            validation_skipped_losers=int(validation.skipped_losers),
            validation_skipped_independent_sum_atr=float(validation.skipped_independent_sum_atr),
            test_chronological_trades=int(test.chronological_trades),
            test_chronological_profit_factor=float(test.chronological_profit_factor),
            test_chronological_total_cash_pnl=float(test.chronological_total_cash_pnl),
            test_chronological_final_balance=float(test.chronological_final_balance),
            test_event_mean_atr=float(test.event_mean_atr),
            test_independent_replay_mean_atr=float(test.independent_replay_mean_atr),
            test_event_to_independent_mean_delta_atr=float(test.event_to_independent_mean_delta_atr),
            test_skipped_winners=int(test.skipped_winners),
            test_skipped_losers=int(test.skipped_losers),
            test_skipped_independent_sum_atr=float(test.skipped_independent_sum_atr),
            validation_pass_gate=int(validation.pass_gate),
            test_pass_gate=int(test.pass_gate),
            transfer_pass_gate=int(validation.pass_gate and test.pass_gate),
            validation_score=0.0,
            diagnostic_flags=json.dumps(flags, ensure_ascii=False),
        )
        selections.append(
            ExecutionGapSelectionRow(
                **{**asdict(selection), "validation_score": validation_score(selection, str(args.score_metric))}
            )
        )
    return selections


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: ExecutionGapReport) -> str:
    top_rows = "".join(
        f"<tr><td>{int(row['entry_delay_bars'])}</td>"
        f"<td>{html.escape(str(row['same_bar_policy']))}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{int(row['validation_chronological_trades'])}</td>"
        f"<td>{float(row['validation_chronological_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['validation_chronological_profit_factor']):.3f}</td>"
        f"<td>{int(row['test_chronological_trades'])}</td>"
        f"<td>{float(row['test_chronological_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['test_chronological_profit_factor']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.top_config_rows[:50]
    )
    split_rows = "".join(
        f"<tr><td>{html.escape(str(row['split']))}</td>"
        f"<td>{int(row['entry_delay_bars'])}</td>"
        f"<td>{html.escape(str(row['same_bar_policy']))}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{int(row['candidate_rows'])}</td>"
        f"<td>{float(row['event_mean_atr']):.4f}</td>"
        f"<td>{float(row['independent_replay_mean_atr']):.4f}</td>"
        f"<td>{float(row['event_to_independent_mean_delta_atr']):.4f}</td>"
        f"<td>{int(row['chronological_trades'])}</td>"
        f"<td>{int(row['skipped_winners'])}/{int(row['skipped_losers'])}</td>"
        f"<td>{float(row['chronological_total_cash_pnl']):.3f}</td>"
        f"<td>{float(row['chronological_profit_factor']):.3f}</td></tr>"
        for row in report.split_rows_preview[:90]
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
.bad {{ color:#fca5a5; }} .good {{ color:#86efac; }} .warn {{ color:#fcd34d; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase162A execution-gap audit for the strict bottom-buy pivot diagnostic. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Selected validation-only diagnostic config</h2><pre>{html.escape(json.dumps({
        'entry_delay_bars': report.selected_entry_delay_bars,
        'same_bar_policy': report.selected_same_bar_policy,
        'spread_value': report.selected_spread_value,
        'validation_pf': report.selected_validation_chronological_profit_factor,
        'test_pf': report.selected_test_chronological_profit_factor,
        'validation_pnl': report.selected_validation_chronological_total_cash_pnl,
        'test_pnl': report.selected_test_chronological_total_cash_pnl,
        'transfer_pass_gate': report.selected_transfer_pass_gate,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Config selection rows</h2><table><thead><tr><th>Delay</th><th>Same-bar</th><th>Spread</th><th>Val trades</th><th>Val PnL</th><th>Val PF</th><th>Test trades</th><th>Test PnL</th><th>Test PF</th><th>Transfer</th></tr></thead><tbody>{top_rows}</tbody></table></section>
<section class="card"><h2>Execution-gap split preview</h2><table><thead><tr><th>Split</th><th>Delay</th><th>Same-bar</th><th>Spread</th><th>Candidates</th><th>Event mean ATR</th><th>Replay mean ATR</th><th>Delta</th><th>Chrono trades</th><th>Skipped W/L</th><th>Chrono PnL</th><th>Chrono PF</th></tr></thead><tbody>{split_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def evaluate_all(args: argparse.Namespace, frame: pd.DataFrame, selected_rows: np.ndarray, candidate_mask: np.ndarray) -> tuple[list[ExecutionGapSplitRow], list[dict[str, Any]], list[ExecutionEventRow]]:
    atr = resolve_atr(frame)
    train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
    split_specs = [("train", train_idx), ("validation", validation_idx), ("test", test_idx)]
    delays = parse_int_grid(args.entry_delays, (0, 1, 2, 3))
    policies = parse_policy_grid(args.same_bar_policies, ("stop_first", "tp_first"))
    spread_values = parse_float_grid(args.spread_values, (0.0, 0.06))
    split_rows: list[ExecutionGapSplitRow] = []
    monthly_rows: list[dict[str, Any]] = []
    event_rows: list[ExecutionEventRow] = []
    event_rows_remaining = max(int(args.max_event_rows), 0)
    for delay in delays:
        for policy in policies:
            for spread_value in spread_values:
                for split, split_idx in split_specs:
                    row, month_rows, events, event_rows_remaining = evaluate_config_split(
                        split,
                        frame,
                        selected_rows,
                        split_idx,
                        candidate_mask,
                        atr,
                        int(delay),
                        str(policy),
                        float(spread_value),
                        args,
                        event_rows_remaining,
                    )
                    split_rows.append(row)
                    monthly_rows.extend(month_rows)
                    event_rows.extend(events)
    return split_rows, monthly_rows, event_rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE162A PIVOT BOTTOM-BUY EXECUTION GAP AUDIT")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, meta_path = load_meta_sample_indices(args, len(frame))
        train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
        candidate_mask = build_bottom_buy_mask(frame, selected_rows, args)
        split_rows, monthly_rows, event_rows = evaluate_all(args, frame, selected_rows, candidate_mask)
        selection_rows = build_selection_rows(split_rows, args)
        ranked = sorted(
            selection_rows,
            key=lambda row: (
                row.transfer_pass_gate,
                row.validation_pass_gate,
                row.validation_score,
                row.validation_chronological_profit_factor,
                -row.validation_chronological_trades,
            ),
            reverse=True,
        )
        selected = ranked[0] if ranked else None
        grid_csv = output_dir / "latest_grid.csv"
        selection_csv = output_dir / "latest_selection.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        events_csv = output_dir / "latest_events.csv"
        write_csv(grid_csv, [asdict(row) for row in split_rows])
        write_csv(selection_csv, [asdict(row) for row in ranked])
        write_csv(monthly_csv, monthly_rows)
        write_csv(events_csv, [asdict(row) for row in event_rows])
        delays = parse_int_grid(args.entry_delays, (0, 1, 2, 3))
        policies = parse_policy_grid(args.same_bar_policies, ("stop_first", "tp_first"))
        spread_values = parse_float_grid(args.spread_values, (0.0, 0.06))
        report = ExecutionGapReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(meta_path or ""),
            sampled_universe=sampled_universe,
            flat_rows=int(len(frame)),
            sampled_rows=int(len(selected_rows)),
            train_rows=int(len(train_idx)),
            validation_rows=int(len(validation_idx)),
            test_rows=int(len(test_idx)),
            target_id=str(args.target_id),
            side_mapping="bottom_buy",
            recent_window_bars=int(args.recent_window_bars),
            pivot_zone_atr=float(args.pivot_zone_atr),
            top_position_threshold=float(args.top_position_threshold),
            bottom_position_threshold=float(args.bottom_position_threshold),
            exclude_both_zones=int(args.exclude_both_zones),
            min_range_width_atr=float(args.min_range_width_atr),
            max_range_width_atr=float(args.max_range_width_atr),
            event_lookahead_bars=int(args.event_lookahead_bars),
            hold_bars=int(args.hold_bars),
            tp_atr=float(args.tp_atr),
            sl_atr=float(args.sl_atr),
            entry_delay_grid=delays,
            same_bar_policy_grid=policies,
            spread_value_grid=spread_values,
            evaluated_configs=int(len(selection_rows)),
            validation_pass_configs=int(sum(row.validation_pass_gate for row in selection_rows)),
            transfer_pass_configs=int(sum(row.transfer_pass_gate for row in selection_rows)),
            selected_entry_delay_bars=int(selected.entry_delay_bars) if selected else 0,
            selected_same_bar_policy=str(selected.same_bar_policy) if selected else "",
            selected_spread_value=float(selected.spread_value) if selected else 0.0,
            selected_validation_chronological_profit_factor=float(selected.validation_chronological_profit_factor) if selected else 0.0,
            selected_test_chronological_profit_factor=float(selected.test_chronological_profit_factor) if selected else 0.0,
            selected_validation_chronological_total_cash_pnl=float(selected.validation_chronological_total_cash_pnl) if selected else 0.0,
            selected_test_chronological_total_cash_pnl=float(selected.test_chronological_total_cash_pnl) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            top_config_rows=[asdict(row) for row in ranked[:80]],
            split_rows_preview=[asdict(row) for row in split_rows[:120]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_grid_csv=str(grid_csv),
            output_selection_csv=str(selection_csv),
            output_monthly_csv=str(monthly_csv),
            output_events_csv=str(events_csv),
            production_status="BLOCKED — Phase162A execution-gap diagnostic only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase162A execution-gap audit complete")
        print(f"  configs          : {report.evaluated_configs}")
        print(f"  validation pass  : {report.validation_pass_configs}")
        print(f"  transfer pass    : {report.transfer_pass_configs}")
        print(f"  selected         : delay={report.selected_entry_delay_bars} same_bar={report.selected_same_bar_policy or 'none'} spread={report.selected_spread_value:g}")
        print(f"  selected val PF  : {report.selected_validation_chronological_profit_factor:.4f}")
        print(f"  selected test PF : {report.selected_test_chronological_profit_factor:.4f}")
        print(f"  output           : {report.output_json}")
        print(f"  elapsed          : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
