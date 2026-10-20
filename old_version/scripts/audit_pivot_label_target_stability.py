"""Phase152A: pivot label / target stability audit.

This diagnostic answers whether the pivot targets themselves are stable across
chronological train/validation/test regimes before more model training is done.
It consumes the existing pivot sequence flat parquet and optional tensor meta so
it audits the exact sampled universe used by the sequence models.

Research-only. No paper/live approval.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
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
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_pivot_pattern_sequence_tensor import target_buy_r, target_sell_r  # noqa: E402
from train_pivot_pattern_image_cnn import selected_indices, split_indices  # noqa: E402
from train_pivot_pattern_recognition import (  # noqa: E402
    ACTION_BUY,
    ACTION_HOLD,
    ACTION_NAMES,
    ACTION_SELL,
    PivotLabelConfig,
    class_counts,
    label_pivot_targets,
)
from train_pivot_pattern_sequence_wavenet import default_meta_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_label_target_stability")


@dataclass(frozen=True)
class SplitStabilityRow:
    split: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    sell_count: int
    hold_count: int
    buy_count: int
    sell_rate: float
    hold_rate: float
    buy_rate: float
    top_zone_rate: float
    bottom_zone_rate: float
    future_up_r_mean: float
    future_down_r_mean: float
    future_up_r_std: float
    future_down_r_std: float
    buy_r_mean: float
    sell_r_mean: float
    buy_r_positive_rate: float
    sell_r_positive_rate: float
    action_psi_vs_train: float
    buy_r_mean_delta_vs_train: float
    sell_r_mean_delta_vs_train: float


@dataclass(frozen=True)
class MonthStabilityRow:
    month: str
    split: str
    rows: int
    sell_count: int
    hold_count: int
    buy_count: int
    sell_rate: float
    hold_rate: float
    buy_rate: float
    top_zone_rate: float
    bottom_zone_rate: float
    future_up_r_mean: float
    future_down_r_mean: float
    buy_r_mean: float
    sell_r_mean: float
    action_psi_vs_train: float


@dataclass(frozen=True)
class SensitivityRow:
    lookahead_bars: int
    pivot_move_atr: float
    pivot_zone_atr: float
    min_direction_edge: float
    sampled_rows: int
    train_sell_rate: float
    train_hold_rate: float
    train_buy_rate: float
    validation_sell_rate: float
    validation_hold_rate: float
    validation_buy_rate: float
    test_sell_rate: float
    test_hold_rate: float
    test_buy_rate: float
    validation_psi_vs_train: float
    test_psi_vs_train: float
    train_actionable_rate: float
    validation_actionable_rate: float
    test_actionable_rate: float
    train_buy_r_mean: float
    validation_buy_r_mean: float
    test_buy_r_mean: float
    train_sell_r_mean: float
    validation_sell_r_mean: float
    test_sell_r_mean: float
    drift_score: float


@dataclass(frozen=True)
class StabilityReport:
    symbol: str
    timeframe: str
    flat_path: str
    meta_path: str
    sampled_universe: str
    flat_rows: int
    sampled_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    first_timestamp: str
    last_timestamp: str
    current_label_config: dict[str, Any]
    current_target_counts: dict[str, int]
    train_action_distribution: dict[str, float]
    validation_action_distribution: dict[str, float]
    test_action_distribution: dict[str, float]
    validation_psi_vs_train: float
    test_psi_vs_train: float
    max_monthly_psi_vs_train: float
    worst_month_by_psi: str
    warnings: list[str]
    top_sensitivity_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_split_csv: str
    output_monthly_csv: str
    output_sensitivity_csv: str
    production_status: str


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            values.append(float(item))
    return values or [float(value) for value in default]


def parse_int_grid(text: str, default: Sequence[int]) -> list[int]:
    raw = str(text or "").strip()
    if not raw:
        return [int(value) for value in default]
    values: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            values.append(int(item))
    return values or [int(value) for value in default]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit pivot label/target stability across train/validation/test.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--lookahead-bars", type=int, default=48)
    parser.add_argument("--pivot-move-atr", type=float, default=0.75)
    parser.add_argument("--pivot-zone-atr", type=float, default=0.35)
    parser.add_argument("--recent-window-bars", type=int, default=48)
    parser.add_argument("--min-direction-edge", type=float, default=1.10)
    parser.add_argument("--sensitivity-lookahead-bars", default="24,48,72")
    parser.add_argument("--sensitivity-pivot-move-atrs", default="0.5,0.75,1.0")
    parser.add_argument("--sensitivity-pivot-zone-atrs", default="0.25,0.35,0.5")
    parser.add_argument("--sensitivity-min-direction-edges", default="1.0,1.1,1.25")
    parser.add_argument("--max-sensitivity-combinations", type=int, default=40)
    parser.add_argument("--psi-warning-threshold", type=float, default=0.20)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase152A pivot label target stability audit")
    return parser.parse_args(argv)


def read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Flat input file not found: {path}")
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        frame = pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    if "timestamp" not in frame.columns:
        raise RuntimeError("flat file must include timestamp/open_time")
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    if "target_buy_r" not in frame.columns and {"future_up_r", "future_down_r"}.issubset(frame.columns):
        frame["target_buy_r"] = target_buy_r(frame)
    if "target_sell_r" not in frame.columns and {"future_up_r", "future_down_r"}.issubset(frame.columns):
        frame["target_sell_r"] = target_sell_r(frame)
    return frame


def load_meta_sample_indices(args: argparse.Namespace, flat_rows: int) -> tuple[np.ndarray, str, Path | None]:
    meta_path = Path(args.meta_path) if str(args.meta_path).strip() else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    if meta_path.exists():
        with np.load(meta_path, allow_pickle=True) as meta:
            if "sample_indices" in meta.files:
                sample_indices = np.asarray(meta["sample_indices"], dtype=np.int64)
                selected_tensor_rows = selected_indices(len(sample_indices), int(args.max_samples))
                selected_flat_rows = sample_indices[selected_tensor_rows]
                selected_flat_rows = selected_flat_rows[(selected_flat_rows >= 0) & (selected_flat_rows < flat_rows)]
                if len(selected_flat_rows):
                    return selected_flat_rows.astype(np.int64), "meta_sample_indices", meta_path
    start = max(int(args.window_size) - 1, 0)
    flat_positions = np.arange(start, flat_rows, dtype=np.int64)
    selected = selected_indices(len(flat_positions), int(args.max_samples))
    return flat_positions[selected].astype(np.int64), "flat_window_positions", meta_path if meta_path.exists() else None


def action_distribution(frame: pd.DataFrame) -> dict[str, float]:
    rows = max(len(frame), 1)
    actions = frame["target_action"].astype(int)
    return {
        "SELL": float(np.mean(actions == ACTION_SELL)) if len(frame) else 0.0,
        "HOLD": float(np.mean(actions == ACTION_HOLD)) if len(frame) else 0.0,
        "BUY": float(np.mean(actions == ACTION_BUY)) if len(frame) else 0.0,
        "rows": float(rows),
    }


def action_psi(current: Mapping[str, float], baseline: Mapping[str, float]) -> float:
    eps = 1e-6
    total = 0.0
    for key in ("SELL", "HOLD", "BUY"):
        actual = max(float(current.get(key, 0.0)), eps)
        expected = max(float(baseline.get(key, 0.0)), eps)
        total += (actual - expected) * float(np.log(actual / expected))
    return float(total)


def split_frames(sampled: pd.DataFrame, args: argparse.Namespace) -> dict[str, pd.DataFrame]:
    train_idx, validation_idx, test_idx = split_indices(len(sampled), args.train_frac, args.val_frac, args.purge_gap)
    return {
        "train": sampled.iloc[train_idx].copy().reset_index(drop=True),
        "validation": sampled.iloc[validation_idx].copy().reset_index(drop=True),
        "test": sampled.iloc[test_idx].copy().reset_index(drop=True),
    }


def target_counts_from_frame(frame: pd.DataFrame) -> dict[str, int]:
    if frame.empty:
        return {"SELL": 0, "HOLD": 0, "BUY": 0}
    return class_counts(frame["target_action"].astype(int))


def split_summary(name: str, frame: pd.DataFrame, train_dist: Mapping[str, float], train_ref: pd.DataFrame | None) -> SplitStabilityRow:
    rows = len(frame)
    dist = action_distribution(frame)
    train_buy_mean = float(train_ref["target_buy_r"].mean()) if train_ref is not None and len(train_ref) else 0.0
    train_sell_mean = float(train_ref["target_sell_r"].mean()) if train_ref is not None and len(train_ref) else 0.0
    return SplitStabilityRow(
        split=name,
        rows=rows,
        first_timestamp=str(frame["timestamp"].iloc[0]) if rows else "",
        last_timestamp=str(frame["timestamp"].iloc[-1]) if rows else "",
        sell_count=int((frame["target_action"].astype(int) == ACTION_SELL).sum()) if rows else 0,
        hold_count=int((frame["target_action"].astype(int) == ACTION_HOLD).sum()) if rows else 0,
        buy_count=int((frame["target_action"].astype(int) == ACTION_BUY).sum()) if rows else 0,
        sell_rate=float(dist["SELL"]),
        hold_rate=float(dist["HOLD"]),
        buy_rate=float(dist["BUY"]),
        top_zone_rate=float(frame["target_top_zone"].mean()) if rows else 0.0,
        bottom_zone_rate=float(frame["target_bottom_zone"].mean()) if rows else 0.0,
        future_up_r_mean=float(frame["future_up_r"].mean()) if rows else 0.0,
        future_down_r_mean=float(frame["future_down_r"].mean()) if rows else 0.0,
        future_up_r_std=float(frame["future_up_r"].std(ddof=0)) if rows else 0.0,
        future_down_r_std=float(frame["future_down_r"].std(ddof=0)) if rows else 0.0,
        buy_r_mean=float(frame["target_buy_r"].mean()) if rows else 0.0,
        sell_r_mean=float(frame["target_sell_r"].mean()) if rows else 0.0,
        buy_r_positive_rate=float(np.mean(frame["target_buy_r"].to_numpy(dtype=float) > 0)) if rows else 0.0,
        sell_r_positive_rate=float(np.mean(frame["target_sell_r"].to_numpy(dtype=float) > 0)) if rows else 0.0,
        action_psi_vs_train=0.0 if name == "train" else action_psi(dist, train_dist),
        buy_r_mean_delta_vs_train=(float(frame["target_buy_r"].mean()) - train_buy_mean) if rows else 0.0,
        sell_r_mean_delta_vs_train=(float(frame["target_sell_r"].mean()) - train_sell_mean) if rows else 0.0,
    )


def monthly_rows(sampled: pd.DataFrame, split_lookup: Mapping[int, str], train_dist: Mapping[str, float]) -> list[MonthStabilityRow]:
    rows: list[MonthStabilityRow] = []
    work = sampled.copy()
    work["month"] = work["timestamp"].dt.strftime("%Y-%m")
    work["split"] = [split_lookup.get(int(position), "unknown") for position in range(len(work))]
    for (month, split), group in work.groupby(["month", "split"], sort=True):
        dist = action_distribution(group)
        rows.append(
            MonthStabilityRow(
                month=str(month),
                split=str(split),
                rows=len(group),
                sell_count=int((group["target_action"].astype(int) == ACTION_SELL).sum()),
                hold_count=int((group["target_action"].astype(int) == ACTION_HOLD).sum()),
                buy_count=int((group["target_action"].astype(int) == ACTION_BUY).sum()),
                sell_rate=float(dist["SELL"]),
                hold_rate=float(dist["HOLD"]),
                buy_rate=float(dist["BUY"]),
                top_zone_rate=float(group["target_top_zone"].mean()),
                bottom_zone_rate=float(group["target_bottom_zone"].mean()),
                future_up_r_mean=float(group["future_up_r"].mean()),
                future_down_r_mean=float(group["future_down_r"].mean()),
                buy_r_mean=float(group["target_buy_r"].mean()),
                sell_r_mean=float(group["target_sell_r"].mean()),
                action_psi_vs_train=action_psi(dist, train_dist),
            )
        )
    return rows


def sensitivity_configs(args: argparse.Namespace) -> list[PivotLabelConfig]:
    lookaheads = parse_int_grid(args.sensitivity_lookahead_bars, (48,))
    moves = parse_float_grid(args.sensitivity_pivot_move_atrs, (0.75,))
    zones = parse_float_grid(args.sensitivity_pivot_zone_atrs, (0.35,))
    edges = parse_float_grid(args.sensitivity_min_direction_edges, (1.10,))
    configs: list[PivotLabelConfig] = []
    for lookahead in lookaheads:
        for move in moves:
            for zone in zones:
                for edge in edges:
                    configs.append(
                        PivotLabelConfig(
                            lookahead_bars=int(lookahead),
                            pivot_move_atr=float(move),
                            pivot_zone_atr=float(zone),
                            recent_window_bars=int(args.recent_window_bars),
                            min_direction_edge=float(edge),
                        )
                    )
    return configs[: max(int(args.max_sensitivity_combinations), 0)]


def sensitivity_row(base: pd.DataFrame, selected_rows: np.ndarray, args: argparse.Namespace, config: PivotLabelConfig) -> SensitivityRow:
    relabeled = label_pivot_targets(base, config)
    relabeled["target_buy_r"] = target_buy_r(relabeled)
    relabeled["target_sell_r"] = target_sell_r(relabeled)
    usable_rows = selected_rows[selected_rows < len(relabeled)]
    sampled = relabeled.iloc[usable_rows].copy().reset_index(drop=True)
    sampled = sampled[sampled["target_available"] >= 0.5].copy().reset_index(drop=True)
    splits = split_frames(sampled, args)
    train = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    train_dist = action_distribution(train)
    val_dist = action_distribution(validation)
    test_dist = action_distribution(test)
    val_psi = action_psi(val_dist, train_dist)
    test_psi = action_psi(test_dist, train_dist)
    train_buy_mean = float(train["target_buy_r"].mean()) if len(train) else 0.0
    val_buy_mean = float(validation["target_buy_r"].mean()) if len(validation) else 0.0
    test_buy_mean = float(test["target_buy_r"].mean()) if len(test) else 0.0
    train_sell_mean = float(train["target_sell_r"].mean()) if len(train) else 0.0
    val_sell_mean = float(validation["target_sell_r"].mean()) if len(validation) else 0.0
    test_sell_mean = float(test["target_sell_r"].mean()) if len(test) else 0.0
    drift_score = val_psi + test_psi + abs(val_buy_mean - train_buy_mean) + abs(test_buy_mean - train_buy_mean) + abs(val_sell_mean - train_sell_mean) + abs(test_sell_mean - train_sell_mean)
    return SensitivityRow(
        lookahead_bars=config.lookahead_bars,
        pivot_move_atr=float(config.pivot_move_atr),
        pivot_zone_atr=float(config.pivot_zone_atr),
        min_direction_edge=float(config.min_direction_edge),
        sampled_rows=len(sampled),
        train_sell_rate=float(train_dist["SELL"]),
        train_hold_rate=float(train_dist["HOLD"]),
        train_buy_rate=float(train_dist["BUY"]),
        validation_sell_rate=float(val_dist["SELL"]),
        validation_hold_rate=float(val_dist["HOLD"]),
        validation_buy_rate=float(val_dist["BUY"]),
        test_sell_rate=float(test_dist["SELL"]),
        test_hold_rate=float(test_dist["HOLD"]),
        test_buy_rate=float(test_dist["BUY"]),
        validation_psi_vs_train=float(val_psi),
        test_psi_vs_train=float(test_psi),
        train_actionable_rate=float(train_dist["SELL"] + train_dist["BUY"]),
        validation_actionable_rate=float(val_dist["SELL"] + val_dist["BUY"]),
        test_actionable_rate=float(test_dist["SELL"] + test_dist["BUY"]),
        train_buy_r_mean=train_buy_mean,
        validation_buy_r_mean=val_buy_mean,
        test_buy_r_mean=test_buy_mean,
        train_sell_r_mean=train_sell_mean,
        validation_sell_r_mean=val_sell_mean,
        test_sell_r_mean=test_sell_mean,
        drift_score=float(drift_score),
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: StabilityReport) -> str:
    sensitivity = "".join(
        f"<tr><td>{row.get('lookahead_bars')}</td><td>{row.get('pivot_move_atr')}</td><td>{row.get('pivot_zone_atr')}</td><td>{row.get('min_direction_edge')}</td><td>{float(row.get('drift_score', 0.0)):.4f}</td><td>{float(row.get('test_psi_vs_train', 0.0)):.4f}</td></tr>"
        for row in report.top_sensitivity_rows[:15]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase152A pivot label/target stability audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Warnings</h2><pre>{html.escape(json.dumps(report.warnings, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Summary</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Most stable sensitivity configs</h2><table><thead><tr><th>Lookahead</th><th>Move</th><th>Zone</th><th>Edge</th><th>Drift</th><th>Test PSI</th></tr></thead><tbody>{sensitivity}</tbody></table></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE152A PIVOT LABEL / TARGET STABILITY AUDIT")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, resolved_meta_path = load_meta_sample_indices(args, len(frame))
        sampled = frame.iloc[selected_rows].copy().reset_index(drop=True)
        splits = split_frames(sampled, args)
        train_dist = action_distribution(splits["train"])
        split_rows = [
            split_summary(name, split_frame, train_dist, splits["train"])
            for name, split_frame in splits.items()
        ]
        split_lookup: dict[int, str] = {}
        cursor = 0
        for name in ("train", "validation", "test"):
            count = len(splits[name])
            for local in range(cursor, cursor + count):
                split_lookup[local] = name
            cursor += count
        monthly = monthly_rows(sampled, split_lookup, train_dist)
        configs = sensitivity_configs(args)
        sensitivity = [sensitivity_row(frame, selected_rows, args, config) for config in configs]
        sensitivity_sorted = sorted(sensitivity, key=lambda row: row.drift_score)
        max_monthly_psi = max((row.action_psi_vs_train for row in monthly), default=0.0)
        worst_month = max(monthly, key=lambda row: row.action_psi_vs_train).month if monthly else ""
        validation_psi = next(row.action_psi_vs_train for row in split_rows if row.split == "validation")
        test_psi = next(row.action_psi_vs_train for row in split_rows if row.split == "test")
        warnings: list[str] = []
        if validation_psi > float(args.psi_warning_threshold):
            warnings.append(f"validation action PSI vs train is high: {validation_psi:.4f}")
        if test_psi > float(args.psi_warning_threshold):
            warnings.append(f"test action PSI vs train is high: {test_psi:.4f}")
        if max_monthly_psi > float(args.psi_warning_threshold):
            warnings.append(f"monthly action PSI exceeds threshold: {max_monthly_psi:.4f} at {worst_month}")
        train = splits["train"]
        validation = splits["validation"]
        test = splits["test"]
        if abs(float(validation["target_sell_r"].mean()) - float(train["target_sell_r"].mean())) > 0.25:
            warnings.append("validation sell_r mean materially differs from train")
        if abs(float(test["target_sell_r"].mean()) - float(train["target_sell_r"].mean())) > 0.25:
            warnings.append("test sell_r mean materially differs from train")
        if abs(float(validation["target_buy_r"].mean()) - float(train["target_buy_r"].mean())) > 0.25:
            warnings.append("validation buy_r mean materially differs from train")
        if abs(float(test["target_buy_r"].mean()) - float(train["target_buy_r"].mean())) > 0.25:
            warnings.append("test buy_r mean materially differs from train")
        split_csv = output_dir / "latest_splits.csv"
        monthly_csv = output_dir / "latest_monthly.csv"
        sensitivity_csv = output_dir / "latest_sensitivity.csv"
        write_csv(split_csv, [asdict(row) for row in split_rows])
        write_csv(monthly_csv, [asdict(row) for row in monthly])
        write_csv(sensitivity_csv, [asdict(row) for row in sensitivity_sorted])
        report = StabilityReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(resolved_meta_path or ""),
            sampled_universe=sampled_universe,
            flat_rows=len(frame),
            sampled_rows=len(sampled),
            train_rows=len(train),
            validation_rows=len(validation),
            test_rows=len(test),
            first_timestamp=str(sampled["timestamp"].iloc[0]) if len(sampled) else "",
            last_timestamp=str(sampled["timestamp"].iloc[-1]) if len(sampled) else "",
            current_label_config=asdict(
                PivotLabelConfig(
                    lookahead_bars=int(args.lookahead_bars),
                    pivot_move_atr=float(args.pivot_move_atr),
                    pivot_zone_atr=float(args.pivot_zone_atr),
                    recent_window_bars=int(args.recent_window_bars),
                    min_direction_edge=float(args.min_direction_edge),
                )
            ),
            current_target_counts=target_counts_from_frame(sampled),
            train_action_distribution={key: value for key, value in train_dist.items() if key != "rows"},
            validation_action_distribution={key: value for key, value in action_distribution(validation).items() if key != "rows"},
            test_action_distribution={key: value for key, value in action_distribution(test).items() if key != "rows"},
            validation_psi_vs_train=float(validation_psi),
            test_psi_vs_train=float(test_psi),
            max_monthly_psi_vs_train=float(max_monthly_psi),
            worst_month_by_psi=str(worst_month),
            warnings=warnings,
            top_sensitivity_rows=[asdict(row) for row in sensitivity_sorted[:20]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_split_csv=str(split_csv),
            output_monthly_csv=str(monthly_csv),
            output_sensitivity_csv=str(sensitivity_csv),
            production_status="BLOCKED — research label stability audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print(f"  flat rows   : {len(frame):,}")
        print(f"  sampled     : {len(sampled):,} ({sampled_universe})")
        print(f"  splits      : train={len(train):,} validation={len(validation):,} test={len(test):,}")
        print(f"  val/test PSI: {validation_psi:.4f} / {test_psi:.4f}")
        print(f"  warnings    : {len(warnings)}")
        print(f"  output      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
