"""Phase169A: broker cost reality + research lane reset audit.

The recent pivot lane found and then rejected two candidate routes:

* 5M strict bottom-buy failed realistic replay/execution-gap checks.
* 1H fixed-spread breakout passed a static lockdown, but failed walk-forward and
  predeclared filter confirmation.

This phase resets the research lane explicitly and audits whether the current
broker-cost assumptions are trustworthy enough for future research decisions. It
loads available phase run logs, summarizes route decisions, and computes
spread/ATR economics for fixed and percent spread assumptions on available OHLC
flat files. It can also summarize an optional broker spread sample file.

Research-only. No model training, paper shadow, live trading, or production gate.
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

from audit_pivot_1h_entry_feasibility import read_ohlc_frame  # noqa: E402
from audit_pivot_payoff_target_redesign import resolve_atr  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("run_logs/research_lane_reset_cost_audit")
DEFAULT_STORAGE = Path("datasets")


@dataclass(frozen=True)
class DatasetHealthRow:
    timeframe: str
    path: str
    status: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    duplicate_timestamps: int
    nonfinite_ohlc_cells: int
    invalid_ohlc_rows: int
    atr_mean: float
    atr_median: float
    atr_p90: float
    atr_nonpositive_rows: int
    notes: str


@dataclass(frozen=True)
class CostAssumptionRow:
    timeframe: str
    spread_mode: str
    spread_value: float
    rows: int
    atr_median: float
    full_spread_atr_mean: float
    full_spread_atr_median: float
    full_spread_atr_p90: float
    half_spread_atr_median: float
    feasible_gate: int
    notes: str


@dataclass(frozen=True)
class SpreadSampleRow:
    path: str
    status: str
    rows: int
    first_timestamp: str
    last_timestamp: str
    spread_median: float
    spread_p90: float
    spread_p99: float
    spread_mean: float
    notes: str


@dataclass(frozen=True)
class PhaseSourceRow:
    phase: str
    path: str
    status: str
    key_metrics: str


@dataclass(frozen=True)
class RouteDecisionRow:
    route: str
    phase: str
    status: str
    decision: str
    evidence: str
    allowed_next_action: str
    blocked_actions: str


@dataclass(frozen=True)
class Phase169Report:
    symbol: str
    generated_at_utc: str
    run_logs_root: str
    route_decision: str
    broker_cost_reality_status: str
    recommended_next_phase: str
    production_status: str
    dataset_health_rows: list[dict[str, Any]]
    cost_assumption_rows: list[dict[str, Any]]
    spread_sample_rows: list[dict[str, Any]]
    phase_source_rows: list[dict[str, Any]]
    route_decision_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_route_decisions_csv: str
    output_cost_assumptions_csv: str
    output_dataset_health_csv: str
    output_phase_sources_csv: str
    output_spread_samples_csv: str


def parse_float_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip()
        if item:
            values.append(float(item))
    return values or [float(value) for value in default]


def parse_timeframes(text: str) -> list[str]:
    values = [item.strip().upper() for item in str(text or "").replace(";", ",").split(",") if item.strip()]
    return values or ["5M", "1H"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset the research lane and audit broker-cost reality assumptions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframes", default="5M,1H")
    parser.add_argument("--m5-flat-path", default="datasets/processed/XAUUSD/5M/pivot_pattern_sequence_flat_latest.parquet")
    parser.add_argument("--h1-flat-path", default="datasets/processed/XAUUSD/1H/v1.parquet")
    parser.add_argument("--h4-flat-path", default="datasets/processed/XAUUSD/4H/v1.parquet")
    parser.add_argument("--d1-flat-path", default="datasets/processed/XAUUSD/1D/v1.parquet")
    parser.add_argument("--fixed-spreads", default="0.2,0.5,1.0,1.5,2.0")
    parser.add_argument("--pct-spreads", default="0.01,0.02,0.03,0.06")
    parser.add_argument("--max-median-spread-atr", type=float, default=0.12)
    parser.add_argument("--spread-sample-path", default="")
    parser.add_argument("--run-logs-root", default="run_logs")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase169A broker cost reality and research lane reset audit")
    return parser.parse_args(argv)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        return result if np.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def default_path_for_timeframe(args: argparse.Namespace, timeframe: str) -> Path:
    tf = timeframe.upper()
    if tf == "5M":
        return Path(args.m5_flat_path)
    if tf == "1H":
        return Path(args.h1_flat_path)
    if tf == "4H":
        return Path(args.h4_flat_path)
    if tf == "1D":
        return Path(args.d1_flat_path)
    return Path(args.storage_root) / "processed" / str(args.symbol).upper() / tf / "v1.parquet"


def ohlc_invalid_count(frame: pd.DataFrame) -> int:
    high = pd.to_numeric(frame["high"], errors="coerce").to_numpy(dtype=np.float64)
    low = pd.to_numeric(frame["low"], errors="coerce").to_numpy(dtype=np.float64)
    open_ = pd.to_numeric(frame["open"], errors="coerce").to_numpy(dtype=np.float64)
    close = pd.to_numeric(frame["close"], errors="coerce").to_numpy(dtype=np.float64)
    invalid = (high < low) | (high < np.maximum(open_, close)) | (low > np.minimum(open_, close))
    return int(np.sum(invalid))


def load_dataset_health(args: argparse.Namespace, timeframe: str) -> tuple[DatasetHealthRow, pd.DataFrame | None, np.ndarray | None]:
    path = default_path_for_timeframe(args, timeframe)
    if not path.exists():
        return (
            DatasetHealthRow(
                timeframe=timeframe,
                path=str(path),
                status="MISSING",
                rows=0,
                first_timestamp="",
                last_timestamp="",
                duplicate_timestamps=0,
                nonfinite_ohlc_cells=0,
                invalid_ohlc_rows=0,
                atr_mean=0.0,
                atr_median=0.0,
                atr_p90=0.0,
                atr_nonpositive_rows=0,
                notes="flat file not found",
            ),
            None,
            None,
        )
    try:
        frame = read_ohlc_frame(path, 0)
        atr = resolve_atr(frame)
        ohlc = frame[["open", "high", "low", "close"]].to_numpy(dtype=np.float64)
        atr_clean = atr[np.isfinite(atr)]
        return (
            DatasetHealthRow(
                timeframe=timeframe,
                path=str(path),
                status="PASS",
                rows=int(len(frame)),
                first_timestamp=str(frame["timestamp"].iloc[0]) if len(frame) else "",
                last_timestamp=str(frame["timestamp"].iloc[-1]) if len(frame) else "",
                duplicate_timestamps=int(frame["timestamp"].duplicated().sum()) if len(frame) else 0,
                nonfinite_ohlc_cells=int(np.sum(~np.isfinite(ohlc))) if len(frame) else 0,
                invalid_ohlc_rows=ohlc_invalid_count(frame) if len(frame) else 0,
                atr_mean=float(np.mean(atr_clean)) if len(atr_clean) else 0.0,
                atr_median=float(np.median(atr_clean)) if len(atr_clean) else 0.0,
                atr_p90=float(np.percentile(atr_clean, 90)) if len(atr_clean) else 0.0,
                atr_nonpositive_rows=int(np.sum(~np.isfinite(atr) | (atr <= 0))),
                notes="",
            ),
            frame,
            atr,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI behavior.
        return (
            DatasetHealthRow(
                timeframe=timeframe,
                path=str(path),
                status="ERROR",
                rows=0,
                first_timestamp="",
                last_timestamp="",
                duplicate_timestamps=0,
                nonfinite_ohlc_cells=0,
                invalid_ohlc_rows=0,
                atr_mean=0.0,
                atr_median=0.0,
                atr_p90=0.0,
                atr_nonpositive_rows=0,
                notes=f"{type(exc).__name__}: {exc}",
            ),
            None,
            None,
        )


def spread_atr_rows_for_frame(args: argparse.Namespace, timeframe: str, frame: pd.DataFrame, atr: np.ndarray) -> list[CostAssumptionRow]:
    close = pd.to_numeric(frame["close"], errors="coerce").to_numpy(dtype=np.float64)
    atr_safe = np.maximum(atr.astype(np.float64), 1e-9)
    rows: list[CostAssumptionRow] = []
    for mode, values in (
        ("fixed", parse_float_grid(args.fixed_spreads, (0.2, 0.5, 1.0, 1.5, 2.0))),
        ("pct", parse_float_grid(args.pct_spreads, (0.01, 0.02, 0.03, 0.06))),
    ):
        for spread_value in values:
            if mode == "fixed":
                full_spread = np.full(len(frame), float(spread_value), dtype=np.float64)
            else:
                full_spread = close * float(spread_value) / 100.0
            ratio = full_spread / atr_safe
            median = float(np.nanmedian(ratio)) if len(ratio) else 0.0
            rows.append(
                CostAssumptionRow(
                    timeframe=timeframe,
                    spread_mode=mode,
                    spread_value=float(spread_value),
                    rows=int(len(frame)),
                    atr_median=float(np.nanmedian(atr_safe)) if len(atr_safe) else 0.0,
                    full_spread_atr_mean=float(np.nanmean(ratio)) if len(ratio) else 0.0,
                    full_spread_atr_median=median,
                    full_spread_atr_p90=float(np.nanpercentile(ratio, 90)) if len(ratio) else 0.0,
                    half_spread_atr_median=float(np.nanmedian(ratio / 2.0)) if len(ratio) else 0.0,
                    feasible_gate=int(median <= float(args.max_median_spread_atr)),
                    notes="",
                )
            )
    return rows


def load_json(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def metric_text(data: Mapping[str, Any] | None, keys: Sequence[str]) -> str:
    if data is None:
        return "missing"
    values: dict[str, Any] = {}
    for key in keys:
        if key in data:
            values[key] = data[key]
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def phase_sources(args: argparse.Namespace) -> dict[str, tuple[Path, Mapping[str, Any] | None]]:
    root = Path(args.run_logs_root)
    mapping = {
        "Phase162A": root / "pivot_bottom_buy_execution_gap" / "latest.json",
        "Phase163A": root / "pivot_1h_entry_feasibility" / "latest.json",
        "Phase164A": root / "pivot_1h_spread_bracket_sensitivity" / "latest.json",
        "Phase165A": root / "pivot_1h_fixed_spread_candidate_lockdown" / "latest.json",
        "Phase166A": root / "pivot_1h_locked_candidate_walk_forward" / "latest.json",
        "Phase167A": root / "pivot_1h_locked_candidate_regime_failures" / "latest.json",
        "Phase168A": root / "pivot_1h_predeclared_filter_confirmation" / "latest.json",
    }
    return {phase: (path, load_json(path)) for phase, path in mapping.items()}


def build_phase_source_rows(sources: Mapping[str, tuple[Path, Mapping[str, Any] | None]]) -> list[PhaseSourceRow]:
    keys = {
        "Phase162A": ["selected_transfer_pass_gate", "selected_validation_chronological_profit_factor", "selected_test_chronological_profit_factor"],
        "Phase163A": ["route_feasible_gate", "validation_pass_configs", "transfer_pass_configs", "spread_feasible_gate"],
        "Phase164A": ["route_feasible_gate", "validation_pass_configs", "transfer_pass_configs", "selected_transfer_pass_gate"],
        "Phase165A": ["lockdown_pass_gate", "transfer_pass_gate", "train_pass_gate", "validation_pass_gate", "test_pass_gate"],
        "Phase166A": ["walk_forward_pass_gate", "fold_pass_count", "test_pass_count", "aggregate_test_cash_pnl"],
        "Phase167A": ["recommendation", "dominant_failure_reason", "best_filter_name", "best_filter_fold_pass_ratio"],
        "Phase168A": ["confirmation_pass_gate", "recommendation", "selected_filter_name", "selected_fold_pass_ratio"],
    }
    rows: list[PhaseSourceRow] = []
    for phase, (path, data) in sources.items():
        rows.append(
            PhaseSourceRow(
                phase=phase,
                path=str(path),
                status="FOUND" if data is not None else "MISSING",
                key_metrics=metric_text(data, keys.get(phase, ())),
            )
        )
    return rows


def build_route_decisions(sources: Mapping[str, tuple[Path, Mapping[str, Any] | None]]) -> list[RouteDecisionRow]:
    def data(phase: str) -> Mapping[str, Any] | None:
        return sources.get(phase, (Path(), None))[1]

    p162 = data("Phase162A")
    p168 = data("Phase168A")
    p166 = data("Phase166A")
    p165 = data("Phase165A")
    p164 = data("Phase164A")
    p163 = data("Phase163A")

    rows: list[RouteDecisionRow] = []
    phase162_gate = int(safe_float(p162.get("selected_transfer_pass_gate") if p162 else 0)) if p162 else 0
    rows.append(
        RouteDecisionRow(
            route="5M pivot bottom-buy",
            phase="Phase162A",
            status="REJECTED" if p162 and phase162_gate == 0 else ("UNKNOWN" if p162 is None else "DIAGNOSTIC_PASS"),
            decision="Stop 5M bottom-buy rescue lane" if p162 else "Missing Phase162A run log",
            evidence=metric_text(p162, ["selected_transfer_pass_gate", "selected_validation_chronological_profit_factor", "selected_test_chronological_profit_factor"]),
            allowed_next_action="None for this route" if p162 else "Run/restore Phase162A log if route status is needed",
            blocked_actions="training,paper,live,Phase134",
        )
    )

    phase168_gate = int(safe_float(p168.get("confirmation_pass_gate") if p168 else 0)) if p168 else 0
    if p168:
        status = "REJECTED" if phase168_gate == 0 else "CONFIRMATION_PASS_DIAGNOSTIC"
        decision = "Stop current 1H locked-candidate route" if phase168_gate == 0 else "Only consider target/model design after owner approval"
        evidence = metric_text(p168, ["confirmation_pass_gate", "recommendation", "selected_filter_name", "selected_fold_pass_ratio", "selected_test_pass_ratio"])
    elif p166:
        status = "REJECTED" if int(safe_float(p166.get("walk_forward_pass_gate"))) == 0 else "WF_PASS_DIAGNOSTIC"
        decision = "Phase168A missing; current route status not fully confirmed"
        evidence = metric_text(p166, ["walk_forward_pass_gate", "fold_pass_count", "test_pass_count", "aggregate_test_cash_pnl"])
    elif p165:
        status = "LOCKDOWN_PASS_ONLY"
        decision = "Needs Phase166A/168A before training"
        evidence = metric_text(p165, ["lockdown_pass_gate", "transfer_pass_gate"])
    else:
        status = "UNKNOWN"
        decision = "Missing Phase165A-168A logs"
        evidence = "missing"
    rows.append(
        RouteDecisionRow(
            route="1H locked breakout BRK_D1_FAST",
            phase="Phase168A/Phase166A",
            status=status,
            decision=decision,
            evidence=evidence,
            allowed_next_action="Redesign/new target family only" if status == "REJECTED" else "Confirmation-only diagnostics; no production",
            blocked_actions="training on rejected target,paper,live,Phase134",
        )
    )

    rows.append(
        RouteDecisionRow(
            route="1H cost model",
            phase="Phase163A-Phase164A",
            status="COST_UNIT_UNRESOLVED",
            decision="Treat broker cost as a first-class input before future research",
            evidence=json.dumps(
                {
                    "phase163": metric_text(p163, ["spread_feasible_gate", "route_feasible_gate"]),
                    "phase164": metric_text(p164, ["fixed_transfer_pass_configs", "pct_transfer_pass_configs", "route_feasible_gate"]),
                },
                ensure_ascii=False,
            ),
            allowed_next_action="Collect/validate real Alpari spread samples or use explicit fixed spread assumptions",
            blocked_actions="interpreting percent spread as broker fact without evidence",
        )
    )
    return rows


def summarize_spread_sample(path_text: str) -> SpreadSampleRow:
    path = Path(str(path_text or ""))
    if not str(path_text).strip():
        return SpreadSampleRow(
            path="",
            status="NOT_PROVIDED",
            rows=0,
            first_timestamp="",
            last_timestamp="",
            spread_median=0.0,
            spread_p90=0.0,
            spread_p99=0.0,
            spread_mean=0.0,
            notes="Optional broker spread sample not provided",
        )
    if not path.exists():
        return SpreadSampleRow(
            path=str(path),
            status="MISSING",
            rows=0,
            first_timestamp="",
            last_timestamp="",
            spread_median=0.0,
            spread_p90=0.0,
            spread_p99=0.0,
            spread_mean=0.0,
            notes="spread sample file not found",
        )
    try:
        frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
        if "timestamp" in frame.columns:
            ts = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        elif "time" in frame.columns:
            ts = pd.to_datetime(frame["time"], utc=True, errors="coerce")
        else:
            ts = pd.Series([], dtype="datetime64[ns, UTC]")
        if "spread" in frame.columns:
            spread = pd.to_numeric(frame["spread"], errors="coerce")
        elif "ask" in frame.columns and "bid" in frame.columns:
            spread = pd.to_numeric(frame["ask"], errors="coerce") - pd.to_numeric(frame["bid"], errors="coerce")
        elif "spread_value" in frame.columns:
            spread = pd.to_numeric(frame["spread_value"], errors="coerce")
        else:
            raise RuntimeError("spread sample must contain spread, spread_value, or bid/ask columns")
        values = spread.replace([np.inf, -np.inf], np.nan).dropna().to_numpy(dtype=np.float64)
        return SpreadSampleRow(
            path=str(path),
            status="PASS",
            rows=int(len(values)),
            first_timestamp=str(ts.dropna().iloc[0]) if len(ts.dropna()) else "",
            last_timestamp=str(ts.dropna().iloc[-1]) if len(ts.dropna()) else "",
            spread_median=float(np.median(values)) if len(values) else 0.0,
            spread_p90=float(np.percentile(values, 90)) if len(values) else 0.0,
            spread_p99=float(np.percentile(values, 99)) if len(values) else 0.0,
            spread_mean=float(np.mean(values)) if len(values) else 0.0,
            notes="",
        )
    except Exception as exc:  # pragma: no cover - defensive CLI behavior.
        return SpreadSampleRow(
            path=str(path),
            status="ERROR",
            rows=0,
            first_timestamp="",
            last_timestamp="",
            spread_median=0.0,
            spread_p90=0.0,
            spread_p99=0.0,
            spread_mean=0.0,
            notes=f"{type(exc).__name__}: {exc}",
        )


def choose_recommendation(route_rows: Sequence[RouteDecisionRow], spread_sample: SpreadSampleRow) -> tuple[str, str, str]:
    rejected_routes = [row for row in route_rows if row.status == "REJECTED"]
    current_locked_rejected = any(row.route == "1H locked breakout BRK_D1_FAST" and row.status == "REJECTED" for row in route_rows)
    if current_locked_rejected:
        route_decision = "STOP_CURRENT_PIVOT_LOCKED_ROUTES"
    elif rejected_routes:
        route_decision = "PARTIAL_REJECTION_NEEDS_REVIEW"
    else:
        route_decision = "INSUFFICIENT_ROUTE_EVIDENCE"
    if spread_sample.status == "PASS":
        cost_status = "BROKER_SPREAD_SAMPLE_AVAILABLE"
    else:
        cost_status = "BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED"
    if current_locked_rejected and spread_sample.status != "PASS":
        next_phase = "Phase170A — Broker Spread Capture / Cost Data Pipeline OR new target-family design with explicit cost assumptions"
    elif current_locked_rejected:
        next_phase = "New target/candidate family design only; do not patch rejected rules"
    else:
        next_phase = "Restore missing phase logs or run confirmation diagnostics"
    return route_decision, cost_status, next_phase


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: Phase169Report) -> str:
    route_rows = "".join(
        f"<tr><td>{html.escape(str(row['route']))}</td>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{html.escape(str(row['decision']))}</td>"
        f"<td><code>{html.escape(str(row['evidence']))}</code></td></tr>"
        for row in report.route_decision_rows
    )
    cost_rows = "".join(
        f"<tr><td>{html.escape(str(row['timeframe']))}</td>"
        f"<td>{html.escape(str(row['spread_mode']))}</td>"
        f"<td>{float(row['spread_value']):.4g}</td>"
        f"<td>{float(row['full_spread_atr_median']):.4f}</td>"
        f"<td>{float(row['full_spread_atr_p90']):.4f}</td>"
        f"<td>{int(row['feasible_gate'])}</td></tr>"
        for row in report.cost_assumption_rows[:80]
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1440px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:12px; }}
th,td {{ border:1px solid #334155; padding:7px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase169A broker cost reality and research lane reset. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Decision</h2><pre>{html.escape(json.dumps({
        'route_decision': report.route_decision,
        'broker_cost_reality_status': report.broker_cost_reality_status,
        'recommended_next_phase': report.recommended_next_phase,
    }, indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Route decisions</h2><table><thead><tr><th>Route</th><th>Status</th><th>Decision</th><th>Evidence</th></tr></thead><tbody>{route_rows}</tbody></table></section>
<section class="card"><h2>Cost assumptions</h2><table><thead><tr><th>TF</th><th>Mode</th><th>Spread</th><th>Median spread/ATR</th><th>P90 spread/ATR</th><th>Gate</th></tr></thead><tbody>{cost_rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE169A BROKER COST REALITY + RESEARCH LANE RESET AUDIT")
        print("=" * 74)
        dataset_rows: list[DatasetHealthRow] = []
        cost_rows: list[CostAssumptionRow] = []
        for timeframe in parse_timeframes(args.timeframes):
            health, frame, atr = load_dataset_health(args, timeframe)
            dataset_rows.append(health)
            if frame is not None and atr is not None:
                cost_rows.extend(spread_atr_rows_for_frame(args, timeframe, frame, atr))
        sources = phase_sources(args)
        source_rows = build_phase_source_rows(sources)
        route_rows = build_route_decisions(sources)
        spread_sample = summarize_spread_sample(str(args.spread_sample_path))
        route_decision, cost_status, next_phase = choose_recommendation(route_rows, spread_sample)
        route_csv = output_dir / "latest_route_decisions.csv"
        cost_csv = output_dir / "latest_cost_assumptions.csv"
        health_csv = output_dir / "latest_dataset_health.csv"
        phase_csv = output_dir / "latest_phase_sources.csv"
        spread_csv = output_dir / "latest_spread_samples.csv"
        write_csv(route_csv, [asdict(row) for row in route_rows])
        write_csv(cost_csv, [asdict(row) for row in cost_rows])
        write_csv(health_csv, [asdict(row) for row in dataset_rows])
        write_csv(phase_csv, [asdict(row) for row in source_rows])
        write_csv(spread_csv, [asdict(spread_sample)])
        report = Phase169Report(
            symbol=str(args.symbol),
            generated_at_utc=pd.Timestamp.utcnow().isoformat(),
            run_logs_root=str(args.run_logs_root),
            route_decision=route_decision,
            broker_cost_reality_status=cost_status,
            recommended_next_phase=next_phase,
            production_status="BLOCKED — Phase169A research lane reset/cost audit only",
            dataset_health_rows=[asdict(row) for row in dataset_rows],
            cost_assumption_rows=[asdict(row) for row in cost_rows],
            spread_sample_rows=[asdict(spread_sample)],
            phase_source_rows=[asdict(row) for row in source_rows],
            route_decision_rows=[asdict(row) for row in route_rows],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_route_decisions_csv=str(route_csv),
            output_cost_assumptions_csv=str(cost_csv),
            output_dataset_health_csv=str(health_csv),
            output_phase_sources_csv=str(phase_csv),
            output_spread_samples_csv=str(spread_csv),
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase169A research reset / cost audit complete")
        print(f"  route decision : {report.route_decision}")
        print(f"  cost status    : {report.broker_cost_reality_status}")
        print(f"  next           : {report.recommended_next_phase}")
        print(f"  output         : {report.output_json}")
        print(f"  elapsed        : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
