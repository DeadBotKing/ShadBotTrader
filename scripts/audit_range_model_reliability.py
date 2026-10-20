"""Phase185A: Range model reliability / calibration / decision-utility audit.

This phase audits the 4H and 1D range models before they are used as entry,
TP/SL, or filtering components. It measures forecast error, calibration,
directional ranking, regime stability and a simple decision-utility proxy.

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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

DEFAULT_OUTPUT_DIR = Path("run_logs/range_model_reliability")
DEFAULT_STORAGE = Path("datasets")


@dataclass(frozen=True)
class ForecastRow:
    timeframe: str
    timestamp: str
    row_index: int
    horizon_bars: int
    reference_close: float
    atr_reference: float
    predicted_high: float
    predicted_low: float
    predicted_width: float
    predicted_up_atr: float
    predicted_down_atr: float
    predicted_width_atr: float
    realized_high: float
    realized_low: float
    realized_up_atr: float
    realized_down_atr: float
    realized_width_atr: float
    high_error_atr: float
    low_error_atr: float
    width_error_atr: float
    high_abs_error_atr: float
    low_abs_error_atr: float
    coherent_high_gate: int
    coherent_low_gate: int
    coherent_range_gate: int
    atr_regime: str
    predicted_width_regime: str


@dataclass(frozen=True)
class SummaryRow:
    timeframe: str
    source_mode: str
    model_id: str
    model_version: int
    target_units: str
    horizon_bars: int
    rows: int
    coherent_rate: float
    high_coherent_rate: float
    low_coherent_rate: float
    median_abs_high_error_atr: float
    median_abs_low_error_atr: float
    p90_abs_high_error_atr: float
    p90_abs_low_error_atr: float
    high_bias_atr: float
    low_bias_atr: float
    high_rmse_atr: float
    low_rmse_atr: float
    up_spearman: float
    down_spearman: float
    width_spearman: float
    up_monotonicity: float
    down_monotonicity: float
    decision_proxy_trades: int
    decision_proxy_rate: float
    decision_proxy_quality_rate: float
    decision_proxy_mean_score: float
    baseline_buy_quality_rate: float
    baseline_sell_quality_rate: float
    coherence_gate: int
    error_gate: int
    ranking_gate: int
    calibration_gate: int
    decision_utility_gate: int
    range_reliability_gate: int
    primary_failure_reason: str


@dataclass(frozen=True)
class CalibrationBinRow:
    timeframe: str
    side: str
    bin_id: int
    rows: int
    pred_min: float
    pred_max: float
    mean_pred_atr: float
    mean_realized_atr: float
    hit_rate_pred_reached: float
    hit_rate_1atr: float
    hit_rate_15atr: float


@dataclass(frozen=True)
class RegimeRow:
    timeframe: str
    regime_axis: str
    regime: str
    rows: int
    median_abs_high_error_atr: float
    median_abs_low_error_atr: float
    up_spearman: float
    down_spearman: float
    decision_proxy_quality_rate: float
    decision_proxy_mean_score: float


@dataclass(frozen=True)
class DecisionUtilityRow:
    timeframe: str
    policy_id: str
    rows: int
    selected_events: int
    selected_rate: float
    buy_events: int
    sell_events: int
    quality_pass_rate: float
    mean_score_atr: float
    profit_factor_proxy: float
    verdict: str


@dataclass(frozen=True)
class DecisionRow:
    route_id: str
    status: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class Phase185AReport:
    symbol: str
    timeframes: list[str]
    source_mode: str
    evaluated_timeframes: int
    reliable_timeframes: int
    selected_timeframe: str
    selected_reliability_gate: int
    range_model_reliability_ready_gate: int
    no_training_gate: int
    no_paper_live_gate: int
    summary_rows: list[dict[str, Any]]
    calibration_rows: list[dict[str, Any]]
    regime_rows: list[dict[str, Any]]
    decision_utility_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_forecast_errors_csv: str
    output_summary_csv: str
    output_calibration_bins_csv: str
    output_regime_breakdown_csv: str
    output_decision_utility_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase185A range model reliability, calibration and decision utility audit.",
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
    parser.add_argument("--h4-horizon", type=int, default=0, help="0 = model record horizon or fallback")
    parser.add_argument("--d1-horizon", type=int, default=0, help="0 = model record horizon or fallback")
    parser.add_argument("--fallback-h4-horizon", type=int, default=6)
    parser.add_argument("--fallback-d1-horizon", type=int, default=5)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--progress-every", type=int, default=2000)
    parser.add_argument("--calibration-bins", type=int, default=5)
    parser.add_argument("--decision-edge-atr", type=float, default=0.25)
    parser.add_argument("--decision-mfe-atr", type=float, default=1.0)
    parser.add_argument("--decision-mae-atr", type=float, default=1.0)
    parser.add_argument("--min-coherent-rate", type=float, default=0.98)
    parser.add_argument("--max-median-abs-error-atr", type=float, default=1.0)
    parser.add_argument("--min-abs-spearman", type=float, default=0.05)
    parser.add_argument("--min-monotonicity", type=float, default=0.50)
    parser.add_argument("--min-decision-quality-lift", type=float, default=0.02)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase185A range model reliability audit")
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


def read_ohlc_frame(path: Path, max_rows: int = 0) -> pd.DataFrame:
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
    result = result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if max_rows > 0 and len(result) > max_rows:
        result = result.iloc[-max_rows:].copy().reset_index(drop=True)
    return result


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
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


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(float(denominator)) <= 1e-12:
        return float(default)
    return float(numerator) / float(denominator)


def rmse(values: Sequence[float]) -> float:
    data = np.asarray(list(values), dtype=np.float64)
    if len(data) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(data))))


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3 or len(y) < 3:
        return 0.0
    xs = pd.Series(list(x), dtype="float64").rank(method="average")
    ys = pd.Series(list(y), dtype="float64").rank(method="average")
    value = xs.corr(ys)
    if value is None or not np.isfinite(float(value)):
        return 0.0
    return float(value)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def percentile(values: Sequence[float], pct: float) -> float:
    data = np.asarray(list(values), dtype=np.float64)
    data = data[np.isfinite(data)]
    if len(data) == 0:
        return 0.0
    return float(np.percentile(data, pct))


def range_raw_pair(raw: np.ndarray) -> tuple[float, float]:
    """Return high/low output values from scalar or seq2seq range model output."""
    if raw.ndim == 2 and raw.shape[-1] >= 2 and raw.shape[0] > 2:
        last_step = raw[-1]
        pairs = len(last_step) // 2
        if pairs == 1:
            return float(last_step[0]), float(last_step[1])
        highs = [float(last_step[k * 2]) for k in range(pairs)]
        lows = [float(last_step[k * 2 + 1]) for k in range(pairs)]
        return max(highs), min(lows)
    if raw.ndim == 1 and len(raw) >= 2:
        return float(raw[0]), float(raw[1])
    if raw.ndim == 2 and raw.shape[0] == 1 and raw.shape[1] >= 2:
        return float(raw[0, 0]), float(raw[0, 1])
    raise RuntimeError(f"Unexpected range model output shape: {raw.shape}")


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


def model_forecast_rows(timeframe: str, args: argparse.Namespace) -> tuple[list[ForecastRow], str, int, str, int]:
    from build_hybrid_xgboost_matrix import RangeFeatureConfig, RangeFeatureProvider
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window
    from ShadBotTrader.infrastructure.ai.dual_predictor import _load

    label = "4h" if timeframe == "4H" else "1d"
    model_id = args.range_4h_model_id if timeframe == "4H" else args.range_1d_model_id
    version = int(args.range_4h_version if timeframe == "4H" else args.range_1d_version)
    forced_horizon = int(args.h4_horizon if timeframe == "4H" else args.d1_horizon)
    fallback_horizon = int(args.fallback_h4_horizon if timeframe == "4H" else args.fallback_d1_horizon)
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
    horizon = forced_horizon if forced_horizon > 0 else max(int(record.horizon or fallback_horizon), 1)
    candles = provider.candles
    high = np.asarray([float(c.high.amount) for c in candles], dtype=np.float64)
    low = np.asarray([float(c.low.amount) for c in candles], dtype=np.float64)
    close = np.asarray([float(c.close.amount) for c in candles], dtype=np.float64)
    atr = wilder_atr(high, low, close)
    stride = max(int(args.sample_stride), 1)
    window_size = max(int(getattr(record, "window_size", 1) or 1), 1)
    start = max(window_size - 1, 0)
    indices = list(range(start, max(start, len(candles) - horizon), stride))
    if int(args.max_rows) > 0 and len(indices) > int(args.max_rows):
        indices = indices[-int(args.max_rows) :]
    print(
        f"[i] {timeframe}: preparing {len(indices)} windows "
        f"(rows={len(candles)}, horizon={horizon}, window={window_size}, stride={stride})",
        flush=True,
    )
    model = _load(artifact)
    rows: list[ForecastRow] = []
    batch_x: list[list[list[float]]] = []
    batch_meta: list[int] = []
    batch_size = max(int(args.batch_size), 1)
    progress_every = max(int(args.progress_every), 0)
    processed = 0

    def flush_batch() -> None:
        nonlocal processed
        if not batch_x:
            return
        x = np.asarray(batch_x, dtype=np.float32)
        raw_out = model.predict(x, verbose=0)
        for raw, original_index in zip(raw_out, batch_meta, strict=True):
            high_value, low_value = range_raw_pair(np.asarray(raw))
            pred_high, pred_low = range_output_to_prices(
                high_value,
                low_value,
                float(close[original_index]),
                float(atr[original_index]),
                str(record.target_units or "pct"),
            )
            rows.append(
                build_forecast_row(
                    timeframe,
                    str(candles[original_index].open_time.value),
                    original_index,
                    horizon,
                    float(close[original_index]),
                    float(atr[original_index]),
                    pred_high,
                    pred_low,
                    high,
                    low,
                    original_index,
                )
            )
            processed += 1
            if progress_every and processed % progress_every == 0:
                print(f"[i] {timeframe}: forecasted {processed}/{len(indices)} windows", flush=True)
        batch_x.clear()
        batch_meta.clear()

    for original_index in indices:
        matrix_index = provider.original_to_matrix.get(original_index)
        if matrix_index is None or matrix_index < window_size - 1:
            continue
        window_rows = provider.matrix.rows[matrix_index - window_size + 1 : matrix_index + 1]
        scaled = minmax_scale_window([list(row) for row in window_rows])
        batch_x.append(scaled)
        batch_meta.append(original_index)
        if len(batch_x) >= batch_size:
            flush_batch()
    flush_batch()
    print(f"[i] {timeframe}: completed {len(rows)} forecasts", flush=True)
    return rows, str(record.model_id), int(record.version), str(record.target_units or "pct"), horizon


def predictions_forecast_rows(timeframe: str, args: argparse.Namespace) -> tuple[list[ForecastRow], str, int, str, int]:
    pred_path = Path(str(args.predictions_path))
    if not pred_path.exists():
        raise RuntimeError(f"Predictions path not found: {pred_path}")
    predictions = pd.read_csv(pred_path) if pred_path.suffix.lower() == ".csv" else pd.read_parquet(pred_path)
    if "timeframe" in predictions.columns:
        predictions = predictions[predictions["timeframe"].astype(str).str.upper().map(canonical_timeframe) == timeframe].copy()
    flat_path = Path(str(args.h4_flat_path if timeframe == "4H" else args.d1_flat_path))
    flat = read_ohlc_frame(flat_path, 0)
    high = flat["high"].to_numpy(dtype=np.float64)
    low = flat["low"].to_numpy(dtype=np.float64)
    close = flat["close"].to_numpy(dtype=np.float64)
    atr = wilder_atr(high, low, close)
    timestamp_to_index = {str(ts): i for i, ts in enumerate(flat["timestamp"].astype(str))}
    label = "4h" if timeframe == "4H" else "1d"
    forced_horizon = int(args.h4_horizon if timeframe == "4H" else args.d1_horizon)
    horizon = forced_horizon if forced_horizon > 0 else int(args.fallback_h4_horizon if timeframe == "4H" else args.fallback_d1_horizon)
    rows: list[ForecastRow] = []
    for _, row in predictions.iterrows():
        ts = str(pd.to_datetime(row.get("timestamp", row.get("open_time", "")), utc=True, errors="coerce"))
        if ts not in timestamp_to_index:
            continue
        index = int(timestamp_to_index[ts])
        if index + horizon >= len(flat):
            continue
        pred_high = column_value(row, ("predicted_high", f"range_{label}_high_price", "range_high_price"), 0.0)
        pred_low = column_value(row, ("predicted_low", f"range_{label}_low_price", "range_low_price"), 0.0)
        if pred_high <= 0 or pred_low <= 0:
            continue
        rows.append(
            build_forecast_row(
                timeframe,
                ts,
                index,
                horizon,
                float(close[index]),
                float(atr[index]),
                pred_high,
                pred_low,
                high,
                low,
                index,
            )
        )
    return rows, "predictions_file", 0, "unknown", horizon


def column_value(row: Mapping[str, Any], names: Sequence[str], default: float = 0.0) -> float:
    for name in names:
        if name in row:
            try:
                value = float(row[name])
                if np.isfinite(value):
                    return value
            except Exception:
                continue
    return float(default)


def regime_label(value: float, q1: float, q2: float) -> str:
    if value <= q1:
        return "low"
    if value <= q2:
        return "mid"
    return "high"


def build_forecast_row(
    timeframe: str,
    timestamp: str,
    index: int,
    horizon: int,
    reference_close: float,
    atr_reference: float,
    predicted_high: float,
    predicted_low: float,
    high: np.ndarray,
    low: np.ndarray,
    row_index: int,
) -> ForecastRow:
    future_high = float(np.max(high[row_index + 1 : row_index + 1 + horizon]))
    future_low = float(np.min(low[row_index + 1 : row_index + 1 + horizon]))
    atr_value = max(float(atr_reference), 1e-9)
    pred_up = (float(predicted_high) - reference_close) / atr_value
    pred_down = (reference_close - float(predicted_low)) / atr_value
    real_up = (future_high - reference_close) / atr_value
    real_down = (reference_close - future_low) / atr_value
    pred_width = float(predicted_high) - float(predicted_low)
    pred_width_atr = pred_width / atr_value
    real_width_atr = (future_high - future_low) / atr_value
    high_error = pred_up - real_up
    low_error = pred_down - real_down
    width_error = pred_width_atr - real_width_atr
    return ForecastRow(
        timeframe=timeframe,
        timestamp=str(timestamp),
        row_index=int(index),
        horizon_bars=int(horizon),
        reference_close=float(reference_close),
        atr_reference=float(atr_value),
        predicted_high=float(predicted_high),
        predicted_low=float(predicted_low),
        predicted_width=float(pred_width),
        predicted_up_atr=float(pred_up),
        predicted_down_atr=float(pred_down),
        predicted_width_atr=float(pred_width_atr),
        realized_high=float(future_high),
        realized_low=float(future_low),
        realized_up_atr=float(real_up),
        realized_down_atr=float(real_down),
        realized_width_atr=float(real_width_atr),
        high_error_atr=float(high_error),
        low_error_atr=float(low_error),
        width_error_atr=float(width_error),
        high_abs_error_atr=float(abs(high_error)),
        low_abs_error_atr=float(abs(low_error)),
        coherent_high_gate=int(float(predicted_high) >= reference_close),
        coherent_low_gate=int(float(predicted_low) <= reference_close),
        coherent_range_gate=int(float(predicted_high) >= float(predicted_low)),
        atr_regime="",
        predicted_width_regime="",
    )


def assign_regimes(rows: Sequence[ForecastRow]) -> list[ForecastRow]:
    if not rows:
        return []
    atr_values = np.asarray([row.atr_reference for row in rows], dtype=np.float64)
    width_values = np.asarray([row.predicted_width_atr for row in rows], dtype=np.float64)
    atr_q1, atr_q2 = np.percentile(atr_values, [33.333, 66.667])
    width_q1, width_q2 = np.percentile(width_values, [33.333, 66.667])
    output: list[ForecastRow] = []
    for row in rows:
        output.append(
            ForecastRow(
                **{
                    **asdict(row),
                    "atr_regime": f"atr_{regime_label(row.atr_reference, atr_q1, atr_q2)}",
                    "predicted_width_regime": f"pred_width_{regime_label(row.predicted_width_atr, width_q1, width_q2)}",
                }
            )
        )
    return output


def prediction_is_effectively_constant(values: pd.Series, abs_tol: float = 1e-8, rel_tol: float = 1e-6) -> bool:
    """True when binning would only split float noise, not a real forecast."""
    data = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < 2:
        return True
    span = float(data.max() - data.min())
    scale = max(abs(float(data.median())), 1e-12)
    return span <= abs_tol or span / scale <= rel_tol


def calibration_bins(timeframe: str, rows: Sequence[ForecastRow], bins: int) -> list[CalibrationBinRow]:
    output: list[CalibrationBinRow] = []
    frame = pd.DataFrame([asdict(row) for row in rows])
    if frame.empty:
        return []
    for side, pred_col, real_col in (
        ("up", "predicted_up_atr", "realized_up_atr"),
        ("down", "predicted_down_atr", "realized_down_atr"),
    ):
        values = pd.to_numeric(frame[pred_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if prediction_is_effectively_constant(values):
            continue
        try:
            frame["_bin"] = pd.qcut(frame[pred_col], q=max(int(bins), 2), labels=False, duplicates="drop")
        except ValueError:
            continue
        for bin_id, group in frame.groupby("_bin"):
            pred = group[pred_col].to_numpy(dtype=np.float64)
            real = group[real_col].to_numpy(dtype=np.float64)
            output.append(
                CalibrationBinRow(
                    timeframe=timeframe,
                    side=side,
                    bin_id=int(bin_id),
                    rows=int(len(group)),
                    pred_min=float(np.min(pred)),
                    pred_max=float(np.max(pred)),
                    mean_pred_atr=float(np.mean(pred)),
                    mean_realized_atr=float(np.mean(real)),
                    hit_rate_pred_reached=float(np.mean(real >= pred)) if len(real) else 0.0,
                    hit_rate_1atr=float(np.mean(real >= 1.0)) if len(real) else 0.0,
                    hit_rate_15atr=float(np.mean(real >= 1.5)) if len(real) else 0.0,
                )
            )
    return output


def monotonicity(bin_rows: Sequence[CalibrationBinRow], timeframe: str, side: str) -> float:
    rows = sorted([row for row in bin_rows if row.timeframe == timeframe and row.side == side], key=lambda row: row.bin_id)
    if len(rows) < 2:
        return 0.0
    diffs = [rows[i + 1].mean_realized_atr - rows[i].mean_realized_atr for i in range(len(rows) - 1)]
    return float(sum(1 for diff in diffs if diff >= -1e-9) / len(diffs))


def decision_scores(rows: Sequence[ForecastRow], edge: float, mfe: float, mae: float) -> tuple[list[float], int, int, int]:
    scores: list[float] = []
    buy = 0
    sell = 0
    selected = 0
    for row in rows:
        direction = row.predicted_up_atr - row.predicted_down_atr
        if direction >= edge:
            selected += 1
            buy += 1
            passed = row.realized_up_atr >= mfe and row.realized_down_atr <= mae
            scores.append(float(mfe if passed else -mae))
        elif direction <= -edge:
            selected += 1
            sell += 1
            passed = row.realized_down_atr >= mfe and row.realized_up_atr <= mae
            scores.append(float(mfe if passed else -mae))
    return scores, selected, buy, sell


def decision_utility_rows(timeframe: str, rows: Sequence[ForecastRow], args: argparse.Namespace) -> list[DecisionUtilityRow]:
    output: list[DecisionUtilityRow] = []
    edge = float(args.decision_edge_atr)
    mfe = float(args.decision_mfe_atr)
    mae = float(args.decision_mae_atr)
    policies = {
        "range_direction_edge": rows,
        "top_predicted_width_half": sorted(rows, key=lambda row: row.predicted_width_atr, reverse=True)[: max(len(rows) // 2, 1)],
    }
    for policy_id, policy_rows in policies.items():
        scores, selected, buy, sell = decision_scores(policy_rows, edge, mfe, mae)
        quality = float(np.mean([score > 0 for score in scores])) if scores else 0.0
        mean_score = float(np.mean(scores)) if scores else 0.0
        pf = profit_factor(scores)
        verdict = "POSITIVE_PROXY" if mean_score > 0 and pf >= 1.0 else "NO_DECISION_EDGE"
        output.append(
            DecisionUtilityRow(
                timeframe=timeframe,
                policy_id=policy_id,
                rows=int(len(rows)),
                selected_events=int(selected),
                selected_rate=safe_div(selected, len(rows)),
                buy_events=int(buy),
                sell_events=int(sell),
                quality_pass_rate=quality,
                mean_score_atr=mean_score,
                profit_factor_proxy=float(pf),
                verdict=verdict,
            )
        )
    return output


def regime_rows(timeframe: str, rows: Sequence[ForecastRow], args: argparse.Namespace) -> list[RegimeRow]:
    output: list[RegimeRow] = []
    frame = pd.DataFrame([asdict(row) for row in rows])
    if frame.empty:
        return []
    for axis in ("atr_regime", "predicted_width_regime"):
        for regime, group in frame.groupby(axis):
            subset = [ForecastRow(**record) for record in group.to_dict("records")]
            scores, selected, _buy, _sell = decision_scores(subset, float(args.decision_edge_atr), float(args.decision_mfe_atr), float(args.decision_mae_atr))
            output.append(
                RegimeRow(
                    timeframe=timeframe,
                    regime_axis=axis,
                    regime=str(regime),
                    rows=int(len(group)),
                    median_abs_high_error_atr=percentile(group["high_abs_error_atr"], 50),
                    median_abs_low_error_atr=percentile(group["low_abs_error_atr"], 50),
                    up_spearman=spearman(group["predicted_up_atr"], group["realized_up_atr"]),
                    down_spearman=spearman(group["predicted_down_atr"], group["realized_down_atr"]),
                    decision_proxy_quality_rate=float(np.mean([score > 0 for score in scores])) if scores else 0.0,
                    decision_proxy_mean_score=float(np.mean(scores)) if scores else 0.0,
                )
            )
    return output


def summary_row(
    timeframe: str,
    source_mode: str,
    model_id: str,
    model_version: int,
    target_units: str,
    horizon: int,
    rows: Sequence[ForecastRow],
    cal_rows: Sequence[CalibrationBinRow],
    args: argparse.Namespace,
) -> SummaryRow:
    high_err = [row.high_error_atr for row in rows]
    low_err = [row.low_error_atr for row in rows]
    high_abs = [row.high_abs_error_atr for row in rows]
    low_abs = [row.low_abs_error_atr for row in rows]
    coherent = [int(row.coherent_high_gate and row.coherent_low_gate and row.coherent_range_gate) for row in rows]
    up_corr = spearman([row.predicted_up_atr for row in rows], [row.realized_up_atr for row in rows])
    down_corr = spearman([row.predicted_down_atr for row in rows], [row.realized_down_atr for row in rows])
    width_corr = spearman([row.predicted_width_atr for row in rows], [row.realized_width_atr for row in rows])
    up_mono = monotonicity(cal_rows, timeframe, "up")
    down_mono = monotonicity(cal_rows, timeframe, "down")
    scores, selected, _buy, _sell = decision_scores(rows, float(args.decision_edge_atr), float(args.decision_mfe_atr), float(args.decision_mae_atr))
    quality = float(np.mean([score > 0 for score in scores])) if scores else 0.0
    mean_score = float(np.mean(scores)) if scores else 0.0
    baseline_buy = float(np.mean([row.realized_up_atr >= float(args.decision_mfe_atr) and row.realized_down_atr <= float(args.decision_mae_atr) for row in rows])) if rows else 0.0
    baseline_sell = float(np.mean([row.realized_down_atr >= float(args.decision_mfe_atr) and row.realized_up_atr <= float(args.decision_mae_atr) for row in rows])) if rows else 0.0
    coherent_rate = float(np.mean(coherent)) if coherent else 0.0
    high_coherent = float(np.mean([row.coherent_high_gate for row in rows])) if rows else 0.0
    low_coherent = float(np.mean([row.coherent_low_gate for row in rows])) if rows else 0.0
    median_high = percentile(high_abs, 50)
    median_low = percentile(low_abs, 50)
    coherence_gate = int(coherent_rate >= float(args.min_coherent_rate))
    error_gate = int(median_high <= float(args.max_median_abs_error_atr) and median_low <= float(args.max_median_abs_error_atr))
    ranking_gate = int(abs(up_corr) >= float(args.min_abs_spearman) and abs(down_corr) >= float(args.min_abs_spearman))
    calibration_gate = int(up_mono >= float(args.min_monotonicity) and down_mono >= float(args.min_monotonicity))
    decision_gate = int(quality >= max(baseline_buy, baseline_sell) + float(args.min_decision_quality_lift) and mean_score > 0)
    reliability_gate = int(coherence_gate and error_gate and ranking_gate and calibration_gate and decision_gate)
    failures = []
    if not coherence_gate:
        failures.append("coherence_gate_failed")
    if not error_gate:
        failures.append("error_gate_failed")
    if not ranking_gate:
        failures.append("ranking_gate_failed")
    if not calibration_gate:
        failures.append("calibration_gate_failed")
    if not decision_gate:
        failures.append("decision_utility_gate_failed")
    return SummaryRow(
        timeframe=timeframe,
        source_mode=source_mode,
        model_id=model_id,
        model_version=int(model_version),
        target_units=target_units,
        horizon_bars=int(horizon),
        rows=int(len(rows)),
        coherent_rate=coherent_rate,
        high_coherent_rate=high_coherent,
        low_coherent_rate=low_coherent,
        median_abs_high_error_atr=median_high,
        median_abs_low_error_atr=median_low,
        p90_abs_high_error_atr=percentile(high_abs, 90),
        p90_abs_low_error_atr=percentile(low_abs, 90),
        high_bias_atr=float(np.mean(high_err)) if high_err else 0.0,
        low_bias_atr=float(np.mean(low_err)) if low_err else 0.0,
        high_rmse_atr=rmse(high_err),
        low_rmse_atr=rmse(low_err),
        up_spearman=up_corr,
        down_spearman=down_corr,
        width_spearman=width_corr,
        up_monotonicity=up_mono,
        down_monotonicity=down_mono,
        decision_proxy_trades=int(selected),
        decision_proxy_rate=safe_div(selected, len(rows)),
        decision_proxy_quality_rate=quality,
        decision_proxy_mean_score=mean_score,
        baseline_buy_quality_rate=baseline_buy,
        baseline_sell_quality_rate=baseline_sell,
        coherence_gate=coherence_gate,
        error_gate=error_gate,
        ranking_gate=ranking_gate,
        calibration_gate=calibration_gate,
        decision_utility_gate=decision_gate,
        range_reliability_gate=reliability_gate,
        primary_failure_reason=failures[0] if failures else "none",
    )


def decision_matrix(summaries: Sequence[SummaryRow]) -> list[DecisionRow]:
    reliable = [row for row in summaries if row.range_reliability_gate]
    best = max(summaries, key=lambda row: (row.range_reliability_gate, row.decision_proxy_mean_score, -row.median_abs_high_error_atr)) if summaries else None
    best_text = f"{best.timeframe}: gate={best.range_reliability_gate}" if best else "none"
    return [
        DecisionRow(
            route_id="RANGE_AS_TP_SL_ENGINE",
            status="BLOCKED" if not reliable else "OWNER_REVIEW_REQUIRED",
            score=0.0 if not reliable else 60.0,
            evidence=f"reliable_timeframes={len(reliable)}; best={best_text}",
            recommendation="Do not use range model as TP/SL engine unless reliability and decision gates pass.",
        ),
        DecisionRow(
            route_id="RANGE_AS_CONTEXT_FEATURE",
            status="DIAGNOSTIC_ONLY" if not reliable else "CANDIDATE_CONTEXT_FEATURE",
            score=45.0 if not reliable else 65.0,
            evidence="Range forecasts may still be useful as weak context if ranking/regime diagnostics are nonzero.",
            recommendation="Use only as context after owner review; never as execution authority from this phase alone.",
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="Phase185A is reliability audit only.",
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


def render_html(report: Phase185AReport, title: str) -> str:
    summary_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{int(row['rows'])}</td>"
        f"<td>{float(row['coherent_rate']):.3f}</td>"
        f"<td>{float(row['median_abs_high_error_atr']):.3f}</td>"
        f"<td>{float(row['median_abs_low_error_atr']):.3f}</td>"
        f"<td>{float(row['up_spearman']):.3f}</td>"
        f"<td>{float(row['down_spearman']):.3f}</td>"
        f"<td>{int(row['range_reliability_gate'])}</td>"
        "</tr>"
        for row in report.summary_rows
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
    pre = html.escape(json.dumps({"ready_gate": report.range_model_reliability_ready_gate, "selected": report.selected_timeframe, "production_status": report.production_status}, indent=2))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;background:#10131a;color:#eef2ff;margin:0;padding:24px}}section{{background:#171b25;border:1px solid #2b3242;border-radius:14px;padding:18px;margin:16px 0}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #303849;padding:8px;text-align:left}}th{{color:#a7c7ff}}pre{{white-space:pre-wrap;background:#0b0e14;padding:12px;border-radius:10px}}</style></head><body>
<section><h1>{html.escape(title)}</h1><p><strong>{html.escape(report.production_status)}</strong></p><pre>{pre}</pre></section>
<section><h2>Summary</h2><table><thead><tr><th>TF</th><th>Rows</th><th>Coherent</th><th>High MAE</th><th>Low MAE</th><th>Up rho</th><th>Down rho</th><th>Reliable</th></tr></thead><tbody>{summary_rows}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase185AReport:
    args = parse_args(argv)
    timeframes = parse_timeframes(args.timeframes)
    all_rows: list[ForecastRow] = []
    summaries: list[SummaryRow] = []
    all_cal: list[CalibrationBinRow] = []
    all_regimes: list[RegimeRow] = []
    all_utility: list[DecisionUtilityRow] = []
    for timeframe in timeframes:
        if args.source_mode == "models":
            rows, model_id, version, units, horizon = model_forecast_rows(timeframe, args)
        else:
            rows, model_id, version, units, horizon = predictions_forecast_rows(timeframe, args)
        rows = assign_regimes(rows)
        cal = calibration_bins(timeframe, rows, int(args.calibration_bins))
        summary = summary_row(timeframe, args.source_mode, model_id, version, units, horizon, rows, cal, args)
        all_rows.extend(rows)
        all_cal.extend(cal)
        summaries.append(summary)
        all_regimes.extend(regime_rows(timeframe, rows, args))
        all_utility.extend(decision_utility_rows(timeframe, rows, args))

    reliable_count = sum(row.range_reliability_gate for row in summaries)
    selected = max(summaries, key=lambda row: (row.range_reliability_gate, row.decision_proxy_mean_score, -row.median_abs_high_error_atr)) if summaries else None
    decisions = decision_matrix(summaries)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    output_errors = output_dir / "latest_forecast_errors.csv"
    output_summary = output_dir / "latest_summary.csv"
    output_cal = output_dir / "latest_calibration_bins.csv"
    output_regime = output_dir / "latest_regime_breakdown.csv"
    output_utility = output_dir / "latest_decision_utility.csv"
    output_decisions = output_dir / "latest_decision_matrix.csv"

    report = Phase185AReport(
        symbol=str(args.symbol).upper(),
        timeframes=timeframes,
        source_mode=str(args.source_mode),
        evaluated_timeframes=len(summaries),
        reliable_timeframes=int(reliable_count),
        selected_timeframe=selected.timeframe if selected else "",
        selected_reliability_gate=int(selected.range_reliability_gate) if selected else 0,
        range_model_reliability_ready_gate=int(reliable_count == len(summaries) and reliable_count > 0),
        no_training_gate=1,
        no_paper_live_gate=1,
        summary_rows=[asdict(row) for row in summaries],
        calibration_rows=[asdict(row) for row in all_cal],
        regime_rows=[asdict(row) for row in all_regimes],
        decision_utility_rows=[asdict(row) for row in all_utility],
        decision_matrix=[asdict(row) for row in decisions],
        output_json=str(output_json),
        output_html=str(output_html),
        output_forecast_errors_csv=str(output_errors),
        output_summary_csv=str(output_summary),
        output_calibration_bins_csv=str(output_cal),
        output_regime_breakdown_csv=str(output_regime),
        output_decision_utility_csv=str(output_utility),
        output_decision_matrix_csv=str(output_decisions),
        production_status="BLOCKED — Phase185A range reliability audit only; no model training/paper/live",
    )
    write_csv(output_errors, [asdict(row) for row in all_rows])
    write_csv(output_summary, report.summary_rows)
    write_csv(output_cal, report.calibration_rows)
    write_csv(output_regime, report.regime_rows)
    write_csv(output_utility, report.decision_utility_rows)
    write_csv(output_decisions, report.decision_matrix)
    output_html.write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    output_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[DONE] Phase185A range model reliability audit complete")
    print(f"  symbol      : {report.symbol}")
    print(f"  timeframes  : {','.join(report.timeframes)}")
    print(f"  reliable    : {report.reliable_timeframes}/{report.evaluated_timeframes}")
    print(f"  ready gate  : {report.range_model_reliability_ready_gate}")
    print(f"  json        : {report.output_json}")
    print(f"  html        : {report.output_html}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
