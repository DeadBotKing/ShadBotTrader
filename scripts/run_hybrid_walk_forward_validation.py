"""Phase133A: walk-forward validation for the hybrid meta-labeler.

This phase trains only on the past, calibrates thresholds on past validation
months, and tests on the next unseen month/block. It intentionally starts with
the Phase128 flat telemetry meta-labeler because it is the fastest baseline and
the reference that heavier neural models must beat.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
SRC = REPO_ROOT / "src"
for import_path in (SCRIPT_DIR, SRC):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import numpy as np
import pandas as pd
from backtest_hybrid_meta_labeler import (
    MetaThresholdSpec,
    max_drawdown,
)
from backtest_hybrid_meta_labeler import (
    backtest as backtest_flat_meta,
)
from report_hybrid_full_backtest import FixedBacktestSummary, account_summary
from train_hybrid_meta_labeler import (
    BOOSTER_CHOICES,
    TASKS,
    class_weights,
    default_flat_path,
    feature_columns,
    make_model,
    positive_scores,
    sample_weights,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_walk_forward_validation")
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class FoldReport:
    fold: int
    test_month: str
    train_months: str
    validation_months: str
    train_rows: int
    validation_rows: int
    test_rows: int
    train_candidates: int
    validation_candidates: int
    test_candidates: int
    selected_threshold: float
    selected_validation_score: float
    base_trades: int
    base_total_pnl: float
    base_profit_factor: float
    base_max_drawdown: float
    meta_trades: int
    meta_total_pnl: float
    meta_profit_factor: float
    meta_max_drawdown: float
    meta_win_rate: float
    meta_coverage: float
    meta_final_balance: float
    meta_would_breach_zero: bool
    skipped_by_meta: int
    skipped_while_open: int


@dataclass(frozen=True)
class AggregateReport:
    folds: int
    test_months: int
    positive_months: int
    negative_months: int
    base_total_pnl: float
    meta_total_pnl: float
    meta_gross_profit: float
    meta_gross_loss: float
    meta_profit_factor: float
    meta_max_drawdown: float
    meta_trades: int
    meta_avg_pnl: float
    meta_final_balance: float
    meta_return_percent: float
    meta_would_breach_zero: bool
    best_month: str
    worst_month: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase133 walk-forward validation for the flat hybrid meta-labeler.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_meta_walkforward_5m")
    parser.add_argument("--task", choices=TASKS, default="classifier")
    parser.add_argument("--target", default="", help="empty = task default")
    parser.add_argument("--booster", choices=BOOSTER_CHOICES, default="lightgbm")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--train-months-min", type=int, default=3)
    parser.add_argument("--validation-months", type=int, default=1)
    parser.add_argument("--purge-gap-bars", type=int, default=336)
    parser.add_argument("--meta-thresholds", default="0.45,0.50,0.55,0.60,0.65,0.70")
    parser.add_argument("--score-thresholds", default="0,0.05,0.10,0.20")
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def target_column(args: argparse.Namespace) -> str:
    if args.target.strip():
        return args.target.strip()
    return "target_trade_win" if args.task == "classifier" else "target_trade_score_r"


def parse_thresholds(text: str) -> list[float]:
    values: list[float] = []
    for token in (item.strip() for item in text.split(",")):
        if token:
            values.append(float(token))
    return values or [0.55]


def month_labels(frame: pd.DataFrame) -> pd.Series:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    return timestamps.dt.strftime("%Y-%m")


def selected_months(all_months: Sequence[str], start_month: str, end_month: str) -> list[str]:
    months = sorted({month for month in all_months if month and month != "NaT"})
    if start_month:
        months = [month for month in months if month >= start_month]
    if end_month:
        months = [month for month in months if month <= end_month]
    return months


def fold_months(
    months: Sequence[str], train_months_min: int, validation_months: int
) -> list[tuple[list[str], list[str], str]]:
    folds: list[tuple[list[str], list[str], str]] = []
    min_train = max(train_months_min, 1)
    val_count = max(validation_months, 1)
    for test_index in range(min_train + val_count, len(months)):
        train = list(months[: test_index - val_count])
        validation = list(months[test_index - val_count : test_index])
        folds.append((train, validation, months[test_index]))
    return folds


def filter_by_months(frame: pd.DataFrame, months: Sequence[str]) -> pd.DataFrame:
    wanted = set(months)
    return frame[frame["month"].isin(wanted)].copy()


def apply_candidate_filter(frame: pd.DataFrame, candidate_only: str) -> pd.DataFrame:
    if candidate_only != "1":
        return frame.copy()
    return frame[frame["candidate_mask"].astype(float) >= 0.5].copy()


def apply_purge_before(
    frame: pd.DataFrame, boundary_source_index: int, purge_gap: int
) -> pd.DataFrame:
    cutoff = int(boundary_source_index) - max(int(purge_gap), 0)
    return frame[frame["source_index"].astype(int) < cutoff].copy()


def train_model(
    args: argparse.Namespace, train_frame: pd.DataFrame, features: Sequence[str]
) -> tuple[str, Any]:
    model_args = argparse.Namespace(
        booster=args.booster,
        task=args.task,
        n_estimators=max(args.n_estimators, 1),
        learning_rate=max(args.learning_rate, 1e-8),
        max_depth=max(args.max_depth, 1),
        num_leaves=max(args.num_leaves, 2),
    )
    booster_name, model = make_model(model_args)
    x_train = train_frame[list(features)].to_numpy(dtype=np.float32)
    y_train = train_frame[target_column(args)].to_numpy(dtype=np.float32)
    if args.task == "classifier":
        weights = class_weights(y_train.astype(int).tolist(), args.class_weight)
        sample_weight = sample_weights(y_train.astype(int).tolist(), weights)
        fit_kwargs = {"sample_weight": sample_weight} if sample_weight is not None else {}
        model.fit(x_train, y_train.astype(int), **fit_kwargs)
    else:
        model.fit(x_train, y_train)
    return booster_name, model


def score_value(summary: FixedBacktestSummary, account: dict[str, Any], metric: str) -> float:
    if metric == "profit_factor":
        return summary.profit_factor
    if metric == "final_balance":
        return float(account["final_balance"])
    if metric == "drawdown_adjusted":
        return summary.total_pnl - summary.max_drawdown
    return summary.total_pnl


def evaluate_threshold(
    frame: pd.DataFrame,
    scores: np.ndarray,
    threshold: float,
    args: argparse.Namespace,
) -> tuple[FixedBacktestSummary, Any, list[Any], float]:
    spec = MetaThresholdSpec(
        meta_threshold=threshold if args.task == "classifier" else 999.0,
        score_threshold=threshold if args.task == "regressor" else 0.0,
        source="walk_forward_validation",
    )
    summary, counters, trades = backtest_flat_meta(frame, scores, spec, task=args.task)
    account = account_summary(summary, args.initial_capital, args.units)
    score = score_value(summary, account, args.score_metric)
    return summary, counters, trades, score


def select_threshold(
    frame: pd.DataFrame,
    scores: np.ndarray,
    thresholds: Sequence[float],
    args: argparse.Namespace,
) -> tuple[float, float]:
    best_threshold = float(thresholds[0])
    best_score = -1e18
    for threshold in thresholds:
        summary, _counters, _trades, score = evaluate_threshold(
            frame, scores, float(threshold), args
        )
        if summary.trades < args.min_trades:
            continue
        if score > best_score:
            best_threshold = float(threshold)
            best_score = float(score)
    return best_threshold, best_score


def base_evaluation(frame: pd.DataFrame) -> tuple[FixedBacktestSummary, Any, list[Any]]:
    return backtest_flat_meta(
        frame,
        np.ones(len(frame), dtype=np.float64),
        MetaThresholdSpec(0.0, 0.0, "base"),
        task="classifier",
    )


def fold_report(
    fold_no: int,
    train_months_list: Sequence[str],
    validation_months_list: Sequence[str],
    test_month: str,
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    threshold: float,
    validation_score: float,
    base_summary: FixedBacktestSummary,
    meta_summary: FixedBacktestSummary,
    meta_counters: Any,
    args: argparse.Namespace,
) -> FoldReport:
    account = account_summary(meta_summary, args.initial_capital, args.units)
    return FoldReport(
        fold=fold_no,
        test_month=test_month,
        train_months=",".join(train_months_list),
        validation_months=",".join(validation_months_list),
        train_rows=len(train_frame),
        validation_rows=len(validation_frame),
        test_rows=len(test_frame),
        train_candidates=int(train_frame["candidate_mask"].astype(float).sum()),
        validation_candidates=int(validation_frame["candidate_mask"].astype(float).sum()),
        test_candidates=int(test_frame["candidate_mask"].astype(float).sum()),
        selected_threshold=threshold,
        selected_validation_score=validation_score,
        base_trades=base_summary.trades,
        base_total_pnl=base_summary.total_pnl,
        base_profit_factor=base_summary.profit_factor,
        base_max_drawdown=base_summary.max_drawdown,
        meta_trades=meta_summary.trades,
        meta_total_pnl=meta_summary.total_pnl,
        meta_profit_factor=meta_summary.profit_factor,
        meta_max_drawdown=meta_summary.max_drawdown,
        meta_win_rate=meta_summary.win_rate,
        meta_coverage=meta_summary.coverage,
        meta_final_balance=float(account["final_balance"]),
        meta_would_breach_zero=bool(account["would_breach_zero"]),
        skipped_by_meta=int(getattr(meta_counters, "skipped_by_meta", 0)),
        skipped_while_open=int(getattr(meta_counters, "skipped_while_open", 0)),
    )


def aggregate(
    rows: Sequence[FoldReport], meta_trades: Sequence[Any], args: argparse.Namespace
) -> AggregateReport:
    pnls = [float(trade.pnl) for trade in meta_trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    total = sum(pnls)
    account = {
        "final_balance": args.initial_capital + total * args.units,
        "net_profit": total * args.units,
        "return_percent": (
            (total * args.units / args.initial_capital) if args.initial_capital else 0.0
        ),
        "would_breach_zero": args.initial_capital - max_drawdown(pnls) * args.units <= 0,
    }
    best = max(rows, key=lambda row: row.meta_total_pnl, default=None)
    worst = min(rows, key=lambda row: row.meta_total_pnl, default=None)
    return AggregateReport(
        folds=len(rows),
        test_months=len(rows),
        positive_months=sum(1 for row in rows if row.meta_total_pnl > 0),
        negative_months=sum(1 for row in rows if row.meta_total_pnl < 0),
        base_total_pnl=sum(row.base_total_pnl for row in rows),
        meta_total_pnl=total,
        meta_gross_profit=gross_profit,
        meta_gross_loss=gross_loss,
        meta_profit_factor=(
            gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        meta_max_drawdown=max_drawdown(pnls),
        meta_trades=len(meta_trades),
        meta_avg_pnl=(total / len(meta_trades) if meta_trades else 0.0),
        meta_final_balance=float(account["final_balance"]),
        meta_return_percent=float(account["return_percent"]),
        meta_would_breach_zero=bool(account["would_breach_zero"]),
        best_month="" if best is None else best.test_month,
        worst_month="" if worst is None else worst.test_month,
    )


def write_csv(path: Path, rows: Sequence[FoldReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def html_report(rows: Sequence[FoldReport], aggregate_report: AggregateReport) -> str:
    body = "".join(
        "<tr>"
        f"<td>{row.test_month}</td>"
        f"<td>{row.train_rows:,}</td>"
        f"<td>{row.validation_rows:,}</td>"
        f"<td>{row.test_rows:,}</td>"
        f"<td>{row.selected_threshold:.3f}</td>"
        f"<td>{row.base_total_pnl:+.2f}</td>"
        f"<td>{row.meta_total_pnl:+.2f}</td>"
        f"<td>{row.meta_profit_factor:.3f}</td>"
        f"<td>{row.meta_trades:,}</td>"
        f"<td>{row.meta_coverage:.2%}</td>"
        "</tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Hybrid walk-forward validation</title>
<style>
body {{ font-family: Arial, sans-serif; background:#020617; color:#e2e8f0; padding:24px; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:8px; text-align:left; }}
th {{ color:#bae6fd; }}
.card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:14px; margin-bottom:16px; }}
</style></head><body>
<h1>Hybrid walk-forward validation</h1>
<div class="card"><pre>{json.dumps(asdict(aggregate_report), indent=2)}</pre></div>
<table><thead><tr><th>test month</th><th>train rows</th><th>val rows</th><th>test rows</th><th>threshold</th><th>base pnl</th><th>meta pnl</th><th>meta PF</th><th>trades</th><th>coverage</th></tr></thead><tbody>{body}</tbody></table>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        rule("PHASE133 WALK-FORWARD VALIDATION")
        print(f"  flat        : {flat_path}")
        print(f"  booster     : {args.booster}")
        print(f"  task        : {args.task}")
        frame = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
        if target_column(args) not in frame.columns:
            raise RuntimeError(f"Missing target column: {target_column(args)}")
        frame = frame.copy()
        frame["month"] = month_labels(frame)
        months = selected_months(frame["month"].tolist(), args.start_month, args.end_month)
        folds = fold_months(months, args.train_months_min, args.validation_months)
        if not folds:
            raise RuntimeError(
                "No walk-forward folds. Lower --train-months-min/--validation-months or widen month range."
            )
        features = feature_columns(frame)
        thresholds = parse_thresholds(
            args.meta_thresholds if args.task == "classifier" else args.score_thresholds
        )
        rows: list[FoldReport] = []
        all_meta_trades: list[Any] = []

        for fold_no, (train_months_list, validation_months_list, test_month) in enumerate(
            folds, start=1
        ):
            train_raw = filter_by_months(frame, train_months_list)
            validation_raw = filter_by_months(frame, validation_months_list)
            test_frame = filter_by_months(frame, [test_month]).reset_index(drop=True)
            if validation_raw.empty or test_frame.empty:
                continue
            test_min_source = int(test_frame["source_index"].astype(int).min())
            validation_raw = apply_purge_before(
                validation_raw, test_min_source, args.purge_gap_bars
            )
            if validation_raw.empty:
                continue
            val_min_source = int(validation_raw["source_index"].astype(int).min())
            train_raw = apply_purge_before(train_raw, val_min_source, args.purge_gap_bars)
            train_frame = apply_candidate_filter(train_raw, args.candidate_only).reset_index(
                drop=True
            )
            validation_frame = validation_raw.reset_index(drop=True)
            if len(train_frame) < max(args.min_trades, 20):
                continue
            booster_name, model = train_model(args, train_frame, features)
            val_scores = positive_scores(
                model, validation_frame[features].to_numpy(dtype=np.float32), args.task
            )
            selected_threshold, validation_score = select_threshold(
                validation_frame, val_scores, thresholds, args
            )
            test_scores = positive_scores(
                model, test_frame[features].to_numpy(dtype=np.float32), args.task
            )
            base_summary, _base_counters, _base_trades = base_evaluation(test_frame)
            meta_summary, meta_counters, meta_trades, _score = evaluate_threshold(
                test_frame, test_scores, selected_threshold, args
            )
            all_meta_trades.extend(meta_trades)
            report = fold_report(
                fold_no,
                train_months_list,
                validation_months_list,
                test_month,
                train_frame,
                validation_frame,
                test_frame,
                selected_threshold,
                validation_score,
                base_summary,
                meta_summary,
                meta_counters,
                args,
            )
            rows.append(report)
            print(
                f"  fold {fold_no:<2} test={test_month} booster={booster_name} "
                f"th={selected_threshold:.3f} base={base_summary.total_pnl:+.2f} "
                f"meta={meta_summary.total_pnl:+.2f} trades={meta_summary.trades:,}"
            )

        if not rows:
            raise RuntimeError(
                "All walk-forward folds were skipped; not enough train/validation/test rows"
            )
        aggregate_report = aggregate(rows, all_meta_trades, args)
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        html_path = out_dir / "latest.html"
        write_csv(csv_path, rows)
        html_path.write_text(html_report(rows, aggregate_report), encoding="utf-8")
        payload = {
            "args": vars(args),
            "flat_path": str(flat_path),
            "features": features,
            "folds": [asdict(row) for row in rows],
            "aggregate": asdict(aggregate_report),
            "files": {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)},
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rule("DONE")
        print(f"  folds       : {aggregate_report.folds}")
        print(f"  base pnl    : {aggregate_report.base_total_pnl:+.2f}")
        print(f"  meta pnl    : {aggregate_report.meta_total_pnl:+.2f}")
        print(f"  meta PF     : {aggregate_report.meta_profit_factor:.3f}")
        print(f"  meta trades : {aggregate_report.meta_trades:,}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
