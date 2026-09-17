"""Phase142B: walk-forward validation for Keras pivot-pattern WaveNet models."""

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
from backtest_pivot_pattern_wavenet import (
    BacktestReport,
    BacktestTrade,
    default_flat_path,
    run_backtest,
)
from train_pivot_pattern_wavenet import (
    build_wavenet_model,
    default_tensor_path,
    load_tensor,
    normalize_train_only,
    prediction_dict,
    require_tensorflow,
    sample_weight_dict,
    target_dict,
)

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_wavenet_walk_forward")
SCORE_METRICS = ("net_profit", "profit_factor", "final_balance", "drawdown_adjusted")


@dataclass(frozen=True)
class FoldRow:
    fold: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_rows: int
    validation_rows: int
    test_rows: int
    selected_params: dict[str, Any]
    validation_net_profit: float
    validation_profit_factor: float
    validation_trades: int
    validation_max_drawdown: float
    test_net_profit: float
    test_profit_factor: float
    test_trades: int
    test_final_balance: float
    test_max_drawdown: float


@dataclass(frozen=True)
class WalkForwardReport:
    tensor_path: str
    flat_path: str
    samples: int
    folds: int
    positive_folds: int
    negative_folds: int
    no_trade_folds: int
    trades: int
    buy_trades: int
    sell_trades: int
    wins: int
    losses: int
    win_rate: float
    initial_balance: float
    final_balance: float
    net_profit: float
    return_percent: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown_cash: float
    output_json: str
    output_html: str
    output_folds_csv: str
    output_trades_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase142B walk-forward validation for pivot WaveNet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_wavenet_wf_5m")
    parser.add_argument("--train-days-min", type=int, default=120)
    parser.add_argument("--validation-days", type=int, default=20)
    parser.add_argument("--test-days", type=int, default=20)
    parser.add_argument("--purge-hours", type=float, default=4.0)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--filters", type=int, default=48)
    parser.add_argument("--kernel-size", type=int, default=3)
    parser.add_argument("--n-layers", type=int, default=6)
    parser.add_argument("--n-blocks", type=int, default=2)
    parser.add_argument("--dense-units", type=int, default=96)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--action-loss-weight", type=float, default=1.0)
    parser.add_argument("--top-loss-weight", type=float, default=0.5)
    parser.add_argument("--bottom-loss-weight", type=float, default=0.5)
    parser.add_argument("--r-loss-weight", type=float, default=0.5)
    parser.add_argument("--class-weight", choices=("auto", "off"), default="auto")
    parser.add_argument("--early-stopping-patience", type=int, default=10)
    parser.add_argument("--buy-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--sell-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--margins", default="0,0.05")
    parser.add_argument("--top-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--bottom-thresholds", default="0.45,0.55,0.65")
    parser.add_argument("--min-r-values", default="-0.25,0,0.25")
    parser.add_argument("--tp-multipliers", default="0.75,1.0,1.25")
    parser.add_argument("--sl-multipliers", default="0.50,0.75")
    parser.add_argument("--hold-bars", default="24,48")
    parser.add_argument("--min-validation-trades", type=int, default=10)
    parser.add_argument("--score-metric", choices=SCORE_METRICS, default="drawdown_adjusted")
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-title", default="Pivot WaveNet walk-forward validation")
    return parser.parse_args(argv)


def parse_float_list(text: str, default: Sequence[float]) -> list[float]:
    values: list[float] = []
    for raw in (part.strip() for part in text.split(",")):
        if raw:
            value = float(raw)
            if value not in values:
                values.append(value)
    return values or list(default)


def parse_int_list(text: str, default: Sequence[int]) -> list[int]:
    values: list[int] = []
    for raw in (part.strip() for part in text.split(",")):
        if raw:
            value = max(int(raw), 1)
            if value not in values:
                values.append(value)
    return values or list(default)


def parameter_grid(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for buy_threshold in parse_float_list(args.buy_thresholds, [0.45, 0.55, 0.65]):
        for sell_threshold in parse_float_list(args.sell_thresholds, [0.45, 0.55, 0.65]):
            for margin in parse_float_list(args.margins, [0.0, 0.05]):
                for top_threshold in parse_float_list(args.top_thresholds, [0.45, 0.55, 0.65]):
                    for bottom_threshold in parse_float_list(
                        args.bottom_thresholds, [0.45, 0.55, 0.65]
                    ):
                        for min_r in parse_float_list(args.min_r_values, [-0.25, 0.0, 0.25]):
                            for tp_multiplier in parse_float_list(
                                args.tp_multipliers, [0.75, 1.0, 1.25]
                            ):
                                for sl_multiplier in parse_float_list(
                                    args.sl_multipliers, [0.5, 0.75]
                                ):
                                    for hold_bars in parse_int_list(args.hold_bars, [24, 48]):
                                        rows.append(
                                            {
                                                "buy_threshold": buy_threshold,
                                                "sell_threshold": sell_threshold,
                                                "min_margin": margin,
                                                "top_threshold": top_threshold,
                                                "bottom_threshold": bottom_threshold,
                                                "min_buy_r": min_r,
                                                "min_sell_r": min_r,
                                                "tp_multiplier": tp_multiplier,
                                                "sl_multiplier": sl_multiplier,
                                                "hold_bars": hold_bars,
                                            }
                                        )
    return rows


def with_params(
    args: argparse.Namespace, params: Mapping[str, Any], initial_capital: float
) -> argparse.Namespace:
    values = vars(args).copy()
    values.update(params)
    values["buy_threshold"] = params["buy_threshold"]
    values["sell_threshold"] = params["sell_threshold"]
    values["eval_frac"] = 1.0
    values["max_windows"] = 0
    values["model_version"] = 0
    values["initial_capital"] = initial_capital
    return argparse.Namespace(**values)


def validation_score(report: BacktestReport, args: argparse.Namespace) -> float:
    if report.trades < max(int(args.min_validation_trades), 0):
        return -1e18 + report.trades
    if args.score_metric == "profit_factor":
        return report.profit_factor
    if args.score_metric == "final_balance":
        return report.final_balance
    if args.score_metric == "drawdown_adjusted":
        return report.total_cash_pnl - 0.25 * report.max_drawdown_cash
    return report.total_cash_pnl - 0.15 * report.max_drawdown_cash


def select_policy(
    flat: pd.DataFrame,
    sample_positions: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], BacktestReport]:
    best_params: dict[str, Any] | None = None
    best_report: BacktestReport | None = None
    best_score = -1e30
    empty_record = {"payload": {"thresholds": {}}}
    for params in parameter_grid(args):
        candidate_args = with_params(args, params, args.initial_capital)
        report, _trades = run_backtest(
            flat, sample_positions, predictions, candidate_args, empty_record
        )
        score = validation_score(report, args)
        if score > best_score:
            best_score = score
            best_params = dict(params)
            best_report = report
    if best_params is None or best_report is None:
        raise RuntimeError("No validation policy selected")
    return best_params, best_report


def date_folds(
    timestamps: pd.Series, args: argparse.Namespace
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    dates = timestamps.dt.date
    unique_days = sorted(dates.unique())
    folds: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    cursor = max(int(args.train_days_min), 1)
    purge = pd.Timedelta(hours=max(float(args.purge_hours), 0.0))
    while cursor + args.validation_days + args.test_days <= len(unique_days):
        validation_start = pd.Timestamp(unique_days[cursor], tz="UTC")
        test_start = pd.Timestamp(unique_days[cursor + args.validation_days], tz="UTC")
        test_end = pd.Timestamp(
            unique_days[cursor + args.validation_days + args.test_days - 1], tz="UTC"
        ) + pd.Timedelta(days=1)
        train_mask = timestamps < validation_start - purge
        validation_mask = (timestamps >= validation_start) & (timestamps < test_start - purge)
        test_mask = (timestamps >= test_start) & (timestamps < test_end - purge)
        train_idx = np.flatnonzero(train_mask.to_numpy())
        validation_idx = np.flatnonzero(validation_mask.to_numpy())
        test_idx = np.flatnonzero(test_mask.to_numpy())
        if len(train_idx) >= 100 and len(validation_idx) >= 20 and len(test_idx) >= 20:
            folds.append((train_idx, validation_idx, test_idx))
        if args.max_folds > 0 and len(folds) >= args.max_folds:
            break
        cursor += max(int(args.test_days), 1)
    return folds


def maybe_limit_train(train_idx: np.ndarray, max_train_samples: int) -> np.ndarray:
    if max_train_samples <= 0 or len(train_idx) <= max_train_samples:
        return train_idx
    return train_idx[-max_train_samples:]


def aggregate_trades(
    trades: Sequence[BacktestTrade], initial_capital: float
) -> dict[str, float | int]:
    pnls = [trade.cash_pnl for trade in trades]
    balances = [initial_capital, *[trade.balance for trade in trades]]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    wins = sum(1 for value in pnls if value > 0)
    losses = sum(1 for value in pnls if value < 0)
    peak = initial_capital
    max_dd = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        max_dd = max(max_dd, peak - float(balance))
    final_balance = balances[-1]
    return {
        "trades": len(trades),
        "buy_trades": sum(1 for trade in trades if trade.side == "BUY"),
        "sell_trades": sum(1 for trade in trades if trade.side == "SELL"),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(trades) if trades else 0.0,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": (
            gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        "max_drawdown_cash": max_dd,
        "final_balance": final_balance,
        "net_profit": final_balance - initial_capital,
        "return_percent": (
            (final_balance - initial_capital) / initial_capital if initial_capital else 0.0
        ),
    }


def write_csv(path: Path, rows: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def render_html(title: str, report: WalkForwardReport, folds: Sequence[FoldRow]) -> str:
    fold_rows = "".join(
        "<tr>"
        f"<td>{row.fold}</td>"
        f"<td>{html.escape(row.test_start[:10])} → {html.escape(row.test_end[:10])}</td>"
        f"<td>{row.test_trades}</td>"
        f"<td>{row.test_net_profit:+.2f}</td>"
        f"<td>{row.test_profit_factor:.3f}</td>"
        f"<td>{row.test_final_balance:.2f}</td>"
        f"<td>{html.escape(json.dumps(row.selected_params))}</td>"
        "</tr>"
        for row in folds
    )
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8" /><title>{html.escape(title)}</title>
<style>
body {{ margin:0; background:#020617; color:#e5e7eb; font-family:Tahoma,Arial,sans-serif; line-height:1.7; }}
main {{ max-width:1450px; margin:0 auto; padding:24px; }}
.card,.hero {{ background:#0f172a; border:1px solid #334155; border-radius:18px; padding:18px; margin:16px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
.metric {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:12px; }}
.metric span {{ display:block; color:#94a3b8; font-size:13px; }}
.metric strong {{ direction:ltr; text-align:left; display:block; color:#7dd3fc; font-size:21px; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:12px; }}
th,td {{ border-bottom:1px solid #1e293b; padding:7px; vertical-align:top; }} th {{ color:#bae6fd; }}
code,pre {{ direction:ltr; text-align:left; background:#020617; border:1px solid #334155; border-radius:10px; padding:2px 6px; }}
</style></head><body><main>
<section class="hero"><h1>{html.escape(title)}</h1><p>Each fold trains a fresh Keras WaveNet on past tensor samples and tests the next unseen window.</p>
<div class="grid">
<div class="metric"><span>Final balance</span><strong>${report.final_balance:.2f}</strong></div>
<div class="metric"><span>Return</span><strong>{report.return_percent:.2%}</strong></div>
<div class="metric"><span>PF</span><strong>{report.profit_factor:.3f}</strong></div>
<div class="metric"><span>Folds</span><strong>{report.positive_folds}/{report.negative_folds}</strong></div>
</div><p><strong>{html.escape(report.production_status)}</strong></p></section>
<section class="card"><h2>Report</h2><pre>{html.escape(json.dumps(asdict(report), indent=2, ensure_ascii=False))}</pre></section>
<section class="card"><h2>Folds</h2><table><thead><tr><th>fold</th><th>test</th><th>trades</th><th>net</th><th>PF</th><th>final</th><th>params</th></tr></thead><tbody>{fold_rows}</tbody></table></section>
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
    flat_path = (
        Path(args.flat_path)
        if args.flat_path
        else default_flat_path(Path(args.storage_root), args.symbol, args.timeframe)
    )
    try:
        print("\n" + "=" * 74)
        print("  PHASE142B PIVOT WAVENET WALK-FORWARD")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  flat        : {flat_path}")
        tf = require_tensorflow()
        data = load_tensor(tensor_path)
        flat = pd.read_parquet(flat_path).reset_index(drop=True)
        x_raw = np.asarray(data["X"])
        timestamps = pd.to_datetime(
            pd.Series(np.asarray(data["timestamp"]).astype(str)), utc=True, errors="coerce"
        )
        sample_positions = np.asarray(data["sample_indices"], dtype=np.int64)
        targets_all = {
            "target_action": np.asarray(data["target_action"], dtype=np.int64),
            "target_top_zone": np.asarray(data["target_top_zone"], dtype=np.float32),
            "target_bottom_zone": np.asarray(data["target_bottom_zone"], dtype=np.float32),
            "target_buy_r": np.asarray(data["target_buy_r"], dtype=np.float32),
            "target_sell_r": np.asarray(data["target_sell_r"], dtype=np.float32),
        }
        folds = date_folds(timestamps, args)
        if not folds:
            raise RuntimeError(
                "No walk-forward folds could be formed; lower day requirements or build more tensor samples"
            )
        fold_rows: list[FoldRow] = []
        all_trades: list[BacktestTrade] = []
        balance = float(args.initial_capital)
        empty_record = {"payload": {"thresholds": {}}}
        for fold_number, (train_idx_raw, validation_idx, test_idx) in enumerate(folds, start=1):
            train_idx = maybe_limit_train(train_idx_raw, int(args.max_train_samples))
            print(
                f"  fold {fold_number}: train={len(train_idx):,} val={len(validation_idx):,} test={len(test_idx):,}"
            )
            x_values, _mean, _std = normalize_train_only(x_raw, train_idx)
            train_targets = target_dict(targets_all, train_idx)
            validation_targets = target_dict(targets_all, validation_idx)
            model = build_wavenet_model(tf, (int(x_values.shape[1]), int(x_values.shape[2])), args)
            callbacks = [
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=max(int(args.early_stopping_patience), 1),
                    restore_best_weights=True,
                )
            ]
            model.fit(
                x_values[train_idx],
                train_targets,
                validation_data=(x_values[validation_idx], validation_targets),
                sample_weight=sample_weight_dict(train_targets, args.class_weight),
                batch_size=max(int(args.batch_size), 1),
                epochs=max(int(args.epochs), 1),
                callbacks=callbacks,
                verbose=2,
            )
            validation_predictions = prediction_dict(
                model.predict(x_values[validation_idx], batch_size=args.batch_size, verbose=0)
            )
            test_predictions = prediction_dict(
                model.predict(x_values[test_idx], batch_size=args.batch_size, verbose=0)
            )
            selected_params, validation_report = select_policy(
                flat, sample_positions[validation_idx], validation_predictions, args
            )
            fold_args = with_params(args, selected_params, balance)
            test_report, test_trades = run_backtest(
                flat, sample_positions[test_idx], test_predictions, fold_args, empty_record
            )
            for trade in test_trades:
                all_trades.append(BacktestTrade(**{**asdict(trade), "number": len(all_trades) + 1}))
            balance = test_report.final_balance
            fold_rows.append(
                FoldRow(
                    fold=fold_number,
                    train_start=str(timestamps.iloc[train_idx[0]]),
                    train_end=str(timestamps.iloc[train_idx[-1]]),
                    validation_start=str(timestamps.iloc[validation_idx[0]]),
                    validation_end=str(timestamps.iloc[validation_idx[-1]]),
                    test_start=str(timestamps.iloc[test_idx[0]]),
                    test_end=str(timestamps.iloc[test_idx[-1]]),
                    train_rows=len(train_idx),
                    validation_rows=len(validation_idx),
                    test_rows=len(test_idx),
                    selected_params=selected_params,
                    validation_net_profit=validation_report.total_cash_pnl,
                    validation_profit_factor=validation_report.profit_factor,
                    validation_trades=validation_report.trades,
                    validation_max_drawdown=validation_report.max_drawdown_cash,
                    test_net_profit=test_report.total_cash_pnl,
                    test_profit_factor=test_report.profit_factor,
                    test_trades=test_report.trades,
                    test_final_balance=test_report.final_balance,
                    test_max_drawdown=test_report.max_drawdown_cash,
                )
            )
        aggregate = aggregate_trades(all_trades, args.initial_capital)
        report = WalkForwardReport(
            tensor_path=str(tensor_path),
            flat_path=str(flat_path),
            samples=len(x_raw),
            folds=len(fold_rows),
            positive_folds=sum(1 for row in fold_rows if row.test_net_profit > 0),
            negative_folds=sum(1 for row in fold_rows if row.test_net_profit < 0),
            no_trade_folds=sum(1 for row in fold_rows if row.test_trades == 0),
            trades=int(aggregate["trades"]),
            buy_trades=int(aggregate["buy_trades"]),
            sell_trades=int(aggregate["sell_trades"]),
            wins=int(aggregate["wins"]),
            losses=int(aggregate["losses"]),
            win_rate=float(aggregate["win_rate"]),
            initial_balance=float(args.initial_capital),
            final_balance=float(aggregate["final_balance"]),
            net_profit=float(aggregate["net_profit"]),
            return_percent=float(aggregate["return_percent"]),
            gross_profit=float(aggregate["gross_profit"]),
            gross_loss=float(aggregate["gross_loss"]),
            profit_factor=float(aggregate["profit_factor"]),
            max_drawdown_cash=float(aggregate["max_drawdown_cash"]),
            output_json=str(output_dir / "latest.json"),
            output_html=str(output_dir / "latest.html"),
            output_folds_csv=str(output_dir / "latest_folds.csv"),
            output_trades_csv=str(output_dir / "latest_trades.csv"),
            production_status="BLOCKED — research walk-forward only",
        )
        write_csv(Path(report.output_folds_csv), fold_rows)
        write_csv(Path(report.output_trades_csv), all_trades)
        Path(report.output_html).write_text(
            render_html(args.report_title, report, fold_rows), encoding="utf-8"
        )
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "folds": [asdict(row) for row in fold_rows],
            "trades_preview": [asdict(trade) for trade in all_trades[:250]],
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "folds_csv": report.output_folds_csv,
                "trades_csv": report.output_trades_csv,
            },
        }
        Path(report.output_json).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  folds       : {report.folds:,}")
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
