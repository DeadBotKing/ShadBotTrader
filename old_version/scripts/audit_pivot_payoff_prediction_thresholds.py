"""Phase156A: payoff-target prediction / threshold calibration audit.

Phase155A proved that the B4/B2 payoff-target models can be trained, but the
fixed diagnostic gate under-selected trades. This phase does not retrain. It
loads existing payoff Option B models, archives validation/test predictions,
selects a threshold policy on validation only, then confirms that exact policy on
test.

Research-only. No production/paper/live approval.
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

from backtest_pivot_pattern_sequence_wavenet import (  # noqa: E402
    eval_tensor_indices,
    load_meta,
    load_model,
    load_record,
    make_predict_sequence,
    resolve_model_files,
    run_backtest,
)
from train_pivot_pattern_image_cnn import selected_indices  # noqa: E402
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow, selected_action  # noqa: E402

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_payoff_prediction_thresholds")
DEFAULT_CANDIDATES = "B4,B2"


@dataclass(frozen=True)
class CalibrationCandidate:
    candidate_id: str
    model_id: str
    tensor_name: str


@dataclass(frozen=True)
class ProbabilitySummary:
    candidate_id: str
    split: str
    rows: int
    sell_mean: float
    sell_p90: float
    sell_p95: float
    sell_p99: float
    hold_mean: float
    hold_p10: float
    hold_p50: float
    hold_p90: float
    buy_mean: float
    buy_p90: float
    buy_p95: float
    buy_p99: float
    buy_margin_p95: float
    sell_margin_p95: float
    buy_r_mean: float
    buy_r_p90: float
    sell_r_mean: float
    sell_r_p90: float


@dataclass(frozen=True)
class ThresholdGridRow:
    candidate_id: str
    split: str
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    min_buy_r: float
    min_sell_r: float
    evaluated_samples: int
    model_selected_count: int
    model_selected_rate: float
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    win_rate: float
    total_cash_pnl: float
    buy_cash_pnl: float
    sell_cash_pnl: float
    final_balance: float
    profit_factor: float
    max_drawdown_cash: float
    skipped_by_model: int
    skipped_while_open: int
    validation_score: float
    pass_gate: int


@dataclass(frozen=True)
class CandidateSelectionRow:
    candidate_id: str
    model_id: str
    selected_buy_threshold: float
    selected_sell_threshold: float
    selected_min_margin: float
    selected_min_buy_r: float
    selected_min_sell_r: float
    validation_trades: int
    validation_final_balance: float
    validation_profit_factor: float
    validation_total_cash_pnl: float
    validation_max_drawdown: float
    validation_score: float
    validation_pass_gate: int
    test_trades: int
    test_final_balance: float
    test_profit_factor: float
    test_total_cash_pnl: float
    test_max_drawdown: float
    test_pass_gate: int
    transfer_pass_gate: int


@dataclass(frozen=True)
class PayoffThresholdAuditReport:
    symbol: str
    timeframe: str
    candidates: list[dict[str, Any]]
    completed_candidates: int
    selected_candidate_id: str
    selected_model_id: str
    selected_validation_score: float
    selected_validation_profit_factor: float
    selected_test_profit_factor: float
    selected_test_final_balance: float
    selected_transfer_pass_gate: int
    probability_summaries: list[dict[str, Any]]
    selections: list[dict[str, Any]]
    validation_top_rows: list[dict[str, Any]]
    output_json: str
    output_html: str
    output_validation_grid_csv: str
    output_selection_csv: str
    output_probability_csv: str
    production_status: str


def safe_slug(text: str) -> str:
    cleaned = []
    for character in str(text).strip().lower():
        if character.isalnum():
            cleaned.append(character)
        elif character in {"-", "_", " ", "."}:
            cleaned.append("_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "candidate"


def parse_candidate_specs(text: str) -> list[CalibrationCandidate]:
    candidates: list[CalibrationCandidate] = []
    for raw in str(text or "").replace(";", ",").split(","):
        item = raw.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split(":")]
        if len(parts) == 1:
            candidate_id = parts[0].upper()
            slug = safe_slug(candidate_id)
            candidates.append(
                CalibrationCandidate(
                    candidate_id=candidate_id,
                    model_id=f"gold_pivot_payoff_option_b_{slug}_5m",
                    tensor_name=f"pivot_payoff_sequence_tensor_{slug}_latest",
                )
            )
        elif len(parts) == 3:
            candidates.append(
                CalibrationCandidate(
                    candidate_id=parts[0].upper(), model_id=parts[1], tensor_name=parts[2]
                )
            )
        else:
            raise RuntimeError(
                "Candidate format must be ID or ID:model_id:tensor_name; got " f"{item!r}"
            )
    if not candidates:
        raise RuntimeError("At least one calibration candidate is required")
    return candidates


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


def parse_r_grid(text: str, default: Sequence[float]) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return [float(value) for value in default]
    values: list[float] = []
    for token in raw.replace(";", ",").split(","):
        item = token.strip().lower()
        if not item:
            continue
        if item in {"none", "off", "any"}:
            values.append(-999.0)
        else:
            values.append(float(item))
    return values or [float(value) for value in default]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit validation-selected threshold grids for payoff Option B predictions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--buy-thresholds", default="0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50")
    parser.add_argument("--sell-thresholds", default="0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50")
    parser.add_argument("--margins", default="0,0.03,0.05,0.10")
    parser.add_argument("--min-buy-r-values", default="none,0,0.25")
    parser.add_argument("--min-sell-r-values", default="none,0,0.25")
    parser.add_argument("--max-policies", type=int, default=0, help="0 = all grid policies")
    parser.add_argument("--top-threshold", type=float, default=0.0)
    parser.add_argument("--bottom-threshold", type=float, default=0.0)
    parser.add_argument("--tp-multiplier", type=float, default=0.75)
    parser.add_argument("--sl-multiplier", type=float, default=0.75)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--score-metric", choices=("drawdown_adjusted", "total_pnl", "profit_factor", "final_balance"), default="drawdown_adjusted")
    parser.add_argument("--validation-min-trades", type=int, default=20)
    parser.add_argument("--validation-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--validation-min-final-balance", type=float, default=100.0)
    parser.add_argument("--test-min-trades", type=int, default=20)
    parser.add_argument("--test-min-profit-factor", type=float, default=1.05)
    parser.add_argument("--test-min-final-balance", type=float, default=100.0)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase156A payoff prediction threshold calibration audit")
    return parser.parse_args(argv)


def candidate_paths(args: argparse.Namespace, candidate: CalibrationCandidate) -> tuple[Path, Path, Path]:
    root = Path(args.storage_root) / "processed" / args.symbol / args.timeframe.upper()
    tensor = root / f"{candidate.tensor_name}.npy"
    meta = root / f"{candidate.tensor_name}_meta.npz"
    flat = root / f"{candidate.tensor_name.replace('sequence_tensor', 'sequence_flat')}.parquet"
    return tensor, meta, flat


def model_args(args: argparse.Namespace, candidate: CalibrationCandidate) -> argparse.Namespace:
    return argparse.Namespace(
        storage_root=args.storage_root,
        model_id=candidate.model_id,
        model_version=int(args.model_version),
        model_path="",
        record_path="",
    )


def quantile(values: np.ndarray, q: float) -> float:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if len(array) == 0:
        return 0.0
    return float(np.quantile(array, q))


def probability_summary(candidate_id: str, split: str, predictions: Mapping[str, np.ndarray]) -> ProbabilitySummary:
    action = np.asarray(predictions["action"], dtype=np.float32)
    sell = action[:, 0]
    hold = action[:, 1]
    buy = action[:, 2]
    buy_margin = buy - np.maximum(sell, hold)
    sell_margin = sell - np.maximum(buy, hold)
    buy_r = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
    sell_r = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
    return ProbabilitySummary(
        candidate_id=candidate_id,
        split=split,
        rows=int(len(action)),
        sell_mean=float(np.mean(sell)) if len(sell) else 0.0,
        sell_p90=quantile(sell, 0.90),
        sell_p95=quantile(sell, 0.95),
        sell_p99=quantile(sell, 0.99),
        hold_mean=float(np.mean(hold)) if len(hold) else 0.0,
        hold_p10=quantile(hold, 0.10),
        hold_p50=quantile(hold, 0.50),
        hold_p90=quantile(hold, 0.90),
        buy_mean=float(np.mean(buy)) if len(buy) else 0.0,
        buy_p90=quantile(buy, 0.90),
        buy_p95=quantile(buy, 0.95),
        buy_p99=quantile(buy, 0.99),
        buy_margin_p95=quantile(buy_margin, 0.95),
        sell_margin_p95=quantile(sell_margin, 0.95),
        buy_r_mean=float(np.mean(buy_r)) if len(buy_r) else 0.0,
        buy_r_p90=quantile(buy_r, 0.90),
        sell_r_mean=float(np.mean(sell_r)) if len(sell_r) else 0.0,
        sell_r_p90=quantile(sell_r, 0.90),
    )


def selected_count(predictions: Mapping[str, np.ndarray], args: argparse.Namespace) -> int:
    action = selected_action(
        np.asarray(predictions["action"], dtype=np.float32),
        float(args.buy_threshold),
        float(args.sell_threshold),
        float(args.min_margin),
    )
    buy_r = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
    sell_r = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
    mask = ((action == 2) & (buy_r >= float(args.min_buy_r))) | (
        (action == 0) & (sell_r >= float(args.min_sell_r))
    )
    return int(mask.sum())


def validation_score(row: ThresholdGridRow, metric: str) -> float:
    if metric == "total_pnl":
        return float(row.total_cash_pnl)
    if metric == "profit_factor":
        return float(row.profit_factor)
    if metric == "final_balance":
        return float(row.final_balance)
    return float(row.total_cash_pnl) - 0.25 * float(row.max_drawdown_cash)


def pnl_row(
    candidate_id: str,
    split: str,
    predictions: Mapping[str, np.ndarray],
    eval_rows: np.ndarray,
    sample_positions: np.ndarray,
    flat: pd.DataFrame,
    record: Mapping[str, Any],
    base_args: argparse.Namespace,
    buy_threshold: float,
    sell_threshold: float,
    min_margin: float,
    min_buy_r: float,
    min_sell_r: float,
    pass_min_trades: int,
    pass_min_pf: float,
    pass_min_final: float,
) -> ThresholdGridRow:
    run_args = argparse.Namespace(**vars(base_args))
    run_args.buy_threshold = float(buy_threshold)
    run_args.sell_threshold = float(sell_threshold)
    run_args.min_margin = float(min_margin)
    run_args.min_buy_r = float(min_buy_r)
    run_args.min_sell_r = float(min_sell_r)
    trades, _, skips = run_backtest(flat, eval_rows, sample_positions, predictions, run_args, record)
    pnls = [float(trade.cash_pnl) for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    final_balance = float(base_args.initial_capital) + sum(pnls)
    balances = [float(base_args.initial_capital), *[float(trade.balance) for trade in trades]]
    peak = balances[0] if balances else float(base_args.initial_capital)
    max_dd = 0.0
    for balance in balances:
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
    selected = selected_count(predictions, run_args)
    row = ThresholdGridRow(
        candidate_id=candidate_id,
        split=split,
        buy_threshold=float(buy_threshold),
        sell_threshold=float(sell_threshold),
        min_margin=float(min_margin),
        min_buy_r=float(min_buy_r),
        min_sell_r=float(min_sell_r),
        evaluated_samples=int(len(eval_rows)),
        model_selected_count=selected,
        model_selected_rate=float(selected / len(eval_rows)) if len(eval_rows) else 0.0,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=sum(1 for value in pnls if value > 0),
        losses=sum(1 for value in pnls if value < 0),
        win_rate=float(sum(1 for value in pnls if value > 0) / len(trades)) if trades else 0.0,
        total_cash_pnl=sum(pnls),
        buy_cash_pnl=sum(trade.cash_pnl for trade in trades if trade.side == "BUY"),
        sell_cash_pnl=sum(trade.cash_pnl for trade in trades if trade.side == "SELL"),
        final_balance=final_balance,
        profit_factor=gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        max_drawdown_cash=float(max_dd),
        skipped_by_model=int(skips.get("skipped_by_model", 0)),
        skipped_while_open=int(skips.get("skipped_while_open", 0)),
        validation_score=0.0,
        pass_gate=0,
    )
    score = validation_score(row, str(base_args.score_metric))
    return ThresholdGridRow(
        **{**asdict(row), "validation_score": score, "pass_gate": int(row.trades >= pass_min_trades and row.profit_factor >= pass_min_pf and row.final_balance >= pass_min_final)}
    )


def threshold_grid(args: argparse.Namespace) -> list[tuple[float, float, float, float, float]]:
    buy_values = parse_float_grid(args.buy_thresholds, (0.34,))
    sell_values = parse_float_grid(args.sell_thresholds, (0.34,))
    margins = parse_float_grid(args.margins, (0.0,))
    min_buy_values = parse_r_grid(args.min_buy_r_values, (-999.0,))
    min_sell_values = parse_r_grid(args.min_sell_r_values, (-999.0,))
    policies = [
        (buy, sell, margin, min_buy_r, min_sell_r)
        for buy in buy_values
        for sell in sell_values
        for margin in margins
        for min_buy_r in min_buy_values
        for min_sell_r in min_sell_values
    ]
    if int(args.max_policies) > 0:
        return policies[: int(args.max_policies)]
    return policies


def predict_split(
    tf: Any,
    model: Any,
    x_all: np.ndarray,
    rows: np.ndarray,
    record: Mapping[str, Any],
    meta: Mapping[str, Any],
    option_b: bool,
    batch_size: int,
) -> Mapping[str, np.ndarray]:
    sequence = make_predict_sequence(tf, x_all, rows, record, max(int(batch_size), 1), meta, option_b)
    return prediction_dict(model.predict(sequence, verbose=0))


def is_option_b_record(record: Mapping[str, Any]) -> bool:
    model_id = str(record.get("model_id", "")).lower()
    role = str(record.get("role", "")).lower()
    input_shapes = record.get("keras_input_shapes", {})
    return (
        "option_b" in model_id
        or "option_b" in role
        or (isinstance(input_shapes, Mapping) and "source_5m_input" in input_shapes)
    )


def calibrate_candidate(
    args: argparse.Namespace, candidate: CalibrationCandidate
) -> tuple[CandidateSelectionRow, list[ThresholdGridRow], list[ProbabilitySummary]]:
    tensor_path, meta_path, flat_path = candidate_paths(args, candidate)
    model_path, record_path, _ = resolve_model_files(model_args(args, candidate))
    record = load_record(record_path)
    tf = require_tensorflow()
    x_all = np.load(tensor_path, mmap_mode="r")
    meta = load_meta(meta_path)
    model = load_model(model_path, record, meta, tuple(int(value) for value in x_all.shape[1:]))
    flat = pd.read_parquet(flat_path).reset_index(drop=True)
    sample_positions_all = np.asarray(meta["sample_indices"], dtype=np.int64)
    selected_rows = selected_indices(int(x_all.shape[0]), int(args.max_samples))
    validation_rows, _ = eval_tensor_indices(selected_rows, argparse.Namespace(**{**vars(args), "eval_split": "validation", "eval_frac": 0.15, "max_windows": 0}))
    test_rows, _ = eval_tensor_indices(selected_rows, argparse.Namespace(**{**vars(args), "eval_split": "test", "eval_frac": 0.15, "max_windows": 0}))
    option_b = is_option_b_record(record)
    validation_pred = predict_split(tf, model, x_all, validation_rows, record, meta, option_b, int(args.batch_size))
    test_pred = predict_split(tf, model, x_all, test_rows, record, meta, option_b, int(args.batch_size))
    probability_rows = [
        probability_summary(candidate.candidate_id, "validation", validation_pred),
        probability_summary(candidate.candidate_id, "test", test_pred),
    ]
    validation_positions = sample_positions_all[validation_rows]
    test_positions = sample_positions_all[test_rows]
    grid_rows: list[ThresholdGridRow] = []
    for buy_threshold, sell_threshold, min_margin, min_buy_r, min_sell_r in threshold_grid(args):
        grid_rows.append(
            pnl_row(
                candidate.candidate_id,
                "validation",
                validation_pred,
                validation_rows,
                validation_positions,
                flat,
                record,
                args,
                buy_threshold,
                sell_threshold,
                min_margin,
                min_buy_r,
                min_sell_r,
                int(args.validation_min_trades),
                float(args.validation_min_profit_factor),
                float(args.validation_min_final_balance),
            )
        )
    ranked = sorted(
        grid_rows,
        key=lambda row: (row.pass_gate, row.validation_score, row.profit_factor, row.trades),
        reverse=True,
    )
    selected = ranked[0]
    test_row = pnl_row(
        candidate.candidate_id,
        "test",
        test_pred,
        test_rows,
        test_positions,
        flat,
        record,
        args,
        selected.buy_threshold,
        selected.sell_threshold,
        selected.min_margin,
        selected.min_buy_r,
        selected.min_sell_r,
        int(args.test_min_trades),
        float(args.test_min_profit_factor),
        float(args.test_min_final_balance),
    )
    selection = CandidateSelectionRow(
        candidate_id=candidate.candidate_id,
        model_id=candidate.model_id,
        selected_buy_threshold=float(selected.buy_threshold),
        selected_sell_threshold=float(selected.sell_threshold),
        selected_min_margin=float(selected.min_margin),
        selected_min_buy_r=float(selected.min_buy_r),
        selected_min_sell_r=float(selected.min_sell_r),
        validation_trades=int(selected.trades),
        validation_final_balance=float(selected.final_balance),
        validation_profit_factor=float(selected.profit_factor),
        validation_total_cash_pnl=float(selected.total_cash_pnl),
        validation_max_drawdown=float(selected.max_drawdown_cash),
        validation_score=float(selected.validation_score),
        validation_pass_gate=int(selected.pass_gate),
        test_trades=int(test_row.trades),
        test_final_balance=float(test_row.final_balance),
        test_profit_factor=float(test_row.profit_factor),
        test_total_cash_pnl=float(test_row.total_cash_pnl),
        test_max_drawdown=float(test_row.max_drawdown_cash),
        test_pass_gate=int(test_row.pass_gate),
        transfer_pass_gate=int(selected.pass_gate and test_row.pass_gate),
    )
    return selection, ranked, probability_rows


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def render_html(title: str, report: PayoffThresholdAuditReport) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(str(row['candidate_id']))}</td>"
        f"<td>{html.escape(str(row['model_id']))}</td>"
        f"<td>{float(row['selected_buy_threshold']):.2f}</td>"
        f"<td>{float(row['selected_sell_threshold']):.2f}</td>"
        f"<td>{float(row['selected_min_margin']):.2f}</td>"
        f"<td>{int(row['validation_trades'])}</td>"
        f"<td>{float(row['validation_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_profit_factor']):.3f}</td>"
        f"<td>{float(row['test_final_balance']):.3f}</td>"
        f"<td>{int(row['transfer_pass_gate'])}</td></tr>"
        for row in report.selections
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1380px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; font-size:13px; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase156A validation-selected threshold calibration. Research only.</p><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Selections</h2><table><thead><tr><th>ID</th><th>Model</th><th>Buy th</th><th>Sell th</th><th>Margin</th><th>Val trades</th><th>Val PF</th><th>Test PF</th><th>Test final</th><th>Transfer</th></tr></thead><tbody>{rows}</tbody></table></section>
<section class="card"><h2>Full JSON</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        print("\n" + "=" * 74)
        print("  PHASE156A PAYOFF PREDICTION THRESHOLD CALIBRATION AUDIT")
        print("=" * 74)
        candidates = parse_candidate_specs(args.candidates)
        selections: list[CandidateSelectionRow] = []
        all_grid: list[ThresholdGridRow] = []
        all_probabilities: list[ProbabilitySummary] = []
        for candidate in candidates:
            print(f"  [candidate] {candidate.candidate_id} model={candidate.model_id}", flush=True)
            selection, grid_rows, probability_rows = calibrate_candidate(args, candidate)
            selections.append(selection)
            all_grid.extend(grid_rows)
            all_probabilities.extend(probability_rows)
        selection_dicts = [asdict(row) for row in selections]
        probability_dicts = [asdict(row) for row in all_probabilities]
        grid_dicts = [asdict(row) for row in all_grid]
        ranked_selection = sorted(
            selections,
            key=lambda row: (
                row.transfer_pass_gate,
                row.validation_pass_gate,
                row.validation_profit_factor,
                row.test_profit_factor,
            ),
            reverse=True,
        )
        selected = ranked_selection[0] if ranked_selection else None
        validation_top = sorted(
            all_grid,
            key=lambda row: (row.pass_gate, row.validation_score, row.profit_factor, row.trades),
            reverse=True,
        )[:50]
        validation_csv = output_dir / "latest_validation_grid.csv"
        selection_csv = output_dir / "latest_selection.csv"
        probability_csv = output_dir / "latest_probability_summary.csv"
        write_csv(validation_csv, grid_dicts)
        write_csv(selection_csv, selection_dicts)
        write_csv(probability_csv, probability_dicts)
        report = PayoffThresholdAuditReport(
            symbol=str(args.symbol),
            timeframe=str(args.timeframe),
            candidates=[asdict(candidate) for candidate in candidates],
            completed_candidates=len(selections),
            selected_candidate_id=selected.candidate_id if selected else "",
            selected_model_id=selected.model_id if selected else "",
            selected_validation_score=float(selected.validation_score) if selected else 0.0,
            selected_validation_profit_factor=float(selected.validation_profit_factor) if selected else 0.0,
            selected_test_profit_factor=float(selected.test_profit_factor) if selected else 0.0,
            selected_test_final_balance=float(selected.test_final_balance) if selected else 0.0,
            selected_transfer_pass_gate=int(selected.transfer_pass_gate) if selected else 0,
            probability_summaries=probability_dicts,
            selections=selection_dicts,
            validation_top_rows=[asdict(row) for row in validation_top],
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_validation_grid_csv=str(validation_csv),
            output_selection_csv=str(selection_csv),
            output_probability_csv=str(probability_csv),
            production_status="BLOCKED — Phase156A research threshold audit only",
        )
        Path(report.output_json).write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        print("\n[DONE] Phase156A threshold audit complete")
        print(f"  selected candidate : {report.selected_candidate_id or 'none'}")
        print(f"  selected val PF    : {report.selected_validation_profit_factor:.4f}")
        print(f"  selected test PF   : {report.selected_test_profit_factor:.4f}")
        print(f"  transfer pass      : {report.selected_transfer_pass_gate}")
        print(f"  output             : {report.output_json}")
        print(f"  elapsed            : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:  # pragma: no cover - CLI safety net.
        print(f"\n[X] {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
