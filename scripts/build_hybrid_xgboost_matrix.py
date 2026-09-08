"""Build an XGBoost/LightGBM-ready hybrid matrix from model outputs.

Phase 123 implements the operator's requested direction: use model
outputs as features for the final tree model. The matrix can include:

* BUY/SELL booster specialist probabilities;
* optional multiclass booster probabilities;
* optional WaveNet trend_signal probabilities;
* 1D and 4H range model forecasts converted to actionable room features.

No model is trained here. This script produces the supervised matrix that
can be fed to XGBoost/LightGBM in the next step without recomputing every
base model output.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import bisect
import json
import math
import pickle
import sys
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd

from ShadBotTrader.application.services.dual_model_service import DualModelService
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.data_windowing import (
    input_scale_range_for_model,
    minmax_scale_window,
)
from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord
from ShadBotTrader.infrastructure.ai.model_roles import trend_signal_model_role
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
from ShadBotTrader.infrastructure.ai.tabular_window_summary import SUMMARY_MODES, summarise_windows
from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _deserialize_model
from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2
CLASS_NAMES = {CLASS_SELL: "sell", CLASS_HOLD: "hold", CLASS_BUY: "buy"}
SCOPES = ("auto", "holdout", "last-fold", "all")


@dataclass(frozen=True)
class RangeFeatureConfig:
    label: str
    timeframe: str
    model_id: str
    version: int
    required: bool


@dataclass(frozen=True)
class HybridMatrixReport:
    rows: int
    columns: int
    output_path: str
    latest_path: str
    selected_scope: str
    label_counts: dict[str, int]
    warnings: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build hybrid model-output matrix for XGBoost/LightGBM head.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument("--scope", choices=SCOPES, default="holdout")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--val-size", type=int, default=2000)
    parser.add_argument("--max-windows", type=int, default=8000, help="0 = every selected window")
    parser.add_argument("--summary-mode", choices=SUMMARY_MODES, default="basic")
    parser.add_argument("--booster", default="lightgbm")
    parser.add_argument("--include-tabular-summary", choices=("0", "1"), default="0")
    parser.add_argument("--include-multiclass-booster", choices=("0", "1"), default="1")
    parser.add_argument("--include-specialists", choices=("0", "1"), default="1")
    parser.add_argument("--include-wavenet", choices=("0", "1"), default="1")
    parser.add_argument("--require-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--include-range", choices=("0", "1"), default="1")
    parser.add_argument("--require-range", choices=("0", "1"), default="1")
    parser.add_argument("--buy-model-id", default="")
    parser.add_argument("--sell-model-id", default="")
    parser.add_argument("--multiclass-model-id", default="")
    parser.add_argument("--wavenet-model-id", default="gold_trend_signal_5m")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--buy-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--sell-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--multiclass-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--wavenet-model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--range-1d-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--range-4h-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-name", default="hybrid_xgboost_matrix_v1")
    parser.add_argument("--output-dir", default="run_logs/hybrid_xgboost_matrix")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def timeframe_delta(label: str) -> timedelta:
    tf = Timeframe(label)
    if tf.unit.value == "minute":
        return timedelta(minutes=tf.amount)
    if tf.unit.value == "hour":
        return timedelta(hours=tf.amount)
    if tf.unit.value == "day":
        return timedelta(days=tf.amount)
    raise ValidationError(f"Unsupported timeframe: {label}")


def latest_closed_index(end_times: Sequence[Any], timestamp: Any) -> int | None:
    index = bisect.bisect_right(end_times, timestamp) - 1
    return index if index >= 0 else None


def choose_scope(scope: str, train_ratio: float) -> str:
    if scope != "auto":
        return scope
    return "holdout" if 0 < train_ratio < 100 else "last-fold"


def select_evenly(values: Sequence[int], max_count: int) -> list[int]:
    if max_count <= 0 or len(values) <= max_count:
        return list(values)
    step = max(1, len(values) // max_count)
    return list(values[::step])[:max_count]


def class_counts(labels: Sequence[int]) -> dict[str, int]:
    return {name: sum(1 for label in labels if label == cls) for cls, name in CLASS_NAMES.items()}


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    if resolved.is_alias:
        print(f"  [i] {resolved.note}")
    return sorted(
        store.query(Symbol(resolved.resolved), Timeframe(timeframe)),
        key=lambda c: c.open_time.value,
    )


def prepare_trend_dataset(args: argparse.Namespace, candles: Sequence[Any]):
    role = trend_signal_model_role(
        timeframe=args.timeframe,
        threshold=args.atr_mult,
        window_size=args.window,
        label_horizon=args.label_horizon,
    )
    service = DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )
    return role, service.prepare(candles, Symbol(args.symbol), Timeframe(args.timeframe), role)


def resolved_val_size(rows: int, requested: int, window_size: int) -> int:
    candidate = requested if requested > 0 else max(4, min(2000, rows // 10))
    min_train = max(8, min(rows // 4, 20 * window_size))
    return max(4, min(candidate, rows - min_train - window_size - 4))


def last_fold_positions(dataset: Any, rows: int, requested_val: int, max_folds: int) -> list[int]:
    if dataset.sample_ends is None:
        raise RuntimeError("trend_signal dataset did not expose sample_ends")
    resolved = resolved_val_size(rows, requested_val, dataset.role.window_size)
    plan = expanding_split(
        total_length=rows,
        val_size=resolved,
        step=resolved,
        min_train_size=max(8, min(rows // 4, 20 * dataset.role.window_size)),
        purge_gap=max(dataset.role.window_size - 1, 0),
        sample_end_indices=dataset.sample_ends,
        label_end_indices=dataset.sample_label_ends,
        window_size=dataset.role.window_size,
    )
    folds = list(plan.folds)
    if max_folds > 0:
        folds = folds[-max_folds:]
    if not folds:
        return []
    fold = folds[-1]
    return list(range(fold.val_start, fold.val_end))


def selected_positions(args: argparse.Namespace, dataset: Any, candles_count: int) -> list[int]:
    if dataset.sample_ends is None:
        raise RuntimeError("trend_signal dataset did not expose sample_ends")
    total = len(dataset.sample_ends)
    scope = choose_scope(args.scope, args.train_ratio)
    if scope == "all":
        return select_evenly(list(range(total)), args.max_windows)
    if scope == "last-fold":
        return select_evenly(
            last_fold_positions(dataset, total, args.val_size, args.folds), args.max_windows
        )
    if scope == "holdout":
        cutoff = int(candles_count * args.train_ratio / 100.0)
        rows = [
            index
            for index, sample_end in enumerate(dataset.sample_ends)
            if int(sample_end) + int(dataset.dropped_warmup) >= cutoff
        ]
        return select_evenly(rows, args.max_windows)
    raise ValidationError(f"Unknown scope: {scope}")


def default_booster_id(kind: str, booster: str, summary_mode: str, timeframe: str) -> str:
    suffix = kind if kind != "multiclass" else "trend_signal"
    return f"gold_{suffix}_{booster}_{summary_mode}_{timeframe.lower()}"


def latest_or_requested(catalogue: ModelCatalogue, model_id: str, requested: int) -> int:
    if requested > 0:
        return requested
    latest = catalogue.latest_version(model_id)
    if latest < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    return latest


def load_pickle_model(storage_root: Path, model_id: str, version: int) -> Any:
    artifact = FilesystemArtifactStore(storage_root).load(ModelId(model_id), ModelVersion(version))
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{version}")
    try:
        return pickle.loads(artifact.payload)["model"]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not load booster artifact because an optional package is missing. "
            "Install: pip install -r requirements-boosters.txt"
        ) from exc


def aligned_predict_proba(model: Any, x_values: np.ndarray, output_units: int) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    if raw.ndim == 1:
        raw = np.column_stack([1.0 - raw, raw])
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    aligned = np.zeros((len(raw), output_units), dtype=np.float64)
    for raw_col, cls in enumerate(classes):
        if 0 <= cls < output_units:
            aligned[:, cls] = raw[:, raw_col]
    row_sums = aligned.sum(axis=1)
    missing = row_sums <= 0
    if np.any(missing):
        aligned[missing, :] = 1.0 / output_units
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def add_booster_features(
    frame: pd.DataFrame,
    args: argparse.Namespace,
    summary_values: np.ndarray,
    warnings: list[str],
) -> None:
    storage_root = Path(args.storage_root)
    catalogue = ModelCatalogue(storage_root)
    if args.include_specialists == "1":
        buy_id = args.buy_model_id or default_booster_id(
            "buy", args.booster, args.summary_mode, args.timeframe
        )
        sell_id = args.sell_model_id or default_booster_id(
            "sell", args.booster, args.summary_mode, args.timeframe
        )
        try:
            buy_version = latest_or_requested(catalogue, buy_id, args.buy_model_version)
            sell_version = latest_or_requested(catalogue, sell_id, args.sell_model_version)
            buy_model = load_pickle_model(storage_root, buy_id, buy_version)
            sell_model = load_pickle_model(storage_root, sell_id, sell_version)
            buy_probs = aligned_predict_proba(buy_model, summary_values, 2)[:, 1]
            sell_probs = aligned_predict_proba(sell_model, summary_values, 2)[:, 1]
            frame["buy_specialist_prob"] = buy_probs
            frame["sell_specialist_prob"] = sell_probs
            frame["specialist_buy_minus_sell"] = buy_probs - sell_probs
            frame["specialist_sell_minus_buy"] = sell_probs - buy_probs
            frame["specialist_conflict"] = np.minimum(buy_probs, sell_probs)
            frame["specialist_max_prob"] = np.maximum(buy_probs, sell_probs)
            print(f"  specialists : {buy_id} v{buy_version} + {sell_id} v{sell_version}")
        except Exception as error:
            raise RuntimeError(f"Could not add BUY/SELL specialist features: {error}") from error

    if args.include_multiclass_booster == "1":
        model_id = args.multiclass_model_id or default_booster_id(
            "multiclass", args.booster, args.summary_mode, args.timeframe
        )
        try:
            version = latest_or_requested(catalogue, model_id, args.multiclass_model_version)
            model = load_pickle_model(storage_root, model_id, version)
            probs = aligned_predict_proba(model, summary_values, 3)
            frame["booster_sell_prob"] = probs[:, 0]
            frame["booster_hold_prob"] = probs[:, 1]
            frame["booster_buy_prob"] = probs[:, 2]
            frame["booster_action_margin"] = np.abs(probs[:, 2] - probs[:, 0])
            print(f"  multiclass  : {model_id} v{version}")
        except Exception as error:
            warnings.append(f"multiclass booster skipped: {type(error).__name__}: {error}")


def add_wavenet_features(
    frame: pd.DataFrame,
    args: argparse.Namespace,
    dataset: Any,
    positions: Sequence[int],
    warnings: list[str],
) -> None:
    if args.include_wavenet != "1":
        return
    storage_root = Path(args.storage_root)
    catalogue = ModelCatalogue(storage_root)
    required = args.require_wavenet == "1"
    try:
        version = latest_or_requested(catalogue, args.wavenet_model_id, args.wavenet_model_version)
        record = catalogue.read(args.wavenet_model_id, version)
        artifact = FilesystemArtifactStore(storage_root).load(
            ModelId(args.wavenet_model_id), ModelVersion(version)
        )
        if record is None or artifact is None:
            raise RuntimeError("record or artifact missing")
        model = _deserialize_model(artifact.payload)
        expected = getattr(model, "input_shape", None)
        if expected is not None and len(expected) == 3:
            if expected[1] is not None and int(expected[1]) != args.window:
                raise RuntimeError(f"WaveNet expects window={expected[1]}, requested {args.window}")
            if expected[2] is not None and int(expected[2]) != dataset.feature_count:
                raise RuntimeError(
                    f"WaveNet expects {expected[2]} features, matrix has {dataset.feature_count}"
                )
        scale_range = input_scale_range_for_model(args.wavenet_model_id, record.input_scale_range)
        rows: list[list[float]] = []
        for position in positions:
            sample_end = dataset.sample_ends[position]
            window = dataset.series[sample_end - args.window + 1 : sample_end + 1]
            scaled = minmax_scale_window(
                [row[: dataset.feature_count] for row in window], scale_range
            )
            rows.append(scaled)
        x = np.asarray(rows, dtype=np.float32)
        raw = model.predict(x, verbose=0)
        probs = np.asarray(raw, dtype=np.float64)
        if probs.ndim == 3:
            probs = probs[:, -1, :]
        if probs.ndim != 2 or probs.shape[1] != 3:
            raise RuntimeError(f"Unexpected WaveNet output shape {probs.shape}")
        row_sums = probs.sum(axis=1)
        probs = probs / row_sums[:, None]
        frame["wavenet_sell_prob"] = probs[:, 0]
        frame["wavenet_hold_prob"] = probs[:, 1]
        frame["wavenet_buy_prob"] = probs[:, 2]
        frame["wavenet_action_margin"] = np.abs(probs[:, 2] - probs[:, 0])
        print(f"  wavenet     : {args.wavenet_model_id} v{version}")
    except Exception as error:
        message = f"wavenet skipped: {type(error).__name__}: {error}"
        if required:
            raise RuntimeError(message) from error
        warnings.append(message)


class RangeFeatureProvider:
    def __init__(self, storage_root: Path, symbol: str, config: RangeFeatureConfig) -> None:
        self.storage_root = storage_root
        self.symbol = symbol
        self.config = config
        self.record: ModelRecord | None = None
        self.artifact: Any = None
        self.candles: list[Any] = []
        self.matrix: Any = None
        self.original_to_matrix: dict[int, int] = {}
        self.end_times: list[Any] = []
        self.cache: dict[int, dict[str, float]] = {}
        self.warning = ""
        self._load()

    @property
    def available(self) -> bool:
        return self.record is not None and self.artifact is not None and self.matrix is not None

    def _load(self) -> None:
        catalogue = ModelCatalogue(self.storage_root)
        version = latest_or_requested(catalogue, self.config.model_id, self.config.version)
        record = catalogue.read(self.config.model_id, version)
        if record is None:
            raise RuntimeError(f"No record for {self.config.model_id} v{version}")
        artifact = FilesystemArtifactStore(self.storage_root).load(
            ModelId(record.model_id), ModelVersion(record.version)
        )
        if artifact is None:
            raise RuntimeError(f"No artifact for {record.model_id} v{record.version}")
        candles = load_candles(self.storage_root, self.symbol, self.config.timeframe)
        matrix = build_feature_matrix(
            candles=candles,
            symbol=Symbol(self.symbol),
            timeframe=Timeframe(self.config.timeframe),
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
            include_features=True,
            causal_only=True,
            model_role="range",
        )
        self.record = record
        self.artifact = artifact
        self.candles = list(candles)
        self.matrix = matrix
        self.original_to_matrix = {
            source: index for index, source in enumerate(matrix.source_index)
        }
        delta = timeframe_delta(self.config.timeframe)
        self.end_times = [candle.open_time.value + delta for candle in self.candles]

    def forecast_for_signal(self, timestamp: Any, reference_close: float) -> dict[str, float]:
        if not self.available or self.record is None:
            return {f"range_{self.config.label}_available": 0.0}
        original_index = latest_closed_index(self.end_times, timestamp)
        if original_index is None:
            return {f"range_{self.config.label}_available": 0.0}
        if original_index not in self.cache:
            self.cache[original_index] = self._forecast_original_index(original_index)
        base = dict(self.cache[original_index])
        high = base.get(f"range_{self.config.label}_high_price", 0.0)
        low = base.get(f"range_{self.config.label}_low_price", 0.0)
        base[f"range_{self.config.label}_up_room"] = high - reference_close
        base[f"range_{self.config.label}_down_room"] = reference_close - low
        base[f"range_{self.config.label}_up_room_pct"] = (high - reference_close) / reference_close
        base[f"range_{self.config.label}_down_room_pct"] = (reference_close - low) / reference_close
        return base

    def _forecast_original_index(self, original_index: int) -> dict[str, float]:
        assert self.record is not None
        matrix_index = self.original_to_matrix.get(original_index)
        prefix = f"range_{self.config.label}"
        if matrix_index is None or matrix_index < self.record.window_size - 1:
            return {f"{prefix}_available": 0.0}
        window_rows = self.matrix.rows[
            matrix_index - self.record.window_size + 1 : matrix_index + 1
        ]
        candle = self.candles[original_index]
        atr_reference = 0.0
        if (self.record.target_units or "pct") == "atr":
            atr = atr_from_candles(self.candles[: original_index + 1], period=14)
            atr_reference = float(atr or 0.0)
        forecast = RangePredictor(
            horizon=max(int(self.record.horizon or 1), 1),
            timeframe=self.record.timeframe,
            target_units=self.record.target_units or "pct",
        ).forecast(
            self.artifact,
            window_rows,
            reference_close=float(candle.close.amount),
            generated_at=str(candle.open_time.value),
            atr_reference=atr_reference if atr_reference else None,
        )
        high = float(forecast.predicted_high)
        low = float(forecast.predicted_low)
        reference = float(forecast.reference_close)
        return {
            f"{prefix}_available": 1.0,
            f"{prefix}_high_price": high,
            f"{prefix}_low_price": low,
            f"{prefix}_width": high - low,
            f"{prefix}_high_offset": float(forecast.high_offset),
            f"{prefix}_low_offset": float(forecast.low_offset),
            f"{prefix}_width_pct": (high - low) / reference if reference else 0.0,
            f"{prefix}_atr_reference": float(getattr(forecast, "atr_reference", 0.0) or 0.0),
        }


def add_range_features(
    frame: pd.DataFrame,
    args: argparse.Namespace,
    signal_candles: Sequence[Any],
    original_indices: Sequence[int],
    warnings: list[str],
) -> None:
    if args.include_range != "1":
        return
    storage_root = Path(args.storage_root)
    configs = [
        RangeFeatureConfig(
            "1d",
            "1D",
            args.range_1d_model_id,
            args.range_1d_version,
            args.require_range == "1",
        ),
        RangeFeatureConfig(
            "4h",
            "4H",
            args.range_4h_model_id,
            args.range_4h_version,
            args.require_range == "1",
        ),
    ]
    for config in configs:
        try:
            provider = RangeFeatureProvider(storage_root, args.symbol, config)
            rows = []
            for original_index in original_indices:
                candle = signal_candles[original_index]
                rows.append(
                    provider.forecast_for_signal(
                        candle.open_time.value,
                        float(candle.close.amount),
                    )
                )
            range_frame = pd.DataFrame(rows).fillna(0.0)
            for column in range_frame.columns:
                frame[column] = range_frame[column].to_numpy(dtype=float)
            print(f"  range {config.label:<2}  : {config.model_id}")
        except Exception as error:
            message = f"range {config.label} skipped: {type(error).__name__}: {error}"
            if config.required:
                raise RuntimeError(message) from error
            warnings.append(message)


def entropy3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    probs = np.vstack([a, b, c]).T.astype(np.float64)
    probs = np.clip(probs, 1e-12, 1.0)
    return -np.sum(probs * np.log(probs), axis=1) / math.log(3.0)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    warnings: list[str] = []
    try:
        rule("HYBRID XGBOOST MATRIX")
        print(f"  symbol      : {args.symbol}")
        print(f"  timeframe   : {args.timeframe}")
        print(f"  scope       : {args.scope}")
        print(f"  summary     : {args.summary_mode}")
        print(f"  range models: {args.range_1d_model_id}, {args.range_4h_model_id}")

        storage_root = Path(args.storage_root)
        signal_candles = load_candles(storage_root, args.symbol, args.timeframe)
        role, dataset = prepare_trend_dataset(args, signal_candles)
        positions = selected_positions(args, dataset, len(signal_candles))
        if not positions:
            raise RuntimeError("No windows selected for hybrid matrix")
        sample_ends = [dataset.sample_ends[index] for index in positions]
        original_indices = [
            int(dataset.dropped_warmup) + int(sample_end) for sample_end in sample_ends
        ]
        labels = [
            int(round(dataset.series[sample_end][dataset.target_columns[0]]))
            for sample_end in sample_ends
        ]
        timestamps = [str(signal_candles[index].open_time.value) for index in original_indices]
        closes = [float(signal_candles[index].close.amount) for index in original_indices]

        rule("BASE ROWS")
        print(f"  rows        : {len(positions):,}")
        print(f"  labels      : {class_counts(labels)}")
        summary = summarise_windows(
            series=dataset.series,
            feature_count=dataset.feature_count,
            column_names=dataset.column_names,
            sample_ends=sample_ends,
            window_size=role.window_size,
            mode=args.summary_mode,
        )
        print(f"  summary cols: {summary.columns:,}")

        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "source_index": original_indices,
                "sample_end": sample_ends,
                "label": labels,
                "close": closes,
            }
        )
        if args.include_tabular_summary == "1":
            summary_frame = pd.DataFrame(summary.values, columns=summary.feature_names)
            frame = pd.concat([frame, summary_frame], axis=1)

        rule("MODEL OUTPUT FEATURES")
        add_booster_features(frame, args, summary.values, warnings)
        add_wavenet_features(frame, args, dataset, positions, warnings)
        add_range_features(frame, args, signal_candles, original_indices, warnings)

        if {
            "booster_sell_prob",
            "booster_hold_prob",
            "booster_buy_prob",
        }.issubset(frame.columns):
            frame["booster_entropy"] = entropy3(
                frame["booster_sell_prob"].to_numpy(),
                frame["booster_hold_prob"].to_numpy(),
                frame["booster_buy_prob"].to_numpy(),
            )
        if {
            "wavenet_sell_prob",
            "wavenet_hold_prob",
            "wavenet_buy_prob",
        }.issubset(frame.columns):
            frame["wavenet_entropy"] = entropy3(
                frame["wavenet_sell_prob"].to_numpy(),
                frame["wavenet_hold_prob"].to_numpy(),
                frame["wavenet_buy_prob"].to_numpy(),
            )

        out_dir = storage_root / "processed" / args.symbol / args.timeframe
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{args.output_name}.parquet"
        latest_path = out_dir / "hybrid_xgboost_matrix_latest.parquet"
        frame.to_parquet(output_path, index=False)
        frame.to_parquet(latest_path, index=False)

        report = HybridMatrixReport(
            rows=len(frame),
            columns=len(frame.columns),
            output_path=str(output_path),
            latest_path=str(latest_path),
            selected_scope=choose_scope(args.scope, args.train_ratio),
            label_counts=class_counts(labels),
            warnings=warnings,
        )
        log_dir = Path(args.output_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        report_path = log_dir / "latest.json"
        report_path.write_text(
            json.dumps(
                {"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        rule("DONE")
        print(f"  matrix : {output_path}")
        print(f"  latest : {latest_path}")
        print(f"  rows   : {len(frame):,}")
        print(f"  cols   : {len(frame.columns):,}")
        print(f"  report : {report_path}")
        for warning in warnings:
            print(f"  [!] {warning}")
        print(f"  elapsed: {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
