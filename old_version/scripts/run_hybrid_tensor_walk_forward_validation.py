"""Phase133B: walk-forward validation for tensor telemetry models.

This script is the tensor-model counterpart of Phase133A. It trains a fresh
WaveNet/TCN model for each test month using only earlier tensor windows,
selects thresholds only on the immediately preceding validation month(s), and
then evaluates the next unseen test month.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import gc
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
from backtest_hybrid_telemetry_wavenet import (
    TelemetryWaveNetThresholds,
    WaveNetBacktestCounters,
    default_flat_path,
    max_drawdown,
)
from backtest_hybrid_telemetry_wavenet import (
    backtest as backtest_tensor,
)
from report_hybrid_full_backtest import FixedBacktestSummary, account_summary
from train_hybrid_telemetry_wavenet import (
    MONITOR_CHOICES,
    TASKS,
    build_wavenet_model,
    compute_metrics,
    default_tensor_path,
    load_tensor,
    monitor_mode,
    monitor_name,
    prediction_arrays,
    require_tensorflow,
    sample_weight_payload,
    target_payload,
)

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_tensor_walk_forward_validation")
MODEL_FAMILIES = ("wavenet",)
DECISION_MODES = ("meta", "score", "both")
SCORE_METRICS = ("total_pnl", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class ThresholdChoice:
    decision_mode: str
    meta_threshold: float
    score_threshold: float
    validation_score: float
    validation_trades: int
    validation_profit_factor: float
    validation_max_drawdown: float
    validation_status: str


@dataclass(frozen=True)
class TensorFoldReport:
    fold: int
    test_month: str
    train_months: str
    validation_months: str
    train_samples: int
    validation_samples: int
    test_samples: int
    train_candidates: int
    train_selected_samples: int
    validation_candidates: int
    test_candidates: int
    selected_decision_mode: str
    selected_meta_threshold: float
    selected_score_threshold: float
    selected_validation_score: float
    selected_validation_trades: int
    selected_validation_profit_factor: float
    selected_validation_max_drawdown: float
    selected_validation_status: str
    no_trade_selected: int
    base_trades: int
    base_total_pnl: float
    base_profit_factor: float
    base_max_drawdown: float
    tensor_trades: int
    tensor_total_pnl: float
    tensor_profit_factor: float
    tensor_max_drawdown: float
    tensor_win_rate: float
    tensor_coverage: float
    tensor_final_balance: float
    tensor_would_breach_zero: bool
    skipped_by_tensor: int
    skipped_while_open: int
    val_meta_ap: float
    test_meta_ap: float
    val_score_mae: float
    test_score_mae: float
    val_score_selected_target_mean: float
    test_score_selected_target_mean: float
    val_score_collapse: float
    test_score_collapse: float


@dataclass(frozen=True)
class AggregateReport:
    folds: int
    test_months: int
    positive_months: int
    negative_months: int
    no_trade_months: int
    base_total_pnl: float
    tensor_total_pnl: float
    tensor_gross_profit: float
    tensor_gross_loss: float
    tensor_profit_factor: float
    tensor_max_drawdown: float
    tensor_trades: int
    tensor_avg_pnl: float
    tensor_final_balance: float
    tensor_return_percent: float
    tensor_would_breach_zero: bool
    best_month: str
    worst_month: str


def normalize_threshold_argv(argv: list[str] | None) -> list[str]:
    """Allow comma-separated threshold values that begin with a negative number."""

    raw = list(sys.argv[1:] if argv is None else argv)
    output: list[str] = []
    index = 0
    threshold_options = {"--meta-thresholds", "--score-thresholds"}
    while index < len(raw):
        token = raw[index]
        if (
            token in threshold_options
            and index + 1 < len(raw)
            and not raw[index + 1].startswith("--")
        ):
            output.append(f"{token}={raw[index + 1]}")
            index += 2
            continue
        output.append(token)
        index += 1
    return output


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase133B walk-forward validation for tensor telemetry models.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-family", choices=MODEL_FAMILIES, default="wavenet")
    parser.add_argument("--model-id", default="gold_hybrid_tensor_walkforward_wavenet_5m")
    parser.add_argument("--task", choices=TASKS, default="multihead")
    parser.add_argument("--candidate-only", choices=("0", "1"), default="1")
    parser.add_argument("--start-month", default="")
    parser.add_argument("--end-month", default="")
    parser.add_argument("--train-months-min", type=int, default=3)
    parser.add_argument("--validation-months", type=int, default=1)
    parser.add_argument("--purge-gap-bars", type=int, default=336)
    parser.add_argument("--decision-modes", default="score,both")
    parser.add_argument("--meta-thresholds", default="0.55,0.60,0.65,0.70")
    parser.add_argument("--score-thresholds", default="0,0.05,0.10,0.20")
    parser.add_argument("--default-meta-threshold", type=float, default=0.55)
    parser.add_argument("--default-score-threshold", type=float, default=0.0)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument(
        "--allow-no-trade",
        choices=("0", "1"),
        default="0",
        help="When enabled, choose NO_TRADE if validation gates reject every trading threshold.",
    )
    parser.add_argument("--min-validation-score", type=float, default=-1e18)
    parser.add_argument("--min-validation-profit-factor", type=float, default=0.0)
    parser.add_argument(
        "--max-validation-drawdown",
        type=float,
        default=-1.0,
        help="Negative disables the validation drawdown gate.",
    )
    parser.add_argument("--min-train-samples", type=int, default=200)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--max-folds", type=int, default=0, help="0 = all eligible folds")
    parser.add_argument(
        "--max-train-samples", type=int, default=0, help="0 = all selected training samples"
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--filters", type=int, default=48)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--n-layers", type=int, default=5)
    parser.add_argument("--n-blocks", type=int, default=2)
    parser.add_argument("--dense-units", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--score-loss-weight", type=float, default=0.50)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--monitor-metric", choices=MONITOR_CHOICES, default="auto")
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--verbose", type=int, choices=(0, 1, 2), default=2)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--units", type=float, default=0.1)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parsed = parser.parse_args(normalize_threshold_argv(argv))
    parsed.meta_threshold = float(parsed.default_meta_threshold)
    parsed.score_threshold = float(parsed.default_score_threshold)
    return parsed


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def parse_modes(text: str, task: str) -> list[str]:
    modes = [item.strip().lower() for item in text.split(",") if item.strip()]
    selected = [mode for mode in modes if mode in DECISION_MODES]
    if not selected:
        selected = ["score" if task in ("regressor", "multihead") else "meta"]
    if task == "classifier":
        selected = [mode for mode in selected if mode in ("meta", "both")] or ["meta"]
    if task == "regressor":
        selected = [mode for mode in selected if mode in ("score", "both")] or ["score"]
    return selected


def parse_float_options(text: str, default_value: float, allow_record: bool = True) -> list[float]:
    values: list[float] = []
    for token in (item.strip().lower() for item in text.split(",")):
        if not token:
            continue
        if allow_record and token in ("record", "saved", "auto", "default"):
            value = default_value
        else:
            value = float(token)
        if value not in values:
            values.append(value)
    return values or [default_value]


def threshold_grid(
    modes: Sequence[str], meta_thresholds: Sequence[float], score_thresholds: Sequence[float]
) -> list[TelemetryWaveNetThresholds]:
    grid: list[TelemetryWaveNetThresholds] = []
    seen: set[tuple[str, float, float]] = set()
    for mode in modes:
        metas = list(meta_thresholds) if mode in ("meta", "both") else [float(meta_thresholds[0])]
        scores = (
            list(score_thresholds) if mode in ("score", "both") else [float(score_thresholds[0])]
        )
        for meta_threshold in metas:
            for score_threshold in scores:
                key = (mode, float(meta_threshold), float(score_threshold))
                if key in seen:
                    continue
                seen.add(key)
                grid.append(
                    TelemetryWaveNetThresholds(
                        meta_threshold=float(meta_threshold),
                        score_threshold=float(score_threshold),
                        decision_mode=mode,
                        source="walk_forward_validation",
                    )
                )
    return grid


def month_labels_from_tensor(data: Mapping[str, Any]) -> pd.Series:
    raw = data.get("timestamp")
    if raw is None:
        raise RuntimeError("Tensor archive is missing timestamp array; cannot build monthly folds")
    timestamps = pd.to_datetime(np.asarray(raw).astype(str), utc=True, errors="coerce")
    return pd.Series(timestamps).dt.strftime("%Y-%m")


def tensor_index_frame(data: Mapping[str, Any]) -> pd.DataFrame:
    source_indices = np.asarray(data["source_index"], dtype=np.int64)
    months = month_labels_from_tensor(data)
    return pd.DataFrame(
        {
            "tensor_index": np.arange(len(source_indices), dtype=np.int64),
            "source_index": source_indices,
            "month": months.to_numpy(dtype=object),
            "candidate_mask": np.asarray(
                data.get("candidate_mask", np.ones(len(source_indices))), dtype=np.float32
            ),
        }
    )


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


def filter_by_months(index_frame: pd.DataFrame, months: Sequence[str]) -> pd.DataFrame:
    return index_frame[index_frame["month"].isin(set(months))].copy()


def apply_purge_before(
    frame: pd.DataFrame, boundary_source_index: int, purge_gap: int
) -> pd.DataFrame:
    cutoff = int(boundary_source_index) - max(int(purge_gap), 0)
    return frame[frame["source_index"].astype(int) < cutoff].copy()


def candidate_tensor_indices(frame: pd.DataFrame, candidate_only: str) -> np.ndarray:
    if candidate_only != "1":
        return frame["tensor_index"].to_numpy(dtype=np.int64)
    selected = frame[frame["candidate_mask"].astype(float) >= 0.5]
    return selected["tensor_index"].to_numpy(dtype=np.int64)


def cap_training_indices(indices: np.ndarray, max_train_samples: int) -> np.ndarray:
    limit = max(int(max_train_samples), 0)
    if limit <= 0 or len(indices) <= limit:
        return indices
    step = max(1, len(indices) // limit)
    return indices[::step][:limit]


def scaler_from_train(x_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.mean(x_train.astype(np.float32), axis=(0, 1), keepdims=True)
    std = np.std(x_train.astype(np.float32), axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return mean.astype(np.float32), std.astype(np.float32)


def normalize_subset(x_values: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return np.nan_to_num(
        (x_values.astype(np.float32) - mean) / std,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )


def flat_lookup(flat_path: Path) -> dict[int, pd.Series]:
    flat = pd.read_parquet(flat_path).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return {int(row["source_index"]): row for _, row in flat.iterrows()}


def score_value(summary: FixedBacktestSummary, account: Mapping[str, Any], metric: str) -> float:
    if metric == "profit_factor":
        return summary.profit_factor
    if metric == "final_balance":
        return float(account["final_balance"])
    if metric == "drawdown_adjusted":
        return summary.total_pnl - summary.max_drawdown
    return summary.total_pnl


def evaluate_threshold(
    source_indices: np.ndarray,
    candidate_mask: np.ndarray,
    win_scores: np.ndarray,
    score_scores: np.ndarray,
    flat_by_source: Mapping[int, pd.Series],
    thresholds: TelemetryWaveNetThresholds,
    args: argparse.Namespace,
) -> tuple[FixedBacktestSummary, Any, list[Any], float]:
    summary, counters, trades = backtest_tensor(
        source_indices,
        candidate_mask,
        win_scores,
        score_scores,
        flat_by_source,
        thresholds,
    )
    account = account_summary(summary, args.initial_capital, args.units)
    return summary, counters, trades, score_value(summary, account, args.score_metric)


def no_trade_choice(
    status: str,
    reference: tuple[TelemetryWaveNetThresholds, FixedBacktestSummary, float] | None = None,
) -> ThresholdChoice:
    if reference is None:
        return ThresholdChoice(
            decision_mode="no_trade",
            meta_threshold=0.0,
            score_threshold=0.0,
            validation_score=0.0,
            validation_trades=0,
            validation_profit_factor=0.0,
            validation_max_drawdown=0.0,
            validation_status=status,
        )
    thresholds, summary, score = reference
    return ThresholdChoice(
        decision_mode="no_trade",
        meta_threshold=float(thresholds.meta_threshold),
        score_threshold=float(thresholds.score_threshold),
        validation_score=float(score),
        validation_trades=int(summary.trades),
        validation_profit_factor=float(summary.profit_factor),
        validation_max_drawdown=float(summary.max_drawdown),
        validation_status=status,
    )


def validation_gate_status(
    summary: FixedBacktestSummary, score: float, args: argparse.Namespace
) -> str:
    if args.allow_no_trade != "1":
        return "ok"
    if summary.trades < max(args.min_trades, 0):
        return "no_trade:validation_trades_below_min"
    if float(score) < float(args.min_validation_score):
        return "no_trade:validation_score_below_min"
    if float(summary.profit_factor) < float(args.min_validation_profit_factor):
        return "no_trade:validation_profit_factor_below_min"
    max_drawdown_gate = float(args.max_validation_drawdown)
    if max_drawdown_gate >= 0 and float(summary.max_drawdown) > max_drawdown_gate:
        return "no_trade:validation_drawdown_above_max"
    return "ok"


def select_threshold(
    source_indices: np.ndarray,
    candidate_mask: np.ndarray,
    win_scores: np.ndarray,
    score_scores: np.ndarray,
    flat_by_source: Mapping[int, pd.Series],
    grid: Sequence[TelemetryWaveNetThresholds],
    args: argparse.Namespace,
) -> ThresholdChoice:
    best: tuple[TelemetryWaveNetThresholds, FixedBacktestSummary, float] | None = None
    best_any: tuple[TelemetryWaveNetThresholds, FixedBacktestSummary, float] | None = None
    for thresholds in grid:
        summary, _counters, _trades, score = evaluate_threshold(
            source_indices,
            candidate_mask,
            win_scores,
            score_scores,
            flat_by_source,
            thresholds,
            args,
        )
        current = (thresholds, summary, float(score))
        if best_any is None or score > best_any[2]:
            best_any = current
        if summary.trades < max(args.min_trades, 0):
            continue
        if best is None or score > best[2]:
            best = current
    selected = best or best_any
    if selected is None:
        return no_trade_choice("no_thresholds")
    thresholds, summary, score = selected
    if best is None:
        status = "below_min_trades"
        if args.allow_no_trade == "1":
            return no_trade_choice("no_trade:validation_trades_below_min", selected)
    else:
        status = validation_gate_status(summary, score, args)
        if status != "ok":
            return no_trade_choice(status, selected)
    return ThresholdChoice(
        thresholds.decision_mode,
        thresholds.meta_threshold,
        thresholds.score_threshold,
        float(score),
        int(summary.trades),
        float(summary.profit_factor),
        float(summary.max_drawdown),
        status,
    )


def choice_to_thresholds(choice: ThresholdChoice) -> TelemetryWaveNetThresholds:
    return TelemetryWaveNetThresholds(
        meta_threshold=choice.meta_threshold,
        score_threshold=choice.score_threshold,
        decision_mode=choice.decision_mode,
        source="walk_forward_validation",
    )


def no_trade_summary(samples: int) -> FixedBacktestSummary:
    return FixedBacktestSummary(
        samples=int(samples),
        trades=0,
        buy_trades=0,
        sell_trades=0,
        wins=0,
        losses=0,
        timeouts=0,
        label_correct=0,
        false_positive=0,
        no_trade=int(samples),
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
        win_rate=0.0,
        label_precision=0.0,
        total_pnl=0.0,
        avg_pnl=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        profit_factor=0.0,
        max_drawdown=0.0,
        coverage=0.0,
    )


def no_trade_counters(samples: int) -> WaveNetBacktestCounters:
    return WaveNetBacktestCounters(
        skipped_no_candidate=0,
        skipped_by_wavenet=int(samples),
        skipped_while_open=0,
        missing_flat_row=0,
        missing_outcome=0,
    )


def base_evaluation(
    source_indices: np.ndarray,
    candidate_mask: np.ndarray,
    flat_by_source: Mapping[int, pd.Series],
) -> tuple[FixedBacktestSummary, Any, list[Any]]:
    ones = np.ones(len(source_indices), dtype=np.float64)
    summary, counters, trades = backtest_tensor(
        source_indices,
        candidate_mask,
        ones,
        ones,
        flat_by_source,
        TelemetryWaveNetThresholds(0.0, 0.0, "score", "base"),
    )
    return summary, counters, trades


def candidate_ml_indices(frame: pd.DataFrame) -> np.ndarray:
    return frame.loc[frame["candidate_mask"].astype(float) >= 0.5, "tensor_index"].to_numpy(
        dtype=np.int64
    )


def metric_subset(all_indices: np.ndarray, candidate_indices: np.ndarray) -> np.ndarray:
    if len(all_indices) == 0 or len(candidate_indices) == 0:
        return np.asarray([], dtype=np.int64)
    positions = {int(value): pos for pos, value in enumerate(all_indices.tolist())}
    return np.asarray(
        [positions[int(value)] for value in candidate_indices if int(value) in positions],
        dtype=np.int64,
    )


def train_and_predict_fold(
    data: Mapping[str, Any],
    train_indices: np.ndarray,
    validation_fit_indices: np.ndarray,
    validation_eval_indices: np.ndarray,
    test_eval_indices: np.ndarray,
    validation_metric_indices: np.ndarray,
    test_metric_indices: np.ndarray,
    args: argparse.Namespace,
    tf: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    x_train_raw = np.asarray(data["X"][train_indices], dtype=np.float32)
    mean, std = scaler_from_train(x_train_raw)
    x_train = normalize_subset(x_train_raw, mean, std)
    x_val_fit = normalize_subset(
        np.asarray(data["X"][validation_fit_indices], dtype=np.float32), mean, std
    )
    y_train = target_payload(data, train_indices, args.task)
    y_val = target_payload(data, validation_fit_indices, args.task)
    sample_weight = sample_weight_payload(y_train, args)
    model = build_wavenet_model(tf, (x_train.shape[1], x_train.shape[2]), args)
    callbacks: list[Any] = []
    monitor = monitor_name(args)
    if args.early_stopping_patience > 0:
        callbacks.append(
            tf.keras.callbacks.EarlyStopping(
                monitor=monitor,
                mode=monitor_mode(monitor),
                patience=args.early_stopping_patience,
                restore_best_weights=True,
            )
        )
    fit_kwargs: dict[str, Any] = {}
    if sample_weight is not None:
        fit_kwargs["sample_weight"] = sample_weight
    model.fit(
        x_train,
        y_train,
        validation_data=(x_val_fit, y_val),
        epochs=max(args.epochs, 1),
        batch_size=max(args.batch_size, 1),
        callbacks=callbacks,
        verbose=int(args.verbose),
        **fit_kwargs,
    )

    x_val_eval = normalize_subset(
        np.asarray(data["X"][validation_eval_indices], dtype=np.float32), mean, std
    )
    x_test_eval = normalize_subset(
        np.asarray(data["X"][test_eval_indices], dtype=np.float32), mean, std
    )
    val_win, val_score = prediction_arrays(model, x_val_eval, args.task)
    test_win, test_score = prediction_arrays(model, x_test_eval, args.task)
    if args.task == "regressor":
        val_win = np.ones_like(val_score, dtype=np.float64)
        test_win = np.ones_like(test_score, dtype=np.float64)

    metrics: dict[str, float] = {}
    val_metric_positions = metric_subset(validation_eval_indices, validation_metric_indices)
    test_metric_positions = metric_subset(test_eval_indices, test_metric_indices)
    try:
        metrics = compute_metrics(
            data,
            validation_metric_indices,
            test_metric_indices,
            val_win[val_metric_positions],
            val_score[val_metric_positions],
            test_win[test_metric_positions],
            test_score[test_metric_positions],
            args,
        )
    finally:
        del x_train_raw, x_train, x_val_fit, x_val_eval, x_test_eval
        gc.collect()
    return val_win, val_score, test_win, test_score, metrics


def fold_report(
    fold_no: int,
    train_months_list: Sequence[str],
    validation_months_list: Sequence[str],
    test_month: str,
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    choice: ThresholdChoice,
    base_summary: FixedBacktestSummary,
    tensor_summary: FixedBacktestSummary,
    tensor_counters: Any,
    metrics: Mapping[str, float],
    args: argparse.Namespace,
    train_selected_samples: int,
) -> TensorFoldReport:
    account = account_summary(tensor_summary, args.initial_capital, args.units)
    return TensorFoldReport(
        fold=fold_no,
        test_month=test_month,
        train_months=",".join(train_months_list),
        validation_months=",".join(validation_months_list),
        train_samples=len(train_frame),
        validation_samples=len(validation_frame),
        test_samples=len(test_frame),
        train_candidates=int(train_frame["candidate_mask"].astype(float).sum()),
        train_selected_samples=int(train_selected_samples),
        validation_candidates=int(validation_frame["candidate_mask"].astype(float).sum()),
        test_candidates=int(test_frame["candidate_mask"].astype(float).sum()),
        selected_decision_mode=choice.decision_mode,
        selected_meta_threshold=choice.meta_threshold,
        selected_score_threshold=choice.score_threshold,
        selected_validation_score=choice.validation_score,
        selected_validation_trades=choice.validation_trades,
        selected_validation_profit_factor=choice.validation_profit_factor,
        selected_validation_max_drawdown=choice.validation_max_drawdown,
        selected_validation_status=choice.validation_status,
        no_trade_selected=1 if choice.decision_mode == "no_trade" else 0,
        base_trades=base_summary.trades,
        base_total_pnl=base_summary.total_pnl,
        base_profit_factor=base_summary.profit_factor,
        base_max_drawdown=base_summary.max_drawdown,
        tensor_trades=tensor_summary.trades,
        tensor_total_pnl=tensor_summary.total_pnl,
        tensor_profit_factor=tensor_summary.profit_factor,
        tensor_max_drawdown=tensor_summary.max_drawdown,
        tensor_win_rate=tensor_summary.win_rate,
        tensor_coverage=tensor_summary.coverage,
        tensor_final_balance=float(account["final_balance"]),
        tensor_would_breach_zero=bool(account["would_breach_zero"]),
        skipped_by_tensor=int(getattr(tensor_counters, "skipped_by_wavenet", 0)),
        skipped_while_open=int(getattr(tensor_counters, "skipped_while_open", 0)),
        val_meta_ap=float(metrics.get("val_meta_ap", 0.0)),
        test_meta_ap=float(metrics.get("test_meta_ap", 0.0)),
        val_score_mae=float(metrics.get("val_score_mae", 0.0)),
        test_score_mae=float(metrics.get("test_score_mae", 0.0)),
        val_score_selected_target_mean=float(metrics.get("val_score_selected_target_mean", 0.0)),
        test_score_selected_target_mean=float(metrics.get("test_score_selected_target_mean", 0.0)),
        val_score_collapse=float(metrics.get("val_score_collapse", 0.0)),
        test_score_collapse=float(metrics.get("test_score_collapse", 0.0)),
    )


def aggregate(
    rows: Sequence[TensorFoldReport], tensor_trades: Sequence[Any], args: argparse.Namespace
) -> AggregateReport:
    pnls = [float(trade.pnl) for trade in tensor_trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    total = sum(pnls)
    drawdown = max_drawdown(pnls)
    final_balance = float(args.initial_capital) + total * float(args.units)
    best = max(rows, key=lambda row: row.tensor_total_pnl, default=None)
    worst = min(rows, key=lambda row: row.tensor_total_pnl, default=None)
    return AggregateReport(
        folds=len(rows),
        test_months=len(rows),
        positive_months=sum(1 for row in rows if row.tensor_total_pnl > 0),
        negative_months=sum(1 for row in rows if row.tensor_total_pnl < 0),
        no_trade_months=sum(1 for row in rows if row.no_trade_selected),
        base_total_pnl=sum(row.base_total_pnl for row in rows),
        tensor_total_pnl=total,
        tensor_gross_profit=gross_profit,
        tensor_gross_loss=gross_loss,
        tensor_profit_factor=(
            gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        tensor_max_drawdown=drawdown,
        tensor_trades=len(tensor_trades),
        tensor_avg_pnl=(total / len(tensor_trades) if tensor_trades else 0.0),
        tensor_final_balance=final_balance,
        tensor_return_percent=(
            (final_balance - float(args.initial_capital)) / float(args.initial_capital)
            if float(args.initial_capital)
            else 0.0
        ),
        tensor_would_breach_zero=float(args.initial_capital) - drawdown * float(args.units) <= 0,
        best_month="" if best is None else best.test_month,
        worst_month="" if worst is None else worst.test_month,
    )


def write_csv(path: Path, rows: Sequence[TensorFoldReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def html_report(rows: Sequence[TensorFoldReport], aggregate_report: AggregateReport) -> str:
    body = "".join(
        "<tr>"
        f"<td>{html.escape(row.test_month)}</td>"
        f"<td>{html.escape(row.selected_decision_mode)}</td>"
        f"<td>{row.selected_meta_threshold:.3f}</td>"
        f"<td>{row.selected_score_threshold:.3f}</td>"
        f"<td>{row.selected_validation_score:+.2f}</td>"
        f"<td>{row.selected_validation_profit_factor:.3f}</td>"
        f"<td>{row.selected_validation_max_drawdown:.2f}</td>"
        f"<td>{row.no_trade_selected}</td>"
        f"<td>{row.base_total_pnl:+.2f}</td>"
        f"<td>{row.tensor_total_pnl:+.2f}</td>"
        f"<td>{row.tensor_profit_factor:.3f}</td>"
        f"<td>{row.tensor_trades:,}</td>"
        f"<td>{row.tensor_max_drawdown:.2f}</td>"
        f"<td>{row.tensor_coverage:.2%}</td>"
        f"<td>{html.escape(row.selected_validation_status)}</td>"
        "</tr>"
        for row in rows
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Hybrid tensor walk-forward validation</title>
<style>
body {{ font-family: Arial, sans-serif; background:#020617; color:#e2e8f0; padding:24px; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:8px; text-align:left; }}
th {{ color:#bae6fd; }}
.card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:14px; margin-bottom:16px; }}
</style></head><body>
<h1>Phase133B — Tensor walk-forward validation</h1>
<div class="card"><pre>{html.escape(json.dumps(asdict(aggregate_report), indent=2))}</pre></div>
<table><thead><tr><th>test month</th><th>mode</th><th>meta th</th><th>score th</th><th>val score</th><th>val PF</th><th>val DD</th><th>no trade</th><th>base pnl</th><th>tensor pnl</th><th>tensor PF</th><th>trades</th><th>DD</th><th>coverage</th><th>val status</th></tr></thead><tbody>{body}</tbody></table>
</body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    storage_root = Path(args.storage_root)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(storage_root, args.symbol, args.timeframe)
    )
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("PHASE133B TENSOR WALK-FORWARD VALIDATION")
        print(f"  tensor      : {tensor_path}")
        print(f"  flat        : {flat_path}")
        print(f"  family      : {args.model_family}")
        print(f"  task        : {args.task}")
        data = load_tensor(tensor_path)
        index_frame = tensor_index_frame(data)
        months = selected_months(index_frame["month"].tolist(), args.start_month, args.end_month)
        folds = fold_months(months, args.train_months_min, args.validation_months)
        if args.max_folds > 0:
            folds = folds[: args.max_folds]
        if not folds:
            raise RuntimeError(
                "No tensor walk-forward folds. Lower --train-months-min/--validation-months or widen month range."
            )
        modes = parse_modes(args.decision_modes, args.task)
        meta_thresholds = parse_float_options(
            args.meta_thresholds, args.default_meta_threshold, allow_record=True
        )
        score_thresholds = parse_float_options(
            args.score_thresholds, args.default_score_threshold, allow_record=True
        )
        grid = threshold_grid(modes, meta_thresholds, score_thresholds)
        flat_by_source = flat_lookup(flat_path)
        tf = require_tensorflow()
        rows: list[TensorFoldReport] = []
        all_tensor_trades: list[Any] = []

        for fold_no, (train_months_list, validation_months_list, test_month) in enumerate(
            folds, start=1
        ):
            train_raw = filter_by_months(index_frame, train_months_list)
            validation_raw = filter_by_months(index_frame, validation_months_list)
            test_frame = filter_by_months(index_frame, [test_month]).reset_index(drop=True)
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
            train_frame = train_raw.reset_index(drop=True)
            validation_frame = validation_raw.reset_index(drop=True)
            train_indices = cap_training_indices(
                candidate_tensor_indices(train_frame, args.candidate_only), args.max_train_samples
            )
            validation_fit_indices = candidate_tensor_indices(validation_frame, args.candidate_only)
            validation_eval_indices = validation_frame["tensor_index"].to_numpy(dtype=np.int64)
            test_eval_indices = test_frame["tensor_index"].to_numpy(dtype=np.int64)
            validation_metric_indices = candidate_tensor_indices(validation_frame, "1")
            test_metric_indices = candidate_tensor_indices(test_frame, "1")
            if len(train_indices) < max(args.min_train_samples, 20):
                continue
            if len(validation_fit_indices) < max(args.min_trades, 1):
                continue
            print(
                f"  fold {fold_no:<2} test={test_month} "
                f"train={len(train_indices):,} val={len(validation_fit_indices):,} "
                f"test_rows={len(test_eval_indices):,}"
            )
            val_win, val_score, test_win, test_score, metrics = train_and_predict_fold(
                data,
                train_indices,
                validation_fit_indices,
                validation_eval_indices,
                test_eval_indices,
                validation_metric_indices,
                test_metric_indices,
                args,
                tf,
            )
            validation_source = validation_frame["source_index"].to_numpy(dtype=np.int64)
            validation_mask = validation_frame["candidate_mask"].to_numpy(dtype=np.float32)
            test_source = test_frame["source_index"].to_numpy(dtype=np.int64)
            test_mask = test_frame["candidate_mask"].to_numpy(dtype=np.float32)
            choice = select_threshold(
                validation_source,
                validation_mask,
                val_win,
                val_score,
                flat_by_source,
                grid,
                args,
            )
            base_summary, _base_counters, _base_trades = base_evaluation(
                test_source, test_mask, flat_by_source
            )
            if choice.decision_mode == "no_trade":
                tensor_summary = no_trade_summary(len(test_source))
                tensor_counters = no_trade_counters(len(test_source))
                tensor_trades = []
            else:
                tensor_summary, tensor_counters, tensor_trades, _score = evaluate_threshold(
                    test_source,
                    test_mask,
                    test_win,
                    test_score,
                    flat_by_source,
                    choice_to_thresholds(choice),
                    args,
                )
            all_tensor_trades.extend(tensor_trades)
            report = fold_report(
                fold_no,
                train_months_list,
                validation_months_list,
                test_month,
                train_frame,
                validation_frame,
                test_frame,
                choice,
                base_summary,
                tensor_summary,
                tensor_counters,
                metrics,
                args,
                len(train_indices),
            )
            rows.append(report)
            print(
                f"    selected={choice.decision_mode} meta={choice.meta_threshold:.3f} "
                f"score={choice.score_threshold:.3f} val={choice.validation_score:+.2f} "
                f"base={base_summary.total_pnl:+.2f} tensor={tensor_summary.total_pnl:+.2f} "
                f"trades={tensor_summary.trades:,}"
            )
            gc.collect()

        if not rows:
            raise RuntimeError(
                "All tensor walk-forward folds were skipped; not enough train/validation/test samples"
            )
        aggregate_report = aggregate(rows, all_tensor_trades, args)
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        html_path = out_dir / "latest.html"
        write_csv(csv_path, rows)
        html_path.write_text(html_report(rows, aggregate_report), encoding="utf-8")
        payload = {
            "args": vars(args),
            "tensor_path": str(tensor_path),
            "flat_path": str(flat_path),
            "folds": [asdict(row) for row in rows],
            "aggregate": asdict(aggregate_report),
            "files": {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)},
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        rule("DONE")
        print(f"  folds       : {aggregate_report.folds}")
        print(f"  base pnl    : {aggregate_report.base_total_pnl:+.2f}")
        print(f"  tensor pnl  : {aggregate_report.tensor_total_pnl:+.2f}")
        print(f"  tensor PF   : {aggregate_report.tensor_profit_factor:.3f}")
        print(f"  trades      : {aggregate_report.tensor_trades:,}")
        print(f"  report      : {json_path}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
