"""Phase186A: Range candle-by-candle forecast accuracy audit.

Measures whether a range model emits a high/low pair for each future candle
and, if it does, how far that pair is from candle t+k. This is forecast
accuracy only.

It does not:
- train a model
- roll a horizon=1 forecast forward recursively
- score the horizon envelope (max high / min low over t+1..t+H)
- treat open or close as model targets
- authorize TP/SL, entry, paper, or live use

Output contract, matching RangePredictor.forecast:
  seq2seq last timestep layout = [high_1, low_1, ..., high_H, low_H]
  scalar layout = [high, low] which is step 1 only
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_OUTPUT_DIR = Path("run_logs/range_multistep_accuracy")
DEFAULT_STORAGE = Path("datasets")
FORECAST_CONTRACT = "last_timestep_interleaved_high_low_pairs"
AUDIT_CONTRACT = (
    "Phase186A scores each emitted high/low pair against candle t+step only. "
    "It does not score the horizon envelope, does not roll predictions recursively, "
    "and does not treat open/close as model targets. Steps the model does not emit "
    "are reported as not auditable."
)
MAX_ACCEPTED_STEPS = 64


@dataclass(frozen=True)
class StepErrorRow:
    timeframe: str
    timestamp: str
    row_index: int
    step: int
    reference_close: float
    atr_reference: float
    target_units: str
    predicted_high_raw: float
    predicted_low_raw: float
    predicted_high: float
    predicted_low: float
    predicted_width: float
    realized_high: float
    realized_low: float
    realized_open: float
    realized_close: float
    predicted_high_offset_atr: float
    predicted_low_offset_atr: float
    realized_high_offset_atr: float
    realized_low_offset_atr: float
    high_price_error_atr: float
    low_price_error_atr: float
    high_abs_error_atr: float
    low_abs_error_atr: float
    width_error_atr: float
    down_room_error_atr: float
    derived_midpoint_error_atr: float
    pair_coherent: int
    high_covered: int
    low_covered: int
    candle_contained: int
    close_inside_pred: int
    atr_regime: str


@dataclass(frozen=True)
class CapabilityRow:
    timeframe: str
    source_mode: str
    model_id: str
    model_version: int
    target_units: str
    record_horizon: int
    window_size: int
    input_scale_low: float
    input_scale_high: float
    keras_output_shape: str
    observed_output_shape: str
    output_layout: str
    forecast_timestep: str
    forecast_contract: str
    model_output_horizon: int
    requested_steps: int
    multi_step_available: int
    all_requested_steps_emitted: int
    auditable_steps: int
    missing_steps: str
    horizon_mismatch: int
    recursive_rollout_used: int
    envelope_metric_used: int
    production_contract_check: str
    rows_measured: int
    rows_skipped: int
    capability_verdict: str
    notes: str


@dataclass(frozen=True)
class StepSummaryRow:
    timeframe: str
    step: int
    auditable: int
    unavailable_reason: str
    rows: int
    pair_coherent_rate: float | None
    median_abs_high_error_atr: float | None
    median_abs_low_error_atr: float | None
    p75_abs_high_error_atr: float | None
    p75_abs_low_error_atr: float | None
    p90_abs_high_error_atr: float | None
    p90_abs_low_error_atr: float | None
    p95_abs_high_error_atr: float | None
    p95_abs_low_error_atr: float | None
    high_bias_atr: float | None
    low_bias_atr: float | None
    high_rmse_atr: float | None
    low_rmse_atr: float | None
    width_bias_atr: float | None
    mean_predicted_high_offset_atr: float | None
    mean_realized_high_offset_atr: float | None
    mean_predicted_low_offset_atr: float | None
    mean_realized_low_offset_atr: float | None
    high_spearman: float | None
    low_spearman: float | None
    width_spearman: float | None
    high_monotonicity: float | None
    low_monotonicity: float | None
    high_within_025_atr_rate: float | None
    high_within_050_atr_rate: float | None
    low_within_025_atr_rate: float | None
    low_within_050_atr_rate: float | None
    candle_containment_rate: float | None
    close_inside_rate: float | None
    derived_midpoint_median_abs_error_atr: float | None
    calibration_available: int
    step_accuracy_gate: int
    primary_failure_reason: str


@dataclass(frozen=True)
class CalibrationBinRow:
    timeframe: str
    step: int
    side: str
    offset_definition: str
    bin_id: int
    rows: int
    pred_min: float
    pred_max: float
    mean_pred_atr: float
    mean_realized_atr: float
    mae_atr: float


@dataclass(frozen=True)
class RegimeRow:
    timeframe: str
    step: int
    regime: str
    rows: int
    median_abs_high_error_atr: float
    median_abs_low_error_atr: float
    high_spearman: float | None
    low_spearman: float | None
    candle_containment_rate: float


@dataclass(frozen=True)
class TimeframeSummary:
    timeframe: str
    model_id: str
    model_version: int
    target_units: str
    model_output_horizon: int
    requested_steps: int
    multi_step_available: int
    all_requested_steps_emitted: int
    auditable_steps: int
    measured_rows: int
    step1_rows: int
    step1_median_abs_high_error_atr: float | None
    step1_median_abs_low_error_atr: float | None
    step1_high_spearman: float | None
    step1_low_spearman: float | None
    step1_high_within_050_atr_rate: float | None
    step1_low_within_050_atr_rate: float | None
    step1_accuracy_gate: int
    all_requested_steps_accurate: int
    candle_forecast_ready_gate: int
    primary_failure_reason: str
    interpretation: str


@dataclass(frozen=True)
class DecisionRow:
    route_id: str
    status: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class Phase186AReport:
    symbol: str
    timeframes: list[str]
    source_mode: str
    requested_steps: int
    evaluated_timeframes: int
    multistep_timeframes: int
    ready_timeframes: int
    selected_timeframe: str
    candle_forecast_ready_gate: int
    no_training_gate: int
    no_paper_live_gate: int
    recursive_rollout_used: int
    envelope_metric_used: int
    audit_contract: str
    owner_answer: str
    capability_rows: list[dict[str, Any]]
    summary_rows: list[dict[str, Any]]
    step_summary_rows: list[dict[str, Any]]
    bias_rows: list[dict[str, Any]]
    calibration_rows: list[dict[str, Any]]
    degradation_rows: list[dict[str, Any]]
    regime_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_step_errors_csv: str
    output_bias_by_step_csv: str
    output_calibration_by_step_csv: str
    output_degradation_curve_csv: str
    output_regime_breakdown_csv: str
    output_model_capability_csv: str
    output_summary_csv: str
    output_step_summary_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase186A range candle-by-candle forecast accuracy audit.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframes", default="4H,1D")
    parser.add_argument("--source-mode", choices=("models", "predictions"), default="models")
    parser.add_argument("--predictions-path", default="")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--range-1d-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--range-4h-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--h4-flat-path", default="datasets/processed/XAUUSD/4H/v1.parquet")
    parser.add_argument("--d1-flat-path", default="datasets/processed/XAUUSD/1D/v1.parquet")
    parser.add_argument("--requested-steps", type=int, default=5)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--progress-every", type=int, default=2000)
    parser.add_argument("--calibration-bins", type=int, default=5)
    parser.add_argument("--min-rows", type=int, default=30)
    parser.add_argument("--max-median-abs-error-atr", type=float, default=0.50)
    parser.add_argument("--min-spearman", type=float, default=0.10)
    parser.add_argument("--min-pair-coherent-rate", type=float, default=0.98)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase186A range candle-by-candle forecast accuracy audit")
    return parser.parse_args(argv)


def canonical_timeframe(text: str) -> str:
    value = str(text or "").strip().upper()
    if value in {"4", "H4", "4H"}:
        return "4H"
    if value in {"1", "D", "D1", "1D"}:
        return "1D"
    return value


def parse_timeframes(text: str) -> list[str]:
    values = [canonical_timeframe(item) for item in str(text or "").replace(";", ",").split(",") if item.strip()]
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output or ["4H", "1D"]


def timestamp_key(value: Any) -> str:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if ts is pd.NaT or pd.isna(ts):
        return ""
    return pd.Timestamp(ts).isoformat()


def read_ohlc_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"OHLC file not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    missing = sorted({"timestamp", "open", "high", "low", "close"} - set(frame.columns))
    if missing:
        raise RuntimeError(f"OHLC file is missing required columns: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    for column in ("open", "high", "low", "close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    result = result.reset_index(drop=True)
    return result


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Causal Wilder ATR. Must match target_builder.wilder_atr_series."""
    if period < 1:
        raise RuntimeError("ATR period must be >= 1")
    atr = np.zeros(len(close), dtype=np.float64)
    tr_sum = 0.0
    for index in range(len(close)):
        tr = float(high[index] - low[index])
        if index > 0:
            tr = max(tr, abs(float(high[index] - close[index - 1])), abs(float(low[index] - close[index - 1])))
        if index < period:
            tr_sum += tr
            atr[index] = tr_sum / float(index + 1)
        else:
            atr[index] = (atr[index - 1] * float(period - 1) + tr) / float(period)
    return atr


def finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def nullable_stat(values: Sequence[float], fn: Any) -> float | None:
    data = np.asarray(list(values), dtype=np.float64)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return None
    result = fn(data)
    if result is None or not np.isfinite(float(result)):
        return None
    return float(result)


def percentile(values: Sequence[float], pct: float) -> float | None:
    return nullable_stat(values, lambda data: float(np.percentile(data, pct)))


def rmse(values: Sequence[float]) -> float | None:
    return nullable_stat(values, lambda data: float(np.sqrt(np.mean(np.square(data)))))


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) < 3 or len(y) < 3 or len(x) != len(y):
        return None
    xs = pd.Series(list(x), dtype="float64")
    ys = pd.Series(list(y), dtype="float64")
    mask = xs.notna() & ys.notna() & np.isfinite(xs) & np.isfinite(ys)
    if int(mask.sum()) < 3:
        return None
    value = xs[mask].rank(method="average").corr(ys[mask].rank(method="average"))
    if value is None or not np.isfinite(float(value)):
        return None
    return float(value)


def within_rate(values: Sequence[float], limit: float) -> float | None:
    data = np.asarray(list(values), dtype=np.float64)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return None
    return float(np.mean(np.abs(data) <= float(limit)))


def regime_label(value: float, q1: float, q2: float) -> str:
    if value <= q1:
        return "low"
    if value <= q2:
        return "mid"
    return "high"


def missing_step_text(emitted: int, requested: int) -> str:
    if emitted >= requested:
        return ""
    start = max(emitted + 1, 1)
    return ",".join(str(step) for step in range(start, requested + 1))


def capability_verdict(emitted: int, requested: int) -> str:
    if emitted <= 0:
        return "NO_OUTPUT"
    if emitted == 1:
        return "STEP1_ONLY"
    if emitted < requested:
        return "PARTIAL_MULTISTEP"
    return "MULTISTEP_COVERS_REQUEST"


def pairs_from_vector(vector: np.ndarray) -> list[tuple[float, float]]:
    width = int(len(vector))
    if width < 2 or width % 2 != 0:
        raise RuntimeError(
            f"Range output width {width} is not an even [high_1, low_1, ..., high_H, low_H] layout"
        )
    pairs = width // 2
    if pairs > MAX_ACCEPTED_STEPS:
        raise RuntimeError(f"Refusing to treat output width as {pairs} candle steps")
    return [(float(vector[k * 2]), float(vector[k * 2 + 1])) for k in range(pairs)]


def parse_range_steps(raw: np.ndarray) -> tuple[list[tuple[float, float]], str]:
    """Return per-step (high, low) raw values and the layout name.

    This follows RangePredictor.forecast: a seq2seq tensor is read at the last
    timestep, and pairs stay in emission order. It does not collapse to max/min.
    """
    arr = np.asarray(raw, dtype=np.float64)
    if arr.ndim == 3:
        if arr.shape[0] != 1:
            raise RuntimeError(f"Expected one sample, got shape {arr.shape}")
        arr = arr[0]
    if arr.ndim == 2 and arr.shape[-1] >= 2 and arr.shape[0] > 2:
        return pairs_from_vector(arr[-1]), "seq2seq_last_timestep"
    if arr.ndim == 1 and len(arr) >= 2:
        return pairs_from_vector(arr), "vector"
    if arr.ndim == 2 and arr.shape[0] == 1 and arr.shape[1] >= 2:
        return pairs_from_vector(arr[0]), "row_vector"
    raise RuntimeError(f"Unexpected range model output shape: {arr.shape}")


def range_raw_pair(raw: np.ndarray) -> tuple[float, float]:
    """Production collapse used by Phase185A / RangePredictor: one high and one low."""
    arr = np.asarray(raw, dtype=np.float64)
    if arr.ndim == 2 and arr.shape[-1] >= 2 and arr.shape[0] > 2:
        last_step = arr[-1]
        pairs = len(last_step) // 2
        if pairs <= 1:
            return float(last_step[0]), float(last_step[1])
        highs = [float(last_step[k * 2]) for k in range(pairs)]
        lows = [float(last_step[k * 2 + 1]) for k in range(pairs)]
        return max(highs), min(lows)
    if arr.ndim == 1 and len(arr) >= 2:
        return float(arr[0]), float(arr[1])
    if arr.ndim == 2 and arr.shape[0] == 1 and arr.shape[1] >= 2:
        return float(arr[0, 0]), float(arr[0, 1])
    raise RuntimeError(f"Unexpected range model output shape: {arr.shape}")


def production_contract_matches(raw: np.ndarray) -> bool:
    steps, _layout = parse_range_steps(raw)
    high, low = range_raw_pair(raw)
    if not steps:
        return False
    return abs(max(step[0] for step in steps) - high) <= 1e-6 and abs(min(step[1] for step in steps) - low) <= 1e-6


def range_output_to_prices(
    high_value: float,
    low_value: float,
    reference_close: float,
    atr_reference: float,
    target_units: str,
) -> tuple[float, float]:
    if str(target_units or "pct") == "atr":
        return (
            float(reference_close) + float(high_value) * float(atr_reference),
            float(reference_close) + float(low_value) * float(atr_reference),
        )
    return (
        float(reference_close) * (1.0 + float(high_value)),
        float(reference_close) * (1.0 + float(low_value)),
    )


def build_step_error_row(
    *,
    timeframe: str,
    timestamp: str,
    row_index: int,
    step: int,
    reference_close: float,
    atr_reference: float,
    target_units: str,
    predicted_high_raw: float,
    predicted_low_raw: float,
    predicted_high: float,
    predicted_low: float,
    high: np.ndarray,
    low: np.ndarray,
    open_: np.ndarray,
    close: np.ndarray,
) -> StepErrorRow:
    future_index = int(row_index) + int(step)
    if future_index < 0 or future_index >= len(close):
        raise RuntimeError(f"Step {step} at row {row_index} has no future candle")
    atr_value = max(float(atr_reference), 1e-9)
    realized_high = float(high[future_index])
    realized_low = float(low[future_index])
    realized_open = float(open_[future_index])
    realized_close = float(close[future_index])
    pred_high = float(predicted_high)
    pred_low = float(predicted_low)
    high_error = (pred_high - realized_high) / atr_value
    low_error = (pred_low - realized_low) / atr_value
    pred_high_offset = (pred_high - float(reference_close)) / atr_value
    pred_low_offset = (pred_low - float(reference_close)) / atr_value
    real_high_offset = (realized_high - float(reference_close)) / atr_value
    real_low_offset = (realized_low - float(reference_close)) / atr_value
    pred_width = pred_high - pred_low
    real_width = realized_high - realized_low
    width_error = (pred_width - real_width) / atr_value
    down_room_error = ((float(reference_close) - pred_low) - (float(reference_close) - realized_low)) / atr_value
    pred_mid = (pred_high + pred_low) / 2.0
    real_mid = (realized_high + realized_low) / 2.0
    return StepErrorRow(
        timeframe=timeframe,
        timestamp=str(timestamp),
        row_index=int(row_index),
        step=int(step),
        reference_close=float(reference_close),
        atr_reference=float(atr_value),
        target_units=str(target_units or ""),
        predicted_high_raw=float(predicted_high_raw),
        predicted_low_raw=float(predicted_low_raw),
        predicted_high=pred_high,
        predicted_low=pred_low,
        predicted_width=float(pred_width),
        realized_high=realized_high,
        realized_low=realized_low,
        realized_open=realized_open,
        realized_close=realized_close,
        predicted_high_offset_atr=float(pred_high_offset),
        predicted_low_offset_atr=float(pred_low_offset),
        realized_high_offset_atr=float(real_high_offset),
        realized_low_offset_atr=float(real_low_offset),
        high_price_error_atr=float(high_error),
        low_price_error_atr=float(low_error),
        high_abs_error_atr=float(abs(high_error)),
        low_abs_error_atr=float(abs(low_error)),
        width_error_atr=float(width_error),
        down_room_error_atr=float(down_room_error),
        derived_midpoint_error_atr=float((pred_mid - real_mid) / atr_value),
        pair_coherent=int(pred_high >= pred_low),
        high_covered=int(realized_high <= pred_high),
        low_covered=int(realized_low >= pred_low),
        candle_contained=int(pred_low <= realized_low and realized_high <= pred_high),
        close_inside_pred=int(pred_low <= realized_close <= pred_high),
        atr_regime="",
    )


def assign_regimes(rows: Sequence[StepErrorRow]) -> list[StepErrorRow]:
    if not rows:
        return []
    anchors = [row for row in rows if row.step == 1] or list(rows)
    atr_values = np.asarray([row.atr_reference for row in anchors], dtype=np.float64)
    q1, q2 = np.percentile(atr_values, [33.333, 66.667])
    output: list[StepErrorRow] = []
    for row in rows:
        output.append(replace(row, atr_regime=f"atr_{regime_label(row.atr_reference, float(q1), float(q2))}"))
    return output


def calibration_bins(timeframe: str, step: int, rows: Sequence[StepErrorRow], bins: int) -> list[CalibrationBinRow]:
    if not rows:
        return []
    frame = pd.DataFrame([asdict(row) for row in rows])
    output: list[CalibrationBinRow] = []
    definition = "price_minus_reference_close_over_atr"
    for side, pred_col, real_col in (
        ("high", "predicted_high_offset_atr", "realized_high_offset_atr"),
        ("low", "predicted_low_offset_atr", "realized_low_offset_atr"),
    ):
        data = frame[[pred_col, real_col]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(data) < 2 or data[pred_col].nunique() < 2:
            continue
        try:
            data = data.copy()
            data["_bin"] = pd.qcut(data[pred_col], q=max(int(bins), 2), labels=False, duplicates="drop")
        except ValueError:
            continue
        for bin_id, group in data.groupby("_bin"):
            pred = group[pred_col].to_numpy(dtype=np.float64)
            real = group[real_col].to_numpy(dtype=np.float64)
            output.append(
                CalibrationBinRow(
                    timeframe=timeframe,
                    step=int(step),
                    side=side,
                    offset_definition=definition,
                    bin_id=int(bin_id),
                    rows=int(len(group)),
                    pred_min=float(np.min(pred)),
                    pred_max=float(np.max(pred)),
                    mean_pred_atr=float(np.mean(pred)),
                    mean_realized_atr=float(np.mean(real)),
                    mae_atr=float(np.mean(np.abs(pred - real))),
                )
            )
    return output


def monotonicity(bin_rows: Sequence[CalibrationBinRow], side: str) -> float | None:
    rows = sorted([row for row in bin_rows if row.side == side], key=lambda row: row.bin_id)
    if len(rows) < 2:
        return None
    diffs = [rows[index + 1].mean_realized_atr - rows[index].mean_realized_atr for index in range(len(rows) - 1)]
    return float(sum(1 for diff in diffs if diff >= -1e-12) / len(diffs))


def step_failure_reason(row: StepSummaryRow, args: argparse.Namespace) -> tuple[int, str]:
    if not row.auditable:
        return 0, row.unavailable_reason or "not_auditable"
    failures: list[str] = []
    if row.rows < int(args.min_rows):
        failures.append("min_rows_failed")
    if row.pair_coherent_rate is None or row.pair_coherent_rate < float(args.min_pair_coherent_rate):
        failures.append("pair_coherence_failed")
    if row.median_abs_high_error_atr is None or row.median_abs_high_error_atr > float(args.max_median_abs_error_atr):
        failures.append("high_error_failed")
    if row.median_abs_low_error_atr is None or row.median_abs_low_error_atr > float(args.max_median_abs_error_atr):
        failures.append("low_error_failed")
    if row.high_spearman is None or row.high_spearman < float(args.min_spearman):
        failures.append("high_spearman_failed")
    if row.low_spearman is None or row.low_spearman < float(args.min_spearman):
        failures.append("low_spearman_failed")
    if failures:
        return 0, failures[0]
    return 1, "none"


def summarize_steps(
    timeframe: str,
    rows: Sequence[StepErrorRow],
    emitted: int,
    requested: int,
    args: argparse.Namespace,
) -> tuple[list[StepSummaryRow], list[CalibrationBinRow]]:
    frame = pd.DataFrame([asdict(row) for row in rows]) if rows else pd.DataFrame()
    summaries: list[StepSummaryRow] = []
    calibrations: list[CalibrationBinRow] = []
    last_step = max(int(requested), int(emitted), 1)
    for step in range(1, last_step + 1):
        auditable = step <= int(emitted)
        group = frame[frame["step"] == step] if auditable and not frame.empty else pd.DataFrame()
        if not auditable:
            summaries.append(
                StepSummaryRow(
                    timeframe=timeframe,
                    step=step,
                    auditable=0,
                    unavailable_reason="model_did_not_emit_step",
                    rows=0,
                    pair_coherent_rate=None,
                    median_abs_high_error_atr=None,
                    median_abs_low_error_atr=None,
                    p75_abs_high_error_atr=None,
                    p75_abs_low_error_atr=None,
                    p90_abs_high_error_atr=None,
                    p90_abs_low_error_atr=None,
                    p95_abs_high_error_atr=None,
                    p95_abs_low_error_atr=None,
                    high_bias_atr=None,
                    low_bias_atr=None,
                    high_rmse_atr=None,
                    low_rmse_atr=None,
                    width_bias_atr=None,
                    mean_predicted_high_offset_atr=None,
                    mean_realized_high_offset_atr=None,
                    mean_predicted_low_offset_atr=None,
                    mean_realized_low_offset_atr=None,
                    high_spearman=None,
                    low_spearman=None,
                    width_spearman=None,
                    high_monotonicity=None,
                    low_monotonicity=None,
                    high_within_025_atr_rate=None,
                    high_within_050_atr_rate=None,
                    low_within_025_atr_rate=None,
                    low_within_050_atr_rate=None,
                    candle_containment_rate=None,
                    close_inside_rate=None,
                    derived_midpoint_median_abs_error_atr=None,
                    calibration_available=0,
                    step_accuracy_gate=0,
                    primary_failure_reason="model_did_not_emit_step",
                )
            )
            continue
        step_rows = [row for row in rows if row.step == step]
        cal = calibration_bins(timeframe, step, step_rows, int(args.calibration_bins))
        calibrations.extend(cal)
        high_err = group["high_price_error_atr"].tolist() if not group.empty else []
        low_err = group["low_price_error_atr"].tolist() if not group.empty else []
        high_abs = group["high_abs_error_atr"].tolist() if not group.empty else []
        low_abs = group["low_abs_error_atr"].tolist() if not group.empty else []
        draft = StepSummaryRow(
            timeframe=timeframe,
            step=step,
            auditable=1,
            unavailable_reason="",
            rows=int(len(group)),
            pair_coherent_rate=nullable_stat(group["pair_coherent"].tolist(), np.mean) if not group.empty else None,
            median_abs_high_error_atr=percentile(high_abs, 50),
            median_abs_low_error_atr=percentile(low_abs, 50),
            p75_abs_high_error_atr=percentile(high_abs, 75),
            p75_abs_low_error_atr=percentile(low_abs, 75),
            p90_abs_high_error_atr=percentile(high_abs, 90),
            p90_abs_low_error_atr=percentile(low_abs, 90),
            p95_abs_high_error_atr=percentile(high_abs, 95),
            p95_abs_low_error_atr=percentile(low_abs, 95),
            high_bias_atr=nullable_stat(high_err, np.mean),
            low_bias_atr=nullable_stat(low_err, np.mean),
            high_rmse_atr=rmse(high_err),
            low_rmse_atr=rmse(low_err),
            width_bias_atr=nullable_stat(group["width_error_atr"].tolist(), np.mean) if not group.empty else None,
            mean_predicted_high_offset_atr=nullable_stat(group["predicted_high_offset_atr"].tolist(), np.mean) if not group.empty else None,
            mean_realized_high_offset_atr=nullable_stat(group["realized_high_offset_atr"].tolist(), np.mean) if not group.empty else None,
            mean_predicted_low_offset_atr=nullable_stat(group["predicted_low_offset_atr"].tolist(), np.mean) if not group.empty else None,
            mean_realized_low_offset_atr=nullable_stat(group["realized_low_offset_atr"].tolist(), np.mean) if not group.empty else None,
            high_spearman=spearman(group["predicted_high_offset_atr"].tolist(), group["realized_high_offset_atr"].tolist()) if not group.empty else None,
            low_spearman=spearman(group["predicted_low_offset_atr"].tolist(), group["realized_low_offset_atr"].tolist()) if not group.empty else None,
            width_spearman=spearman(
                ((group["predicted_high"] - group["predicted_low"]) / group["atr_reference"]).tolist(),
                ((group["realized_high"] - group["realized_low"]) / group["atr_reference"]).tolist(),
            )
            if not group.empty
            else None,
            high_monotonicity=monotonicity(cal, "high"),
            low_monotonicity=monotonicity(cal, "low"),
            high_within_025_atr_rate=within_rate(high_err, 0.25),
            high_within_050_atr_rate=within_rate(high_err, 0.50),
            low_within_025_atr_rate=within_rate(low_err, 0.25),
            low_within_050_atr_rate=within_rate(low_err, 0.50),
            candle_containment_rate=nullable_stat(group["candle_contained"].tolist(), np.mean) if not group.empty else None,
            close_inside_rate=nullable_stat(group["close_inside_pred"].tolist(), np.mean) if not group.empty else None,
            derived_midpoint_median_abs_error_atr=percentile(np.abs(group["derived_midpoint_error_atr"]).tolist(), 50) if not group.empty else None,
            calibration_available=int(any(item.side == "high" for item in cal) and any(item.side == "low" for item in cal)),
            step_accuracy_gate=0,
            primary_failure_reason="",
        )
        gate, reason = step_failure_reason(draft, args)
        summaries.append(replace(draft, step_accuracy_gate=gate, primary_failure_reason=reason))
    return summaries, calibrations


def primary_failure(cap: CapabilityRow, steps: Sequence[StepSummaryRow]) -> str:
    requested = [row for row in steps if row.step <= cap.requested_steps]
    if not any(row.auditable and row.rows > 0 for row in requested):
        return "no_auditable_rows"
    if cap.model_output_horizon < cap.requested_steps:
        if cap.model_output_horizon <= 1:
            return "multistep_output_not_available"
        return "partial_multistep_output"
    if any(row.auditable and not row.step_accuracy_gate for row in requested):
        return "step_accuracy_gate_failed"
    if any(not row.auditable for row in requested):
        return "multistep_output_not_available"
    return "none"


def build_interpretation(cap: CapabilityRow, summary_failure: str, step1: StepSummaryRow | None, ready: int) -> str:
    if cap.model_output_horizon <= 1 and cap.requested_steps <= 1:
        text = (
            f"{cap.timeframe} model_output_horizon=1. Only the next candle was requested, and it is auditable. "
            "The model does not emit later candles. No recursive rollout was used."
        )
    elif cap.model_output_horizon <= 1:
        text = (
            f"{cap.timeframe} model_output_horizon=1, so only the next candle high/low is auditable. "
            f"Requested steps {cap.missing_steps} were not emitted. No recursive rollout was used."
        )
    elif not cap.all_requested_steps_emitted:
        text = (
            f"{cap.timeframe} emits {cap.model_output_horizon} steps but requested {cap.requested_steps}. "
            f"Missing steps: {cap.missing_steps}."
        )
    else:
        text = (
            f"{cap.timeframe} emits {cap.model_output_horizon} candle steps and covers "
            f"requested_steps={cap.requested_steps}."
        )
    if step1 is None or step1.rows <= 0:
        text += " Step 1 had no measurable rows."
    elif step1.step_accuracy_gate:
        text += " Step 1 passed the diagnostic accuracy thresholds."
    else:
        text += " Step 1 was measured but did not pass the diagnostic accuracy thresholds."
    if ready:
        text += " Candle-forecast ready gate passed for the requested steps."
    else:
        text += f" Candle-forecast ready gate failed: {summary_failure}."
    text += " This is not a trading, TP/SL, or entry result."
    return text


def timeframe_summary(cap: CapabilityRow, steps: Sequence[StepSummaryRow]) -> TimeframeSummary:
    requested = [row for row in steps if row.step <= cap.requested_steps]
    step1 = next((row for row in steps if row.step == 1), None)
    failure = primary_failure(cap, steps)
    accurate = bool(requested) and all(row.auditable and row.step_accuracy_gate for row in requested)
    ready = int(cap.all_requested_steps_emitted == 1 and accurate and failure == "none")
    measured_rows = int(step1.rows) if step1 is not None else 0
    return TimeframeSummary(
        timeframe=cap.timeframe,
        model_id=cap.model_id,
        model_version=cap.model_version,
        target_units=cap.target_units,
        model_output_horizon=cap.model_output_horizon,
        requested_steps=cap.requested_steps,
        multi_step_available=cap.multi_step_available,
        all_requested_steps_emitted=cap.all_requested_steps_emitted,
        auditable_steps=cap.auditable_steps,
        measured_rows=measured_rows,
        step1_rows=measured_rows,
        step1_median_abs_high_error_atr=None if step1 is None else step1.median_abs_high_error_atr,
        step1_median_abs_low_error_atr=None if step1 is None else step1.median_abs_low_error_atr,
        step1_high_spearman=None if step1 is None else step1.high_spearman,
        step1_low_spearman=None if step1 is None else step1.low_spearman,
        step1_high_within_050_atr_rate=None if step1 is None else step1.high_within_050_atr_rate,
        step1_low_within_050_atr_rate=None if step1 is None else step1.low_within_050_atr_rate,
        step1_accuracy_gate=0 if step1 is None else int(step1.step_accuracy_gate),
        all_requested_steps_accurate=int(accurate),
        candle_forecast_ready_gate=ready,
        primary_failure_reason=failure,
        interpretation=build_interpretation(cap, failure, step1, ready),
    )


def bias_rows(steps: Sequence[StepSummaryRow]) -> list[dict[str, Any]]:
    return [
        {
            "timeframe": row.timeframe,
            "step": row.step,
            "auditable": row.auditable,
            "rows": row.rows,
            "high_bias_atr": row.high_bias_atr,
            "low_bias_atr": row.low_bias_atr,
            "width_bias_atr": row.width_bias_atr,
            "mean_predicted_high_offset_atr": row.mean_predicted_high_offset_atr,
            "mean_realized_high_offset_atr": row.mean_realized_high_offset_atr,
            "mean_predicted_low_offset_atr": row.mean_predicted_low_offset_atr,
            "mean_realized_low_offset_atr": row.mean_realized_low_offset_atr,
            "bias_sign_note": "positive high_bias means predicted high is too high; positive low_bias means predicted low is too high",
        }
        for row in steps
    ]


def degradation_rows(steps: Sequence[StepSummaryRow]) -> list[dict[str, Any]]:
    step1 = next((row for row in steps if row.step == 1 and row.auditable), None)
    base = None if step1 is None else step1.median_abs_high_error_atr
    output: list[dict[str, Any]] = []
    for row in steps:
        ratio: float | None = None
        if row.auditable and row.step == 1:
            ratio = 1.0 if row.rows else None
        elif row.auditable and base is not None and base > 1e-12 and row.median_abs_high_error_atr is not None:
            ratio = float(row.median_abs_high_error_atr / base)
        output.append(
            {
                "timeframe": row.timeframe,
                "step": row.step,
                "auditable": row.auditable,
                "unavailable_reason": row.unavailable_reason,
                "rows": row.rows,
                "median_abs_high_error_atr": row.median_abs_high_error_atr,
                "median_abs_low_error_atr": row.median_abs_low_error_atr,
                "p90_abs_high_error_atr": row.p90_abs_high_error_atr,
                "p90_abs_low_error_atr": row.p90_abs_low_error_atr,
                "high_spearman": row.high_spearman,
                "low_spearman": row.low_spearman,
                "width_spearman": row.width_spearman,
                "high_within_050_atr_rate": row.high_within_050_atr_rate,
                "low_within_050_atr_rate": row.low_within_050_atr_rate,
                "candle_containment_rate": row.candle_containment_rate,
                "error_vs_step1_ratio": ratio,
                "step_accuracy_gate": row.step_accuracy_gate,
            }
        )
    return output


def regime_rows(timeframe: str, rows: Sequence[StepErrorRow]) -> list[RegimeRow]:
    if not rows:
        return []
    frame = pd.DataFrame([asdict(row) for row in rows])
    output: list[RegimeRow] = []
    for (step, regime), group in frame.groupby(["step", "atr_regime"], dropna=False):
        output.append(
            RegimeRow(
                timeframe=timeframe,
                step=int(step),
                regime=str(regime),
                rows=int(len(group)),
                median_abs_high_error_atr=float(np.median(group["high_abs_error_atr"])),
                median_abs_low_error_atr=float(np.median(group["low_abs_error_atr"])),
                high_spearman=spearman(group["predicted_high_offset_atr"].tolist(), group["realized_high_offset_atr"].tolist()),
                low_spearman=spearman(group["predicted_low_offset_atr"].tolist(), group["realized_low_offset_atr"].tolist()),
                candle_containment_rate=float(np.mean(group["candle_contained"])),
            )
        )
    return output


def owner_answer(capabilities: Sequence[CapabilityRow]) -> str:
    if not capabilities:
        return "No range output was measured."
    lines: list[str] = []
    for cap in capabilities:
        if cap.model_output_horizon <= 0:
            lines.append(f"{cap.timeframe}: no forecast output was measured.")
        elif cap.model_output_horizon == 1 and cap.requested_steps <= 1:
            lines.append(
                f"{cap.timeframe}: model_output_horizon=1. Only step 1 was requested and it is auditable. "
                "The model does not emit later candles, so there is no model evidence for "
                "candle-by-candle forecasts beyond the next candle."
            )
        elif cap.model_output_horizon == 1:
            lines.append(
                f"{cap.timeframe}: model_output_horizon=1. Only step 1 is auditable. "
                f"Steps {cap.missing_steps} were not emitted by the model. "
                "There is no model evidence for candle-by-candle forecasts beyond the next candle."
            )
        elif cap.model_output_horizon < cap.requested_steps:
            lines.append(
                f"{cap.timeframe}: model_output_horizon={cap.model_output_horizon}. "
                f"Steps {cap.missing_steps} were not emitted."
            )
        else:
            lines.append(
                f"{cap.timeframe}: model_output_horizon={cap.model_output_horizon} covers "
                f"requested_steps={cap.requested_steps}."
            )
    return " ".join(lines)


def decision_matrix(summaries: Sequence[TimeframeSummary], capabilities: Sequence[CapabilityRow]) -> list[DecisionRow]:
    any_step1 = any(row.step1_accuracy_gate for row in summaries)
    any_measured = any(row.step1_rows > 0 for row in summaries)
    any_multi = any(row.multi_step_available for row in capabilities)
    all_ready = bool(summaries) and all(row.candle_forecast_ready_gate for row in summaries)
    best = max(summaries, key=lambda row: (row.candle_forecast_ready_gate, row.auditable_steps, -(row.step1_median_abs_high_error_atr or 999.0))) if summaries else None
    best_text = f"{best.timeframe}: ready={best.candle_forecast_ready_gate}; horizon={best.model_output_horizon}" if best else "none"
    if not any_measured:
        step1_status = "NOT_MEASURED"
    elif any_step1:
        step1_status = "MEASURED_PASS"
    else:
        step1_status = "MEASURED_FAIL"
    if not any_multi:
        multi_status = "NOT_AVAILABLE"
    elif all_ready:
        multi_status = "MEASURED_PASS"
    else:
        multi_status = "PARTIAL_OR_FAILED"
    return [
        DecisionRow(
            route_id="CANDLE_STEP1_HIGH_LOW",
            status=step1_status,
            score=50.0 if any_step1 else 0.0,
            evidence=best_text,
            recommendation="Step 1 is the next candle high/low only. It is not a multi-candle forecast.",
        ),
        DecisionRow(
            route_id="CANDLE_BY_CANDLE_FUTURE_STEPS",
            status=multi_status,
            score=70.0 if all_ready else 0.0,
            evidence=f"multistep_timeframes={sum(row.multi_step_available for row in capabilities)}; {best_text}",
            recommendation="Do not claim candle-by-candle future forecasts unless model_output_horizon covers the requested steps.",
        ),
        DecisionRow(
            route_id="RANGE_AS_FUTURE_PRICE_ENGINE",
            status="OWNER_REVIEW_REQUIRED" if all_ready else "BLOCKED",
            score=60.0 if all_ready else 0.0,
            evidence=best_text,
            recommendation="A diagnostic pass is not permission to trade. No execution authority from this phase.",
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="Phase186A is forecast-accuracy audit only.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def make_capability(
    *,
    timeframe: str,
    source_mode: str,
    model_id: str,
    model_version: int,
    target_units: str,
    record_horizon: int,
    window_size: int,
    input_scale: tuple[float, float],
    keras_output_shape: str,
    observed_output_shape: str,
    output_layout: str,
    forecast_timestep: str,
    emitted: int,
    requested: int,
    production_contract_check: str,
    rows_measured: int,
    rows_skipped: int,
    notes: str,
) -> CapabilityRow:
    return CapabilityRow(
        timeframe=timeframe,
        source_mode=source_mode,
        model_id=model_id,
        model_version=int(model_version),
        target_units=target_units,
        record_horizon=int(record_horizon),
        window_size=int(window_size),
        input_scale_low=float(input_scale[0]),
        input_scale_high=float(input_scale[1]),
        keras_output_shape=keras_output_shape,
        observed_output_shape=observed_output_shape,
        output_layout=output_layout,
        forecast_timestep=forecast_timestep,
        forecast_contract=FORECAST_CONTRACT,
        model_output_horizon=int(emitted),
        requested_steps=int(requested),
        multi_step_available=int(emitted >= 2),
        all_requested_steps_emitted=int(emitted >= requested and emitted > 0),
        auditable_steps=int(emitted),
        missing_steps=missing_step_text(emitted, requested),
        horizon_mismatch=int(record_horizon > 0 and record_horizon != emitted),
        recursive_rollout_used=0,
        envelope_metric_used=0,
        production_contract_check=production_contract_check,
        rows_measured=int(rows_measured),
        rows_skipped=int(rows_skipped),
        capability_verdict=capability_verdict(emitted, requested),
        notes=notes,
    )


def limit_indices(indices: Sequence[int], stride: int, max_rows: int) -> list[int]:
    stepped = list(indices)[:: max(int(stride), 1)] if stride != 1 else list(indices)
    if int(max_rows) > 0 and len(stepped) > int(max_rows):
        return stepped[-int(max_rows) :]
    return stepped


def as_batch_array(raw_out: Any) -> np.ndarray:
    if isinstance(raw_out, (list, tuple)):
        if not raw_out:
            raise RuntimeError("Range model returned an empty output list")
        raw_out = raw_out[0]
    array = np.asarray(raw_out)
    if array.ndim == 0:
        raise RuntimeError(f"Range model returned a scalar output: {array}")
    return array


def model_forecast_rows(timeframe: str, args: argparse.Namespace) -> tuple[list[StepErrorRow], CapabilityRow]:
    from build_hybrid_xgboost_matrix import RangeFeatureConfig, RangeFeatureProvider
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window, normalize_scale_range
    from ShadBotTrader.infrastructure.ai.dual_predictor import _load

    label = "4h" if timeframe == "4H" else "1d"
    model_id = args.range_4h_model_id if timeframe == "4H" else args.range_1d_model_id
    version = int(args.range_4h_version if timeframe == "4H" else args.range_1d_version)
    requested = int(args.requested_steps)
    print(f"[i] Loading {timeframe} range provider: model_id={model_id} version={version or 'latest'}", flush=True)
    provider = RangeFeatureProvider(
        Path(args.storage_root),
        str(args.symbol).upper(),
        RangeFeatureConfig(label, timeframe, model_id, version, True),
    )
    if not provider.available:
        raise RuntimeError(f"Range provider unavailable for {timeframe} {model_id}")
    record = provider.record
    artifact = provider.artifact
    if record is None or artifact is None:
        raise RuntimeError(f"No model record/artifact loaded for {timeframe} {model_id}")
    candles = provider.candles
    high = np.asarray([float(c.high.amount) for c in candles], dtype=np.float64)
    low = np.asarray([float(c.low.amount) for c in candles], dtype=np.float64)
    open_ = np.asarray([float(c.open.amount) for c in candles], dtype=np.float64)
    close = np.asarray([float(c.close.amount) for c in candles], dtype=np.float64)
    atr = wilder_atr(high, low, close, period=max(int(args.atr_period), 1))
    window_size = max(int(getattr(record, "window_size", 1) or 1), 1)
    scale_range = normalize_scale_range(getattr(record, "input_scale_range", None))
    model = _load(artifact)

    def has_window(original_index: int) -> bool:
        matrix_index = provider.original_to_matrix.get(original_index)
        return matrix_index is not None and matrix_index >= window_size - 1

    def scaled_window(original_index: int) -> list[list[float]] | None:
        matrix_index = provider.original_to_matrix.get(original_index)
        if matrix_index is None or matrix_index < window_size - 1:
            return None
        window_rows = provider.matrix.rows[matrix_index - window_size + 1 : matrix_index + 1]
        return minmax_scale_window([list(row) for row in window_rows], scale_range)

    probe_index = next((index for index in range(window_size - 1, max(window_size - 1, len(candles) - 1)) if has_window(index)), None)
    if probe_index is None:
        raise RuntimeError(f"No valid range window for {timeframe} {model_id}")
    probe_window = scaled_window(probe_index)
    if probe_window is None:
        raise RuntimeError(f"Probe window missing for {timeframe} {model_id}")
    probe_out = as_batch_array(model.predict(np.asarray([probe_window], dtype=np.float32), verbose=0))
    probe_sample = probe_out[0]
    steps, layout = parse_range_steps(probe_sample)
    emitted = len(steps)
    if emitted < 1:
        raise RuntimeError(f"{timeframe} range model emitted no high/low pair")
    contract = "matched" if production_contract_matches(probe_sample) else "mismatched"
    keras_shape = str(getattr(model, "output_shape", ""))
    observed_shape = f"batch={tuple(int(v) for v in probe_out.shape)}; sample={tuple(int(v) for v in np.asarray(probe_sample).shape)}"
    print(
        f"[i] {timeframe} capability: layout={layout} model_output_horizon={emitted} "
        f"requested_steps={requested} record_horizon={int(record.horizon or 0)} "
        f"observed={observed_shape} contract={contract}",
        flush=True,
    )
    if contract != "matched":
        print(f"[!] {timeframe}: parsed steps do not match the production max/min collapse. Audit continues with per-step pairs.", flush=True)
    indices = limit_indices(
        [index for index in range(window_size - 1, len(candles) - emitted) if has_window(index)],
        int(args.sample_stride),
        int(args.max_rows),
    )
    print(
        f"[i] {timeframe}: preparing {len(indices)} windows "
        f"(rows={len(candles)}, emitted_steps={emitted}, window={window_size})",
        flush=True,
    )
    rows: list[StepErrorRow] = []
    skipped = 0
    batch_x: list[list[list[float]]] = []
    batch_meta: list[int] = []
    batch_size = max(int(args.batch_size), 1)
    progress_every = max(int(args.progress_every), 0)
    processed = 0
    target_units = str(record.target_units or "pct")

    def append_sample(sample: np.ndarray, original_index: int) -> None:
        nonlocal skipped
        sample_steps, _sample_layout = parse_range_steps(sample)
        if len(sample_steps) != emitted:
            raise RuntimeError(
                f"{timeframe} output horizon changed from {emitted} to {len(sample_steps)} at row {original_index}"
            )
        reference_close = float(close[original_index])
        atr_reference = float(atr[original_index])
        if reference_close <= 0 or atr_reference <= 0 or not np.isfinite(atr_reference):
            skipped += 1
            return
        if any(not np.isfinite(value) for pair in sample_steps for value in pair):
            skipped += 1
            return
        timestamp = str(candles[original_index].open_time.value)
        for step, (high_raw, low_raw) in enumerate(sample_steps, start=1):
            pred_high, pred_low = range_output_to_prices(high_raw, low_raw, reference_close, atr_reference, target_units)
            rows.append(
                build_step_error_row(
                    timeframe=timeframe,
                    timestamp=timestamp,
                    row_index=original_index,
                    step=step,
                    reference_close=reference_close,
                    atr_reference=atr_reference,
                    target_units=target_units,
                    predicted_high_raw=high_raw,
                    predicted_low_raw=low_raw,
                    predicted_high=pred_high,
                    predicted_low=pred_low,
                    high=high,
                    low=low,
                    open_=open_,
                    close=close,
                )
            )

    def flush_batch() -> None:
        nonlocal processed
        if not batch_x:
            return
        raw_out = as_batch_array(model.predict(np.asarray(batch_x, dtype=np.float32), verbose=0))
        if len(raw_out) != len(batch_meta):
            raise RuntimeError(f"{timeframe} predict batch length {len(raw_out)} != {len(batch_meta)}")
        for sample, original_index in zip(raw_out, batch_meta, strict=True):
            append_sample(np.asarray(sample), original_index)
            processed += 1
            if progress_every and processed % progress_every == 0:
                print(f"[i] {timeframe}: forecasted {processed}/{len(indices)} windows", flush=True)
        batch_x.clear()
        batch_meta.clear()

    for original_index in indices:
        window = scaled_window(original_index)
        if window is None:
            skipped += 1
            continue
        batch_x.append(window)
        batch_meta.append(original_index)
        if len(batch_x) >= batch_size:
            flush_batch()
    flush_batch()
    measured = len({row.row_index for row in rows})
    print(f"[i] {timeframe}: completed {measured} forecasts, skipped={skipped}, auditable_steps={emitted}", flush=True)
    notes = (
        f"{AUDIT_CONTRACT} input_scale={scale_range}. keras_output_shape={keras_shape}. "
        "Open/close are reported only as realized context, not as model targets."
    )
    capability = make_capability(
        timeframe=timeframe,
        source_mode="models",
        model_id=str(record.model_id),
        model_version=int(record.version),
        target_units=target_units,
        record_horizon=int(record.horizon or 0),
        window_size=window_size,
        input_scale=scale_range,
        keras_output_shape=keras_shape,
        observed_output_shape=observed_shape,
        output_layout=layout,
        forecast_timestep="last",
        emitted=emitted,
        requested=requested,
        production_contract_check=contract,
        rows_measured=measured,
        rows_skipped=skipped,
        notes=notes,
    )
    return rows, capability


def discover_prediction_steps(columns: Sequence[str]) -> tuple[int, str]:
    names = {str(column) for column in columns}
    emitted = 0
    for step in range(1, MAX_ACCEPTED_STEPS + 1):
        if f"predicted_high_{step}" in names and f"predicted_low_{step}" in names:
            emitted = step
        elif emitted:
            break
    if emitted:
        return emitted, "indexed_price_columns"
    if "predicted_high" in names and "predicted_low" in names:
        return 1, "scalar_price_columns"
    return 0, "none"


def prediction_price(row: Mapping[str, Any], step: int, layout: str, side: str) -> float | None:
    if layout == "indexed_price_columns":
        return finite_float(row.get(f"predicted_{side}_{step}"))
    return finite_float(row.get(f"predicted_{side}"))


def predictions_forecast_rows(timeframe: str, args: argparse.Namespace) -> tuple[list[StepErrorRow], CapabilityRow]:
    pred_path = Path(str(args.predictions_path))
    if not pred_path.exists():
        raise RuntimeError(f"Predictions path not found: {pred_path}")
    predictions = pd.read_csv(pred_path) if pred_path.suffix.lower() == ".csv" else pd.read_parquet(pred_path)
    requested = int(args.requested_steps)
    flat_path = Path(str(args.h4_flat_path if timeframe == "4H" else args.d1_flat_path))
    flat = read_ohlc_frame(flat_path)
    if "timeframe" in predictions.columns:
        predictions = predictions[predictions["timeframe"].astype(str).map(canonical_timeframe) == timeframe].copy()
    elif len(parse_timeframes(args.timeframes)) > 1:
        raise RuntimeError("Predictions file has no timeframe column; pass one timeframe or add a timeframe column")
    emitted, layout = discover_prediction_steps(predictions.columns)
    high = flat["high"].to_numpy(dtype=np.float64)
    low = flat["low"].to_numpy(dtype=np.float64)
    open_ = flat["open"].to_numpy(dtype=np.float64)
    close = flat["close"].to_numpy(dtype=np.float64)
    atr = wilder_atr(high, low, close, period=max(int(args.atr_period), 1))
    timestamp_to_index = {timestamp_key(ts): index for index, ts in enumerate(flat["timestamp"])}
    target_units = "price"
    if "target_units" in predictions.columns and not predictions.empty:
        target_units = str(predictions["target_units"].iloc[0] or "price")
    rows: list[StepErrorRow] = []
    skipped = 0
    matched_indexes: list[int] = []
    staged: list[tuple[int, str, list[tuple[float, float]]]] = []
    if emitted > 0:
        for record in predictions.to_dict(orient="records"):
            key = timestamp_key(record.get("timestamp", record.get("open_time", "")))
            index = timestamp_to_index.get(key)
            if index is None or index + emitted >= len(flat):
                skipped += 1
                continue
            prices: list[tuple[float, float]] = []
            bad = False
            for step in range(1, emitted + 1):
                pred_high = prediction_price(record, step, layout, "high")
                pred_low = prediction_price(record, step, layout, "low")
                if pred_high is None or pred_low is None:
                    bad = True
                    break
                prices.append((pred_high, pred_low))
            if bad:
                skipped += 1
                continue
            staged.append((index, key, prices))
            staged.sort(key=lambda item: item[0])
            keep = set(limit_indices([item[0] for item in staged], int(args.sample_stride), int(args.max_rows)))
        for index, key, prices in staged:
            if index not in keep:
                continue
            if float(close[index]) <= 0 or float(atr[index]) <= 0:
                skipped += 1
                continue
            matched_indexes.append(index)
            for step, (pred_high, pred_low) in enumerate(prices, start=1):
                rows.append(
                    build_step_error_row(
                        timeframe=timeframe,
                        timestamp=key,
                        row_index=index,
                        step=step,
                        reference_close=float(close[index]),
                        atr_reference=float(atr[index]),
                        target_units=target_units,
                        predicted_high_raw=float("nan"),
                        predicted_low_raw=float("nan"),
                        predicted_high=pred_high,
                        predicted_low=pred_low,
                        high=high,
                        low=low,
                        open_=open_,
                        close=close,
                    )
                )
    notes = (
        f"{AUDIT_CONTRACT} Predictions mode reads explicit price columns only. "
        "It does not infer later candles from a step-1 price."
    )
    capability = make_capability(
        timeframe=timeframe,
        source_mode="predictions",
        model_id="predictions_file",
        model_version=0,
        target_units=target_units,
        record_horizon=0,
        window_size=0,
        input_scale=(0.0, 0.0),
        keras_output_shape="",
        observed_output_shape=layout,
        output_layout=layout,
        forecast_timestep="predictions_file",
        emitted=emitted,
        requested=requested,
        production_contract_check="not_applicable",
        rows_measured=len(set(matched_indexes)),
        rows_skipped=skipped,
        notes=notes,
    )
    return rows, capability


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

    def csv_value(value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, float) and not np.isfinite(value):
            return ""
        return value

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key, "")) for key in fields})


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if not np.isfinite(number):
        return "n/a"
    return f"{number:.{digits}f}"


def render_html(report: Phase186AReport, title: str) -> str:
    banner = "MULTI-STEP OUTPUT AVAILABLE" if report.multistep_timeframes else "MULTI-STEP OUTPUT NOT AVAILABLE"
    banner_color = "#14532d" if report.multistep_timeframes else "#7f1d1d"
    capabilities = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['model_id']))}</td>"
        f"<td>{int(row['model_output_horizon'])}</td>"
        f"<td>{int(row['requested_steps'])}</td>"
        f"<td>{html.escape(str(row['missing_steps']))}</td>"
        f"<td>{html.escape(str(row['capability_verdict']))}</td>"
        f"<td>{html.escape(str(row['output_layout']))}</td>"
        f"<td>{int(row['recursive_rollout_used'])}</td>"
        "</tr>"
        for row in report.capability_rows
    )
    steps = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{int(row['step'])}</td>"
        f"<td>{int(row['auditable'])}</td>"
        f"<td>{int(row['rows'])}</td>"
        f"<td>{fmt(row['median_abs_high_error_atr'])}</td>"
        f"<td>{fmt(row['median_abs_low_error_atr'])}</td>"
        f"<td>{fmt(row['high_spearman'])}</td>"
        f"<td>{fmt(row['low_spearman'])}</td>"
        f"<td>{fmt(row['high_within_050_atr_rate'])}</td>"
        f"<td>{int(row['step_accuracy_gate'])}</td>"
        f"<td>{html.escape(str(row['primary_failure_reason']))}</td>"
        "</tr>"
        for row in report.step_summary_rows
    )
    decisions = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['route_id']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{html.escape(str(row['recommendation']))}</td>"
        "</tr>"
        for row in report.decision_matrix
    )
    interpretations = "".join(f"<li>{html.escape(str(row['interpretation']))}</li>" for row in report.summary_rows)
    pre = html.escape(
        json.dumps(
            {
                "ready_gate": report.candle_forecast_ready_gate,
                "multistep_timeframes": report.multistep_timeframes,
                "owner_answer": report.owner_answer,
                "production_status": report.production_status,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;background:#10131a;color:#eef2ff;margin:0;padding:24px}}section{{background:#171b25;border:1px solid #2b3242;border-radius:14px;padding:18px;margin:16px 0}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #303849;padding:8px;text-align:left;vertical-align:top}}th{{color:#a7c7ff}}.banner{{background:{banner_color};padding:12px 14px;border-radius:10px;font-weight:700}}pre{{white-space:pre-wrap;background:#0b0e14;padding:12px;border-radius:10px}}</style></head><body>
<section><h1>{html.escape(title)}</h1><div class="banner">{html.escape(banner)}</div>
<p>این گزارش دقت high/low هر کندل آینده را جداگانه می‌سنجد، نه envelope کل افق و نه سیگنال معاملاتی. اگر model_output_horizon برابر 1 باشد، فقط کندل بعدی قابل سنجش است. steps بعدی ساخته نمی‌شوند.</p>
<p><strong>{html.escape(report.production_status)}</strong></p><pre>{pre}</pre></section>
<section><h2>Owner answer</h2><p>{html.escape(report.owner_answer)}</p><ul>{interpretations}</ul></section>
<section><h2>Model capability</h2><table><thead><tr><th>TF</th><th>Model</th><th>Output horizon</th><th>Requested</th><th>Missing</th><th>Verdict</th><th>Layout</th><th>Rollout</th></tr></thead><tbody>{capabilities}</tbody></table></section>
<section><h2>Per-step accuracy</h2><table><thead><tr><th>TF</th><th>Step</th><th>Auditable</th><th>Rows</th><th>High MAE</th><th>Low MAE</th><th>High rho</th><th>Low rho</th><th>High within 0.50</th><th>Gate</th><th>Failure</th></tr></thead><tbody>{steps}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase186AReport:
    args = parse_args(argv)
    if int(args.requested_steps) < 1:
        raise RuntimeError("--requested-steps must be >= 1")
    if int(args.requested_steps) > MAX_ACCEPTED_STEPS:
        raise RuntimeError(f"--requested-steps must be <= {MAX_ACCEPTED_STEPS}")
    timeframes = parse_timeframes(args.timeframes)
    all_rows: list[StepErrorRow] = []
    capabilities: list[CapabilityRow] = []
    summaries: list[TimeframeSummary] = []
    all_steps: list[StepSummaryRow] = []
    all_cal: list[CalibrationBinRow] = []
    all_regimes: list[RegimeRow] = []
    for timeframe in timeframes:
        if args.source_mode == "models":
            rows, capability = model_forecast_rows(timeframe, args)
        else:
            rows, capability = predictions_forecast_rows(timeframe, args)
        rows = assign_regimes(rows)
        step_summaries, calibrations = summarize_steps(
            timeframe,
            rows,
            capability.model_output_horizon,
            int(args.requested_steps),
            args,
        )
        capabilities.append(capability)
        summaries.append(timeframe_summary(capability, step_summaries))
        all_rows.extend(rows)
        all_steps.extend(step_summaries)
        all_cal.extend(calibrations)
        all_regimes.extend(regime_rows(timeframe, rows))

    decisions = decision_matrix(summaries, capabilities)
    ready_count = sum(row.candle_forecast_ready_gate for row in summaries)
    selected = (
        max(
            summaries,
            key=lambda row: (
                row.candle_forecast_ready_gate,
                row.auditable_steps,
                row.step1_accuracy_gate,
                -(row.step1_median_abs_high_error_atr or 999.0),
            ),
        )
        if summaries
        else None
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / "latest.json",
        "html": output_dir / "latest.html",
        "errors": output_dir / "latest_step_errors.csv",
        "bias": output_dir / "latest_bias_by_step.csv",
        "cal": output_dir / "latest_calibration_by_step.csv",
        "curve": output_dir / "latest_degradation_curve.csv",
        "regime": output_dir / "latest_regime_breakdown.csv",
        "capability": output_dir / "latest_model_capability.csv",
        "summary": output_dir / "latest_summary.csv",
        "step_summary": output_dir / "latest_step_summary.csv",
        "decisions": output_dir / "latest_decision_matrix.csv",
    }
    answer = owner_answer(capabilities)
    report = Phase186AReport(
        symbol=str(args.symbol).upper(),
        timeframes=timeframes,
        source_mode=str(args.source_mode),
        requested_steps=int(args.requested_steps),
        evaluated_timeframes=len(summaries),
        multistep_timeframes=sum(row.multi_step_available for row in capabilities),
        ready_timeframes=int(ready_count),
        selected_timeframe=selected.timeframe if selected else "",
        candle_forecast_ready_gate=int(ready_count == len(summaries) and ready_count > 0),
        no_training_gate=1,
        no_paper_live_gate=1,
        recursive_rollout_used=0,
        envelope_metric_used=0,
        audit_contract=AUDIT_CONTRACT,
        owner_answer=answer,
        capability_rows=[asdict(row) for row in capabilities],
        summary_rows=[asdict(row) for row in summaries],
        step_summary_rows=[asdict(row) for row in all_steps],
        bias_rows=bias_rows(all_steps),
        calibration_rows=[asdict(row) for row in all_cal],
        degradation_rows=degradation_rows(all_steps),
        regime_rows=[asdict(row) for row in all_regimes],
        decision_matrix=[asdict(row) for row in decisions],
        output_json=str(paths["json"]),
        output_html=str(paths["html"]),
        output_step_errors_csv=str(paths["errors"]),
        output_bias_by_step_csv=str(paths["bias"]),
        output_calibration_by_step_csv=str(paths["cal"]),
        output_degradation_curve_csv=str(paths["curve"]),
        output_regime_breakdown_csv=str(paths["regime"]),
        output_model_capability_csv=str(paths["capability"]),
        output_summary_csv=str(paths["summary"]),
        output_step_summary_csv=str(paths["step_summary"]),
        output_decision_matrix_csv=str(paths["decisions"]),
        production_status="BLOCKED — Phase186A candle-by-candle forecast accuracy audit only; no model training/paper/live",
    )
    write_csv(paths["errors"], [asdict(row) for row in all_rows])
    write_csv(paths["bias"], report.bias_rows)
    write_csv(paths["cal"], report.calibration_rows)
    write_csv(paths["curve"], report.degradation_rows)
    write_csv(paths["regime"], report.regime_rows)
    write_csv(paths["capability"], report.capability_rows)
    write_csv(paths["summary"], report.summary_rows)
    write_csv(paths["step_summary"], report.step_summary_rows)
    write_csv(paths["decisions"], report.decision_matrix)
    paths["html"].write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    paths["json"].write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n[DONE] Phase186A range candle-by-candle forecast accuracy audit complete", flush=True)
    print(f"  symbol      : {report.symbol}", flush=True)
    print(f"  timeframes  : {','.join(report.timeframes)}", flush=True)
    print(f"  requested   : {report.requested_steps}", flush=True)
    print(f"  multistep   : {report.multistep_timeframes}/{report.evaluated_timeframes}", flush=True)
    print(f"  ready gate  : {report.candle_forecast_ready_gate}", flush=True)
    print(f"  answer      : {report.owner_answer}", flush=True)
    print(f"  json        : {report.output_json}", flush=True)
    print(f"  html        : {report.output_html}", flush=True)
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
