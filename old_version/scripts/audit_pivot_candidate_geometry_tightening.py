"""Phase159A: pivot candidate geometry tightening audit.

Phase158A showed the current top/bottom zone definitions are far too broad
(B4 ~90% zone-event rate, B2 ~70%) and have negative expectancy. This phase
searches *live-known* candidate geometry before any model training:

* recent range window
* near-high / near-low ATR distance
* position inside recent range
* optional exclusion of rows that are both top and bottom zones
* optional recent-range-width filters

For each geometry policy it evaluates first-hit payoff scores from B4/B2-style
barriers on chronological train/validation/test splits. Research-only.
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

from audit_pivot_payoff_target_redesign import first_hit_score, resolve_atr  # noqa: E402
from train_pivot_pattern_image_cnn import selected_indices, split_indices  # noqa: E402
from train_pivot_pattern_sequence_wavenet import default_meta_path  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_candidate_geometry_tightening")
DEFAULT_TARGETS = "B4:24:1.0:0.5;B2:24:1.0:0.75"


@dataclass(frozen=True)
class PayoffTargetSpec:
    target_id: str
    lookahead_bars: int
    tp_atr: float
    sl_atr: float


@dataclass(frozen=True)
class GeometrySplitMetrics:
    split: str
    rows: int
    event_count: int
    event_rate: float
    sell_events: int
    buy_events: int
    both_zone_rows: int
    win_count: int
    win_rate: float
    mean_r: float
    sum_r: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    sell_mean_r: float
    buy_mean_r: float
    sell_win_rate: float
    buy_win_rate: float
    best_side: str


@dataclass(frozen=True)
class GeometryPolicyRow:
    policy_id: str
    target_id: str
    lookahead_bars: int
    tp_atr: float
    sl_atr: float
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    train_event_count: int
    train_event_rate: float
    train_mean_r: float
    train_profit_factor: float
    validation_event_count: int
    validation_event_rate: float
    validation_win_rate: float
    validation_mean_r: float
    validation_sum_r: float
    validation_profit_factor: float
    validation_best_side: str
    test_event_count: int
    test_event_rate: float
    test_win_rate: float
    test_mean_r: float
    test_sum_r: float
    test_profit_factor: float
    test_best_side: str
    event_mean_r_sign_flip: int
    side_preference_stable_gate: int
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    validation_score: float
    warnings: str


@dataclass(frozen=True)
class GeometryAuditReport:
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
    policies: int
    validation_pass_policies: int
    transfer_pass_policies: int
    selected_policy_id: str
    selected_target_id: str
    selected_validation_mean_r: float
    selected_test_mean_r: float
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_transfer_pass_gate: int
    top_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_grid_csv: str
    production_status: str


def parse_targets(text: str) -> list[PayoffTargetSpec]:
    targets: list[PayoffTargetSpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 4:
            raise RuntimeError("target format must be ID:lookahead:tp_atr:sl_atr")
        targets.append(
            PayoffTargetSpec(
                target_id=parts[0].upper(),
                lookahead_bars=max(int(parts[1]), 1),
                tp_atr=max(float(parts[2]), 0.01),
                sl_atr=max(float(parts[3]), 0.01),
            )
        )
    if not targets:
        raise RuntimeError("At least one payoff target spec is required")
    return targets


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip().lower()
        if not item:
            continue
        if item in {"off", "none", "0off"}:
            values.append(0.0)
        else:
            values.append(float(item))
    return values or [float(value) for value in default]


def parse_int_grid(text: str, default: Sequence[int]) -> list[int]:
    raw = str(text or "").strip()
    if not raw:
        return [int(value) for value in default]
    values: list[int] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip()
        if item:
            values.append(int(item))
    return values or [int(value) for value in default]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit tightened pivot candidate geometry before model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--targets", default=DEFAULT_TARGETS)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--recent-window-bars", default="24,48,96")
    parser.add_argument("--pivot-zone-atrs", default="0.05,0.10,0.15,0.20,0.25")
    parser.add_argument("--top-position-thresholds", default="0.85,0.90,0.95")
    parser.add_argument("--bottom-position-thresholds", default="0.15,0.10,0.05")
    parser.add_argument("--exclude-both-zones", default="1,0")
    parser.add_argument("--min-range-width-atrs", default="0,0.5,1.0")
    parser.add_argument("--max-range-width-atrs", default="0")
    parser.add_argument("--zone-logic", choices=("and", "or"), default="and")
    parser.add_argument("--same-bar-policy", choices=("stop_first", "target_first", "skip_ambiguous"), default="stop_first")
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--min-validation-events", type=int, default=50)
    parser.add_argument("--min-test-events", type=int, default=50)
    parser.add_argument("--max-validation-event-rate", type=float, default=0.35)
    parser.add_argument("--max-test-event-rate", type=float, default=0.35)
    parser.add_argument("--min-validation-mean-r", type=float, default=0.0)
    parser.add_argument("--min-test-mean-r", type=float, default=0.0)
    parser.add_argument("--score-metric", choices=("mean_r", "sum_r", "profit_factor"), default="mean_r")
    parser.add_argument("--max-policies", type=int, default=0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase159A pivot candidate geometry tightening audit")
    return parser.parse_args(argv)


def read_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"Flat file not found: {path}")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    if "timestamp" not in frame.columns and "open_time" in frame.columns:
        frame = frame.rename(columns={"open_time": "timestamp"})
    required = {"timestamp", "high", "low", "close"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"flat file is missing required columns: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    return result.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


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


def rolling_high_low(high: np.ndarray, low: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    high_roll = pd.Series(high).rolling(max(int(window), 1), min_periods=1).max().to_numpy(dtype=np.float64)
    low_roll = pd.Series(low).rolling(max(int(window), 1), min_periods=1).min().to_numpy(dtype=np.float64)
    return high_roll, low_roll


def precompute_scores(
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    target: PayoffTargetSpec,
    atr: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray]:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    buy_scores = np.zeros(len(selected_rows), dtype=np.float32)
    sell_scores = np.zeros(len(selected_rows), dtype=np.float32)
    for local, row in enumerate(selected_rows):
        row_int = int(row)
        future_start = row_int + 1
        future_end = min(len(frame), row_int + 1 + int(target.lookahead_bars))
        if future_start >= future_end:
            continue
        buy, _, _, _ = first_hit_score(
            high[future_start:future_end],
            low[future_start:future_end],
            close[future_start:future_end],
            float(close[row_int]),
            float(atr[row_int]),
            float(target.tp_atr),
            float(target.sl_atr),
            "BUY",
            str(args.same_bar_policy),
            str(args.timeout_score_mode),
        )
        sell, _, _, _ = first_hit_score(
            high[future_start:future_end],
            low[future_start:future_end],
            close[future_start:future_end],
            float(close[row_int]),
            float(atr[row_int]),
            float(target.tp_atr),
            float(target.sl_atr),
            "SELL",
            str(args.same_bar_policy),
            str(args.timeout_score_mode),
        )
        buy_scores[local] = buy
        sell_scores[local] = sell
    return buy_scores, sell_scores


def split_metrics(
    split_name: str,
    local_indices: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    both_mask: np.ndarray,
    buy_scores: np.ndarray,
    sell_scores: np.ndarray,
) -> GeometrySplitMetrics:
    idx = np.asarray(local_indices, dtype=np.int64)
    top = top_mask[idx]
    bottom = bottom_mask[idx]
    both = both_mask[idx]
    sell_values = sell_scores[idx][top]
    buy_values = buy_scores[idx][bottom]
    values = np.concatenate([sell_values, buy_values]) if len(sell_values) or len(buy_values) else np.asarray([], dtype=np.float32)
    wins = values > 0
    gross_profit = float(np.sum(values[values > 0])) if len(values) else 0.0
    gross_loss = float(abs(np.sum(values[values < 0]))) if len(values) else 0.0
    sell_wins = sell_values > 0
    buy_wins = buy_values > 0
    sell_mean = float(np.mean(sell_values)) if len(sell_values) else 0.0
    buy_mean = float(np.mean(buy_values)) if len(buy_values) else 0.0
    best = "SELL" if sell_mean > buy_mean else ("BUY" if buy_mean > sell_mean else "TIE")
    return GeometrySplitMetrics(
        split=split_name,
        rows=int(len(idx)),
        event_count=int(len(values)),
        event_rate=float(len(values) / len(idx)) if len(idx) else 0.0,
        sell_events=int(len(sell_values)),
        buy_events=int(len(buy_values)),
        both_zone_rows=int(np.sum(both)),
        win_count=int(np.sum(wins)),
        win_rate=float(np.mean(wins)) if len(values) else 0.0,
        mean_r=float(np.mean(values)) if len(values) else 0.0,
        sum_r=float(np.sum(values)) if len(values) else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        sell_mean_r=sell_mean,
        buy_mean_r=buy_mean,
        sell_win_rate=float(np.mean(sell_wins)) if len(sell_values) else 0.0,
        buy_win_rate=float(np.mean(buy_wins)) if len(buy_values) else 0.0,
        best_side=best,
    )


def sign(value: float, eps: float = 1e-9) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def sign_flip(train_value: float, validation_value: float, test_value: float) -> int:
    train_sign = sign(train_value)
    validation_sign = sign(validation_value)
    test_sign = sign(test_value)
    return int(train_sign != 0 and validation_sign == train_sign and test_sign not in {0, train_sign})


def validation_score(metrics: GeometrySplitMetrics, metric: str) -> float:
    if metric == "sum_r":
        return float(metrics.sum_r)
    if metric == "profit_factor":
        return float(metrics.profit_factor)
    return float(metrics.mean_r)


def build_policy_row(
    target: PayoffTargetSpec,
    recent_window: int,
    zone_atr: float,
    top_position: float,
    bottom_position: float,
    exclude_both: int,
    min_width: float,
    max_width: float,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    both_mask: np.ndarray,
    buy_scores: np.ndarray,
    sell_scores: np.ndarray,
    args: argparse.Namespace,
) -> GeometryPolicyRow:
    train = split_metrics("train", train_idx, top_mask, bottom_mask, both_mask, buy_scores, sell_scores)
    validation = split_metrics("validation", validation_idx, top_mask, bottom_mask, both_mask, buy_scores, sell_scores)
    test = split_metrics("test", test_idx, top_mask, bottom_mask, both_mask, buy_scores, sell_scores)
    mean_flip = sign_flip(train.mean_r, validation.mean_r, test.mean_r)
    side_stable = int(validation.best_side == test.best_side and validation.best_side != "TIE")
    validation_pass = int(
        validation.event_count >= int(args.min_validation_events)
        and validation.event_rate <= float(args.max_validation_event_rate)
        and validation.mean_r >= float(args.min_validation_mean_r)
    )
    test_pass = int(
        test.event_count >= int(args.min_test_events)
        and test.event_rate <= float(args.max_test_event_rate)
        and test.mean_r >= float(args.min_test_mean_r)
    )
    warnings: list[str] = []
    if validation.event_rate > float(args.max_validation_event_rate):
        warnings.append("validation event rate above max")
    if test.event_rate > float(args.max_test_event_rate):
        warnings.append("test event rate above max")
    if validation.mean_r < float(args.min_validation_mean_r):
        warnings.append("validation mean R below minimum")
    if test.mean_r < float(args.min_test_mean_r):
        warnings.append("test mean R below minimum")
    if not side_stable:
        warnings.append("side preference not stable")
    policy_id = (
        f"{target.target_id}|rw={recent_window}|zone={zone_atr:g}|top={top_position:g}|"
        f"bottom={bottom_position:g}|exclude_both={exclude_both}|minw={min_width:g}|maxw={max_width:g}"
    )
    return GeometryPolicyRow(
        policy_id=policy_id,
        target_id=target.target_id,
        lookahead_bars=int(target.lookahead_bars),
        tp_atr=float(target.tp_atr),
        sl_atr=float(target.sl_atr),
        recent_window_bars=int(recent_window),
        pivot_zone_atr=float(zone_atr),
        top_position_threshold=float(top_position),
        bottom_position_threshold=float(bottom_position),
        exclude_both_zones=int(exclude_both),
        min_range_width_atr=float(min_width),
        max_range_width_atr=float(max_width),
        train_event_count=int(train.event_count),
        train_event_rate=float(train.event_rate),
        train_mean_r=float(train.mean_r),
        train_profit_factor=float(train.profit_factor),
        validation_event_count=int(validation.event_count),
        validation_event_rate=float(validation.event_rate),
        validation_win_rate=float(validation.win_rate),
        validation_mean_r=float(validation.mean_r),
        validation_sum_r=float(validation.sum_r),
        validation_profit_factor=float(validation.profit_factor),
        validation_best_side=validation.best_side,
        test_event_count=int(test.event_count),
        test_event_rate=float(test.event_rate),
        test_win_rate=float(test.win_rate),
        test_mean_r=float(test.mean_r),
        test_sum_r=float(test.sum_r),
        test_profit_factor=float(test.profit_factor),
        test_best_side=test.best_side,
        event_mean_r_sign_flip=int(mean_flip),
        side_preference_stable_gate=int(side_stable),
        validation_pass_gate=validation_pass,
        test_pass_gate=test_pass,
        transfer_pass_gate=int(validation_pass and test_pass and side_stable and not mean_flip),
        validation_score=validation_score(validation, str(args.score_metric)),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )


def evaluate_policies(args: argparse.Namespace, frame: pd.DataFrame, selected_rows: np.ndarray) -> list[GeometryPolicyRow]:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    atr = resolve_atr(frame)
    train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
    recent_values = parse_int_grid(args.recent_window_bars, (24, 48, 96))
    zone_values = parse_float_grid(args.pivot_zone_atrs, (0.05, 0.10, 0.15, 0.20, 0.25))
    top_values = parse_float_grid(args.top_position_thresholds, (0.85, 0.90, 0.95))
    bottom_values = parse_float_grid(args.bottom_position_thresholds, (0.15, 0.10, 0.05))
    exclude_values = [int(value) for value in parse_int_grid(args.exclude_both_zones, (1, 0))]
    min_width_values = parse_float_grid(args.min_range_width_atrs, (0.0, 0.5, 1.0))
    max_width_values = parse_float_grid(args.max_range_width_atrs, (0.0,))
    targets = parse_targets(args.targets)
    score_cache = {
        target.target_id: precompute_scores(frame, selected_rows, target, atr, args) for target in targets
    }
    rolling_cache = {window: rolling_high_low(high, low, window) for window in recent_values}
    rows: list[GeometryPolicyRow] = []
    policy_counter = 0
    for target in targets:
        buy_scores, sell_scores = score_cache[target.target_id]
        for recent in recent_values:
            recent_high, recent_low = rolling_cache[recent]
            width = np.maximum(recent_high - recent_low, 1e-9)
            position = (close - recent_low) / width
            width_atr = width / np.maximum(atr, 1e-9)
            selected_high = recent_high[selected_rows]
            selected_low = recent_low[selected_rows]
            selected_width_atr = width_atr[selected_rows]
            selected_position = position[selected_rows]
            selected_close = close[selected_rows]
            selected_atr = atr[selected_rows]
            for zone in zone_values:
                near_top_distance = selected_high - selected_close <= float(zone) * selected_atr
                near_bottom_distance = selected_close - selected_low <= float(zone) * selected_atr
                for top_pos in top_values:
                    top_position_mask = selected_position >= float(top_pos)
                    for bottom_pos in bottom_values:
                        bottom_position_mask = selected_position <= float(bottom_pos)
                        if args.zone_logic == "or":
                            base_top = near_top_distance | top_position_mask
                            base_bottom = near_bottom_distance | bottom_position_mask
                        else:
                            base_top = near_top_distance & top_position_mask
                            base_bottom = near_bottom_distance & bottom_position_mask
                        for exclude_both in exclude_values:
                            both = base_top & base_bottom
                            top_mask = base_top.copy()
                            bottom_mask = base_bottom.copy()
                            if int(exclude_both):
                                top_mask = top_mask & ~both
                                bottom_mask = bottom_mask & ~both
                            for min_width in min_width_values:
                                width_ok_min = selected_width_atr >= float(min_width)
                                for max_width in max_width_values:
                                    width_ok = width_ok_min.copy()
                                    if float(max_width) > 0:
                                        width_ok = width_ok & (selected_width_atr <= float(max_width))
                                    final_top = top_mask & width_ok
                                    final_bottom = bottom_mask & width_ok
                                    rows.append(
                                        build_policy_row(
                                            target,
                                            recent,
                                            zone,
                                            top_pos,
                                            bottom_pos,
                                            int(exclude_both),
                                            float(min_width),
                                            float(max_width),
                                            train_idx,
                                            validation_idx,
                                            test_idx,
                                            final_top,
                                            final_bottom,
                                            both & width_ok,
                                            buy_scores,
                                            sell_scores,
                                            args,
                                        )
                                    )
                                    policy_counter += 1
                                    if int(args.max_policies) > 0 and policy_counter >= int(args.max_policies):
                                        return rows
    return rows


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


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: GeometryAuditReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['policy_id']))}</td>"
        f"<td>{float(row['validation_event_rate']):.3f}</td>"
        f"<td>{float(row['validation_mean_r']):.4f}</td>"
        f"<td>{float(row['test_event_rate']):.3f}</td>"
        f"<td>{float(row['test_mean_r']):.4f}</td>"
        f"<td>{html.escape(str(row['validation_best_side']))}</td>"
        f"<td>{html.escape(str(row['test_best_side']))}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.top_rows[:30]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1400px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase159A pivot candidate geometry tightening audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Top policies</h2><table><thead><tr><th>Policy</th><th>Val rate</th><th>Val mean R</th><th>Test rate</th><th>Test mean R</th><th>Val side</th><th>Test side</th><th>Transfer</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE159A PIVOT CANDIDATE GEOMETRY TIGHTENING AUDIT")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, meta_path = load_meta_sample_indices(args, len(frame))
        train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
        print(f"  flat rows   : {len(frame):,}")
        print(f"  sampled     : {len(selected_rows):,} ({sampled_universe})")
        rows = evaluate_policies(args, frame, selected_rows)
        ranked = sorted(
            rows,
            key=lambda row: (
                row.transfer_pass_gate,
                row.validation_pass_gate,
                row.validation_score,
                row.validation_profit_factor,
                -row.validation_event_rate,
            ),
            reverse=True,
        )
        selected = ranked[0] if ranked else None
        row_dicts = [asdict(row) for row in ranked]
        grid_csv = output_dir / "latest_grid.csv"
        write_csv(grid_csv, row_dicts)
        report = GeometryAuditReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(meta_path or ""),
            sampled_universe=sampled_universe,
            flat_rows=len(frame),
            sampled_rows=len(selected_rows),
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            policies=len(rows),
            validation_pass_policies=sum(int(row.validation_pass_gate) for row in rows),
            transfer_pass_policies=sum(int(row.transfer_pass_gate) for row in rows),
            selected_policy_id=selected.policy_id if selected else "",
            selected_target_id=selected.target_id if selected else "",
            selected_validation_mean_r=float(selected.validation_mean_r) if selected else 0.0,
            selected_test_mean_r=float(selected.test_mean_r) if selected else 0.0,
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            top_rows=[asdict(row) for row in ranked[:50]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_grid_csv=str(grid_csv),
            production_status="BLOCKED — Phase159A geometry audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase159A geometry audit complete")
        print(f"  policies        : {report.policies}")
        print(f"  validation pass : {report.validation_pass_policies}")
        print(f"  transfer pass   : {report.transfer_pass_policies}")
        print(f"  selected policy : {report.selected_policy_id or 'none'}")
        print(f"  output          : {report.output_json}")
        print(f"  elapsed         : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
