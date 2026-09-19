"""Phase145A: audit 3D Pivot Sequence tensor health.

This checks the owner-requested Option A tensor layout:

    stored X: [samples, window_size, features]
    Keras batch: [batch, window_size, features]

The audit is intentionally research/diagnostic only. It verifies structural
alignment, metadata integrity, finite target/scaler arrays, and optionally scans
all tensor cells chunk-by-chunk without loading the full tensor into RAM.
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
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_tensor_health")

TARGET_ARRAYS = (
    "target_action",
    "target_top_zone",
    "target_bottom_zone",
    "target_buy_r",
    "target_sell_r",
)
SCALER_ARRAYS = ("feature_center", "feature_scale")
ACTION_NAMES = {0: "SELL", 1: "HOLD", 2: "BUY"}


@dataclass(frozen=True)
class TensorScanSummary:
    scanned_cells: int
    nonfinite_cells: int
    min_value: float
    max_value: float
    max_abs: float
    chunks: int


@dataclass(frozen=True)
class PivotSequenceTensorHealthReport:
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
    features: int
    keras_batch_shape: str
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
    feature_count: int
    generated_5m_feature_count: int
    source_5m_feature_count: int
    session_feature_count: int
    htf_feature_count: int
    other_feature_count: int
    source_5m_feature_path: str
    source_5m_numeric_candidate_count: int
    feature_names_preview: list[str]
    feature_groups_preview: list[str]
    axis_normalization: str
    feature_clip: float
    reported_nonfinite_feature_values: int
    scan: TensorScanSummary
    warnings: list[str]
    errors: list[str]
    output_json: str
    output_html: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Phase145A [samples, window, features] sequence tensor health.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument(
        "--builder-report", default="run_logs/pivot_pattern_sequence_tensor/latest.json"
    )
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--full-scan", choices=("0", "1"), default="1")
    parser.add_argument("--max-scan-samples", type=int, default=0)
    parser.add_argument("--fail-on-reported-feature-nonfinite", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def default_tensor_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "pivot_pattern_sequence_tensor_latest.npy"


def default_meta_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_sequence_tensor_latest_meta.npz"
    )


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_sequence_flat_latest.parquet"
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


def load_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Sequence tensor metadata not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def load_builder_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def scalar_from_meta(meta: Mapping[str, Any], key: str, default: float | str | int) -> Any:
    if key not in meta:
        return default
    value = meta[key]
    array = np.asarray(value)
    if array.size == 0:
        return default
    item = array.reshape(-1)[0]
    return item.item() if hasattr(item, "item") else item


def object_list(meta: Mapping[str, Any], key: str) -> list[str]:
    if key not in meta:
        return []
    return [str(value) for value in np.asarray(meta[key], dtype=object).tolist()]


def target_counts(values: Sequence[int] | np.ndarray) -> dict[str, int]:
    y = np.asarray(values, dtype=np.int64)
    return {name: int(np.sum(y == code)) for code, name in ACTION_NAMES.items()}


def scan_tensor(
    tensor: np.ndarray, chunk_size: int, full_scan: str, max_scan_samples: int
) -> TensorScanSummary:
    rows = int(tensor.shape[0])
    if full_scan != "1":
        rows = min(rows, max(max_scan_samples, 1)) if max_scan_samples > 0 else min(rows, chunk_size)
    elif max_scan_samples > 0:
        rows = min(rows, max_scan_samples)
    scanned_cells = 0
    nonfinite = 0
    min_value = np.inf
    max_value = -np.inf
    max_abs = 0.0
    chunks = 0
    step = max(int(chunk_size), 1)
    for start in range(0, rows, step):
        end = min(rows, start + step)
        batch = np.asarray(tensor[start:end])
        chunks += 1
        scanned_cells += int(batch.size)
        finite_mask = np.isfinite(batch)
        nonfinite += int(batch.size - int(finite_mask.sum()))
        if finite_mask.any():
            finite = batch[finite_mask].astype(np.float32, copy=False)
            min_value = min(min_value, float(np.min(finite)))
            max_value = max(max_value, float(np.max(finite)))
            max_abs = max(max_abs, float(np.max(np.abs(finite))))
    if not np.isfinite(min_value):
        min_value = 0.0
    if not np.isfinite(max_value):
        max_value = 0.0
    return TensorScanSummary(
        scanned_cells=int(scanned_cells),
        nonfinite_cells=int(nonfinite),
        min_value=float(min_value),
        max_value=float(max_value),
        max_abs=float(max_abs),
        chunks=int(chunks),
    )


def group_counts(groups: Sequence[str]) -> dict[str, int]:
    values = [str(group) for group in groups]
    return {
        "generated_5m": sum(1 for group in values if group == "generated_5m"),
        "source_5m": sum(1 for group in values if group == "source_5m"),
        "session": sum(1 for group in values if group == "session"),
        "htf": sum(1 for group in values if group in {"closed_4h", "closed_1d"}),
        "other": sum(
            1
            for group in values
            if group
            not in {"generated_5m", "source_5m", "session", "closed_4h", "closed_1d"}
        ),
    }


def validate_tensor(
    tensor: np.ndarray,
    meta: Mapping[str, Any],
    flat: pd.DataFrame,
    builder_report: Mapping[str, Any],
    args: argparse.Namespace,
) -> tuple[list[str], list[str], TensorScanSummary]:
    errors: list[str] = []
    warnings: list[str] = []
    if tensor.ndim != 3:
        errors.append(f"Tensor rank must be 3 for Option A; got shape={list(tensor.shape)}")
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
    feature_names = object_list(meta, "feature_names")
    feature_groups = object_list(meta, "feature_groups")
    if tensor.ndim >= 3 and feature_names and len(feature_names) != int(tensor.shape[2]):
        errors.append("feature_names length does not match tensor feature axis")
    if feature_groups and len(feature_groups) != len(feature_names):
        errors.append("feature_groups length does not match feature_names length")
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
            errors.append(f"Missing feature scaler metadata: {scaler}")
            continue
        values = np.asarray(meta[scaler], dtype=np.float32)
        if not np.isfinite(values).all():
            errors.append(f"{scaler} contains NaN/Inf")
        if scaler == "feature_scale" and np.any(np.abs(values) < 1e-12):
            errors.append("feature_scale contains near-zero values")
    report_payload = builder_report.get("report", {}) if isinstance(builder_report, Mapping) else {}
    reported_nonfinite_feature = int(scalar_from_meta(meta, "nonfinite_feature_values", -1))
    if report_payload:
        report_shape = report_payload.get("stored_x_shape")
        if report_shape and list(report_shape) != [int(value) for value in tensor.shape]:
            errors.append("Tensor shape does not match builder report stored_x_shape")
        reported_nonfinite_feature = int(
            report_payload.get("nonfinite_feature_values", reported_nonfinite_feature)
        )
        if int(report_payload.get("features", tensor.shape[-1])) != int(tensor.shape[-1]):
            errors.append("Builder report feature count does not match tensor feature axis")
        source_count = int(report_payload.get("source_5m_feature_count", -1))
        if source_count >= 0 and feature_groups:
            counted_source = sum(1 for group in feature_groups if group == "source_5m")
            if source_count != counted_source:
                errors.append("source_5m_feature_count does not match feature_groups source_5m count")
    if reported_nonfinite_feature > 0:
        message = f"Builder reported nonfinite_feature_values={reported_nonfinite_feature}"
        if args.fail_on_reported_feature_nonfinite == "1":
            errors.append(message)
        else:
            warnings.append(message)
    source_path = str(scalar_from_meta(meta, "source_5m_feature_path", ""))
    source_numeric_candidates = int(scalar_from_meta(meta, "source_5m_numeric_candidate_count", -1))
    if feature_groups and sum(1 for group in feature_groups if group == "source_5m") > 0:
        if not source_path:
            warnings.append("source_5m features exist but source_5m_feature_path is empty")
        if source_numeric_candidates == 0:
            warnings.append("source_5m features exist but source_5m_numeric_candidate_count is 0")
    scan = scan_tensor(tensor, int(args.chunk_size), args.full_scan, int(args.max_scan_samples))
    if scan.nonfinite_cells != 0:
        errors.append(f"Tensor contains {scan.nonfinite_cells} NaN/Inf cells")
    feature_clip = float(scalar_from_meta(meta, "feature_clip", report_payload.get("feature_clip", 0.0)))
    if feature_clip > 0 and scan.max_abs > feature_clip + 1e-3:
        errors.append(f"Tensor max_abs={scan.max_abs:.6g} exceeds feature_clip={feature_clip:.6g}")
    return errors, warnings, scan


def build_report(
    args: argparse.Namespace,
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    builder_report_path: Path,
    tensor: np.ndarray,
    meta: Mapping[str, Any],
    flat: pd.DataFrame,
    errors: Sequence[str],
    warnings: Sequence[str],
    scan: TensorScanSummary,
    output_json: Path,
    output_html: Path,
) -> PivotSequenceTensorHealthReport:
    sample_indices = np.asarray(meta.get("sample_indices", []), dtype=np.int64)
    timestamps = pd.to_datetime(
        pd.Series(np.asarray(meta.get("timestamp", [])).astype(str)), utc=True, errors="coerce"
    )
    feature_names = object_list(meta, "feature_names")
    feature_groups = object_list(meta, "feature_groups")
    groups = group_counts(feature_groups)
    diffs = np.diff(sample_indices) if len(sample_indices) > 1 else np.asarray([], dtype=np.int64)
    target_action = np.asarray(meta.get("target_action", []), dtype=np.int64)
    return PivotSequenceTensorHealthReport(
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
        features=int(tensor.shape[2]) if tensor.ndim >= 3 else 0,
        keras_batch_shape=(
            f"[batch, {int(tensor.shape[1])}, {int(tensor.shape[2])}]"
            if tensor.ndim == 3
            else "invalid"
        ),
        flat_rows=len(flat),
        sample_indices_count=len(sample_indices),
        sample_index_min=int(sample_indices.min()) if len(sample_indices) else -1,
        sample_index_max=int(sample_indices.max()) if len(sample_indices) else -1,
        sample_index_min_step=int(diffs.min()) if len(diffs) else 0,
        sample_index_max_step=int(diffs.max()) if len(diffs) else 0,
        timestamp_count=len(timestamps),
        first_timestamp=str(timestamps.iloc[0]) if len(timestamps) else "",
        last_timestamp=str(timestamps.iloc[-1]) if len(timestamps) else "",
        target_action_counts=target_counts(target_action),
        feature_count=len(feature_names),
        generated_5m_feature_count=groups["generated_5m"],
        source_5m_feature_count=groups["source_5m"],
        session_feature_count=groups["session"],
        htf_feature_count=groups["htf"],
        other_feature_count=groups["other"],
        source_5m_feature_path=str(scalar_from_meta(meta, "source_5m_feature_path", "")),
        source_5m_numeric_candidate_count=int(
            scalar_from_meta(meta, "source_5m_numeric_candidate_count", 0)
        ),
        feature_names_preview=feature_names[:30],
        feature_groups_preview=feature_groups[:30],
        axis_normalization=str(scalar_from_meta(meta, "axis_normalization", "unknown")),
        feature_clip=float(scalar_from_meta(meta, "feature_clip", 0.0)),
        reported_nonfinite_feature_values=int(
            scalar_from_meta(meta, "nonfinite_feature_values", -1)
        ),
        scan=scan,
        warnings=list(warnings),
        errors=list(errors),
        output_json=str(output_json),
        output_html=str(output_html),
    )


def render_html(report: PivotSequenceTensorHealthReport) -> str:
    tone = "#22c55e" if report.status == "PASS" else "#ef4444"
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" />
<title>Phase145A Sequence Tensor Health</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.status {{ color:{tone}; font-size:32px; font-weight:800; direction:ltr; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
.metric {{ background:#020617; border:1px solid #334155; border-radius:14px; padding:14px; }}
.metric span {{ color:#94a3b8; display:block; }}
.metric strong {{ direction:ltr; display:block; color:#7dd3fc; font-size:20px; }}
pre,code {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:4px 8px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>Phase145A — Sequence Tensor Health Audit</h1><div class="status">{report.status}</div></section>
<section class="grid">
<div class="metric"><span>Tensor shape</span><strong>{report.tensor_shape}</strong></div>
<div class="metric"><span>Keras batch</span><strong>{html.escape(report.keras_batch_shape)}</strong></div>
<div class="metric"><span>Features</span><strong>{report.feature_count}</strong></div>
<div class="metric"><span>Source 5M features</span><strong>{report.source_5m_feature_count}</strong></div>
<div class="metric"><span>Nonfinite cells</span><strong>{report.scan.nonfinite_cells}</strong></div>
<div class="metric"><span>Max abs</span><strong>{report.scan.max_abs:.6g}</strong></div>
</section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        print("\n" + "=" * 74)
        print("  PHASE145A PIVOT SEQUENCE TENSOR HEALTH AUDIT")
        print("=" * 74)
        tensor_path, meta_path, flat_path, builder_report_path = resolve_paths(args)
        if not tensor_path.exists():
            raise RuntimeError(f"Sequence tensor not found: {tensor_path}")
        if not flat_path.exists():
            raise RuntimeError(f"Sequence flat parquet not found: {flat_path}")
        tensor = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        flat = pd.read_parquet(flat_path)
        builder_report = load_builder_report(builder_report_path)
        errors, warnings, scan = validate_tensor(tensor, meta, flat, builder_report, args)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_json = output_dir / "latest.json"
        output_html = output_dir / "latest.html"
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
            json.dumps({"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        output_html.write_text(render_html(report), encoding="utf-8")
        print(f"  status      : {report.status}")
        print(f"  shape       : {report.tensor_shape}")
        print(f"  dtype       : {report.tensor_dtype}")
        print(f"  features    : total={report.feature_count:,} source5m={report.source_5m_feature_count:,}")
        print(f"  source path : {report.source_5m_feature_path or 'none'}")
        print(f"  nonfinite   : {report.scan.nonfinite_cells:,}")
        print(f"  max_abs     : {report.scan.max_abs:.6g}")
        print(f"  clip        : {report.feature_clip:g}")
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
