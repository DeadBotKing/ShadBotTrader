"""Phase182A: Entry-event failure attribution / quality-geometry decision.

Phase181B separated entry events from profit targets and found that entry-event
families were often stable, separable and cost-feasible, but failed MFE/MAE,
replay and walk-forward gates. This phase consumes the Phase181B outputs and
attributes those failures before any redesign or model training.

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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

DEFAULT_OUTPUT_DIR = Path("run_logs/entry_event_failure_attribution")


@dataclass(frozen=True)
class FamilyAttributionRow:
    timeframe: str
    family_id: str
    family_type: str
    train_events: int
    validation_events: int
    test_events: int
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    train_replay_profit_factor: float
    validation_replay_profit_factor: float
    test_replay_profit_factor: float
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
    entry_family_ready_gate: int
    failure_reason_count: int
    primary_failure_reason: str
    near_miss_gate: int
    attribution_bucket: str
    recommendation: str


@dataclass(frozen=True)
class SideAttributionRow:
    timeframe: str
    family_id: str
    family_type: str
    side: str
    triggered_events: int
    quality_pass_events: int
    quality_pass_rate: float
    mean_mfe_atr: float
    mean_mae_atr: float
    median_mfe_atr: float
    median_mae_atr: float
    mfe_mae_ratio: float
    replay_profit_factor: float
    mean_replay_score_atr: float
    fail_mae_first_rate: float
    timeout_rate: float
    pass_mfe_first_rate: float
    side_verdict: str


@dataclass(frozen=True)
class TimeframeAttributionRow:
    timeframe: str
    family_count: int
    ready_families: int
    near_miss_families: int
    total_test_events: int
    best_family_id: str
    best_family_type: str
    best_test_quality_pass_rate: float
    best_test_replay_profit_factor: float
    best_walkforward_pass_ratio: float
    dominant_failure_reason: str
    timeframe_verdict: str


@dataclass(frozen=True)
class QualityGeometryRow:
    timeframe: str
    family_id: str
    family_type: str
    current_mfe_atr: float
    current_mae_atr: float
    triggered_events: int
    mfe_p50: float
    mfe_p75: float
    mfe_p90: float
    mae_p50: float
    mae_p75: float
    mae_p90: float
    pct_mfe_ge_current: float
    pct_mae_le_current: float
    pct_mfe_ge_current_and_mae_le_current: float
    median_trigger_delay_bars: float
    trigger_delay_p75_bars: float
    quality_geometry_verdict: str


@dataclass(frozen=True)
class WalkForwardAttributionRow:
    timeframe: str
    family_id: str
    family_type: str
    folds: int
    pass_folds: int
    train_gate_failed_folds: int
    validation_gate_failed_folds: int
    test_gate_failed_folds: int
    worst_test_quality_pass_rate: float
    best_test_quality_pass_rate: float
    worst_test_event_rate: float
    best_test_event_rate: float
    walkforward_verdict: str


@dataclass(frozen=True)
class FailureReasonRow:
    reason: str
    count: int
    share: float
    example: str


@dataclass(frozen=True)
class DecisionRow:
    route_id: str
    status: str
    score: float
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class NextPlanRow:
    step: int
    phase: str
    action: str
    purpose: str
    allowed: str


@dataclass(frozen=True)
class Phase182AReport:
    phase181b_path: str
    source_symbol: str
    source_timeframes: list[str]
    source_ready_families: int
    source_entry_event_discovery_ready_gate: int
    family_rows: int
    near_miss_families: int
    selected_focus_timeframe: str
    selected_focus_family_id: str
    selected_focus_family_type: str
    selected_primary_failure_reason: str
    selected_next_route_id: str
    selected_next_phase: str
    no_training_gate: int
    no_paper_live_gate: int
    root_cause_summary: str
    family_attribution_rows: list[dict[str, Any]]
    side_attribution_rows: list[dict[str, Any]]
    timeframe_attribution_rows: list[dict[str, Any]]
    quality_geometry_rows: list[dict[str, Any]]
    walkforward_attribution_rows: list[dict[str, Any]]
    failure_reason_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    next_plan: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_family_attribution_csv: str
    output_side_attribution_csv: str
    output_timeframe_attribution_csv: str
    output_quality_geometry_csv: str
    output_walkforward_attribution_csv: str
    output_failure_reasons_csv: str
    output_decision_matrix_csv: str
    output_next_plan_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase182A entry-event failure attribution and quality-geometry decision.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase181b-path", default="run_logs/entry_event_discovery/latest.json")
    parser.add_argument("--events-path", default="")
    parser.add_argument("--replay-path", default="")
    parser.add_argument("--splits-path", default="")
    parser.add_argument("--walkforward-path", default="")
    parser.add_argument("--min-near-miss-test-pf", type=float, default=1.0)
    parser.add_argument("--min-near-miss-test-quality", type=float, default=0.35)
    parser.add_argument("--min-near-miss-feature-smd", type=float, default=0.25)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase182A entry-event failure attribution")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Phase181B json not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def csv_path(payload: Mapping[str, Any], override: str, key: str) -> Path | None:
    value = str(override or "").strip() or str(payload.get(key, "")).strip()
    if not value:
        return None
    return Path(value)


def read_csv_optional(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    if path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def as_float(row: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, default)
        if value is None or value == "":
            return float(default)
        number = float(value)
        if not np.isfinite(number):
            return float(default)
        return number
    except Exception:
        return float(default)


def as_int(row: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except Exception:
        return int(default)


def parse_reasons(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return [str(item) for item in value]
    except Exception:
        pass
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def percentile(values: Sequence[float], pct: float) -> float:
    data = np.asarray([float(value) for value in values if np.isfinite(float(value))], dtype=np.float64)
    if len(data) == 0:
        return 0.0
    return float(np.percentile(data, pct))


def family_primary_failure(row: Mapping[str, Any]) -> str:
    reasons = parse_reasons(row.get("failure_reasons", ""))
    preferred = [
        "mfe_mae_gate_failed",
        "replay_gate_failed",
        "walkforward_pass_ratio_failed",
        "density_gate_failed",
        "direction_balance_gate_failed",
        "temporal_stability_gate_failed",
        "feature_separability_gate_failed",
        "cost_gate_failed",
        "entry_family_ready_gate_failed",
    ]
    for reason in preferred:
        if reason in reasons:
            return reason
    return reasons[0] if reasons else "none"


def near_miss_gate(row: Mapping[str, Any], args: argparse.Namespace) -> int:
    structural_ok = all(
        as_int(row, key) == 1
        for key in (
            "density_gate",
            "direction_balance_gate",
            "temporal_stability_gate",
            "feature_separability_gate",
            "cost_gate",
        )
    )
    if not structural_ok or as_int(row, "entry_family_ready_gate") != 0:
        return 0
    test_pf = as_float(row, "test_replay_profit_factor")
    test_quality = as_float(row, "test_quality_pass_rate")
    feature = max(
        as_float(row, "train_feature_smd"),
        as_float(row, "validation_feature_smd"),
        as_float(row, "test_feature_smd"),
    )
    return int(
        feature >= float(args.min_near_miss_feature_smd)
        and (
            test_pf >= float(args.min_near_miss_test_pf)
            or test_quality >= float(args.min_near_miss_test_quality)
        )
    )


def attribution_bucket(row: Mapping[str, Any]) -> tuple[str, str]:
    if as_int(row, "mfe_mae_gate") == 0 and as_int(row, "replay_gate") == 0:
        return (
            "QUALITY_AND_REPLAY_FAILURE",
            "Redesign trigger/entry/quality geometry before considering any model.",
        )
    if as_int(row, "mfe_mae_gate") == 0:
        return "QUALITY_GEOMETRY_FAILURE", "Audit MFE/MAE thresholds and trigger placement."
    if as_int(row, "replay_gate") == 0:
        return "REPLAY_ECONOMICS_FAILURE", "Audit broker-cost-adjusted replay by side and timeframe."
    if as_float(row, "walkforward_pass_ratio") <= 0:
        return "WALKFORWARD_TRANSFER_FAILURE", "Audit fold instability before redesign."
    if as_int(row, "density_gate") == 0:
        return "DENSITY_FAILURE", "Redesign event density; target is too sparse or too broad."
    return "MIXED_FAILURE", "Review detailed side/timeframe attribution."


def build_family_attribution_rows(payload: Mapping[str, Any], args: argparse.Namespace) -> list[FamilyAttributionRow]:
    rows: list[FamilyAttributionRow] = []
    for raw in payload.get("family_rows", []) or []:
        if not isinstance(raw, Mapping):
            continue
        reasons = parse_reasons(raw.get("failure_reasons", ""))
        primary = family_primary_failure(raw)
        bucket, recommendation = attribution_bucket(raw)
        rows.append(
            FamilyAttributionRow(
                timeframe=str(raw.get("timeframe", "")),
                family_id=str(raw.get("family_id", "")),
                family_type=str(raw.get("family_type", "")),
                train_events=as_int(raw, "train_events"),
                validation_events=as_int(raw, "validation_events"),
                test_events=as_int(raw, "test_events"),
                train_quality_pass_rate=as_float(raw, "train_quality_pass_rate"),
                validation_quality_pass_rate=as_float(raw, "validation_quality_pass_rate"),
                test_quality_pass_rate=as_float(raw, "test_quality_pass_rate"),
                train_replay_profit_factor=as_float(raw, "train_replay_profit_factor"),
                validation_replay_profit_factor=as_float(raw, "validation_replay_profit_factor"),
                test_replay_profit_factor=as_float(raw, "test_replay_profit_factor"),
                train_feature_smd=as_float(raw, "train_feature_smd"),
                validation_feature_smd=as_float(raw, "validation_feature_smd"),
                test_feature_smd=as_float(raw, "test_feature_smd"),
                walkforward_folds=as_int(raw, "walkforward_folds"),
                walkforward_pass_folds=as_int(raw, "walkforward_pass_folds"),
                walkforward_pass_ratio=as_float(raw, "walkforward_pass_ratio"),
                density_gate=as_int(raw, "density_gate"),
                direction_balance_gate=as_int(raw, "direction_balance_gate"),
                temporal_stability_gate=as_int(raw, "temporal_stability_gate"),
                mfe_mae_gate=as_int(raw, "mfe_mae_gate"),
                replay_gate=as_int(raw, "replay_gate"),
                feature_separability_gate=as_int(raw, "feature_separability_gate"),
                cost_gate=as_int(raw, "cost_gate"),
                entry_family_ready_gate=as_int(raw, "entry_family_ready_gate"),
                failure_reason_count=len(reasons),
                primary_failure_reason=primary,
                near_miss_gate=near_miss_gate(raw, args),
                attribution_bucket=bucket,
                recommendation=recommendation,
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            row.near_miss_gate,
            row.test_replay_profit_factor,
            row.test_quality_pass_rate,
            row.validation_replay_profit_factor,
            row.train_replay_profit_factor,
        ),
        reverse=True,
    )


def side_attribution_rows(replay: pd.DataFrame) -> list[SideAttributionRow]:
    if replay.empty:
        return []
    rows: list[SideAttributionRow] = []
    group_cols = ["timeframe", "family_id", "family_type", "side"]
    for keys, group in replay.groupby(group_cols, dropna=False):
        timeframe, family_id, family_type, side = [str(item) for item in keys]
        scores = pd.to_numeric(group.get("replay_score_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        mfe = pd.to_numeric(group.get("mfe_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        mae = pd.to_numeric(group.get("mae_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        quality = pd.to_numeric(group.get("quality_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        outcomes = group.get("replay_outcome", pd.Series([], dtype=str)).astype(str)
        triggered = len(group)
        pf = profit_factor(scores.tolist())
        quality_rate = float(np.mean(quality)) if len(quality) else 0.0
        fail_mae_first_rate = float(outcomes.str.contains("fail", case=False, regex=False).mean()) if len(outcomes) else 0.0
        timeout_rate = float((outcomes == "timeout").mean()) if len(outcomes) else 0.0
        pass_mfe_first_rate = float(outcomes.str.contains("pass", case=False, regex=False).mean()) if len(outcomes) else 0.0
        ratio = float(np.mean(mfe) / max(np.mean(mae), 1e-9)) if len(mfe) and len(mae) else 0.0
        verdict = "SIDE_NEAR_MISS" if pf >= 1.0 and quality_rate >= 0.30 else "SIDE_FAILED"
        rows.append(
            SideAttributionRow(
                timeframe=timeframe,
                family_id=family_id,
                family_type=family_type,
                side=side,
                triggered_events=int(triggered),
                quality_pass_events=int(np.sum(quality)),
                quality_pass_rate=quality_rate,
                mean_mfe_atr=float(np.mean(mfe)) if len(mfe) else 0.0,
                mean_mae_atr=float(np.mean(mae)) if len(mae) else 0.0,
                median_mfe_atr=float(np.median(mfe)) if len(mfe) else 0.0,
                median_mae_atr=float(np.median(mae)) if len(mae) else 0.0,
                mfe_mae_ratio=ratio,
                replay_profit_factor=float(pf),
                mean_replay_score_atr=float(np.mean(scores)) if len(scores) else 0.0,
                fail_mae_first_rate=fail_mae_first_rate,
                timeout_rate=timeout_rate,
                pass_mfe_first_rate=pass_mfe_first_rate,
                side_verdict=verdict,
            )
        )
    return sorted(rows, key=lambda row: (row.replay_profit_factor, row.quality_pass_rate, row.triggered_events), reverse=True)


def quality_geometry_rows(payload: Mapping[str, Any], replay: pd.DataFrame) -> list[QualityGeometryRow]:
    if replay.empty:
        return []
    family_lookup = {
        (str(row.get("timeframe", "")), str(row.get("family_id", ""))): row
        for row in payload.get("family_rows", []) or []
        if isinstance(row, Mapping)
    }
    rows: list[QualityGeometryRow] = []
    for (timeframe, family_id, family_type), group in replay.groupby(["timeframe", "family_id", "family_type"], dropna=False):
        key = (str(timeframe), str(family_id))
        family = family_lookup.get(key, {})
        current_mfe = as_float(family, "mfe_atr")
        current_mae = as_float(family, "mae_atr")
        mfe = pd.to_numeric(group.get("mfe_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        mae = pd.to_numeric(group.get("mae_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        setup = pd.to_numeric(group.get("setup_row", 0), errors="coerce").fillna(0).to_numpy(dtype=float)
        trigger = pd.to_numeric(group.get("trigger_row", 0), errors="coerce").fillna(0).to_numpy(dtype=float)
        delay = np.maximum(trigger - setup, 0.0)
        pct_mfe = float(np.mean(mfe >= current_mfe)) if len(mfe) else 0.0
        pct_mae = float(np.mean(mae <= current_mae)) if len(mae) else 0.0
        pct_both = float(np.mean((mfe >= current_mfe) & (mae <= current_mae))) if len(mfe) else 0.0
        if pct_mfe < 0.35 and pct_mae < 0.50:
            verdict = "MFE_TOO_FAR_AND_MAE_TOO_TIGHT"
        elif pct_mfe < 0.35:
            verdict = "MFE_TARGET_TOO_FAR"
        elif pct_mae < 0.50:
            verdict = "MAE_LIMIT_TOO_TIGHT_OR_ENTRY_LATE"
        elif pct_both < 0.35:
            verdict = "ORDER_OR_PATH_QUALITY_FAILURE"
        else:
            verdict = "DISTRIBUTION_NEAR_MISS_ORDER_NEEDS_AUDIT"
        rows.append(
            QualityGeometryRow(
                timeframe=str(timeframe),
                family_id=str(family_id),
                family_type=str(family_type),
                current_mfe_atr=float(current_mfe),
                current_mae_atr=float(current_mae),
                triggered_events=int(len(group)),
                mfe_p50=percentile(mfe, 50),
                mfe_p75=percentile(mfe, 75),
                mfe_p90=percentile(mfe, 90),
                mae_p50=percentile(mae, 50),
                mae_p75=percentile(mae, 75),
                mae_p90=percentile(mae, 90),
                pct_mfe_ge_current=pct_mfe,
                pct_mae_le_current=pct_mae,
                pct_mfe_ge_current_and_mae_le_current=pct_both,
                median_trigger_delay_bars=percentile(delay, 50),
                trigger_delay_p75_bars=percentile(delay, 75),
                quality_geometry_verdict=verdict,
            )
        )
    return sorted(rows, key=lambda row: (row.pct_mfe_ge_current_and_mae_le_current, row.pct_mfe_ge_current), reverse=True)


def walkforward_attribution_rows(walkforward: pd.DataFrame) -> list[WalkForwardAttributionRow]:
    if walkforward.empty:
        return []
    rows: list[WalkForwardAttributionRow] = []
    for (timeframe, family_id, family_type), group in walkforward.groupby(["timeframe", "family_id", "family_type"], dropna=False):
        pass_gate = pd.to_numeric(group.get("pass_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        train_gate = pd.to_numeric(group.get("train_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        val_gate = pd.to_numeric(group.get("validation_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        test_gate = pd.to_numeric(group.get("test_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        test_quality = pd.to_numeric(group.get("test_quality_pass_rate", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        test_rate = pd.to_numeric(group.get("test_event_rate", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        verdict = "WF_ZERO_TRANSFER" if int(np.sum(pass_gate)) == 0 else "WF_PARTIAL_TRANSFER"
        rows.append(
            WalkForwardAttributionRow(
                timeframe=str(timeframe),
                family_id=str(family_id),
                family_type=str(family_type),
                folds=int(len(group)),
                pass_folds=int(np.sum(pass_gate)),
                train_gate_failed_folds=int(np.sum(train_gate == 0)),
                validation_gate_failed_folds=int(np.sum(val_gate == 0)),
                test_gate_failed_folds=int(np.sum(test_gate == 0)),
                worst_test_quality_pass_rate=float(np.min(test_quality)) if len(test_quality) else 0.0,
                best_test_quality_pass_rate=float(np.max(test_quality)) if len(test_quality) else 0.0,
                worst_test_event_rate=float(np.min(test_rate)) if len(test_rate) else 0.0,
                best_test_event_rate=float(np.max(test_rate)) if len(test_rate) else 0.0,
                walkforward_verdict=verdict,
            )
        )
    return sorted(rows, key=lambda row: (row.pass_folds, row.best_test_quality_pass_rate), reverse=True)


def failure_reason_rows(families: Sequence[FamilyAttributionRow]) -> list[FailureReasonRow]:
    counts: dict[str, int] = {}
    examples: dict[str, str] = {}
    for row in families:
        for reason in (
            row.primary_failure_reason,
            "walkforward_pass_ratio_failed" if row.walkforward_pass_ratio <= 0 else "",
            "entry_family_ready_gate_failed" if row.entry_family_ready_gate == 0 else "",
        ):
            if not reason or reason == "none":
                continue
            counts[reason] = counts.get(reason, 0) + 1
            examples.setdefault(reason, f"{row.timeframe}|{row.family_id}")
    total = max(len(families), 1)
    return sorted(
        [
            FailureReasonRow(reason=reason, count=count, share=count / total, example=examples.get(reason, ""))
            for reason, count in counts.items()
        ],
        key=lambda row: row.count,
        reverse=True,
    )


def timeframe_attribution_rows(families: Sequence[FamilyAttributionRow]) -> list[TimeframeAttributionRow]:
    rows: list[TimeframeAttributionRow] = []
    by_tf: dict[str, list[FamilyAttributionRow]] = {}
    for row in families:
        by_tf.setdefault(row.timeframe, []).append(row)
    for timeframe, group in by_tf.items():
        best = max(
            group,
            key=lambda row: (
                row.near_miss_gate,
                row.test_replay_profit_factor,
                row.test_quality_pass_rate,
                row.validation_replay_profit_factor,
            ),
        )
        failures = failure_reason_rows(group)
        dominant = failures[0].reason if failures else "none"
        verdict = "NEAR_MISS_ONLY" if any(row.near_miss_gate for row in group) else "NO_USABLE_ENTRY_FAMILY"
        rows.append(
            TimeframeAttributionRow(
                timeframe=timeframe,
                family_count=len(group),
                ready_families=sum(row.entry_family_ready_gate for row in group),
                near_miss_families=sum(row.near_miss_gate for row in group),
                total_test_events=sum(row.test_events for row in group),
                best_family_id=best.family_id,
                best_family_type=best.family_type,
                best_test_quality_pass_rate=best.test_quality_pass_rate,
                best_test_replay_profit_factor=best.test_replay_profit_factor,
                best_walkforward_pass_ratio=best.walkforward_pass_ratio,
                dominant_failure_reason=dominant,
                timeframe_verdict=verdict,
            )
        )
    return sorted(rows, key=lambda row: (row.near_miss_families, row.best_test_replay_profit_factor), reverse=True)


def decision_matrix(families: Sequence[FamilyAttributionRow]) -> list[DecisionRow]:
    near_miss = [row for row in families if row.near_miss_gate]
    best_text = f"{near_miss[0].timeframe}|{near_miss[0].family_id}" if near_miss else "none"
    return [
        DecisionRow(
            route_id="ENTRY_EVENT_MODEL_TRAINING",
            status="BLOCKED",
            score=0.0,
            evidence=f"ready_families=0; near_miss_families={len(near_miss)}; best_near_miss={best_text}",
            recommendation="Do not train; Phase181B families did not pass discovery gates.",
        ),
        DecisionRow(
            route_id="ENTRY_QUALITY_GEOMETRY_REDESIGN",
            status="RECOMMENDED_DIAGNOSTIC" if near_miss else "OWNER_REVIEW_REQUIRED",
            score=82.0 if near_miss else 45.0,
            evidence="Failures concentrate in MFE/MAE, replay and walk-forward while cost/health/stability often pass.",
            recommendation=(
                "Build a diagnostic-only quality-geometry candidate audit focused on trigger timing and MFE/MAE thresholds."
                if near_miss
                else "No strong near-miss found; owner should decide whether to stop or redefine entry families."
            ),
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="No entry family passed discovery gates and this phase performs no execution approval.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def next_plan(families: Sequence[FamilyAttributionRow]) -> list[NextPlanRow]:
    focus = [row for row in families if row.near_miss_gate][:3]
    focus_text = ", ".join(f"{row.timeframe}|{row.family_id}" for row in focus) or "none"
    return [
        NextPlanRow(
            step=1,
            phase="Phase182A",
            action="Record failure attribution and freeze Phase181B as non-training-ready.",
            purpose="Protect project from training on stable-but-unclean entry events.",
            allowed="DONE_BY_THIS_PHASE",
        ),
        NextPlanRow(
            step=2,
            phase="Phase183A",
            action=f"Audit quality-geometry candidates for near-miss families: {focus_text}.",
            purpose="Test whether trigger placement, MFE target or MAE limit can be redesigned without relaxing gates blindly.",
            allowed="DIAGNOSTIC_ONLY_WITH_OWNER_APPROVAL",
        ),
        NextPlanRow(
            step=3,
            phase="Owner review",
            action="Approve or reject any new entry-geometry candidate before model preflight.",
            purpose="Prevent uncontrolled route expansion.",
            allowed="NO_MODEL_TRAINING_YET",
        ),
    ]


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


def render_html(report: Phase182AReport, title: str) -> str:
    families = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['family_id']))}</td>"
        f"<td>{html.escape(str(row['primary_failure_reason']))}</td>"
        f"<td>{int(row['near_miss_gate'])}</td>"
        f"<td>{float(row['test_replay_profit_factor']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        "</tr>"
        for row in report.family_attribution_rows[:20]
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
                "near_miss_families": report.near_miss_families,
                "selected_focus": f"{report.selected_focus_timeframe}|{report.selected_focus_family_id}",
                "next_phase": report.selected_next_phase,
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
<section><h2>Family attribution</h2><table><thead><tr><th>TF</th><th>Family</th><th>Primary failure</th><th>Near miss</th><th>Test PF</th><th>WF pass</th></tr></thead><tbody>{families}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase182AReport:
    args = parse_args(argv)
    phase181b_path = Path(args.phase181b_path)
    payload = load_json(phase181b_path)

    replay = read_csv_optional(csv_path(payload, args.replay_path, "output_replay_csv"))
    if replay.empty:
        events = read_csv_optional(csv_path(payload, args.events_path, "output_events_csv"))
        if not events.empty and "trigger_gate" in events.columns:
            replay = events[pd.to_numeric(events["trigger_gate"], errors="coerce").fillna(0).astype(int) == 1].copy()
    splits = read_csv_optional(csv_path(payload, args.splits_path, "output_splits_csv"))
    walkforward = read_csv_optional(csv_path(payload, args.walkforward_path, "output_walkforward_csv"))

    family_attr = build_family_attribution_rows(payload, args)
    side_attr = side_attribution_rows(replay)
    quality_attr = quality_geometry_rows(payload, replay)
    wf_attr = walkforward_attribution_rows(walkforward)
    failure_attr = failure_reason_rows(family_attr)
    tf_attr = timeframe_attribution_rows(family_attr)
    decisions = decision_matrix(family_attr)
    plan = next_plan(family_attr)

    near_misses = [row for row in family_attr if row.near_miss_gate]
    selected = near_misses[0] if near_misses else (family_attr[0] if family_attr else None)
    primary_failure = selected.primary_failure_reason if selected else "none"
    selected_next_phase = (
        "Phase183A — entry quality-geometry candidate audit"
        if near_misses
        else "Owner review — stop or redefine entry event families"
    )
    selected_next_route = "ENTRY_QUALITY_GEOMETRY_REDESIGN" if near_misses else "STOP_OR_REDEFINE_ENTRY_EVENT_ROUTE"
    root_summary = (
        "Phase181B did not fail because of data health or broker cost. Entry events are often stable and feature-separable, "
        "but triggered entries fail MFE/MAE quality, replay economics and walk-forward transfer."
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    output_family = output_dir / "latest_family_attribution.csv"
    output_side = output_dir / "latest_side_attribution.csv"
    output_tf = output_dir / "latest_timeframe_attribution.csv"
    output_quality = output_dir / "latest_quality_geometry.csv"
    output_wf = output_dir / "latest_walkforward_attribution.csv"
    output_failures = output_dir / "latest_failure_reasons.csv"
    output_decisions = output_dir / "latest_decision_matrix.csv"
    output_plan = output_dir / "latest_next_plan.csv"

    report = Phase182AReport(
        phase181b_path=str(phase181b_path),
        source_symbol=str(payload.get("symbol", "")),
        source_timeframes=[str(item) for item in payload.get("timeframes", [])],
        source_ready_families=as_int(payload, "ready_families"),
        source_entry_event_discovery_ready_gate=as_int(payload, "entry_event_discovery_ready_gate"),
        family_rows=len(family_attr),
        near_miss_families=len(near_misses),
        selected_focus_timeframe=selected.timeframe if selected else "",
        selected_focus_family_id=selected.family_id if selected else "",
        selected_focus_family_type=selected.family_type if selected else "",
        selected_primary_failure_reason=primary_failure,
        selected_next_route_id=selected_next_route,
        selected_next_phase=selected_next_phase,
        no_training_gate=1,
        no_paper_live_gate=1,
        root_cause_summary=root_summary,
        family_attribution_rows=[asdict(row) for row in family_attr],
        side_attribution_rows=[asdict(row) for row in side_attr],
        timeframe_attribution_rows=[asdict(row) for row in tf_attr],
        quality_geometry_rows=[asdict(row) for row in quality_attr],
        walkforward_attribution_rows=[asdict(row) for row in wf_attr],
        failure_reason_rows=[asdict(row) for row in failure_attr],
        decision_matrix=[asdict(row) for row in decisions],
        next_plan=[asdict(row) for row in plan],
        output_json=str(output_json),
        output_html=str(output_html),
        output_family_attribution_csv=str(output_family),
        output_side_attribution_csv=str(output_side),
        output_timeframe_attribution_csv=str(output_tf),
        output_quality_geometry_csv=str(output_quality),
        output_walkforward_attribution_csv=str(output_wf),
        output_failure_reasons_csv=str(output_failures),
        output_decision_matrix_csv=str(output_decisions),
        output_next_plan_csv=str(output_plan),
        production_status="BLOCKED — Phase182A failure attribution only; no model training/paper/live",
    )

    write_csv(output_family, report.family_attribution_rows)
    write_csv(output_side, report.side_attribution_rows)
    write_csv(output_tf, report.timeframe_attribution_rows)
    write_csv(output_quality, report.quality_geometry_rows)
    write_csv(output_wf, report.walkforward_attribution_rows)
    write_csv(output_failures, report.failure_reason_rows)
    write_csv(output_decisions, report.decision_matrix)
    write_csv(output_plan, report.next_plan)
    output_html.write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    output_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[DONE] Phase182A entry-event failure attribution complete")
    print(f"  phase181b       : {report.phase181b_path}")
    print(f"  families        : {report.family_rows}")
    print(f"  near_miss       : {report.near_miss_families}")
    print(f"  focus           : {report.selected_focus_timeframe}|{report.selected_focus_family_id}" if report.selected_focus_family_id else "  focus           : none")
    print(f"  next            : {report.selected_next_phase}")
    print(f"  json            : {report.output_json}")
    print(f"  html            : {report.output_html}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
