"""Phase147C: audit Option B expanded sequence-model inputs.

The stored Phase145A tensor remains:

    X = [samples, window_size, features]

Option B may expand each grouped branch at batch time, for example:

    m5_context_input  = [batch, 100, 180]
    source_5m_input   = [batch, 100, 180]
    htf_context_input = [batch, 100, 180]

This script scans those actual training-time inputs, using the same selected
sample universe, chronological split, train-only scaler, and causal feature
augmentation settings as the trainer. It does not write a huge duplicated tensor
to disk; it builds batches exactly like training and audits them chunk by chunk.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_pivot_pattern_image_cnn import selected_indices, split_indices
from train_pivot_pattern_recognition import ACTION_NAMES
from train_pivot_pattern_sequence_wavenet import (
    compute_streaming_scaler_sequence,
    default_meta_path,
    default_tensor_path,
    load_meta,
)
from train_pivot_pattern_sequence_wavenet_option_b import grouped_batch, option_b_groups

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_option_b_input_health")
TARGET_ARRAYS = (
    "target_action",
    "target_top_zone",
    "target_bottom_zone",
    "target_buy_r",
    "target_sell_r",
)


@dataclass(frozen=True)
class BranchScan:
    scanned_cells: int
    nonfinite_cells: int
    min_value: float
    max_value: float
    max_abs: float
    chunks: int


@dataclass(frozen=True)
class OptionBInputHealthReport:
    status: str
    symbol: str
    timeframe: str
    tensor_path: str
    meta_path: str
    stored_x_shape: list[int]
    selected_x_shape: list[int]
    train_rows: int
    validation_rows: int
    test_rows: int
    raw_m5_context_features: int
    raw_source_5m_features: int
    raw_htf_context_features: int
    branch_target_features: int
    feature_augmentation_mode: str
    feature_augmentation_clip: float
    keras_input_shapes: dict[str, str]
    target_action_counts: dict[str, int]
    scaler_nonfinite_input_values: int
    scaler_mean_finite: bool
    scaler_std_finite: bool
    scanned_samples: int
    scan: dict[str, BranchScan]
    warnings: list[str]
    errors: list[str]
    output_json: str
    output_html: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Phase147C Option B expanded training-time input batches.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--stream-chunk-size", type=int, default=512)
    parser.add_argument("--scan-chunk-size", type=int, default=256)
    parser.add_argument("--full-scan", choices=("0", "1"), default="1")
    parser.add_argument("--max-scan-samples", type=int, default=0)
    parser.add_argument("--branch-target-features", type=int, default=180)
    parser.add_argument("--feature-augmentation-mode", choices=("off", "causal"), default="causal")
    parser.add_argument("--feature-augmentation-clip", type=float, default=8.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def target_counts(values: Sequence[int] | np.ndarray) -> dict[str, int]:
    y = np.asarray(values, dtype=np.int64)
    return {name: int(np.sum(y == code)) for code, name in ACTION_NAMES.items()}


def empty_scan() -> BranchScan:
    return BranchScan(
        scanned_cells=0,
        nonfinite_cells=0,
        min_value=0.0,
        max_value=0.0,
        max_abs=0.0,
        chunks=0,
    )


def update_scan(previous: BranchScan, values: np.ndarray) -> BranchScan:
    batch = np.asarray(values)
    finite_mask = np.isfinite(batch)
    nonfinite = int(batch.size - int(finite_mask.sum()))
    if finite_mask.any():
        finite = batch[finite_mask].astype(np.float32, copy=False)
        batch_min = float(np.min(finite))
        batch_max = float(np.max(finite))
        batch_abs = float(np.max(np.abs(finite)))
        if previous.scanned_cells == 0:
            min_value = batch_min
            max_value = batch_max
        else:
            min_value = min(previous.min_value, batch_min)
            max_value = max(previous.max_value, batch_max)
        max_abs = max(previous.max_abs, batch_abs)
    else:
        min_value = previous.min_value
        max_value = previous.max_value
        max_abs = previous.max_abs
    return BranchScan(
        scanned_cells=previous.scanned_cells + int(batch.size),
        nonfinite_cells=previous.nonfinite_cells + nonfinite,
        min_value=float(min_value),
        max_value=float(max_value),
        max_abs=float(max_abs),
        chunks=previous.chunks + 1,
    )


def scan_option_b_inputs(
    x_values: np.ndarray,
    rows: np.ndarray,
    groups: Any,
    mean: np.ndarray,
    std: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, BranchScan], int]:
    if args.full_scan != "1":
        limit = max(int(args.max_scan_samples), 1) if args.max_scan_samples > 0 else max(int(args.scan_chunk_size), 1)
        rows = rows[:limit]
    elif int(args.max_scan_samples) > 0:
        rows = rows[: int(args.max_scan_samples)]
    scans = {
        "m5_context_input": empty_scan(),
        "source_5m_input": empty_scan(),
        "htf_context_input": empty_scan(),
    }
    step = max(int(args.scan_chunk_size), 1)
    for start in range(0, len(rows), step):
        batch_rows = rows[start : start + step]
        batch = grouped_batch(
            np.asarray(x_values[batch_rows]),
            groups,
            mean,
            std,
            max(int(args.branch_target_features), 0),
            args.feature_augmentation_mode,
            float(args.feature_augmentation_clip),
        )
        for key, value in batch.items():
            scans[key] = update_scan(scans[key], value)
    return scans, int(len(rows))


def validate_report(report: OptionBInputHealthReport) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if len(report.stored_x_shape) != 3:
        errors.append(f"Stored sequence tensor rank must be 3; got {report.stored_x_shape}")
    if not report.scaler_mean_finite:
        errors.append("train-only scaler mean contains NaN/Inf")
    if not report.scaler_std_finite:
        errors.append("train-only scaler std contains NaN/Inf")
    if report.scaler_nonfinite_input_values > 0:
        warnings.append(
            f"raw selected training tensor had {report.scaler_nonfinite_input_values} nonfinite values before sanitization"
        )
    target = max(int(report.branch_target_features), 0)
    for name, scan in report.scan.items():
        if scan.nonfinite_cells != 0:
            errors.append(f"{name} contains {scan.nonfinite_cells} NaN/Inf cells")
        if target > 0 and not report.keras_input_shapes[name].endswith(f", {target}]"):
            errors.append(f"{name} shape does not end with target feature count {target}")
        if report.feature_augmentation_clip > 0 and scan.max_abs > report.feature_augmentation_clip + 1e-3:
            errors.append(
                f"{name} max_abs={scan.max_abs:.6g} exceeds feature_augmentation_clip={report.feature_augmentation_clip:.6g}"
            )
    if report.raw_source_5m_features <= 0:
        warnings.append("source_5m branch is empty; Option B would fall back to all features")
    return errors, warnings


def render_html(report: OptionBInputHealthReport) -> str:
    tone = "#22c55e" if report.status == "PASS" else "#ef4444"
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" />
<title>Phase147C Option B Input Health</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.status {{ color:{tone}; font-size:32px; font-weight:800; direction:ltr; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:20px; }}
pre,code {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:4px 8px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>Phase147C — Option B 180-channel Input Health</h1><div class="status">{report.status}</div></section>
<section class="grid">
<div class="metric"><span>Stored X</span><strong>{report.stored_x_shape}</strong></div>
<div class="metric"><span>m5 input</span><strong>{html.escape(report.keras_input_shapes['m5_context_input'])}</strong></div>
<div class="metric"><span>source input</span><strong>{html.escape(report.keras_input_shapes['source_5m_input'])}</strong></div>
<div class="metric"><span>HTF input</span><strong>{html.escape(report.keras_input_shapes['htf_context_input'])}</strong></div>
<div class="metric"><span>Scanned samples</span><strong>{report.scanned_samples}</strong></div>
<div class="metric"><span>Errors</span><strong>{len(report.errors)}</strong></div>
</section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    meta_path = (
        Path(args.meta_path)
        if args.meta_path
        else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    try:
        print("\n" + "=" * 74)
        print("  PHASE147C OPTION B INPUT HEALTH AUDIT")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        groups = option_b_groups(meta)
        selected_rows = selected_indices(len(x_all), int(args.max_samples))
        train_idx, validation_idx, test_idx = split_indices(
            len(selected_rows), args.train_frac, args.val_frac, args.purge_gap
        )
        mean, std, scaler_nonfinite = compute_streaming_scaler_sequence(
            x_all, selected_rows[train_idx], int(args.stream_chunk_size)
        )
        scan, scanned = scan_option_b_inputs(x_all, selected_rows, groups, mean, std, args)
        branch_target = max(int(args.branch_target_features), 0)
        m5_count = branch_target if branch_target > 0 else len(groups.m5_context)
        source_count = branch_target if branch_target > 0 else len(groups.source_5m)
        htf_count = branch_target if branch_target > 0 else len(groups.htf_context)
        target_action = np.asarray(meta.get("target_action", []), dtype=np.int64)[selected_rows]
        draft = OptionBInputHealthReport(
            status="PENDING",
            symbol=args.symbol,
            timeframe=args.timeframe,
            tensor_path=str(tensor_path),
            meta_path=str(meta_path),
            stored_x_shape=[int(value) for value in x_all.shape],
            selected_x_shape=[int(len(selected_rows)), int(x_all.shape[1]), int(x_all.shape[2])],
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            raw_m5_context_features=len(groups.m5_context),
            raw_source_5m_features=len(groups.source_5m),
            raw_htf_context_features=len(groups.htf_context),
            branch_target_features=int(args.branch_target_features),
            feature_augmentation_mode=args.feature_augmentation_mode,
            feature_augmentation_clip=float(args.feature_augmentation_clip),
            keras_input_shapes={
                "m5_context_input": f"[batch, {int(x_all.shape[1])}, {m5_count}]",
                "source_5m_input": f"[batch, {int(x_all.shape[1])}, {source_count}]",
                "htf_context_input": f"[batch, {int(x_all.shape[1])}, {htf_count}]",
            },
            target_action_counts=target_counts(target_action),
            scaler_nonfinite_input_values=int(scaler_nonfinite),
            scaler_mean_finite=bool(np.isfinite(mean).all()),
            scaler_std_finite=bool(np.isfinite(std).all()),
            scanned_samples=scanned,
            scan=scan,
            warnings=[],
            errors=[],
            output_json=str(output_json),
            output_html=str(output_html),
            production_status="BLOCKED — research Option B input audit only",
        )
        errors, warnings = validate_report(draft)
        report = OptionBInputHealthReport(
            **{**asdict(draft), "status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}
        )
        output_json.write_text(
            json.dumps({"args": vars(args), "report": asdict(report)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        output_html.write_text(render_html(report), encoding="utf-8")
        print(f"  status      : {report.status}")
        print(f"  stored X    : {report.stored_x_shape}")
        print(f"  inputs      : {report.keras_input_shapes}")
        print(f"  scanned     : {report.scanned_samples:,}")
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
