"""Phase142A: backtest a trained Keras pivot-pattern WaveNet model."""

# ruff: noqa: E402,E501

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
from train_pivot_pattern_recognition import trade_path
from train_pivot_pattern_wavenet import (
    default_tensor_path,
    load_tensor,
    prediction_dict,
    require_tensorflow,
    selected_action,
)

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_wavenet_backtest")


@dataclass(frozen=True)
class BacktestTrade:
    number: int
    timestamp: str
    side: str
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
    tensor_path: str
    flat_path: str
    samples: int
    evaluated_samples: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    win_rate: float
    total_cash_pnl: float
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
    output_json: str
    output_html: str
    output_trades_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest Phase142A Keras pivot WaveNet on a 3D tensor.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_wavenet_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--model-path", default="")
    parser.add_argument("--record-path", default="")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--top-threshold", type=float, default=0.50)
    parser.add_argument("--bottom-threshold", type=float, default=0.50)
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
    parser.add_argument("--report-title", default="Pivot WaveNet backtest")
    return parser.parse_args(argv)


def default_flat_path(storage_root: Path, symbol: str, timeframe: str) -> Path:
    return storage_root / "processed" / symbol / timeframe / "pivot_pattern_flat_latest.parquet"


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


def load_model(model_path: Path) -> Any:
    if not model_path.exists():
        raise RuntimeError(f"Keras model not found: {model_path}")
    tf = require_tensorflow()
    return tf.keras.models.load_model(model_path)


def normalize_with_record(x_values: np.ndarray, record: Mapping[str, Any]) -> np.ndarray:
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    mean = np.asarray(payload.get("scaler_mean"), dtype=np.float32)
    std = np.asarray(payload.get("scaler_std"), dtype=np.float32)
    if mean.size == 0 or std.size == 0:
        raise RuntimeError("Model record payload must include scaler_mean and scaler_std")
    std = np.where(std < 1e-6, 1.0, std)
    return np.nan_to_num(
        (x_values.astype(np.float32) - mean) / std, nan=0.0, posinf=0.0, neginf=0.0
    )


def threshold_value(
    args_value: float, record: Mapping[str, Any], key: str, default: float
) -> float:
    if args_value >= 0:
        return float(args_value)
    payload = record.get("payload", {}) if isinstance(record, Mapping) else {}
    thresholds = payload.get("thresholds", {}) if isinstance(payload, Mapping) else {}
    return float(thresholds.get(key, default))


def eval_indices(rows: int, eval_frac: float, max_windows: int) -> np.ndarray:
    if not 0 < eval_frac <= 1:
        raise RuntimeError("eval-frac must be in (0, 1]")
    count = max(1, int(rows * eval_frac))
    indices = np.arange(rows - count, rows, dtype=np.int64)
    if max_windows > 0 and len(indices) > max_windows:
        step = max(1, len(indices) // max_windows)
        indices = indices[::step][:max_windows]
    return indices


def max_drawdown(balances: Sequence[float]) -> float:
    peak = float(balances[0]) if balances else 0.0
    worst = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        worst = max(worst, peak - float(balance))
    return worst


def summarize_trades(
    trades: Sequence[BacktestTrade],
    initial_capital: float,
    evaluated_samples: int,
    skipped_by_model: int,
    skipped_while_open: int,
    invalid_trade: int,
    args: argparse.Namespace,
) -> BacktestReport:
    pnls = [trade.cash_pnl for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    balances = [initial_capital, *[trade.balance for trade in trades]]
    final_balance = balances[-1]
    return BacktestReport(
        model_id=args.model_id,
        model_version=int(args.model_version),
        tensor_path=str(args.tensor_path),
        flat_path=str(args.flat_path),
        samples=0,
        evaluated_samples=evaluated_samples,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        win_rate=wins / len(trades) if trades else 0.0,
        total_cash_pnl=sum(pnls),
        final_balance=final_balance,
        return_percent=(
            (final_balance - initial_capital) / initial_capital if initial_capital else 0.0
        ),
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
        output_json=str(Path(args.output_dir) / "latest.json"),
        output_html=str(Path(args.output_dir) / "latest.html"),
        output_trades_csv=str(Path(args.output_dir) / "latest_trades.csv"),
        production_status="BLOCKED — research WaveNet backtest only",
    )


def write_trades_csv(path: Path, trades: Sequence[BacktestTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not trades:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(trades[0]).keys()))
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def render_html(title: str, report: BacktestReport) -> str:
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1300px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase142A WaveNet model replay on pivot tensor. Research only.</p>
<div class="grid">
<div class="metric"><span>Final balance</span><strong>${report.final_balance:.2f}</strong></div>
<div class="metric"><span>Return</span><strong>{report.return_percent:.2%}</strong></div>
<div class="metric"><span>PF</span><strong>{report.profit_factor:.3f}</strong></div>
<div class="metric"><span>Trades</span><strong>{report.trades}</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
</main></body></html>"""


def run_backtest(
    flat: pd.DataFrame,
    sample_positions: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    args: argparse.Namespace,
    record: Mapping[str, Any],
) -> tuple[BacktestReport, list[BacktestTrade]]:
    buy_threshold = threshold_value(args.buy_threshold, record, "buy_threshold", 0.55)
    sell_threshold = threshold_value(args.sell_threshold, record, "sell_threshold", 0.55)
    min_margin = threshold_value(args.min_margin, record, "min_margin", 0.05)
    min_buy_r = (
        args.min_buy_r if args.min_buy_r > -998 else threshold_value(-1.0, record, "min_buy_r", 0.0)
    )
    min_sell_r = (
        args.min_sell_r
        if args.min_sell_r > -998
        else threshold_value(-1.0, record, "min_sell_r", 0.0)
    )
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
        if side == 2:
            if bottom_prob[offset] < args.bottom_threshold or buy_r[offset] < min_buy_r:
                skipped_by_model += 1
                continue
        elif side == 0:
            if top_prob[offset] < args.top_threshold or sell_r[offset] < min_sell_r:
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
                side="BUY" if side == 2 else "SELL",
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
        open_until = max(open_until, exit_row)
        if balance <= 0:
            break
    report = summarize_trades(
        trades,
        args.initial_capital,
        len(sample_positions),
        skipped_by_model,
        skipped_while_open,
        invalid_trade,
        args,
    )
    return report, trades


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
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE142A BACKTEST PIVOT WAVENET")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  flat        : {flat_path}")
        model_path, record_path, version = resolve_model_files(args)
        record = load_record(record_path)
        model = load_model(model_path)
        data = load_tensor(tensor_path)
        flat = pd.read_parquet(flat_path).reset_index(drop=True)
        x_raw = np.asarray(data["X"])
        sample_positions = np.asarray(data["sample_indices"], dtype=np.int64)
        eval_idx = eval_indices(len(x_raw), args.eval_frac, args.max_windows)
        x_eval = normalize_with_record(x_raw[eval_idx], record)
        raw_predictions = model.predict(x_eval, batch_size=128, verbose=0)
        predictions = prediction_dict(raw_predictions)
        report, trades = run_backtest(flat, sample_positions[eval_idx], predictions, args, record)
        report = BacktestReport(
            **{
                **asdict(report),
                "samples": len(x_raw),
                "model_version": version,
                "tensor_path": str(tensor_path),
                "flat_path": str(flat_path),
            }
        )
        write_trades_csv(Path(report.output_trades_csv), trades)
        Path(report.output_html).write_text(
            render_html(args.report_title, report), encoding="utf-8"
        )
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
        print(f"  evaluated   : {report.evaluated_samples:,}")
        print(f"  trades      : {report.trades:,}")
        print(f"  final       : ${report.final_balance:.2f}")
        print(f"  return      : {report.return_percent:.2%}")
        print(f"  PF          : {report.profit_factor:.3f}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
