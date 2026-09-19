"""Phase145A: build a 3D feature-sequence tensor for Conv1D/WaveNet.

Stored tensor layout:

    X = [samples, window_size, features]

Keras Conv1D/WaveNet batch layout:

    batch_X = [batch, window_size, features]

This is Option A from the owner discussion: 5M, closed 4H, closed 1D and
session/context features are concatenated on the feature/channel axis instead
of being expanded into a 4D interaction image.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import html
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import numpy as np
import pandas as pd
from build_pivot_pattern_image_tensor import axis_normalize
from numpy.lib.stride_tricks import sliding_window_view
from train_pivot_pattern_recognition import (
    PivotLabelConfig,
    build_feature_frame,
    class_counts,
    label_pivot_targets,
    load_market_data,
    storage_timeframe_path,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_tensor")
DTYPE_CHOICES = ("float16", "float32")


@dataclass(frozen=True)
class SequenceTensorReport:
    source_mode: str
    symbol: str
    data_note: str
    daily_rows: int
    h4_rows: int
    five_rows: int
    flat_rows: int
    samples: int
    window_size: int
    features: int
    stored_x_shape: list[int]
    keras_batch_shape: str
    dtype: str
    estimated_uncompressed_mb: float
    sample_stride: int
    axis_normalization: str
    feature_clip: float
    nonfinite_feature_values: int
    generated_feature_count: int
    source_5m_feature_count: int
    source_5m_feature_path: str
    source_5m_total_columns: int
    source_5m_numeric_candidate_count: int
    target_counts: dict[str, int]
    feature_names_preview: list[str]
    output_tensor: str
    output_meta: str
    output_flat: str
    output_json: str
    output_html: str


@dataclass(frozen=True)
class SourceFeatureRead:
    frame: pd.DataFrame | None
    path: str
    total_columns: int
    numeric_candidate_count: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Phase145A sequence tensor [samples, window, features].",
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
    parser.add_argument("--lookahead-bars", type=int, default=48)
    parser.add_argument("--pivot-move-atr", type=float, default=0.75)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.35)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--min-direction-edge", type=float, default=1.10)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all rolling samples")
    parser.add_argument("--include-source-5m-features", choices=("0", "1"), default="1")
    parser.add_argument(
        "--source-5m-feature-path",
        nargs="?",
        const="",
        default="",
        help=(
            "Optional explicit parquet/csv containing timestamp/open_time plus extra 5M "
            "numeric features. Empty storage mode auto-probes hybrid telemetry/matrix files "
            "before falling back to the OHLCV storage parquet. The value is optional so "
            "PowerShell commands that drop an empty string still auto-probe safely."
        ),
    )
    parser.add_argument(
        "--max-features", type=int, default=0, help="0 = keep every selected feature"
    )
    parser.add_argument("--dtype", choices=DTYPE_CHOICES, default="float16")
    parser.add_argument(
        "--axis-normalization", choices=("robust", "standard", "none"), default="robust"
    )
    parser.add_argument("--feature-clip", type=float, default=8.0)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--max-tensor-mb", type=float, default=8192.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-name", default="pivot_pattern_sequence_tensor_latest")
    return parser.parse_args(argv)


def normalize_timestamp_column(frame: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "open_time": "timestamp",
        "time": "timestamp",
        "datetime": "timestamp",
        "date": "timestamp",
    }
    result = frame.rename(
        columns={key: value for key, value in aliases.items() if key in frame.columns}
    ).copy()
    if "timestamp" not in result.columns:
        raise RuntimeError("source 5M feature frame must include timestamp/open_time")
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    return result.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates("timestamp")


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)


def source_5m_candidate_paths(args: argparse.Namespace) -> list[Path]:
    explicit = str(getattr(args, "source_5m_feature_path", "") or "").strip()
    if explicit:
        return [Path(explicit)]
    paths: list[Path] = []
    if args.source_mode == "storage":
        directory = Path(args.storage_root) / "processed" / args.symbol / args.five_timeframe.upper()
        priority_names = (
            "hybrid_telemetry_flat_latest.parquet",
            "hybrid_xgboost_matrix_latest.parquet",
            "hybrid_xgboost_matrix_all_5m.parquet",
        )
        for name in priority_names:
            candidate = directory / name
            if candidate.exists():
                paths.append(candidate)
        for pattern in ("hybrid_*flat*.parquet", "hybrid_*matrix*.parquet"):
            for candidate in sorted(directory.glob(pattern)):
                if candidate not in paths:
                    paths.append(candidate)
        try:
            ohlcv_path = storage_timeframe_path(
                Path(args.storage_root), args.symbol, args.five_timeframe
            )
            if ohlcv_path not in paths:
                paths.append(ohlcv_path)
        except RuntimeError:
            pass
    elif args.source_mode == "files" and args.five_path:
        paths.append(Path(args.five_path))
    return paths


def read_source_5m_frame(args: argparse.Namespace) -> SourceFeatureRead:
    if args.include_source_5m_features != "1":
        return SourceFeatureRead(None, "", 0, 0)
    first_existing_without_candidates: SourceFeatureRead | None = None
    for path in source_5m_candidate_paths(args):
        if not path.exists():
            if str(getattr(args, "source_5m_feature_path", "") or "").strip():
                raise RuntimeError(f"source 5M feature path does not exist: {path}")
            continue
        frame = normalize_timestamp_column(read_table(path))
        candidate_count = len(source_feature_columns(frame))
        read = SourceFeatureRead(frame, str(path), len(frame.columns), candidate_count)
        if candidate_count > 0:
            return read
        if first_existing_without_candidates is None:
            first_existing_without_candidates = read
    return first_existing_without_candidates or SourceFeatureRead(None, "", 0, 0)


def source_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked_exact = {
        "timestamp",
        "open_time",
        "time",
        "date",
        "datetime",
        "symbol",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "tick_volume",
        "real_volume",
        "spread",
        "label",
        "source_index",
        "tensor_index",
        "sample_index",
        "row_id",
        "row_index",
    }
    blocked_prefixes = (
        "target_",
        "future_",
        "candidate_",
        "prediction_",
        "pred_",
        "prob_",
    )
    columns: list[str] = []
    for column in frame.columns:
        lower = str(column).lower()
        if lower in blocked_exact or lower.startswith(blocked_prefixes):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(str(column))
    return columns


def merge_source_features(
    frame: pd.DataFrame, source: pd.DataFrame | None
) -> tuple[pd.DataFrame, list[str]]:
    if source is None:
        return frame, []
    columns = source_feature_columns(source)
    if not columns:
        return frame, []
    renamed = {column: f"src5m_{column}" for column in columns}
    source_features = source[["timestamp", *columns]].rename(columns=renamed).copy()
    merged = pd.merge(
        frame,
        source_features,
        on="timestamp",
        how="left",
        validate="one_to_one",
    )
    source_columns = list(renamed.values())
    merged[source_columns] = merged[source_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return merged, source_columns


def classify_feature_group(name: str) -> str:
    if name.startswith("src5m_"):
        return "source_5m"
    if name.startswith("m5_"):
        return "generated_5m"
    if name.startswith("h4_"):
        return "closed_4h"
    if name.startswith("d1_"):
        return "closed_1d"
    if name.startswith("session_"):
        return "session"
    return "other"


def target_buy_r(frame: pd.DataFrame) -> np.ndarray:
    return np.clip(
        frame["future_up_r"].to_numpy(dtype=np.float32)
        - frame["future_down_r"].to_numpy(dtype=np.float32),
        -3.0,
        3.0,
    ).astype(np.float32)


def target_sell_r(frame: pd.DataFrame) -> np.ndarray:
    return np.clip(
        frame["future_down_r"].to_numpy(dtype=np.float32)
        - frame["future_up_r"].to_numpy(dtype=np.float32),
        -3.0,
        3.0,
    ).astype(np.float32)


def sample_indices(rows: int, window_size: int, sample_stride: int, max_samples: int) -> np.ndarray:
    if window_size < 2:
        raise RuntimeError("window-size must be at least 2")
    if rows < window_size:
        raise RuntimeError(f"Need at least {window_size} rows; got {rows}")
    indices = np.arange(window_size - 1, rows, max(sample_stride, 1), dtype=np.int64)
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    return indices


def estimate_mb(samples: int, window_size: int, features: int, dtype: str) -> float:
    return samples * window_size * features * np.dtype(dtype).itemsize / (1024.0 * 1024.0)


def output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.five_timeframe.upper()
    root.mkdir(parents=True, exist_ok=True)
    tensor_path = root / f"{args.output_name}.npy"
    meta_path = root / f"{args.output_name}_meta.npz"
    flat_path = root / f"{args.output_name.replace('sequence_tensor', 'sequence_flat')}.parquet"
    output_dir = Path(args.output_dir)
    return tensor_path, meta_path, flat_path, output_dir / "latest.json", output_dir / "latest.html"


def feature_matrix(
    frame: pd.DataFrame, columns: Sequence[str], args: argparse.Namespace
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    raw = (
        frame[list(columns)]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )
    normalized, center, scale, nonfinite = axis_normalize(
        raw, args.axis_normalization, float(args.feature_clip)
    )
    return (
        normalized.astype(np.float32),
        center.astype(np.float32),
        scale.astype(np.float32),
        int(nonfinite),
    )


def build_sequence_tensor_memmap(
    values: np.ndarray,
    indices: np.ndarray,
    output_path: Path,
    window_size: int,
    dtype: str,
    chunk_size: int,
) -> np.memmap:
    shape = (len(indices), window_size, values.shape[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tensor = np.lib.format.open_memmap(output_path, mode="w+", dtype=np.dtype(dtype), shape=shape)
    windows = sliding_window_view(values, window_shape=window_size, axis=0).transpose(0, 2, 1)
    window_positions = indices - window_size + 1
    for start in range(0, len(indices), max(int(chunk_size), 1)):
        end = min(len(indices), start + max(int(chunk_size), 1))
        tensor[start:end] = windows[window_positions[start:end]].astype(dtype, copy=False)
    tensor.flush()
    return tensor


def build_report(
    args: argparse.Namespace,
    daily: pd.DataFrame,
    h4: pd.DataFrame,
    five: pd.DataFrame,
    frame: pd.DataFrame,
    tensor_shape: Sequence[int],
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    json_path: Path,
    html_path: Path,
    data_note: str,
    feature_names: Sequence[str],
    generated_feature_count: int,
    source_5m_feature_count: int,
    source_read: SourceFeatureRead,
    nonfinite_feature_values: int,
) -> SequenceTensorReport:
    return SequenceTensorReport(
        source_mode=args.source_mode,
        symbol=args.symbol,
        data_note=data_note,
        daily_rows=len(daily),
        h4_rows=len(h4),
        five_rows=len(five),
        flat_rows=len(frame),
        samples=int(tensor_shape[0]),
        window_size=int(tensor_shape[1]),
        features=int(tensor_shape[2]),
        stored_x_shape=[int(value) for value in tensor_shape],
        keras_batch_shape=f"[batch, {int(tensor_shape[1])}, {int(tensor_shape[2])}]",
        dtype=args.dtype,
        estimated_uncompressed_mb=estimate_mb(
            int(tensor_shape[0]), int(tensor_shape[1]), int(tensor_shape[2]), args.dtype
        ),
        sample_stride=max(int(args.sample_stride), 1),
        axis_normalization=args.axis_normalization,
        feature_clip=float(args.feature_clip),
        nonfinite_feature_values=nonfinite_feature_values,
        generated_feature_count=generated_feature_count,
        source_5m_feature_count=source_5m_feature_count,
        source_5m_feature_path=source_read.path,
        source_5m_total_columns=source_read.total_columns,
        source_5m_numeric_candidate_count=source_read.numeric_candidate_count,
        target_counts=class_counts(frame["target_action"].astype(int)),
        feature_names_preview=list(feature_names[:30]),
        output_tensor=str(tensor_path),
        output_meta=str(meta_path),
        output_flat=str(flat_path),
        output_json=str(json_path),
        output_html=str(html_path),
    )


def render_html(report: SequenceTensorReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>Phase145A Pivot Sequence Tensor</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>Phase145A — Pivot Sequence Tensor</h1><p>Option A: <code>[samples, WindowSize, Features]</code> برای Conv1D/WaveNet.</p></section>
<section class="card"><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        print("\n" + "=" * 74)
        print("  PHASE145A BUILD PIVOT SEQUENCE TENSOR")
        print("=" * 74)
        daily, h4, five, data_note = load_market_data(args)
        frame, generated_features = build_feature_frame(daily, h4, five)
        source_read = read_source_5m_frame(args)
        frame, source_features = merge_source_features(frame, source_read.frame)
        feature_names = [*generated_features, *source_features]
        if args.max_features > 0:
            feature_names = feature_names[: int(args.max_features)]
        config = PivotLabelConfig(
            lookahead_bars=max(int(args.lookahead_bars), 1),
            pivot_move_atr=max(float(args.pivot_move_atr), 0.01),
            pivot_zone_atr=max(float(args.pivot_zone_atr), 0.01),
            recent_window_bars=max(int(args.recent_window_bars), 1),
            min_direction_edge=max(float(args.min_direction_edge), 1.0),
        )
        frame = label_pivot_targets(frame, config)
        frame = frame[frame["target_available"] >= 0.5].copy().reset_index(drop=True)
        frame["target_buy_r"] = target_buy_r(frame)
        frame["target_sell_r"] = target_sell_r(frame)
        values, center, scale, nonfinite = feature_matrix(frame, feature_names, args)
        indices = sample_indices(
            len(frame), int(args.window_size), int(args.sample_stride), int(args.max_samples)
        )
        estimated = estimate_mb(len(indices), int(args.window_size), len(feature_names), args.dtype)
        if estimated > float(args.max_tensor_mb):
            raise RuntimeError(
                f"Estimated tensor size {estimated:.1f} MB exceeds --max-tensor-mb {args.max_tensor_mb}. "
                "Raise cap, increase sample stride, use float16, or reduce max-features."
            )
        tensor_path, meta_path, flat_path, json_path, html_path = output_paths(args)
        tensor = build_sequence_tensor_memmap(
            values, indices, tensor_path, int(args.window_size), args.dtype, int(args.chunk_size)
        )
        flat_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(flat_path, index=False)
        np.savez(
            meta_path,
            sample_indices=indices.astype(np.int64),
            row_id=frame["row_id"].to_numpy(dtype=np.int64)[indices],
            timestamp=frame["timestamp"].astype(str).to_numpy()[indices],
            target_action=frame["target_action"].to_numpy(dtype=np.int64)[indices],
            target_top_zone=frame["target_top_zone"].to_numpy(dtype=np.float32)[indices],
            target_bottom_zone=frame["target_bottom_zone"].to_numpy(dtype=np.float32)[indices],
            target_buy_r=frame["target_buy_r"].to_numpy(dtype=np.float32)[indices],
            target_sell_r=frame["target_sell_r"].to_numpy(dtype=np.float32)[indices],
            future_up_r=frame["future_up_r"].to_numpy(dtype=np.float32)[indices],
            future_down_r=frame["future_down_r"].to_numpy(dtype=np.float32)[indices],
            feature_names=np.asarray(feature_names, dtype=object),
            feature_groups=np.asarray(
                [classify_feature_group(name) for name in feature_names], dtype=object
            ),
            source_5m_feature_path=np.asarray([source_read.path], dtype=object),
            source_5m_total_columns=np.asarray([source_read.total_columns], dtype=np.int64),
            source_5m_numeric_candidate_count=np.asarray(
                [source_read.numeric_candidate_count], dtype=np.int64
            ),
            feature_center=center.astype(np.float32),
            feature_scale=scale.astype(np.float32),
            axis_normalization=np.asarray([args.axis_normalization], dtype=object),
            feature_clip=np.asarray([float(args.feature_clip)], dtype=np.float32),
            nonfinite_feature_values=np.asarray([int(nonfinite)], dtype=np.int64),
            window_size=np.asarray([int(args.window_size)], dtype=np.int32),
            tensor_layout=np.asarray(["[samples, window_size, features]"], dtype=object),
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        report = build_report(
            args,
            daily,
            h4,
            five,
            frame,
            tensor.shape,
            tensor_path,
            meta_path,
            flat_path,
            json_path,
            html_path,
            data_note,
            feature_names,
            len(generated_features),
            len(source_features),
            source_read,
            int(nonfinite),
        )
        payload = {
            "args": vars(args),
            "label_config": asdict(config),
            "report": asdict(report),
            "files": {
                "tensor_npy": str(tensor_path),
                "meta_npz": str(meta_path),
                "flat": str(flat_path),
                "json": str(json_path),
                "html": str(html_path),
            },
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        html_path.write_text(render_html(report), encoding="utf-8")
        print(f"  rows        : daily={len(daily):,} h4={len(h4):,} 5m={len(five):,}")
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  Keras batch : {report.keras_batch_shape}")
        print(
            f"  features    : {report.features:,} generated={len(generated_features):,} source5m={len(source_features):,}"
        )
        print(
            f"  source5m    : {source_read.path or 'none'} "
            f"candidates={source_read.numeric_candidate_count:,}"
        )
        print(f"  nonfinite   : features={report.nonfinite_feature_values:,}")
        print(f"  targets     : {report.target_counts}")
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
