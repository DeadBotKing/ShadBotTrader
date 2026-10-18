"""Phase181B: Entry Event Discovery Framework.

This diagnostic phase deliberately separates entry discovery from profit-target
training. It asks whether a market state at candle ``t`` creates a valid setup,
whether a future trigger creates an actual entry, and whether the triggered
entry has clean MFE/MAE structure after broker costs.

Research only:
- no model training
- no paper/live trading
- no Phase134
- no gate relaxation
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

from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/entry_event_discovery")
DEFAULT_STORAGE = Path("datasets")
DEFAULT_TIMEFRAMES = "1H,4H,1D"
DEFAULT_FAMILIES = (
    "E1_BREAKOUT:breakout_entry:breakout:24:0.05:1.0:0:3:12:1.5:0.75:20:12:0.25:1.10:0.45;"
    "E2_PULLBACK_REJECTION:pullback_rejection_entry:pullback_rejection:24:0.03:1.0:0:3:12:1.5:0.75:20:12:0.20:1.00:0.45;"
    "E3_CONTINUATION:impulse_continuation_entry:continuation:12:0.03:0.5:0:2:10:1.2:0.75:20:12:0.45:1.20:0.50"
)
SUPPORTED_FAMILY_TYPES = {"breakout", "pullback_rejection", "continuation"}
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
LABEL_BUY = 1
LABEL_SELL = -1
LABEL_NONE = 0


@dataclass(frozen=True)
class EntryFamilySpec:
    family_id: str
    label: str
    family_type: str
    recent_window_bars: int
    buffer_atr: float
    min_width_atr: float
    max_width_atr: float
    trigger_horizon_bars: int
    quality_bars: int
    mfe_atr: float
    mae_atr: float
    trend_window_bars: int
    compression_window_bars: int
    min_body_atr: float
    min_expansion_ratio: float
    pullback_position: float


@dataclass(frozen=True)
class TimeframeHealthRow:
    timeframe: str
    flat_path: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    duplicate_timestamps: int
    missing_timestamp_rows: int
    nonfinite_ohlc_cells: int
    invalid_ohlc_rows: int
    atr_nonpositive_rows: int
    health_gate: int


@dataclass(frozen=True)
class CostRow:
    timeframe: str
    split: str
    rows: int
    spread_mode: str
    spread_value: float
    atr_median: float
    full_spread_atr_median: float
    full_spread_atr_p90: float
    cost_feasible_gate: int


@dataclass(frozen=True)
class EventAttempt:
    timeframe: str
    family_id: str
    family_type: str
    setup_row: int
    setup_timestamp: str
    side: str
    setup_gate: int
    trigger_gate: int
    quality_gate: int
    trigger_row: int
    entry_row: int
    trigger_timestamp: str
    entry_timestamp: str
    trigger_price: float
    entry_price: float
    raw_entry_price: float
    spread_abs: float
    atr_value: float
    mfe_atr: float
    mae_atr: float
    mfe_before_mae_gate: int
    replay_outcome: str
    replay_score_atr: float
    position: float
    width_atr: float
    body_atr: float
    close_location: float
    trend_return_atr: float
    expansion_ratio: float


@dataclass(frozen=True)
class SplitMetricsRow:
    timeframe: str
    family_id: str
    family_type: str
    split: str
    rows: int
    setup_attempts: int
    triggered_events: int
    buy_events: int
    sell_events: int
    no_entry_rows: int
    event_rate: float
    buy_share: float
    sell_share: float
    direction_balance: float
    quality_pass_events: int
    quality_pass_rate: float
    timeout_events: int
    fail_events: int
    mean_mfe_atr: float
    mean_mae_atr: float
    median_mfe_atr: float
    median_mae_atr: float
    mfe_mae_ratio: float
    replay_profit_factor: float
    mean_replay_score_atr: float
    label_psi_vs_train: float
    max_feature_abs_smd: float
    mean_feature_abs_smd: float
    density_gate: int
    direction_balance_gate: int
    temporal_stability_gate: int
    mfe_mae_gate: int
    replay_gate: int
    feature_separability_gate: int
    split_pass_gate: int


@dataclass(frozen=True)
class WalkForwardRow:
    timeframe: str
    family_id: str
    family_type: str
    fold: int
    train_events: int
    validation_events: int
    test_events: int
    train_event_rate: float
    validation_event_rate: float
    test_event_rate: float
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_gate: int
    validation_gate: int
    test_gate: int
    pass_gate: int


@dataclass(frozen=True)
class FamilySummaryRow:
    timeframe: str
    family_id: str
    label: str
    family_type: str
    recent_window_bars: int
    buffer_atr: float
    trigger_horizon_bars: int
    quality_bars: int
    mfe_atr: float
    mae_atr: float
    train_events: int
    validation_events: int
    test_events: int
    train_event_rate: float
    validation_event_rate: float
    test_event_rate: float
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_replay_profit_factor: float
    validation_replay_profit_factor: float
    test_replay_profit_factor: float
    train_feature_smd: float
    validation_feature_smd: float
    test_feature_smd: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    density_gate: int
    direction_balance_gate: int
    temporal_stability_gate: int
    mfe_mae_gate: int
    replay_gate: int
    feature_separability_gate: int
    cost_gate: int
    entry_family_ready_gate: int
    failure_reasons: str


@dataclass(frozen=True)
class DecisionRow:
    route_id: str
    status: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class Phase181BReport:
    symbol: str
    timeframes: list[str]
    spread_mode: str
    spread_value: float
    evaluated_timeframes: int
    evaluated_families: int
    ready_families: int
    selected_timeframe: str
    selected_family_id: str
    selected_family_type: str
    selected_family_ready_gate: int
    entry_event_discovery_ready_gate: int
    no_training_gate: int
    no_paper_live_gate: int
    health_rows: list[dict[str, Any]]
    cost_rows: list[dict[str, Any]]
    family_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_families_csv: str
    output_events_csv: str
    output_replay_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_mfe_mae_csv: str
    output_cost_csv: str
    output_feature_separability_csv: str
    output_decision_matrix_csv: str
    production_status: str


def safe_slug(text: str) -> str:
    cleaned: list[str] = []
    for char in str(text).strip():
        if char.isalnum():
            cleaned.append(char)
        elif char in {"-", "_", " ", "."}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "item"


def canonical_timeframe(text: str) -> str:
    value = str(text or "").strip().upper()
    if value in {"H1", "1H"}:
        return "1H"
    if value in {"H4", "4H", "4"}:
        return "4H"
    if value in {"D1", "1D", "D", "1"}:
        return "1D"
    if value in {"M5", "5M", "5"}:
        return "5M"
    return value


def parse_timeframes(text: str) -> list[str]:
    values = [canonical_timeframe(item) for item in str(text or "").replace(";", ",").split(",") if item.strip()]
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
    return output or ["1H", "4H", "1D"]


def parse_families(text: str) -> list[EntryFamilySpec]:
    families: list[EntryFamilySpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 16:
            raise RuntimeError(
                "family format must be "
                "ID:label:type:rw:buffer:min_width:max_width:trigger_horizon:quality_bars:"
                "mfe:mae:trend_window:compression_window:min_body_atr:min_expansion_ratio:pullback_position"
            )
        family_type = parts[2].strip().lower()
        if family_type not in SUPPORTED_FAMILY_TYPES:
            raise RuntimeError(f"Unsupported entry family type: {family_type}")
        families.append(
            EntryFamilySpec(
                family_id=safe_slug(parts[0]),
                label=safe_slug(parts[1]),
                family_type=family_type,
                recent_window_bars=max(int(parts[3]), 2),
                buffer_atr=max(float(parts[4]), 0.0),
                min_width_atr=max(float(parts[5]), 0.0),
                max_width_atr=max(float(parts[6]), 0.0),
                trigger_horizon_bars=max(int(parts[7]), 1),
                quality_bars=max(int(parts[8]), 1),
                mfe_atr=max(float(parts[9]), 0.01),
                mae_atr=max(float(parts[10]), 0.01),
                trend_window_bars=max(int(parts[11]), 1),
                compression_window_bars=max(int(parts[12]), 2),
                min_body_atr=max(float(parts[13]), 0.0),
                min_expansion_ratio=max(float(parts[14]), 0.0),
                pullback_position=min(max(float(parts[15]), 0.01), 0.99),
            )
        )
    if not families:
        raise RuntimeError("At least one entry family is required")
    return families


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase181B entry-event discovery audit. No model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframes", default=DEFAULT_TIMEFRAMES)
    parser.add_argument("--h1-flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--h4-flat-path", default="datasets/processed/XAUUSD/4H/v1.parquet")
    parser.add_argument("--d1-flat-path", default="datasets/processed/XAUUSD/1D/v1.parquet")
    parser.add_argument("--m5-flat-path", default="datasets/processed/XAUUSD/5M/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--families", default=DEFAULT_FAMILIES)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.4)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=10)
    parser.add_argument("--max-folds", type=int, default=6)
    parser.add_argument("--fold-train-frac", type=float, default=0.50)
    parser.add_argument("--fold-validation-frac", type=float, default=0.12)
    parser.add_argument("--fold-test-frac", type=float, default=0.12)
    parser.add_argument("--fold-step-frac", type=float, default=0.08)
    parser.add_argument("--min-train-events", type=int, default=30)
    parser.add_argument("--min-validation-events", type=int, default=8)
    parser.add_argument("--min-test-events", type=int, default=8)
    parser.add_argument("--min-side-events", type=int, default=3)
    parser.add_argument("--max-event-rate", type=float, default=0.35)
    parser.add_argument("--min-direction-balance", type=float, default=0.20)
    parser.add_argument("--max-label-psi", type=float, default=0.30)
    parser.add_argument("--min-quality-pass-rate", type=float, default=0.45)
    parser.add_argument("--min-mfe-mae-ratio", type=float, default=1.10)
    parser.add_argument("--min-replay-profit-factor", type=float, default=1.05)
    parser.add_argument("--min-feature-separability", type=float, default=0.05)
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=3)
    parser.add_argument("--max-event-rows", type=int, default=200000)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase181B entry-event discovery framework")
    return parser.parse_args(argv)


def resolve_flat_path(timeframe: str, args: argparse.Namespace) -> Path:
    requested_by_tf = {
        "1H": Path(str(args.h1_flat_path)),
        "4H": Path(str(args.h4_flat_path)),
        "1D": Path(str(args.d1_flat_path)),
        "5M": Path(str(args.m5_flat_path)),
    }
    requested = requested_by_tf.get(canonical_timeframe(timeframe), Path(str(args.h1_flat_path)))
    if requested.exists():
        return requested
    base = Path(args.storage_root) / "processed" / str(args.symbol).upper() / canonical_timeframe(timeframe)
    candidates = [
        base / "v1.parquet",
        base / "hybrid_telemetry_flat_latest.parquet",
        base / "pivot_pattern_sequence_flat_latest.parquet",
    ]
    candidates.extend(sorted(base.glob("*.parquet"), reverse=True))
    candidates.extend(sorted(base.glob("*.csv"), reverse=True))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"Flat file not found for {timeframe}. Requested={requested}; searched under {base}")


def read_ohlc_frame(path: Path, max_rows: int = 0) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"flat file not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    missing = sorted({"timestamp", "open", "high", "low", "close"} - set(frame.columns))
    if missing:
        raise RuntimeError(f"flat file is missing required columns: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if int(max_rows) > 0 and len(result) > int(max_rows):
        result = result.iloc[-int(max_rows) :].copy().reset_index(drop=True)
    if len(result) < 100:
        raise RuntimeError(f"Need at least 100 rows for entry-event discovery; got {len(result)}")
    return result


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    atr = np.zeros(n, dtype=np.float64)
    tr_sum = 0.0
    for index in range(n):
        true_range = float(high[index] - low[index])
        if index > 0:
            true_range = max(
                true_range,
                abs(float(high[index] - close[index - 1])),
                abs(float(low[index] - close[index - 1])),
            )
        if index < period:
            tr_sum += true_range
            atr[index] = tr_sum / float(index + 1)
        else:
            atr[index] = (atr[index - 1] * float(period - 1) + true_range) / float(period)
    return atr


def rolling_max(values: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(values)
    return series.rolling(max(int(window), 1), min_periods=1).max().to_numpy(dtype=np.float64)


def rolling_min(values: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(values)
    return series.rolling(max(int(window), 1), min_periods=1).min().to_numpy(dtype=np.float64)


def rolling_median(values: np.ndarray, window: int) -> np.ndarray:
    series = pd.Series(values)
    return series.rolling(max(int(window), 2), min_periods=1).median().to_numpy(dtype=np.float64)


def spread_abs(price: float, mode: str, value: float) -> float:
    if str(mode) == "fixed":
        return max(float(value), 0.0)
    return max(float(price) * float(value) / 100.0, 0.0)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(float(denominator)) <= 1e-12:
        return float(default)
    return float(numerator) / float(denominator)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def label_distribution(rows: Sequence[EventAttempt], split_indices_local: np.ndarray, total_rows: int) -> dict[int, float]:
    idx_set = set(int(value) for value in np.asarray(split_indices_local, dtype=np.int64))
    buy = sum(1 for row in rows if int(row.setup_row) in idx_set and row.trigger_gate and row.side == SIDE_BUY)
    sell = sum(1 for row in rows if int(row.setup_row) in idx_set and row.trigger_gate and row.side == SIDE_SELL)
    none = max(int(total_rows) - buy - sell, 0)
    denom = max(int(total_rows), 1)
    return {LABEL_BUY: buy / denom, LABEL_SELL: sell / denom, LABEL_NONE: none / denom}


def label_psi(current: Mapping[int, float], baseline: Mapping[int, float]) -> float:
    eps = 1e-6
    total = 0.0
    for key in (LABEL_SELL, LABEL_NONE, LABEL_BUY):
        actual = max(float(current.get(key, 0.0)), eps)
        expected = max(float(baseline.get(key, 0.0)), eps)
        total += (actual - expected) * float(np.log(actual / expected))
    return float(total)


def timeframe_health(timeframe: str, frame: pd.DataFrame, path: Path, atr: np.ndarray) -> TimeframeHealthRow:
    ohlc = frame[["open", "high", "low", "close"]].to_numpy(dtype=np.float64)
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    open_ = frame["open"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    invalid = (high < low) | (high < np.maximum(open_, close)) | (low > np.minimum(open_, close))
    nonfinite = int(np.sum(~np.isfinite(ohlc)))
    invalid_rows = int(np.sum(invalid))
    atr_bad = int(np.sum(~np.isfinite(atr) | (atr <= 0)))
    missing_timestamps = int(frame["timestamp"].isna().sum())
    duplicate_timestamps = int(frame["timestamp"].duplicated().sum())
    return TimeframeHealthRow(
        timeframe=timeframe,
        flat_path=str(path),
        rows=int(len(frame)),
        first_timestamp=str(frame["timestamp"].iloc[0]) if len(frame) else "",
        last_timestamp=str(frame["timestamp"].iloc[-1]) if len(frame) else "",
        duplicate_timestamps=duplicate_timestamps,
        missing_timestamp_rows=missing_timestamps,
        nonfinite_ohlc_cells=nonfinite,
        invalid_ohlc_rows=invalid_rows,
        atr_nonpositive_rows=atr_bad,
        health_gate=int(nonfinite == 0 and invalid_rows == 0 and missing_timestamps == 0 and atr_bad == 0),
    )


def cost_row(timeframe: str, split: str, frame: pd.DataFrame, indices: np.ndarray, atr: np.ndarray, args: argparse.Namespace) -> CostRow:
    idx = np.asarray(indices, dtype=np.int64)
    close = frame["close"].to_numpy(dtype=np.float64)
    atr_values = atr[idx] if len(idx) else np.asarray([], dtype=np.float64)
    spreads = np.asarray(
        [spread_abs(float(close[row]), str(args.spread_mode), float(args.spread_value)) for row in idx],
        dtype=np.float64,
    )
    spread_atr = spreads / np.maximum(atr_values, 1e-9) if len(idx) else np.asarray([], dtype=np.float64)
    median_spread_atr = float(np.median(spread_atr)) if len(spread_atr) else 999.0
    return CostRow(
        timeframe=timeframe,
        split=split,
        rows=int(len(idx)),
        spread_mode=str(args.spread_mode),
        spread_value=float(args.spread_value),
        atr_median=float(np.median(atr_values)) if len(atr_values) else 0.0,
        full_spread_atr_median=median_spread_atr,
        full_spread_atr_p90=float(np.percentile(spread_atr, 90)) if len(spread_atr) else 999.0,
        cost_feasible_gate=int(median_spread_atr <= float(args.max_median_spread_atr)),
    )


def setup_features(
    index: int,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    recent_high: np.ndarray,
    recent_low: np.ndarray,
    trend_window: int,
    expansion_ratio: float,
) -> dict[str, float]:
    width = max(float(recent_high[index] - recent_low[index]), 1e-9)
    atr_value = max(float(atr[index]), 1e-9)
    candle_range = max(float(high[index] - low[index]), 1e-9)
    body = float(close[index] - open_[index])
    trend_base = max(index - int(trend_window), 0)
    return {
        "position": float(np.clip((close[index] - recent_low[index]) / width, 0.0, 1.0)),
        "width_atr": safe_div(width, atr_value),
        "body_atr": safe_div(body, atr_value),
        "close_location": float(np.clip((close[index] - low[index]) / candle_range, 0.0, 1.0)),
        "trend_return_atr": safe_div(float(close[index] - close[trend_base]), atr_value),
        "expansion_ratio": float(expansion_ratio),
    }


def first_trigger(
    side: str,
    trigger_price: float,
    start: int,
    horizon: int,
    high: np.ndarray,
    low: np.ndarray,
) -> int:
    stop = min(len(high), int(start) + max(int(horizon), 1))
    for row in range(int(start), stop):
        if side == SIDE_BUY and float(high[row]) >= float(trigger_price):
            return int(row)
        if side == SIDE_SELL and float(low[row]) <= float(trigger_price):
            return int(row)
    return -1


def quality_path(
    side: str,
    entry_price: float,
    trigger_row: int,
    quality_bars: int,
    mfe_target_atr: float,
    mae_limit_atr: float,
    atr_value: float,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    args: argparse.Namespace,
) -> tuple[int, str, float, float, float]:
    stop = min(len(high), int(trigger_row) + max(int(quality_bars), 1))
    if trigger_row < 0 or trigger_row >= len(high) or stop <= trigger_row or atr_value <= 0:
        return 0, "no_trigger", 0.0, 0.0, 0.0
    max_mfe = 0.0
    max_mae = 0.0
    outcome = "timeout"
    score = 0.0
    for row in range(int(trigger_row), stop):
        half = spread_abs(float(close[row]), str(args.spread_mode), float(args.spread_value)) / 2.0
        if side == SIDE_BUY:
            favorable = float(high[row]) - half - float(entry_price)
            adverse = float(entry_price) - (float(low[row]) - half)
        else:
            favorable = float(entry_price) - (float(low[row]) + half)
            adverse = (float(high[row]) + half) - float(entry_price)
        mfe = max(0.0, favorable / float(atr_value))
        mae = max(0.0, adverse / float(atr_value))
        max_mfe = max(max_mfe, mfe)
        max_mae = max(max_mae, mae)
        hit_good = mfe >= float(mfe_target_atr)
        hit_bad = mae >= float(mae_limit_atr)
        if hit_good and hit_bad:
            if str(args.same_bar_policy) == "tp_first":
                return 1, "quality_pass_same_bar", float(max_mfe), float(max_mae), float(mfe_target_atr)
            return 0, "quality_fail_same_bar", float(max_mfe), float(max_mae), -float(mae_limit_atr)
        if hit_bad:
            return 0, "quality_fail_mae_first", float(max_mfe), float(max_mae), -float(mae_limit_atr)
        if hit_good:
            return 1, "quality_pass_mfe_first", float(max_mfe), float(max_mae), float(mfe_target_atr)
    if stop > trigger_row:
        half = spread_abs(float(close[stop - 1]), str(args.spread_mode), float(args.spread_value)) / 2.0
        if side == SIDE_BUY:
            exit_price = float(close[stop - 1]) - half
            drift = exit_price - float(entry_price)
        else:
            exit_price = float(close[stop - 1]) + half
            drift = float(entry_price) - exit_price
        score = float(np.clip(drift / float(atr_value), -float(mae_limit_atr), float(mfe_target_atr)))
    return 0, outcome, float(max_mfe), float(max_mae), float(score)


def make_attempt(
    timeframe: str,
    family: EntryFamilySpec,
    index: int,
    side: str,
    trigger_price: float,
    features: Mapping[str, float],
    frame: pd.DataFrame,
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    args: argparse.Namespace,
) -> EventAttempt:
    trigger_row = first_trigger(
        side,
        trigger_price,
        index + 1,
        family.trigger_horizon_bars,
        high,
        low,
    )
    atr_value = float(atr[index]) if 0 <= index < len(atr) else 0.0
    entry_row = trigger_row
    raw_entry = float(trigger_price) if trigger_row >= 0 else 0.0
    spread = spread_abs(raw_entry if raw_entry > 0 else float(close[index]), str(args.spread_mode), float(args.spread_value))
    half_spread = spread / 2.0
    if trigger_row >= 0:
        entry_price = raw_entry + half_spread if side == SIDE_BUY else raw_entry - half_spread
        quality_gate, replay_outcome, mfe_atr, mae_atr, replay_score = quality_path(
            side,
            entry_price,
            trigger_row,
            family.quality_bars,
            family.mfe_atr,
            family.mae_atr,
            atr_value,
            high,
            low,
            close,
            args,
        )
    else:
        entry_price = 0.0
        quality_gate = 0
        replay_outcome = "not_triggered"
        mfe_atr = 0.0
        mae_atr = 0.0
        replay_score = 0.0
    return EventAttempt(
        timeframe=timeframe,
        family_id=family.family_id,
        family_type=family.family_type,
        setup_row=int(index),
        setup_timestamp=str(frame.at[index, "timestamp"]),
        side=side,
        setup_gate=1,
        trigger_gate=int(trigger_row >= 0),
        quality_gate=int(quality_gate),
        trigger_row=int(trigger_row),
        entry_row=int(entry_row),
        trigger_timestamp=str(frame.at[trigger_row, "timestamp"]) if trigger_row >= 0 else "",
        entry_timestamp=str(frame.at[entry_row, "timestamp"]) if entry_row >= 0 else "",
        trigger_price=float(trigger_price),
        entry_price=float(entry_price),
        raw_entry_price=float(raw_entry),
        spread_abs=float(spread),
        atr_value=float(atr_value),
        mfe_atr=float(mfe_atr),
        mae_atr=float(mae_atr),
        mfe_before_mae_gate=int(quality_gate),
        replay_outcome=str(replay_outcome),
        replay_score_atr=float(replay_score),
        position=float(features.get("position", 0.0)),
        width_atr=float(features.get("width_atr", 0.0)),
        body_atr=float(features.get("body_atr", 0.0)),
        close_location=float(features.get("close_location", 0.0)),
        trend_return_atr=float(features.get("trend_return_atr", 0.0)),
        expansion_ratio=float(features.get("expansion_ratio", 0.0)),
    )


def discover_family_events(timeframe: str, family: EntryFamilySpec, frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace) -> list[EventAttempt]:
    open_ = frame["open"].to_numpy(dtype=np.float64)
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    recent_high = rolling_max(high, family.recent_window_bars)
    recent_low = rolling_min(low, family.recent_window_bars)
    prev_high = pd.Series(high).shift(1).rolling(family.recent_window_bars, min_periods=1).max().fillna(high[0]).to_numpy(dtype=np.float64)
    prev_low = pd.Series(low).shift(1).rolling(family.recent_window_bars, min_periods=1).min().fillna(low[0]).to_numpy(dtype=np.float64)
    candle_range = np.maximum(high - low, 1e-9)
    median_range = rolling_median(candle_range, family.compression_window_bars)
    events: list[EventAttempt] = []
    max_forward = max(family.trigger_horizon_bars + family.quality_bars + 1, 2)
    start_index = max(family.recent_window_bars, family.trend_window_bars, family.compression_window_bars, 2)
    end_index = max(start_index, len(frame) - max_forward)
    for index in range(start_index, end_index):
        atr_value = float(atr[index])
        if not np.isfinite(atr_value) or atr_value <= 0:
            continue
        width = max(float(recent_high[index] - recent_low[index]), 1e-9)
        width_atr = width / max(atr_value, 1e-9)
        if width_atr < float(family.min_width_atr):
            continue
        if float(family.max_width_atr) > 0 and width_atr > float(family.max_width_atr):
            continue
        expansion = safe_div(float(candle_range[index]), float(median_range[index]), 0.0)
        features = setup_features(index, open_, high, low, close, atr, recent_high, recent_low, family.trend_window_bars, expansion)
        position = float(features["position"])
        body_atr = float(features["body_atr"])
        close_location = float(features["close_location"])
        trend_return_atr = float(features["trend_return_atr"])
        buffer_distance = float(family.buffer_atr) * atr_value
        lower_wick_atr = max(0.0, min(open_[index], close[index]) - low[index]) / atr_value
        upper_wick_atr = max(0.0, high[index] - max(open_[index], close[index])) / atr_value
        if family.family_type == "breakout":
            if position >= 0.55:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_BUY,
                        float(recent_high[index] + buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
            if position <= 0.45:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_SELL,
                        float(recent_low[index] - buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
        elif family.family_type == "pullback_rejection":
            bullish_trend = trend_return_atr > 0 and close[index] >= close[max(index - family.trend_window_bars, 0)]
            bearish_trend = trend_return_atr < 0 and close[index] <= close[max(index - family.trend_window_bars, 0)]
            buy_rejection = close[index] > open_[index] and close_location >= 0.55 and lower_wick_atr >= max(family.buffer_atr, 0.01)
            sell_rejection = close[index] < open_[index] and close_location <= 0.45 and upper_wick_atr >= max(family.buffer_atr, 0.01)
            if bullish_trend and position <= family.pullback_position and buy_rejection:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_BUY,
                        float(high[index] + buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
            if bearish_trend and position >= 1.0 - family.pullback_position and sell_rejection:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_SELL,
                        float(low[index] - buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
        elif family.family_type == "continuation":
            buy_impulse = close[index] > prev_high[index] + buffer_distance and body_atr >= family.min_body_atr and expansion >= family.min_expansion_ratio
            sell_impulse = close[index] < prev_low[index] - buffer_distance and -body_atr >= family.min_body_atr and expansion >= family.min_expansion_ratio
            if buy_impulse:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_BUY,
                        float(high[index] + buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
            if sell_impulse:
                events.append(
                    make_attempt(
                        timeframe,
                        family,
                        index,
                        SIDE_SELL,
                        float(low[index] - buffer_distance),
                        features,
                        frame,
                        open_,
                        high,
                        low,
                        close,
                        atr,
                        args,
                    )
                )
    return events


def feature_matrix_for_rows(frame: pd.DataFrame, atr: np.ndarray, family: EntryFamilySpec) -> np.ndarray:
    open_ = frame["open"].to_numpy(dtype=np.float64)
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    recent_high = rolling_max(high, family.recent_window_bars)
    recent_low = rolling_min(low, family.recent_window_bars)
    candle_range = np.maximum(high - low, 1e-9)
    median_range = rolling_median(candle_range, family.compression_window_bars)
    features = np.zeros((len(frame), 6), dtype=np.float64)
    for index in range(len(frame)):
        expansion = safe_div(float(candle_range[index]), float(median_range[index]), 0.0)
        row = setup_features(index, open_, high, low, close, atr, recent_high, recent_low, family.trend_window_bars, expansion)
        features[index, :] = [
            row["position"],
            row["width_atr"],
            row["body_atr"],
            row["close_location"],
            row["trend_return_atr"],
            row["expansion_ratio"],
        ]
    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def feature_separability(
    frame: pd.DataFrame,
    atr: np.ndarray,
    family: EntryFamilySpec,
    events: Sequence[EventAttempt],
    indices: np.ndarray,
) -> tuple[float, float, list[dict[str, Any]]]:
    idx = np.asarray(indices, dtype=np.int64)
    if len(idx) == 0:
        return 0.0, 0.0, []
    features = feature_matrix_for_rows(frame, atr, family)
    labels = np.zeros(len(frame), dtype=np.int64)
    for event in events:
        if event.trigger_gate:
            labels[int(event.setup_row)] = 1
    idx = idx[(idx >= 0) & (idx < len(frame))]
    event_idx = idx[labels[idx] == 1]
    none_idx = idx[labels[idx] == 0]
    names = ["position", "width_atr", "body_atr", "close_location", "trend_return_atr", "expansion_ratio"]
    rows: list[dict[str, Any]] = []
    values: list[float] = []
    if len(event_idx) < 2 or len(none_idx) < 2:
        for name in names:
            rows.append({"feature": name, "abs_smd": 0.0, "event_mean": 0.0, "none_mean": 0.0})
        return 0.0, 0.0, rows
    for col, name in enumerate(names):
        event_values = features[event_idx, col]
        none_values = features[none_idx, col]
        event_mean = float(np.mean(event_values))
        none_mean = float(np.mean(none_values))
        pooled = float(np.sqrt((np.var(event_values) + np.var(none_values)) / 2.0))
        smd = abs(safe_div(event_mean - none_mean, pooled, 0.0))
        values.append(float(smd))
        rows.append(
            {
                "feature": name,
                "abs_smd": float(smd),
                "event_mean": event_mean,
                "none_mean": none_mean,
            }
        )
    return float(max(values) if values else 0.0), float(np.mean(values) if values else 0.0), rows


def split_metrics(
    timeframe: str,
    family: EntryFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    split: str,
    indices: np.ndarray,
    events: Sequence[EventAttempt],
    args: argparse.Namespace,
    train_dist: Mapping[int, float] | None,
) -> tuple[SplitMetricsRow, list[dict[str, Any]]]:
    idx = np.asarray(indices, dtype=np.int64)
    idx_set = set(int(value) for value in idx)
    split_events_all = [event for event in events if int(event.setup_row) in idx_set]
    triggered = [event for event in split_events_all if int(event.trigger_gate)]
    quality_pass = [event for event in triggered if int(event.quality_gate)]
    buys = [event for event in triggered if event.side == SIDE_BUY]
    sells = [event for event in triggered if event.side == SIDE_SELL]
    setup_attempts = len(split_events_all)
    event_count = len(triggered)
    rows = len(idx)
    buy_events = len(buys)
    sell_events = len(sells)
    no_entry_rows = max(rows - event_count, 0)
    event_rate = safe_div(event_count, rows)
    buy_share = safe_div(buy_events, event_count)
    sell_share = safe_div(sell_events, event_count)
    direction_balance = safe_div(min(buy_events, sell_events), max(buy_events, sell_events), 0.0) if event_count else 0.0
    quality_pass_rate = safe_div(len(quality_pass), event_count)
    fail_events = sum(1 for event in triggered if "fail" in event.replay_outcome)
    timeout_events = sum(1 for event in triggered if event.replay_outcome == "timeout")
    mfe_values = [float(event.mfe_atr) for event in triggered]
    mae_values = [float(event.mae_atr) for event in triggered]
    score_values = [float(event.replay_score_atr) for event in triggered]
    mean_mfe = float(np.mean(mfe_values)) if mfe_values else 0.0
    mean_mae = float(np.mean(mae_values)) if mae_values else 0.0
    median_mfe = float(np.median(mfe_values)) if mfe_values else 0.0
    median_mae = float(np.median(mae_values)) if mae_values else 0.0
    mfe_mae_ratio = safe_div(mean_mfe, mean_mae, 0.0)
    replay_pf = profit_factor(score_values)
    mean_score = float(np.mean(score_values)) if score_values else 0.0
    current_dist = label_distribution(events, idx, rows)
    psi = label_psi(current_dist, train_dist) if train_dist is not None else 0.0
    max_smd, mean_smd, feature_rows = feature_separability(frame, atr, family, events, idx)
    min_events = {
        "train": int(args.min_train_events),
        "validation": int(args.min_validation_events),
        "test": int(args.min_test_events),
    }.get(split, int(args.min_validation_events))
    density_gate = int(
        event_count >= min_events
        and buy_events >= int(args.min_side_events)
        and sell_events >= int(args.min_side_events)
        and event_rate <= float(args.max_event_rate)
    )
    direction_gate = int(direction_balance >= float(args.min_direction_balance))
    temporal_gate = int(psi <= float(args.max_label_psi))
    mfe_mae_gate = int(
        quality_pass_rate >= float(args.min_quality_pass_rate)
        and mfe_mae_ratio >= float(args.min_mfe_mae_ratio)
    )
    replay_gate = int(replay_pf >= float(args.min_replay_profit_factor) and mean_score >= 0.0)
    feature_gate = int(max_smd >= float(args.min_feature_separability))
    split_pass = int(
        density_gate
        and direction_gate
        and temporal_gate
        and mfe_mae_gate
        and replay_gate
        and feature_gate
    )
    metrics = SplitMetricsRow(
        timeframe=timeframe,
        family_id=family.family_id,
        family_type=family.family_type,
        split=split,
        rows=int(rows),
        setup_attempts=int(setup_attempts),
        triggered_events=int(event_count),
        buy_events=int(buy_events),
        sell_events=int(sell_events),
        no_entry_rows=int(no_entry_rows),
        event_rate=float(event_rate),
        buy_share=float(buy_share),
        sell_share=float(sell_share),
        direction_balance=float(direction_balance),
        quality_pass_events=int(len(quality_pass)),
        quality_pass_rate=float(quality_pass_rate),
        timeout_events=int(timeout_events),
        fail_events=int(fail_events),
        mean_mfe_atr=float(mean_mfe),
        mean_mae_atr=float(mean_mae),
        median_mfe_atr=float(median_mfe),
        median_mae_atr=float(median_mae),
        mfe_mae_ratio=float(mfe_mae_ratio),
        replay_profit_factor=float(replay_pf),
        mean_replay_score_atr=float(mean_score),
        label_psi_vs_train=float(psi),
        max_feature_abs_smd=float(max_smd),
        mean_feature_abs_smd=float(mean_smd),
        density_gate=density_gate,
        direction_balance_gate=direction_gate,
        temporal_stability_gate=temporal_gate,
        mfe_mae_gate=mfe_mae_gate,
        replay_gate=replay_gate,
        feature_separability_gate=feature_gate,
        split_pass_gate=split_pass,
    )
    feature_output = [
        {
            "timeframe": timeframe,
            "family_id": family.family_id,
            "family_type": family.family_type,
            "split": split,
            **row,
        }
        for row in feature_rows
    ]
    return metrics, feature_output


def idx_range(start: int, end: int) -> np.ndarray:
    return np.arange(int(start), int(end), dtype=np.int64)


def walkforward_rows_for_family(
    timeframe: str,
    family: EntryFamilySpec,
    frame: pd.DataFrame,
    atr: np.ndarray,
    events: Sequence[EventAttempt],
    args: argparse.Namespace,
) -> list[WalkForwardRow]:
    total_rows = len(frame)
    train_bars = max(int(total_rows * float(args.fold_train_frac)), 1)
    validation_bars = max(int(total_rows * float(args.fold_validation_frac)), 1)
    test_bars = max(int(total_rows * float(args.fold_test_frac)), 1)
    step_bars = max(int(total_rows * float(args.fold_step_frac)), 1)
    specs = build_fold_specs(
        total_rows,
        train_bars,
        validation_bars,
        test_bars,
        step_bars,
        int(args.purge_gap),
        int(args.max_folds),
    )
    rows: list[WalkForwardRow] = []
    for spec in specs:
        train_idx = idx_range(spec.train_start, spec.train_end)
        validation_idx = idx_range(spec.validation_start, spec.validation_end)
        test_idx = idx_range(spec.test_start, spec.test_end)
        train_dist = label_distribution(events, train_idx, len(train_idx))
        train_metrics, _ = split_metrics(timeframe, family, frame, atr, "train", train_idx, events, args, None)
        validation_metrics, _ = split_metrics(timeframe, family, frame, atr, "validation", validation_idx, events, args, train_dist)
        test_metrics, _ = split_metrics(timeframe, family, frame, atr, "test", test_idx, events, args, train_dist)
        pass_gate = int(
            train_metrics.split_pass_gate
            and validation_metrics.split_pass_gate
            and test_metrics.split_pass_gate
        )
        rows.append(
            WalkForwardRow(
                timeframe=timeframe,
                family_id=family.family_id,
                family_type=family.family_type,
                fold=int(spec.fold),
                train_events=int(train_metrics.triggered_events),
                validation_events=int(validation_metrics.triggered_events),
                test_events=int(test_metrics.triggered_events),
                train_event_rate=float(train_metrics.event_rate),
                validation_event_rate=float(validation_metrics.event_rate),
                test_event_rate=float(test_metrics.event_rate),
                train_quality_pass_rate=float(train_metrics.quality_pass_rate),
                validation_quality_pass_rate=float(validation_metrics.quality_pass_rate),
                test_quality_pass_rate=float(test_metrics.quality_pass_rate),
                validation_label_psi=float(validation_metrics.label_psi_vs_train),
                test_label_psi=float(test_metrics.label_psi_vs_train),
                train_gate=int(train_metrics.split_pass_gate),
                validation_gate=int(validation_metrics.split_pass_gate),
                test_gate=int(test_metrics.split_pass_gate),
                pass_gate=pass_gate,
            )
        )
    return rows


def family_failure_reasons(summary: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key in (
        "density_gate",
        "direction_balance_gate",
        "temporal_stability_gate",
        "mfe_mae_gate",
        "replay_gate",
        "feature_separability_gate",
        "cost_gate",
    ):
        if int(summary.get(key, 0)) == 0:
            reasons.append(f"{key}_failed")
    if float(summary.get("walkforward_pass_ratio", 0.0)) < 0.50:
        reasons.append("walkforward_pass_ratio_failed")
    if int(summary.get("entry_family_ready_gate", 0)) == 0:
        reasons.append("entry_family_ready_gate_failed")
    return reasons


def build_family_summary(
    timeframe: str,
    family: EntryFamilySpec,
    split_rows: Mapping[str, SplitMetricsRow],
    wf_rows: Sequence[WalkForwardRow],
    cost_rows_for_tf: Sequence[CostRow],
    args: argparse.Namespace,
) -> FamilySummaryRow:
    train = split_rows["train"]
    validation = split_rows["validation"]
    test = split_rows["test"]
    wf_pass = sum(int(row.pass_gate) for row in wf_rows)
    wf_total = len(wf_rows)
    wf_ratio = safe_div(wf_pass, wf_total)
    cost_gate = int(all(row.cost_feasible_gate for row in cost_rows_for_tf)) if cost_rows_for_tf else 0
    density_gate = int(train.density_gate and validation.density_gate and test.density_gate)
    direction_gate = int(train.direction_balance_gate and validation.direction_balance_gate and test.direction_balance_gate)
    temporal_gate = int(validation.temporal_stability_gate and test.temporal_stability_gate)
    mfe_mae_gate = int(train.mfe_mae_gate and validation.mfe_mae_gate and test.mfe_mae_gate)
    replay_gate = int(train.replay_gate and validation.replay_gate and test.replay_gate)
    feature_gate = int(train.feature_separability_gate and validation.feature_separability_gate and test.feature_separability_gate)
    ready_gate = int(
        density_gate
        and direction_gate
        and temporal_gate
        and mfe_mae_gate
        and replay_gate
        and feature_gate
        and cost_gate
        and wf_total >= int(args.min_walkforward_folds)
        and wf_ratio >= float(args.min_walkforward_pass_ratio)
    )
    temp = {
        "density_gate": density_gate,
        "direction_balance_gate": direction_gate,
        "temporal_stability_gate": temporal_gate,
        "mfe_mae_gate": mfe_mae_gate,
        "replay_gate": replay_gate,
        "feature_separability_gate": feature_gate,
        "cost_gate": cost_gate,
        "walkforward_pass_ratio": wf_ratio,
        "entry_family_ready_gate": ready_gate,
    }
    reasons = family_failure_reasons(temp)
    return FamilySummaryRow(
        timeframe=timeframe,
        family_id=family.family_id,
        label=family.label,
        family_type=family.family_type,
        recent_window_bars=int(family.recent_window_bars),
        buffer_atr=float(family.buffer_atr),
        trigger_horizon_bars=int(family.trigger_horizon_bars),
        quality_bars=int(family.quality_bars),
        mfe_atr=float(family.mfe_atr),
        mae_atr=float(family.mae_atr),
        train_events=int(train.triggered_events),
        validation_events=int(validation.triggered_events),
        test_events=int(test.triggered_events),
        train_event_rate=float(train.event_rate),
        validation_event_rate=float(validation.event_rate),
        test_event_rate=float(test.event_rate),
        train_quality_pass_rate=float(train.quality_pass_rate),
        validation_quality_pass_rate=float(validation.quality_pass_rate),
        test_quality_pass_rate=float(test.quality_pass_rate),
        validation_label_psi=float(validation.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        train_replay_profit_factor=float(train.replay_profit_factor),
        validation_replay_profit_factor=float(validation.replay_profit_factor),
        test_replay_profit_factor=float(test.replay_profit_factor),
        train_feature_smd=float(train.max_feature_abs_smd),
        validation_feature_smd=float(validation.max_feature_abs_smd),
        test_feature_smd=float(test.max_feature_abs_smd),
        walkforward_folds=int(wf_total),
        walkforward_pass_folds=int(wf_pass),
        walkforward_pass_ratio=float(wf_ratio),
        density_gate=density_gate,
        direction_balance_gate=direction_gate,
        temporal_stability_gate=temporal_gate,
        mfe_mae_gate=mfe_mae_gate,
        replay_gate=replay_gate,
        feature_separability_gate=feature_gate,
        cost_gate=cost_gate,
        entry_family_ready_gate=ready_gate,
        failure_reasons=json.dumps(reasons, ensure_ascii=False),
    )


def rank_family(row: FamilySummaryRow) -> tuple[float, float, float, float, float]:
    return (
        float(row.entry_family_ready_gate),
        float(row.walkforward_pass_ratio),
        float(row.validation_quality_pass_rate + row.test_quality_pass_rate),
        float(row.validation_replay_profit_factor + row.test_replay_profit_factor),
        float(row.validation_events + row.test_events),
    )


def decision_matrix(family_rows: Sequence[FamilySummaryRow]) -> list[DecisionRow]:
    ready = [row for row in family_rows if row.entry_family_ready_gate]
    best = max(family_rows, key=rank_family) if family_rows else None
    ready_text = f"ready_families={len(ready)}"
    best_text = f"best={best.timeframe}|{best.family_id}" if best else "best=none"
    return [
        DecisionRow(
            route_id="ENTRY_EVENT_MODEL_TRAINING",
            status="BLOCKED" if not ready else "REQUIRES_OWNER_REVIEW",
            score=0.0 if not ready else 65.0,
            evidence=f"{ready_text}; {best_text}; target discovery is not model training.",
            recommendation=(
                "Do not train; no entry family passed discovery gates."
                if not ready
                else "Owner review required before any model preflight."
            ),
        ),
        DecisionRow(
            route_id="ENTRY_EVENT_DISCOVERY_CONTINUE",
            status="RECOMMENDED_DIAGNOSTIC" if not ready else "OPTIONAL_REFINEMENT",
            score=82.0 if not ready else 55.0,
            evidence="Entry target is now separated into setup/trigger and quality/replay diagnostics.",
            recommendation="Review failed families by density, MFE/MAE, cost and walk-forward before changing formulas.",
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="This phase is target discovery only and does not approve execution.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(str(key))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def render_html(report: Phase181BReport, title: str) -> str:
    family_rows = report.family_rows[:40]
    table = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{html.escape(str(row['family_type']))}</td>"
        f"<td>{int(row['train_events'])}/{int(row['validation_events'])}/{int(row['test_events'])}</td>"
        f"<td>{float(row['validation_quality_pass_rate']):.3f}</td>"
        f"<td>{float(row['test_quality_pass_rate']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['entry_family_ready_gate'])}</td>"
        "</tr>"
        for row in family_rows
    )
    decisions = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['route_id']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['score']):.1f}</td>"
        f"<td>{html.escape(str(row['recommendation']))}</td>"
        "</tr>"
        for row in report.decision_matrix
    )
    summary = html.escape(
        json.dumps(
            {
                "entry_event_discovery_ready_gate": report.entry_event_discovery_ready_gate,
                "ready_families": report.ready_families,
                "selected": f"{report.selected_timeframe}|{report.selected_family_id}" if report.selected_family_id else "none",
                "production_status": report.production_status,
            },
            indent=2,
        )
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;background:#10131a;color:#eef2ff;margin:0;padding:24px}}
section{{background:#171b25;border:1px solid #2b3242;border-radius:14px;padding:18px;margin:16px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #303849;padding:8px;text-align:left}}th{{color:#a7c7ff}}pre{{white-space:pre-wrap;background:#0b0e14;padding:12px;border-radius:10px}}
.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:#29364f;color:#cfe0ff}}
</style></head><body>
<section><h1>{html.escape(title)}</h1><p><span class="badge">Research only</span> <strong>{html.escape(report.production_status)}</strong></p><pre>{summary}</pre></section>
<section><h2>Family summary</h2><table><thead><tr><th>TF</th><th>Family</th><th>Type</th><th>Events T/V/Test</th><th>Val quality</th><th>Test quality</th><th>WF pass</th><th>Ready</th></tr></thead><tbody>{table}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase181BReport:
    args = parse_args(argv)
    started = time.time()
    timeframes = parse_timeframes(args.timeframes)
    families = parse_families(args.families)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_health: list[TimeframeHealthRow] = []
    all_cost: list[CostRow] = []
    all_family_rows: list[FamilySummaryRow] = []
    all_split_rows: list[SplitMetricsRow] = []
    all_wf_rows: list[WalkForwardRow] = []
    all_events: list[dict[str, Any]] = []
    all_replay: list[dict[str, Any]] = []
    all_feature_rows: list[dict[str, Any]] = []

    for timeframe in timeframes:
        path = resolve_flat_path(timeframe, args)
        frame = read_ohlc_frame(path, int(args.max_rows))
        high = frame["high"].to_numpy(dtype=np.float64)
        low = frame["low"].to_numpy(dtype=np.float64)
        close = frame["close"].to_numpy(dtype=np.float64)
        atr = wilder_atr(high, low, close)
        all_health.append(timeframe_health(timeframe, frame, path, atr))
        train_idx, validation_idx, test_idx = split_indices(len(frame), float(args.train_frac), float(args.val_frac), int(args.purge_gap))
        split_index_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
        tf_cost_rows = [cost_row(timeframe, split, frame, idx, atr, args) for split, idx in split_index_map.items()]
        all_cost.extend(tf_cost_rows)
        for family in families:
            events = discover_family_events(timeframe, family, frame, atr, args)
            if int(args.max_event_rows) > 0:
                export_events = events[: int(args.max_event_rows)]
            else:
                export_events = events
            all_events.extend(asdict(row) for row in export_events)
            all_replay.extend(asdict(row) for row in export_events if row.trigger_gate)
            train_dist = label_distribution(events, train_idx, len(train_idx))
            split_metrics_by_name: dict[str, SplitMetricsRow] = {}
            for split, idx in split_index_map.items():
                metrics, feature_rows = split_metrics(
                    timeframe,
                    family,
                    frame,
                    atr,
                    split,
                    idx,
                    events,
                    args,
                    None if split == "train" else train_dist,
                )
                split_metrics_by_name[split] = metrics
                all_split_rows.append(metrics)
                all_feature_rows.extend(feature_rows)
            wf_rows = walkforward_rows_for_family(timeframe, family, frame, atr, events, args)
            all_wf_rows.extend(wf_rows)
            family_cost_rows = [row for row in tf_cost_rows if row.timeframe == timeframe]
            all_family_rows.append(
                build_family_summary(timeframe, family, split_metrics_by_name, wf_rows, family_cost_rows, args)
            )

    ranked = sorted(all_family_rows, key=rank_family, reverse=True)
    selected = ranked[0] if ranked else None
    ready_count = sum(int(row.entry_family_ready_gate) for row in all_family_rows)
    decisions = decision_matrix(all_family_rows)

    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    output_families = output_dir / "latest_families.csv"
    output_events = output_dir / "latest_events.csv"
    output_replay = output_dir / "latest_replay.csv"
    output_splits = output_dir / "latest_splits.csv"
    output_walkforward = output_dir / "latest_walkforward.csv"
    output_mfe_mae = output_dir / "latest_mfe_mae.csv"
    output_cost = output_dir / "latest_cost.csv"
    output_features = output_dir / "latest_feature_separability.csv"
    output_decisions = output_dir / "latest_decision_matrix.csv"

    family_dicts = [asdict(row) for row in ranked]
    split_dicts = [asdict(row) for row in all_split_rows]
    wf_dicts = [asdict(row) for row in all_wf_rows]
    cost_dicts = [asdict(row) for row in all_cost]
    decision_dicts = [asdict(row) for row in decisions]
    mfe_rows = [
        {
            "timeframe": row["timeframe"],
            "family_id": row["family_id"],
            "side": row["side"],
            "setup_row": row["setup_row"],
            "trigger_gate": row["trigger_gate"],
            "quality_gate": row["quality_gate"],
            "mfe_atr": row["mfe_atr"],
            "mae_atr": row["mae_atr"],
            "replay_score_atr": row["replay_score_atr"],
            "replay_outcome": row["replay_outcome"],
        }
        for row in all_events
    ]

    report = Phase181BReport(
        symbol=str(args.symbol).upper(),
        timeframes=timeframes,
        spread_mode=str(args.spread_mode),
        spread_value=float(args.spread_value),
        evaluated_timeframes=len(timeframes),
        evaluated_families=len(all_family_rows),
        ready_families=int(ready_count),
        selected_timeframe=selected.timeframe if selected else "",
        selected_family_id=selected.family_id if selected else "",
        selected_family_type=selected.family_type if selected else "",
        selected_family_ready_gate=int(selected.entry_family_ready_gate) if selected else 0,
        entry_event_discovery_ready_gate=int(ready_count > 0),
        no_training_gate=1,
        no_paper_live_gate=1,
        health_rows=[asdict(row) for row in all_health],
        cost_rows=cost_dicts,
        family_rows=family_dicts,
        split_rows=split_dicts,
        walkforward_rows=wf_dicts,
        decision_matrix=decision_dicts,
        output_json=str(output_json),
        output_html=str(output_html),
        output_families_csv=str(output_families),
        output_events_csv=str(output_events),
        output_replay_csv=str(output_replay),
        output_splits_csv=str(output_splits),
        output_walkforward_csv=str(output_walkforward),
        output_mfe_mae_csv=str(output_mfe_mae),
        output_cost_csv=str(output_cost),
        output_feature_separability_csv=str(output_features),
        output_decision_matrix_csv=str(output_decisions),
        production_status="BLOCKED — Phase181B entry-event discovery only; no model training/paper/live",
    )

    write_csv(output_families, family_dicts)
    write_csv(output_events, all_events)
    write_csv(output_replay, all_replay)
    write_csv(output_splits, split_dicts)
    write_csv(output_walkforward, wf_dicts)
    write_csv(output_mfe_mae, mfe_rows)
    write_csv(output_cost, cost_dicts)
    write_csv(output_features, all_feature_rows)
    write_csv(output_decisions, decision_dicts)
    output_html.write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    output_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - started
    print("\n[DONE] Phase181B entry-event discovery complete")
    print(f"  symbol       : {report.symbol}")
    print(f"  timeframes   : {','.join(report.timeframes)}")
    print(f"  families     : {report.evaluated_families}")
    print(f"  ready        : {report.ready_families}")
    print(f"  selected     : {report.selected_timeframe}|{report.selected_family_id}" if report.selected_family_id else "  selected     : none")
    print(f"  ready gate   : {report.entry_event_discovery_ready_gate}")
    print(f"  json         : {report.output_json}")
    print(f"  html         : {report.output_html}")
    print(f"  elapsed_sec  : {elapsed:.1f}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
