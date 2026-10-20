"""Phase160A: pivot candidate side-mapping / counterfactual direction audit.

Phase159A tightened pivot candidate geometry but the reversal-style mapping still
had negative expectancy. This phase keeps the live-known geometry and audits
counterfactual side mappings without training:

* reversal: top -> SELL, bottom -> BUY
* breakout: top -> BUY, bottom -> SELL
* top-only and bottom-only variants
* all-buy/all-sell stress controls
* optional entry delays

Policy selection is validation-only; test is confirmation-only. Research-only.
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

from audit_pivot_candidate_geometry_tightening import (  # noqa: E402
    PayoffTargetSpec,
    load_meta_sample_indices,
    parse_targets,
    read_frame,
    rolling_high_low,
    sign_flip,
    validation_score,
)
from audit_pivot_payoff_target_redesign import first_hit_score, resolve_atr  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_candidate_side_mapping")
DEFAULT_GEOMETRY_GRID = Path("run_logs/pivot_candidate_geometry_tightening/latest_grid.csv")
SIDE_SELL = "SELL"
SIDE_BUY = "BUY"


@dataclass(frozen=True)
class GeometryPolicy:
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


@dataclass(frozen=True)
class MappingMetrics:
    split: str
    events: int
    event_rate: float
    wins: int
    losses: int
    win_rate: float
    mean_r: float
    sum_r: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    top_events: int
    bottom_events: int
    sell_events: int
    buy_events: int
    sell_mean_r: float
    buy_mean_r: float
    sell_win_rate: float
    buy_win_rate: float


@dataclass(frozen=True)
class SideMappingRow:
    geometry_policy_id: str
    target_id: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    exclude_both_zones: int
    min_range_width_atr: float
    max_range_width_atr: float
    validation_events: int
    validation_event_rate: float
    validation_win_rate: float
    validation_mean_r: float
    validation_sum_r: float
    validation_profit_factor: float
    validation_sell_mean_r: float
    validation_buy_mean_r: float
    test_events: int
    test_event_rate: float
    test_win_rate: float
    test_mean_r: float
    test_sum_r: float
    test_profit_factor: float
    test_sell_mean_r: float
    test_buy_mean_r: float
    mean_r_sign_flip: int
    validation_pass_gate: int
    test_pass_gate: int
    transfer_pass_gate: int
    validation_score: float
    warnings: str


@dataclass(frozen=True)
class SideMappingReport:
    symbol: str
    timeframe: str
    flat_path: str
    meta_path: str
    geometry_grid_path: str
    sampled_universe: str
    flat_rows: int
    sampled_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    geometry_policies_loaded: int
    evaluated_rows: int
    validation_pass_rows: int
    transfer_pass_rows: int
    selected_geometry_policy_id: str
    selected_side_mapping: str
    selected_entry_delay_bars: int
    selected_validation_mean_r: float
    selected_test_mean_r: float
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_transfer_pass_gate: int
    top_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_csv: str
    production_status: str


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
        description="Audit side mapping / direction counterfactuals for tightened pivot candidates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--geometry-grid-path", default=str(DEFAULT_GEOMETRY_GRID))
    parser.add_argument("--fallback-targets", default="B4:24:1.0:0.5;B2:24:1.0:0.75")
    parser.add_argument("--max-geometry-policies", type=int, default=30)
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--window-size", type=int, default=100)
    parser.add_argument("--side-mappings", default="reversal,breakout,top_sell,bottom_buy,top_buy,bottom_sell,all_buy,all_sell")
    parser.add_argument("--entry-delays", default="0,1,2,3")
    parser.add_argument("--same-bar-policy", choices=("stop_first", "target_first", "skip_ambiguous"), default="stop_first")
    parser.add_argument("--timeout-score-mode", choices=("zero", "close_r"), default="zero")
    parser.add_argument("--zone-logic", choices=("and", "or"), default="and")
    parser.add_argument("--min-validation-events", type=int, default=30)
    parser.add_argument("--min-test-events", type=int, default=30)
    parser.add_argument("--max-validation-event-rate", type=float, default=0.35)
    parser.add_argument("--max-test-event-rate", type=float, default=0.35)
    parser.add_argument("--min-validation-mean-r", type=float, default=0.0)
    parser.add_argument("--min-test-mean-r", type=float, default=0.0)
    parser.add_argument("--score-metric", choices=("mean_r", "sum_r", "profit_factor"), default="mean_r")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase160A pivot candidate side-mapping audit")
    return parser.parse_args(argv)


def safe_float(row: Mapping[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def safe_int(row: Mapping[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except (TypeError, ValueError):
        return int(default)


def policy_from_grid_row(row: Mapping[str, str]) -> GeometryPolicy:
    return GeometryPolicy(
        policy_id=str(row.get("policy_id", "")),
        target_id=str(row.get("target_id", "")).upper(),
        lookahead_bars=safe_int(row, "lookahead_bars", 24),
        tp_atr=safe_float(row, "tp_atr", 1.0),
        sl_atr=safe_float(row, "sl_atr", 0.75),
        recent_window_bars=safe_int(row, "recent_window_bars", 48),
        pivot_zone_atr=safe_float(row, "pivot_zone_atr", 0.05),
        top_position_threshold=safe_float(row, "top_position_threshold", 0.85),
        bottom_position_threshold=safe_float(row, "bottom_position_threshold", 0.15),
        exclude_both_zones=safe_int(row, "exclude_both_zones", 1),
        min_range_width_atr=safe_float(row, "min_range_width_atr", 0.0),
        max_range_width_atr=safe_float(row, "max_range_width_atr", 0.0),
    )


def fallback_policies(args: argparse.Namespace) -> list[GeometryPolicy]:
    policies: list[GeometryPolicy] = []
    for target in parse_targets(args.fallback_targets):
        policies.append(
            GeometryPolicy(
                policy_id=f"{target.target_id}|fallback|rw=48|zone=0.05|top=0.85|bottom=0.15|exclude_both=1|minw=1|maxw=0",
                target_id=target.target_id,
                lookahead_bars=target.lookahead_bars,
                tp_atr=target.tp_atr,
                sl_atr=target.sl_atr,
                recent_window_bars=48,
                pivot_zone_atr=0.05,
                top_position_threshold=0.85,
                bottom_position_threshold=0.15,
                exclude_both_zones=1,
                min_range_width_atr=1.0,
                max_range_width_atr=0.0,
            )
        )
    return policies


def load_geometry_policies(args: argparse.Namespace) -> list[GeometryPolicy]:
    path = Path(args.geometry_grid_path)
    if not path.exists():
        return fallback_policies(args)
    rows: list[GeometryPolicy] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(policy_from_grid_row(row))
            if int(args.max_geometry_policies) > 0 and len(rows) >= int(args.max_geometry_policies):
                break
    return rows or fallback_policies(args)


def build_geometry_masks(
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    atr: np.ndarray,
    policy: GeometryPolicy,
    zone_logic: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    recent_high, recent_low = rolling_high_low(high, low, int(policy.recent_window_bars))
    width = np.maximum(recent_high - recent_low, 1e-9)
    position = (close - recent_low) / width
    width_atr = width / np.maximum(atr, 1e-9)
    selected_high = recent_high[selected_rows]
    selected_low = recent_low[selected_rows]
    selected_close = close[selected_rows]
    selected_atr = atr[selected_rows]
    selected_position = position[selected_rows]
    selected_width_atr = width_atr[selected_rows]
    near_top_distance = selected_high - selected_close <= float(policy.pivot_zone_atr) * selected_atr
    near_bottom_distance = selected_close - selected_low <= float(policy.pivot_zone_atr) * selected_atr
    top_position = selected_position >= float(policy.top_position_threshold)
    bottom_position = selected_position <= float(policy.bottom_position_threshold)
    if zone_logic == "or":
        top = near_top_distance | top_position
        bottom = near_bottom_distance | bottom_position
    else:
        top = near_top_distance & top_position
        bottom = near_bottom_distance & bottom_position
    both = top & bottom
    if int(policy.exclude_both_zones):
        top = top & ~both
        bottom = bottom & ~both
    width_ok = selected_width_atr >= float(policy.min_range_width_atr)
    if float(policy.max_range_width_atr) > 0:
        width_ok = width_ok & (selected_width_atr <= float(policy.max_range_width_atr))
    return top & width_ok, bottom & width_ok, both & width_ok


def side_for_event(mapping: str, zone: str) -> str | None:
    if mapping == "reversal":
        return SIDE_SELL if zone == "top" else SIDE_BUY
    if mapping == "breakout":
        return SIDE_BUY if zone == "top" else SIDE_SELL
    if mapping == "top_sell":
        return SIDE_SELL if zone == "top" else None
    if mapping == "top_buy":
        return SIDE_BUY if zone == "top" else None
    if mapping == "bottom_buy":
        return SIDE_BUY if zone == "bottom" else None
    if mapping == "bottom_sell":
        return SIDE_SELL if zone == "bottom" else None
    if mapping == "all_buy":
        return SIDE_BUY
    if mapping == "all_sell":
        return SIDE_SELL
    return None


def delayed_score(
    frame: pd.DataFrame,
    row: int,
    side: str,
    target: GeometryPolicy,
    atr: np.ndarray,
    delay: int,
    args: argparse.Namespace,
) -> float | None:
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    entry_row = int(row) + max(int(delay), 0)
    if entry_row >= len(frame) - 1:
        return None
    future_start = entry_row + 1
    future_end = min(len(frame), entry_row + 1 + int(target.lookahead_bars))
    if future_start >= future_end:
        return None
    score, _, _, _ = first_hit_score(
        high[future_start:future_end],
        low[future_start:future_end],
        close[future_start:future_end],
        float(close[entry_row]),
        float(atr[entry_row]),
        float(target.tp_atr),
        float(target.sl_atr),
        side,
        str(args.same_bar_policy),
        str(args.timeout_score_mode),
    )
    return float(score)


def evaluate_mapping_split(
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    local_indices: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    policy: GeometryPolicy,
    mapping: str,
    delay: int,
    atr: np.ndarray,
    args: argparse.Namespace,
) -> MappingMetrics:
    values: list[float] = []
    zones: list[str] = []
    sides: list[str] = []
    for local in np.asarray(local_indices, dtype=np.int64):
        flat_row = int(selected_rows[int(local)])
        if top_mask[int(local)]:
            side = side_for_event(mapping, "top")
            if side is not None:
                score = delayed_score(frame, flat_row, side, policy, atr, delay, args)
                if score is not None:
                    values.append(score)
                    zones.append("top")
                    sides.append(side)
        if bottom_mask[int(local)]:
            side = side_for_event(mapping, "bottom")
            if side is not None:
                score = delayed_score(frame, flat_row, side, policy, atr, delay, args)
                if score is not None:
                    values.append(score)
                    zones.append("bottom")
                    sides.append(side)
    arr = np.asarray(values, dtype=np.float32)
    side_arr = np.asarray(sides, dtype=object)
    zone_arr = np.asarray(zones, dtype=object)
    wins = arr > 0
    gross_profit = float(np.sum(arr[arr > 0])) if len(arr) else 0.0
    gross_loss = float(abs(np.sum(arr[arr < 0]))) if len(arr) else 0.0
    sell_mask = side_arr == SIDE_SELL
    buy_mask = side_arr == SIDE_BUY
    return MappingMetrics(
        split="",
        events=int(len(arr)),
        event_rate=float(len(arr) / len(local_indices)) if len(local_indices) else 0.0,
        wins=int(np.sum(wins)),
        losses=int(np.sum(arr < 0)),
        win_rate=float(np.mean(wins)) if len(arr) else 0.0,
        mean_r=float(np.mean(arr)) if len(arr) else 0.0,
        sum_r=float(np.sum(arr)) if len(arr) else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        top_events=int(np.sum(zone_arr == "top")),
        bottom_events=int(np.sum(zone_arr == "bottom")),
        sell_events=int(np.sum(sell_mask)),
        buy_events=int(np.sum(buy_mask)),
        sell_mean_r=float(np.mean(arr[sell_mask])) if np.any(sell_mask) else 0.0,
        buy_mean_r=float(np.mean(arr[buy_mask])) if np.any(buy_mask) else 0.0,
        sell_win_rate=float(np.mean(wins[sell_mask])) if np.any(sell_mask) else 0.0,
        buy_win_rate=float(np.mean(wins[buy_mask])) if np.any(buy_mask) else 0.0,
    )


def row_for_mapping(
    frame: pd.DataFrame,
    selected_rows: np.ndarray,
    train_idx: np.ndarray,
    validation_idx: np.ndarray,
    test_idx: np.ndarray,
    top_mask: np.ndarray,
    bottom_mask: np.ndarray,
    policy: GeometryPolicy,
    mapping: str,
    delay: int,
    atr: np.ndarray,
    args: argparse.Namespace,
) -> SideMappingRow:
    train = evaluate_mapping_split(frame, selected_rows, train_idx, top_mask, bottom_mask, policy, mapping, delay, atr, args)
    validation = evaluate_mapping_split(frame, selected_rows, validation_idx, top_mask, bottom_mask, policy, mapping, delay, atr, args)
    test = evaluate_mapping_split(frame, selected_rows, test_idx, top_mask, bottom_mask, policy, mapping, delay, atr, args)
    mean_flip = sign_flip(train.mean_r, validation.mean_r, test.mean_r)
    validation_pass = int(
        validation.events >= int(args.min_validation_events)
        and validation.event_rate <= float(args.max_validation_event_rate)
        and validation.mean_r >= float(args.min_validation_mean_r)
    )
    test_pass = int(
        test.events >= int(args.min_test_events)
        and test.event_rate <= float(args.max_test_event_rate)
        and test.mean_r >= float(args.min_test_mean_r)
    )
    warnings: list[str] = []
    if validation.mean_r < float(args.min_validation_mean_r):
        warnings.append("validation mean R below minimum")
    if test.mean_r < float(args.min_test_mean_r):
        warnings.append("test mean R below minimum")
    if validation.events < int(args.min_validation_events):
        warnings.append("validation events below minimum")
    if test.events < int(args.min_test_events):
        warnings.append("test events below minimum")
    return SideMappingRow(
        geometry_policy_id=policy.policy_id,
        target_id=policy.target_id,
        side_mapping=mapping,
        entry_delay_bars=int(delay),
        recent_window_bars=int(policy.recent_window_bars),
        pivot_zone_atr=float(policy.pivot_zone_atr),
        top_position_threshold=float(policy.top_position_threshold),
        bottom_position_threshold=float(policy.bottom_position_threshold),
        exclude_both_zones=int(policy.exclude_both_zones),
        min_range_width_atr=float(policy.min_range_width_atr),
        max_range_width_atr=float(policy.max_range_width_atr),
        validation_events=int(validation.events),
        validation_event_rate=float(validation.event_rate),
        validation_win_rate=float(validation.win_rate),
        validation_mean_r=float(validation.mean_r),
        validation_sum_r=float(validation.sum_r),
        validation_profit_factor=float(validation.profit_factor),
        validation_sell_mean_r=float(validation.sell_mean_r),
        validation_buy_mean_r=float(validation.buy_mean_r),
        test_events=int(test.events),
        test_event_rate=float(test.event_rate),
        test_win_rate=float(test.win_rate),
        test_mean_r=float(test.mean_r),
        test_sum_r=float(test.sum_r),
        test_profit_factor=float(test.profit_factor),
        test_sell_mean_r=float(test.sell_mean_r),
        test_buy_mean_r=float(test.buy_mean_r),
        mean_r_sign_flip=int(mean_flip),
        validation_pass_gate=validation_pass,
        test_pass_gate=test_pass,
        transfer_pass_gate=int(validation_pass and test_pass and not mean_flip),
        validation_score=validation_score(validation, str(args.score_metric)),
        warnings=json.dumps(warnings, ensure_ascii=False),
    )


def evaluate_rows(args: argparse.Namespace, frame: pd.DataFrame, selected_rows: np.ndarray, policies: Sequence[GeometryPolicy]) -> list[SideMappingRow]:
    atr = resolve_atr(frame)
    train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
    mappings = [item.strip() for item in str(args.side_mappings).split(",") if item.strip()]
    delays = parse_int_grid(args.entry_delays, (0,))
    rows: list[SideMappingRow] = []
    for policy in policies:
        top_mask, bottom_mask, _ = build_geometry_masks(frame, selected_rows, atr, policy, str(args.zone_logic))
        for mapping in mappings:
            for delay in delays:
                rows.append(
                    row_for_mapping(
                        frame,
                        selected_rows,
                        train_idx,
                        validation_idx,
                        test_idx,
                        top_mask,
                        bottom_mask,
                        policy,
                        mapping,
                        int(delay),
                        atr,
                        args,
                    )
                )
    return rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: SideMappingReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['side_mapping']))}</td>"
        f"<td>{int(row['entry_delay_bars'])}</td>"
        f"<td>{html.escape(str(row['target_id']))}</td>"
        f"<td>{int(row['validation_events'])}</td>"
        f"<td>{float(row['validation_mean_r']):.4f}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{int(row['test_events'])}</td>"
        f"<td>{float(row['test_mean_r']):.4f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.top_rows[:50]
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase160A pivot side-mapping audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Top rows</h2><table><thead><tr><th>Mapping</th><th>Delay</th><th>Target</th><th>Val events</th><th>Val mean R</th><th>Val PF</th><th>Test events</th><th>Test mean R</th><th>Test PF</th><th>Transfer</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE160A PIVOT CANDIDATE SIDE-MAPPING AUDIT")
        print("=" * 74)
        flat_path = Path(args.flat_path)
        frame = read_frame(flat_path)
        selected_rows, sampled_universe, meta_path = load_meta_sample_indices(args, len(frame))
        policies = load_geometry_policies(args)
        train_idx, validation_idx, test_idx = split_indices(len(selected_rows), args.train_frac, args.val_frac, args.purge_gap)
        rows = evaluate_rows(args, frame, selected_rows, policies)
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
        output_csv = output_dir / "latest_grid.csv"
        write_csv(output_csv, row_dicts)
        report = SideMappingReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            flat_path=str(flat_path),
            meta_path=str(meta_path or ""),
            geometry_grid_path=str(args.geometry_grid_path),
            sampled_universe=sampled_universe,
            flat_rows=len(frame),
            sampled_rows=len(selected_rows),
            train_rows=len(train_idx),
            validation_rows=len(validation_idx),
            test_rows=len(test_idx),
            geometry_policies_loaded=len(policies),
            evaluated_rows=len(rows),
            validation_pass_rows=sum(int(row.validation_pass_gate) for row in rows),
            transfer_pass_rows=sum(int(row.transfer_pass_gate) for row in rows),
            selected_geometry_policy_id=selected.geometry_policy_id if selected else "",
            selected_side_mapping=selected.side_mapping if selected else "",
            selected_entry_delay_bars=int(selected.entry_delay_bars) if selected else 0,
            selected_validation_mean_r=float(selected.validation_mean_r) if selected else 0.0,
            selected_test_mean_r=float(selected.test_mean_r) if selected else 0.0,
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            top_rows=[asdict(row) for row in ranked[:80]],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_csv=str(output_csv),
            production_status="BLOCKED — Phase160A side-mapping audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase160A side-mapping audit complete")
        print(f"  geometry policies : {report.geometry_policies_loaded}")
        print(f"  evaluated rows    : {report.evaluated_rows}")
        print(f"  validation pass   : {report.validation_pass_rows}")
        print(f"  transfer pass     : {report.transfer_pass_rows}")
        print(f"  selected mapping  : {report.selected_side_mapping or 'none'} delay={report.selected_entry_delay_bars}")
        print(f"  output            : {report.output_json}")
        print(f"  elapsed           : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
