"""Phase136A: diagnose tensor walk-forward failures by regime.

This is a research/diagnostic script. It does not train a model and it does
not approve production. It explains where candidate outcomes and walk-forward
validation-to-test transfer break down.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import html
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/tensor_failure_regimes")
DEFAULT_WALK_FORWARD_JSON = Path("run_logs/hybrid_tensor_walk_forward_validation/latest.json")


@dataclass(frozen=True)
class RegimeRow:
    section: str
    bucket: str
    rows: int
    wins: int
    losses: int
    buy_rows: int
    sell_rows: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    share_of_candidates: float
    notes: str


@dataclass(frozen=True)
class TransferRow:
    fold: int
    test_month: str
    validation_months: str
    selected_mode: str
    selected_meta_threshold: float
    selected_score_threshold: float
    validation_score: float
    validation_profit_factor: float
    validation_max_drawdown: float
    validation_trades: int
    no_trade_selected: int
    base_total_pnl: float
    tensor_total_pnl: float
    tensor_profit_factor: float
    tensor_trades: int
    tensor_max_drawdown: float
    transfer_delta: float
    transfer_status: str


@dataclass(frozen=True)
class DiagnosticReport:
    flat_path: str
    walk_forward_json: str
    candidate_rows: int
    months: int
    total_pnl: float
    win_rate: float
    profit_factor: float
    worst_month: str
    best_month: str
    transfer_rows: int
    transfer_total_pnl: float
    transfer_profit_factor: float
    no_trade_months: int
    risk_flags: list[str]
    output_json: str
    output_html: str
    output_regime_csv: str
    output_transfer_csv: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Phase133B/C tensor walk-forward failure regimes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--walk-forward-json", default=str(DEFAULT_WALK_FORWARD_JSON))
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--min-group-rows", type=int, default=20)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--quantile-bins", type=int, default=5)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_telemetry_flat_latest.parquet"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if np.isfinite(number) else default


def safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def profit_factor(pnls: Sequence[float]) -> float:
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    if gross_loss:
        return safe_div(gross_profit, gross_loss)
    return 999.0 if gross_profit else 0.0


def max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += float(pnl)
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def outcome_label(value: Any) -> str:
    code = safe_float(value, 0.0)
    if code > 0.5:
        return "take_profit"
    if code < -0.5:
        return "stop_loss"
    return "timeout"


def prepare_candidate_frame(frame: pd.DataFrame, candidate_only: str) -> pd.DataFrame:
    result = frame.replace([np.inf, -np.inf], 0.0).fillna(0.0).copy()
    if "candidate_mask" in result.columns and candidate_only == "1":
        result = result[result["candidate_mask"].astype(float) >= 0.5].copy()
    result["timestamp_dt"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["month"] = result["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
    result["hour"] = result["timestamp_dt"].dt.hour.fillna(-1).astype(int).astype(str)
    result["side"] = np.where(result["target_side"].astype(float) >= 0, "BUY", "SELL")
    result["target_win_bool"] = result["target_trade_win"].astype(float) >= 0.5
    result["target_pnl_float"] = result["target_trade_pnl"].astype(float)
    result["outcome"] = result["target_outcome_code"].map(outcome_label)
    result["side_4h_room"] = np.where(
        result["side"] == "BUY",
        result.get("range_4h_up_room", 0.0),
        result.get("range_4h_down_room", 0.0),
    ).astype(float)
    result["side_1d_room"] = np.where(
        result["side"] == "BUY",
        result.get("range_1d_up_room", 0.0),
        result.get("range_1d_down_room", 0.0),
    ).astype(float)
    return result.reset_index(drop=True)


def summarize_subset(section: str, bucket: str, subset: pd.DataFrame, total_rows: int) -> RegimeRow:
    pnls = subset["target_pnl_float"].astype(float).tolist()
    wins = int(subset["target_win_bool"].sum())
    losses = int(len(subset) - wins)
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    return RegimeRow(
        section=section,
        bucket=str(bucket),
        rows=int(len(subset)),
        wins=wins,
        losses=losses,
        buy_rows=int((subset["side"] == "BUY").sum()),
        sell_rows=int((subset["side"] == "SELL").sum()),
        win_rate=safe_div(wins, len(subset)),
        total_pnl=float(sum(pnls)),
        avg_pnl=safe_div(sum(pnls), len(subset)),
        gross_profit=float(gross_profit),
        gross_loss=float(gross_loss),
        profit_factor=profit_factor(pnls),
        max_drawdown=max_drawdown(pnls),
        share_of_candidates=safe_div(len(subset), total_rows),
        notes="candidate-outcome distribution; not chronological replay",
    )


def group_summary(
    frame: pd.DataFrame, section: str, column: str, total_rows: int, min_rows: int
) -> list[RegimeRow]:
    if column not in frame.columns:
        return []
    rows: list[RegimeRow] = []
    for bucket, subset in frame.groupby(column, dropna=False, sort=True):
        if len(subset) < min_rows:
            continue
        rows.append(summarize_subset(section, str(bucket), subset, total_rows))
    return sorted(rows, key=lambda row: row.total_pnl)


def quantile_labels(series: pd.Series, bins: int) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if numeric.nunique(dropna=True) < 2:
        return pd.Series(["single_or_missing"] * len(series), index=series.index)
    bucket_count = max(int(bins), 2)
    try:
        bucketed = pd.qcut(numeric, q=bucket_count, duplicates="drop")
    except ValueError:
        return pd.Series(["single_or_missing"] * len(series), index=series.index)
    return bucketed.astype(str).fillna("missing")


def add_numeric_bin_summary(
    frame: pd.DataFrame,
    section: str,
    column: str,
    total_rows: int,
    bins: int,
    min_rows: int,
) -> list[RegimeRow]:
    if column not in frame.columns:
        return []
    bucket_col = f"__bucket_{column}"
    work = frame.copy()
    work[bucket_col] = quantile_labels(work[column], bins)
    return group_summary(work, section, bucket_col, total_rows, min_rows)


def build_regime_rows(frame: pd.DataFrame, min_rows: int, bins: int) -> list[RegimeRow]:
    total_rows = len(frame)
    rows: list[RegimeRow] = []
    categorical = [
        ("month", "month"),
        ("side", "side"),
        ("month_side", "month_side"),
        ("hour", "hour"),
        ("side_hour", "side_hour"),
        ("outcome", "outcome"),
        ("specialist_conflict", "specialist_conflict"),
        ("candidate_valid_range", "candidate_valid_range"),
        ("candidate_valid_bracket", "candidate_valid_bracket"),
    ]
    work = frame.copy()
    work["month_side"] = work["month"].astype(str) + " / " + work["side"].astype(str)
    work["side_hour"] = work["side"].astype(str) + " / hour=" + work["hour"].astype(str)
    for section, column in categorical:
        rows.extend(group_summary(work, section, column, total_rows, min_rows))
    numeric = [
        ("candidate_confidence_bin", "candidate_confidence"),
        ("candidate_reward_risk_bin", "candidate_reward_risk"),
        ("candidate_tp_distance_bin", "candidate_tp_distance"),
        ("candidate_sl_distance_bin", "candidate_sl_distance"),
        ("side_4h_room_bin", "side_4h_room"),
        ("side_1d_room_bin", "side_1d_room"),
        ("range_4h_width_bin", "range_4h_width"),
        ("range_1d_width_bin", "range_1d_width"),
        ("booster_entropy_bin", "booster_entropy"),
        ("booster_action_margin_bin", "booster_action_margin"),
        ("specialist_max_prob_bin", "specialist_max_prob"),
        ("target_score_r_bin_analysis_only", "target_trade_score_r"),
    ]
    for section, column in numeric:
        rows.extend(add_numeric_bin_summary(work, section, column, total_rows, bins, min_rows))
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def transfer_status(fold: Mapping[str, Any]) -> str:
    no_trade = int(safe_float(fold.get("no_trade_selected", 0.0)))
    validation_score = safe_float(fold.get("selected_validation_score", 0.0))
    validation_pf = safe_float(fold.get("selected_validation_profit_factor", 0.0))
    tensor_pnl = safe_float(fold.get("tensor_total_pnl", 0.0))
    tensor_trades = int(safe_float(fold.get("tensor_trades", 0.0)))
    status = str(fold.get("selected_validation_status", ""))
    if no_trade:
        return status or "blocked_by_validation_gate"
    if tensor_trades <= 0:
        return "validation_passed_but_no_test_trades"
    if validation_score > 0 and validation_pf >= 1.1 and tensor_pnl < 0:
        return "positive_validation_failed_test"
    if validation_score > 0 and tensor_pnl > 0:
        return "positive_validation_transferred"
    if validation_score < 0 and tensor_pnl < 0:
        return "negative_validation_forced_loss"
    if tensor_pnl > 0:
        return "test_positive"
    return "test_negative"


def build_transfer_rows(payload: Mapping[str, Any]) -> list[TransferRow]:
    rows: list[TransferRow] = []
    for fold in payload.get("folds", []) or []:
        validation_score = safe_float(fold.get("selected_validation_score", 0.0))
        tensor_pnl = safe_float(fold.get("tensor_total_pnl", 0.0))
        rows.append(
            TransferRow(
                fold=int(safe_float(fold.get("fold", 0.0))),
                test_month=str(fold.get("test_month", "")),
                validation_months=str(fold.get("validation_months", "")),
                selected_mode=str(fold.get("selected_decision_mode", "")),
                selected_meta_threshold=safe_float(fold.get("selected_meta_threshold", 0.0)),
                selected_score_threshold=safe_float(fold.get("selected_score_threshold", 0.0)),
                validation_score=validation_score,
                validation_profit_factor=safe_float(
                    fold.get("selected_validation_profit_factor", 0.0)
                ),
                validation_max_drawdown=safe_float(
                    fold.get("selected_validation_max_drawdown", 0.0)
                ),
                validation_trades=int(safe_float(fold.get("selected_validation_trades", 0.0))),
                no_trade_selected=int(safe_float(fold.get("no_trade_selected", 0.0))),
                base_total_pnl=safe_float(fold.get("base_total_pnl", 0.0)),
                tensor_total_pnl=tensor_pnl,
                tensor_profit_factor=safe_float(fold.get("tensor_profit_factor", 0.0)),
                tensor_trades=int(safe_float(fold.get("tensor_trades", 0.0))),
                tensor_max_drawdown=safe_float(fold.get("tensor_max_drawdown", 0.0)),
                transfer_delta=tensor_pnl - validation_score,
                transfer_status=transfer_status(fold),
            )
        )
    return rows


def top_rows(rows: Sequence[RegimeRow], top_n: int, worst: bool) -> list[RegimeRow]:
    eligible = [
        row for row in rows if row.rows > 0 and row.section != "target_score_r_bin_analysis_only"
    ]
    return sorted(eligible, key=lambda row: row.total_pnl, reverse=not worst)[: max(top_n, 1)]


def risk_flags(regime_rows: Sequence[RegimeRow], transfer_rows: Sequence[TransferRow]) -> list[str]:
    flags: list[str] = []
    transfer_failures = [
        row for row in transfer_rows if row.transfer_status == "positive_validation_failed_test"
    ]
    if transfer_failures:
        flags.append(
            f"{len(transfer_failures)} fold(s) had positive validation quality but negative test PnL."
        )
    blocked = [row for row in transfer_rows if row.no_trade_selected]
    if blocked:
        flags.append(f"{len(blocked)} fold(s) were blocked by validation no-trade gates.")
    active_losses = [
        row for row in transfer_rows if row.tensor_trades > 0 and row.tensor_total_pnl < 0
    ]
    if active_losses:
        flags.append(f"{len(active_losses)} active trading fold(s) still lost money after gates.")
    side_rows = [row for row in regime_rows if row.section == "side"]
    for row in side_rows:
        if row.total_pnl < 0:
            flags.append(
                f"Side {row.bucket} is negative in candidate distribution: {row.total_pnl:+.2f} raw PnL."
            )
    if not flags:
        flags.append("No obvious single risk flag found; inspect detailed regime tables.")
    return flags


def write_csv(path: Path, rows: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def regime_table(rows: Sequence[RegimeRow], title: str) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.section)}</td>"
        f"<td>{html.escape(row.bucket)}</td>"
        f"<td>{row.rows:,}</td>"
        f"<td>{row.buy_rows:,}/{row.sell_rows:,}</td>"
        f"<td>{row.win_rate:.2%}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.max_drawdown:.2f}</td>"
        f"<td>{row.share_of_candidates:.2%}</td>"
        "</tr>"
        for row in rows
    )
    return f"""
    <section class="card">
      <h2>{html.escape(title)}</h2>
      <table><thead><tr><th>section</th><th>bucket</th><th>rows</th><th>buy/sell</th><th>win rate</th><th>total pnl</th><th>PF</th><th>DD</th><th>share</th></tr></thead><tbody>{body}</tbody></table>
    </section>
    """


def transfer_table(rows: Sequence[TransferRow]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{row.fold}</td>"
        f"<td>{html.escape(row.validation_months)}</td>"
        f"<td>{html.escape(row.test_month)}</td>"
        f"<td>{html.escape(row.selected_mode)}</td>"
        f"<td>{row.selected_score_threshold:.3f}</td>"
        f"<td>{row.validation_score:+.2f}</td>"
        f"<td>{row.validation_profit_factor:.3f}</td>"
        f"<td>{row.validation_trades:,}</td>"
        f"<td>{row.no_trade_selected}</td>"
        f"<td>{row.tensor_total_pnl:+.2f}</td>"
        f"<td>{row.tensor_profit_factor:.3f}</td>"
        f"<td>{row.tensor_trades:,}</td>"
        f"<td>{html.escape(row.transfer_status)}</td>"
        "</tr>"
        for row in rows
    )
    return f"""
    <section class="card">
      <h2>Validation → Test Transfer</h2>
      <table><thead><tr><th>fold</th><th>validation</th><th>test</th><th>mode</th><th>score th</th><th>val score</th><th>val PF</th><th>val trades</th><th>no trade</th><th>test pnl</th><th>test PF</th><th>test trades</th><th>status</th></tr></thead><tbody>{body}</tbody></table>
    </section>
    """


def render_html(
    report: DiagnosticReport,
    regime_rows: Sequence[RegimeRow],
    transfer_rows: Sequence[TransferRow],
    top_n: int,
) -> str:
    worst = top_rows(regime_rows, top_n, worst=True)
    best = top_rows(regime_rows, top_n, worst=False)
    flags = "".join(f"<li>{html.escape(flag)}</li>" for flag in report.risk_flags)
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phase136A Tensor Failure / Regime Diagnostics</title>
  <style>
    body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma, Segoe UI, Arial, sans-serif; line-height:1.7; }}
    main {{ max-width:1500px; margin:0 auto; padding:24px; }}
    .hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; box-shadow:0 18px 40px rgba(0,0,0,.24); }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
    .metric span {{ display:block; color:#94a3b8; font-size:13px; }}
    .metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
    table {{ border-collapse:collapse; width:100%; direction:ltr; text-align:left; font-size:12px; }}
    th,td {{ border-bottom:1px solid #1e293b; padding:7px; vertical-align:top; }}
    th {{ color:#bae6fd; background:#02061799; }}
    code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; color:#dbeafe; padding:10px; }}
    .warn {{ border-right:4px solid #f59e0b; background:#f59e0b1a; border-radius:10px; padding:10px; }}
    .danger {{ border-right:4px solid #ef4444; background:#ef44441a; border-radius:10px; padding:10px; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
  </style>
</head>
<body><main>
  <section class="hero">
    <h1>Phase136A — Tensor Failure / Regime Diagnostics</h1>
    <p>این report برای فهم شکست Phase133B/C است. اینجا مدل train نمی‌شود و هیچ مجوز paper/live صادر نمی‌شود.</p>
    <div class="grid">
      <div class="metric"><span>Candidate rows</span><strong>{report.candidate_rows:,}</strong></div>
      <div class="metric"><span>Candidate total PnL</span><strong>{report.total_pnl:+.2f}</strong></div>
      <div class="metric"><span>Candidate PF</span><strong>{report.profit_factor:.3f}</strong></div>
      <div class="metric"><span>Transfer PnL</span><strong>{report.transfer_total_pnl:+.2f}</strong></div>
    </div>
    <div class="danger"><strong>Production remains blocked.</strong> This is diagnostic-only.</div>
  </section>
  <section class="card"><h2>Risk flags</h2><ul>{flags}</ul></section>
  {transfer_table(transfer_rows)}
  {regime_table(worst, f"Worst {top_n} candidate regimes")}
  {regime_table(best, f"Best {top_n} candidate regimes")}
  {regime_table([row for row in regime_rows if row.section in ('month', 'side', 'month_side')], "Month / Side candidate distribution")}
</main></body></html>"""


def build_report(
    flat_path: Path,
    walk_forward_path: Path,
    output_dir: Path,
    candidate_frame: pd.DataFrame,
    regime_rows: Sequence[RegimeRow],
    transfer_rows: Sequence[TransferRow],
    walk_forward_payload: Mapping[str, Any],
) -> DiagnosticReport:
    pnls = candidate_frame["target_pnl_float"].astype(float).tolist()
    month_rows = [row for row in regime_rows if row.section == "month"]
    worst = min(month_rows, key=lambda row: row.total_pnl, default=None)
    best = max(month_rows, key=lambda row: row.total_pnl, default=None)
    transfer_pnls = [row.tensor_total_pnl for row in transfer_rows]
    wf_aggregate = walk_forward_payload.get("aggregate", {}) or {}
    flags = risk_flags(regime_rows, transfer_rows)
    return DiagnosticReport(
        flat_path=str(flat_path),
        walk_forward_json=str(walk_forward_path),
        candidate_rows=len(candidate_frame),
        months=len({str(value) for value in candidate_frame["month"].tolist()}),
        total_pnl=float(sum(pnls)),
        win_rate=safe_div(int(candidate_frame["target_win_bool"].sum()), len(candidate_frame)),
        profit_factor=profit_factor(pnls),
        worst_month="" if worst is None else worst.bucket,
        best_month="" if best is None else best.bucket,
        transfer_rows=len(transfer_rows),
        transfer_total_pnl=safe_float(wf_aggregate.get("tensor_total_pnl"), sum(transfer_pnls)),
        transfer_profit_factor=safe_float(
            wf_aggregate.get("tensor_profit_factor"), profit_factor(transfer_pnls)
        ),
        no_trade_months=int(
            safe_float(
                wf_aggregate.get("no_trade_months"),
                sum(1 for row in transfer_rows if row.no_trade_selected),
            )
        ),
        risk_flags=flags,
        output_json=str(output_dir / "latest.json"),
        output_html=str(output_dir / "latest.html"),
        output_regime_csv=str(output_dir / "latest_regimes.csv"),
        output_transfer_csv=str(output_dir / "latest_transfer.csv"),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    storage_root = Path(args.storage_root)
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    walk_forward_path = Path(args.walk_forward_json)
    try:
        print("\n" + "=" * 74)
        print("  PHASE136A TENSOR FAILURE / REGIME DIAGNOSTICS")
        print("=" * 74)
        print(f"  flat        : {flat_path}")
        print(f"  walk-forward: {walk_forward_path}")
        flat = pd.read_parquet(flat_path)
        candidate_frame = prepare_candidate_frame(flat, args.candidate_only)
        if candidate_frame.empty:
            raise RuntimeError("No candidate rows available for regime diagnostics")
        regime_rows = build_regime_rows(
            candidate_frame, max(args.min_group_rows, 1), max(args.quantile_bins, 2)
        )
        walk_forward_payload = read_json(walk_forward_path)
        transfer_rows = build_transfer_rows(walk_forward_payload)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report = build_report(
            flat_path,
            walk_forward_path,
            output_dir,
            candidate_frame,
            regime_rows,
            transfer_rows,
            walk_forward_payload,
        )
        write_csv(Path(report.output_regime_csv), regime_rows)
        write_csv(Path(report.output_transfer_csv), transfer_rows)
        Path(report.output_html).write_text(
            render_html(report, regime_rows, transfer_rows, max(args.top_n, 1)),
            encoding="utf-8",
        )
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "transfer_rows": [asdict(row) for row in transfer_rows],
            "worst_regimes": [asdict(row) for row in top_rows(regime_rows, args.top_n, True)],
            "best_regimes": [asdict(row) for row in top_rows(regime_rows, args.top_n, False)],
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "regime_csv": report.output_regime_csv,
                "transfer_csv": report.output_transfer_csv,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  candidates  : {report.candidate_rows:,}")
        print(f"  cand pnl    : {report.total_pnl:+.2f}")
        print(f"  cand PF     : {report.profit_factor:.3f}")
        print(f"  transfer pnl: {report.transfer_total_pnl:+.2f}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
