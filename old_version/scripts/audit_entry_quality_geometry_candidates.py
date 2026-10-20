"""Phase183A: entry quality-geometry candidate audit.

Phase182A found that entry-event families were not blocked by data health or
broker cost. They failed because the current trigger/entry quality geometry did
not produce clean MFE-before-MAE paths or walk-forward transfer. This phase
redesigns *geometry only* (trigger buffer, trigger horizon, MFE target, MAE
limit, quality window and optional side-specific diagnostics) and audits those
candidates without training any model.

Research only:
- no model training
- no paper/live trading
- no Phase134
- no gate relaxation
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import audit_entry_event_discovery as phase181b  # noqa: E402
from replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/entry_quality_geometry_candidates")
DEFAULT_CANDIDATES = (
    "Q1_D1_E3_M10_A10:d1_continuation_mfe10_mae10:1D:continuation:12:0.03:0.5:0:2:10:1.0:1.0:20:12:0.45:1.20:0.50:ALL;"
    "Q2_D1_E3_M08_A10:d1_continuation_mfe08_mae10:1D:continuation:12:0.03:0.5:0:2:10:0.8:1.0:20:12:0.45:1.20:0.50:ALL;"
    "Q3_D1_E3_B00_M10_A10:d1_continuation_no_buffer:1D:continuation:12:0.00:0.5:0:2:10:1.0:1.0:20:12:0.45:1.20:0.50:ALL;"
    "Q4_D1_E3_M10_A125:d1_continuation_mae125:1D:continuation:12:0.03:0.5:0:2:10:1.0:1.25:20:12:0.45:1.20:0.50:ALL;"
    "Q5_H4_E2_M10_A10:h4_pullback_mfe10_mae10:4H:pullback_rejection:24:0.03:1.0:0:3:12:1.0:1.0:20:12:0.20:1.00:0.45:ALL;"
    "Q6_H4_E2_M08_A10:h4_pullback_mfe08_mae10:4H:pullback_rejection:24:0.03:1.0:0:3:12:0.8:1.0:20:12:0.20:1.00:0.45:ALL;"
    "Q7_H4_E2_B00_M10_A10:h4_pullback_no_buffer:4H:pullback_rejection:24:0.00:1.0:0:3:12:1.0:1.0:20:12:0.20:1.00:0.45:ALL;"
    "Q8_H4_E3_M10_A10:h4_continuation_mfe10_mae10:4H:continuation:12:0.03:0.5:0:2:10:1.0:1.0:20:12:0.45:1.20:0.50:ALL;"
    "Q9_H4_E3_M08_A10:h4_continuation_mfe08_mae10:4H:continuation:12:0.03:0.5:0:2:10:0.8:1.0:20:12:0.45:1.20:0.50:ALL;"
    "Q10_H4_E3_M10_A125:h4_continuation_mae125:4H:continuation:12:0.03:0.5:0:2:10:1.0:1.25:20:12:0.45:1.20:0.50:ALL;"
    "Q11_D1_E2_BUY_M10_A10:d1_pullback_buy_only_mfe10_mae10:1D:pullback_rejection:24:0.03:1.0:0:3:12:1.0:1.0:20:12:0.20:1.00:0.45:BUY;"
    "Q12_D1_E2_BUY_M08_A10:d1_pullback_buy_only_mfe08_mae10:1D:pullback_rejection:24:0.03:1.0:0:3:12:0.8:1.0:20:12:0.20:1.00:0.45:BUY"
)
SIDE_ALL = "ALL"
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"


@dataclass(frozen=True)
class QualityCandidateSpec:
    candidate_id: str
    label: str
    timeframe: str
    family_type: str
    recent_window_bars: int
    buffer_atr: float
    min_width_atr: float
    max_width_atr: float
    trigger_horizon_bars: int
    quality_bars: int
    mfe_atr: float
    mae_atr: float
    trend_window_bars: int
    compression_window_bars: int
    min_body_atr: float
    min_expansion_ratio: float
    pullback_position: float
    side_filter: str


@dataclass(frozen=True)
class CandidateSummaryRow:
    candidate_id: str
    label: str
    timeframe: str
    family_type: str
    side_filter: str
    recent_window_bars: int
    buffer_atr: float
    trigger_horizon_bars: int
    quality_bars: int
    mfe_atr: float
    mae_atr: float
    train_events: int
    validation_events: int
    test_events: int
    train_event_rate: float
    validation_event_rate: float
    test_event_rate: float
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    train_replay_profit_factor: float
    validation_replay_profit_factor: float
    test_replay_profit_factor: float
    train_mean_score: float
    validation_mean_score: float
    test_mean_score: float
    validation_label_psi: float
    test_label_psi: float
    train_feature_smd: float
    validation_feature_smd: float
    test_feature_smd: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    density_gate: int
    direction_balance_gate: int
    temporal_stability_gate: int
    mfe_mae_gate: int
    replay_gate: int
    feature_separability_gate: int
    cost_gate: int
    quality_geometry_candidate_ready_gate: int
    failure_reasons: str
    diagnostic_score: float


@dataclass(frozen=True)
class CandidateSplitRow:
    candidate_id: str
    timeframe: str
    family_type: str
    side_filter: str
    split: str
    rows: int
    triggered_events: int
    buy_events: int
    sell_events: int
    event_rate: float
    quality_pass_rate: float
    mean_mfe_atr: float
    mean_mae_atr: float
    mfe_mae_ratio: float
    replay_profit_factor: float
    mean_replay_score_atr: float
    label_psi_vs_train: float
    max_feature_abs_smd: float
    density_gate: int
    direction_balance_gate: int
    temporal_stability_gate: int
    mfe_mae_gate: int
    replay_gate: int
    feature_separability_gate: int
    split_pass_gate: int


@dataclass(frozen=True)
class CandidateWalkForwardRow:
    candidate_id: str
    timeframe: str
    family_type: str
    side_filter: str
    fold: int
    train_events: int
    validation_events: int
    test_events: int
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    validation_label_psi: float
    test_label_psi: float
    train_gate: int
    validation_gate: int
    test_gate: int
    pass_gate: int


@dataclass(frozen=True)
class GeometryComparisonRow:
    candidate_id: str
    source_focus: str
    current_mfe_atr: float
    current_mae_atr: float
    candidate_mfe_atr: float
    candidate_mae_atr: float
    test_quality_pass_rate: float
    test_replay_profit_factor: float
    walkforward_pass_ratio: float
    verdict: str


@dataclass(frozen=True)
class DecisionRow:
    route_id: str
    status: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class Phase183AReport:
    phase182a_path: str
    source_symbol: str
    source_focus: str
    evaluated_candidates: int
    ready_candidates: int
    selected_candidate_id: str
    selected_timeframe: str
    selected_family_type: str
    selected_side_filter: str
    selected_candidate_ready_gate: int
    selected_test_quality_pass_rate: float
    selected_test_replay_profit_factor: float
    selected_walkforward_pass_ratio: float
    quality_geometry_redesign_ready_gate: int
    no_training_gate: int
    no_paper_live_gate: int
    recommendation: str
    candidate_rows: list[dict[str, Any]]
    split_rows: list[dict[str, Any]]
    walkforward_rows: list[dict[str, Any]]
    geometry_comparison_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidates_csv: str
    output_splits_csv: str
    output_walkforward_csv: str
    output_events_csv: str
    output_replay_csv: str
    output_geometry_comparison_csv: str
    output_decision_matrix_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase183A entry quality-geometry candidate audit. No model training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase182a-path", default="run_logs/entry_event_failure_attribution/latest.json")
    parser.add_argument("--phase181b-path", default="run_logs/entry_event_discovery/latest.json")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--h1-flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--h4-flat-path", default="datasets/processed/XAUUSD/4H/v1.parquet")
    parser.add_argument("--d1-flat-path", default="datasets/processed/XAUUSD/1D/v1.parquet")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--spread-mode", choices=("fixed", "pct"), default="fixed")
    parser.add_argument("--spread-value", type=float, default=0.4)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=10)
    parser.add_argument("--max-folds", type=int, default=4)
    parser.add_argument("--fold-train-frac", type=float, default=0.50)
    parser.add_argument("--fold-validation-frac", type=float, default=0.12)
    parser.add_argument("--fold-test-frac", type=float, default=0.12)
    parser.add_argument("--fold-step-frac", type=float, default=0.08)
    parser.add_argument("--min-train-events", type=int, default=30)
    parser.add_argument("--min-validation-events", type=int, default=8)
    parser.add_argument("--min-test-events", type=int, default=8)
    parser.add_argument("--min-side-events", type=int, default=3)
    parser.add_argument("--max-event-rate", type=float, default=0.35)
    parser.add_argument("--min-direction-balance", type=float, default=0.20)
    parser.add_argument("--max-label-psi", type=float, default=0.30)
    parser.add_argument("--min-quality-pass-rate", type=float, default=0.45)
    parser.add_argument("--min-mfe-mae-ratio", type=float, default=1.10)
    parser.add_argument("--min-replay-profit-factor", type=float, default=1.05)
    parser.add_argument("--min-feature-separability", type=float, default=0.05)
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=3)
    parser.add_argument("--max-event-rows", type=int, default=200000)
    parser.add_argument("--storage-root", default="datasets")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase183A entry quality-geometry candidate audit")
    return parser.parse_args(argv)


def load_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_slug(text: str) -> str:
    return phase181b.safe_slug(text)


def canonical_timeframe(text: str) -> str:
    return phase181b.canonical_timeframe(text)


def parse_candidates(text: str) -> list[QualityCandidateSpec]:
    candidates: list[QualityCandidateSpec] = []
    for raw in str(text or "").split(";"):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 18:
            raise RuntimeError(
                "candidate format must be "
                "ID:label:timeframe:type:rw:buffer:min_width:max_width:trigger_horizon:quality_bars:"
                "mfe:mae:trend_window:compression_window:min_body_atr:min_expansion_ratio:pullback_position:side_filter"
            )
        side_filter = parts[17].upper()
        if side_filter not in {SIDE_ALL, SIDE_BUY, SIDE_SELL}:
            raise RuntimeError(f"Unsupported side_filter: {side_filter}")
        candidates.append(
            QualityCandidateSpec(
                candidate_id=safe_slug(parts[0]),
                label=safe_slug(parts[1]),
                timeframe=canonical_timeframe(parts[2]),
                family_type=parts[3].lower(),
                recent_window_bars=max(int(parts[4]), 2),
                buffer_atr=max(float(parts[5]), 0.0),
                min_width_atr=max(float(parts[6]), 0.0),
                max_width_atr=max(float(parts[7]), 0.0),
                trigger_horizon_bars=max(int(parts[8]), 1),
                quality_bars=max(int(parts[9]), 1),
                mfe_atr=max(float(parts[10]), 0.01),
                mae_atr=max(float(parts[11]), 0.01),
                trend_window_bars=max(int(parts[12]), 1),
                compression_window_bars=max(int(parts[13]), 2),
                min_body_atr=max(float(parts[14]), 0.0),
                min_expansion_ratio=max(float(parts[15]), 0.0),
                pullback_position=min(max(float(parts[16]), 0.01), 0.99),
                side_filter=side_filter,
            )
        )
    if not candidates:
        raise RuntimeError("At least one quality-geometry candidate is required")
    return candidates


def to_entry_family(candidate: QualityCandidateSpec) -> phase181b.EntryFamilySpec:
    return phase181b.EntryFamilySpec(
        family_id=candidate.candidate_id,
        label=candidate.label,
        family_type=candidate.family_type,
        recent_window_bars=candidate.recent_window_bars,
        buffer_atr=candidate.buffer_atr,
        min_width_atr=candidate.min_width_atr,
        max_width_atr=candidate.max_width_atr,
        trigger_horizon_bars=candidate.trigger_horizon_bars,
        quality_bars=candidate.quality_bars,
        mfe_atr=candidate.mfe_atr,
        mae_atr=candidate.mae_atr,
        trend_window_bars=candidate.trend_window_bars,
        compression_window_bars=candidate.compression_window_bars,
        min_body_atr=candidate.min_body_atr,
        min_expansion_ratio=candidate.min_expansion_ratio,
        pullback_position=candidate.pullback_position,
    )


def filter_events(events: Sequence[phase181b.EventAttempt], side_filter: str) -> list[phase181b.EventAttempt]:
    if side_filter == SIDE_ALL:
        return list(events)
    return [event for event in events if event.side == side_filter]


def adjusted_split_metrics(
    metrics: phase181b.SplitMetricsRow,
    side_filter: str,
    args: argparse.Namespace,
    split: str,
) -> phase181b.SplitMetricsRow:
    if side_filter == SIDE_ALL:
        return metrics
    min_events = {
        "train": int(args.min_train_events),
        "validation": int(args.min_validation_events),
        "test": int(args.min_test_events),
    }.get(split, int(args.min_validation_events))
    density_gate = int(metrics.triggered_events >= min_events and metrics.event_rate <= float(args.max_event_rate))
    direction_gate = 1
    split_pass = int(
        density_gate
        and direction_gate
        and metrics.temporal_stability_gate
        and metrics.mfe_mae_gate
        and metrics.replay_gate
        and metrics.feature_separability_gate
    )
    return replace(
        metrics,
        density_gate=density_gate,
        direction_balance_gate=direction_gate,
        split_pass_gate=split_pass,
    )


def split_metric_row(
    candidate: QualityCandidateSpec,
    metrics: phase181b.SplitMetricsRow,
) -> CandidateSplitRow:
    return CandidateSplitRow(
        candidate_id=candidate.candidate_id,
        timeframe=candidate.timeframe,
        family_type=candidate.family_type,
        side_filter=candidate.side_filter,
        split=metrics.split,
        rows=metrics.rows,
        triggered_events=metrics.triggered_events,
        buy_events=metrics.buy_events,
        sell_events=metrics.sell_events,
        event_rate=metrics.event_rate,
        quality_pass_rate=metrics.quality_pass_rate,
        mean_mfe_atr=metrics.mean_mfe_atr,
        mean_mae_atr=metrics.mean_mae_atr,
        mfe_mae_ratio=metrics.mfe_mae_ratio,
        replay_profit_factor=metrics.replay_profit_factor,
        mean_replay_score_atr=metrics.mean_replay_score_atr,
        label_psi_vs_train=metrics.label_psi_vs_train,
        max_feature_abs_smd=metrics.max_feature_abs_smd,
        density_gate=metrics.density_gate,
        direction_balance_gate=metrics.direction_balance_gate,
        temporal_stability_gate=metrics.temporal_stability_gate,
        mfe_mae_gate=metrics.mfe_mae_gate,
        replay_gate=metrics.replay_gate,
        feature_separability_gate=metrics.feature_separability_gate,
        split_pass_gate=metrics.split_pass_gate,
    )


def idx_range(start: int, end: int) -> np.ndarray:
    return np.arange(int(start), int(end), dtype=np.int64)


def walkforward_rows(
    candidate: QualityCandidateSpec,
    family: phase181b.EntryFamilySpec,
    frame: Any,
    atr: np.ndarray,
    events: Sequence[phase181b.EventAttempt],
    args: argparse.Namespace,
) -> list[CandidateWalkForwardRow]:
    total_rows = len(frame)
    train_bars = max(int(total_rows * float(args.fold_train_frac)), 1)
    validation_bars = max(int(total_rows * float(args.fold_validation_frac)), 1)
    test_bars = max(int(total_rows * float(args.fold_test_frac)), 1)
    step_bars = max(int(total_rows * float(args.fold_step_frac)), 1)
    specs = build_fold_specs(
        total_rows,
        train_bars,
        validation_bars,
        test_bars,
        step_bars,
        int(args.purge_gap),
        int(args.max_folds),
    )
    rows: list[CandidateWalkForwardRow] = []
    for spec in specs:
        train_idx = idx_range(spec.train_start, spec.train_end)
        validation_idx = idx_range(spec.validation_start, spec.validation_end)
        test_idx = idx_range(spec.test_start, spec.test_end)
        train_dist = phase181b.label_distribution(events, train_idx, len(train_idx))
        train_metrics, _ = phase181b.split_metrics(candidate.timeframe, family, frame, atr, "train", train_idx, events, args, None)
        validation_metrics, _ = phase181b.split_metrics(candidate.timeframe, family, frame, atr, "validation", validation_idx, events, args, train_dist)
        test_metrics, _ = phase181b.split_metrics(candidate.timeframe, family, frame, atr, "test", test_idx, events, args, train_dist)
        train_metrics = adjusted_split_metrics(train_metrics, candidate.side_filter, args, "train")
        validation_metrics = adjusted_split_metrics(validation_metrics, candidate.side_filter, args, "validation")
        test_metrics = adjusted_split_metrics(test_metrics, candidate.side_filter, args, "test")
        pass_gate = int(train_metrics.split_pass_gate and validation_metrics.split_pass_gate and test_metrics.split_pass_gate)
        rows.append(
            CandidateWalkForwardRow(
                candidate_id=candidate.candidate_id,
                timeframe=candidate.timeframe,
                family_type=candidate.family_type,
                side_filter=candidate.side_filter,
                fold=int(spec.fold),
                train_events=int(train_metrics.triggered_events),
                validation_events=int(validation_metrics.triggered_events),
                test_events=int(test_metrics.triggered_events),
                train_quality_pass_rate=float(train_metrics.quality_pass_rate),
                validation_quality_pass_rate=float(validation_metrics.quality_pass_rate),
                test_quality_pass_rate=float(test_metrics.quality_pass_rate),
                validation_label_psi=float(validation_metrics.label_psi_vs_train),
                test_label_psi=float(test_metrics.label_psi_vs_train),
                train_gate=int(train_metrics.split_pass_gate),
                validation_gate=int(validation_metrics.split_pass_gate),
                test_gate=int(test_metrics.split_pass_gate),
                pass_gate=pass_gate,
            )
        )
    return rows


def failure_reasons(summary: Mapping[str, Any]) -> list[str]:
    reasons = []
    for key in (
        "density_gate",
        "direction_balance_gate",
        "temporal_stability_gate",
        "mfe_mae_gate",
        "replay_gate",
        "feature_separability_gate",
        "cost_gate",
    ):
        if int(summary.get(key, 0)) == 0:
            reasons.append(f"{key}_failed")
    if float(summary.get("walkforward_pass_ratio", 0.0)) < 0.50:
        reasons.append("walkforward_pass_ratio_failed")
    if int(summary.get("quality_geometry_candidate_ready_gate", 0)) == 0:
        reasons.append("quality_geometry_candidate_ready_gate_failed")
    return reasons


def candidate_summary(
    candidate: QualityCandidateSpec,
    split_rows_by_name: Mapping[str, phase181b.SplitMetricsRow],
    wf_rows: Sequence[CandidateWalkForwardRow],
    cost_gate: int,
    args: argparse.Namespace,
) -> CandidateSummaryRow:
    train = split_rows_by_name["train"]
    validation = split_rows_by_name["validation"]
    test = split_rows_by_name["test"]
    wf_pass = sum(row.pass_gate for row in wf_rows)
    wf_total = len(wf_rows)
    wf_ratio = phase181b.safe_div(wf_pass, wf_total)
    density_gate = int(train.density_gate and validation.density_gate and test.density_gate)
    direction_gate = int(train.direction_balance_gate and validation.direction_balance_gate and test.direction_balance_gate)
    temporal_gate = int(validation.temporal_stability_gate and test.temporal_stability_gate)
    mfe_mae_gate = int(train.mfe_mae_gate and validation.mfe_mae_gate and test.mfe_mae_gate)
    replay_gate = int(train.replay_gate and validation.replay_gate and test.replay_gate)
    feature_gate = int(train.feature_separability_gate and validation.feature_separability_gate and test.feature_separability_gate)
    ready = int(
        density_gate
        and direction_gate
        and temporal_gate
        and mfe_mae_gate
        and replay_gate
        and feature_gate
        and cost_gate
        and wf_total >= int(args.min_walkforward_folds)
        and wf_ratio >= float(args.min_walkforward_pass_ratio)
    )
    temp = {
        "density_gate": density_gate,
        "direction_balance_gate": direction_gate,
        "temporal_stability_gate": temporal_gate,
        "mfe_mae_gate": mfe_mae_gate,
        "replay_gate": replay_gate,
        "feature_separability_gate": feature_gate,
        "cost_gate": cost_gate,
        "walkforward_pass_ratio": wf_ratio,
        "quality_geometry_candidate_ready_gate": ready,
    }
    reasons = failure_reasons(temp)
    diagnostic_score = (
        100.0 * ready
        + 20.0 * wf_ratio
        + 10.0 * min(test.replay_profit_factor, 2.0)
        + 10.0 * test.quality_pass_rate
        + 5.0 * min(validation.replay_profit_factor, 2.0)
        + 5.0 * validation.quality_pass_rate
    )
    return CandidateSummaryRow(
        candidate_id=candidate.candidate_id,
        label=candidate.label,
        timeframe=candidate.timeframe,
        family_type=candidate.family_type,
        side_filter=candidate.side_filter,
        recent_window_bars=int(candidate.recent_window_bars),
        buffer_atr=float(candidate.buffer_atr),
        trigger_horizon_bars=int(candidate.trigger_horizon_bars),
        quality_bars=int(candidate.quality_bars),
        mfe_atr=float(candidate.mfe_atr),
        mae_atr=float(candidate.mae_atr),
        train_events=int(train.triggered_events),
        validation_events=int(validation.triggered_events),
        test_events=int(test.triggered_events),
        train_event_rate=float(train.event_rate),
        validation_event_rate=float(validation.event_rate),
        test_event_rate=float(test.event_rate),
        train_quality_pass_rate=float(train.quality_pass_rate),
        validation_quality_pass_rate=float(validation.quality_pass_rate),
        test_quality_pass_rate=float(test.quality_pass_rate),
        train_replay_profit_factor=float(train.replay_profit_factor),
        validation_replay_profit_factor=float(validation.replay_profit_factor),
        test_replay_profit_factor=float(test.replay_profit_factor),
        train_mean_score=float(train.mean_replay_score_atr),
        validation_mean_score=float(validation.mean_replay_score_atr),
        test_mean_score=float(test.mean_replay_score_atr),
        validation_label_psi=float(validation.label_psi_vs_train),
        test_label_psi=float(test.label_psi_vs_train),
        train_feature_smd=float(train.max_feature_abs_smd),
        validation_feature_smd=float(validation.max_feature_abs_smd),
        test_feature_smd=float(test.max_feature_abs_smd),
        walkforward_folds=int(wf_total),
        walkforward_pass_folds=int(wf_pass),
        walkforward_pass_ratio=float(wf_ratio),
        density_gate=density_gate,
        direction_balance_gate=direction_gate,
        temporal_stability_gate=temporal_gate,
        mfe_mae_gate=mfe_mae_gate,
        replay_gate=replay_gate,
        feature_separability_gate=feature_gate,
        cost_gate=cost_gate,
        quality_geometry_candidate_ready_gate=ready,
        failure_reasons=json.dumps(reasons, ensure_ascii=False),
        diagnostic_score=float(diagnostic_score),
    )


def rank_candidate(row: CandidateSummaryRow) -> tuple[float, float, float, float, float]:
    return (
        float(row.quality_geometry_candidate_ready_gate),
        float(row.walkforward_pass_ratio),
        float(row.validation_replay_profit_factor + row.test_replay_profit_factor),
        float(row.validation_quality_pass_rate + row.test_quality_pass_rate),
        float(row.diagnostic_score),
    )


def decision_matrix(rows: Sequence[CandidateSummaryRow]) -> list[DecisionRow]:
    ready = [row for row in rows if row.quality_geometry_candidate_ready_gate]
    best = max(rows, key=rank_candidate) if rows else None
    best_text = f"{best.timeframe}|{best.candidate_id}" if best else "none"
    return [
        DecisionRow(
            route_id="ENTRY_QUALITY_GEOMETRY_MODEL_PREFLIGHT",
            status="BLOCKED" if not ready else "OWNER_REVIEW_REQUIRED",
            score=0.0 if not ready else 62.0,
            evidence=f"ready_candidates={len(ready)}; best={best_text}",
            recommendation="Do not train; no redesigned quality geometry passed gates." if not ready else "Owner review required before any model preflight.",
        ),
        DecisionRow(
            route_id="ENTRY_GEOMETRY_REDESIGN_CONTINUE",
            status="RECOMMENDED_DIAGNOSTIC" if not ready else "OPTIONAL_REFINEMENT",
            score=75.0 if not ready else 45.0,
            evidence="Phase183A changes target geometry only; it does not relax readiness gates.",
            recommendation="Review candidate failures and decide whether to stop this route or create a narrower Phase184A.",
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="No model or execution gate is opened by Phase183A.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def comparison_rows(rows: Sequence[CandidateSummaryRow], phase182: Mapping[str, Any]) -> list[GeometryComparisonRow]:
    focus = f"{phase182.get('selected_focus_timeframe', '')}|{phase182.get('selected_focus_family_id', '')}"
    current_mfe = 0.0
    current_mae = 0.0
    for row in phase182.get("quality_geometry_rows", []) or []:
        if f"{row.get('timeframe', '')}|{row.get('family_id', '')}" == focus:
            current_mfe = float(row.get("current_mfe_atr", 0.0) or 0.0)
            current_mae = float(row.get("current_mae_atr", 0.0) or 0.0)
            break
    output: list[GeometryComparisonRow] = []
    for row in rows:
        if row.quality_geometry_candidate_ready_gate:
            verdict = "READY_FOR_OWNER_REVIEW"
        elif row.test_replay_profit_factor >= 1.0 and row.validation_replay_profit_factor >= 1.0:
            verdict = "STATIC_REPLAY_NEAR_MISS_WF_FAILED"
        elif row.test_replay_profit_factor >= 1.0:
            verdict = "TEST_ONLY_NOT_TRANSFERRED"
        else:
            verdict = "GEOMETRY_NOT_CONFIRMED"
        output.append(
            GeometryComparisonRow(
                candidate_id=row.candidate_id,
                source_focus=focus,
                current_mfe_atr=float(current_mfe),
                current_mae_atr=float(current_mae),
                candidate_mfe_atr=float(row.mfe_atr),
                candidate_mae_atr=float(row.mae_atr),
                test_quality_pass_rate=float(row.test_quality_pass_rate),
                test_replay_profit_factor=float(row.test_replay_profit_factor),
                walkforward_pass_ratio=float(row.walkforward_pass_ratio),
                verdict=verdict,
            )
        )
    return output


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(str(key))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def render_html(report: Phase183AReport, title: str) -> str:
    candidates = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['family_type']))}</td>"
        f"<td>{html.escape(str(row['side_filter']))}</td>"
        f"<td>{float(row['validation_replay_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_replay_profit_factor']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['quality_geometry_candidate_ready_gate'])}</td>"
        "</tr>"
        for row in report.candidate_rows[:30]
    )
    decisions = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['route_id']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{float(row['score']):.1f}</td>"
        f"<td>{html.escape(str(row['recommendation']))}</td>"
        "</tr>"
        for row in report.decision_matrix
    )
    summary = html.escape(
        json.dumps(
            {
                "ready_candidates": report.ready_candidates,
                "selected": report.selected_candidate_id,
                "ready_gate": report.quality_geometry_redesign_ready_gate,
                "production_status": report.production_status,
            },
            indent=2,
        )
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;background:#10131a;color:#eef2ff;margin:0;padding:24px}}
section{{background:#171b25;border:1px solid #2b3242;border-radius:14px;padding:18px;margin:16px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #303849;padding:8px;text-align:left}}th{{color:#a7c7ff}}pre{{white-space:pre-wrap;background:#0b0e14;padding:12px;border-radius:10px}}
</style></head><body>
<section><h1>{html.escape(title)}</h1><p><strong>{html.escape(report.production_status)}</strong></p><pre>{summary}</pre></section>
<section><h2>Candidates</h2><table><thead><tr><th>Candidate</th><th>TF</th><th>Type</th><th>Side</th><th>Val PF</th><th>Test PF</th><th>WF</th><th>Ready</th></tr></thead><tbody>{candidates}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase183AReport:
    args = parse_args(argv)
    phase182 = load_json_optional(Path(args.phase182a_path))
    phase181 = load_json_optional(Path(args.phase181b_path))
    candidates = parse_candidates(args.candidates)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames: dict[str, Any] = {}
    atrs: dict[str, np.ndarray] = {}
    costs: dict[str, int] = {}
    for timeframe in sorted({candidate.timeframe for candidate in candidates}):
        mini_args = phase181b.parse_args(
            [
                "--symbol", str(args.symbol),
                "--timeframes", timeframe,
                "--h1-flat-path", str(args.h1_flat_path),
                "--h4-flat-path", str(args.h4_flat_path),
                "--d1-flat-path", str(args.d1_flat_path),
                "--max-rows", str(max(int(args.max_rows), 0)),
                "--spread-mode", str(args.spread_mode),
                "--spread-value", str(float(args.spread_value)),
            ]
        )
        path = phase181b.resolve_flat_path(timeframe, mini_args)
        frame = phase181b.read_ohlc_frame(path, int(args.max_rows))
        atr = phase181b.wilder_atr(
            frame["high"].to_numpy(dtype=np.float64),
            frame["low"].to_numpy(dtype=np.float64),
            frame["close"].to_numpy(dtype=np.float64),
        )
        frames[timeframe] = frame
        atrs[timeframe] = atr
        train_idx, validation_idx, test_idx = phase181b.split_indices(len(frame), float(args.train_frac), float(args.val_frac), int(args.purge_gap))
        split_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
        cost_rows = [phase181b.cost_row(timeframe, split, frame, idx, atr, args) for split, idx in split_map.items()]
        costs[timeframe] = int(all(row.cost_feasible_gate for row in cost_rows)) if cost_rows else 0

    all_events: list[dict[str, Any]] = []
    all_replay: list[dict[str, Any]] = []
    split_rows: list[CandidateSplitRow] = []
    walk_rows: list[CandidateWalkForwardRow] = []
    summary_rows: list[CandidateSummaryRow] = []

    for candidate in candidates:
        frame = frames[candidate.timeframe]
        atr = atrs[candidate.timeframe]
        family = to_entry_family(candidate)
        train_idx, validation_idx, test_idx = phase181b.split_indices(len(frame), float(args.train_frac), float(args.val_frac), int(args.purge_gap))
        split_index_map = {"train": train_idx, "validation": validation_idx, "test": test_idx}
        raw_events = phase181b.discover_family_events(candidate.timeframe, family, frame, atr, args)
        events = filter_events(raw_events, candidate.side_filter)
        train_dist = phase181b.label_distribution(events, train_idx, len(train_idx))
        metrics_by_name: dict[str, phase181b.SplitMetricsRow] = {}
        for split, idx in split_index_map.items():
            metrics, _features = phase181b.split_metrics(
                candidate.timeframe,
                family,
                frame,
                atr,
                split,
                idx,
                events,
                args,
                None if split == "train" else train_dist,
            )
            metrics = adjusted_split_metrics(metrics, candidate.side_filter, args, split)
            metrics_by_name[split] = metrics
            split_rows.append(split_metric_row(candidate, metrics))
        wf_rows = walkforward_rows(candidate, family, frame, atr, events, args)
        walk_rows.extend(wf_rows)
        summary = candidate_summary(candidate, metrics_by_name, wf_rows, costs.get(candidate.timeframe, 0), args)
        summary_rows.append(summary)
        export_events = events[: int(args.max_event_rows)] if int(args.max_event_rows) > 0 else events
        for event in export_events:
            row = asdict(event)
            row["candidate_id"] = candidate.candidate_id
            row["side_filter"] = candidate.side_filter
            all_events.append(row)
            if event.trigger_gate:
                all_replay.append(row)

    ranked = sorted(summary_rows, key=rank_candidate, reverse=True)
    selected = ranked[0] if ranked else None
    ready_count = sum(row.quality_geometry_candidate_ready_gate for row in ranked)
    decisions = decision_matrix(ranked)
    comparisons = comparison_rows(ranked, phase182)

    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    output_candidates = output_dir / "latest_candidates.csv"
    output_splits = output_dir / "latest_splits.csv"
    output_wf = output_dir / "latest_walkforward.csv"
    output_events = output_dir / "latest_events.csv"
    output_replay = output_dir / "latest_replay.csv"
    output_comparison = output_dir / "latest_geometry_comparison.csv"
    output_decisions = output_dir / "latest_decision_matrix.csv"

    candidate_dicts = [asdict(row) for row in ranked]
    split_dicts = [asdict(row) for row in split_rows]
    wf_dicts = [asdict(row) for row in walk_rows]
    comparison_dicts = [asdict(row) for row in comparisons]
    decision_dicts = [asdict(row) for row in decisions]

    report = Phase183AReport(
        phase182a_path=str(args.phase182a_path),
        source_symbol=str(phase181.get("symbol", args.symbol)),
        source_focus=f"{phase182.get('selected_focus_timeframe', '')}|{phase182.get('selected_focus_family_id', '')}",
        evaluated_candidates=len(ranked),
        ready_candidates=int(ready_count),
        selected_candidate_id=selected.candidate_id if selected else "",
        selected_timeframe=selected.timeframe if selected else "",
        selected_family_type=selected.family_type if selected else "",
        selected_side_filter=selected.side_filter if selected else "",
        selected_candidate_ready_gate=int(selected.quality_geometry_candidate_ready_gate) if selected else 0,
        selected_test_quality_pass_rate=float(selected.test_quality_pass_rate) if selected else 0.0,
        selected_test_replay_profit_factor=float(selected.test_replay_profit_factor) if selected else 0.0,
        selected_walkforward_pass_ratio=float(selected.walkforward_pass_ratio) if selected else 0.0,
        quality_geometry_redesign_ready_gate=int(ready_count > 0),
        no_training_gate=1,
        no_paper_live_gate=1,
        recommendation=(
            "OWNER_REVIEW_BEFORE_MODEL_PREFLIGHT" if ready_count > 0 else "NO_QUALITY_GEOMETRY_READY_STOP_OR_NARROWER_DIAGNOSTIC"
        ),
        candidate_rows=candidate_dicts,
        split_rows=split_dicts,
        walkforward_rows=wf_dicts,
        geometry_comparison_rows=comparison_dicts,
        decision_matrix=decision_dicts,
        output_json=str(output_json),
        output_html=str(output_html),
        output_candidates_csv=str(output_candidates),
        output_splits_csv=str(output_splits),
        output_walkforward_csv=str(output_wf),
        output_events_csv=str(output_events),
        output_replay_csv=str(output_replay),
        output_geometry_comparison_csv=str(output_comparison),
        output_decision_matrix_csv=str(output_decisions),
        production_status="BLOCKED — Phase183A quality-geometry audit only; no model training/paper/live",
    )

    write_csv(output_candidates, candidate_dicts)
    write_csv(output_splits, split_dicts)
    write_csv(output_wf, wf_dicts)
    write_csv(output_events, all_events)
    write_csv(output_replay, all_replay)
    write_csv(output_comparison, comparison_dicts)
    write_csv(output_decisions, decision_dicts)
    output_html.write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    output_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[DONE] Phase183A entry quality-geometry candidate audit complete")
    print(f"  candidates : {report.evaluated_candidates}")
    print(f"  ready      : {report.ready_candidates}")
    print(f"  selected   : {report.selected_timeframe}|{report.selected_candidate_id}" if report.selected_candidate_id else "  selected   : none")
    print(f"  ready gate : {report.quality_geometry_redesign_ready_gate}")
    print(f"  json       : {report.output_json}")
    print(f"  html       : {report.output_html}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
