"""Phase138A: analyze hybrid trade anatomy and TP/SL failure modes.

This diagnostic phase does not train models and does not approve production.
It explains why the candidate stream loses money by inspecting side, outcome,
TP/SL distance, reward/risk, range context and hold-time anatomy.
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
from typing import Any, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/trade_anatomy")


@dataclass(frozen=True)
class AnatomyGroupRow:
    section: str
    bucket: str
    rows: int
    buy_rows: int
    sell_rows: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    take_profit_rate: float
    stop_loss_rate: float
    timeout_rate: float
    avg_tp_distance: float
    avg_sl_distance: float
    avg_reward_risk: float
    avg_hold_bars: float
    share_of_candidates: float
    notes: str


@dataclass(frozen=True)
class AnatomyReport:
    flat_path: str
    candidate_rows: int
    months: int
    total_pnl: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    take_profit_rate: float
    stop_loss_rate: float
    timeout_rate: float
    buy_rows: int
    buy_total_pnl: float
    buy_profit_factor: float
    buy_stop_loss_rate: float
    buy_avg_sl_distance: float
    sell_rows: int
    sell_total_pnl: float
    sell_profit_factor: float
    sell_stop_loss_rate: float
    sell_avg_sl_distance: float
    worst_month: str
    best_month: str
    risk_flags: list[str]
    output_json: str
    output_html: str
    output_csv: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze TP/SL and trade anatomy failure modes in hybrid telemetry.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--allowed-sides", default="BUY,SELL")
    parser.add_argument("--min-group-rows", type=int, default=20)
    parser.add_argument("--quantile-bins", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=15)
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
    code = safe_float(value)
    if code > 0.5:
        return "take_profit"
    if code < -0.5:
        return "stop_loss"
    return "timeout"


def parse_sides(text: str) -> set[str]:
    sides = {item.strip().upper() for item in text.split(",") if item.strip()}
    return sides or {"BUY", "SELL"}


def prepare_candidate_frame(frame: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    result = frame.replace([np.inf, -np.inf], 0.0).fillna(0.0).copy()
    if args.candidate_only == "1":
        if "candidate_mask" not in result.columns:
            raise RuntimeError("candidate-only analysis needs candidate_mask column")
        result = result[result["candidate_mask"].astype(float) >= 0.5].copy()
    result["timestamp_dt"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["month"] = result["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
    if args.start_month:
        result = result[result["month"] >= args.start_month].copy()
    if args.end_month:
        result = result[result["month"] <= args.end_month].copy()
    result["hour"] = result["timestamp_dt"].dt.hour.fillna(-1).astype(int).astype(str)
    result["side"] = np.where(result["target_side"].astype(float) >= 0, "BUY", "SELL")
    allowed_sides = parse_sides(args.allowed_sides)
    result = result[result["side"].isin(allowed_sides)].copy()
    result["target_pnl_float"] = result["target_trade_pnl"].astype(float)
    result["target_win_bool"] = result["target_trade_win"].astype(float) >= 0.5
    result["outcome"] = result["target_outcome_code"].map(outcome_label)
    result["entry_price"] = result.get("candidate_entry_price", 0.0).astype(float)
    result["tp_price"] = result.get("candidate_take_profit", 0.0).astype(float)
    result["sl_price"] = result.get("candidate_stop_loss", 0.0).astype(float)
    result["tp_distance_calc"] = np.where(
        result.get("candidate_tp_distance", 0.0).astype(float) > 0,
        result.get("candidate_tp_distance", 0.0).astype(float),
        (result["tp_price"] - result["entry_price"]).abs(),
    )
    result["sl_distance_calc"] = np.where(
        result.get("candidate_sl_distance", 0.0).astype(float) > 0,
        result.get("candidate_sl_distance", 0.0).astype(float),
        (result["entry_price"] - result["sl_price"]).abs(),
    )
    result["reward_risk_calc"] = np.where(
        result["sl_distance_calc"].abs() > 1e-9,
        result["tp_distance_calc"] / result["sl_distance_calc"].replace(0.0, np.nan),
        0.0,
    )
    result["reward_risk_calc"] = (
        result["reward_risk_calc"].replace([np.inf, -np.inf], 0.0).fillna(0.0)
    )
    result["hold_bars"] = (
        result.get("target_exit_index", -1).astype(float)
        - result.get("source_index", 0).astype(float)
    ).clip(lower=0)
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
    result["month_side"] = result["month"].astype(str) + " / " + result["side"].astype(str)
    result["side_outcome"] = result["side"].astype(str) + " / " + result["outcome"].astype(str)
    result["side_hour"] = result["side"].astype(str) + " / hour=" + result["hour"].astype(str)
    return result.reset_index(drop=True)


def summarize_subset(
    section: str, bucket: str, subset: pd.DataFrame, total_rows: int
) -> AnatomyGroupRow:
    pnls = subset["target_pnl_float"].astype(float).tolist()
    wins = int(subset["target_win_bool"].sum())
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    return AnatomyGroupRow(
        section=section,
        bucket=str(bucket),
        rows=int(len(subset)),
        buy_rows=int((subset["side"] == "BUY").sum()),
        sell_rows=int((subset["side"] == "SELL").sum()),
        wins=wins,
        losses=int(len(subset) - wins),
        win_rate=safe_div(wins, len(subset)),
        total_pnl=float(sum(pnls)),
        avg_pnl=safe_div(sum(pnls), len(subset)),
        gross_profit=float(gross_profit),
        gross_loss=float(gross_loss),
        profit_factor=profit_factor(pnls),
        max_drawdown=max_drawdown(pnls),
        take_profit_rate=safe_div(int((subset["outcome"] == "take_profit").sum()), len(subset)),
        stop_loss_rate=safe_div(int((subset["outcome"] == "stop_loss").sum()), len(subset)),
        timeout_rate=safe_div(int((subset["outcome"] == "timeout").sum()), len(subset)),
        avg_tp_distance=(
            float(subset["tp_distance_calc"].astype(float).mean()) if len(subset) else 0.0
        ),
        avg_sl_distance=(
            float(subset["sl_distance_calc"].astype(float).mean()) if len(subset) else 0.0
        ),
        avg_reward_risk=(
            float(subset["reward_risk_calc"].astype(float).mean()) if len(subset) else 0.0
        ),
        avg_hold_bars=float(subset["hold_bars"].astype(float).mean()) if len(subset) else 0.0,
        share_of_candidates=safe_div(len(subset), total_rows),
        notes="candidate anatomy; not chronological replay",
    )


def group_summary(
    frame: pd.DataFrame, section: str, column: str, min_rows: int
) -> list[AnatomyGroupRow]:
    if column not in frame.columns:
        return []
    total_rows = len(frame)
    rows: list[AnatomyGroupRow] = []
    for bucket, subset in frame.groupby(column, sort=True, dropna=False):
        if len(subset) >= min_rows:
            rows.append(summarize_subset(section, str(bucket), subset, total_rows))
    return sorted(rows, key=lambda row: row.total_pnl)


def quantile_labels(series: pd.Series, bins: int) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if numeric.nunique(dropna=True) < 2:
        return pd.Series(["single_or_missing"] * len(series), index=series.index)
    try:
        bucketed = pd.qcut(numeric, q=max(bins, 2), duplicates="drop")
    except ValueError:
        return pd.Series(["single_or_missing"] * len(series), index=series.index)
    return bucketed.astype(str).fillna("missing")


def numeric_bin_summary(
    frame: pd.DataFrame, section: str, column: str, bins: int, min_rows: int
) -> list[AnatomyGroupRow]:
    if column not in frame.columns:
        return []
    work = frame.copy()
    bucket_column = f"__bucket_{column}"
    work[bucket_column] = quantile_labels(work[column], bins)
    return group_summary(work, section, bucket_column, min_rows)


def build_anatomy_rows(frame: pd.DataFrame, min_rows: int, bins: int) -> list[AnatomyGroupRow]:
    rows: list[AnatomyGroupRow] = []
    for section, column in [
        ("side", "side"),
        ("outcome", "outcome"),
        ("side_outcome", "side_outcome"),
        ("month", "month"),
        ("month_side", "month_side"),
        ("hour", "hour"),
        ("side_hour", "side_hour"),
    ]:
        rows.extend(group_summary(frame, section, column, min_rows))
    for section, column in [
        ("tp_distance_bin", "tp_distance_calc"),
        ("sl_distance_bin", "sl_distance_calc"),
        ("reward_risk_bin", "reward_risk_calc"),
        ("hold_bars_bin", "hold_bars"),
        ("side_4h_room_bin", "side_4h_room"),
        ("side_1d_room_bin", "side_1d_room"),
        ("range_4h_width_bin", "range_4h_width"),
        ("range_1d_width_bin", "range_1d_width"),
        ("candidate_confidence_bin", "candidate_confidence"),
        ("candidate_reward_risk_bin", "candidate_reward_risk"),
        ("candidate_sl_distance_bin", "candidate_sl_distance"),
        ("candidate_tp_distance_bin", "candidate_tp_distance"),
    ]:
        rows.extend(numeric_bin_summary(frame, section, column, bins, min_rows))
    return rows


def side_row(rows: Sequence[AnatomyGroupRow], side: str) -> AnatomyGroupRow | None:
    for row in rows:
        if row.section == "side" and row.bucket == side:
            return row
    return None


def risk_flags(rows: Sequence[AnatomyGroupRow], frame: pd.DataFrame) -> list[str]:
    flags: list[str] = []
    all_row = summarize_subset("all", "all", frame, len(frame))
    if all_row.stop_loss_rate > 0.50:
        flags.append(f"Stop-loss rate is above 50%: {all_row.stop_loss_rate:.2%}.")
    buy = side_row(rows, "BUY")
    sell = side_row(rows, "SELL")
    if buy and buy.total_pnl < 0:
        flags.append(
            f"BUY candidate anatomy is negative: {buy.total_pnl:+.2f} raw PnL, PF={buy.profit_factor:.3f}."
        )
    if sell and sell.total_pnl < 0:
        flags.append(
            f"SELL candidate anatomy is negative: {sell.total_pnl:+.2f} raw PnL, PF={sell.profit_factor:.3f}."
        )
    stop_loss = [row for row in rows if row.section == "outcome" and row.bucket == "stop_loss"]
    if stop_loss:
        flags.append(
            f"Stop-loss candidates account for {stop_loss[0].rows:,} rows and {stop_loss[0].total_pnl:+.2f} raw PnL."
        )
    worst = sorted(
        [row for row in rows if row.section in {"month", "month_side"}],
        key=lambda item: item.total_pnl,
    )[:3]
    for row in worst:
        flags.append(f"Worst {row.section} bucket: {row.bucket} with {row.total_pnl:+.2f} raw PnL.")
    return flags or ["No dominant anatomy flag found; inspect CSV tables."]


def build_report(
    flat_path: Path, output_dir: Path, frame: pd.DataFrame, rows: Sequence[AnatomyGroupRow]
) -> AnatomyReport:
    all_row = summarize_subset("all", "all", frame, len(frame))
    buy = side_row(rows, "BUY")
    sell = side_row(rows, "SELL")
    month_rows = [row for row in rows if row.section == "month"]
    worst = min(month_rows, key=lambda row: row.total_pnl, default=None)
    best = max(month_rows, key=lambda row: row.total_pnl, default=None)
    return AnatomyReport(
        flat_path=str(flat_path),
        candidate_rows=len(frame),
        months=len({str(value) for value in frame["month"].tolist()}),
        total_pnl=all_row.total_pnl,
        win_rate=all_row.win_rate,
        profit_factor=all_row.profit_factor,
        max_drawdown=all_row.max_drawdown,
        take_profit_rate=all_row.take_profit_rate,
        stop_loss_rate=all_row.stop_loss_rate,
        timeout_rate=all_row.timeout_rate,
        buy_rows=0 if buy is None else buy.rows,
        buy_total_pnl=0.0 if buy is None else buy.total_pnl,
        buy_profit_factor=0.0 if buy is None else buy.profit_factor,
        buy_stop_loss_rate=0.0 if buy is None else buy.stop_loss_rate,
        buy_avg_sl_distance=0.0 if buy is None else buy.avg_sl_distance,
        sell_rows=0 if sell is None else sell.rows,
        sell_total_pnl=0.0 if sell is None else sell.total_pnl,
        sell_profit_factor=0.0 if sell is None else sell.profit_factor,
        sell_stop_loss_rate=0.0 if sell is None else sell.stop_loss_rate,
        sell_avg_sl_distance=0.0 if sell is None else sell.avg_sl_distance,
        worst_month="" if worst is None else worst.bucket,
        best_month="" if best is None else best.bucket,
        risk_flags=risk_flags(rows, frame),
        output_json=str(output_dir / "latest.json"),
        output_html=str(output_dir / "latest.html"),
        output_csv=str(output_dir / "latest_anatomy.csv"),
    )


def write_csv(path: Path, rows: Sequence[AnatomyGroupRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def top_rows(rows: Sequence[AnatomyGroupRow], top_n: int, worst: bool) -> list[AnatomyGroupRow]:
    return sorted(rows, key=lambda row: row.total_pnl, reverse=not worst)[: max(top_n, 1)]


def table(rows: Sequence[AnatomyGroupRow], title: str) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.section)}</td>"
        f"<td>{html.escape(row.bucket)}</td>"
        f"<td>{row.rows:,}</td>"
        f"<td>{row.buy_rows:,}/{row.sell_rows:,}</td>"
        f"<td>{row.win_rate:.2%}</td>"
        f"<td>{row.take_profit_rate:.2%}</td>"
        f"<td>{row.stop_loss_rate:.2%}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        f"<td>{row.avg_tp_distance:.2f}</td>"
        f"<td>{row.avg_sl_distance:.2f}</td>"
        f"<td>{row.avg_reward_risk:.3f}</td>"
        f"<td>{row.avg_hold_bars:.1f}</td>"
        "</tr>"
        for row in rows
    )
    return f"""
    <section class="card">
      <h2>{html.escape(title)}</h2>
      <table><thead><tr><th>section</th><th>bucket</th><th>rows</th><th>buy/sell</th><th>win</th><th>TP</th><th>SL</th><th>pnl</th><th>PF</th><th>avg TP dist</th><th>avg SL dist</th><th>avg RR</th><th>avg hold</th></tr></thead><tbody>{body}</tbody></table>
    </section>
    """


def render_html(report: AnatomyReport, rows: Sequence[AnatomyGroupRow], top_n: int) -> str:
    flags = "".join(f"<li>{html.escape(flag)}</li>" for flag in report.risk_flags)
    worst = top_rows(rows, top_n, worst=True)
    best = top_rows(rows, top_n, worst=False)
    core = [row for row in rows if row.section in {"side", "outcome", "month", "month_side"}]
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Phase138A Trade Anatomy / TP-SL Failure Analysis</title>
  <style>
    body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma, Segoe UI, Arial, sans-serif; line-height:1.7; }}
    main {{ max-width:1500px; margin:0 auto; padding:24px; }}
    .hero,.card {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
    .metric span {{ display:block; color:#94a3b8; font-size:13px; }}
    .metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
    table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:12px; }}
    th,td {{ border-bottom:1px solid #1e293b; padding:7px; vertical-align:top; }} th {{ color:#bae6fd; }}
    .danger {{ border-right:4px solid #ef4444; background:#ef44441a; border-radius:10px; padding:10px; }}
    @media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:12px; }} }}
  </style>
</head>
<body><main>
  <section class="hero">
    <h1>Phase138A — Trade Anatomy / TP-SL Failure Analysis</h1>
    <p>این گزارش برای فهم طراحی TP/SL و anatomy ضررهاست. مدل train نمی‌کند و مجوز paper/live نیست.</p>
    <div class="grid">
      <div class="metric"><span>Total PnL</span><strong>{report.total_pnl:+.2f}</strong></div>
      <div class="metric"><span>PF</span><strong>{report.profit_factor:.3f}</strong></div>
      <div class="metric"><span>Stop-loss rate</span><strong>{report.stop_loss_rate:.2%}</strong></div>
      <div class="metric"><span>BUY PnL</span><strong>{report.buy_total_pnl:+.2f}</strong></div>
    </div>
    <div class="danger">Production remains blocked. This is diagnostic-only.</div>
  </section>
  <section class="card"><h2>Risk flags</h2><ul>{flags}</ul></section>
  {table(core, "Core anatomy")}
  {table(worst, f"Worst {top_n} anatomy buckets")}
  {table(best, f"Best {top_n} anatomy buckets")}
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    storage_root = Path(args.storage_root)
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE138A TRADE ANATOMY / TP-SL FAILURE ANALYSIS")
        print("=" * 74)
        print(f"  flat        : {flat_path}")
        flat = pd.read_parquet(flat_path)
        frame = prepare_candidate_frame(flat, args)
        if frame.empty:
            raise RuntimeError("No candidate rows available for anatomy analysis")
        rows = build_anatomy_rows(frame, max(args.min_group_rows, 1), max(args.quantile_bins, 2))
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report = build_report(flat_path, output_dir, frame, rows)
        write_csv(Path(report.output_csv), rows)
        Path(report.output_html).write_text(
            render_html(report, rows, max(args.top_n, 1)), encoding="utf-8"
        )
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "side_rows": [asdict(row) for row in rows if row.section == "side"],
            "outcome_rows": [asdict(row) for row in rows if row.section == "outcome"],
            "worst_rows": [asdict(row) for row in top_rows(rows, args.top_n, True)],
            "best_rows": [asdict(row) for row in top_rows(rows, args.top_n, False)],
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "csv": report.output_csv,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  candidates  : {report.candidate_rows:,}")
        print(f"  total pnl   : {report.total_pnl:+.2f}")
        print(f"  PF          : {report.profit_factor:.3f}")
        print(f"  SL rate     : {report.stop_loss_rate:.2%}")
        print(f"  BUY pnl     : {report.buy_total_pnl:+.2f}")
        print(f"  SELL pnl    : {report.sell_total_pnl:+.2f}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
