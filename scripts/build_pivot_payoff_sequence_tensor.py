"""Phase155A: build a sequence tensor for first-hit payoff pivot targets.

This builder keeps the Phase145A feature universe and tensor layout:

    stored X: [samples, window_size, features]

but replaces the old top/bottom future-extrema target with a Phase154A
first-hit/barrier trade-outcome target. It is research-only.
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

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_pivot_payoff_target_redesign import PayoffCandidate, apply_payoff_candidate  # noqa: E402
from build_pivot_pattern_sequence_tensor import (  # noqa: E402
    DEFAULT_STORAGE,
    DTYPE_CHOICES,
    SourceFeatureRead,
    build_sequence_tensor_memmap,
    classify_feature_group,
    estimate_mb,
    feature_matrix,
    merge_source_features,
    read_source_5m_frame,
    sample_indices,
)
from train_pivot_pattern_recognition import (  # noqa: E402
    build_feature_frame,
    class_counts,
    load_market_data,
)

DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_payoff_sequence_tensor")


@dataclass(frozen=True)
class PayoffSequenceTensorReport:
    source_mode: str
    symbol: str
    timeframe: str
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
    payoff_candidate: dict[str, object]
    target_counts: dict[str, int]
    actionable_rate: float
    buy_score_mean: float
    sell_score_mean: float
    selected_trade_r_mean: float
    selected_trade_win_rate: float
    feature_names_preview: list[str]
    output_tensor: str
    output_meta: str
    output_flat: str
    output_json: str
    output_html: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Phase155A sequence tensor with first-hit payoff pivot targets.",
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
    parser.add_argument("--candidate-id", default="B4")
    parser.add_argument("--candidate-label", default="asym_24_tp1_sl05")
    parser.add_argument("--lookahead-bars", type=int, default=24)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.35)
    parser.add_argument("--tp-atr", type=float, default=1.0)
    parser.add_argument("--sl-atr", type=float, default=0.5)
    parser.add_argument("--min-score-edge", type=float, default=0.1)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "target_first", "skip_ambiguous"), default="stop_first")
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all rolling samples")
    parser.add_argument("--include-source-5m-features", choices=("0", "1"), default="1")
    parser.add_argument("--source-5m-feature-path", nargs="?", const="", default="")
    parser.add_argument("--max-features", type=int, default=0, help="0 = keep every selected feature")
    parser.add_argument("--dtype", choices=DTYPE_CHOICES, default="float16")
    parser.add_argument("--axis-normalization", choices=("robust", "standard", "none"), default="robust")
    parser.add_argument("--feature-clip", type=float, default=8.0)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--max-tensor-mb", type=float, default=8192.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-name", default="pivot_payoff_sequence_tensor_b4_latest")
    return parser.parse_args(argv)


def output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.five_timeframe.upper()
    root.mkdir(parents=True, exist_ok=True)
    tensor_path = root / f"{args.output_name}.npy"
    meta_path = root / f"{args.output_name}_meta.npz"
    flat_path = root / f"{args.output_name.replace('sequence_tensor', 'sequence_flat')}.parquet"
    output_dir = Path(args.output_dir)
    return tensor_path, meta_path, flat_path, output_dir / "latest.json", output_dir / "latest.html"


def payoff_candidate_from_args(args: argparse.Namespace) -> PayoffCandidate:
    return PayoffCandidate(
        candidate_id=str(args.candidate_id).upper() or "B4",
        label=str(args.candidate_label).strip() or "payoff",
        lookahead_bars=max(int(args.lookahead_bars), 1),
        pivot_zone_atr=max(float(args.pivot_zone_atr), 0.01),
        tp_atr=max(float(args.tp_atr), 0.01),
        sl_atr=max(float(args.sl_atr), 0.01),
        min_score_edge=max(float(args.min_score_edge), 0.0),
    )


def build_report(
    args: argparse.Namespace,
    candidate: PayoffCandidate,
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
) -> PayoffSequenceTensorReport:
    actions = frame["target_action"].astype(int).to_numpy()
    actionable = frame[actions != 1]
    return PayoffSequenceTensorReport(
        source_mode=str(args.source_mode),
        symbol=str(args.symbol),
        timeframe=str(args.five_timeframe).upper(),
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
        dtype=str(args.dtype),
        estimated_uncompressed_mb=estimate_mb(
            int(tensor_shape[0]), int(tensor_shape[1]), int(tensor_shape[2]), args.dtype
        ),
        sample_stride=max(int(args.sample_stride), 1),
        axis_normalization=str(args.axis_normalization),
        feature_clip=float(args.feature_clip),
        nonfinite_feature_values=int(nonfinite_feature_values),
        generated_feature_count=int(generated_feature_count),
        source_5m_feature_count=int(source_5m_feature_count),
        source_5m_feature_path=str(source_read.path),
        source_5m_total_columns=int(source_read.total_columns),
        source_5m_numeric_candidate_count=int(source_read.numeric_candidate_count),
        payoff_candidate=asdict(candidate),
        target_counts=class_counts(frame["target_action"].astype(int)),
        actionable_rate=float(np.mean(actions != 1)) if len(actions) else 0.0,
        buy_score_mean=float(frame["target_buy_trade_r"].mean()) if len(frame) else 0.0,
        sell_score_mean=float(frame["target_sell_trade_r"].mean()) if len(frame) else 0.0,
        selected_trade_r_mean=float(actionable["target_trade_r"].mean()) if len(actionable) else 0.0,
        selected_trade_win_rate=float(actionable["target_trade_win"].mean()) if len(actionable) else 0.0,
        feature_names_preview=list(feature_names[:30]),
        output_tensor=str(tensor_path),
        output_meta=str(meta_path),
        output_flat=str(flat_path),
        output_json=str(json_path),
        output_html=str(html_path),
        production_status="BLOCKED — Phase155A payoff target tensor build only",
    )


def render_html(report: PayoffSequenceTensorReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>Phase155A Payoff Sequence Tensor</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>Phase155A — Payoff Sequence Tensor</h1><p>First-hit payoff target tensor. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    try:
        print("\n" + "=" * 74)
        print("  PHASE155A BUILD PAYOFF-TARGET SEQUENCE TENSOR")
        print("=" * 74)
        daily, h4, five, data_note = load_market_data(args)
        frame, generated_features = build_feature_frame(daily, h4, five)
        source_read = read_source_5m_frame(args)
        frame, source_features = merge_source_features(frame, source_read.frame)
        feature_names = [*generated_features, *source_features]
        if args.max_features > 0:
            feature_names = feature_names[: int(args.max_features)]
        candidate = payoff_candidate_from_args(args)
        frame = apply_payoff_candidate(
            frame,
            candidate,
            max(int(args.recent_window_bars), 1),
            str(args.same_bar_policy),
            str(args.timeout_score_mode),
        )
        frame = frame[frame["target_available"] >= 0.5].copy().reset_index(drop=True)
        frame["target_buy_r"] = np.clip(
            frame["target_buy_trade_r"].to_numpy(dtype=np.float32), -3.0, 3.0
        ).astype(np.float32)
        frame["target_sell_r"] = np.clip(
            frame["target_sell_trade_r"].to_numpy(dtype=np.float32), -3.0, 3.0
        ).astype(np.float32)
        frame["future_up_r"] = np.clip(
            np.maximum(frame["target_buy_trade_r"].to_numpy(dtype=np.float32), 0.0), 0.0, 3.0
        ).astype(np.float32)
        frame["future_down_r"] = np.clip(
            np.maximum(frame["target_sell_trade_r"].to_numpy(dtype=np.float32), 0.0), 0.0, 3.0
        ).astype(np.float32)
        values, center, scale, nonfinite = feature_matrix(frame, feature_names, args)
        indices = sample_indices(
            len(frame), int(args.window_size), int(args.sample_stride), int(args.max_samples)
        )
        estimated = estimate_mb(len(indices), int(args.window_size), len(feature_names), args.dtype)
        if estimated > float(args.max_tensor_mb):
            raise RuntimeError(
                f"Estimated tensor size {estimated:.1f} MB exceeds --max-tensor-mb {args.max_tensor_mb}."
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
            target_trade_r=frame["target_trade_r"].to_numpy(dtype=np.float32)[indices],
            target_trade_win=frame["target_trade_win"].to_numpy(dtype=np.float32)[indices],
            target_buy_trade_r=frame["target_buy_trade_r"].to_numpy(dtype=np.float32)[indices],
            target_sell_trade_r=frame["target_sell_trade_r"].to_numpy(dtype=np.float32)[indices],
            feature_names=np.asarray(feature_names, dtype=object),
            feature_groups=np.asarray([classify_feature_group(name) for name in feature_names], dtype=object),
            source_5m_feature_path=np.asarray([source_read.path], dtype=object),
            source_5m_total_columns=np.asarray([source_read.total_columns], dtype=np.int64),
            source_5m_numeric_candidate_count=np.asarray([source_read.numeric_candidate_count], dtype=np.int64),
            feature_center=center.astype(np.float32),
            feature_scale=scale.astype(np.float32),
            axis_normalization=np.asarray([args.axis_normalization], dtype=object),
            feature_clip=np.asarray([float(args.feature_clip)], dtype=np.float32),
            nonfinite_feature_values=np.asarray([int(nonfinite)], dtype=np.int64),
            window_size=np.asarray([int(args.window_size)], dtype=np.int32),
            tensor_layout=np.asarray(["[samples, window_size, features]"], dtype=object),
            target_mode=np.asarray(["first_hit_payoff"], dtype=object),
            payoff_candidate_id=np.asarray([candidate.candidate_id], dtype=object),
            payoff_candidate_label=np.asarray([candidate.label], dtype=object),
            payoff_lookahead_bars=np.asarray([candidate.lookahead_bars], dtype=np.int32),
            payoff_pivot_zone_atr=np.asarray([candidate.pivot_zone_atr], dtype=np.float32),
            payoff_tp_atr=np.asarray([candidate.tp_atr], dtype=np.float32),
            payoff_sl_atr=np.asarray([candidate.sl_atr], dtype=np.float32),
            payoff_min_score_edge=np.asarray([candidate.min_score_edge], dtype=np.float32),
            payoff_same_bar_policy=np.asarray([str(args.same_bar_policy)], dtype=object),
            payoff_timeout_score_mode=np.asarray([str(args.timeout_score_mode)], dtype=object),
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        report = build_report(
            args,
            candidate,
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
        json_path.write_text(
            json.dumps(
                {
                    "args": vars(args),
                    "payoff_candidate": asdict(candidate),
                    "report": asdict(report),
                    "files": {
                        "tensor_npy": str(tensor_path),
                        "meta_npz": str(meta_path),
                        "flat": str(flat_path),
                        "json": str(json_path),
                        "html": str(html_path),
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        html_path.write_text(render_html(report), encoding="utf-8")
        print(f"  candidate   : {candidate.candidate_id} {candidate.label}")
        print(f"  X shape     : {report.stored_x_shape}")
        print(f"  features    : {report.features:,} source5m={report.source_5m_feature_count:,}")
        print(f"  targets     : {report.target_counts}")
        print(f"  actionable  : {report.actionable_rate:.2%}")
        print(f"  tensor      : {tensor_path}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
