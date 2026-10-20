"""Calibrate and backtest the Phase 124 hybrid head with range TP/SL.

The hybrid head predicts SELL/HOLD/BUY from the Phase 123 matrix. This
script turns those probabilities into trades, uses the already-computed
1D/4H range columns for entry filters and TP/SL brackets, and scores the
result on a chronological evaluation slice.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import pandas as pd

from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import FilesystemArtifactStore
from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue
from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol, stored_symbols

DEFAULT_STORAGE = REPO_ROOT / "datasets"
CLASS_SELL = 0
CLASS_HOLD = 1
CLASS_BUY = 2
CLASS_NAMES = {CLASS_SELL: "sell", CLASS_HOLD: "hold", CLASS_BUY: "buy"}
SCORE_METRICS = ("total_pnl", "profit_factor", "precision_then_pnl", "winrate_then_pnl")


@dataclass(frozen=True)
class TradeResult:
    side: str
    row_index: int
    source_index: int
    entry_index: int
    exit_index: int
    entry: float
    tp: float
    sl: float
    exit_price: float
    outcome: str
    pnl: float
    label: int
    label_correct: bool


@dataclass(frozen=True)
class BacktestRow:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    samples: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    timeouts: int
    label_correct: int
    false_positive: int
    no_trade: int
    ambiguous: int
    invalid_range: int
    invalid_bracket: int
    win_rate: float
    label_precision: float
    total_pnl: float
    avg_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    coverage: float
    score: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest/calibrate hybrid head decisions with 1D/4H range TP/SL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=0.30)
    parser.add_argument("--threshold-min", type=float, default=0.35)
    parser.add_argument("--threshold-max", type=float, default=0.95)
    parser.add_argument("--threshold-step", type=float, default=0.05)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--precision-floor", type=float, default=0.0)
    parser.add_argument("--min-profit-factor", type=float, default=0.0)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="total_pnl")
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=0.0)
    parser.add_argument("--min-1d-room", type=float, default=0.0)
    parser.add_argument("--min-tp-distance", type=float, default=1.0)
    parser.add_argument("--min-sl-distance", type=float, default=1.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all eval rows")
    parser.add_argument("--save-record", choices=("0", "1"), default="1")
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default="run_logs/hybrid_head_backtest")
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0:
        raise RuntimeError("threshold-step must be positive")
    values: list[float] = []
    current = start
    while current <= stop + 1e-12:
        values.append(round(current, 6))
        current += step
    return values


def default_matrix_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "hybrid_xgboost_matrix_latest.parquet"


def eval_slice_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def load_head(storage_root: Path, model_id: str, version: int) -> tuple[Any, list[str], int]:
    catalogue = ModelCatalogue(storage_root)
    resolved_version = version if version > 0 else catalogue.latest_version(model_id)
    if resolved_version < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    artifact = FilesystemArtifactStore(storage_root).load(
        ModelId(model_id), ModelVersion(resolved_version)
    )
    if artifact is None:
        raise RuntimeError(f"No artifact bytes found for {model_id} v{resolved_version}")
    try:
        payload = pickle.loads(artifact.payload)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not load hybrid head because an optional booster package is missing. "
            "Install: pip install -r requirements-boosters.txt"
        ) from exc
    return payload["model"], list(payload["feature_names"]), resolved_version


def aligned_predict_proba(model: Any, x_values: np.ndarray) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x_values), dtype=np.float64)
    classes = [int(value) for value in getattr(model, "classes_", list(range(raw.shape[1])))]
    aligned = np.zeros((len(raw), 3), dtype=np.float64)
    for raw_col, cls in enumerate(classes):
        if 0 <= cls < 3:
            aligned[:, cls] = raw[:, raw_col]
    row_sums = aligned.sum(axis=1)
    missing = row_sums <= 0
    if np.any(missing):
        aligned[missing, :] = 1.0 / 3.0
        row_sums = aligned.sum(axis=1)
    return aligned / row_sums[:, None]


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    _, store, _ = build_data_service(storage_root)
    resolved = resolve_stored_symbol(store, symbol, timeframe)
    if not resolved.found:
        raise RuntimeError(
            f"No stored candles for {symbol} {timeframe}. "
            f"symbols on disk: {', '.join(stored_symbols(storage_root)) or 'none'}"
        )
    return sorted(
        store.query(Symbol(resolved.resolved), Timeframe(timeframe)),
        key=lambda c: c.open_time.value,
    )


def spread_abs(price: float, mode: str, value: float) -> float:
    if mode == "fixed":
        return max(0.0, value)
    return max(0.0, price * value / 100.0)


def decide_action(
    probabilities: Sequence[float],
    buy_threshold: float,
    sell_threshold: float,
    min_margin: float,
) -> int | None:
    sell_p, hold_p, buy_p = [float(value) for value in probabilities]
    buy_ok = (
        buy_p >= buy_threshold and buy_p - sell_p >= min_margin and buy_p - hold_p >= min_margin
    )
    sell_ok = (
        sell_p >= sell_threshold and sell_p - buy_p >= min_margin and sell_p - hold_p >= min_margin
    )
    if buy_ok and sell_ok:
        return -1
    if buy_ok:
        return CLASS_BUY
    if sell_ok:
        return CLASS_SELL
    return None


def bracket_for(row: pd.Series, side: int, entry: float) -> tuple[float, float] | None:
    if side == CLASS_BUY:
        tp_candidates = [float(row.get("range_4h_high_price", 0.0))]
        daily_high = float(row.get("range_1d_high_price", 0.0))
        if daily_high > 0:
            tp_candidates.append(daily_high)
        tp = min(value for value in tp_candidates if value > 0)
        sl = float(row.get("range_4h_low_price", 0.0))
        if tp <= entry or sl >= entry or sl <= 0:
            return None
        return tp, sl
    tp_candidates = [float(row.get("range_4h_low_price", 0.0))]
    daily_low = float(row.get("range_1d_low_price", 0.0))
    if daily_low > 0:
        tp_candidates.append(daily_low)
    tp = max(value for value in tp_candidates if value > 0)
    sl = float(row.get("range_4h_high_price", 0.0))
    if tp >= entry or sl <= entry or sl <= 0:
        return None
    return tp, sl


def range_filter_pass(row: pd.Series, side: int, min_4h_room: float, min_1d_room: float) -> bool:
    if float(row.get("range_4h_available", 0.0)) < 0.5:
        return False
    if float(row.get("range_1d_available", 0.0)) < 0.5:
        return False
    if side == CLASS_BUY:
        return (
            float(row.get("range_4h_up_room", 0.0)) >= min_4h_room
            and float(row.get("range_1d_up_room", 0.0)) >= min_1d_room
        )
    return (
        float(row.get("range_4h_down_room", 0.0)) >= min_4h_room
        and float(row.get("range_1d_down_room", 0.0)) >= min_1d_room
    )


def simulate_trade(
    row: pd.Series,
    side: int,
    candles: Sequence[Any],
    args: argparse.Namespace,
) -> TradeResult | None:
    source_index = int(row["source_index"])
    entry_index = source_index + 1
    if entry_index >= len(candles):
        return None
    raw_entry = float(candles[entry_index].open.amount)
    half_spread = spread_abs(raw_entry, args.spread_mode, args.spread_value) / 2.0
    if side == CLASS_BUY:
        entry = raw_entry + half_spread + max(args.slippage, 0.0)
    else:
        entry = raw_entry - half_spread - max(args.slippage, 0.0)
    bracket = bracket_for(row, side, entry)
    if bracket is None:
        return None
    tp, sl = bracket
    if abs(tp - entry) < args.min_tp_distance or abs(entry - sl) < args.min_sl_distance:
        return None

    max_exit = min(len(candles) - 1, entry_index + max(args.max_hold_bars, 1) - 1)
    exit_index = max_exit
    exit_price = float(candles[max_exit].close.amount)
    outcome = "timeout"
    for index in range(entry_index, max_exit + 1):
        candle = candles[index]
        close_for_spread = float(candle.close.amount)
        half = spread_abs(close_for_spread, args.spread_mode, args.spread_value) / 2.0
        if side == CLASS_BUY:
            high_exit = float(candle.high.amount) - half
            low_exit = float(candle.low.amount) - half
            hit_tp = high_exit >= tp
            hit_sl = low_exit <= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_index = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_index = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_index = index
                break
        else:
            low_exit = float(candle.low.amount) + half
            high_exit = float(candle.high.amount) + half
            hit_tp = low_exit <= tp
            hit_sl = high_exit >= sl
            if hit_tp and hit_sl:
                outcome = "stop_loss" if args.same_bar_policy == "stop_first" else "take_profit"
                exit_price = sl if outcome == "stop_loss" else tp
                exit_index = index
                break
            if hit_sl:
                outcome = "stop_loss"
                exit_price = sl
                exit_index = index
                break
            if hit_tp:
                outcome = "take_profit"
                exit_price = tp
                exit_index = index
                break
    if outcome == "timeout":
        half = spread_abs(exit_price, args.spread_mode, args.spread_value) / 2.0
        exit_price = exit_price - half if side == CLASS_BUY else exit_price + half
    pnl = exit_price - entry if side == CLASS_BUY else entry - exit_price
    label = int(row["label"])
    return TradeResult(
        side="BUY" if side == CLASS_BUY else "SELL",
        row_index=int(row.name) if row.name is not None else -1,
        source_index=source_index,
        entry_index=entry_index,
        exit_index=exit_index,
        entry=entry,
        tp=tp,
        sl=sl,
        exit_price=exit_price,
        outcome=outcome,
        pnl=pnl,
        label=label,
        label_correct=(label == side),
    )


def max_drawdown(pnls: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    worst = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def score_row(
    row: BacktestRow,
    min_trades: int,
    precision_floor: float,
    min_profit_factor: float,
    metric: str,
) -> float:
    if row.trades < min_trades:
        return -1.0
    if row.label_precision < precision_floor:
        return -1.0
    if row.profit_factor < min_profit_factor:
        return -1.0
    if metric == "profit_factor":
        return row.profit_factor
    if metric == "precision_then_pnl":
        return row.label_precision * 10_000.0 + row.total_pnl
    if metric == "winrate_then_pnl":
        return row.win_rate * 10_000.0 + row.total_pnl
    return row.total_pnl


def evaluate_thresholds(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    candles: Sequence[Any],
    args: argparse.Namespace,
    buy_threshold: float,
    sell_threshold: float,
) -> BacktestRow:
    trades: list[TradeResult] = []
    no_trade = ambiguous = invalid_range = invalid_bracket = 0
    for offset, (_, row) in enumerate(frame.iterrows()):
        decision = decide_action(
            probabilities[offset], buy_threshold, sell_threshold, args.min_margin
        )
        if decision == -1:
            ambiguous += 1
            no_trade += 1
            continue
        if decision is None:
            no_trade += 1
            continue
        if not range_filter_pass(row, decision, args.min_4h_room, args.min_1d_room):
            invalid_range += 1
            no_trade += 1
            continue
        trade = simulate_trade(row, decision, candles, args)
        if trade is None:
            invalid_bracket += 1
            no_trade += 1
            continue
        trades.append(trade)

    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    timeouts = sum(1 for trade in trades if trade.outcome == "timeout")
    label_correct = sum(1 for trade in trades if trade.label_correct)
    false_positive = len(trades) - label_correct
    buy_trades = sum(1 for trade in trades if trade.side == "BUY")
    sell_trades = sum(1 for trade in trades if trade.side == "SELL")
    row = BacktestRow(
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        min_margin=args.min_margin,
        samples=len(frame),
        trades=len(trades),
        buy_trades=buy_trades,
        sell_trades=sell_trades,
        wins=wins,
        losses=losses,
        timeouts=timeouts,
        label_correct=label_correct,
        false_positive=false_positive,
        no_trade=no_trade,
        ambiguous=ambiguous,
        invalid_range=invalid_range,
        invalid_bracket=invalid_bracket,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(label_correct, len(trades)),
        total_pnl=sum(pnls),
        avg_pnl=safe_div(sum(pnls), len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        coverage=safe_div(len(trades), len(frame)),
        score=0.0,
    )
    return row.__class__(
        **{
            **asdict(row),
            "score": score_row(
                row,
                args.min_trades,
                args.precision_floor,
                args.min_profit_factor,
                args.score_metric,
            ),
        }
    )


def write_csv(path: Path, rows: Sequence[BacktestRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def save_record_thresholds(
    args: argparse.Namespace,
    version: int,
    best: BacktestRow,
    files: dict[str, str],
) -> str:
    catalogue = ModelCatalogue(Path(args.storage_root))
    record = catalogue.read(args.model_id, version)
    if record is None:
        return ""
    record.decision_thresholds = {
        "buy_prob": best.buy_threshold,
        "sell_prob": best.sell_threshold,
        "min_margin": best.min_margin,
        "selected_by": "phase125_hybrid_head_range_backtest",
        "score_metric": args.score_metric,
        "total_pnl": best.total_pnl,
        "avg_pnl": best.avg_pnl,
        "win_rate": best.win_rate,
        "profit_factor": best.profit_factor,
        "max_drawdown": best.max_drawdown,
        "trades": best.trades,
        "coverage": best.coverage,
        "label_precision": best.label_precision,
        "files": files,
    }
    return str(catalogue.write(record))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("HYBRID HEAD RANGE BACKTEST")
        print(f"  matrix      : {matrix_path}")
        print(f"  model       : {args.model_id}")
        print(f"  score       : {args.score_metric}")
        model, features, version = load_head(storage_root, args.model_id, args.model_version)
        full_frame = pd.read_parquet(matrix_path)
        indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
        frame = full_frame.iloc[indices].copy()
        missing = [name for name in features if name not in frame.columns]
        if missing:
            raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
        x_values = (
            frame[features].replace([np.inf, -np.inf], 0.0).fillna(0.0).to_numpy(dtype=np.float32)
        )
        probabilities = aligned_predict_proba(model, x_values)
        candles = load_candles(storage_root, args.symbol, args.timeframe)
        thresholds = frange(args.threshold_min, args.threshold_max, args.threshold_step)
        rows = [
            evaluate_thresholds(frame, probabilities, candles, args, buy_threshold, sell_threshold)
            for buy_threshold in thresholds
            for sell_threshold in thresholds
        ]
        valid = [row for row in rows if row.score >= 0]
        best = max(
            valid,
            key=lambda row: (row.score, row.total_pnl, row.profit_factor, row.trades),
            default=None,
        )

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        write_csv(csv_path, rows)
        files = {"csv": str(csv_path), "json": str(json_path)}
        record_path = ""
        if best is not None and args.save_record == "1":
            record_path = save_record_thresholds(args, version, best, files)

        payload = {
            "args": vars(args),
            "model_version": version,
            "matrix_rows": len(full_frame),
            "eval_rows": len(frame),
            "best": asdict(best) if best else None,
            "rows": [asdict(row) for row in rows],
            "record_path": record_path,
            "files": files,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        rule("BEST RANGE BACKTEST")
        if best is None:
            print("  [X] No threshold pair satisfied the constraints.")
            return 2
        print(f"  buy/sell th : {best.buy_threshold:.3f} / {best.sell_threshold:.3f}")
        print(f"  trades      : {best.trades:,}/{best.samples:,} ({best.coverage:.1%})")
        print(f"  buy/sell    : {best.buy_trades:,} / {best.sell_trades:,}")
        print(f"  win rate    : {best.win_rate:.1%}")
        print(f"  label prec. : {best.label_precision:.1%}")
        print(f"  total pnl   : {best.total_pnl:.2f} USD per 1.00 lot/unit")
        print(f"  avg pnl     : {best.avg_pnl:.4f}")
        print(f"  profit fact.: {best.profit_factor:.3f}")
        print(f"  max DD      : {best.max_drawdown:.2f}")
        print(f"  TP/SL/time  : {best.wins}/{best.losses}/{best.timeouts}")
        if record_path:
            print(f"  record saved: {record_path}")
        print(f"  report      : {json_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
