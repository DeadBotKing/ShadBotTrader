"""Phase143A: build a 4D pivot image tensor for Conv2D/Conv3D models.

The owner-requested layout is:

    X = [samples, window_size, features_5m, features_4h_1d]

Keras Conv2D receives batches as:

    batch_X = [batch, window_size, features_5m, features_4h_1d]

Keras Conv3D can consume the same tensor with a singleton channel axis added at
runtime:

    batch_X = [batch, window_size, features_5m, features_4h_1d, 1]

Each cell is an interaction between one 5M feature and one HTF feature:

    X[t, i, j] = feature_5m[t, i] * feature_htf[t, j]

A bias feature is prepended to both axes, so the tensor also preserves pure 5M
features and pure 4H/1D features, not only interactions.
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
from numpy.lib.stride_tricks import sliding_window_view
from train_pivot_pattern_recognition import (
    PivotLabelConfig,
    build_feature_frame,
    class_counts,
    label_pivot_targets,
    load_market_data,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_image_tensor")
DTYPE_CHOICES = ("float16", "float32")
DEFAULT_5M_FEATURES = (
    "m5_pos_in_range_48",
    "m5_dist_high_48_atr",
    "m5_dist_low_48_atr",
    "m5_fast_mid_dist_atr",
    "m5_price_z_96",
    "m5_pos_in_range_24",
    "m5_ret48",
    "m5_close_mid_dist_atr",
    "m5_ret24",
    "m5_dist_high_24_atr",
    "m5_pos_in_range_96",
    "m5_mid_slow_dist_atr",
)
DEFAULT_HTF_FEATURES = (
    "h4_ret1",
    "h4_body_pct",
    "h4_range_pct",
    "h4_rsi14",
    "h4_room_up_atr",
    "h4_room_down_atr",
    "d1_ret1",
    "d1_body_pct",
)


@dataclass(frozen=True)
class ImageTensorReport:
    source_mode: str
    symbol: str
    data_note: str
    daily_rows: int
    h4_rows: int
    five_rows: int
    flat_rows: int
    samples: int
    window_size: int
    features_5m: int
    features_4h_1d: int
    stored_x_shape: list[int]
    conv2d_batch_shape: str
    conv3d_batch_shape: str
    dtype: str
    estimated_uncompressed_mb: float
    sample_stride: int
    axis_normalization: str
    feature_clip: float
    interaction_clip: float
    nonfinite_feature_values: int
    nonfinite_interaction_values: int
    target_counts: dict[str, int]
    feature_5m_names: list[str]
    feature_htf_names: list[str]
    output_tensor: str
    output_meta: str
    output_flat: str
    output_json: str
    output_html: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Phase143A 4D pivot image tensor [samples, window, 5M features, 4H/1D features].",
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
    parser.add_argument("--max-5m-features", type=int, default=24)
    parser.add_argument("--max-htf-features", type=int, default=16)
    parser.add_argument("--dtype", choices=DTYPE_CHOICES, default="float16")
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--max-tensor-mb", type=float, default=8192.0)
    parser.add_argument(
        "--axis-normalization", choices=("robust", "standard", "none"), default="robust"
    )
    parser.add_argument("--feature-clip", type=float, default=8.0)
    parser.add_argument("--interaction-clip", type=float, default=32.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-name", default="pivot_pattern_image_tensor_latest")
    return parser.parse_args(argv)


def finite_frame(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    return (
        frame[list(columns)].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
    )


def sanitize_array(values: np.ndarray) -> tuple[np.ndarray, int]:
    nonfinite = int(values.size - np.isfinite(values).sum())
    clean = np.nan_to_num(values.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    return clean, nonfinite


def axis_normalize(
    values: np.ndarray, mode: str, feature_clip: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    clean, nonfinite = sanitize_array(values)
    if mode == "none":
        center = np.zeros((1, clean.shape[1]), dtype=np.float32)
        scale = np.ones((1, clean.shape[1]), dtype=np.float32)
        normalized = clean
    elif mode == "standard":
        center = np.mean(clean, axis=0, keepdims=True).astype(np.float32)
        scale = np.std(clean, axis=0, keepdims=True).astype(np.float32)
        scale = np.where((~np.isfinite(scale)) | (scale < 1e-6), 1.0, scale).astype(np.float32)
        normalized = (clean - center) / scale
    else:
        center = np.median(clean, axis=0, keepdims=True).astype(np.float32)
        q75 = np.percentile(clean, 75, axis=0, keepdims=True).astype(np.float32)
        q25 = np.percentile(clean, 25, axis=0, keepdims=True).astype(np.float32)
        robust_scale = ((q75 - q25) / 1.349).astype(np.float32)
        std_scale = np.std(clean, axis=0, keepdims=True).astype(np.float32)
        scale = np.where(robust_scale >= 1e-6, robust_scale, std_scale).astype(np.float32)
        scale = np.where((~np.isfinite(scale)) | (scale < 1e-6), 1.0, scale).astype(np.float32)
        normalized = (clean - center) / scale
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    if feature_clip > 0:
        normalized = np.clip(normalized, -float(feature_clip), float(feature_clip)).astype(
            np.float32
        )
    return normalized, center, scale, nonfinite


def available_features(
    columns: Sequence[str], preferred: Sequence[str], prefix: str, limit: int
) -> list[str]:
    selected = [name for name in preferred if name in columns]
    if len(selected) < limit:
        for name in columns:
            if name.startswith(prefix) and name not in selected:
                selected.append(name)
            if len(selected) >= limit:
                break
    return selected[: max(limit, 1)]


def select_feature_axes(
    feature_columns: Sequence[str], args: argparse.Namespace
) -> tuple[list[str], list[str]]:
    five_features = available_features(
        feature_columns, DEFAULT_5M_FEATURES, "m5_", max(int(args.max_5m_features), 1)
    )
    htf_candidates = [name for name in feature_columns if name.startswith(("h4_", "d1_"))]
    htf_features = [name for name in DEFAULT_HTF_FEATURES if name in htf_candidates]
    if len(htf_features) < max(int(args.max_htf_features), 1):
        for name in htf_candidates:
            if name not in htf_features:
                htf_features.append(name)
            if len(htf_features) >= max(int(args.max_htf_features), 1):
                break
    if not five_features or not htf_features:
        raise RuntimeError("Could not select both 5M and 4H/1D feature axes")
    return five_features, htf_features[: max(int(args.max_htf_features), 1)]


def add_bias(values: np.ndarray) -> np.ndarray:
    return np.concatenate([np.ones((len(values), 1), dtype=np.float32), values], axis=1)


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


def estimate_mb(
    samples: int, window_size: int, five_features: int, htf_features: int, dtype: str
) -> float:
    return (
        samples
        * window_size
        * five_features
        * htf_features
        * np.dtype(dtype).itemsize
        / (1024.0 * 1024.0)
    )


def build_image_tensor_memmap(
    five_values: np.ndarray,
    htf_values: np.ndarray,
    indices: np.ndarray,
    output_path: Path,
    window_size: int,
    dtype: str,
    chunk_size: int,
    interaction_clip: float,
    diagnostics: dict[str, int] | None = None,
) -> np.memmap:
    samples = len(indices)
    shape = (samples, window_size, five_values.shape[1], htf_values.shape[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tensor = np.lib.format.open_memmap(output_path, mode="w+", dtype=np.dtype(dtype), shape=shape)
    five_windows = sliding_window_view(five_values, window_shape=window_size, axis=0).transpose(
        0, 2, 1
    )
    htf_windows = sliding_window_view(htf_values, window_shape=window_size, axis=0).transpose(
        0, 2, 1
    )
    window_positions = indices - window_size + 1
    for start in range(0, samples, max(chunk_size, 1)):
        end = min(samples, start + max(chunk_size, 1))
        positions = window_positions[start:end]
        five_chunk = five_windows[positions]
        htf_chunk = htf_windows[positions]
        product = five_chunk[:, :, :, None] * htf_chunk[:, :, None, :]
        nonfinite = int(product.size - np.isfinite(product).sum())
        if diagnostics is not None:
            diagnostics["nonfinite_interaction_values"] = (
                diagnostics.get("nonfinite_interaction_values", 0) + nonfinite
            )
        clip_value = max(float(interaction_clip), 0.0)
        product = np.nan_to_num(
            product,
            nan=0.0,
            posinf=clip_value if clip_value else 0.0,
            neginf=-(clip_value if clip_value else 0.0),
        )
        if clip_value > 0:
            product = np.clip(product, -clip_value, clip_value)
        tensor[start:end] = product.astype(dtype, copy=False)
    tensor.flush()
    return tensor


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


def output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.five_timeframe.upper()
    root.mkdir(parents=True, exist_ok=True)
    tensor_path = root / f"{args.output_name}.npy"
    meta_path = root / f"{args.output_name}_meta.npz"
    flat_path = root / f"{args.output_name.replace('image_tensor', 'image_flat')}.parquet"
    output_dir = Path(args.output_dir)
    return tensor_path, meta_path, flat_path, output_dir / "latest.json", output_dir / "latest.html"


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
    five_features: Sequence[str],
    htf_features: Sequence[str],
    nonfinite_feature_values: int,
    nonfinite_interaction_values: int,
) -> ImageTensorReport:
    return ImageTensorReport(
        source_mode=args.source_mode,
        symbol=args.symbol,
        data_note=data_note,
        daily_rows=len(daily),
        h4_rows=len(h4),
        five_rows=len(five),
        flat_rows=len(frame),
        samples=int(tensor_shape[0]),
        window_size=int(tensor_shape[1]),
        features_5m=int(tensor_shape[2]),
        features_4h_1d=int(tensor_shape[3]),
        stored_x_shape=[int(value) for value in tensor_shape],
        conv2d_batch_shape=(
            f"[batch, {int(tensor_shape[1])}, {int(tensor_shape[2])}, {int(tensor_shape[3])}]"
        ),
        conv3d_batch_shape=(
            f"[batch, {int(tensor_shape[1])}, {int(tensor_shape[2])}, {int(tensor_shape[3])}, 1]"
        ),
        dtype=args.dtype,
        estimated_uncompressed_mb=estimate_mb(
            int(tensor_shape[0]),
            int(tensor_shape[1]),
            int(tensor_shape[2]),
            int(tensor_shape[3]),
            args.dtype,
        ),
        sample_stride=max(int(args.sample_stride), 1),
        axis_normalization=args.axis_normalization,
        feature_clip=float(args.feature_clip),
        interaction_clip=float(args.interaction_clip),
        nonfinite_feature_values=int(nonfinite_feature_values),
        nonfinite_interaction_values=int(nonfinite_interaction_values),
        target_counts=class_counts(frame["target_action"].astype(int)),
        feature_5m_names=["__5m_bias__", *five_features],
        feature_htf_names=["__htf_bias__", *htf_features],
        output_tensor=str(tensor_path),
        output_meta=str(meta_path),
        output_flat=str(flat_path),
        output_json=str(json_path),
        output_html=str(html_path),
    )


def render_html(report: ImageTensorReport) -> str:
    f5 = "".join(f"<li><code>{html.escape(name)}</code></li>" for name in report.feature_5m_names)
    htf = "".join(f"<li><code>{html.escape(name)}</code></li>" for name in report.feature_htf_names)
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>Phase143A 4D Pivot Image Tensor</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1400px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:20px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>Phase143A — 4D Pivot Image Tensor</h1>
<p>این دیتاست دقیقاً برای Conv2D/Conv3D است: <code>[samples, WindowSize, Features_5M, Features_4H_1D]</code>.</p>
<div class="grid">
<div class="metric"><span>Stored X</span><strong>{report.stored_x_shape}</strong></div>
<div class="metric"><span>Conv2D batch</span><strong>{html.escape(report.conv2d_batch_shape)}</strong></div>
<div class="metric"><span>Conv3D batch</span><strong>{html.escape(report.conv3d_batch_shape)}</strong></div>
<div class="metric"><span>Size MB</span><strong>{report.estimated_uncompressed_mb:.1f}</strong></div>
</div></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>5M feature axis</h2><ul>{f5}</ul></section>
<section class="card"><h2>4H/1D feature axis</h2><ul>{htf}</ul></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        print("\n" + "=" * 74)
        print("  PHASE143A BUILD 4D PIVOT IMAGE TENSOR")
        print("=" * 74)
        print(f"  source      : {args.source_mode}")
        print(f"  symbol      : {args.symbol}")
        daily, h4, five, data_note = load_market_data(args)
        frame, feature_columns = build_feature_frame(daily, h4, five)
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
        five_features, htf_features = select_feature_axes(feature_columns, args)
        five_raw = finite_frame(frame, five_features)
        htf_raw = finite_frame(frame, htf_features)
        five_normalized, five_center, five_scale, five_nonfinite = axis_normalize(
            five_raw, args.axis_normalization, float(args.feature_clip)
        )
        htf_normalized, htf_center, htf_scale, htf_nonfinite = axis_normalize(
            htf_raw, args.axis_normalization, float(args.feature_clip)
        )
        five_values = add_bias(five_normalized)
        htf_values = add_bias(htf_normalized)
        nonfinite_feature_values = five_nonfinite + htf_nonfinite
        indices = sample_indices(
            len(frame), int(args.window_size), int(args.sample_stride), int(args.max_samples)
        )
        estimated = estimate_mb(
            len(indices),
            int(args.window_size),
            five_values.shape[1],
            htf_values.shape[1],
            args.dtype,
        )
        if estimated > float(args.max_tensor_mb):
            raise RuntimeError(
                f"Estimated tensor size {estimated:.1f} MB exceeds --max-tensor-mb {args.max_tensor_mb}. "
                "Reduce feature caps, increase stride, or raise max-tensor-mb."
            )
        tensor_path, meta_path, flat_path, json_path, html_path = output_paths(args)
        diagnostics: dict[str, int] = {"nonfinite_interaction_values": 0}
        tensor = build_image_tensor_memmap(
            five_values,
            htf_values,
            indices,
            tensor_path,
            int(args.window_size),
            args.dtype,
            int(args.chunk_size),
            float(args.interaction_clip),
            diagnostics,
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
            feature_5m_names=np.asarray(["__5m_bias__", *five_features], dtype=object),
            feature_htf_names=np.asarray(["__htf_bias__", *htf_features], dtype=object),
            feature_5m_center=five_center.astype(np.float32),
            feature_5m_scale=five_scale.astype(np.float32),
            feature_htf_center=htf_center.astype(np.float32),
            feature_htf_scale=htf_scale.astype(np.float32),
            axis_normalization=np.asarray([args.axis_normalization], dtype=object),
            feature_clip=np.asarray([float(args.feature_clip)], dtype=np.float32),
            interaction_clip=np.asarray([float(args.interaction_clip)], dtype=np.float32),
            nonfinite_feature_values=np.asarray([int(nonfinite_feature_values)], dtype=np.int64),
            nonfinite_interaction_values=np.asarray(
                [int(diagnostics["nonfinite_interaction_values"])], dtype=np.int64
            ),
            window_size=np.asarray([int(args.window_size)], dtype=np.int32),
            tensor_layout=np.asarray(
                ["[samples, window_size, features_5m, features_4h_1d]"], dtype=object
            ),
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
            five_features,
            htf_features,
            nonfinite_feature_values,
            diagnostics["nonfinite_interaction_values"],
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
        print(f"  Conv2D batch: {report.conv2d_batch_shape}")
        print(f"  Conv3D batch: {report.conv3d_batch_shape}")
        print(f"  targets     : {report.target_counts}")
        print(
            f"  normalization: {report.axis_normalization} feature_clip={report.feature_clip:g} interaction_clip={report.interaction_clip:g}"
        )
        print(
            f"  nonfinite   : features={report.nonfinite_feature_values:,} interactions={report.nonfinite_interaction_values:,}"
        )
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
