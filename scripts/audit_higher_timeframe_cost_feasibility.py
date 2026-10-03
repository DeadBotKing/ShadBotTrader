"""Phase179A: 4H/1D broker-cost feasibility and target pre-audit.

The current 1H broker-cost-aware pivot target-family lane was frozen by
Phase178A. This phase checks whether higher timeframes reduce cost/noise enough
to justify any future target-family work. It is diagnostic-only: no model is
trained, no tensor is built, and no paper/live trading is approved.
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
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_broker_cost_aware_1h_target_family import DEFAULT_STORAGE, parse_families  # noqa: E402
from audit_broker_cost_aware_1h_target_learnability import (  # noqa: E402
    CentroidBinaryModel,
    build_feature_rows,
    matrix_from_rows,
    split_rows_by_name,
)
from audit_pivot_1h_entry_feasibility import build_zone_masks, read_ohlc_frame  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402
from audit_walkforward_target_family_redesign_candidates import (  # noqa: E402
    CandidateFoldRow,
    CandidateSplitRow,
    TargetRedesignCandidateRow,
    candidate_summary,
    evaluate_candidate_split,
    rank_candidates,
    static_candidate_splits,
)
from audit_broker_cost_aware_1h_target_family import evaluate_family_events  # noqa: E402
from train_pivot_pattern_image_cnn import split_indices  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/higher_timeframe_cost_feasibility")
DEFAULT_H4_FLAT_PATH = "datasets/processed/XAUUSD/4H/v1.parquet"
DEFAULT_D1_FLAT_PATH = "datasets/processed/XAUUSD/1D/v1.parquet"
DEFAULT_H4_FAMILIES = (
    "H4_R1_BK_MID_B15_10_H6:h4_breakout_mid_fast:breakout:1:18:0.10:0.85:0.15:1:1.0:0:1.5:1.0:6;"
    "H4_R2_BK_STRICT_B15_10_H6:h4_breakout_strict_fast:breakout:1:18:0.05:0.90:0.10:1:1.0:0:1.5:1.0:6;"
    "H4_R3_BK_WIDE_B20_10_H12:h4_breakout_wide:breakout:1:36:0.10:0.85:0.15:1:1.0:0:2.0:1.0:12;"
    "H4_R4_REV_MID_B10_075_H6:h4_reversal_mid_fast:reversal:1:18:0.10:0.85:0.15:1:1.0:0:1.0:0.75:6"
)
DEFAULT_D1_FAMILIES = (
    "D1_R1_BK_MID_B20_10_H5:d1_breakout_mid:breakout:1:20:0.10:0.85:0.15:1:1.0:0:2.0:1.0:5;"
    "D1_R2_BK_STRICT_B15_10_H5:d1_breakout_strict:breakout:1:20:0.05:0.90:0.10:1:1.0:0:1.5:1.0:5;"
    "D1_R3_BK_WIDE_B25_125_H10:d1_breakout_wide:breakout:1:30:0.10:0.85:0.15:1:1.0:0:2.5:1.25:10;"
    "D1_R4_REV_MID_B10_075_H5:d1_reversal_mid:reversal:1:20:0.10:0.85:0.15:1:1.0:0:1.0:0.75:5"
)
EXPECTED_STEP_MINUTES = {"4H": 240.0, "H4": 240.0, "1D": 1440.0, "D1": 1440.0}


@dataclass(frozen=True)
class TimeframeHealthRow:
    timeframe: str
    flat_path: str
    rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    first_timestamp: str
    last_timestamp: str
    duplicate_timestamps: int
    missing_timestamp_rows: int
    expected_step_minutes: float
    gap_count: int
    max_gap_minutes: float
    nonfinite_ohlc_cells: int
    invalid_ohlc_rows: int
    atr_nonpositive_rows: int
    health_gate: int


@dataclass(frozen=True)
class TimeframeCostRow:
    timeframe: str
    split: str
    rows: int
    spread_mode: str
    spread_value: float
    atr_mean: float
    atr_median: float
    full_spread_atr_mean: float
    full_spread_atr_median: float
    full_spread_atr_p90: float
    cost_feasible_gate: int


@dataclass(frozen=True)
class HigherTimeframeCandidateRow:
    timeframe: str
    family_id: str
    label: str
    side_mapping: str
    entry_delay_bars: int
    recent_window_bars: int
    pivot_zone_atr: float
    top_position_threshold: float
    bottom_position_threshold: float
    tp_atr: float
    sl_atr: float
    reward_risk: float
    hold_bars: int
    train_events: int
    validation_events: int
    test_events: int
    train_positive_rate: float
    validation_positive_rate: float
    test_positive_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_independent_profit_factor: float
    validation_independent_profit_factor: float
    test_independent_profit_factor: float
    train_mean_atr_score: float
    validation_mean_atr_score: float
    test_mean_atr_score: float
    validation_ap_lift: float
    test_ap_lift: float
    validation_balanced_accuracy: float
    test_balanced_accuracy: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    density_gate: int
    economic_gate: int
    static_learnability_gate: int
    walkforward_gate: int
    target_family_ready_gate: int
    failure_reasons: str
    diagnostic_score: float


@dataclass(frozen=True)
class DecisionMatrixRow:
    route_id: str
    route_name: str
    status: str
    score: float
    rank: int
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class Phase179Report:
    symbol: str
    timeframes: list[str]
    spread_mode: str
    spread_value: float
    evaluated_timeframes: int
    evaluated_candidates: int
    ready_candidates: int
    selected_timeframe: str
    selected_family_id: str
    selected_family_ready_gate: int
    selected_walkforward_pass_ratio: float
    selected_train_independent_profit_factor: float
    selected_validation_independent_profit_factor: float
    selected_test_independent_profit_factor: float
    selected_validation_ap_lift: float
    selected_test_ap_lift: float
    higher_timeframe_feasibility_gate: int
    recommendation: str
    health_rows: list[dict[str, Any]]
    cost_rows: list[dict[str, Any]]
    candidate_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    decision_matrix_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_health_csv: str
    output_cost_csv: str
    output_candidates_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit 4H/1D broker-cost feasibility and target-family pre-audit before model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframes", default="4H,1D")
    parser.add_argument("--h4-flat-path", default=DEFAULT_H4_FLAT_PATH)
    parser.add_argument("--d1-flat-path", default=DEFAULT_D1_FLAT_PATH)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--h4-families", default=DEFAULT_H4_FAMILIES)
    parser.add_argument("--d1-families", default=DEFAULT_D1_FAMILIES)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.4)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=10)
    parser.add_argument("--max-folds", type=int, default=6)
    parser.add_argument("--fold-train-frac", type=float, default=0.50)
    parser.add_argument("--fold-validation-frac", type=float, default=0.12)
    parser.add_argument("--fold-test-frac", type=float, default=0.12)
    parser.add_argument("--fold-step-frac", type=float, default=0.08)
    parser.add_argument("--min-train-events", type=int, default=80)
    parser.add_argument("--min-validation-events", type=int, default=15)
    parser.add_argument("--min-test-events", type=int, default=15)
    parser.add_argument("--min-positive-rate", type=float, default=0.10)
    parser.add_argument("--max-positive-rate", type=float, default=0.70)
    parser.add_argument("--max-label-psi", type=float, default=0.25)
    parser.add_argument("--min-ap-lift", type=float, default=0.02)
    parser.add_argument("--min-balanced-accuracy", type=float, default=0.52)
    parser.add_argument("--min-train-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-validation-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-test-independent-pf", type=float, default=1.00)
    parser.add_argument("--min-train-mean-atr-score", type=float, default=0.0)
    parser.add_argument("--max-median-spread-atr", type=float, default=0.08)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=4)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase179A 4H/1D broker-cost feasibility and target pre-audit")
    return parser.parse_args(argv)


def canonical_timeframe(text: str) -> str:
    value = str(text or "").strip().upper()
    if value in {"H4", "4", "4H"}:
        return "4H"
    if value in {"D1", "1", "1D", "D"}:
        return "1D"
    return value


def parse_timeframes(text: str) -> list[str]:
    values: list[str] = []
    for raw in str(text or "").replace(";", ",").split(","):
        value = canonical_timeframe(raw)
        if value and value not in values:
            values.append(value)
    return values or ["4H", "1D"]


def flat_path_for_timeframe(args: argparse.Namespace, timeframe: str) -> Path:
    tf = canonical_timeframe(timeframe)
    raw = args.h4_flat_path if tf == "4H" else args.d1_flat_path
    requested = Path(str(raw))
    if requested.exists():
        return requested
    base = Path(args.storage_root) / "processed" / str(args.symbol).upper() / tf
    candidates = [base / "v1.parquet", base / "hybrid_telemetry_flat_latest.parquet", base / "pivot_pattern_sequence_flat_latest.parquet"]
    candidates.extend(sorted(base.glob("*.parquet"), reverse=True)) if base.exists() else None
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"{tf} flat file not found. Requested={requested}; searched under {base}")


def families_for_timeframe(args: argparse.Namespace, timeframe: str) -> str:
    return str(args.h4_families if timeframe.upper() in {"4H", "H4"} else args.d1_families)


def spread_price(close_value: float, spread_mode: str, spread_value: float) -> float:
    if str(spread_mode) == "pct":
        return abs(float(close_value) * float(spread_value) / 100.0)
    return abs(float(spread_value))


def build_health_row(timeframe: str, flat_path: Path, frame: pd.DataFrame, atr: np.ndarray, train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray) -> TimeframeHealthRow:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    expected = EXPECTED_STEP_MINUTES.get(timeframe.upper(), 0.0)
    deltas = timestamps.diff().dt.total_seconds().dropna().to_numpy(dtype=np.float64) / 60.0
    gap_mask = np.abs(deltas - expected) > max(expected * 0.25, 1.0) if expected > 0 else np.asarray([], dtype=bool)
    ohlc = frame[["open", "high", "low", "close"]].to_numpy(dtype=np.float64)
    high = frame["high"].to_numpy(dtype=np.float64)
    low = frame["low"].to_numpy(dtype=np.float64)
    open_ = frame["open"].to_numpy(dtype=np.float64)
    close = frame["close"].to_numpy(dtype=np.float64)
    invalid = (high < low) | (high < np.maximum(open_, close)) | (low > np.minimum(open_, close))
    bad_atr = ~np.isfinite(atr) | (atr <= 0)
    return TimeframeHealthRow(
        timeframe=timeframe,
        flat_path=str(flat_path),
        rows=int(len(frame)),
        train_rows=int(len(train_idx)),
        validation_rows=int(len(val_idx)),
        test_rows=int(len(test_idx)),
        first_timestamp=str(timestamps.iloc[0]) if len(timestamps) else "",
        last_timestamp=str(timestamps.iloc[-1]) if len(timestamps) else "",
        duplicate_timestamps=int(timestamps.duplicated().sum()) if len(timestamps) else 0,
        missing_timestamp_rows=int(timestamps.isna().sum()) if len(timestamps) else 0,
        expected_step_minutes=float(expected),
        gap_count=int(np.sum(gap_mask)) if len(deltas) else 0,
        max_gap_minutes=float(np.max(deltas)) if len(deltas) else 0.0,
        nonfinite_ohlc_cells=int(np.sum(~np.isfinite(ohlc))),
        invalid_ohlc_rows=int(np.sum(invalid)),
        atr_nonpositive_rows=int(np.sum(bad_atr)),
        health_gate=int(
            int(timestamps.duplicated().sum()) == 0
            and int(timestamps.isna().sum()) == 0
            and int(np.sum(~np.isfinite(ohlc))) == 0
            and int(np.sum(invalid)) == 0
            and int(np.sum(bad_atr)) == 0
        ),
    )


def cost_rows_for_timeframe(timeframe: str, frame: pd.DataFrame, atr: np.ndarray, splits: Mapping[str, np.ndarray], args: argparse.Namespace) -> list[TimeframeCostRow]:
    close = frame["close"].to_numpy(dtype=np.float64)
    rows: list[TimeframeCostRow] = []
    for split, indices in splits.items():
        idx = np.asarray(indices, dtype=np.int64)
        atr_values = atr[idx] if len(idx) else np.asarray([], dtype=np.float64)
        spread_values = np.asarray([spread_price(close[row], str(args.spread_mode), float(args.spread_value)) for row in idx], dtype=np.float64)
        spread_atr = spread_values / np.maximum(atr_values, 1e-9) if len(idx) else np.asarray([], dtype=np.float64)
        median = float(np.median(spread_atr)) if len(spread_atr) else 0.0
        rows.append(
            TimeframeCostRow(
                timeframe=timeframe,
                split=split,
                rows=int(len(idx)),
                spread_mode=str(args.spread_mode),
                spread_value=float(args.spread_value),
                atr_mean=float(np.mean(atr_values)) if len(atr_values) else 0.0,
                atr_median=float(np.median(atr_values)) if len(atr_values) else 0.0,
                full_spread_atr_mean=float(np.mean(spread_atr)) if len(spread_atr) else 0.0,
                full_spread_atr_median=median,
                full_spread_atr_p90=float(np.quantile(spread_atr, 0.90)) if len(spread_atr) else 0.0,
                cost_feasible_gate=int(median <= float(args.max_median_spread_atr)),
            )
        )
    return rows


def auto_fold_specs(n_rows: int, args: argparse.Namespace) -> list[SimpleNamespace]:
    n = int(n_rows)
    if n < 120:
        return []
    train_size = max(40, int(n * float(args.fold_train_frac)))
    val_size = max(10, int(n * float(args.fold_validation_frac)))
    test_size = max(10, int(n * float(args.fold_test_frac)))
    purge = max(int(args.purge_gap), 0)
    total = train_size + val_size + test_size + (2 * purge)
    if total >= n:
        train_size = max(40, int(n * 0.45))
        val_size = max(10, int(n * 0.15))
        test_size = max(10, int(n * 0.15))
        total = train_size + val_size + test_size + (2 * purge)
    if total >= n:
        return []
    max_start = n - total
    fold_count = max(1, int(args.max_folds))
    if fold_count == 1 or max_start <= 0:
        starts = [0]
    else:
        step = max(1, int(n * float(args.fold_step_frac)))
        starts = list(range(0, max_start + 1, step))[:fold_count]
        if starts and starts[-1] != max_start and len(starts) < fold_count:
            starts.append(max_start)
    specs: list[SimpleNamespace] = []
    for fold, start in enumerate(starts, start=1):
        train_start = int(start)
        train_end = train_start + train_size
        validation_start = train_end + purge
        validation_end = validation_start + val_size
        test_start = validation_end + purge
        test_end = test_start + test_size
        if test_end <= n:
            specs.append(
                SimpleNamespace(
                    fold=int(fold),
                    train_start=train_start,
                    train_end=train_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
    return specs


def walkforward_rows_for_family(family: Any, events: Sequence[Any], frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace) -> list[CandidateFoldRow]:
    rows: list[CandidateFoldRow] = []
    for spec in auto_fold_specs(len(frame), args):
        train_idx = np.arange(spec.train_start, spec.train_end, dtype=np.int64)
        val_idx = np.arange(spec.validation_start, spec.validation_end, dtype=np.int64)
        test_idx = np.arange(spec.test_start, spec.test_end, dtype=np.int64)
        event_args = SimpleNamespace(spread_mode=args.spread_mode, spread_value=args.spread_value, same_bar_policy=args.same_bar_policy)
        dataset = build_feature_rows(family, events, frame, atr, event_args, {"train": train_idx, "validation": val_idx, "test": test_idx}, int(spec.fold))
        by_split = split_rows_by_name(dataset)
        x_train, y_train, _sides, _labels = matrix_from_rows(by_split["train"])
        model = CentroidBinaryModel().fit(x_train, y_train)
        train_dist = {
            "POSITIVE": float(np.mean(y_train == 1)) if len(y_train) else 0.0,
            "NEGATIVE": float(np.mean(y_train == 0)) if len(y_train) else 0.0,
            "TIMEOUT": 0.0,
        }
        train_eval = evaluate_candidate_split(model, by_split["train"], None, family, "train", args)
        val_eval = evaluate_candidate_split(model, by_split["validation"], train_dist, family, "validation", args)
        test_eval = evaluate_candidate_split(model, by_split["test"], train_dist, family, "test", args)
        reasons = []
        if not int(train_eval.pass_gate):
            reasons.append("train_gate_failed")
        if not int(val_eval.pass_gate):
            reasons.append("validation_gate_failed")
        if not int(test_eval.pass_gate):
            reasons.append("test_gate_failed")
        rows.append(
            CandidateFoldRow(
                family_id=family.family_id,
                label=family.label,
                fold=int(spec.fold),
                train_events=int(train_eval.events),
                validation_events=int(val_eval.events),
                test_events=int(test_eval.events),
                train_positive_rate=float(train_eval.positive_rate),
                validation_positive_rate=float(val_eval.positive_rate),
                test_positive_rate=float(test_eval.positive_rate),
                validation_label_psi=float(val_eval.label_psi_vs_train),
                test_label_psi=float(test_eval.label_psi_vs_train),
                train_independent_profit_factor=float(train_eval.independent_profit_factor),
                validation_independent_profit_factor=float(val_eval.independent_profit_factor),
                test_independent_profit_factor=float(test_eval.independent_profit_factor),
                train_mean_atr_score=float(train_eval.mean_atr_score),
                validation_mean_atr_score=float(val_eval.mean_atr_score),
                test_mean_atr_score=float(test_eval.mean_atr_score),
                validation_ap_lift=float(val_eval.ap_lift),
                test_ap_lift=float(test_eval.ap_lift),
                validation_balanced_accuracy=float(val_eval.balanced_accuracy),
                test_balanced_accuracy=float(test_eval.balanced_accuracy),
                pass_gate=int(train_eval.pass_gate and val_eval.pass_gate and test_eval.pass_gate),
                failure_reasons=json.dumps(reasons or ["none"], ensure_ascii=False),
            )
        )
    return rows


def build_family_events_and_rows(family: Any, frame: pd.DataFrame, atr: np.ndarray, args: argparse.Namespace, split_map: Mapping[str, np.ndarray]) -> tuple[list[Any], list[Any]]:
    top_mask, bottom_mask, _both = build_zone_masks(
        frame,
        atr,
        family.recent_window_bars,
        family.pivot_zone_atr,
        family.top_position_threshold,
        family.bottom_position_threshold,
        family.exclude_both_zones,
        family.min_range_width_atr,
        family.max_range_width_atr,
    )
    event_args = SimpleNamespace(spread_mode=args.spread_mode, spread_value=args.spread_value, same_bar_policy=args.same_bar_policy)
    events = evaluate_family_events(family, frame, atr, top_mask, bottom_mask, event_args, float(args.spread_value))
    rows = build_feature_rows(family, events, frame, atr, event_args, split_map, 0)
    return events, rows


def wrap_candidate(timeframe: str, row: TargetRedesignCandidateRow) -> HigherTimeframeCandidateRow:
    payload = asdict(row)
    payload["target_family_ready_gate"] = payload.pop("target_family_redesign_ready_gate")
    return HigherTimeframeCandidateRow(timeframe=timeframe, **payload)


def decision_matrix(ready_count: int, selected: HigherTimeframeCandidateRow | None) -> list[DecisionMatrixRow]:
    selected_text = f"{selected.timeframe}|{selected.family_id}" if selected else "none"
    return [
        DecisionMatrixRow(
            route_id="HIGHER_TIMEFRAME_TARGET_READY",
            route_name="Higher-timeframe target family ready for later model-design preflight",
            status="READY_FOR_OWNER_REVIEW" if ready_count > 0 else "NOT_CONFIRMED",
            score=85.0 if ready_count > 0 else 35.0,
            rank=1,
            evidence=f"ready_candidates={ready_count}; selected={selected_text}",
            recommendation=(
                "Owner may authorize a separate model-design preflight, still no paper/live."
                if ready_count > 0
                else "Do not train; higher-timeframe feasibility did not pass target gates."
            ),
        ),
        DecisionMatrixRow(
            route_id="TRAIN_MODEL_NOW",
            route_name="Train a model now",
            status="BLOCKED",
            score=0.0,
            rank=2,
            evidence="Phase179A is a feasibility/target pre-audit only.",
            recommendation="No model training from this phase.",
        ),
        DecisionMatrixRow(
            route_id="PAPER_OR_LIVE",
            route_name="Paper shadow or live trading",
            status="BLOCKED",
            score=0.0,
            rank=3,
            evidence="No production gate exists in Phase179A.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase179Report) -> str:
    candidate_rows = "".join(
        f"<tr><td>{html.escape(str(row['timeframe']))}</td><td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{float(row['tp_atr']):.2f}/{float(row['sl_atr']):.2f}/{int(row['hold_bars'])}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{float(row['train_independent_profit_factor']):.3f}</td>"
        f"<td>{float(row['validation_ap_lift']):.4f}</td><td>{float(row['test_ap_lift']):.4f}</td>"
        f"<td>{int(row['target_family_ready_gate'])}</td></tr>"
        for row in report.candidate_rows
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:12px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase179A 4H/1D broker-cost feasibility and target pre-audit. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'higher_timeframe_feasibility_gate': report.higher_timeframe_feasibility_gate,
        'ready_candidates': report.ready_candidates,
        'selected_timeframe': report.selected_timeframe,
        'selected_family_id': report.selected_family_id,
        'recommendation': report.recommendation,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Candidates</h2><table><thead><tr><th>TF</th><th>Family</th><th>TP/SL/Hold</th><th>WF</th><th>Train PF</th><th>Val AP</th><th>Test AP</th><th>Ready</th></tr></thead><tbody>{candidate_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE179A 4H/1D BROKER-COST FEASIBILITY PRE-AUDIT")
        print("=" * 74)
        timeframes = parse_timeframes(args.timeframes)
        health_rows: list[TimeframeHealthRow] = []
        cost_rows: list[TimeframeCostRow] = []
        candidate_rows: list[HigherTimeframeCandidateRow] = []
        split_rows: list[dict[str, Any]] = []
        wf_rows: list[dict[str, Any]] = []
        for timeframe in timeframes:
            flat_path = flat_path_for_timeframe(args, timeframe)
            frame = read_ohlc_frame(flat_path, int(args.max_rows))
            atr = resolve_atr(frame)
            train_idx, val_idx, test_idx = split_indices(len(frame), float(args.train_frac), float(args.val_frac), int(args.purge_gap))
            split_map = {"train": train_idx, "validation": val_idx, "test": test_idx}
            health_rows.append(build_health_row(timeframe, flat_path, frame, atr, train_idx, val_idx, test_idx))
            cost_rows.extend(cost_rows_for_timeframe(timeframe, frame, atr, split_map, args))
            for family in parse_families(families_for_timeframe(args, timeframe)):
                print(f"[i] {timeframe} family={family.family_id}")
                events, rows = build_family_events_and_rows(family, frame, atr, args, split_map)
                static_rows = static_candidate_splits(family, rows, args)
                family_wf = walkforward_rows_for_family(family, events, frame, atr, args)
                summary = candidate_summary(family, static_rows, family_wf, args)
                candidate_rows.append(wrap_candidate(timeframe, summary))
                for row in static_rows:
                    item = asdict(row)
                    item["timeframe"] = timeframe
                    split_rows.append(item)
                for row in family_wf:
                    item = asdict(row)
                    item["timeframe"] = timeframe
                    wf_rows.append(item)
        ranked = sorted(
            candidate_rows,
            key=lambda row: (
                row.target_family_ready_gate,
                row.walkforward_pass_ratio,
                row.diagnostic_score,
                row.test_balanced_accuracy,
            ),
            reverse=True,
        )
        ready_count = sum(row.target_family_ready_gate for row in ranked)
        selected = ranked[0] if ranked else None
        decisions = decision_matrix(ready_count, selected)
        output_health = output_dir / "latest_health.csv"
        output_cost = output_dir / "latest_cost.csv"
        output_candidates = output_dir / "latest_candidates.csv"
        output_splits = output_dir / "latest_splits.csv"
        output_wf = output_dir / "latest_walkforward.csv"
        output_decision = output_dir / "latest_decision_matrix.csv"
        write_csv(output_health, [asdict(row) for row in health_rows])
        write_csv(output_cost, [asdict(row) for row in cost_rows])
        write_csv(output_candidates, [asdict(row) for row in ranked])
        write_csv(output_splits, split_rows)
        write_csv(output_wf, wf_rows)
        write_csv(output_decision, [asdict(row) for row in decisions])
        report = Phase179Report(
            symbol=str(args.symbol),
            timeframes=timeframes,
            spread_mode=str(args.spread_mode),
            spread_value=float(args.spread_value),
            evaluated_timeframes=len(timeframes),
            evaluated_candidates=len(ranked),
            ready_candidates=int(ready_count),
            selected_timeframe=str(selected.timeframe) if selected else "",
            selected_family_id=str(selected.family_id) if selected else "",
            selected_family_ready_gate=int(selected.target_family_ready_gate) if selected else 0,
            selected_walkforward_pass_ratio=float(selected.walkforward_pass_ratio) if selected else 0.0,
            selected_train_independent_profit_factor=float(selected.train_independent_profit_factor) if selected else 0.0,
            selected_validation_independent_profit_factor=float(selected.validation_independent_profit_factor) if selected else 0.0,
            selected_test_independent_profit_factor=float(selected.test_independent_profit_factor) if selected else 0.0,
            selected_validation_ap_lift=float(selected.validation_ap_lift) if selected else 0.0,
            selected_test_ap_lift=float(selected.test_ap_lift) if selected else 0.0,
            higher_timeframe_feasibility_gate=int(ready_count > 0),
            recommendation=("HIGHER_TIMEFRAME_TARGET_READY_FOR_OWNER_REVIEW_NO_TRAINING" if ready_count > 0 else "NO_HIGHER_TIMEFRAME_TARGET_READY"),
            health_rows=[asdict(row) for row in health_rows],
            cost_rows=[asdict(row) for row in cost_rows],
            candidate_rows=[asdict(row) for row in ranked],
            split_rows=split_rows,
            walkforward_rows=wf_rows,
            decision_matrix_rows=[asdict(row) for row in decisions],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_health_csv=str(output_health),
            output_cost_csv=str(output_cost),
            output_candidates_csv=str(output_candidates),
            output_splits_csv=str(output_splits),
            output_walkforward_csv=str(output_wf),
            output_decision_matrix_csv=str(output_decision),
            production_status="BLOCKED — Phase179A 4H/1D feasibility pre-audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase179A higher-timeframe feasibility audit complete")
        print(f"  timeframes : {','.join(report.timeframes)}")
        print(f"  candidates : {report.evaluated_candidates}")
        print(f"  ready      : {report.ready_candidates}")
        print(f"  selected   : {report.selected_timeframe}|{report.selected_family_id}")
        print(f"  output     : {report.output_json}")
        print(f"  elapsed    : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
