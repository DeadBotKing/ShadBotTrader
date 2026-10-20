"""Phase142A: build a 3D pivot-pattern tensor for Keras WaveNet models.

Stored tensor shape is ``[samples, window, channels]``. During TensorFlow/Keras
training, the data loader adds the batch dimension, so runtime batches have
shape ``[batch, window, channels]``.
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
for import_path in (SCRIPT_DIR,):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from train_pivot_pattern_recognition import (
    PivotLabelConfig,
    build_feature_frame,
    class_counts,
    label_pivot_targets,
    load_market_data,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_tensor")
DTYPE_CHOICES = ("float16", "float32")


@dataclass(frozen=True)
class PivotTensorReport:
    source_mode: str
    symbol: str
    data_note: str
    daily_rows: int
    h4_rows: int
    five_rows: int
    flat_rows: int
    samples: int
    tensor_window: int
    channels: int
    stored_x_shape: list[int]
    keras_batch_shape: str
    dtype: str
    estimated_uncompressed_mb: float
    target_counts: dict[str, int]
    feature_columns: list[str]
    output_tensor: str
    output_flat: str
    output_json: str
    output_html: str
    warnings: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Phase142A 3D pivot-pattern tensor [samples, window, channels].",
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
    parser.add_argument("--tensor-window", type=int, default=288)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all chronological samples")
    parser.add_argument("--dtype", choices=DTYPE_CHOICES, default="float16")
    parser.add_argument("--max-tensor-mb", type=float, default=4096.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-name", default="pivot_pattern_tensor_latest")
    return parser.parse_args(argv)


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


def sample_indices(
    rows: int, tensor_window: int, sample_stride: int, max_samples: int
) -> np.ndarray:
    if tensor_window < 2:
        raise RuntimeError("tensor-window must be at least 2")
    if rows < tensor_window:
        raise RuntimeError(f"Need at least {tensor_window} rows to build tensor; got {rows}")
    indices = np.arange(tensor_window - 1, rows, max(sample_stride, 1), dtype=np.int64)
    if max_samples > 0 and len(indices) > max_samples:
        step = max(1, len(indices) // max_samples)
        indices = indices[::step][:max_samples]
    return indices


def build_tensor_array(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    indices: Sequence[int],
    tensor_window: int,
    dtype: str,
) -> np.ndarray:
    values = (
        frame[list(feature_columns)]
        .replace([np.inf, -np.inf], 0.0)
        .fillna(0.0)
        .to_numpy(dtype=np.float32)
    )
    out = np.empty((len(indices), tensor_window, len(feature_columns)), dtype=np.dtype(dtype))
    for output_row, end_index in enumerate(indices):
        start = int(end_index) - tensor_window + 1
        out[output_row] = values[start : int(end_index) + 1].astype(dtype, copy=False)
    return out


def estimate_mb(samples: int, tensor_window: int, channels: int, dtype: str) -> float:
    return samples * tensor_window * channels * np.dtype(dtype).itemsize / (1024.0 * 1024.0)


def default_output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    storage_root = Path(args.storage_root)
    processed_dir = storage_root / "processed" / args.symbol / args.five_timeframe.upper()
    processed_dir.mkdir(parents=True, exist_ok=True)
    tensor_path = processed_dir / f"{args.output_name}.npz"
    if args.output_name.endswith("_latest"):
        tensor_path = processed_dir / f"{args.output_name}.npz"
    flat_name = args.output_name.replace("tensor", "flat")
    flat_path = processed_dir / f"{flat_name}.parquet"
    output_dir = Path(args.output_dir)
    return tensor_path, flat_path, output_dir / "latest.json", output_dir / "latest.html"


def render_html(report: PivotTensorReport) -> str:
    feature_list = "".join(
        f"<li><code>{html.escape(name)}</code></li>" for name in report.feature_columns
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8" /><title>Phase142A Pivot Pattern Tensor</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>Phase142A — Pivot Pattern Tensor</h1>
<p>خروجی ذخیره‌شده سه‌بعدی است: <code>[samples, window, channels]</code>. در زمان آموزش Keras، batch dimension اضافه می‌شود: <code>[batch, window, channels]</code>.</p>
<div class="grid">
<div class="metric"><span>Stored X shape</span><strong>{report.stored_x_shape}</strong></div>
<div class="metric"><span>Keras batch shape</span><strong>{html.escape(report.keras_batch_shape)}</strong></div>
<div class="metric"><span>Samples</span><strong>{report.samples:,}</strong></div>
<div class="metric"><span>Channels</span><strong>{report.channels}</strong></div>
</div></section>
<section class="card"><h2>Summary</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Feature channels</h2><ul>{feature_list}</ul></section>
</main></body></html>"""


def build_report(
    args: argparse.Namespace,
    daily: pd.DataFrame,
    h4: pd.DataFrame,
    five: pd.DataFrame,
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    tensor: np.ndarray,
    tensor_path: Path,
    flat_path: Path,
    json_path: Path,
    html_path: Path,
    data_note: str,
    warnings: Sequence[str],
) -> PivotTensorReport:
    counts = class_counts(frame.loc[frame["target_available"] >= 0.5, "target_action"].astype(int))
    return PivotTensorReport(
        source_mode=args.source_mode,
        symbol=args.symbol,
        data_note=data_note,
        daily_rows=len(daily),
        h4_rows=len(h4),
        five_rows=len(five),
        flat_rows=len(frame),
        samples=int(tensor.shape[0]),
        tensor_window=int(tensor.shape[1]),
        channels=int(tensor.shape[2]),
        stored_x_shape=[int(value) for value in tensor.shape],
        keras_batch_shape=f"[batch, {int(tensor.shape[1])}, {int(tensor.shape[2])}]",
        dtype=str(tensor.dtype),
        estimated_uncompressed_mb=estimate_mb(
            int(tensor.shape[0]), int(tensor.shape[1]), int(tensor.shape[2]), str(tensor.dtype)
        ),
        target_counts=counts,
        feature_columns=list(feature_columns),
        output_tensor=str(tensor_path),
        output_flat=str(flat_path),
        output_json=str(json_path),
        output_html=str(html_path),
        warnings=list(warnings),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    warnings: list[str] = []
    try:
        print("\n" + "=" * 74)
        print("  PHASE142A BUILD PIVOT PATTERN 3D TENSOR")
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
        indices = sample_indices(
            len(frame), int(args.tensor_window), int(args.sample_stride), int(args.max_samples)
        )
        estimated = estimate_mb(
            len(indices), int(args.tensor_window), len(feature_columns), str(args.dtype)
        )
        if estimated > float(args.max_tensor_mb):
            raise RuntimeError(
                f"Estimated tensor size {estimated:.1f} MB exceeds --max-tensor-mb {args.max_tensor_mb}. "
                "Increase the cap, use float16, raise --sample-stride, or set --max-samples."
            )
        tensor = build_tensor_array(
            frame, feature_columns, indices, int(args.tensor_window), args.dtype
        )
        tensor_path, flat_path, json_path, html_path = default_output_paths(args)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        flat_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(flat_path, index=False)
        np.savez(
            tensor_path,
            X=tensor,
            sample_indices=np.asarray(indices, dtype=np.int64),
            row_id=frame["row_id"].to_numpy(dtype=np.int64)[indices],
            timestamp=frame["timestamp"].astype(str).to_numpy()[indices],
            target_action=frame["target_action"].to_numpy(dtype=np.int64)[indices],
            target_top_zone=frame["target_top_zone"].to_numpy(dtype=np.float32)[indices],
            target_bottom_zone=frame["target_bottom_zone"].to_numpy(dtype=np.float32)[indices],
            target_buy_r=frame["target_buy_r"].to_numpy(dtype=np.float32)[indices],
            target_sell_r=frame["target_sell_r"].to_numpy(dtype=np.float32)[indices],
            future_up_r=frame["future_up_r"].to_numpy(dtype=np.float32)[indices],
            future_down_r=frame["future_down_r"].to_numpy(dtype=np.float32)[indices],
            h4_atr_for_risk=frame["h4_atr_for_risk"].to_numpy(dtype=np.float32)[indices],
            close=frame["close"].to_numpy(dtype=np.float32)[indices],
            feature_columns=np.asarray(feature_columns, dtype=object),
            tensor_window=np.asarray([int(args.tensor_window)], dtype=np.int32),
            source_mode=np.asarray([args.source_mode], dtype=object),
            data_note=np.asarray([data_note], dtype=object),
        )
        report = build_report(
            args,
            daily,
            h4,
            five,
            frame,
            feature_columns,
            tensor,
            tensor_path,
            flat_path,
            json_path,
            html_path,
            data_note,
            warnings,
        )
        payload = {
            "args": vars(args),
            "label_config": asdict(config),
            "report": asdict(report),
            "files": {
                "tensor": str(tensor_path),
                "flat": str(flat_path),
                "json": str(json_path),
                "html": str(html_path),
            },
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        html_path.write_text(render_html(report), encoding="utf-8")
        print(f"  rows        : daily={len(daily):,} h4={len(h4):,} 5m={len(five):,}")
        print(f"  X shape     : {list(tensor.shape)}")
        print(f"  keras batch : {report.keras_batch_shape}")
        print(f"  targets     : {report.target_counts}")
        print(f"  tensor      : {tensor_path}")
        print(f"  flat        : {flat_path}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
