"""Phase141A: multi-timeframe pivot/top-bottom pattern recognition.

This research phase trains and validates a causal pattern-recognition model for
gold reversal zones. It is deliberately not a production/live-trading gate.

The model asks a different question from the failed hybrid candidate stream:

* Is the current 5M context near a top zone that is followed by downside?
* Is it near a bottom zone that is followed by upside?
* Or should the system stay flat?

Data can come from public Yahoo Finance (``GC=F`` by default) or from local CSV /
Parquet files. Yahoo's spot ``XAUUSD=X`` intraday endpoint is often unavailable,
so ``GC=F`` is a practical public proxy, not a broker-perfect Alpari feed.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import html
import json
import pickle
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_recognition")
ACTION_SELL = 0
ACTION_HOLD = 1
ACTION_BUY = 2
ACTION_NAMES = {ACTION_SELL: "SELL", ACTION_HOLD: "HOLD", ACTION_BUY: "BUY"}
MODEL_KINDS = ("auto", "sklearn_hgb", "centroid")
SCORE_METRICS = ("net_profit", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class PivotLabelConfig:
    lookahead_bars: int
    pivot_move_atr: float
    pivot_zone_atr: float
    recent_window_bars: int
    min_direction_edge: float


@dataclass(frozen=True)
class Trade:
    timestamp: str
    fold: int
    side: str
    row_id: int
    entry_row_id: int
    exit_row_id: int
    entry: float
    tp: float
    sl: float
    exit_price: float
    points_pnl: float
    cash_pnl: float
    balance: float
    outcome: str
    tp_distance: float
    sl_distance: float
    risk_amount: float


@dataclass(frozen=True)
class FeatureSelectionRow:
    feature: str
    score: float
    selected_count: int
    mean_rank: float
    family: str


@dataclass(frozen=True)
class FoldSummary:
    fold: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_rows: int
    validation_rows: int
    test_rows: int
    train_class_counts: dict[str, int]
    validation_class_counts: dict[str, int]
    test_class_counts: dict[str, int]
    selected_features: list[str]
    selected_params: dict[str, Any]
    validation_accuracy: float
    test_accuracy: float
    validation_result: dict[str, Any]
    test_result: dict[str, Any]


@dataclass(frozen=True)
class PivotReport:
    source_mode: str
    market_symbol: str
    data_note: str
    daily_rows: int
    h4_rows: int
    five_rows: int
    feature_rows: int
    feature_columns_total: int
    selected_feature_count: int
    target_counts: dict[str, int]
    folds: int
    initial_balance: float
    final_balance: float
    net_profit: float
    return_percent: float
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    max_drawdown_cash: float
    positive_folds: int
    negative_folds: int
    production_status: str
    output_json: str
    output_html: str
    output_folds_csv: str
    output_trades_csv: str
    output_features_csv: str
    model_path: str
    training_record_path: str


class CentroidPatternModel:
    """Small dependency-free baseline classifier used when sklearn is absent.

    It standardizes the selected feature matrix, stores one centroid per class,
    and converts negative distances to probabilities. This is a real trainable
    baseline, not a placeholder, but the preferred model is sklearn HGB when the
    optional package is available.
    """

    def __init__(self) -> None:
        self.classes_ = np.asarray([ACTION_SELL, ACTION_HOLD, ACTION_BUY], dtype=np.int64)
        self.mean_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None
        self.centroids_: np.ndarray | None = None
        self.priors_: np.ndarray | None = None

    def fit(self, x_values: np.ndarray, y_values: np.ndarray) -> "CentroidPatternModel":
        x = np.asarray(x_values, dtype=np.float64)
        y = np.asarray(y_values, dtype=np.int64)
        self.mean_ = np.nanmean(x, axis=0)
        scale = np.nanstd(x, axis=0)
        self.scale_ = np.where(scale <= 1e-9, 1.0, scale)
        z = (x - self.mean_) / self.scale_
        centroids: list[np.ndarray] = []
        priors: list[float] = []
        global_centroid = np.nanmean(z, axis=0)
        for cls in self.classes_:
            mask = y == int(cls)
            if np.any(mask):
                centroids.append(np.nanmean(z[mask], axis=0))
                priors.append(float(np.mean(mask)))
            else:
                centroids.append(global_centroid)
                priors.append(1e-6)
        self.centroids_ = np.vstack(centroids)
        priors_arr = np.asarray(priors, dtype=np.float64)
        self.priors_ = priors_arr / max(float(priors_arr.sum()), 1e-12)
        return self

    def predict_proba(self, x_values: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None or self.centroids_ is None:
            raise RuntimeError("CentroidPatternModel must be fitted before predict_proba")
        x = np.asarray(x_values, dtype=np.float64)
        z = (x - self.mean_) / self.scale_
        distances = np.sqrt(((z[:, None, :] - self.centroids_[None, :, :]) ** 2).mean(axis=2))
        logits = -distances + np.log(np.maximum(self.priors_, 1e-9))[None, :]
        logits -= logits.max(axis=1, keepdims=True)
        raw = np.exp(logits)
        return raw / raw.sum(axis=1, keepdims=True)

    def predict(self, x_values: np.ndarray) -> np.ndarray:
        return self.classes_[self.predict_proba(x_values).argmax(axis=1)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and walk-forward backtest a pivot/top-bottom pattern-recognition model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source-mode", choices=("storage", "yahoo", "files"), default="storage")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--yahoo-symbol", default="GC=F")
    parser.add_argument("--daily-range", default="5y")
    parser.add_argument("--hourly-range", default="730d")
    parser.add_argument("--five-range", default="60d")
    parser.add_argument("--five-timeframe", default="5M")
    parser.add_argument("--hourly-timeframe", default="1H")
    parser.add_argument("--h4-timeframe", default="4H")
    parser.add_argument("--daily-timeframe", default="1D")
    parser.add_argument("--daily-path", default="")
    parser.add_argument("--hourly-path", default="")
    parser.add_argument("--h4-path", default="")
    parser.add_argument("--five-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_recognition_5m")
    parser.add_argument("--model-kind", choices=MODEL_KINDS, default="auto")
    parser.add_argument("--lookahead-bars", type=int, default=48)
    parser.add_argument("--pivot-move-atr", type=float, default=0.75)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.35)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--min-direction-edge", type=float, default=1.10)
    parser.add_argument("--max-features", type=int, default=38)
    parser.add_argument("--train-days-min", type=int, default=20)
    parser.add_argument("--validation-days", type=int, default=5)
    parser.add_argument("--test-days", type=int, default=5)
    parser.add_argument("--purge-hours", type=float, default=4.0)
    parser.add_argument("--buy-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--sell-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--margins", default="0,0.05")
    parser.add_argument("--tp-multipliers", default="0.75,1.0,1.25")
    parser.add_argument("--sl-multipliers", default="0.50,0.75")
    parser.add_argument("--hold-bars", default="24,48")
    parser.add_argument("--min-validation-trades", type=int, default=5)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="net_profit")
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--save-model", choices=("0", "1"), default="1")
    parser.add_argument("--save-data", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Pivot pattern recognition walk-forward")
    return parser.parse_args(argv)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    values: list[float] = []
    for raw in (part.strip() for part in text.split(",")):
        if not raw:
            continue
        value = float(raw)
        if value not in values:
            values.append(value)
    return values or list(default)


def parse_int_grid(text: str, default: Sequence[int]) -> list[int]:
    values: list[int] = []
    for raw in (part.strip() for part in text.split(",")):
        if not raw:
            continue
        value = max(int(raw), 1)
        if value not in values:
            values.append(value)
    return values or list(default)


def class_counts(y_values: Sequence[int] | pd.Series | np.ndarray) -> dict[str, int]:
    y = np.asarray(y_values, dtype=np.int64)
    return {name: int(np.sum(y == cls)) for cls, name in ACTION_NAMES.items()}


def fetch_yahoo(symbol: str, interval: str, range_text: str) -> pd.DataFrame:
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?interval={interval}&range={range_text}&includePrePost=false"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo Finance error for {symbol} {interval}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo Finance returned no data for {symbol} {interval}")
    timestamps = result.get("timestamp") or []
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, unit="s", utc=True),
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
        }
    )
    return normalize_ohlcv(frame)


def read_ohlcv(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise RuntimeError(f"Input file does not exist: {source}")
    if source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
    else:
        frame = pd.read_csv(source)
    return normalize_ohlcv(frame)


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "time": "timestamp",
        "date": "timestamp",
        "datetime": "timestamp",
        "open_time": "timestamp",
        "tick_volume": "volume",
        "real_volume": "volume",
    }
    result = frame.rename(
        columns={key: value for key, value in aliases.items() if key in frame.columns}
    )
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(result.columns)
    if missing:
        raise RuntimeError(f"OHLCV data missing columns: {sorted(missing)}")
    if "volume" not in result.columns:
        result["volume"] = 0.0
    result = result[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result = result.dropna(subset=["timestamp", "open", "high", "low", "close"])
    for column in ("open", "high", "low", "close", "volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["open", "high", "low", "close"])
    return result.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)


def resample_4h(hourly: pd.DataFrame) -> pd.DataFrame:
    source = hourly.set_index("timestamp").sort_index()
    frame = source.resample("4h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return normalize_ohlcv(frame.dropna(subset=["open", "high", "low", "close"]).reset_index())


def storage_timeframe_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    directory = storage_root / "processed" / symbol / timeframe.upper()
    if not directory.exists():
        available = (
            sorted(
                str(path.relative_to(storage_root))
                for path in (storage_root / "processed").glob("*/*")
                if path.is_dir()
            )
            if (storage_root / "processed").exists()
            else []
        )
        raise RuntimeError(
            f"Stored dataset not found for {symbol} {timeframe}: {directory}. "
            f"Available processed datasets: {', '.join(available) or 'none'}"
        )
    versioned = []
    for path in directory.glob("v*.parquet"):
        raw = path.stem.removeprefix("v")
        if raw.isdigit():
            versioned.append((int(raw), path))
    if versioned:
        return sorted(versioned, key=lambda item: item[0])[-1][1]
    candidates = sorted(directory.glob("*.parquet"))
    if not candidates:
        raise RuntimeError(f"No parquet files found in stored dataset directory: {directory}")
    return candidates[-1]


def load_storage_ohlcv(storage_root: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    return read_ohlcv(storage_timeframe_path(storage_root, symbol, timeframe))


def load_market_data(
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    if args.source_mode == "storage":
        storage_root = Path(args.storage_root)
        daily = load_storage_ohlcv(storage_root, args.symbol, args.daily_timeframe)
        five = load_storage_ohlcv(storage_root, args.symbol, args.five_timeframe)
        try:
            h4 = load_storage_ohlcv(storage_root, args.symbol, args.h4_timeframe)
            h4_note = f"{args.h4_timeframe} loaded directly from project storage"
        except RuntimeError:
            hourly = load_storage_ohlcv(storage_root, args.symbol, args.hourly_timeframe)
            h4 = resample_4h(hourly)
            h4_note = f"{args.h4_timeframe} resampled from stored {args.hourly_timeframe}"
        note = (
            f"Project storage datasets for {args.symbol}: {args.five_timeframe}, "
            f"{args.daily_timeframe}; {h4_note}."
        )
        return daily, h4, five, note
    if args.source_mode == "yahoo":
        daily = fetch_yahoo(args.yahoo_symbol, "1d", args.daily_range)
        hourly = fetch_yahoo(args.yahoo_symbol, "1h", args.hourly_range)
        five = fetch_yahoo(args.yahoo_symbol, "5m", args.five_range)
        h4 = resample_4h(hourly)
        note = (
            f"Yahoo Finance {args.yahoo_symbol}; 4H resampled from 1H. "
            "This is public gold-futures proxy data, not broker-perfect Alpari XAUUSD."
        )
        return daily, h4, five, note
    if not args.daily_path or not args.five_path:
        raise RuntimeError("files mode needs at least --daily-path and --five-path")
    daily = read_ohlcv(args.daily_path)
    five = read_ohlcv(args.five_path)
    if args.h4_path:
        h4 = read_ohlcv(args.h4_path)
    elif args.hourly_path:
        h4 = resample_4h(read_ohlcv(args.hourly_path))
    else:
        raise RuntimeError("files mode needs --h4-path or --hourly-path")
    return daily, h4, five, "Local file data supplied by operator."


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=max(2, period // 3)).mean()


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(period, min_periods=max(2, period // 2)).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(period, min_periods=max(2, period // 2)).mean()
    losses = (-delta.clip(upper=0)).rolling(period, min_periods=max(2, period // 2)).mean()
    rs = gains / losses.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def add_time_features(frame: pd.DataFrame) -> None:
    hour = frame["timestamp"].dt.hour + frame["timestamp"].dt.minute / 60.0
    dow = frame["timestamp"].dt.dayofweek
    frame["session_hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
    frame["session_hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)
    frame["session_dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
    frame["session_dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)


def candle_features(frame: pd.DataFrame, prefix: str, atr_period: int) -> pd.DataFrame:
    result = frame.copy()
    close = result["close"].replace(0.0, np.nan)
    result[f"{prefix}_ret1"] = result["close"].pct_change(1)
    result[f"{prefix}_ret3"] = result["close"].pct_change(3)
    result[f"{prefix}_ret6"] = result["close"].pct_change(6)
    result[f"{prefix}_ret12"] = result["close"].pct_change(12)
    result[f"{prefix}_body_pct"] = (result["close"] - result["open"]) / close
    result[f"{prefix}_range_pct"] = (result["high"] - result["low"]) / close
    result[f"{prefix}_upper_wick_pct"] = (
        result["high"] - result[["open", "close"]].max(axis=1)
    ) / close
    result[f"{prefix}_lower_wick_pct"] = (
        result[["open", "close"]].min(axis=1) - result["low"]
    ) / close
    result[f"{prefix}_atr"] = atr(result, atr_period)
    result[f"{prefix}_ema_fast"] = ema(result["close"], 9 if prefix == "m5" else 8)
    result[f"{prefix}_ema_mid"] = ema(result["close"], 21 if prefix == "m5" else 20)
    result[f"{prefix}_ema_slow"] = ema(result["close"], 50)
    result[f"{prefix}_fast_mid_dist_atr"] = (
        result[f"{prefix}_ema_fast"] - result[f"{prefix}_ema_mid"]
    ) / result[f"{prefix}_atr"].replace(0.0, np.nan)
    result[f"{prefix}_mid_slow_dist_atr"] = (
        result[f"{prefix}_ema_mid"] - result[f"{prefix}_ema_slow"]
    ) / result[f"{prefix}_atr"].replace(0.0, np.nan)
    result[f"{prefix}_close_mid_dist_atr"] = (
        result["close"] - result[f"{prefix}_ema_mid"]
    ) / result[f"{prefix}_atr"].replace(0.0, np.nan)
    result[f"{prefix}_rsi14"] = rsi(result["close"], 14)
    return result


def htf_feature_frame(frame: pd.DataFrame, prefix: str, close_delay: pd.Timedelta) -> pd.DataFrame:
    enriched = candle_features(frame, prefix, 14)
    rolling_high = enriched["high"].shift(1).rolling(6, min_periods=2).max()
    rolling_low = enriched["low"].shift(1).rolling(6, min_periods=2).min()
    enriched[f"{prefix}_room_up_atr"] = (rolling_high - enriched["close"]) / enriched[
        f"{prefix}_atr"
    ].replace(0.0, np.nan)
    enriched[f"{prefix}_room_down_atr"] = (enriched["close"] - rolling_low) / enriched[
        f"{prefix}_atr"
    ].replace(0.0, np.nan)
    keep = [
        "timestamp",
        f"{prefix}_ret1",
        f"{prefix}_ret3",
        f"{prefix}_body_pct",
        f"{prefix}_range_pct",
        f"{prefix}_atr",
        f"{prefix}_fast_mid_dist_atr",
        f"{prefix}_mid_slow_dist_atr",
        f"{prefix}_close_mid_dist_atr",
        f"{prefix}_rsi14",
        f"{prefix}_room_up_atr",
        f"{prefix}_room_down_atr",
    ]
    result = enriched[keep].copy()
    result["available_at"] = result["timestamp"] + close_delay
    return result.drop(columns=["timestamp"])


def build_feature_frame(
    daily: pd.DataFrame, h4: pd.DataFrame, five: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    m5 = candle_features(five, "m5", 48).sort_values("timestamp").reset_index(drop=True)
    add_time_features(m5)
    for window in (24, 48, 96):
        high = m5["high"].shift(1).rolling(window, min_periods=max(4, window // 4)).max()
        low = m5["low"].shift(1).rolling(window, min_periods=max(4, window // 4)).min()
        width = (high - low).replace(0.0, np.nan)
        m5[f"m5_pos_in_range_{window}"] = (m5["close"] - low) / width
        m5[f"m5_dist_high_{window}_atr"] = (high - m5["close"]) / m5["m5_atr"].replace(0.0, np.nan)
        m5[f"m5_dist_low_{window}_atr"] = (m5["close"] - low) / m5["m5_atr"].replace(0.0, np.nan)
        m5[f"m5_volatility_{window}"] = (
            m5["close"].pct_change().rolling(window, min_periods=max(4, window // 4)).std()
        )
    m5["m5_ret24"] = m5["close"].pct_change(24)
    m5["m5_ret48"] = m5["close"].pct_change(48)
    m5["m5_price_z_96"] = (m5["close"] - m5["close"].rolling(96, min_periods=16).mean()) / m5[
        "close"
    ].rolling(96, min_periods=16).std().replace(0.0, np.nan)
    m5["bar_close_time"] = m5["timestamp"] + pd.Timedelta(minutes=5)

    h4_features = htf_feature_frame(h4, "h4", pd.Timedelta(hours=4)).sort_values("available_at")
    daily_features = htf_feature_frame(daily, "d1", pd.Timedelta(days=1)).sort_values(
        "available_at"
    )
    merged = pd.merge_asof(
        m5.sort_values("bar_close_time"),
        h4_features,
        left_on="bar_close_time",
        right_on="available_at",
        direction="backward",
    ).rename(columns={"available_at": "h4_available_at"})
    merged = pd.merge_asof(
        merged.sort_values("bar_close_time"),
        daily_features,
        left_on="bar_close_time",
        right_on="available_at",
        direction="backward",
    ).rename(columns={"available_at": "d1_available_at"})
    blocked = {
        "timestamp",
        "bar_close_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "h4_available_at",
        "d1_available_at",
    }
    feature_columns = [column for column in merged.columns if column not in blocked]
    merged[feature_columns] = merged[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    merged["h4_atr_for_risk"] = pd.to_numeric(merged.get("h4_atr", 0.0), errors="coerce").fillna(
        0.0
    )
    merged["row_id"] = np.arange(len(merged), dtype=np.int64)
    return merged.sort_values("timestamp").reset_index(drop=True), feature_columns


def label_pivot_targets(frame: pd.DataFrame, config: PivotLabelConfig) -> pd.DataFrame:
    result = frame.copy()
    n_rows = len(result)
    close = result["close"].to_numpy(dtype=np.float64)
    high = result["high"].to_numpy(dtype=np.float64)
    low = result["low"].to_numpy(dtype=np.float64)
    atr4 = result["h4_atr_for_risk"].to_numpy(dtype=np.float64)
    target = np.full(n_rows, ACTION_HOLD, dtype=np.int64)
    top_zone = np.zeros(n_rows, dtype=np.float64)
    bottom_zone = np.zeros(n_rows, dtype=np.float64)
    future_up_r = np.zeros(n_rows, dtype=np.float64)
    future_down_r = np.zeros(n_rows, dtype=np.float64)
    target_available = np.zeros(n_rows, dtype=np.float64)
    for index in range(n_rows):
        atr_value = atr4[index]
        future_start = index + 1
        future_end = min(n_rows, index + 1 + max(config.lookahead_bars, 1))
        if not np.isfinite(atr_value) or atr_value <= 0 or future_start >= future_end:
            continue
        recent_start = max(0, index - max(config.recent_window_bars, 1) + 1)
        recent_high = float(np.nanmax(high[recent_start : index + 1]))
        recent_low = float(np.nanmin(low[recent_start : index + 1]))
        recent_width = max(recent_high - recent_low, 1e-9)
        position = (close[index] - recent_low) / recent_width
        future_high = float(np.nanmax(high[future_start:future_end]))
        future_low = float(np.nanmin(low[future_start:future_end]))
        up_move = future_high - close[index]
        down_move = close[index] - future_low
        up_r = safe_div(up_move, atr_value)
        down_r = safe_div(down_move, atr_value)
        future_up_r[index] = up_r
        future_down_r[index] = down_r
        target_available[index] = 1.0
        near_top = (
            recent_high - close[index] <= config.pivot_zone_atr * atr_value
        ) or position >= 0.75
        near_bottom = (
            close[index] - recent_low <= config.pivot_zone_atr * atr_value
        ) or position <= 0.25
        is_top = (
            near_top
            and down_r >= config.pivot_move_atr
            and down_move >= up_move * config.min_direction_edge
        )
        is_bottom = (
            near_bottom
            and up_r >= config.pivot_move_atr
            and up_move >= down_move * config.min_direction_edge
        )
        if is_top and is_bottom:
            if down_r > up_r:
                is_bottom = False
            else:
                is_top = False
        if is_top:
            target[index] = ACTION_SELL
            top_zone[index] = 1.0
        elif is_bottom:
            target[index] = ACTION_BUY
            bottom_zone[index] = 1.0
    result["target_action"] = target
    result["target_top_zone"] = top_zone
    result["target_bottom_zone"] = bottom_zone
    result["future_up_r"] = future_up_r
    result["future_down_r"] = future_down_r
    result["target_available"] = target_available
    return result


def feature_family(feature: str) -> str:
    if feature.startswith("m5_"):
        return "5M pattern"
    if feature.startswith("h4_"):
        return "4H context"
    if feature.startswith("d1_"):
        return "1D context"
    if feature.startswith("session_"):
        return "session/time"
    return "other"


def rank_features(frame: pd.DataFrame, feature_columns: Sequence[str]) -> list[tuple[str, float]]:
    y = frame["target_action"].astype(int).to_numpy()
    top = frame["target_top_zone"].astype(float).to_numpy()
    bottom = frame["target_bottom_zone"].astype(float).to_numpy()
    ranks: list[tuple[str, float]] = []
    for feature in feature_columns:
        values = (
            pd.to_numeric(frame[feature], errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
            .to_numpy(dtype=np.float64)
        )
        std = float(np.nanstd(values))
        if std <= 1e-12:
            ranks.append((feature, 0.0))
            continue
        mean_all = float(np.nanmean(values))
        class_score = 0.0
        for cls in (ACTION_SELL, ACTION_HOLD, ACTION_BUY):
            mask = y == cls
            if np.any(mask):
                class_score = max(
                    class_score, abs(float(np.nanmean(values[mask])) - mean_all) / std
                )
        corr_top = abs(float(np.corrcoef(values, top)[0, 1])) if np.nanstd(top) > 1e-12 else 0.0
        corr_bottom = (
            abs(float(np.corrcoef(values, bottom)[0, 1])) if np.nanstd(bottom) > 1e-12 else 0.0
        )
        score = class_score + max(0.0, corr_top) + max(0.0, corr_bottom)
        ranks.append((feature, float(score) if np.isfinite(score) else 0.0))
    return sorted(ranks, key=lambda item: item[1], reverse=True)


def selected_features(
    frame: pd.DataFrame, feature_columns: Sequence[str], max_features: int
) -> tuple[list[str], list[tuple[str, float]]]:
    ranking = rank_features(frame, feature_columns)
    limit = len(ranking) if max_features <= 0 else min(max_features, len(ranking))
    return [name for name, _score in ranking[:limit]], ranking


def train_pattern_model(
    kind: str, x_train: np.ndarray, y_train: np.ndarray, random_state: int
) -> tuple[Any, str]:
    requested = kind
    if kind == "auto":
        requested = "sklearn_hgb"
    if requested == "sklearn_hgb":
        try:
            from sklearn.ensemble import HistGradientBoostingClassifier
        except ModuleNotFoundError:
            model = CentroidPatternModel().fit(x_train, y_train)
            return model, "centroid"
        classes, counts = np.unique(y_train, return_counts=True)
        weights = {
            int(cls): safe_div(len(y_train), len(classes) * count)
            for cls, count in zip(classes, counts, strict=True)
        }
        sample_weight = np.asarray(
            [weights.get(int(value), 1.0) for value in y_train], dtype=np.float64
        )
        model = HistGradientBoostingClassifier(
            max_iter=160,
            learning_rate=0.045,
            max_leaf_nodes=15,
            l2_regularization=0.10,
            random_state=random_state,
        )
        model.fit(x_train, y_train, sample_weight=sample_weight)
        return model, "sklearn_hgb"
    model = CentroidPatternModel().fit(x_train, y_train)
    return model, "centroid"


def aligned_predict_proba(model: Any, x_values: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    aligned = np.zeros((len(raw), 3), dtype=np.float64)
    for raw_column, cls in enumerate(classes):
        if 0 <= cls <= 2:
            aligned[:, cls] = raw[:, raw_column]
    row_sums = aligned.sum(axis=1)
    missing = row_sums <= 0
    if np.any(missing):
        aligned[missing, :] = 1.0 / 3.0
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def simple_accuracy(y_true: Sequence[int], probabilities: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int64)
    if len(y) == 0:
        return 0.0
    return float(np.mean(probabilities.argmax(axis=1) == y))


def spread_abs(price: float, mode: str, value: float) -> float:
    if mode == "fixed":
        return max(0.0, value)
    return max(0.0, price * value / 100.0)


def trade_path(
    frame: pd.DataFrame,
    row_id: int,
    side: int,
    tp_distance: float,
    sl_distance: float,
    hold_bars: int,
    args: argparse.Namespace,
) -> tuple[float, int, int, float, float, float, float, str] | None:
    entry_row = row_id + 1
    if entry_row >= len(frame):
        return None
    raw_entry = safe_float(frame.at[entry_row, "open"])
    half_spread = spread_abs(raw_entry, args.spread_mode, args.spread_value) / 2.0
    if side == ACTION_BUY:
        entry = raw_entry + half_spread
        tp = entry + tp_distance
        sl = entry - sl_distance
    else:
        entry = raw_entry - half_spread
        tp = entry - tp_distance
        sl = entry + sl_distance
    max_exit = min(len(frame) - 1, entry_row + max(hold_bars, 1) - 1)
    exit_row = max_exit
    exit_price = safe_float(frame.at[max_exit, "close"])
    outcome = "timeout"
    for index in range(entry_row, max_exit + 1):
        close_for_spread = safe_float(frame.at[index, "close"])
        half_exit_spread = spread_abs(close_for_spread, args.spread_mode, args.spread_value) / 2.0
        high = safe_float(frame.at[index, "high"])
        low = safe_float(frame.at[index, "low"])
        if side == ACTION_BUY:
            hit_tp = high - half_exit_spread >= tp
            hit_sl = low - half_exit_spread <= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_row = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_row = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_row = index
                break
        else:
            hit_tp = low + half_exit_spread <= tp
            hit_sl = high + half_exit_spread >= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_row = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_row = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_row = index
                break
    if outcome == "timeout":
        half_exit_spread = spread_abs(exit_price, args.spread_mode, args.spread_value) / 2.0
        exit_price = (
            exit_price - half_exit_spread if side == ACTION_BUY else exit_price + half_exit_spread
        )
    points = exit_price - entry if side == ACTION_BUY else entry - exit_price
    return (
        float(points),
        entry_row,
        exit_row,
        float(entry),
        float(tp),
        float(sl),
        float(exit_price),
        outcome,
    )


def decide(probability: Sequence[float], params: dict[str, Any]) -> int | None:
    sell_probability, hold_probability, buy_probability = [float(value) for value in probability]
    margin = float(params["margin"])
    buy_ok = (
        buy_probability >= float(params["buy_threshold"])
        and buy_probability - max(sell_probability, hold_probability) >= margin
    )
    sell_ok = (
        sell_probability >= float(params["sell_threshold"])
        and sell_probability - max(buy_probability, hold_probability) >= margin
    )
    if buy_ok and not sell_ok:
        return ACTION_BUY
    if sell_ok and not buy_ok:
        return ACTION_SELL
    return None


def max_drawdown(balances: Sequence[float]) -> float:
    peak = float(balances[0]) if balances else 0.0
    worst = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        worst = max(worst, peak - float(balance))
    return worst


def simulate_strategy(
    full_frame: pd.DataFrame,
    signal_frame: pd.DataFrame,
    probabilities: np.ndarray,
    params: dict[str, Any],
    args: argparse.Namespace,
    starting_balance: float,
    fold: int,
) -> tuple[dict[str, Any], list[Trade]]:
    balance = float(starting_balance)
    open_until = -1
    trades: list[Trade] = []
    balances = [balance]
    for offset, (_, row) in enumerate(signal_frame.iterrows()):
        row_id = int(row["row_id"])
        if row_id <= open_until:
            continue
        side = decide(probabilities[offset], params)
        if side is None:
            continue
        atr_value = safe_float(row.get("h4_atr_for_risk", 0.0))
        if atr_value <= 0:
            continue
        tp_distance = max(atr_value * float(params["tp_multiplier"]), 0.5)
        sl_distance = max(atr_value * float(params["sl_multiplier"]), 0.5)
        path = trade_path(
            full_frame, row_id, side, tp_distance, sl_distance, int(params["hold_bars"]), args
        )
        if path is None:
            continue
        points, entry_row, exit_row, entry, tp, sl, exit_price, outcome = path
        risk_amount = max(balance * float(args.risk_per_trade), 0.0)
        quantity = safe_div(risk_amount, sl_distance)
        cash_pnl = points * quantity
        balance += cash_pnl
        balances.append(balance)
        trade = Trade(
            timestamp=str(row["timestamp"]),
            fold=fold,
            side=ACTION_NAMES[side],
            row_id=row_id,
            entry_row_id=entry_row,
            exit_row_id=exit_row,
            entry=entry,
            tp=tp,
            sl=sl,
            exit_price=exit_price,
            points_pnl=points,
            cash_pnl=cash_pnl,
            balance=balance,
            outcome=outcome,
            tp_distance=tp_distance,
            sl_distance=sl_distance,
            risk_amount=risk_amount,
        )
        trades.append(trade)
        open_until = max(open_until, exit_row)
        if balance <= 0:
            break
    pnls = [trade.cash_pnl for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    result = {
        "start_balance": starting_balance,
        "final_balance": balance,
        "net_profit": balance - starting_balance,
        "return_percent": safe_div(balance - starting_balance, starting_balance),
        "trades": len(trades),
        "buy_trades": sum(1 for trade in trades if trade.side == "BUY"),
        "sell_trades": sum(1 for trade in trades if trade.side == "SELL"),
        "wins": wins,
        "losses": losses,
        "win_rate": safe_div(wins, len(trades)),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": (
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        "max_drawdown_cash": max_drawdown(balances),
        "take_profits": sum(1 for trade in trades if trade.outcome == "take_profit"),
        "stop_losses": sum(1 for trade in trades if trade.outcome == "stop_loss"),
        "timeouts": sum(1 for trade in trades if trade.outcome == "timeout"),
    }
    return result, trades


def parameter_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for buy_threshold in parse_float_grid(args.buy_thresholds, [0.45, 0.55, 0.65]):
        for sell_threshold in parse_float_grid(args.sell_thresholds, [0.45, 0.55, 0.65]):
            for margin in parse_float_grid(args.margins, [0.0, 0.05]):
                for tp_multiplier in parse_float_grid(args.tp_multipliers, [0.75, 1.0, 1.25]):
                    for sl_multiplier in parse_float_grid(args.sl_multipliers, [0.5, 0.75]):
                        for hold_bars in parse_int_grid(args.hold_bars, [24, 48]):
                            rows.append(
                                {
                                    "buy_threshold": buy_threshold,
                                    "sell_threshold": sell_threshold,
                                    "margin": margin,
                                    "tp_multiplier": tp_multiplier,
                                    "sl_multiplier": sl_multiplier,
                                    "hold_bars": hold_bars,
                                }
                            )
    return rows


def validation_score(result: dict[str, Any], args: argparse.Namespace) -> float:
    if int(result["trades"]) < max(int(args.min_validation_trades), 0):
        return -1e18 + int(result["trades"])
    if args.score_metric == "profit_factor":
        return float(result["profit_factor"])
    if args.score_metric == "final_balance":
        return float(result["final_balance"])
    if args.score_metric == "drawdown_adjusted":
        return float(result["net_profit"]) - 0.25 * float(result["max_drawdown_cash"])
    return float(result["net_profit"]) - 0.15 * float(result["max_drawdown_cash"])


def select_policy(
    full_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    validation_probabilities: np.ndarray,
    args: argparse.Namespace,
    fold: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    best_params: dict[str, Any] | None = None
    best_result: dict[str, Any] | None = None
    best_score = -1e30
    for params in parameter_grid(args):
        result, _trades = simulate_strategy(
            full_frame,
            validation_frame,
            validation_probabilities,
            params,
            args,
            args.initial_capital,
            fold,
        )
        score = validation_score(result, args)
        if score > best_score:
            best_score = score
            best_params = params
            best_result = result
    if best_params is None or best_result is None:
        raise RuntimeError("No validation policy was selected")
    return best_params, best_result


def aggregate_trades(trades: Sequence[Trade], initial_balance: float) -> dict[str, Any]:
    pnls = [trade.cash_pnl for trade in trades]
    balances = [initial_balance]
    for pnl in pnls:
        balances.append(balances[-1] + pnl)
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    final_balance = balances[-1] if balances else initial_balance
    return {
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "net_profit": final_balance - initial_balance,
        "return_percent": safe_div(final_balance - initial_balance, initial_balance),
        "trades": len(trades),
        "buy_trades": sum(1 for trade in trades if trade.side == "BUY"),
        "sell_trades": sum(1 for trade in trades if trade.side == "SELL"),
        "wins": wins,
        "losses": losses,
        "win_rate": safe_div(wins, len(trades)),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": (
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        "max_drawdown_cash": max_drawdown(balances),
        "take_profits": sum(1 for trade in trades if trade.outcome == "take_profit"),
        "stop_losses": sum(1 for trade in trades if trade.outcome == "stop_loss"),
        "timeouts": sum(1 for trade in trades if trade.outcome == "timeout"),
    }


def walk_forward(
    frame: pd.DataFrame, feature_columns: Sequence[str], args: argparse.Namespace
) -> tuple[list[FoldSummary], list[Trade], list[FeatureSelectionRow], str]:
    usable = frame[(frame["target_available"] >= 0.5) & (frame["h4_atr_for_risk"] > 0)].copy()
    usable["date"] = usable["timestamp"].dt.date
    days = sorted(usable["date"].unique())
    if len(days) < args.train_days_min + args.validation_days + args.test_days:
        raise RuntimeError("Not enough 5M days for the requested walk-forward geometry")
    folds: list[FoldSummary] = []
    trades: list[Trade] = []
    ranking_records: list[dict[str, Any]] = []
    balance = float(args.initial_capital)
    model_kind_used = "unknown"
    cursor = max(int(args.train_days_min), 1)
    fold_number = 0
    purge = pd.Timedelta(hours=max(float(args.purge_hours), 0.0))
    while cursor + args.validation_days + args.test_days <= len(days):
        validation_start_day = days[cursor]
        test_start_day = days[cursor + args.validation_days]
        test_end_day = days[cursor + args.validation_days + args.test_days - 1]
        validation_start = pd.Timestamp(validation_start_day, tz="UTC")
        test_start = pd.Timestamp(test_start_day, tz="UTC")
        test_end = pd.Timestamp(test_end_day, tz="UTC") + pd.Timedelta(days=1)
        train = usable[usable["timestamp"] < validation_start - purge].copy()
        validation = usable[
            (usable["timestamp"] >= validation_start) & (usable["timestamp"] < test_start - purge)
        ].copy()
        test = usable[
            (usable["timestamp"] >= test_start) & (usable["timestamp"] < test_end - purge)
        ].copy()
        if (
            len(train) < 500
            or len(validation) < 50
            or len(test) < 50
            or train["target_action"].nunique() < 2
        ):
            cursor += max(int(args.test_days), 1)
            continue
        fold_number += 1
        selected, ranking = selected_features(train, feature_columns, int(args.max_features))
        for rank_index, (feature, score) in enumerate(ranking, start=1):
            ranking_records.append(
                {
                    "feature": feature,
                    "score": float(score),
                    "rank": rank_index,
                    "selected": feature in selected,
                    "fold": fold_number,
                    "family": feature_family(feature),
                }
            )
        x_train = train[selected].to_numpy(dtype=np.float64)
        y_train = train["target_action"].astype(int).to_numpy()
        model, model_kind_used = train_pattern_model(
            args.model_kind, x_train, y_train, 4100 + fold_number
        )
        validation_probabilities = aligned_predict_proba(
            model, validation[selected].to_numpy(dtype=np.float64)
        )
        test_probabilities = aligned_predict_proba(model, test[selected].to_numpy(dtype=np.float64))
        params, validation_result = select_policy(
            frame, validation, validation_probabilities, args, fold_number
        )
        test_result, fold_trades = simulate_strategy(
            frame, test, test_probabilities, params, args, balance, fold_number
        )
        balance = float(test_result["final_balance"])
        trades.extend(fold_trades)
        folds.append(
            FoldSummary(
                fold=fold_number,
                train_start=str(train["timestamp"].min()),
                train_end=str(train["timestamp"].max()),
                validation_start=str(validation["timestamp"].min()),
                validation_end=str(validation["timestamp"].max()),
                test_start=str(test["timestamp"].min()),
                test_end=str(test["timestamp"].max()),
                train_rows=len(train),
                validation_rows=len(validation),
                test_rows=len(test),
                train_class_counts=class_counts(y_train),
                validation_class_counts=class_counts(validation["target_action"].astype(int)),
                test_class_counts=class_counts(test["target_action"].astype(int)),
                selected_features=selected,
                selected_params=params,
                validation_accuracy=simple_accuracy(
                    validation["target_action"].astype(int), validation_probabilities
                ),
                test_accuracy=simple_accuracy(
                    test["target_action"].astype(int), test_probabilities
                ),
                validation_result=validation_result,
                test_result=test_result,
            )
        )
        cursor += max(int(args.test_days), 1)
    if not folds:
        raise RuntimeError("No walk-forward folds could be formed")
    feature_rows = summarize_feature_selection(ranking_records)
    return folds, trades, feature_rows, model_kind_used


def summarize_feature_selection(records: Sequence[dict[str, Any]]) -> list[FeatureSelectionRow]:
    if not records:
        return []
    frame = pd.DataFrame(records)
    rows: list[FeatureSelectionRow] = []
    for feature, subset in frame.groupby("feature", sort=False):
        rows.append(
            FeatureSelectionRow(
                feature=str(feature),
                score=float(subset["score"].mean()),
                selected_count=int(subset["selected"].sum()),
                mean_rank=float(subset["rank"].mean()),
                family=str(subset["family"].iloc[0]),
            )
        )
    return sorted(
        rows, key=lambda row: (row.selected_count, row.score, -row.mean_rank), reverse=True
    )


def next_model_version(model_dir: Path) -> int:
    versions: list[int] = []
    if model_dir.exists():
        for path in model_dir.glob("v*_training.json"):
            stem = path.stem
            raw = stem.removeprefix("v").removesuffix("_training")
            if raw.isdigit():
                versions.append(int(raw))
    return (max(versions) + 1) if versions else 1


def save_final_model(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    feature_rows: Sequence[FeatureSelectionRow],
    folds: Sequence[FoldSummary],
    report: PivotReport,
    args: argparse.Namespace,
) -> tuple[str, str]:
    if args.save_model != "1":
        return "", ""
    usable = frame[(frame["target_available"] >= 0.5) & (frame["h4_atr_for_risk"] > 0)].copy()
    selected = [row.feature for row in feature_rows[: max(int(args.max_features), 1)]]
    if not selected:
        selected = list(feature_columns[: max(int(args.max_features), 1)])
    x_train = usable[selected].to_numpy(dtype=np.float64)
    y_train = usable["target_action"].astype(int).to_numpy()
    model, model_kind_used = train_pattern_model(args.model_kind, x_train, y_train, 99141)
    model_dir = Path(args.storage_root) / "models" / args.model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    version = next_model_version(model_dir)
    model_path = model_dir / f"v{version}_model.pkl"
    record_path = model_dir / f"v{version}_training.json"
    payload = {
        "model": model,
        "model_kind": model_kind_used,
        "feature_columns": selected,
        "action_names": ACTION_NAMES,
        "selected_params_from_last_fold": folds[-1].selected_params if folds else {},
    }
    model_path.write_bytes(pickle.dumps(payload))
    record = {
        "model_id": args.model_id,
        "version": version,
        "phase": "Phase141A",
        "role": "pivot_pattern_recognition",
        "symbol": args.symbol,
        "market_symbol": args.yahoo_symbol if args.source_mode == "yahoo" else args.symbol,
        "timeframe": "5M",
        "model_kind": model_kind_used,
        "training_rows": len(usable),
        "feature_columns": selected,
        "target_counts": class_counts(y_train),
        "latest_walk_forward_report": asdict(report),
        "production_status": "research_only_not_approved",
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(model_path), str(record_path)


def write_dataclass_csv(path: Path, rows: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_feature_csv(path: Path, rows: Sequence[FeatureSelectionRow]) -> None:
    write_dataclass_csv(path, rows)


def render_html(
    title: str,
    report: PivotReport,
    folds: Sequence[FoldSummary],
    features: Sequence[FeatureSelectionRow],
) -> str:
    fold_rows = "".join(
        "<tr>"
        f"<td>{fold.fold}</td>"
        f"<td>{html.escape(fold.test_start[:10])} → {html.escape(fold.test_end[:10])}</td>"
        f"<td>{fold.test_result['trades']}</td>"
        f"<td>{fold.test_result['buy_trades']}/{fold.test_result['sell_trades']}</td>"
        f"<td>{fold.test_result['net_profit']:+.2f}</td>"
        f"<td>{fold.test_result['profit_factor']:.3f}</td>"
        f"<td>{fold.test_result['win_rate']:.2%}</td>"
        f"<td>{html.escape(json.dumps(fold.selected_params, ensure_ascii=False))}</td>"
        "</tr>"
        for fold in folds
    )
    feature_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row.feature)}</td>"
        f"<td>{html.escape(row.family)}</td>"
        f"<td>{row.selected_count}</td>"
        f"<td>{row.mean_rank:.1f}</td>"
        f"<td>{row.score:.4f}</td>"
        "</tr>"
        for row in features[:40]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Segoe UI,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1500px; margin:0 auto; padding:24px; }}
.hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:12px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:7px; vertical-align:top; }} th {{ color:#bae6fd; }}
.danger {{ border-right:4px solid #ef4444; background:#ef44441a; border-radius:10px; padding:10px; margin-top:12px; }}
.info {{ border-right:4px solid #38bdf8; background:#38bdf81a; border-radius:10px; padding:10px; margin-top:12px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
</style>
</head>
<body><main>
<section class="hero">
<h1>{html.escape(title)}</h1>
<p>Phase141A مدل Pattern Recognition برای تشخیص ناحیه قله/کف طلاست. این گزارش research-only است و مجوز paper/live نیست.</p>
<div class="grid">
  <div class="metric"><span>Final balance</span><strong>${report.final_balance:.2f}</strong></div>
  <div class="metric"><span>Return</span><strong>{report.return_percent:.2%}</strong></div>
  <div class="metric"><span>Profit factor</span><strong>{report.profit_factor:.3f}</strong></div>
  <div class="metric"><span>Trades</span><strong>{report.trades}</strong></div>
</div>
<div class="danger"><strong>Production status:</strong> {html.escape(report.production_status)}</div>
<div class="info"><strong>Data:</strong> {html.escape(report.data_note)}</div>
</section>
<section class="card"><h2>Summary</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Walk-forward folds</h2><table><thead><tr><th>fold</th><th>test window</th><th>trades</th><th>BUY/SELL</th><th>net</th><th>PF</th><th>win</th><th>params</th></tr></thead><tbody>{fold_rows}</tbody></table></section>
<section class="card"><h2>Top selected features</h2><table><thead><tr><th>feature</th><th>family</th><th>selected count</th><th>mean rank</th><th>score</th></tr></thead><tbody>{feature_rows}</tbody></table></section>
</main></body></html>"""


def make_report(
    args: argparse.Namespace,
    daily: pd.DataFrame,
    h4: pd.DataFrame,
    five: pd.DataFrame,
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    target_counts: dict[str, int],
    folds: Sequence[FoldSummary],
    trades: Sequence[Trade],
    model_path: str,
    record_path: str,
    data_note: str,
    output_dir: Path,
) -> PivotReport:
    aggregate = aggregate_trades(trades, args.initial_capital)
    return PivotReport(
        source_mode=args.source_mode,
        market_symbol=args.yahoo_symbol if args.source_mode == "yahoo" else args.symbol,
        data_note=data_note,
        daily_rows=len(daily),
        h4_rows=len(h4),
        five_rows=len(five),
        feature_rows=len(frame),
        feature_columns_total=len(feature_columns),
        selected_feature_count=max(0, int(args.max_features)),
        target_counts=target_counts,
        folds=len(folds),
        initial_balance=float(args.initial_capital),
        final_balance=float(aggregate["final_balance"]),
        net_profit=float(aggregate["net_profit"]),
        return_percent=float(aggregate["return_percent"]),
        trades=int(aggregate["trades"]),
        buy_trades=int(aggregate["buy_trades"]),
        sell_trades=int(aggregate["sell_trades"]),
        wins=int(aggregate["wins"]),
        losses=int(aggregate["losses"]),
        win_rate=float(aggregate["win_rate"]),
        profit_factor=float(aggregate["profit_factor"]),
        max_drawdown_cash=float(aggregate["max_drawdown_cash"]),
        positive_folds=sum(1 for fold in folds if fold.test_result["net_profit"] > 0),
        negative_folds=sum(1 for fold in folds if fold.test_result["net_profit"] < 0),
        production_status="BLOCKED — research pattern-recognition model only",
        output_json=str(output_dir / "latest.json"),
        output_html=str(output_dir / "latest.html"),
        output_folds_csv=str(output_dir / "latest_folds.csv"),
        output_trades_csv=str(output_dir / "latest_trades.csv"),
        output_features_csv=str(output_dir / "latest_features.csv"),
        model_path=model_path,
        training_record_path=record_path,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE141A PIVOT / TOP-BOTTOM PATTERN RECOGNITION")
        print("=" * 74)
        print(f"  source      : {args.source_mode}")
        print(f"  yahoo symbol: {args.yahoo_symbol}")
        daily, h4, five, data_note = load_market_data(args)
        if args.save_data == "1":
            daily.to_csv(output_dir / "source_daily_1d.csv", index=False)
            h4.to_csv(output_dir / "source_4h.csv", index=False)
            five.to_csv(output_dir / "source_5m.csv", index=False)
        print(f"  rows        : daily={len(daily):,} h4={len(h4):,} 5m={len(five):,}")
        frame, feature_columns = build_feature_frame(daily, h4, five)
        config = PivotLabelConfig(
            lookahead_bars=max(int(args.lookahead_bars), 1),
            pivot_move_atr=max(float(args.pivot_move_atr), 0.01),
            pivot_zone_atr=max(float(args.pivot_zone_atr), 0.01),
            recent_window_bars=max(int(args.recent_window_bars), 1),
            min_direction_edge=max(float(args.min_direction_edge), 1.0),
        )
        frame = label_pivot_targets(frame, config)
        target_counts = class_counts(
            frame.loc[frame["target_available"] >= 0.5, "target_action"].astype(int)
        )
        print(f"  features    : {len(feature_columns):,}")
        print(f"  targets     : {target_counts}")
        folds, trades, feature_rows, model_kind_used = walk_forward(frame, feature_columns, args)
        temporary_report = make_report(
            args,
            daily,
            h4,
            five,
            frame,
            feature_columns,
            target_counts,
            folds,
            trades,
            "",
            "",
            data_note,
            output_dir,
        )
        model_path, record_path = save_final_model(
            frame, feature_columns, feature_rows, folds, temporary_report, args
        )
        report = make_report(
            args,
            daily,
            h4,
            five,
            frame,
            feature_columns,
            target_counts,
            folds,
            trades,
            model_path,
            record_path,
            data_note,
            output_dir,
        )
        if record_path:
            record_file = Path(record_path)
            record = json.loads(record_file.read_text(encoding="utf-8"))
            record["latest_walk_forward_report"] = asdict(report)
            record_file.write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        write_dataclass_csv(Path(report.output_folds_csv), folds)
        write_dataclass_csv(Path(report.output_trades_csv), trades)
        write_feature_csv(Path(report.output_features_csv), feature_rows)
        Path(report.output_html).write_text(
            render_html(args.report_title, report, folds, feature_rows), encoding="utf-8"
        )
        payload = {
            "args": vars(args),
            "label_config": asdict(config),
            "model_kind_used": model_kind_used,
            "report": asdict(report),
            "folds": [asdict(fold) for fold in folds],
            "top_features": [asdict(row) for row in feature_rows[:80]],
            "trades_preview": [asdict(trade) for trade in trades[:250]],
            "data": {
                "daily_first": str(daily["timestamp"].min()),
                "daily_last": str(daily["timestamp"].max()),
                "h4_first": str(h4["timestamp"].min()),
                "h4_last": str(h4["timestamp"].max()),
                "five_first": str(five["timestamp"].min()),
                "five_last": str(five["timestamp"].max()),
            },
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "folds_csv": report.output_folds_csv,
                "trades_csv": report.output_trades_csv,
                "features_csv": report.output_features_csv,
                "model": report.model_path,
                "training_record": report.training_record_path,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  model kind  : {model_kind_used}")
        print(f"  folds       : {report.folds:,}")
        print(f"  trades      : {report.trades:,}")
        print(f"  final       : ${report.final_balance:.2f}")
        print(f"  return      : {report.return_percent:.2%}")
        print(f"  PF          : {report.profit_factor:.3f}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
