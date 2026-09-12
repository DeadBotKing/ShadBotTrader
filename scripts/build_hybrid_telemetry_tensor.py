"""Phase127: build a causal 3D hybrid telemetry tensor.

The tensor is built from online-safe information only. Trade outcomes are used
as targets, and as telemetry features only after a configurable causal lag
(default 48 bars = the 4H TP/SL horizon on 5M candles).
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
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
from backtest_hybrid_xgboost_head import (
    CLASS_BUY,
    CLASS_SELL,
    aligned_predict_proba,
    decide_action,
    default_matrix_path,
    eval_slice_indices,
    load_candles,
    load_head,
    range_filter_pass,
    safe_div,
    simulate_trade,
)
from build_hybrid_xgboost_matrix import (
    RangeFeatureConfig,
    RangeFeatureProvider,
    prepare_trend_dataset,
    timeframe_delta,
)
from report_hybrid_full_backtest import (
    ThresholdSpec,
    add_entropy_columns,
    build_stream_chunk,
    fill_missing_model_features,
    load_record,
    resolve_thresholds,
    select_stream_positions,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_telemetry_tensor")
TARGET_SET = "C"
PRICE_EPS = 1e-9


@dataclass(frozen=True)
class TargetEvent:
    source_index: int
    exit_index: int
    side: int
    pnl: float
    score_r: float
    win: int
    outcome: str


@dataclass(frozen=True)
class TelemetryReport:
    rows: int
    tensor_samples: int
    tensor_window: int
    channels: int
    tensor_shape: list[int]
    candidate_rows: int
    candidate_rate: float
    target_win_rate: float
    target_score_r_mean: float
    target_pnl_sum: float
    safe_lag_bars: int
    lag_mode: str
    source_mode: str
    sample_stride: int
    dtype: str
    flat_path: str
    tensor_path: str
    latest_tensor_path: str
    warnings: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build causal 3D hybrid telemetry tensor with Target C.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument(
        "--source-mode",
        choices=("matrix", "stream"),
        default="matrix",
        help="matrix reads an existing Phase123 matrix; stream builds rows in chunks.",
    )
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all selected rows")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument(
        "--stream-scope",
        choices=("all", "holdout", "last-fold", "auto"),
        default="all",
    )
    parser.add_argument("--stream-chunk-size", type=int, default=500)
    parser.add_argument(
        "--stream-wavenet",
        choices=("neutral", "batch"),
        default="neutral",
        help="neutral is memory-safe and fills WaveNet channels with 1/3.",
    )
    parser.add_argument("--booster", default="lightgbm")
    parser.add_argument("--summary-mode", default="basic")
    parser.add_argument("--include-specialists", choices=("0", "1"), default="1")
    parser.add_argument("--include-multiclass-booster", choices=("0", "1"), default="1")
    parser.add_argument("--include-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--require-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--buy-model-id", default="")
    parser.add_argument("--sell-model-id", default="")
    parser.add_argument("--multiclass-model-id", default="")
    parser.add_argument("--wavenet-model-id", default="gold_trend_signal_5m")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--buy-model-version", type=int, default=0)
    parser.add_argument("--sell-model-version", type=int, default=0)
    parser.add_argument("--multiclass-model-version", type=int, default=0)
    parser.add_argument("--wavenet-model-version", type=int, default=0)
    parser.add_argument("--range-1d-version", type=int, default=0)
    parser.add_argument("--range-4h-version", type=int, default=0)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument(
        "--same-bar-policy",
        choices=("stop_first", "tp_first"),
        default="stop_first",
        help="Resolution when TP and SL are both touched by the same 5M candle.",
    )
    parser.add_argument("--tensor-window", type=int, default=150)
    parser.add_argument("--safe-lag-bars", type=int, default=48)
    parser.add_argument(
        "--telemetry-lag-mode",
        choices=("fixed", "exit_closed"),
        default="fixed",
    )
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all tensor samples")
    parser.add_argument("--candidate-samples-only", choices=("0", "1"), default="0")
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16")
    parser.add_argument("--max-tensor-mb", type=float, default=512.0)
    parser.add_argument("--include-htf-context", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-name", default="hybrid_telemetry_tensor_v1")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def _close_amount(candle: Any) -> float:
    return float(candle.close.amount)


def _open_amount(candle: Any) -> float:
    return float(candle.open.amount)


def _high_amount(candle: Any) -> float:
    return float(candle.high.amount)


def _low_amount(candle: Any) -> float:
    return float(candle.low.amount)


def candle_context(
    candles: Sequence[Any], source_index: int, prefix: str = "5m"
) -> dict[str, float]:
    if source_index < 0 or source_index >= len(candles):
        return {
            f"{prefix}_return_1": 0.0,
            f"{prefix}_body_pct": 0.0,
            f"{prefix}_range_pct": 0.0,
            f"{prefix}_upper_wick_pct": 0.0,
            f"{prefix}_lower_wick_pct": 0.0,
            f"{prefix}_close_position": 0.0,
        }
    candle = candles[source_index]
    close = _close_amount(candle)
    open_ = _open_amount(candle)
    high = _high_amount(candle)
    low = _low_amount(candle)
    prev_close = _close_amount(candles[source_index - 1]) if source_index > 0 else close
    denom = max(abs(prev_close), PRICE_EPS)
    range_width = max(high - low, PRICE_EPS)
    upper_wick = high - max(open_, close)
    lower_wick = min(open_, close) - low
    return {
        f"{prefix}_return_1": (close - prev_close) / denom,
        f"{prefix}_body_pct": (close - open_) / max(abs(open_), PRICE_EPS),
        f"{prefix}_range_pct": (high - low) / max(abs(open_), PRICE_EPS),
        f"{prefix}_upper_wick_pct": upper_wick / max(abs(open_), PRICE_EPS),
        f"{prefix}_lower_wick_pct": lower_wick / max(abs(open_), PRICE_EPS),
        f"{prefix}_close_position": (close - low) / range_width,
    }


def add_time_context(row: dict[str, float], timestamp: Any) -> None:
    try:
        moment = pd.to_datetime(timestamp, utc=True)
        hour = float(moment.hour) + float(moment.minute) / 60.0
        dow = float(moment.dayofweek)
    except Exception:
        hour = 0.0
        dow = 0.0
    row["session_hour_sin"] = float(np.sin(2.0 * np.pi * hour / 24.0))
    row["session_hour_cos"] = float(np.cos(2.0 * np.pi * hour / 24.0))
    row["session_dow_sin"] = float(np.sin(2.0 * np.pi * dow / 7.0))
    row["session_dow_cos"] = float(np.cos(2.0 * np.pi * dow / 7.0))


def build_htf_lookup(candles: Sequence[Any], timeframe: str) -> tuple[list[Any], list[Any]]:
    delta = timeframe_delta(timeframe)
    ordered = sorted(candles, key=lambda candle: candle.open_time.value)
    end_times = [pd.to_datetime(candle.open_time.value + delta, utc=True) for candle in ordered]
    return ordered, end_times


def comparable_timestamp(timestamp: Any) -> Any | None:
    try:
        parsed = pd.to_datetime(timestamp, utc=True)
    except Exception:
        return None
    if pd.isna(parsed):
        return None
    return parsed


def latest_closed(end_times: Sequence[Any], timestamp: Any) -> int | None:
    import bisect

    comparable = comparable_timestamp(timestamp)
    if comparable is None:
        return None
    index = bisect.bisect_right(end_times, comparable) - 1
    return index if index >= 0 else None


def add_htf_context(
    output: dict[str, float],
    timestamp: Any,
    htf_data: Mapping[str, tuple[Sequence[Any], Sequence[Any]]],
) -> None:
    for label, (candles, end_times) in htf_data.items():
        prefix = label.lower()
        index = latest_closed(end_times, timestamp)
        if index is None:
            output.update(candle_context([], -1, prefix=prefix))
            output[f"{prefix}_last_closed_age_5m"] = 0.0
            continue
        output.update(candle_context(candles, index, prefix=prefix))
        try:
            age_minutes = (
                pd.to_datetime(timestamp, utc=True) - pd.to_datetime(end_times[index], utc=True)
            ).total_seconds() / 60.0
        except Exception:
            age_minutes = 0.0
        output[f"{prefix}_last_closed_age_5m"] = max(age_minutes / 5.0, 0.0)


def candidate_columns() -> list[str]:
    return [
        "candidate_side",
        "candidate_confidence",
        "candidate_action_margin",
        "candidate_tp_distance",
        "candidate_sl_distance",
        "candidate_reward_risk",
        "candidate_entry_price",
        "candidate_take_profit",
        "candidate_stop_loss",
        "candidate_valid_range",
        "candidate_valid_bracket",
    ]


def model_feature_columns(frame: pd.DataFrame) -> list[str]:
    prefixes = (
        "buy_specialist_",
        "sell_specialist_",
        "specialist_",
        "booster_",
        "wavenet_",
        "range_1d_",
        "range_4h_",
    )
    blocked = {
        "range_1d_high_price",
        "range_1d_low_price",
        "range_4h_high_price",
        "range_4h_low_price",
    }
    columns = []
    for column in frame.columns:
        if column in blocked:
            continue
        if column.startswith(prefixes):
            columns.append(column)
    return columns


def decide_and_target_row(
    row: pd.Series,
    probs: Sequence[float],
    candles: Sequence[Any],
    args: argparse.Namespace,
    thresholds: ThresholdSpec,
) -> tuple[dict[str, float], TargetEvent | None]:
    decision = decide_action(
        probs,
        thresholds.buy_threshold,
        thresholds.sell_threshold,
        thresholds.min_margin,
    )
    features = {name: 0.0 for name in candidate_columns()}
    if decision == -1 or decision is None:
        return features, None

    side_sign = 1.0 if decision == CLASS_BUY else -1.0
    confidence = float(probs[CLASS_BUY] if decision == CLASS_BUY else probs[CLASS_SELL])
    features["candidate_side"] = side_sign
    features["candidate_confidence"] = confidence
    features["candidate_action_margin"] = abs(float(probs[CLASS_BUY]) - float(probs[CLASS_SELL]))
    features["candidate_valid_range"] = (
        1.0 if range_filter_pass(row, decision, args.min_4h_room, args.min_1d_room) else 0.0
    )
    if features["candidate_valid_range"] < 0.5:
        return features, None

    trade = simulate_trade(row, decision, candles, args)
    if trade is None:
        return features, None

    tp_distance = abs(trade.tp - trade.entry)
    sl_distance = abs(trade.entry - trade.sl)
    features["candidate_valid_bracket"] = 1.0
    features["candidate_entry_price"] = trade.entry
    features["candidate_take_profit"] = trade.tp
    features["candidate_stop_loss"] = trade.sl
    features["candidate_tp_distance"] = tp_distance
    features["candidate_sl_distance"] = sl_distance
    features["candidate_reward_risk"] = safe_div(tp_distance, sl_distance)
    score_r = float(np.clip(safe_div(trade.pnl, sl_distance), -3.0, 3.0))
    event = TargetEvent(
        source_index=trade.source_index,
        exit_index=trade.exit_index,
        side=decision,
        pnl=trade.pnl,
        score_r=score_r,
        win=1 if trade.pnl > 0 else 0,
        outcome=trade.outcome,
    )
    return features, event


def outcome_code(outcome: str) -> float:
    if outcome == "take_profit":
        return 1.0
    if outcome == "stop_loss":
        return -1.0
    return 0.0


def build_lagged_telemetry(
    source_indices: Sequence[int],
    events: Sequence[TargetEvent],
    safe_lag_bars: int,
    mode: str,
) -> pd.DataFrame:
    if mode == "exit_closed":
        sorted_events = sorted(events, key=lambda event: (event.exit_index, event.source_index))
    else:
        sorted_events = sorted(events, key=lambda event: (event.source_index, event.exit_index))
    rows: list[dict[str, float]] = []
    pointer = 0
    available: list[TargetEvent] = []
    for source_index in source_indices:
        while pointer < len(sorted_events):
            event = sorted_events[pointer]
            ready = (
                event.exit_index < source_index
                if mode == "exit_closed"
                else event.source_index <= source_index - safe_lag_bars
            )
            if not ready:
                break
            available.append(event)
            pointer += 1
        rows.append(telemetry_stats(available, source_index))
    return pd.DataFrame(rows).fillna(0.0)


def _window_stats(events: Sequence[TargetEvent], size: int) -> dict[str, float]:
    subset = list(events[-size:]) if size > 0 else list(events)
    if not subset:
        return {
            f"rolling_{size}_trades_win_rate_lag": 0.0,
            f"rolling_{size}_trades_avg_pnl_lag": 0.0,
            f"rolling_{size}_trades_profit_factor_lag": 0.0,
            f"rolling_{size}_trades_tp_rate_lag": 0.0,
            f"rolling_{size}_trades_sl_rate_lag": 0.0,
            f"rolling_{size}_trades_timeout_rate_lag": 0.0,
        }
    pnls = [event.pnl for event in subset]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    return {
        f"rolling_{size}_trades_win_rate_lag": sum(event.win for event in subset) / len(subset),
        f"rolling_{size}_trades_avg_pnl_lag": sum(pnls) / len(subset),
        f"rolling_{size}_trades_profit_factor_lag": safe_div(gross_profit, gross_loss),
        f"rolling_{size}_trades_tp_rate_lag": sum(
            event.outcome == "take_profit" for event in subset
        )
        / len(subset),
        f"rolling_{size}_trades_sl_rate_lag": sum(event.outcome == "stop_loss" for event in subset)
        / len(subset),
        f"rolling_{size}_trades_timeout_rate_lag": sum(
            event.outcome == "timeout" for event in subset
        )
        / len(subset),
    }


def telemetry_stats(events: Sequence[TargetEvent], source_index: int) -> dict[str, float]:
    output: dict[str, float] = {
        "lagged_trade_count": float(len(events)),
        "last_closed_trade_pnl_lag": 0.0,
        "bars_since_last_closed_trade": 0.0,
        "recent_buy_win_rate_lag": 0.0,
        "recent_sell_win_rate_lag": 0.0,
    }
    for size in (12, 24, 48):
        output.update(_window_stats(events, size))
    if events:
        last = events[-1]
        output["last_closed_trade_pnl_lag"] = last.pnl
        output["bars_since_last_closed_trade"] = float(max(source_index - last.exit_index, 0))
        recent = list(events[-48:])
        buys = [event for event in recent if event.side == CLASS_BUY]
        sells = [event for event in recent if event.side == CLASS_SELL]
        output["recent_buy_win_rate_lag"] = safe_div(sum(event.win for event in buys), len(buys))
        output["recent_sell_win_rate_lag"] = safe_div(sum(event.win for event in sells), len(sells))
    return output


def lagged_telemetry_columns() -> list[str]:
    return list(telemetry_stats([], 0).keys())


def outcome_from_code(value: Any) -> str:
    code = _safe(value, 0.0)
    if code > 0.5:
        return "take_profit"
    if code < -0.5:
        return "stop_loss"
    return "timeout"


def target_event_from_row(row: pd.Series) -> TargetEvent | None:
    if _safe(row.get("candidate_mask", 0.0)) < 0.5:
        return None
    side_value = _safe(row.get("target_side", 0.0))
    if side_value >= 0.5:
        side = CLASS_BUY
    elif side_value <= -0.5:
        side = CLASS_SELL
    else:
        return None
    exit_index = int(_safe(row.get("target_exit_index", -1.0), -1.0))
    if exit_index < 0:
        return None
    return TargetEvent(
        source_index=int(row["source_index"]),
        exit_index=exit_index,
        side=side,
        pnl=_safe(row.get("target_trade_pnl", 0.0)),
        score_r=_safe(row.get("target_trade_score_r", 0.0)),
        win=1 if _safe(row.get("target_trade_win", 0.0)) >= 0.5 else 0,
        outcome=outcome_from_code(row.get("target_outcome_code", 0.0)),
    )


def recompute_lagged_telemetry(frame: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    source_indices = [int(value) for value in frame["source_index"].tolist()]
    events = [
        event for _, row in frame.iterrows() if (event := target_event_from_row(row)) is not None
    ]
    telemetry = build_lagged_telemetry(
        source_indices,
        events,
        max(int(args.safe_lag_bars), 1),
        args.telemetry_lag_mode,
    )
    result = frame.copy()
    for column in lagged_telemetry_columns():
        result[column] = telemetry[column].to_numpy(dtype=np.float32)
    return result


def htf_context_data(
    storage_root: Path, symbol: str, enabled: bool, warnings: list[str]
) -> dict[str, tuple[Sequence[Any], Sequence[Any]]]:
    if not enabled:
        return {}
    data: dict[str, tuple[Sequence[Any], Sequence[Any]]] = {}
    for label in ("4H", "1D"):
        try:
            candles = load_candles(storage_root, symbol, label)
            data[label] = build_htf_lookup(candles, label)
        except Exception as error:
            warnings.append(f"{label} context skipped: {type(error).__name__}: {error}")
    return data


def enrich_frame(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    candles: Sequence[Any],
    args: argparse.Namespace,
    thresholds: ThresholdSpec,
    model_features: Sequence[str],
    htf_data: Mapping[str, tuple[Sequence[Any], Sequence[Any]]],
) -> pd.DataFrame:
    source_indices = [int(value) for value in frame["source_index"].tolist()]
    feature_rows: list[dict[str, float]] = []
    events: list[TargetEvent] = []
    target_win: list[float] = []
    target_score_r: list[float] = []
    target_pnl: list[float] = []
    target_side: list[float] = []
    target_exit_index: list[float] = []
    target_outcome_code: list[float] = []
    candidate_mask: list[float] = []

    for offset, (_, row) in enumerate(frame.iterrows()):
        source_index = int(row["source_index"])
        features: dict[str, float] = {}
        features.update(candle_context(candles, source_index, prefix="5m"))
        add_time_context(features, row.get("timestamp", ""))
        add_htf_context(features, row.get("timestamp", ""), htf_data)
        for column in model_features:
            features[column] = _safe(row.get(column, 0.0))
        candidate_features, event = decide_and_target_row(
            row, probabilities[offset], candles, args, thresholds
        )
        features.update(candidate_features)
        if event is None:
            target_win.append(0.0)
            target_score_r.append(0.0)
            target_pnl.append(0.0)
            target_side.append(0.0)
            target_exit_index.append(-1.0)
            target_outcome_code.append(0.0)
            candidate_mask.append(0.0)
        else:
            events.append(event)
            target_win.append(float(event.win))
            target_score_r.append(event.score_r)
            target_pnl.append(event.pnl)
            target_side.append(1.0 if event.side == CLASS_BUY else -1.0)
            target_exit_index.append(float(event.exit_index))
            target_outcome_code.append(outcome_code(event.outcome))
            candidate_mask.append(1.0)
        feature_rows.append(features)

    feature_frame = pd.DataFrame(feature_rows).fillna(0.0)
    telemetry = build_lagged_telemetry(
        source_indices,
        events,
        max(int(args.safe_lag_bars), 1),
        args.telemetry_lag_mode,
    )
    result = pd.concat(
        [
            frame[["timestamp", "source_index", "label", "close"]].reset_index(drop=True),
            feature_frame.reset_index(drop=True),
            telemetry.reset_index(drop=True),
        ],
        axis=1,
    )
    result["target_trade_win"] = np.asarray(target_win, dtype=np.float32)
    result["target_trade_score_r"] = np.asarray(target_score_r, dtype=np.float32)
    result["target_trade_pnl"] = np.asarray(target_pnl, dtype=np.float32)
    result["target_side"] = np.asarray(target_side, dtype=np.float32)
    result["target_exit_index"] = np.asarray(target_exit_index, dtype=np.float32)
    result["target_outcome_code"] = np.asarray(target_outcome_code, dtype=np.float32)
    result["candidate_mask"] = np.asarray(candidate_mask, dtype=np.float32)
    return result


def online_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked = {
        "timestamp",
        "source_index",
        "label",
        "close",
        "target_trade_win",
        "target_trade_score_r",
        "target_trade_pnl",
        "target_side",
        "target_exit_index",
        "target_outcome_code",
        "candidate_mask",
    }
    return [column for column in frame.columns if column not in blocked]


def tensor_sample_indices(
    rows: int,
    window: int,
    stride: int,
    max_samples: int,
    candidate_mask: np.ndarray,
    candidate_only: bool,
) -> np.ndarray:
    if window < 2:
        raise RuntimeError("tensor-window must be >= 2")
    if rows < window:
        raise RuntimeError(f"Need at least {window} rows to build tensor windows; got {rows}")
    indices = np.arange(window - 1, rows, max(stride, 1), dtype=np.int64)
    if candidate_only:
        indices = indices[candidate_mask[indices] >= 0.5]
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    return indices


def build_tensor(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    args: argparse.Namespace,
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    values = (
        frame[list(feature_columns)]
        .replace([np.inf, -np.inf], 0.0)
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )
    candidate_mask = frame["candidate_mask"].to_numpy(dtype=np.float32)
    window = max(int(args.tensor_window), 2)
    sample_indices = tensor_sample_indices(
        len(frame),
        window,
        max(int(args.sample_stride), 1),
        max(int(args.max_samples), 0),
        candidate_mask,
        args.candidate_samples_only == "1",
    )
    dtype = np.float16 if args.dtype == "float16" else np.float32
    bytes_needed = len(sample_indices) * window * len(feature_columns) * np.dtype(dtype).itemsize
    max_bytes = max(float(args.max_tensor_mb), 1.0) * 1024 * 1024
    if bytes_needed > max_bytes:
        raise RuntimeError(
            f"Requested tensor would use about {bytes_needed / (1024 * 1024):.1f} MB, "
            f"above --max-tensor-mb {args.max_tensor_mb:.1f}. Increase --sample-stride, "
            "lower --tensor-window, set --max-samples, or raise --max-tensor-mb."
        )
    tensor = np.empty((len(sample_indices), window, len(feature_columns)), dtype=dtype)
    for out_index, row_index in enumerate(sample_indices):
        tensor[out_index] = values[row_index - window + 1 : row_index + 1].astype(dtype, copy=False)
    targets = {
        "target_trade_win": frame["target_trade_win"].to_numpy(dtype=np.float32)[sample_indices],
        "target_trade_score_r": frame["target_trade_score_r"].to_numpy(dtype=np.float32)[
            sample_indices
        ],
        "target_trade_pnl": frame["target_trade_pnl"].to_numpy(dtype=np.float32)[sample_indices],
        "target_side": frame["target_side"].to_numpy(dtype=np.float32)[sample_indices],
        "target_exit_index": frame["target_exit_index"].to_numpy(dtype=np.int64)[sample_indices],
        "target_outcome_code": frame["target_outcome_code"].to_numpy(dtype=np.float32)[
            sample_indices
        ],
        "candidate_mask": frame["candidate_mask"].to_numpy(dtype=np.float32)[sample_indices],
        "source_index": frame["source_index"].to_numpy(dtype=np.int64)[sample_indices],
    }
    return tensor, targets, sample_indices


def build_from_matrix(
    args: argparse.Namespace,
    matrix_path: Path,
    model: Any,
    features: Sequence[str],
    thresholds: ThresholdSpec,
    warnings: list[str],
) -> pd.DataFrame:
    full_frame = pd.read_parquet(matrix_path)
    missing = [name for name in features if name not in full_frame.columns]
    if missing:
        raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
    indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
    frame = full_frame.iloc[indices].copy().reset_index(drop=True)
    x_values = (
        frame[list(features)].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
    )
    probabilities = aligned_predict_proba(model, x_values)
    candles = load_candles(Path(args.storage_root), args.symbol, args.timeframe)
    model_cols = model_feature_columns(frame)
    htf_data = htf_context_data(
        Path(args.storage_root), args.symbol, args.include_htf_context == "1", warnings
    )
    return enrich_frame(frame, probabilities, candles, args, thresholds, model_cols, htf_data)


def build_from_stream(
    args: argparse.Namespace,
    model: Any,
    features: Sequence[str],
    thresholds: ThresholdSpec,
    warnings: list[str],
) -> pd.DataFrame:
    storage_root = Path(args.storage_root)
    signal_candles = load_candles(storage_root, args.symbol, args.timeframe)
    role, dataset = prepare_trend_dataset(args, signal_candles)
    positions = select_stream_positions(args, dataset, len(signal_candles))
    if not positions:
        raise RuntimeError("No stream positions selected for telemetry tensor")
    range_1d_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("1d", "1D", args.range_1d_model_id, args.range_1d_version, True),
    )
    range_4h_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("4h", "4H", args.range_4h_model_id, args.range_4h_version, True),
    )
    htf_data = htf_context_data(
        storage_root, args.symbol, args.include_htf_context == "1", warnings
    )
    chunks: list[pd.DataFrame] = []
    chunk_size = max(int(args.stream_chunk_size), 50)
    for start in range(0, len(positions), chunk_size):
        chunk_positions = positions[start : start + chunk_size]
        frame = build_stream_chunk(
            args,
            dataset,
            role,
            signal_candles,
            chunk_positions,
            range_1d_provider,
            range_4h_provider,
            features,
            warnings,
        )
        fill_missing_model_features(frame, features)
        add_entropy_columns(frame)
        x_values = (
            frame[list(features)]
            .replace([np.inf, -np.inf], 0.0)
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
        probabilities = aligned_predict_proba(model, x_values)
        model_cols = model_feature_columns(frame)
        chunks.append(
            enrich_frame(
                frame, probabilities, signal_candles, args, thresholds, model_cols, htf_data
            )
        )
        print(f"  stream rows : {min(start + chunk_size, len(positions)):,}/{len(positions):,}")
    streamed = pd.concat(chunks, axis=0, ignore_index=True)
    return recompute_lagged_telemetry(streamed, args)


def write_outputs(
    args: argparse.Namespace,
    flat: pd.DataFrame,
    tensor: np.ndarray,
    targets: Mapping[str, np.ndarray],
    sample_indices: np.ndarray,
    feature_columns: Sequence[str],
    thresholds: ThresholdSpec,
    warnings: list[str],
) -> TelemetryReport:
    storage_root = Path(args.storage_root)
    output_dir = storage_root / "processed" / args.symbol / args.timeframe
    output_dir.mkdir(parents=True, exist_ok=True)
    flat_path = output_dir / "hybrid_telemetry_flat_latest.parquet"
    tensor_path = output_dir / f"{args.output_name}.npz"
    latest_path = output_dir / "hybrid_telemetry_tensor_latest.npz"
    flat.to_parquet(flat_path, index=False)
    payload = {
        "X": tensor,
        **targets,
        "timestamp": flat["timestamp"].astype(str).to_numpy()[sample_indices],
        "channel_names": np.asarray(list(feature_columns), dtype=object),
        "target_set": np.asarray([TARGET_SET], dtype=object),
    }
    np.savez_compressed(tensor_path, **payload)
    np.savez_compressed(latest_path, **payload)

    candidates = int(float(flat["candidate_mask"].sum()))
    target_wins = flat.loc[flat["candidate_mask"] >= 0.5, "target_trade_win"]
    target_scores = flat.loc[flat["candidate_mask"] >= 0.5, "target_trade_score_r"]
    target_pnl = flat.loc[flat["candidate_mask"] >= 0.5, "target_trade_pnl"]
    report = TelemetryReport(
        rows=len(flat),
        tensor_samples=len(tensor),
        tensor_window=max(int(args.tensor_window), 2),
        channels=len(feature_columns),
        tensor_shape=[int(value) for value in tensor.shape],
        candidate_rows=candidates,
        candidate_rate=safe_div(candidates, len(flat)),
        target_win_rate=float(target_wins.mean()) if len(target_wins) else 0.0,
        target_score_r_mean=float(target_scores.mean()) if len(target_scores) else 0.0,
        target_pnl_sum=float(target_pnl.sum()) if len(target_pnl) else 0.0,
        safe_lag_bars=max(int(args.safe_lag_bars), 1),
        lag_mode=args.telemetry_lag_mode,
        source_mode=args.source_mode,
        sample_stride=max(int(args.sample_stride), 1),
        dtype=str(tensor.dtype),
        flat_path=str(flat_path),
        tensor_path=str(tensor_path),
        latest_tensor_path=str(latest_path),
        warnings=warnings,
    )
    log_dir = Path(args.output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "latest.json").write_text(
        json.dumps(
            {
                "args": vars(args),
                "thresholds": asdict(thresholds),
                "report": asdict(report),
                "channel_names": list(feature_columns),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    warnings: list[str] = []
    storage_root = Path(args.storage_root)
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE127 CAUSAL HYBRID TELEMETRY TENSOR")
        print(f"  source      : {args.source_mode}")
        print(f"  symbol/tf   : {args.symbol} {args.timeframe}")
        print(f"  tensor win  : {args.tensor_window}")
        print(f"  safe lag    : {args.safe_lag_bars} bars")
        record, version = load_record(storage_root, args.model_id, args.model_version)
        thresholds = resolve_thresholds(args, record)
        print(
            "  thresholds  : "
            f"buy={thresholds.buy_threshold:.3f} "
            f"sell={thresholds.sell_threshold:.3f} "
            f"margin={thresholds.min_margin:.3f} ({thresholds.source})"
        )
        model, features, _ = load_head(storage_root, args.model_id, version)
        if args.source_mode == "stream":
            flat = build_from_stream(args, model, features, thresholds, warnings)
        else:
            flat = build_from_matrix(args, matrix_path, model, features, thresholds, warnings)
        feature_columns = online_feature_columns(flat)
        tensor, targets, sample_indices = build_tensor(flat, feature_columns, args)
        report = write_outputs(
            args,
            flat,
            tensor,
            targets,
            sample_indices,
            feature_columns,
            thresholds,
            warnings,
        )
        rule("DONE")
        print(f"  flat rows   : {report.rows:,}")
        print(f"  candidates  : {report.candidate_rows:,} ({report.candidate_rate:.2%})")
        print(f"  tensor      : {report.tensor_shape}")
        print(f"  win rate y  : {report.target_win_rate:.2%}")
        print(f"  score_r y   : {report.target_score_r_mean:+.4f}")
        print(f"  pnl y sum   : {report.target_pnl_sum:+.2f}")
        print(f"  flat        : {report.flat_path}")
        print(f"  tensor      : {report.latest_tensor_path}")
        print(f"  report      : {Path(args.output_dir) / 'latest.json'}")
        for warning in warnings[:10]:
            print(f"  [!] {warning}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
