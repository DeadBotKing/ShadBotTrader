"""Phase184A: entry-geometry test-only failure attribution / stop-or-narrow decision.

Phase183A showed that quality-geometry redesign improved several final-test
pockets but did not transfer through validation or walk-forward gates. This
phase performs closure attribution only. It does not generate new targets and it
does not train any model.

Research only:
- no model training
- no paper/live trading
- no Phase134
- no gate relaxation
- no broad parameter search
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

DEFAULT_OUTPUT_DIR = Path("run_logs/entry_route_test_only_failure_attribution")


@dataclass(frozen=True)
class CandidateClosureRow:
    candidate_id: str
    label: str
    timeframe: str
    family_type: str
    side_filter: str
    train_events: int
    validation_events: int
    test_events: int
    train_quality_pass_rate: float
    validation_quality_pass_rate: float
    test_quality_pass_rate: float
    train_replay_profit_factor: float
    validation_replay_profit_factor: float
    test_replay_profit_factor: float
    train_mean_score: float
    validation_mean_score: float
    test_mean_score: float
    walkforward_folds: int
    walkforward_pass_folds: int
    walkforward_pass_ratio: float
    test_only_gate: int
    static_transfer_gate: int
    walkforward_transfer_gate: int
    narrow_candidate_gate: int
    primary_failure_reason: str
    closure_verdict: str
    recommendation: str


@dataclass(frozen=True)
class SplitTransferRow:
    candidate_id: str
    split: str
    timeframe: str
    family_type: str
    side_filter: str
    triggered_events: int
    quality_pass_rate: float
    replay_profit_factor: float
    mean_replay_score_atr: float
    split_pass_gate: int
    transfer_role: str


@dataclass(frozen=True)
class WalkForwardClosureRow:
    candidate_id: str
    timeframe: str
    family_type: str
    side_filter: str
    folds: int
    pass_folds: int
    train_gate_failed_folds: int
    validation_gate_failed_folds: int
    test_gate_failed_folds: int
    test_gate_pass_folds: int
    validation_gate_pass_folds: int
    train_gate_pass_folds: int
    max_test_quality_pass_rate: float
    min_test_quality_pass_rate: float
    test_only_fold_pattern_gate: int
    walkforward_closure_verdict: str


@dataclass(frozen=True)
class ReplayMonthRow:
    candidate_id: str
    timeframe: str
    family_type: str
    side_filter: str
    month: str
    events: int
    buy_events: int
    sell_events: int
    quality_pass_rate: float
    replay_profit_factor: float
    mean_replay_score_atr: float
    positive_score_rate: float


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
    route: str
    action: str
    purpose: str
    allowed: str


@dataclass(frozen=True)
class Phase184AReport:
    phase183a_path: str
    source_symbol: str
    evaluated_candidates: int
    ready_candidates: int
    test_only_candidates: int
    narrow_candidate_count: int
    selected_candidate_id: str
    selected_timeframe: str
    selected_family_type: str
    selected_closure_verdict: str
    selected_decision_route_id: str
    selected_decision: str
    no_training_gate: int
    no_paper_live_gate: int
    root_cause_summary: str
    candidate_closure_rows: list[dict[str, Any]]
    split_transfer_rows: list[dict[str, Any]]
    walkforward_closure_rows: list[dict[str, Any]]
    replay_month_rows: list[dict[str, Any]]
    failure_reason_rows: list[dict[str, Any]]
    decision_matrix: list[dict[str, Any]]
    next_plan: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_candidate_closure_csv: str
    output_split_transfer_csv: str
    output_walkforward_closure_csv: str
    output_replay_months_csv: str
    output_failure_reasons_csv: str
    output_decision_matrix_csv: str
    output_next_plan_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase184A entry route test-only failure attribution / stop-or-narrow decision.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--phase183a-path", default="run_logs/entry_quality_geometry_candidates/latest.json")
    parser.add_argument("--candidates-path", default="")
    parser.add_argument("--splits-path", default="")
    parser.add_argument("--walkforward-path", default="")
    parser.add_argument("--replay-path", default="")
    parser.add_argument("--min-train-pf", type=float, default=1.0)
    parser.add_argument("--min-validation-pf", type=float, default=1.0)
    parser.add_argument("--min-test-pf", type=float, default=1.0)
    parser.add_argument("--min-quality-pass-rate", type=float, default=0.45)
    parser.add_argument("--min-walkforward-pass-ratio", type=float, default=0.50)
    parser.add_argument("--min-walkforward-folds", type=int, default=3)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase184A entry route test-only failure attribution")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Phase183A json not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


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


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = float(sum(value for value in values if value > 0))
    gross_loss = float(abs(sum(value for value in values if value < 0)))
    if gross_loss <= 0:
        return 999.0 if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def candidate_primary_failure(row: Mapping[str, Any], args: argparse.Namespace) -> str:
    if as_float(row, "walkforward_pass_ratio") < float(args.min_walkforward_pass_ratio):
        return "walkforward_transfer_failed"
    if as_float(row, "validation_replay_profit_factor") < float(args.min_validation_pf):
        return "validation_replay_failed"
    if as_float(row, "train_replay_profit_factor") < float(args.min_train_pf):
        return "train_replay_failed"
    if as_float(row, "validation_quality_pass_rate") < float(args.min_quality_pass_rate):
        return "validation_quality_failed"
    reasons = parse_reasons(row.get("failure_reasons", ""))
    return reasons[0] if reasons else "none"


def build_candidate_closure_rows(payload: Mapping[str, Any], args: argparse.Namespace) -> list[CandidateClosureRow]:
    rows: list[CandidateClosureRow] = []
    for raw in payload.get("candidate_rows", []) or []:
        if not isinstance(raw, Mapping):
            continue
        train_pf = as_float(raw, "train_replay_profit_factor")
        val_pf = as_float(raw, "validation_replay_profit_factor")
        test_pf = as_float(raw, "test_replay_profit_factor")
        train_quality = as_float(raw, "train_quality_pass_rate")
        val_quality = as_float(raw, "validation_quality_pass_rate")
        test_quality = as_float(raw, "test_quality_pass_rate")
        wf_ratio = as_float(raw, "walkforward_pass_ratio")
        test_only_gate = int(
            test_pf >= float(args.min_test_pf)
            and test_quality >= float(args.min_quality_pass_rate)
            and (val_pf < float(args.min_validation_pf) or train_pf < float(args.min_train_pf) or wf_ratio <= 0.0)
        )
        static_transfer_gate = int(
            train_pf >= float(args.min_train_pf)
            and val_pf >= float(args.min_validation_pf)
            and test_pf >= float(args.min_test_pf)
            and train_quality >= float(args.min_quality_pass_rate)
            and val_quality >= float(args.min_quality_pass_rate)
            and test_quality >= float(args.min_quality_pass_rate)
        )
        wf_gate = int(
            as_int(raw, "walkforward_folds") >= int(args.min_walkforward_folds)
            and wf_ratio >= float(args.min_walkforward_pass_ratio)
        )
        narrow_gate = int(static_transfer_gate and wf_gate and as_int(raw, "quality_geometry_candidate_ready_gate") == 1)
        primary = candidate_primary_failure(raw, args)
        if narrow_gate:
            verdict = "NARROW_CANDIDATE_ALLOWED_FOR_OWNER_REVIEW"
            recommendation = "Owner review before any model preflight."
        elif test_only_gate:
            verdict = "TEST_ONLY_NOT_TRANSFERRED"
            recommendation = "Do not continue as model route; treat as test-only artifact unless a separate non-test explanation exists."
        else:
            verdict = "GEOMETRY_NOT_CONFIRMED"
            recommendation = "Freeze this candidate unless owner requests a narrower attribution-only review."
        rows.append(
            CandidateClosureRow(
                candidate_id=str(raw.get("candidate_id", "")),
                label=str(raw.get("label", "")),
                timeframe=str(raw.get("timeframe", "")),
                family_type=str(raw.get("family_type", "")),
                side_filter=str(raw.get("side_filter", "")),
                train_events=as_int(raw, "train_events"),
                validation_events=as_int(raw, "validation_events"),
                test_events=as_int(raw, "test_events"),
                train_quality_pass_rate=train_quality,
                validation_quality_pass_rate=val_quality,
                test_quality_pass_rate=test_quality,
                train_replay_profit_factor=train_pf,
                validation_replay_profit_factor=val_pf,
                test_replay_profit_factor=test_pf,
                train_mean_score=as_float(raw, "train_mean_score"),
                validation_mean_score=as_float(raw, "validation_mean_score"),
                test_mean_score=as_float(raw, "test_mean_score"),
                walkforward_folds=as_int(raw, "walkforward_folds"),
                walkforward_pass_folds=as_int(raw, "walkforward_pass_folds"),
                walkforward_pass_ratio=wf_ratio,
                test_only_gate=test_only_gate,
                static_transfer_gate=static_transfer_gate,
                walkforward_transfer_gate=wf_gate,
                narrow_candidate_gate=narrow_gate,
                primary_failure_reason=primary,
                closure_verdict=verdict,
                recommendation=recommendation,
            )
        )
    return sorted(
        rows,
        key=lambda row: (
            row.narrow_candidate_gate,
            row.test_only_gate,
            row.test_replay_profit_factor,
            row.test_quality_pass_rate,
            row.validation_replay_profit_factor,
        ),
        reverse=True,
    )


def split_transfer_rows(payload: Mapping[str, Any], splits: pd.DataFrame) -> list[SplitTransferRow]:
    rows: list[SplitTransferRow] = []
    raw_rows: list[Mapping[str, Any]]
    if not splits.empty:
        raw_rows = [row for row in splits.to_dict("records")]
    else:
        raw_rows = []
        for candidate in payload.get("candidate_rows", []) or []:
            if not isinstance(candidate, Mapping):
                continue
            for split in ("train", "validation", "test"):
                raw_rows.append(
                    {
                        "candidate_id": candidate.get("candidate_id", ""),
                        "timeframe": candidate.get("timeframe", ""),
                        "family_type": candidate.get("family_type", ""),
                        "side_filter": candidate.get("side_filter", ""),
                        "split": split,
                        "triggered_events": candidate.get(f"{split}_events", 0),
                        "quality_pass_rate": candidate.get(f"{split}_quality_pass_rate", 0.0),
                        "replay_profit_factor": candidate.get(f"{split}_replay_profit_factor", 0.0),
                        "mean_replay_score_atr": candidate.get(f"{split}_mean_score", 0.0),
                        "split_pass_gate": int(candidate.get("quality_geometry_candidate_ready_gate", 0)) if split != "test" else 0,
                    }
                )
    for raw in raw_rows:
        split = str(raw.get("split", ""))
        role = {"train": "FIT_BASE", "validation": "SELECTION_TRANSFER", "test": "FINAL_CONFIRMATION"}.get(split, split)
        rows.append(
            SplitTransferRow(
                candidate_id=str(raw.get("candidate_id", "")),
                split=split,
                timeframe=str(raw.get("timeframe", "")),
                family_type=str(raw.get("family_type", "")),
                side_filter=str(raw.get("side_filter", "")),
                triggered_events=as_int(raw, "triggered_events"),
                quality_pass_rate=as_float(raw, "quality_pass_rate"),
                replay_profit_factor=as_float(raw, "replay_profit_factor"),
                mean_replay_score_atr=as_float(raw, "mean_replay_score_atr"),
                split_pass_gate=as_int(raw, "split_pass_gate"),
                transfer_role=role,
            )
        )
    return rows


def walkforward_closure_rows(walkforward: pd.DataFrame) -> list[WalkForwardClosureRow]:
    if walkforward.empty:
        return []
    rows: list[WalkForwardClosureRow] = []
    for (candidate_id, timeframe, family_type, side_filter), group in walkforward.groupby(
        ["candidate_id", "timeframe", "family_type", "side_filter"], dropna=False
    ):
        pass_gate = pd.to_numeric(group.get("pass_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        train_gate = pd.to_numeric(group.get("train_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        val_gate = pd.to_numeric(group.get("validation_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        test_gate = pd.to_numeric(group.get("test_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        test_quality = pd.to_numeric(group.get("test_quality_pass_rate", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        test_only_fold_pattern = int(np.sum(test_gate) > 0 and np.sum(pass_gate) == 0)
        verdict = "TEST_FOLDS_PASS_BUT_FULL_WF_FAILS" if test_only_fold_pattern else "WF_ZERO_OR_NO_TEST_CONFIRMATION"
        rows.append(
            WalkForwardClosureRow(
                candidate_id=str(candidate_id),
                timeframe=str(timeframe),
                family_type=str(family_type),
                side_filter=str(side_filter),
                folds=int(len(group)),
                pass_folds=int(np.sum(pass_gate)),
                train_gate_failed_folds=int(np.sum(train_gate == 0)),
                validation_gate_failed_folds=int(np.sum(val_gate == 0)),
                test_gate_failed_folds=int(np.sum(test_gate == 0)),
                test_gate_pass_folds=int(np.sum(test_gate)),
                validation_gate_pass_folds=int(np.sum(val_gate)),
                train_gate_pass_folds=int(np.sum(train_gate)),
                max_test_quality_pass_rate=float(np.max(test_quality)) if len(test_quality) else 0.0,
                min_test_quality_pass_rate=float(np.min(test_quality)) if len(test_quality) else 0.0,
                test_only_fold_pattern_gate=test_only_fold_pattern,
                walkforward_closure_verdict=verdict,
            )
        )
    return sorted(rows, key=lambda row: (row.test_gate_pass_folds, row.max_test_quality_pass_rate), reverse=True)


def replay_month_rows(replay: pd.DataFrame) -> list[ReplayMonthRow]:
    if replay.empty or "candidate_id" not in replay.columns:
        return []
    frame = replay.copy()
    timestamp_col = "trigger_timestamp" if "trigger_timestamp" in frame.columns else "setup_timestamp"
    if timestamp_col not in frame.columns:
        return []
    frame["_timestamp"] = pd.to_datetime(frame[timestamp_col], utc=True, errors="coerce")
    frame = frame.dropna(subset=["_timestamp"])
    if frame.empty:
        return []
    frame["_month"] = frame["_timestamp"].dt.strftime("%Y-%m")
    rows: list[ReplayMonthRow] = []
    for (candidate_id, month), group in frame.groupby(["candidate_id", "_month"], dropna=False):
        scores = pd.to_numeric(group.get("replay_score_atr", 0.0), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        quality = pd.to_numeric(group.get("quality_gate", 0), errors="coerce").fillna(0).to_numpy(dtype=int)
        side = group.get("side", pd.Series([], dtype=str)).astype(str)
        first = group.iloc[0]
        rows.append(
            ReplayMonthRow(
                candidate_id=str(candidate_id),
                timeframe=str(first.get("timeframe", "")),
                family_type=str(first.get("family_type", "")),
                side_filter=str(first.get("side_filter", "")),
                month=str(month),
                events=int(len(group)),
                buy_events=int((side == "BUY").sum()) if len(side) else 0,
                sell_events=int((side == "SELL").sum()) if len(side) else 0,
                quality_pass_rate=float(np.mean(quality)) if len(quality) else 0.0,
                replay_profit_factor=profit_factor(scores.tolist()),
                mean_replay_score_atr=float(np.mean(scores)) if len(scores) else 0.0,
                positive_score_rate=float(np.mean(scores > 0)) if len(scores) else 0.0,
            )
        )
    return sorted(rows, key=lambda row: (row.candidate_id, row.month))


def failure_reason_rows(candidates: Sequence[CandidateClosureRow]) -> list[FailureReasonRow]:
    counts: dict[str, int] = {}
    examples: dict[str, str] = {}
    for row in candidates:
        reasons = [row.primary_failure_reason]
        if row.test_only_gate:
            reasons.append("test_only_not_transferred")
        if row.walkforward_transfer_gate == 0:
            reasons.append("walkforward_transfer_gate_failed")
        if row.static_transfer_gate == 0:
            reasons.append("static_transfer_gate_failed")
        for reason in reasons:
            if not reason or reason == "none":
                continue
            counts[reason] = counts.get(reason, 0) + 1
            examples.setdefault(reason, row.candidate_id)
    total = max(len(candidates), 1)
    return sorted(
        [FailureReasonRow(reason=reason, count=count, share=count / total, example=examples.get(reason, "")) for reason, count in counts.items()],
        key=lambda row: row.count,
        reverse=True,
    )


def decision_matrix(candidates: Sequence[CandidateClosureRow]) -> list[DecisionRow]:
    narrow = [row for row in candidates if row.narrow_candidate_gate]
    test_only = [row for row in candidates if row.test_only_gate]
    best = candidates[0] if candidates else None
    best_text = best.candidate_id if best else "none"
    freeze_recommended = len(narrow) == 0
    return [
        DecisionRow(
            route_id="ENTRY_GEOMETRY_MODEL_PREFLIGHT",
            status="BLOCKED",
            score=0.0,
            evidence=f"narrow_candidates={len(narrow)}; test_only_candidates={len(test_only)}; best={best_text}",
            recommendation="Do not train; no geometry candidate transferred through validation and walk-forward.",
        ),
        DecisionRow(
            route_id="FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE",
            status="RECOMMENDED" if freeze_recommended else "OPTIONAL_AFTER_OWNER_REVIEW",
            score=88.0 if freeze_recommended else 40.0,
            evidence="Phase183A produced test-only pockets but no walk-forward transfer.",
            recommendation="Freeze this entry-quality geometry route as failed diagnostic." if freeze_recommended else "Owner may still review the narrow candidate before any model preflight.",
        ),
        DecisionRow(
            route_id="ALLOW_ONE_NARROW_PHASE185A",
            status="BLOCKED" if freeze_recommended else "OWNER_REVIEW_REQUIRED",
            score=0.0 if freeze_recommended else 55.0,
            evidence=f"narrow_candidates={len(narrow)}",
            recommendation="Do not create another redesign phase unless owner explicitly overrides the freeze recommendation.",
        ),
        DecisionRow(
            route_id="PAPER_OR_LIVE",
            status="BLOCKED",
            score=0.0,
            evidence="No model/execution gate is opened by Phase184A.",
            recommendation="No Phase134, no paper shadow, no live trading.",
        ),
    ]


def next_plan(candidates: Sequence[CandidateClosureRow]) -> list[NextPlanRow]:
    test_only = [row.candidate_id for row in candidates if row.test_only_gate][:5]
    return [
        NextPlanRow(
            step=1,
            route="ENTRY_EVENT_GEOMETRY_ROUTE",
            action="Freeze current E1/E2/E3 quality-geometry route as failed diagnostic.",
            purpose="Avoid test-aware overfitting after Phase183A produced test-only pockets.",
            allowed="RECOMMENDED",
        ),
        NextPlanRow(
            step=2,
            route="OWNER_REVIEW",
            action="Review whether to switch research route instead of generating more geometry candidates.",
            purpose="Keep project owner in control before any new lane is opened.",
            allowed="REQUIRED",
        ),
        NextPlanRow(
            step=3,
            route="OPTIONAL_EXCEPTION",
            action="If owner rejects freeze, allow only one manually specified narrow diagnostic; no broad grid.",
            purpose=f"Current test-only examples: {', '.join(test_only) or 'none'}.",
            allowed="OWNER_OVERRIDE_ONLY_NO_MODEL_TRAINING",
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


def render_html(report: Phase184AReport, title: str) -> str:
    candidates = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['closure_verdict']))}</td>"
        f"<td>{float(row['validation_replay_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_replay_profit_factor']):.3f}</td>"
        f"<td>{float(row['walkforward_pass_ratio']):.2f}</td>"
        f"<td>{int(row['test_only_gate'])}</td>"
        "</tr>"
        for row in report.candidate_closure_rows[:30]
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
                "selected_decision": report.selected_decision,
                "test_only_candidates": report.test_only_candidates,
                "narrow_candidate_count": report.narrow_candidate_count,
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
<section><h2>Candidate closure</h2><table><thead><tr><th>Candidate</th><th>Verdict</th><th>Val PF</th><th>Test PF</th><th>WF</th><th>Test-only</th></tr></thead><tbody>{candidates}</tbody></table></section>
<section><h2>Decision matrix</h2><table><thead><tr><th>Route</th><th>Status</th><th>Score</th><th>Recommendation</th></tr></thead><tbody>{decisions}</tbody></table></section>
</body></html>"""


def run(argv: list[str] | None = None) -> Phase184AReport:
    args = parse_args(argv)
    payload = load_json(Path(args.phase183a_path))
    splits = read_csv_optional(csv_path(payload, args.splits_path, "output_splits_csv"))
    walkforward = read_csv_optional(csv_path(payload, args.walkforward_path, "output_walkforward_csv"))
    replay = read_csv_optional(csv_path(payload, args.replay_path, "output_replay_csv"))

    candidates = build_candidate_closure_rows(payload, args)
    split_rows = split_transfer_rows(payload, splits)
    wf_rows = walkforward_closure_rows(walkforward)
    month_rows = replay_month_rows(replay)
    failure_rows = failure_reason_rows(candidates)
    decisions = decision_matrix(candidates)
    plan = next_plan(candidates)

    narrow_count = sum(row.narrow_candidate_gate for row in candidates)
    test_only_count = sum(row.test_only_gate for row in candidates)
    selected = candidates[0] if candidates else None
    freeze = narrow_count == 0
    selected_route = "FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE" if freeze else "ALLOW_ONE_NARROW_PHASE185A"
    selected_decision = "FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE" if freeze else "OWNER_REVIEW_REQUIRED_FOR_ONE_NARROW_PHASE185A"
    root_summary = (
        "Phase183A produced final-test pockets, but they did not transfer through validation and walk-forward. "
        "The current entry-quality geometry route is test-only and should be frozen unless the owner explicitly requests one narrow diagnostic exception."
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / "latest.json"
    output_html = output_dir / "latest.html"
    output_candidate = output_dir / "latest_candidate_closure.csv"
    output_split = output_dir / "latest_split_transfer.csv"
    output_wf = output_dir / "latest_walkforward_closure.csv"
    output_months = output_dir / "latest_replay_months.csv"
    output_failures = output_dir / "latest_failure_reasons.csv"
    output_decisions = output_dir / "latest_decision_matrix.csv"
    output_plan = output_dir / "latest_next_plan.csv"

    report = Phase184AReport(
        phase183a_path=str(args.phase183a_path),
        source_symbol=str(payload.get("source_symbol", "")),
        evaluated_candidates=len(candidates),
        ready_candidates=int(payload.get("ready_candidates", 0) or 0),
        test_only_candidates=int(test_only_count),
        narrow_candidate_count=int(narrow_count),
        selected_candidate_id=selected.candidate_id if selected else "",
        selected_timeframe=selected.timeframe if selected else "",
        selected_family_type=selected.family_type if selected else "",
        selected_closure_verdict=selected.closure_verdict if selected else "",
        selected_decision_route_id=selected_route,
        selected_decision=selected_decision,
        no_training_gate=1,
        no_paper_live_gate=1,
        root_cause_summary=root_summary,
        candidate_closure_rows=[asdict(row) for row in candidates],
        split_transfer_rows=[asdict(row) for row in split_rows],
        walkforward_closure_rows=[asdict(row) for row in wf_rows],
        replay_month_rows=[asdict(row) for row in month_rows],
        failure_reason_rows=[asdict(row) for row in failure_rows],
        decision_matrix=[asdict(row) for row in decisions],
        next_plan=[asdict(row) for row in plan],
        output_json=str(output_json),
        output_html=str(output_html),
        output_candidate_closure_csv=str(output_candidate),
        output_split_transfer_csv=str(output_split),
        output_walkforward_closure_csv=str(output_wf),
        output_replay_months_csv=str(output_months),
        output_failure_reasons_csv=str(output_failures),
        output_decision_matrix_csv=str(output_decisions),
        output_next_plan_csv=str(output_plan),
        production_status="BLOCKED — Phase184A closure attribution only; no model training/paper/live",
    )

    write_csv(output_candidate, report.candidate_closure_rows)
    write_csv(output_split, report.split_transfer_rows)
    write_csv(output_wf, report.walkforward_closure_rows)
    write_csv(output_months, report.replay_month_rows)
    write_csv(output_failures, report.failure_reason_rows)
    write_csv(output_decisions, report.decision_matrix)
    write_csv(output_plan, report.next_plan)
    output_html.write_text(render_html(report, str(args.report_title)), encoding="utf-8")
    output_json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n[DONE] Phase184A entry route test-only failure attribution complete")
    print(f"  candidates     : {report.evaluated_candidates}")
    print(f"  test-only      : {report.test_only_candidates}")
    print(f"  narrow         : {report.narrow_candidate_count}")
    print(f"  selected       : {report.selected_candidate_id or 'none'}")
    print(f"  decision       : {report.selected_decision}")
    print(f"  json           : {report.output_json}")
    print(f"  html           : {report.output_html}")
    return report


def main() -> None:
    run()


if __name__ == "__main__":
    main()
