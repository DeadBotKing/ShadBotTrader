"""Phase146A: Backtest/PnL audit for Phase145A sequence WaveNet.

This is a research-only replay for the owner-requested Option A tensor:

    stored X: [samples, window_size, features]
    Keras batch: [batch, window_size, features]

It loads the trained Keras multi-head sequence WaveNet, predicts on a selected
chronological split, converts action probabilities into BUY/SELL candidates,
and simulates simple ATR-based TP/SL paths with spread/risk assumptions.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_pivot_pattern_image_cnn import selected_indices, split_indices
from train_pivot_pattern_recognition import ACTION_BUY, ACTION_SELL, trade_path
from train_pivot_pattern_sequence_wavenet import (
    build_sequence_wavenet_model,
    default_meta_path,
    default_tensor_path,
)
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow, selected_action

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_wavenet_backtest")


@dataclass(frozen=True)
class BacktestTrade:
    number: int
    timestamp: str
    side: str
    tensor_row: int
    sample_index: int
    row_id: int
    entry_row_id: int
    exit_row_id: int
    entry: float
    tp: float
    sl: float
    exit_price: float
    points_pnl: float
    cash_pnl: float
    balance: float
    outcome: str
    action_sell_prob: float
    action_hold_prob: float
    action_buy_prob: float
    top_prob: float
    bottom_prob: float
    buy_r_pred: float
    sell_r_pred: float


@dataclass(frozen=True)
class BacktestReport:
    model_id: str
    model_version: int
    model_path: str
    record_path: str
    tensor_path: str
    meta_path: str
    flat_path: str
    tensor_shape: list[int]
    eval_split: str
    selected_samples: int
    evaluated_samples: int
    evaluated_first_timestamp: str
    evaluated_last_timestamp: str
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
    return_percent: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown_cash: float
    take_profits: int
    stop_losses: int
    timeouts: int
    skipped_by_model: int
    skipped_while_open: int
    invalid_trade: int
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    top_threshold: float
    bottom_threshold: float
    min_buy_r: float
    min_sell_r: float
    tp_multiplier: float
    sl_multiplier: float
    hold_bars: int
    spread_mode: str
    spread_value: float
    same_bar_policy: str
    monthly_pnl: dict[str, float]
    monthly_trades: dict[str, int]
    positive_months: int
    negative_months: int
    output_json: str
    output_html: str
    output_trades_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase146A research PnL audit for Phase145A sequence WaveNet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_sequence_wavenet_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--model-path", default="")
    parser.add_argument("--record-path", default="")
    parser.add_argument("--max-samples", type=int, default=24000)
    parser.add_argument("--eval-split", choices=("test", "validation", "all", "tail"), default="test")
    parser.add_argument("--eval-frac", type=float, default=0.15, help="Used only with --eval-split tail")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--top-threshold", type=float, default=0.0)
    parser.add_argument("--bottom-threshold", type=float, default=0.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--tp-multiplier", type=float, default=0.75)
    parser.add_argument("--sl-multiplier", type=float, default=0.75)
    parser.add_argument("--hold-bars", type=int, default=48)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Phase146A sequence WaveNet PnL audit")
    return parser.parse_args(argv)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return (
        storage_root
        / "processed"
        / symbol
        / timeframe
        / "pivot_pattern_sequence_flat_latest.parquet"
    )


def model_dir(args: argparse.Namespace) -> Path:
    return Path(args.storage_root) / "models" / args.model_id


def latest_version(directory: Path) -> int:
    versions: list[int] = []
    if directory.exists():
        for path in directory.glob("v*_training.json"):
            raw = path.stem.removeprefix("v").removesuffix("_training")
            if raw.isdigit():
                versions.append(int(raw))
    return max(versions, default=0)


def resolve_model_files(args: argparse.Namespace) -> tuple[Path, Path, int]:
    if args.model_path and args.record_path:
        version = int(args.model_version) if args.model_version > 0 else 0
        return Path(args.model_path), Path(args.record_path), version
    directory = model_dir(args)
    version = int(args.model_version) if args.model_version > 0 else latest_version(directory)
    if version < 1:
        raise RuntimeError(f"No model record found for {args.model_id} in {directory}")
    return directory / f"v{version}_model.keras", directory / f"v{version}_training.json", version


def load_record(record_path: Path) -> dict[str, Any]:
    if not record_path.exists():
        raise RuntimeError(f"Model record not found: {record_path}")
    return json.loads(record_path.read_text(encoding="utf-8"))


def model_args_from_record(record: Mapping[str, Any]) -> argparse.Namespace:
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    architecture = payload.get("architecture", {}) if isinstance(payload, Mapping) else {}
    return argparse.Namespace(
        branch_filters=int(architecture.get("branch_filters", 48)),
        temporal_filters=int(architecture.get("temporal_filters", 96)),
        temporal_kernels=",".join(str(v) for v in architecture.get("temporal_kernels", [3, 5, 9])),
        dilations=",".join(str(v) for v in architecture.get("dilations", [1, 2, 4, 8, 16, 32])),
        residual_blocks=int(architecture.get("residual_blocks", 2)),
        attention_heads=int(architecture.get("attention_heads", 4)),
        attention_key_dim=int(architecture.get("attention_key_dim", 16)),
        se_ratio=int(architecture.get("se_ratio", 8)),
        dense_units=int(architecture.get("dense_units", 128)),
        dropout=float(architecture.get("dropout", 0.25)),
        activation=str(architecture.get("activation", "tanh")),
        learning_rate=float(architecture.get("learning_rate", 0.0005)),
        action_loss_weight=float(architecture.get("action_loss_weight", 1.0)),
        top_loss_weight=float(architecture.get("top_loss_weight", 0.5)),
        bottom_loss_weight=float(architecture.get("bottom_loss_weight", 0.5)),
        r_loss_weight=float(architecture.get("r_loss_weight", 0.5)),
    )


def load_weights_from_keras_archive(model: Any, model_path: Path) -> None:
    try:
        model.load_weights(str(model_path))
        return
    except Exception as direct_error:
        if model_path.suffix.lower() != ".keras":
            raise direct_error
    with zipfile.ZipFile(model_path, "r") as archive:
        weight_names = [name for name in archive.namelist() if name.endswith((".weights.h5", ".h5"))]
        if not weight_names:
            raise RuntimeError(f"No H5 weights file found inside Keras archive: {model_path}")
        preferred = "model.weights.h5" if "model.weights.h5" in weight_names else weight_names[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            extracted = Path(tmpdir) / Path(preferred).name
            extracted.write_bytes(archive.read(preferred))
            model.load_weights(str(extracted))


def rebuild_model_from_record(
    tf: Any,
    model_path: Path,
    record: Mapping[str, Any],
    meta: Mapping[str, Any],
    input_shape: tuple[int, int],
) -> Any:
    model = build_sequence_wavenet_model(tf, input_shape, meta, model_args_from_record(record))
    load_weights_from_keras_archive(model, model_path)
    return model


def load_model(
    model_path: Path,
    record: Mapping[str, Any] | None = None,
    meta: Mapping[str, Any] | None = None,
    input_shape: tuple[int, int] | None = None,
) -> Any:
    if not model_path.exists():
        raise RuntimeError(f"Keras model not found: {model_path}")
    tf = require_tensorflow()
    # The project-owned Phase145A model uses Keras Lambda layers for feature
    # slicing (5M/HTF/all branches and last-timestep pooling). Keras 3 blocks
    # lambda deserialization by default, so this research-only loader explicitly
    # trusts local artifacts generated by this project. Some Keras versions still
    # cannot infer deserialized Lambda output shapes; in that case we rebuild the
    # architecture from the local training record and load weights from the .keras
    # archive.
    try:
        return tf.keras.models.load_model(model_path, safe_mode=False, compile=False)
    except TypeError:
        try:
            tf.keras.config.enable_unsafe_deserialization()
        except Exception:
            pass
        try:
            return tf.keras.models.load_model(model_path, compile=False)
        except Exception:
            if record is None or meta is None or input_shape is None:
                raise
    except (NotImplementedError, ValueError):
        if record is None or meta is None or input_shape is None:
            raise
    return rebuild_model_from_record(tf, model_path, record, meta, input_shape)


def load_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Sequence tensor metadata not found: {path}")
    with np.load(path, allow_pickle=True) as data:
        return {name: data[name] for name in data.files}


def normalize_batch(x_batch: np.ndarray, record: Mapping[str, Any]) -> np.ndarray:
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    mean = np.asarray(payload.get("scaler_mean"), dtype=np.float32)
    std = np.asarray(payload.get("scaler_std"), dtype=np.float32)
    if mean.size == 0 or std.size == 0:
        raise RuntimeError("Model record payload must include scaler_mean and scaler_std")
    std = np.where((~np.isfinite(std)) | (std < 1e-6), 1.0, std).astype(np.float32)
    clean = np.nan_to_num(x_batch.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    normalized = (clean - mean) / std
    return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def make_predict_sequence(
    tf: Any,
    x_values: np.ndarray,
    tensor_indices: Sequence[int],
    record: Mapping[str, Any],
    batch_size: int,
) -> Any:
    class PivotSequencePredict(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            super().__init__()
            self.tensor_indices = np.asarray(tensor_indices, dtype=np.int64)

        def __len__(self) -> int:
            return int(np.ceil(len(self.tensor_indices) / max(int(batch_size), 1)))

        def __getitem__(self, index: int) -> np.ndarray:
            start = index * max(int(batch_size), 1)
            end = min(len(self.tensor_indices), start + max(int(batch_size), 1))
            rows = self.tensor_indices[start:end]
            return normalize_batch(np.asarray(x_values[rows]), record)

    return PivotSequencePredict()


def threshold_value(
    args_value: float, record: Mapping[str, Any], key: str, default: float
) -> float:
    if args_value >= 0:
        return float(args_value)
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    thresholds = payload.get("thresholds", {}) if isinstance(payload, Mapping) else {}
    return float(thresholds.get(key, default))


def apply_max_windows(indices: np.ndarray, max_windows: int) -> np.ndarray:
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        return indices[::step][:max_windows]
    return indices


def eval_tensor_indices(
    selected_rows: np.ndarray, args: argparse.Namespace
) -> tuple[np.ndarray, str]:
    if args.eval_split == "all":
        return apply_max_windows(selected_rows, int(args.max_windows)), "all"
    if args.eval_split == "tail":
        if not 0 < float(args.eval_frac) <= 1:
            raise RuntimeError("eval-frac must be in (0,1]")
        count = max(1, int(len(selected_rows) * float(args.eval_frac)))
        return apply_max_windows(selected_rows[-count:], int(args.max_windows)), "tail"
    train_idx, validation_idx, test_idx = split_indices(
        len(selected_rows), float(args.train_frac), float(args.val_frac), int(args.purge_gap)
    )
    local = validation_idx if args.eval_split == "validation" else test_idx
    return apply_max_windows(selected_rows[local], int(args.max_windows)), args.eval_split


def max_drawdown(balances: Sequence[float]) -> float:
    peak = float(balances[0]) if balances else 0.0
    worst = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        worst = max(worst, peak - float(balance))
    return worst


def write_trades_csv(path: Path, trades: Sequence[BacktestTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(asdict(trades[0]).keys()) if trades else list(BacktestTrade.__annotations__)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def monthly_stats(trades: Sequence[BacktestTrade]) -> tuple[dict[str, float], dict[str, int]]:
    pnl: dict[str, float] = {}
    counts: dict[str, int] = {}
    for trade in trades:
        month = str(trade.timestamp)[:7] if trade.timestamp else "unknown"
        pnl[month] = pnl.get(month, 0.0) + float(trade.cash_pnl)
        counts[month] = counts.get(month, 0) + 1
    return dict(sorted(pnl.items())), dict(sorted(counts.items()))


def summarize_trades(
    trades: Sequence[BacktestTrade],
    initial_capital: float,
    evaluated_samples: int,
    skipped_by_model: int,
    skipped_while_open: int,
    invalid_trade: int,
    args: argparse.Namespace,
    model_path: Path,
    record_path: Path,
    version: int,
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    tensor_shape: Sequence[int],
    selected_samples: int,
    evaluated_first_timestamp: str,
    evaluated_last_timestamp: str,
    thresholds: Mapping[str, float],
) -> BacktestReport:
    pnls = [float(trade.cash_pnl) for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    balances = [float(initial_capital), *[float(trade.balance) for trade in trades]]
    final_balance = balances[-1]
    month_pnl, month_trades = monthly_stats(trades)
    return BacktestReport(
        model_id=args.model_id,
        model_version=version,
        model_path=str(model_path),
        record_path=str(record_path),
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        flat_path=str(flat_path),
        tensor_shape=[int(value) for value in tensor_shape],
        eval_split=str(args.eval_split),
        selected_samples=int(selected_samples),
        evaluated_samples=int(evaluated_samples),
        evaluated_first_timestamp=evaluated_first_timestamp,
        evaluated_last_timestamp=evaluated_last_timestamp,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        win_rate=wins / len(trades) if trades else 0.0,
        total_cash_pnl=sum(pnls),
        buy_cash_pnl=sum(trade.cash_pnl for trade in trades if trade.side == "BUY"),
        sell_cash_pnl=sum(trade.cash_pnl for trade in trades if trade.side == "SELL"),
        final_balance=final_balance,
        return_percent=(final_balance - initial_capital) / initial_capital if initial_capital else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        max_drawdown_cash=max_drawdown(balances),
        take_profits=sum(1 for trade in trades if trade.outcome == "take_profit"),
        stop_losses=sum(1 for trade in trades if trade.outcome == "stop_loss"),
        timeouts=sum(1 for trade in trades if trade.outcome == "timeout"),
        skipped_by_model=skipped_by_model,
        skipped_while_open=skipped_while_open,
        invalid_trade=invalid_trade,
        buy_threshold=float(thresholds["buy_threshold"]),
        sell_threshold=float(thresholds["sell_threshold"]),
        min_margin=float(thresholds["min_margin"]),
        top_threshold=float(args.top_threshold),
        bottom_threshold=float(args.bottom_threshold),
        min_buy_r=float(thresholds["min_buy_r"]),
        min_sell_r=float(thresholds["min_sell_r"]),
        tp_multiplier=float(args.tp_multiplier),
        sl_multiplier=float(args.sl_multiplier),
        hold_bars=int(args.hold_bars),
        spread_mode=str(args.spread_mode),
        spread_value=float(args.spread_value),
        same_bar_policy=str(args.same_bar_policy),
        monthly_pnl=month_pnl,
        monthly_trades=month_trades,
        positive_months=sum(1 for value in month_pnl.values() if value > 0),
        negative_months=sum(1 for value in month_pnl.values() if value < 0),
        output_json=str(Path(args.output_dir) / "latest.json"),
        output_html=str(Path(args.output_dir) / "latest.html"),
        output_trades_csv=str(Path(args.output_dir) / "latest_trades.csv"),
        production_status="BLOCKED — research Phase146A sequence WaveNet PnL audit only",
    )


def run_backtest(
    flat: pd.DataFrame,
    tensor_rows: np.ndarray,
    sample_positions: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    args: argparse.Namespace,
    record: Mapping[str, Any],
) -> tuple[list[BacktestTrade], dict[str, float], dict[str, int]]:
    buy_threshold = threshold_value(args.buy_threshold, record, "buy_threshold", 0.34)
    sell_threshold = threshold_value(args.sell_threshold, record, "sell_threshold", 0.34)
    min_margin = threshold_value(args.min_margin, record, "min_margin", 0.0)
    min_buy_r = (
        float(args.min_buy_r)
        if float(args.min_buy_r) > -998
        else threshold_value(-1.0, record, "min_buy_r", -999.0)
    )
    min_sell_r = (
        float(args.min_sell_r)
        if float(args.min_sell_r) > -998
        else threshold_value(-1.0, record, "min_sell_r", -999.0)
    )
    thresholds = {
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "min_margin": min_margin,
        "min_buy_r": min_buy_r,
        "min_sell_r": min_sell_r,
    }
    action_prob = np.asarray(predictions["action"], dtype=np.float32)
    top_prob = np.asarray(predictions["top"], dtype=np.float32).reshape(-1)
    bottom_prob = np.asarray(predictions["bottom"], dtype=np.float32).reshape(-1)
    buy_r = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
    sell_r = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
    actions = selected_action(action_prob, buy_threshold, sell_threshold, min_margin)
    balance = float(args.initial_capital)
    open_until = -1
    skipped_by_model = 0
    skipped_while_open = 0
    invalid_trade = 0
    trades: list[BacktestTrade] = []
    for offset, row_position in enumerate(sample_positions):
        row_id = int(row_position)
        if row_id <= open_until:
            skipped_while_open += 1
            continue
        side = int(actions[offset])
        if side == ACTION_BUY:
            if bottom_prob[offset] < float(args.bottom_threshold) or buy_r[offset] < min_buy_r:
                skipped_by_model += 1
                continue
        elif side == ACTION_SELL:
            if top_prob[offset] < float(args.top_threshold) or sell_r[offset] < min_sell_r:
                skipped_by_model += 1
                continue
        else:
            skipped_by_model += 1
            continue
        atr_value = float(flat.iloc[row_id].get("h4_atr_for_risk", 0.0))
        if not np.isfinite(atr_value) or atr_value <= 0:
            invalid_trade += 1
            continue
        tp_distance = max(atr_value * float(args.tp_multiplier), 0.5)
        sl_distance = max(atr_value * float(args.sl_multiplier), 0.5)
        path = trade_path(flat, row_id, side, tp_distance, sl_distance, int(args.hold_bars), args)
        if path is None:
            invalid_trade += 1
            continue
        points, entry_row, exit_row, entry, tp, sl, exit_price, outcome = path
        risk_amount = max(balance * float(args.risk_per_trade), 0.0)
        quantity = risk_amount / sl_distance if sl_distance else 0.0
        cash_pnl = points * quantity
        balance += cash_pnl
        trades.append(
            BacktestTrade(
                number=len(trades) + 1,
                timestamp=str(flat.iloc[row_id].get("timestamp", "")),
                side="BUY" if side == ACTION_BUY else "SELL",
                tensor_row=int(tensor_rows[offset]),
                sample_index=offset,
                row_id=row_id,
                entry_row_id=entry_row,
                exit_row_id=exit_row,
                entry=entry,
                tp=tp,
                sl=sl,
                exit_price=exit_price,
                points_pnl=points,
                cash_pnl=cash_pnl,
                balance=balance,
                outcome=outcome,
                action_sell_prob=float(action_prob[offset, 0]),
                action_hold_prob=float(action_prob[offset, 1]),
                action_buy_prob=float(action_prob[offset, 2]),
                top_prob=float(top_prob[offset]),
                bottom_prob=float(bottom_prob[offset]),
                buy_r_pred=float(buy_r[offset]),
                sell_r_pred=float(sell_r[offset]),
            )
        )
        open_until = max(open_until, int(exit_row))
        if balance <= 0:
            break
    skips = {
        "skipped_by_model": skipped_by_model,
        "skipped_while_open": skipped_while_open,
        "invalid_trade": invalid_trade,
    }
    return trades, thresholds, skips


def render_html(title: str, report: BacktestReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1320px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; overflow:auto; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase146A sequence WaveNet PnL audit. Research only.</p>
<div class="grid">
<div class="metric"><span>Final balance</span><strong>${report.final_balance:.2f}</strong></div>
<div class="metric"><span>Return</span><strong>{report.return_percent:.2%}</strong></div>
<div class="metric"><span>PF</span><strong>{report.profit_factor:.3f}</strong></div>
<div class="metric"><span>Trades</span><strong>{report.trades}</strong></div>
<div class="metric"><span>Max DD</span><strong>${report.max_drawdown_cash:.2f}</strong></div>
<div class="metric"><span>Win rate</span><strong>{report.win_rate:.2%}</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.monotonic()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tensor_path = (
        Path(args.tensor_path)
        if args.tensor_path
        else default_tensor_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    meta_path = (
        Path(args.meta_path)
        if args.meta_path
        else default_meta_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE146A BACKTEST/PnL AUDIT — SEQUENCE WAVENET")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        print(f"  flat        : {flat_path}")
        model_path, record_path, version = resolve_model_files(args)
        record = load_record(record_path)
        tf = require_tensorflow()
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = load_meta(meta_path)
        model = load_model(model_path, record, meta, tuple(int(v) for v in x_all.shape[1:]))
        flat = pd.read_parquet(flat_path).reset_index(drop=True)
        sample_positions_all = np.asarray(meta["sample_indices"], dtype=np.int64)
        if len(sample_positions_all) != int(x_all.shape[0]):
            raise RuntimeError("meta.sample_indices length does not match tensor samples")
        selected_rows = selected_indices(int(x_all.shape[0]), int(args.max_samples))
        eval_rows, eval_name = eval_tensor_indices(selected_rows, args)
        if len(eval_rows) < 1:
            raise RuntimeError("No evaluation rows selected")
        sample_positions = sample_positions_all[eval_rows]
        predict_sequence = make_predict_sequence(
            tf, x_all, eval_rows, record, max(int(args.batch_size), 1)
        )
        predictions = prediction_dict(model.predict(predict_sequence, verbose=0))
        trades, thresholds, skips = run_backtest(flat, eval_rows, sample_positions, predictions, args, record)
        first_time = str(flat.iloc[int(sample_positions[0])].get("timestamp", ""))
        last_time = str(flat.iloc[int(sample_positions[-1])].get("timestamp", ""))
        report = summarize_trades(
            trades,
            float(args.initial_capital),
            len(eval_rows),
            int(skips["skipped_by_model"]),
            int(skips["skipped_while_open"]),
            int(skips["invalid_trade"]),
            args,
            model_path,
            record_path,
            version,
            tensor_path,
            meta_path,
            flat_path,
            x_all.shape,
            len(selected_rows),
            first_time,
            last_time,
            thresholds,
        )
        write_trades_csv(Path(report.output_trades_csv), trades)
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "trades_preview": [asdict(trade) for trade in trades[:250]],
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "trades_csv": report.output_trades_csv,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  model       : {model_path}")
        print(f"  version     : {version}")
        print(f"  split       : {eval_name}")
        print(f"  evaluated   : {report.evaluated_samples:,}")
        print(f"  trades      : {report.trades:,}")
        print(f"  final       : ${report.final_balance:.2f}")
        print(f"  return      : {report.return_percent:.2%}")
        print(f"  PF          : {report.profit_factor:.3f}")
        print(f"  max DD      : ${report.max_drawdown_cash:.2f}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
