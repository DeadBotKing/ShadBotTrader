"""Phase137A: backtest live-safe regime filters on hybrid telemetry candidates.

This script does not train a model. It tests hypotheses from Phase136A, such as
"SELL pockets look better" or "BUY needs stricter gates", through the same
chronological single-position replay style used by the meta-filter backtests.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_meta_labeler import MetaThresholdSpec
from backtest_hybrid_meta_labeler import backtest as backtest_flat_meta
from report_hybrid_full_backtest import (
    FixedBacktestSummary,
    account_summary,
    monthly_summary,
    safe_div,
)
from train_hybrid_meta_labeler import default_flat_path

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/regime_filtered_hybrid")
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class RegimeFilterReport:
    rows: int
    evaluated_rows: int
    source_candidates: int
    kept_candidates: int
    removed_candidates: int
    kept_rate: float
    base_total_pnl: float
    base_profit_factor: float
    base_max_drawdown: float
    base_trades: int
    filtered_total_pnl: float
    filtered_profit_factor: float
    filtered_max_drawdown: float
    filtered_trades: int
    filtered_win_rate: float
    filtered_final_balance: float
    improvement_vs_base: float
    filter_score: float
    output_json: str
    output_html: str
    output_csv: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest side-aware regime filters on Phase127 flat telemetry candidates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--allowed-sides", default="BUY,SELL")
    parser.add_argument("--allowed-hours", default="")
    parser.add_argument("--buy-allowed-hours", default="")
    parser.add_argument("--sell-allowed-hours", default="")
    parser.add_argument("--min-candidate-confidence", type=float, default=0.0)
    parser.add_argument("--buy-min-confidence", type=float, default=-1.0)
    parser.add_argument("--sell-min-confidence", type=float, default=-1.0)
    parser.add_argument("--min-reward-risk", type=float, default=0.0)
    parser.add_argument("--buy-min-reward-risk", type=float, default=-1.0)
    parser.add_argument("--sell-min-reward-risk", type=float, default=-1.0)
    parser.add_argument("--max-sl-distance", type=float, default=-1.0)
    parser.add_argument("--buy-max-sl-distance", type=float, default=-1.0)
    parser.add_argument("--sell-max-sl-distance", type=float, default=-1.0)
    parser.add_argument("--min-side-4h-room", type=float, default=0.0)
    parser.add_argument("--buy-min-side-4h-room", type=float, default=-1.0)
    parser.add_argument("--sell-min-side-4h-room", type=float, default=-1.0)
    parser.add_argument("--min-side-1d-room", type=float, default=0.0)
    parser.add_argument("--buy-min-side-1d-room", type=float, default=-1.0)
    parser.add_argument("--sell-min-side-1d-room", type=float, default=-1.0)
    parser.add_argument("--min-range-4h-width", type=float, default=-1.0)
    parser.add_argument("--max-range-4h-width", type=float, default=-1.0)
    parser.add_argument("--min-range-1d-width", type=float, default=-1.0)
    parser.add_argument("--max-range-1d-width", type=float, default=-1.0)
    parser.add_argument("--block-specialist-conflict", choices=("0", "1"), default="0")
    parser.add_argument("--max-booster-entropy", type=float, default=-1.0)
    parser.add_argument("--min-booster-action-margin", type=float, default=0.0)
    parser.add_argument("--min-specialist-max-prob", type=float, default=0.0)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Regime-filtered hybrid replay")
    return parser.parse_args(argv)


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def parse_set(text: str) -> set[str]:
    return {item.strip().upper() for item in text.split(",") if item.strip()}


def parse_hours(text: str) -> set[int]:
    hours: set[int] = set()
    for token in (item.strip() for item in text.split(",") if item.strip()):
        try:
            hour = int(token)
        except ValueError:
            continue
        if 0 <= hour <= 23:
            hours.add(hour)
    return hours


def side_for_row(row: pd.Series) -> str:
    return "BUY" if float(row.get("target_side", 0.0)) >= 0 else "SELL"


def side_value(row: pd.Series, side: str, buy_column: str, sell_column: str) -> float:
    column = buy_column if side == "BUY" else sell_column
    return float(row.get(column, 0.0) or 0.0)


def side_threshold(side: str, global_value: float, buy_value: float, sell_value: float) -> float:
    if side == "BUY" and buy_value >= 0:
        return buy_value
    if side == "SELL" and sell_value >= 0:
        return sell_value
    return global_value


def prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.replace([np.inf, -np.inf], 0.0).fillna(0.0).copy()
    result["timestamp_dt"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["month"] = result["timestamp_dt"].dt.strftime("%Y-%m").fillna("unknown")
    result["hour"] = result["timestamp_dt"].dt.hour.fillna(-1).astype(int)
    result["side"] = np.where(result["target_side"].astype(float) >= 0, "BUY", "SELL")
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
    return result


def month_filter(frame: pd.DataFrame, start_month: str, end_month: str) -> pd.DataFrame:
    result = frame
    if start_month:
        result = result[result["month"] >= start_month]
    if end_month:
        result = result[result["month"] <= end_month]
    return result.copy()


def failure_reason(row: pd.Series, args: argparse.Namespace) -> str:
    side = str(row.get("side", side_for_row(row)))
    allowed_sides = parse_set(args.allowed_sides) or {"BUY", "SELL"}
    if side not in allowed_sides:
        return "side_not_allowed"

    global_hours = parse_hours(args.allowed_hours)
    buy_hours = parse_hours(args.buy_allowed_hours)
    sell_hours = parse_hours(args.sell_allowed_hours)
    hour = int(row.get("hour", -1))
    if global_hours and hour not in global_hours:
        return "hour_not_allowed"
    if side == "BUY" and buy_hours and hour not in buy_hours:
        return "buy_hour_not_allowed"
    if side == "SELL" and sell_hours and hour not in sell_hours:
        return "sell_hour_not_allowed"

    min_confidence = side_threshold(
        side, args.min_candidate_confidence, args.buy_min_confidence, args.sell_min_confidence
    )
    if float(row.get("candidate_confidence", 0.0)) < min_confidence:
        return "candidate_confidence_below_min"

    min_reward_risk = side_threshold(
        side, args.min_reward_risk, args.buy_min_reward_risk, args.sell_min_reward_risk
    )
    if float(row.get("candidate_reward_risk", 0.0)) < min_reward_risk:
        return "reward_risk_below_min"

    max_sl = side_threshold(
        side, args.max_sl_distance, args.buy_max_sl_distance, args.sell_max_sl_distance
    )
    if max_sl >= 0 and float(row.get("candidate_sl_distance", 0.0)) > max_sl:
        return "sl_distance_above_max"

    min_4h = side_threshold(
        side, args.min_side_4h_room, args.buy_min_side_4h_room, args.sell_min_side_4h_room
    )
    if float(row.get("side_4h_room", 0.0)) < min_4h:
        return "side_4h_room_below_min"

    min_1d = side_threshold(
        side, args.min_side_1d_room, args.buy_min_side_1d_room, args.sell_min_side_1d_room
    )
    if float(row.get("side_1d_room", 0.0)) < min_1d:
        return "side_1d_room_below_min"

    if (
        args.min_range_4h_width >= 0
        and float(row.get("range_4h_width", 0.0)) < args.min_range_4h_width
    ):
        return "range_4h_width_below_min"
    if (
        args.max_range_4h_width >= 0
        and float(row.get("range_4h_width", 0.0)) > args.max_range_4h_width
    ):
        return "range_4h_width_above_max"
    if (
        args.min_range_1d_width >= 0
        and float(row.get("range_1d_width", 0.0)) < args.min_range_1d_width
    ):
        return "range_1d_width_below_min"
    if (
        args.max_range_1d_width >= 0
        and float(row.get("range_1d_width", 0.0)) > args.max_range_1d_width
    ):
        return "range_1d_width_above_max"

    if args.block_specialist_conflict == "1" and float(row.get("specialist_conflict", 0.0)) >= 0.5:
        return "specialist_conflict_blocked"
    if (
        args.max_booster_entropy >= 0
        and float(row.get("booster_entropy", 0.0)) > args.max_booster_entropy
    ):
        return "booster_entropy_above_max"
    if float(row.get("booster_action_margin", 0.0)) < args.min_booster_action_margin:
        return "booster_margin_below_min"
    if float(row.get("specialist_max_prob", 0.0)) < args.min_specialist_max_prob:
        return "specialist_max_prob_below_min"
    return "kept"


def apply_regime_filter(
    frame: pd.DataFrame, args: argparse.Namespace
) -> tuple[pd.DataFrame, dict[str, int]]:
    result = frame.copy()
    candidate_mask = result["candidate_mask"].astype(float) >= 0.5
    reasons: dict[str, int] = {}
    keep = np.zeros(len(result), dtype=bool)
    for index, row in result.loc[candidate_mask].iterrows():
        reason = failure_reason(row, args)
        reasons[reason] = reasons.get(reason, 0) + 1
        if reason == "kept":
            keep[int(index)] = True
    filtered_mask = np.where(keep, 1.0, 0.0).astype(np.float32)
    result["candidate_mask"] = filtered_mask
    return result, reasons


def run_replay(frame: pd.DataFrame) -> tuple[FixedBacktestSummary, Any, list[Any]]:
    return backtest_flat_meta(
        frame,
        np.ones(len(frame), dtype=np.float64),
        MetaThresholdSpec(meta_threshold=0.0, score_threshold=0.0, source="regime_filter"),
        task="classifier",
    )


def score_value(summary: FixedBacktestSummary, account: Mapping[str, Any], metric: str) -> float:
    if metric == "profit_factor":
        return summary.profit_factor
    if metric == "final_balance":
        return float(account["final_balance"])
    if metric == "drawdown_adjusted":
        return summary.total_pnl - summary.max_drawdown
    return summary.total_pnl


def write_trades_csv(path: Path, trades: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not trades:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(trades[0]).keys()))
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def monthly_payload(trades: Sequence[Any]) -> list[dict[str, Any]]:
    return [asdict(row) for row in monthly_summary(trades)]


def render_html(
    title: str,
    args: argparse.Namespace,
    report: RegimeFilterReport,
    base_summary: FixedBacktestSummary,
    filtered_summary: FixedBacktestSummary,
    reason_counts: Mapping[str, int],
    monthly: Sequence[Mapping[str, Any]],
) -> str:
    reason_rows = "".join(
        f"<tr><td>{html.escape(reason)}</td><td>{count:,}</td></tr>"
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    )
    month_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('month', '')))}</td>"
        f"<td>{int(row.get('trades', 0)):,}</td>"
        f"<td>{int(row.get('wins', 0)):,}</td>"
        f"<td>{int(row.get('losses', 0)):,}</td>"
        f"<td>{float(row.get('total_pnl', 0.0)):+.2f}</td>"
        f"<td>{float(row.get('profit_factor', 0.0)):.3f}</td>"
        "</tr>"
        for row in monthly
    )
    payload = {
        "filters": {
            key: value
            for key, value in vars(args).items()
            if key
            not in {
                "storage_root",
                "output_dir",
                "report_title",
                "initial_capital",
                "units",
            }
        },
        "report": asdict(report),
        "base_summary": asdict(base_summary),
        "filtered_summary": asdict(filtered_summary),
    }
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma, Segoe UI, Arial, sans-serif; line-height:1.7; }}
    main {{ max-width:1400px; margin:0 auto; padding:24px; }}
    .card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
    .metric span {{ display:block; color:#94a3b8; font-size:13px; }}
    .metric strong {{ direction:ltr; text-align:left; display:block; font-size:22px; color:#7dd3fc; }}
    table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:13px; }}
    th,td {{ border-bottom:1px solid #1e293b; padding:8px; }} th {{ color:#bae6fd; }}
    pre {{ direction:ltr; text-align:left; overflow:auto; background:#020617; border:1px solid #334155; border-radius:10px; padding:12px; }}
  </style>
</head>
<body><main>
  <section class="hero">
    <h1>{html.escape(title)}</h1>
    <p>Phase137A tests live-safe, side-aware regime filters. It does not remove BUY permanently; it lets us compare strict BUY, SELL-only and mixed filters honestly.</p>
    <div class="grid">
      <div class="metric"><span>Base PnL</span><strong>{base_summary.total_pnl:+.2f}</strong></div>
      <div class="metric"><span>Filtered PnL</span><strong>{filtered_summary.total_pnl:+.2f}</strong></div>
      <div class="metric"><span>Filtered PF</span><strong>{filtered_summary.profit_factor:.3f}</strong></div>
      <div class="metric"><span>Kept candidates</span><strong>{report.kept_candidates:,}</strong></div>
    </div>
  </section>
  <section class="card"><h2>Filter reasons</h2><table><thead><tr><th>reason</th><th>count</th></tr></thead><tbody>{reason_rows}</tbody></table></section>
  <section class="card"><h2>Filtered monthly replay</h2><table><thead><tr><th>month</th><th>trades</th><th>wins</th><th>losses</th><th>pnl</th><th>PF</th></tr></thead><tbody>{month_rows}</tbody></table></section>
  <section class="card"><h2>Payload</h2><pre>{html.escape(json.dumps(payload, indent=2, ensure_ascii=False))}</pre></section>
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
        print("  PHASE137A REGIME-FILTERED HYBRID REPLAY")
        print("=" * 74)
        print(f"  flat        : {flat_path}")
        frame_all = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        frame_all = prepare_frame(frame_all)
        frame_all = month_filter(frame_all, args.start_month, args.end_month)
        if frame_all.empty:
            raise RuntimeError("No rows left after month filter")
        indices = eval_indices(len(frame_all), args.eval_frac, args.max_windows)
        frame = frame_all.iloc[indices].copy().reset_index(drop=True)
        source_candidates = int((frame["candidate_mask"].astype(float) >= 0.5).sum())
        base_summary, _base_counters, _base_trades = run_replay(frame.copy())
        filtered_frame, reason_counts = apply_regime_filter(frame, args)
        kept_candidates = int((filtered_frame["candidate_mask"].astype(float) >= 0.5).sum())
        filtered_summary, filtered_counters, filtered_trades = run_replay(filtered_frame)
        filtered_account = account_summary(filtered_summary, args.initial_capital, args.units)
        filtered_monthly = monthly_payload(filtered_trades)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "latest.csv"
        json_path = output_dir / "latest.json"
        html_path = output_dir / "latest.html"
        report = RegimeFilterReport(
            rows=len(frame_all),
            evaluated_rows=len(frame),
            source_candidates=source_candidates,
            kept_candidates=kept_candidates,
            removed_candidates=source_candidates - kept_candidates,
            kept_rate=safe_div(kept_candidates, source_candidates),
            base_total_pnl=base_summary.total_pnl,
            base_profit_factor=base_summary.profit_factor,
            base_max_drawdown=base_summary.max_drawdown,
            base_trades=base_summary.trades,
            filtered_total_pnl=filtered_summary.total_pnl,
            filtered_profit_factor=filtered_summary.profit_factor,
            filtered_max_drawdown=filtered_summary.max_drawdown,
            filtered_trades=filtered_summary.trades,
            filtered_win_rate=filtered_summary.win_rate,
            filtered_final_balance=float(filtered_account["final_balance"]),
            improvement_vs_base=filtered_summary.total_pnl - base_summary.total_pnl,
            filter_score=score_value(filtered_summary, filtered_account, args.score_metric),
            output_json=str(json_path),
            output_html=str(html_path),
            output_csv=str(csv_path),
        )
        write_trades_csv(csv_path, filtered_trades)
        html_path.write_text(
            render_html(
                args.report_title,
                args,
                report,
                base_summary,
                filtered_summary,
                reason_counts,
                filtered_monthly,
            ),
            encoding="utf-8",
        )
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "base_summary": asdict(base_summary),
            "filtered_summary": asdict(filtered_summary),
            "filtered_counters": asdict(filtered_counters),
            "filtered_account": filtered_account,
            "filtered_monthly": filtered_monthly,
            "filter_reason_counts": dict(
                sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
            "files": {"json": str(json_path), "html": str(html_path), "csv": str(csv_path)},
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  source cand : {source_candidates:,}")
        print(f"  kept cand   : {kept_candidates:,} ({report.kept_rate:.2%})")
        print(f"  base pnl    : {base_summary.total_pnl:+.2f}")
        print(f"  filt pnl    : {filtered_summary.total_pnl:+.2f}")
        print(f"  filt PF     : {filtered_summary.profit_factor:.3f}")
        print(f"  filt trades : {filtered_summary.trades:,}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
