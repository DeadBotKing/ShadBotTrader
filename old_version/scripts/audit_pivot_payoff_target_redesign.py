"""Phase154A: pivot payoff / trade-outcome target redesign audit.

Phase152A/153A showed that changing pivot label density did not remove the
validation-to-test payoff sign flip. This phase audits trade-outcome targets
that are closer to a tradable question:

    Did the BUY barrier hit before the BUY stop?
    Did the SELL barrier hit before the SELL stop?

It is research-only and does not train a model.
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

from train_pivot_pattern_image_cnn import selected_indices, split_indices  # noqa: E402
from train_pivot_pattern_recognition import (  # noqa: E402
    ACTION_BUY,
    ACTION_HOLD,
    ACTION_NAMES,
    ACTION_SELL,
    class_counts,
)
from train_pivot_pattern_sequence_wavenet import default_meta_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_payoff_target_redesign")
DEFAULT_CANDIDATES = (
    "B1:balanced_24_rr1:24:0.35:0.75:0.75:0.0;"
    "B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1;"
    "B3:dense_24_half_atr:24:0.50:0.50:0.50:0.0;"
    "B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1;"
    "B5:short_12_rr1:12:0.35:0.75:0.75:0.0;"
    "B6:wide_36_rr1:36:0.35:0.75:0.75:0.0"
)


@dataclass(frozen=True)
class PayoffCandidate:
    candidate_id: str
    label: str
    lookahead_bars: int
    pivot_zone_atr: float
    tp_atr: float
    sl_atr: float
    min_score_edge: float


@dataclass(frozen=True)
class SplitPayoffRow:
    candidate_id: str
    split: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    sell_count: int
    hold_count: int
    buy_count: int
    sell_rate: float
    hold_rate: float
    buy_rate: float
    actionable_rate: float
    buy_score_mean: float
    sell_score_mean: float
    buy_score_positive_rate: float
    sell_score_positive_rate: float
    selected_trade_r_mean: float
    selected_trade_r_sum: float
    selected_trade_win_rate: float
    action_psi_vs_train: float


@dataclass(frozen=True)
class CandidatePayoffRow:
    candidate_id: str
    label: str
    lookahead_bars: int
    pivot_zone_atr: float
    tp_atr: float
    sl_atr: float
    min_score_edge: float
    sampled_rows: int
    train_sell_rate: float
    train_hold_rate: float
    train_buy_rate: float
    validation_sell_rate: float
    validation_hold_rate: float
    validation_buy_rate: float
    test_sell_rate: float
    test_hold_rate: float
    test_buy_rate: float
    train_actionable_rate: float
    validation_actionable_rate: float
    test_actionable_rate: float
    validation_psi_vs_train: float
    test_psi_vs_train: float
    train_buy_score_mean: float
    validation_buy_score_mean: float
    test_buy_score_mean: float
    train_sell_score_mean: float
    validation_sell_score_mean: float
    test_sell_score_mean: float
    train_selected_trade_r_mean: float
    validation_selected_trade_r_mean: float
    test_selected_trade_r_mean: float
    buy_score_sign_flip: int
    sell_score_sign_flip: int
    label_stability_pass_gate: int
    payoff_stability_pass_gate: int
    candidate_ready_for_tensor_gate: int
    warnings: str


@dataclass(frozen=True)
class PayoffTargetAuditReport:
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
    candidates: list[dict[str, Any]]
    completed_candidates: int
    label_stable_candidates: int
    payoff_stable_candidates: int
    tensor_ready_candidates: int
    best_candidate_id: str
    best_candidate_reason: str
    rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    output_monthly_csv: str
    production_status: str


def safe_slug(text: str) -> str:
    cleaned = []
    for character in str(text).strip().lower():
        if character.isalnum():
            cleaned.append(character)
        elif character in {"-", "_", " ", "."}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "candidate"


def parse_candidates(text: str) -> list[PayoffCandidate]:
    """Parse candidate specs.

    Format per item:

        ID:label:lookahead:pivot_zone_atr:tp_atr:sl_atr:min_score_edge
    """
    candidates: list[PayoffCandidate] = []
    for raw_item in str(text or "").split(";"):
        item = raw_item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 7:
            raise RuntimeError(
                "candidate specs must use "
                "ID:label:lookahead:pivot_zone_atr:tp_atr:sl_atr:min_score_edge; "
                f"got: {item!r}"
            )
        candidate = PayoffCandidate(
            candidate_id=parts[0].upper() or f"B{len(candidates) + 1}",
            label=safe_slug(parts[1]),
            lookahead_bars=max(int(parts[2]), 1),
            pivot_zone_atr=max(float(parts[3]), 0.01),
            tp_atr=max(float(parts[4]), 0.01),
            sl_atr=max(float(parts[5]), 0.01),
            min_score_edge=max(float(parts[6]), 0.0),
        )
        if candidate.candidate_id in {existing.candidate_id for existing in candidates}:
            raise RuntimeError(f"duplicate candidate id: {candidate.candidate_id}")
        candidates.append(candidate)
    if not candidates:
        raise RuntimeError("At least one payoff target candidate is required")
    return candidates


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit first-hit/barrier pivot payoff target candidates before training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "target_first", "skip_ambiguous"), default="stop_first")
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--psi-warning-threshold", type=float, default=0.20)
    parser.add_argument("--min-train-actionable-rate", type=float, default=0.02)
    parser.add_argument("--min-validation-actionable-rate", type=float, default=0.02)
    parser.add_argument("--min-test-actionable-rate", type=float, default=0.02)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase154A pivot payoff target redesign audit")
    return parser.parse_args(argv)


def read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Flat input file not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    required = {"timestamp", "high", "low", "close"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"flat file is missing required columns: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if "row_id" not in result.columns:
        result["row_id"] = np.arange(len(result), dtype=np.int64)
    return result


def load_meta_sample_indices(args: argparse.Namespace, flat_rows: int) -> tuple[np.ndarray, str, Path | None]:
    meta_path = Path(args.meta_path) if str(args.meta_path).strip() else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    if meta_path.exists():
        with np.load(meta_path, allow_pickle=True) as meta:
            if "sample_indices" in meta.files:
                sample_indices = np.asarray(meta["sample_indices"], dtype=np.int64)
                selected_tensor_rows = selected_indices(len(sample_indices), int(args.max_samples))
                selected_flat_rows = sample_indices[selected_tensor_rows]
                selected_flat_rows = selected_flat_rows[(selected_flat_rows >= 0) & (selected_flat_rows < flat_rows)]
                if len(selected_flat_rows):
                    return selected_flat_rows.astype(np.int64), "meta_sample_indices", meta_path
    start = max(int(args.window_size) - 1, 0)
    flat_positions = np.arange(start, flat_rows, dtype=np.int64)
    selected = selected_indices(len(flat_positions), int(args.max_samples))
    return flat_positions[selected].astype(np.int64), "flat_window_positions", meta_path if meta_path.exists() else None


def resolve_atr(frame: pd.DataFrame) -> np.ndarray:
    for column in ("h4_atr_for_risk", "h4_atr", "src5m_h4_atr", "m5_atr", "atr"):
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
            return values.to_numpy(dtype=np.float64)
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    previous_close = np.r_[close[0], close[:-1]]
    true_range = np.maximum(high - low, np.maximum(np.abs(high - previous_close), np.abs(low - previous_close)))
    atr = pd.Series(true_range).rolling(14, min_periods=1).mean().to_numpy(dtype=np.float64)
    return atr


def split_frames(sampled: pd.DataFrame, args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    train_idx, validation_idx, test_idx = split_indices(len(sampled), args.train_frac, args.val_frac, args.purge_gap)
    return {
        "train": sampled.iloc[train_idx].copy().reset_index(drop=True),
        "validation": sampled.iloc[validation_idx].copy().reset_index(drop=True),
        "test": sampled.iloc[test_idx].copy().reset_index(drop=True),
    }


def action_distribution(frame: pd.DataFrame) -> dict[str, float]:
    actions = frame["target_action"].astype(int) if len(frame) else pd.Series([], dtype=int)
    return {
        "SELL": float(np.mean(actions == ACTION_SELL)) if len(frame) else 0.0,
        "HOLD": float(np.mean(actions == ACTION_HOLD)) if len(frame) else 0.0,
        "BUY": float(np.mean(actions == ACTION_BUY)) if len(frame) else 0.0,
    }


def action_psi(current: Mapping[str, float], baseline: Mapping[str, float]) -> float:
    eps = 1e-6
    total = 0.0
    for key in ("SELL", "HOLD", "BUY"):
        actual = max(float(current.get(key, 0.0)), eps)
        expected = max(float(baseline.get(key, 0.0)), eps)
        total += (actual - expected) * float(np.log(actual / expected))
    return float(total)


def sign(value: float, eps: float = 1e-9) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def sign_flip(train_value: float, validation_value: float, test_value: float) -> int:
    train_sign = sign(train_value)
    validation_sign = sign(validation_value)
    test_sign = sign(test_value)
    return int(train_sign != 0 and validation_sign == train_sign and test_sign not in {0, train_sign})


def first_hit_score(
    high_path: np.ndarray,
    low_path: np.ndarray,
    close_path: np.ndarray,
    entry: float,
    atr_value: float,
    tp_atr: float,
    sl_atr: float,
    side: str,
    same_bar_policy: str,
    timeout_score_mode: str,
) -> tuple[float, int, int, int]:
    """Return R score plus hit diagnostics for one hypothetical side.

    score is expressed in ATR units of the configured barrier: +tp_atr on target,
    -sl_atr on stop. Timeout is zero by default or horizon close drift in ATR
    units when timeout_score_mode=close_r.
    """
    if atr_value <= 0 or not np.isfinite(atr_value) or len(high_path) == 0:
        return 0.0, 0, 0, 0
    if side == "BUY":
        target_price = entry + tp_atr * atr_value
        stop_price = entry - sl_atr * atr_value
    else:
        target_price = entry - tp_atr * atr_value
        stop_price = entry + sl_atr * atr_value
    ambiguous = 0
    for high, low in zip(high_path, low_path):
        if side == "BUY":
            target_hit = bool(high >= target_price)
            stop_hit = bool(low <= stop_price)
        else:
            target_hit = bool(low <= target_price)
            stop_hit = bool(high >= stop_price)
        if target_hit and stop_hit:
            ambiguous = 1
            if same_bar_policy == "target_first":
                return float(tp_atr), 1, 0, ambiguous
            if same_bar_policy == "skip_ambiguous":
                return 0.0, 0, 0, ambiguous
            return -float(sl_atr), 0, 1, ambiguous
        if target_hit:
            return float(tp_atr), 1, 0, ambiguous
        if stop_hit:
            return -float(sl_atr), 0, 1, ambiguous
    if timeout_score_mode == "close_r" and len(close_path):
        drift = float(close_path[-1] - entry)
        if side == "SELL":
            drift = -drift
        return float(np.clip(drift / atr_value, -float(sl_atr), float(tp_atr))), 0, 0, ambiguous
    return 0.0, 0, 0, ambiguous


def apply_payoff_candidate(
    frame: pd.DataFrame,
    candidate: PayoffCandidate,
    recent_window_bars: int,
    same_bar_policy: str,
    timeout_score_mode: str,
) -> pd.DataFrame:
    result = frame.copy()
    n_rows = len(result)
    close = result["close"].to_numpy(dtype=np.float64)
    high = result["high"].to_numpy(dtype=np.float64)
    low = result["low"].to_numpy(dtype=np.float64)
    atr = resolve_atr(result)
    target = np.full(n_rows, ACTION_HOLD, dtype=np.int64)
    top_zone = np.zeros(n_rows, dtype=np.float64)
    bottom_zone = np.zeros(n_rows, dtype=np.float64)
    buy_score = np.zeros(n_rows, dtype=np.float64)
    sell_score = np.zeros(n_rows, dtype=np.float64)
    target_trade_r = np.zeros(n_rows, dtype=np.float64)
    buy_target_hits = np.zeros(n_rows, dtype=np.float64)
    buy_stop_hits = np.zeros(n_rows, dtype=np.float64)
    sell_target_hits = np.zeros(n_rows, dtype=np.float64)
    sell_stop_hits = np.zeros(n_rows, dtype=np.float64)
    ambiguous_hits = np.zeros(n_rows, dtype=np.float64)
    target_available = np.zeros(n_rows, dtype=np.float64)

    for index in range(n_rows):
        atr_value = float(atr[index])
        future_start = index + 1
        future_end = min(n_rows, index + 1 + candidate.lookahead_bars)
        if not np.isfinite(atr_value) or atr_value <= 0 or future_start >= future_end:
            continue
        recent_start = max(0, index - max(recent_window_bars, 1) + 1)
        recent_high = float(np.nanmax(high[recent_start : index + 1]))
        recent_low = float(np.nanmin(low[recent_start : index + 1]))
        recent_width = max(recent_high - recent_low, 1e-9)
        position = (float(close[index]) - recent_low) / recent_width
        near_top = (recent_high - close[index] <= candidate.pivot_zone_atr * atr_value) or position >= 0.75
        near_bottom = (close[index] - recent_low <= candidate.pivot_zone_atr * atr_value) or position <= 0.25
        top_zone[index] = float(near_top)
        bottom_zone[index] = float(near_bottom)
        buy_value, buy_target, buy_stop, buy_amb = first_hit_score(
            high[future_start:future_end],
            low[future_start:future_end],
            close[future_start:future_end],
            float(close[index]),
            atr_value,
            candidate.tp_atr,
            candidate.sl_atr,
            "BUY",
            same_bar_policy,
            timeout_score_mode,
        )
        sell_value, sell_target, sell_stop, sell_amb = first_hit_score(
            high[future_start:future_end],
            low[future_start:future_end],
            close[future_start:future_end],
            float(close[index]),
            atr_value,
            candidate.tp_atr,
            candidate.sl_atr,
            "SELL",
            same_bar_policy,
            timeout_score_mode,
        )
        buy_score[index] = buy_value
        sell_score[index] = sell_value
        buy_target_hits[index] = buy_target
        buy_stop_hits[index] = buy_stop
        sell_target_hits[index] = sell_target
        sell_stop_hits[index] = sell_stop
        ambiguous_hits[index] = max(buy_amb, sell_amb)
        target_available[index] = 1.0
        is_buy = near_bottom and buy_value > 0 and (buy_value - sell_value) >= candidate.min_score_edge
        is_sell = near_top and sell_value > 0 and (sell_value - buy_value) >= candidate.min_score_edge
        if is_buy and is_sell:
            if buy_value >= sell_value:
                is_sell = False
            else:
                is_buy = False
        if is_buy:
            target[index] = ACTION_BUY
            target_trade_r[index] = buy_value
        elif is_sell:
            target[index] = ACTION_SELL
            target_trade_r[index] = sell_value

    result["target_action"] = target
    result["target_top_zone"] = top_zone
    result["target_bottom_zone"] = bottom_zone
    result["target_buy_trade_r"] = buy_score
    result["target_sell_trade_r"] = sell_score
    result["target_trade_r"] = target_trade_r
    result["target_trade_win"] = (target_trade_r > 0).astype(float)
    result["target_buy_first_target_hit"] = buy_target_hits
    result["target_buy_first_stop_hit"] = buy_stop_hits
    result["target_sell_first_target_hit"] = sell_target_hits
    result["target_sell_first_stop_hit"] = sell_stop_hits
    result["target_same_bar_ambiguous"] = ambiguous_hits
    result["target_available"] = target_available
    return result


def split_summary(candidate_id: str, name: str, frame: pd.DataFrame, train_dist: Mapping[str, float]) -> SplitPayoffRow:
    rows = len(frame)
    dist = action_distribution(frame)
    actionable = frame[frame["target_action"].astype(int) != ACTION_HOLD]
    return SplitPayoffRow(
        candidate_id=candidate_id,
        split=name,
        rows=rows,
        first_timestamp=str(frame["timestamp"].iloc[0]) if rows else "",
        last_timestamp=str(frame["timestamp"].iloc[-1]) if rows else "",
        sell_count=int((frame["target_action"].astype(int) == ACTION_SELL).sum()) if rows else 0,
        hold_count=int((frame["target_action"].astype(int) == ACTION_HOLD).sum()) if rows else 0,
        buy_count=int((frame["target_action"].astype(int) == ACTION_BUY).sum()) if rows else 0,
        sell_rate=float(dist["SELL"]),
        hold_rate=float(dist["HOLD"]),
        buy_rate=float(dist["BUY"]),
        actionable_rate=float(dist["SELL"] + dist["BUY"]),
        buy_score_mean=float(frame["target_buy_trade_r"].mean()) if rows else 0.0,
        sell_score_mean=float(frame["target_sell_trade_r"].mean()) if rows else 0.0,
        buy_score_positive_rate=float(np.mean(frame["target_buy_trade_r"].to_numpy(dtype=float) > 0)) if rows else 0.0,
        sell_score_positive_rate=float(np.mean(frame["target_sell_trade_r"].to_numpy(dtype=float) > 0)) if rows else 0.0,
        selected_trade_r_mean=float(actionable["target_trade_r"].mean()) if len(actionable) else 0.0,
        selected_trade_r_sum=float(actionable["target_trade_r"].sum()) if len(actionable) else 0.0,
        selected_trade_win_rate=float(actionable["target_trade_win"].mean()) if len(actionable) else 0.0,
        action_psi_vs_train=0.0 if name == "train" else action_psi(dist, train_dist),
    )


def monthly_rows(candidate_id: str, sampled: pd.DataFrame, train_dist: Mapping[str, float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    work = sampled.copy()
    work["month"] = work["timestamp"].dt.strftime("%Y-%m")
    for month, group in work.groupby("month", sort=True):
        dist = action_distribution(group)
        actionable = group[group["target_action"].astype(int) != ACTION_HOLD]
        rows.append(
            {
                "candidate_id": candidate_id,
                "month": str(month),
                "rows": int(len(group)),
                "sell_rate": float(dist["SELL"]),
                "hold_rate": float(dist["HOLD"]),
                "buy_rate": float(dist["BUY"]),
                "actionable_rate": float(dist["SELL"] + dist["BUY"]),
                "buy_score_mean": float(group["target_buy_trade_r"].mean()) if len(group) else 0.0,
                "sell_score_mean": float(group["target_sell_trade_r"].mean()) if len(group) else 0.0,
                "selected_trade_r_mean": float(actionable["target_trade_r"].mean()) if len(actionable) else 0.0,
                "selected_trade_r_sum": float(actionable["target_trade_r"].sum()) if len(actionable) else 0.0,
                "action_psi_vs_train": action_psi(dist, train_dist),
            }
        )
    return rows


def candidate_audit(
    base: pd.DataFrame,
    selected_rows: np.ndarray,
    candidate: PayoffCandidate,
    args: argparse.Namespace,
) -> tuple[CandidatePayoffRow, list[SplitPayoffRow], list[dict[str, Any]]]:
    relabeled = apply_payoff_candidate(
        base,
        candidate,
        max(int(args.recent_window_bars), 1),
        str(args.same_bar_policy),
        str(args.timeout_score_mode),
    )
    usable_rows = selected_rows[selected_rows < len(relabeled)]
    sampled = relabeled.iloc[usable_rows].copy().reset_index(drop=True)
    sampled = sampled[sampled["target_available"] >= 0.5].copy().reset_index(drop=True)
    splits = split_frames(sampled, args)
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    train_dist = action_distribution(train)
    split_rows = [
        split_summary(candidate.candidate_id, name, split_frame, train_dist)
        for name, split_frame in splits.items()
    ]
    split_lookup = {row.split: row for row in split_rows}
    train_row = split_lookup["train"]
    validation_row = split_lookup["validation"]
    test_row = split_lookup["test"]
    validation_psi = validation_row.action_psi_vs_train
    test_psi = test_row.action_psi_vs_train
    buy_flip = sign_flip(
        train_row.buy_score_mean, validation_row.buy_score_mean, test_row.buy_score_mean
    )
    sell_flip = sign_flip(
        train_row.sell_score_mean, validation_row.sell_score_mean, test_row.sell_score_mean
    )
    warnings: list[str] = []
    if validation_psi > float(args.psi_warning_threshold):
        warnings.append(f"validation action PSI exceeds threshold: {validation_psi:.4f}")
    if test_psi > float(args.psi_warning_threshold):
        warnings.append(f"test action PSI exceeds threshold: {test_psi:.4f}")
    if buy_flip:
        warnings.append("buy trade-outcome score mean flips sign from validation to test")
    if sell_flip:
        warnings.append("sell trade-outcome score mean flips sign from validation to test")
    label_pass = int(
        validation_psi <= float(args.psi_warning_threshold)
        and test_psi <= float(args.psi_warning_threshold)
        and train_row.actionable_rate >= float(args.min_train_actionable_rate)
        and validation_row.actionable_rate >= float(args.min_validation_actionable_rate)
        and test_row.actionable_rate >= float(args.min_test_actionable_rate)
    )
    payoff_pass = int(not buy_flip and not sell_flip)
    ready = int(label_pass and payoff_pass)
    candidate_row = CandidatePayoffRow(
        candidate_id=candidate.candidate_id,
        label=candidate.label,
        lookahead_bars=int(candidate.lookahead_bars),
        pivot_zone_atr=float(candidate.pivot_zone_atr),
        tp_atr=float(candidate.tp_atr),
        sl_atr=float(candidate.sl_atr),
        min_score_edge=float(candidate.min_score_edge),
        sampled_rows=len(sampled),
        train_sell_rate=float(train_row.sell_rate),
        train_hold_rate=float(train_row.hold_rate),
        train_buy_rate=float(train_row.buy_rate),
        validation_sell_rate=float(validation_row.sell_rate),
        validation_hold_rate=float(validation_row.hold_rate),
        validation_buy_rate=float(validation_row.buy_rate),
        test_sell_rate=float(test_row.sell_rate),
        test_hold_rate=float(test_row.hold_rate),
        test_buy_rate=float(test_row.buy_rate),
        train_actionable_rate=float(train_row.actionable_rate),
        validation_actionable_rate=float(validation_row.actionable_rate),
        test_actionable_rate=float(test_row.actionable_rate),
        validation_psi_vs_train=float(validation_psi),
        test_psi_vs_train=float(test_psi),
        train_buy_score_mean=float(train_row.buy_score_mean),
        validation_buy_score_mean=float(validation_row.buy_score_mean),
        test_buy_score_mean=float(test_row.buy_score_mean),
        train_sell_score_mean=float(train_row.sell_score_mean),
        validation_sell_score_mean=float(validation_row.sell_score_mean),
        test_sell_score_mean=float(test_row.sell_score_mean),
        train_selected_trade_r_mean=float(train_row.selected_trade_r_mean),
        validation_selected_trade_r_mean=float(validation_row.selected_trade_r_mean),
        test_selected_trade_r_mean=float(test_row.selected_trade_r_mean),
        buy_score_sign_flip=int(buy_flip),
        sell_score_sign_flip=int(sell_flip),
        label_stability_pass_gate=int(label_pass),
        payoff_stability_pass_gate=int(payoff_pass),
        candidate_ready_for_tensor_gate=int(ready),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )
    return candidate_row, split_rows, monthly_rows(candidate.candidate_id, sampled, train_dist)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def choose_best(rows: Sequence[CandidatePayoffRow]) -> tuple[str, str]:
    ready = [row for row in rows if row.candidate_ready_for_tensor_gate]
    if ready:
        ranked = sorted(
            ready,
            key=lambda row: (
                row.test_selected_trade_r_mean,
                -abs(row.test_actionable_rate - row.validation_actionable_rate),
                -row.test_psi_vs_train,
            ),
            reverse=True,
        )
        selected = ranked[0]
        return selected.candidate_id, "ready candidate with best test selected_trade_r_mean diagnostic"
    label_stable = [row for row in rows if row.label_stability_pass_gate]
    if label_stable:
        ranked = sorted(
            label_stable,
            key=lambda row: (
                row.payoff_stability_pass_gate,
                -row.buy_score_sign_flip - row.sell_score_sign_flip,
                -row.test_psi_vs_train,
                row.test_selected_trade_r_mean,
            ),
            reverse=True,
        )
        selected = ranked[0]
        return selected.candidate_id, "no training-ready candidate; best label-stable diagnostic only"
    return "", "no candidate passed label stability"


def render_html(title: str, report: PayoffTargetAuditReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['label']))}</td>"
        f"<td>{int(row['lookahead_bars'])}</td>"
        f"<td>{float(row['pivot_zone_atr']):.3f}</td>"
        f"<td>{float(row['tp_atr']):.3f}</td>"
        f"<td>{float(row['sl_atr']):.3f}</td>"
        f"<td>{float(row['validation_psi_vs_train']):.4f}</td>"
        f"<td>{float(row['test_psi_vs_train']):.4f}</td>"
        f"<td>{float(row['train_actionable_rate']):.3f}</td>"
        f"<td>{float(row['validation_actionable_rate']):.3f}</td>"
        f"<td>{float(row['test_actionable_rate']):.3f}</td>"
        f"<td>{float(row['train_buy_score_mean']):.4f}</td>"
        f"<td>{float(row['validation_buy_score_mean']):.4f}</td>"
        f"<td>{float(row['test_buy_score_mean']):.4f}</td>"
        f"<td>{float(row['train_sell_score_mean']):.4f}</td>"
        f"<td>{float(row['validation_sell_score_mean']):.4f}</td>"
        f"<td>{float(row['test_sell_score_mean']):.4f}</td>"
        f"<td>{int(row['candidate_ready_for_tensor_gate'])}</td></tr>"
        for row in report.rows
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
.badge {{ display:inline-block; border:1px solid #64748b; border-radius:999px; padding:4px 10px; margin:2px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase154A first-hit/barrier payoff target audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Summary</h2><p><span class="badge">completed={report.completed_candidates}</span><span class="badge">label stable={report.label_stable_candidates}</span><span class="badge">payoff stable={report.payoff_stable_candidates}</span><span class="badge">tensor ready={report.tensor_ready_candidates}</span><span class="badge">best={html.escape(report.best_candidate_id or 'none')}</span></p><p>{html.escape(report.best_candidate_reason)}</p></section>
<section class="card"><h2>Candidates</h2><table><thead><tr><th>ID</th><th>Label</th><th>Lookahead</th><th>Zone ATR</th><th>TP ATR</th><th>SL ATR</th><th>Val PSI</th><th>Test PSI</th><th>Train act</th><th>Val act</th><th>Test act</th><th>Train buy mean</th><th>Val buy mean</th><th>Test buy mean</th><th>Train sell mean</th><th>Val sell mean</th><th>Test sell mean</th><th>Ready</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE154A PIVOT PAYOFF / TRADE-OUTCOME TARGET REDESIGN AUDIT")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, resolved_meta_path = load_meta_sample_indices(args, len(frame))
        candidates = parse_candidates(args.candidates)
        print(f"  flat rows   : {len(frame):,}")
        print(f"  sampled     : {len(selected_rows):,} ({sampled_universe})")
        print("  candidates  : " + ", ".join(candidate.candidate_id for candidate in candidates))
        candidate_rows: list[CandidatePayoffRow] = []
        split_rows_all: list[SplitPayoffRow] = []
        monthly_all: list[dict[str, Any]] = []
        for candidate in candidates:
            print(
                f"  [candidate] {candidate.candidate_id} {candidate.label} "
                f"lookahead={candidate.lookahead_bars} zone={candidate.pivot_zone_atr} "
                f"tp={candidate.tp_atr} sl={candidate.sl_atr} edge={candidate.min_score_edge}"
            )
            candidate_row, split_rows, monthly_rows_for_candidate = candidate_audit(
                frame, selected_rows, candidate, args
            )
            candidate_rows.append(candidate_row)
            split_rows_all.extend(split_rows)
            monthly_all.extend(monthly_rows_for_candidate)
        candidate_dicts = [asdict(row) for row in candidate_rows]
        split_dicts = [asdict(row) for row in split_rows_all]
        candidates_csv = output_dir / "latest_candidates.csv"
        splits_csv = output_dir / "latest_splits.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        write_csv(candidates_csv, candidate_dicts)
        write_csv(splits_csv, split_dicts)
        write_csv(monthly_csv, monthly_all)
        sampled_for_rows = frame.iloc[selected_rows].copy().reset_index(drop=True)
        split_sizes = split_frames(sampled_for_rows, args)
        best_id, best_reason = choose_best(candidate_rows)
        report = PayoffTargetAuditReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(resolved_meta_path or ""),
            sampled_universe=sampled_universe,
            flat_rows=len(frame),
            sampled_rows=len(selected_rows),
            train_rows=len(split_sizes["train"]),
            validation_rows=len(split_sizes["validation"]),
            test_rows=len(split_sizes["test"]),
            candidates=[asdict(candidate) for candidate in candidates],
            completed_candidates=len(candidate_rows),
            label_stable_candidates=sum(int(row.label_stability_pass_gate) for row in candidate_rows),
            payoff_stable_candidates=sum(int(row.payoff_stability_pass_gate) for row in candidate_rows),
            tensor_ready_candidates=sum(int(row.candidate_ready_for_tensor_gate) for row in candidate_rows),
            best_candidate_id=best_id,
            best_candidate_reason=best_reason,
            rows=candidate_dicts,
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_candidates_csv=str(candidates_csv),
            output_splits_csv=str(splits_csv),
            output_monthly_csv=str(monthly_csv),
            production_status="BLOCKED — Phase154A research payoff target audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase154A payoff target audit complete")
        print(f"  completed      : {report.completed_candidates}")
        print(f"  label stable   : {report.label_stable_candidates}")
        print(f"  payoff stable  : {report.payoff_stable_candidates}")
        print(f"  tensor ready   : {report.tensor_ready_candidates}")
        print(f"  best candidate : {report.best_candidate_id or 'none'}")
        print(f"  output         : {report.output_json}")
        print(f"  elapsed        : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
