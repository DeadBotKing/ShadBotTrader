"""Phase143A: audit 4D pivot image tensor health before training.

This script is a pre-training gate. It validates the owner-requested 4D tensor:

    X = [samples, WindowSize, Features_5M, Features_4H_1D]

It does not train a model and does not approve production. It only confirms the
dataset is structurally clean, finite, aligned with metadata, and safe for
Conv2D/Conv3D training.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_image_tensor_health")
TARGET_ARRAYS = (
    "target_action",
    "target_top_zone",
    "target_bottom_zone",
    "target_buy_r",
    "target_sell_r",
)
SCALER_ARRAYS = (
    "feature_5m_center",
    "feature_5m_scale",
    "feature_htf_center",
    "feature_htf_scale",
)


@dataclass(frozen=True)
class TensorScanSummary:
    scanned_cells: int
    nonfinite_cells: int
    min_value: float
    max_value: float
    max_abs: float
    chunks: int


@dataclass(frozen=True)
class PivotImageTensorHealthReport:
    status: str
    symbol: str
    timeframe: str
    tensor_path: str
    meta_path: str
    flat_path: str
    builder_report_path: str
    tensor_shape: list[int]
    tensor_dtype: str
    samples: int
    window_size: int
    features_5m: int
    features_4h_1d: int
    conv2d_batch_shape: str
    conv3d_batch_shape: str
    flat_rows: int
    sample_indices_count: int
    sample_index_min: int
    sample_index_max: int
    sample_index_min_step: int
    sample_index_max_step: int
    timestamp_count: int
    first_timestamp: str
    last_timestamp: str
    target_action_counts: dict[str, int]
    feature_5m_count: int
    feature_htf_count: int
    feature_5m_preview: list[str]
    feature_htf_preview: list[str]
    axis_normalization: str
    feature_clip: float
    interaction_clip: float
    reported_nonfinite_feature_values: int
    reported_nonfinite_interaction_values: int
    scan: TensorScanSummary
    warnings: list[str]
    errors: list[str]
    output_json: str
    output_html: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Phase143A 4D pivot image tensor health before CNN training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument(
        "--builder-report", default="run_logs/pivot_pattern_image_tensor/latest.json"
    )
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--full-scan", choices=("0", "1"), default="1")
    parser.add_argument("--max-scan-samples", type=int, default=0)
    parser.add_argument("--fail-on-reported-feature-nonfinite", choices=("0", "1"), default="0")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "pivot_pattern_image_tensor_latest.npy"


def default_meta_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_image_tensor_latest_meta.npz"
    )


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root / "processed" / symbol / timeframe / "pivot_pattern_image_flat_latest.parquet"
    )


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    storage_root = Path(args.storage_root)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(storage_root, args.symbol, args.timeframe)
    )
    meta_path = (
        Path(args.meta_path)
        if args.meta_path
        else default_meta_path(storage_root, args.symbol, args.timeframe)
    )
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    return tensor_path, meta_path, flat_path, Path(args.builder_report)


def scalar_from_meta(meta: dict[str, Any], key: str, default: float | str | int) -> Any:
    if key not in meta:
        return default
    value = np.asarray(meta[key])
    if value.size == 0:
        return default
    raw = value.reshape(-1)[0]
    if isinstance(default, str):
        return str(raw)
    if isinstance(default, int):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def load_builder_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def scan_tensor(
    tensor: np.ndarray, chunk_size: int, full_scan: str, max_scan_samples: int
) -> TensorScanSummary:
    samples = int(tensor.shape[0])
    if full_scan != "1":
        scan_indices = np.linspace(
            0, max(samples - 1, 0), num=min(samples, max(max_scan_samples, 1)), dtype=np.int64
        )
        scan_ranges = [(int(index), int(index) + 1) for index in scan_indices]
    else:
        limit = samples if max_scan_samples <= 0 else min(samples, max_scan_samples)
        scan_ranges = [
            (start, min(limit, start + max(chunk_size, 1)))
            for start in range(0, limit, max(chunk_size, 1))
        ]
    nonfinite = 0
    scanned_cells = 0
    min_value: float | None = None
    max_value: float | None = None
    max_abs = 0.0
    chunks = 0
    for start, end in scan_ranges:
        chunk = np.asarray(tensor[start:end], dtype=np.float32)
        chunks += 1
        scanned_cells += int(chunk.size)
        finite_mask = np.isfinite(chunk)
        nonfinite += int(chunk.size - int(finite_mask.sum()))
        if np.any(finite_mask):
            values = chunk[finite_mask]
            cmin = float(values.min())
            cmax = float(values.max())
            min_value = cmin if min_value is None else min(min_value, cmin)
            max_value = cmax if max_value is None else max(max_value, cmax)
            max_abs = max(max_abs, float(np.abs(values).max()))
    return TensorScanSummary(
        scanned_cells=scanned_cells,
        nonfinite_cells=nonfinite,
        min_value=0.0 if min_value is None else float(min_value),
        max_value=0.0 if max_value is None else float(max_value),
        max_abs=float(max_abs),
        chunks=chunks,
    )


def feature_names(meta: dict[str, Any], key: str) -> list[str]:
    if key not in meta:
        return []
    return [str(value) for value in np.asarray(meta[key]).tolist()]


def target_counts(target_action: np.ndarray) -> dict[str, int]:
    names = {0: "SELL", 1: "HOLD", 2: "BUY"}
    unique, counts = np.unique(target_action.astype(np.int64), return_counts=True)
    return {
        names.get(int(value), str(int(value))): int(count)
        for value, count in zip(unique, counts, strict=True)
    }


def validate_tensor(
    tensor: np.ndarray,
    meta: dict[str, Any],
    flat: pd.DataFrame,
    builder_report: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[list[str], list[str], TensorScanSummary]:
    errors: list[str] = []
    warnings: list[str] = []
    if tensor.ndim != 4:
        errors.append(f"Tensor rank must be 4; got shape={list(tensor.shape)}")
    sample_indices = np.asarray(meta.get("sample_indices", []), dtype=np.int64)
    timestamps = pd.to_datetime(
        pd.Series(np.asarray(meta.get("timestamp", [])).astype(str)), utc=True, errors="coerce"
    )
    if len(sample_indices) != int(tensor.shape[0]):
        errors.append("sample_indices length does not match tensor samples")
    if len(timestamps) != int(tensor.shape[0]):
        errors.append("timestamp length does not match tensor samples")
    if len(sample_indices) and int(sample_indices.max()) >= len(flat):
        errors.append("sample_indices exceed flat row count")
    if len(sample_indices) > 1:
        diffs = np.diff(sample_indices)
        if not np.all(diffs >= 1):
            errors.append("sample_indices must be strictly increasing")
    if len(timestamps) and not timestamps.is_monotonic_increasing:
        errors.append("timestamps are not monotonic increasing")
    window_size = int(
        scalar_from_meta(meta, "window_size", int(tensor.shape[1]) if tensor.ndim >= 2 else 0)
    )
    if tensor.ndim >= 2 and int(tensor.shape[1]) != window_size:
        errors.append("tensor window dimension does not match meta.window_size")
    names_5m = feature_names(meta, "feature_5m_names")
    names_htf = feature_names(meta, "feature_htf_names")
    if tensor.ndim >= 3 and names_5m and len(names_5m) != int(tensor.shape[2]):
        errors.append("feature_5m_names length does not match tensor axis 2")
    if tensor.ndim >= 4 and names_htf and len(names_htf) != int(tensor.shape[3]):
        errors.append("feature_htf_names length does not match tensor axis 3")
    for target in TARGET_ARRAYS:
        if target not in meta:
            errors.append(f"Missing target array: {target}")
            continue
        values = np.asarray(meta[target])
        if len(values) != int(tensor.shape[0]):
            errors.append(f"{target} length does not match tensor samples")
        if values.dtype.kind in "fc" and not np.isfinite(values).all():
            errors.append(f"{target} contains NaN/Inf")
    for scaler in SCALER_ARRAYS:
        if scaler not in meta:
            warnings.append(f"Missing axis scaler metadata: {scaler}")
            continue
        values = np.asarray(meta[scaler], dtype=np.float32)
        if not np.isfinite(values).all():
            errors.append(f"{scaler} contains NaN/Inf")
    reported_nonfinite_feature = int(scalar_from_meta(meta, "nonfinite_feature_values", -1))
    reported_nonfinite_interaction = int(scalar_from_meta(meta, "nonfinite_interaction_values", -1))
    report_payload = builder_report.get("report", {}) if isinstance(builder_report, dict) else {}
    if report_payload:
        report_shape = report_payload.get("stored_x_shape")
        if report_shape and list(report_shape) != [int(value) for value in tensor.shape]:
            errors.append("Tensor shape does not match builder report stored_x_shape")
        reported_nonfinite_feature = int(
            report_payload.get("nonfinite_feature_values", reported_nonfinite_feature)
        )
        reported_nonfinite_interaction = int(
            report_payload.get("nonfinite_interaction_values", reported_nonfinite_interaction)
        )
    if reported_nonfinite_feature > 0:
        message = f"Builder reported nonfinite_feature_values={reported_nonfinite_feature}"
        if args.fail_on_reported_feature_nonfinite == "1":
            errors.append(message)
        else:
            warnings.append(message)
    if reported_nonfinite_interaction > 0:
        errors.append(
            f"Builder reported nonfinite_interaction_values={reported_nonfinite_interaction}"
        )
    scan = scan_tensor(tensor, int(args.chunk_size), args.full_scan, int(args.max_scan_samples))
    if scan.nonfinite_cells != 0:
        errors.append(f"Tensor contains {scan.nonfinite_cells} NaN/Inf cells")
    interaction_clip = float(
        scalar_from_meta(meta, "interaction_clip", report_payload.get("interaction_clip", 0.0))
    )
    if interaction_clip > 0 and scan.max_abs > interaction_clip + 1e-3:
        errors.append(
            f"Tensor max_abs={scan.max_abs:.6g} exceeds interaction_clip={interaction_clip:.6g}"
        )
    return errors, warnings, scan


def build_report(
    args: argparse.Namespace,
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    builder_report_path: Path,
    tensor: np.ndarray,
    meta: dict[str, Any],
    flat: pd.DataFrame,
    errors: Sequence[str],
    warnings: Sequence[str],
    scan: TensorScanSummary,
    output_json: Path,
    output_html: Path,
) -> PivotImageTensorHealthReport:
    sample_indices = np.asarray(meta.get("sample_indices", []), dtype=np.int64)
    timestamps = pd.to_datetime(
        pd.Series(np.asarray(meta.get("timestamp", [])).astype(str)), utc=True, errors="coerce"
    )
    names_5m = feature_names(meta, "feature_5m_names")
    names_htf = feature_names(meta, "feature_htf_names")
    target_action = np.asarray(meta.get("target_action", []), dtype=np.int64)
    diffs = np.diff(sample_indices) if len(sample_indices) > 1 else np.asarray([], dtype=np.int64)
    axis_normalization = str(scalar_from_meta(meta, "axis_normalization", "unknown"))
    return PivotImageTensorHealthReport(
        status="PASS" if not errors else "FAIL",
        symbol=args.symbol,
        timeframe=args.timeframe,
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        flat_path=str(flat_path),
        builder_report_path=str(builder_report_path),
        tensor_shape=[int(value) for value in tensor.shape],
        tensor_dtype=str(tensor.dtype),
        samples=int(tensor.shape[0]),
        window_size=int(tensor.shape[1]) if tensor.ndim >= 2 else 0,
        features_5m=int(tensor.shape[2]) if tensor.ndim >= 3 else 0,
        features_4h_1d=int(tensor.shape[3]) if tensor.ndim >= 4 else 0,
        conv2d_batch_shape=(
            f"[batch, {int(tensor.shape[1])}, {int(tensor.shape[2])}, {int(tensor.shape[3])}]"
            if tensor.ndim == 4
            else "invalid"
        ),
        conv3d_batch_shape=(
            f"[batch, {int(tensor.shape[1])}, {int(tensor.shape[2])}, {int(tensor.shape[3])}, 1]"
            if tensor.ndim == 4
            else "invalid"
        ),
        flat_rows=len(flat),
        sample_indices_count=len(sample_indices),
        sample_index_min=0 if len(sample_indices) == 0 else int(sample_indices.min()),
        sample_index_max=0 if len(sample_indices) == 0 else int(sample_indices.max()),
        sample_index_min_step=0 if len(diffs) == 0 else int(diffs.min()),
        sample_index_max_step=0 if len(diffs) == 0 else int(diffs.max()),
        timestamp_count=len(timestamps),
        first_timestamp="" if len(timestamps) == 0 else str(timestamps.iloc[0]),
        last_timestamp="" if len(timestamps) == 0 else str(timestamps.iloc[-1]),
        target_action_counts=target_counts(target_action) if len(target_action) else {},
        feature_5m_count=len(names_5m),
        feature_htf_count=len(names_htf),
        feature_5m_preview=names_5m[:10],
        feature_htf_preview=names_htf[:10],
        axis_normalization=axis_normalization,
        feature_clip=float(scalar_from_meta(meta, "feature_clip", 0.0)),
        interaction_clip=float(scalar_from_meta(meta, "interaction_clip", 0.0)),
        reported_nonfinite_feature_values=int(
            scalar_from_meta(meta, "nonfinite_feature_values", -1)
        ),
        reported_nonfinite_interaction_values=int(
            scalar_from_meta(meta, "nonfinite_interaction_values", -1)
        ),
        scan=scan,
        warnings=list(warnings),
        errors=list(errors),
        output_json=str(output_json),
        output_html=str(output_html),
    )


def render_html(report: PivotImageTensorHealthReport) -> str:
    errors = "".join(f"<li>{html.escape(item)}</li>" for item in report.errors) or "<li>None</li>"
    warnings = (
        "".join(f"<li>{html.escape(item)}</li>" for item in report.warnings) or "<li>None</li>"
    )
    tone = "#22c55e" if report.status == "PASS" else "#ef4444"
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>Pivot image tensor health</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:20px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
.status {{ color:{tone}; font-size:28px; font-weight:800; }}
</style></head><body><main>
<section class="hero"><h1>Phase143A — Pivot Image Tensor Health</h1><p class="status">{report.status}</p>
<div class="grid">
<div class="metric"><span>Tensor shape</span><strong>{report.tensor_shape}</strong></div>
<div class="metric"><span>Nonfinite cells</span><strong>{report.scan.nonfinite_cells}</strong></div>
<div class="metric"><span>Max abs</span><strong>{report.scan.max_abs:.4g}</strong></div>
<div class="metric"><span>Interaction clip</span><strong>{report.interaction_clip:g}</strong></div>
</div></section>
<section class="card"><h2>Errors</h2><ul>{errors}</ul></section>
<section class="card"><h2>Warnings</h2><ul>{warnings}</ul></section>
<section class="card"><h2>Full report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    try:
        print("\n" + "=" * 74)
        print("  PHASE143A PIVOT IMAGE TENSOR HEALTH AUDIT")
        print("=" * 74)
        tensor_path, meta_path, flat_path, builder_report_path = resolve_paths(args)
        missing = [path for path in (tensor_path, meta_path, flat_path) if not path.exists()]
        if missing:
            raise RuntimeError(
                "Missing required files: " + ", ".join(str(path) for path in missing)
            )
        tensor = np.load(tensor_path, mmap_mode="r")
        with np.load(meta_path, allow_pickle=True) as loaded:
            meta = {name: loaded[name] for name in loaded.files}
        flat = pd.read_parquet(flat_path)
        builder_report = load_builder_report(builder_report_path)
        errors, warnings, scan = validate_tensor(tensor, meta, flat, builder_report, args)
        report = build_report(
            args,
            tensor_path,
            meta_path,
            flat_path,
            builder_report_path,
            tensor,
            meta,
            flat,
            errors,
            warnings,
            scan,
            output_json,
            output_html,
        )
        output_json.write_text(
            json.dumps(
                {"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        output_html.write_text(render_html(report), encoding="utf-8")
        print(f"  status      : {report.status}")
        print(f"  shape       : {report.tensor_shape}")
        print(f"  dtype       : {report.tensor_dtype}")
        print(f"  nonfinite   : {report.scan.nonfinite_cells:,}")
        print(f"  max_abs     : {report.scan.max_abs:.6g}")
        print(f"  clip        : {report.interaction_clip:g}")
        print(f"  errors      : {len(report.errors)}")
        print(f"  warnings    : {len(report.warnings)}")
        print(f"  report      : {output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0 if report.status == "PASS" else 1
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
