"""Phase148A: range-aware prediction/backtest archive for sequence WaveNet.

This is Step 4 of the owner-approved research plan. It produces a complete
prediction + decision + range-aware trade simulation archive for a trained
Phase145/147 sequence WaveNet model.

Unlike Phase146A's first replay, TP/SL can be derived from range-model forecasts
stored in the sequence flat parquet (usually copied from hybrid telemetry as
`src5m_range_*` columns) or computed from the project range models.

Research-only. No paper/live approval.
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
    apply_max_windows,
    default_flat_path,
    eval_tensor_indices,
    is_option_b_record,
    load_meta,
    load_model,
    load_record,
    make_predict_sequence,
    resolve_model_files,
    threshold_value,
)
from train_pivot_pattern_image_cnn import selected_indices
from train_pivot_pattern_recognition import (
    ACTION_BUY,
    ACTION_NAMES,
    ACTION_SELL,
    safe_float,
    spread_abs,
    trade_path,
)
from train_pivot_pattern_sequence_wavenet import default_meta_path, default_tensor_path
from train_pivot_pattern_wavenet import prediction_dict, require_tensorflow, selected_action

DEFAULT_STORAGE = Path("datasets")
DEFAULT_OUTPUT_DIR = Path("run_logs/pivot_pattern_sequence_wavenet_range_archive")


@dataclass(frozen=True)
class RangeArchiveReport:
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
    range_source: str
    range_bracket_mode: str
    range_fallback: str
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
    skipped_range_unavailable: int
    skipped_range_filter: int
    invalid_bracket: int
    invalid_trade: int
    monthly_pnl: dict[str, float]
    monthly_trades: dict[str, int]
    side_pnl: dict[str, float]
    side_trades: dict[str, int]
    positive_months: int
    negative_months: int
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    top_threshold: float
    bottom_threshold: float
    min_buy_r: float
    min_sell_r: float
    min_range_4h_room: float
    min_range_1d_room: float
    min_tp_distance: float
    min_sl_distance: float
    max_tp_atr: float
    max_sl_atr: float
    hold_bars: int
    spread_mode: str
    spread_value: float
    same_bar_policy: str
    output_json: str
    output_html: str
    output_predictions: str
    output_predictions_csv: str
    output_trades: str
    output_trades_csv: str
    output_monthly_csv: str
    output_side_csv: str
    production_status: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase148A range-aware prediction/backtest archive for sequence WaveNet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--tensor-path", default="")
    parser.add_argument("--meta-path", default="")
    parser.add_argument("--flat-path", default="")
    parser.add_argument("--model-id", default="gold_pivot_pattern_sequence_wavenet_option_b_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--model-path", default="")
    parser.add_argument("--record-path", default="")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--eval-split", choices=("test", "validation", "all", "tail"), default="test")
    parser.add_argument("--eval-frac", type=float, default=0.15, help="Used only with --eval-split tail")
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--purge-gap", type=int, default=336)
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--buy-threshold", type=float, default=0.34)
    parser.add_argument("--sell-threshold", type=float, default=0.34)
    parser.add_argument("--min-margin", type=float, default=0.0)
    parser.add_argument("--top-threshold", type=float, default=0.0)
    parser.add_argument("--bottom-threshold", type=float, default=0.0)
    parser.add_argument("--min-buy-r", type=float, default=-999.0)
    parser.add_argument("--min-sell-r", type=float, default=-999.0)
    parser.add_argument("--range-source", choices=("auto", "flat", "models"), default="auto")
    parser.add_argument(
        "--range-bracket-mode",
        choices=("range", "range_capped", "atr"),
        default="range_capped",
    )
    parser.add_argument("--range-fallback", choices=("skip", "atr"), default="skip")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--range-1d-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--range-4h-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--use-1d-tp-cap", choices=("0", "1"), default="1")
    parser.add_argument("--min-range-4h-room", type=float, default=0.0)
    parser.add_argument("--min-range-1d-room", type=float, default=0.0)
    parser.add_argument("--min-tp-distance", type=float, default=0.5)
    parser.add_argument("--min-sl-distance", type=float, default=0.5)
    parser.add_argument("--max-tp-atr", type=float, default=2.0, help="0 disables ATR cap")
    parser.add_argument("--max-sl-atr", type=float, default=1.25, help="0 disables ATR cap")
    parser.add_argument("--atr-tp-multiplier", type=float, default=0.75)
    parser.add_argument("--atr-sl-multiplier", type=float, default=0.75)
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
    parser.add_argument("--report-title", default="Phase148A range-aware sequence WaveNet archive")
    return parser.parse_args(argv)


class RangeModelContext:
    def __init__(self, args: argparse.Namespace) -> None:
        from build_hybrid_xgboost_matrix import RangeFeatureConfig, RangeFeatureProvider

        self.provider_1d = RangeFeatureProvider(
            Path(args.storage_root),
            args.symbol,
            RangeFeatureConfig("1d", "1D", args.range_1d_model_id, int(args.range_1d_version), True),
        )
        self.provider_4h = RangeFeatureProvider(
            Path(args.storage_root),
            args.symbol,
            RangeFeatureConfig("4h", "4H", args.range_4h_model_id, int(args.range_4h_version), True),
        )

    def forecast(self, timestamp: Any, reference_close: float) -> dict[str, float]:
        values: dict[str, float] = {}
        values.update(self.provider_4h.forecast_for_signal(timestamp, reference_close))
        values.update(self.provider_1d.forecast_for_signal(timestamp, reference_close))
        return values


def row_value(row: pd.Series, key: str, default: float = 0.0) -> float:
    candidates = (key, f"src5m_{key}")
    for candidate in candidates:
        if candidate in row:
            value = safe_float(row.get(candidate, default), default)
            if np.isfinite(value):
                return float(value)
    return float(default)


def flat_range_record(row: pd.Series) -> dict[str, float]:
    keys = (
        "range_4h_available",
        "range_4h_high_price",
        "range_4h_low_price",
        "range_4h_width",
        "range_4h_up_room",
        "range_4h_down_room",
        "range_1d_available",
        "range_1d_high_price",
        "range_1d_low_price",
        "range_1d_width",
        "range_1d_up_room",
        "range_1d_down_room",
    )
    return {key: row_value(row, key, 0.0) for key in keys}


def has_flat_range(row: pd.Series) -> bool:
    values = flat_range_record(row)
    return (
        values.get("range_4h_available", 0.0) >= 0.5
        and values.get("range_4h_high_price", 0.0) > 0
        and values.get("range_4h_low_price", 0.0) > 0
    )


def combined_range_record(
    row: pd.Series,
    args: argparse.Namespace,
    model_context: RangeModelContext | None,
) -> tuple[dict[str, float], str]:
    if args.range_source in {"auto", "flat"} and has_flat_range(row):
        return flat_range_record(row), "flat"
    if args.range_source in {"auto", "models"}:
        if model_context is None:
            raise RuntimeError("range-source=models needs range model context")
        return model_context.forecast(row.get("timestamp", ""), row_value(row, "close", 0.0)), "models"
    return flat_range_record(row), "flat"


def model_context_if_needed(args: argparse.Namespace, flat: pd.DataFrame) -> RangeModelContext | None:
    if args.range_source == "models":
        return RangeModelContext(args)
    if args.range_source != "auto" or flat.empty:
        return None
    probe_count = min(len(flat), 250)
    for _, row in flat.head(probe_count).iterrows():
        if has_flat_range(row):
            return None
    return RangeModelContext(args)


def entry_price_for_row(flat: pd.DataFrame, row_id: int, side: int, args: argparse.Namespace) -> float | None:
    entry_row = row_id + 1
    if entry_row >= len(flat):
        return None
    raw_entry = safe_float(flat.at[entry_row, "open"])
    half_spread = spread_abs(raw_entry, args.spread_mode, args.spread_value) / 2.0
    return raw_entry + half_spread if side == ACTION_BUY else raw_entry - half_spread


def range_rooms(record: Mapping[str, float], reference_close: float, side: int) -> tuple[float, float]:
    if side == ACTION_BUY:
        room_4h = float(record.get("range_4h_up_room", 0.0))
        room_1d = float(record.get("range_1d_up_room", 0.0))
        if room_4h == 0.0 and record.get("range_4h_high_price", 0.0) > 0:
            room_4h = float(record["range_4h_high_price"]) - reference_close
        if room_1d == 0.0 and record.get("range_1d_high_price", 0.0) > 0:
            room_1d = float(record["range_1d_high_price"]) - reference_close
        return room_4h, room_1d
    room_4h = float(record.get("range_4h_down_room", 0.0))
    room_1d = float(record.get("range_1d_down_room", 0.0))
    if room_4h == 0.0 and record.get("range_4h_low_price", 0.0) > 0:
        room_4h = reference_close - float(record["range_4h_low_price"])
    if room_1d == 0.0 and record.get("range_1d_low_price", 0.0) > 0:
        room_1d = reference_close - float(record["range_1d_low_price"])
    return room_4h, room_1d


def range_filter_pass(record: Mapping[str, float], reference_close: float, side: int, args: argparse.Namespace) -> bool:
    if float(record.get("range_4h_available", 0.0)) < 0.5:
        return False
    if float(args.min_range_1d_room) > 0 and float(record.get("range_1d_available", 0.0)) < 0.5:
        return False
    room_4h, room_1d = range_rooms(record, reference_close, side)
    if room_4h < float(args.min_range_4h_room):
        return False
    return not (float(args.min_range_1d_room) > 0 and room_1d < float(args.min_range_1d_room))


def atr_distances(atr_value: float, args: argparse.Namespace) -> tuple[float, float]:
    tp_distance = max(float(atr_value) * float(args.atr_tp_multiplier), float(args.min_tp_distance))
    sl_distance = max(float(atr_value) * float(args.atr_sl_multiplier), float(args.min_sl_distance))
    return tp_distance, sl_distance


def range_distances(
    record: Mapping[str, float],
    side: int,
    entry: float,
    atr_value: float,
    args: argparse.Namespace,
) -> tuple[float, float, str] | None:
    if args.range_bracket_mode == "atr":
        tp_distance, sl_distance = atr_distances(atr_value, args)
        return tp_distance, sl_distance, "atr"
    high_4h = float(record.get("range_4h_high_price", 0.0))
    low_4h = float(record.get("range_4h_low_price", 0.0))
    high_1d = float(record.get("range_1d_high_price", 0.0))
    low_1d = float(record.get("range_1d_low_price", 0.0))
    if high_4h <= 0 or low_4h <= 0:
        return None
    if side == ACTION_BUY:
        tp_candidates = [value for value in (high_4h, high_1d if args.use_1d_tp_cap == "1" else 0.0) if value > entry]
        if not tp_candidates or low_4h >= entry:
            return None
        target_tp = min(tp_candidates)
        target_sl = low_4h
        tp_distance = target_tp - entry
        sl_distance = entry - target_sl
    else:
        tp_candidates = [value for value in (low_4h, low_1d if args.use_1d_tp_cap == "1" else 0.0) if 0 < value < entry]
        if not tp_candidates or high_4h <= entry:
            return None
        target_tp = max(tp_candidates)
        target_sl = high_4h
        tp_distance = entry - target_tp
        sl_distance = target_sl - entry
    if tp_distance <= 0 or sl_distance <= 0:
        return None
    if args.range_bracket_mode == "range_capped":
        if float(args.max_tp_atr) > 0 and atr_value > 0:
            tp_distance = min(tp_distance, float(args.max_tp_atr) * atr_value)
        if float(args.max_sl_atr) > 0 and atr_value > 0:
            sl_distance = min(sl_distance, float(args.max_sl_atr) * atr_value)
    tp_distance = max(float(tp_distance), float(args.min_tp_distance))
    sl_distance = max(float(sl_distance), float(args.min_sl_distance))
    return tp_distance, sl_distance, "range"


def selected_action_name(value: int) -> str:
    return ACTION_NAMES.get(int(value), "NONE") if int(value) >= 0 else "NONE"


def max_drawdown(balances: Sequence[float]) -> float:
    peak = float(balances[0]) if balances else 0.0
    worst = 0.0
    for balance in balances:
        peak = max(peak, float(balance))
        worst = max(worst, peak - float(balance))
    return worst


def month_key(timestamp: str) -> str:
    return str(timestamp)[:7] if timestamp else "unknown"


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_frame_archive(frame: pd.DataFrame, parquet_path: Path, csv_path: Path) -> str:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(parquet_path, index=False)
        return str(parquet_path)
    except Exception:
        frame.to_csv(csv_path, index=False)
        return str(csv_path)


def summarize_side(trades: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for side in ("BUY", "SELL"):
        selected = [trade for trade in trades if trade.get("side") == side]
        pnls = [float(trade.get("cash_pnl", 0.0)) for trade in selected]
        gross_profit = sum(value for value in pnls if value > 0)
        gross_loss = abs(sum(value for value in pnls if value < 0))
        rows.append(
            {
                "side": side,
                "trades": len(selected),
                "wins": sum(1 for value in pnls if value > 0),
                "losses": sum(1 for value in pnls if value < 0),
                "cash_pnl": sum(pnls),
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
            }
        )
    return rows


def summarize_monthly(trades: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    months = sorted({month_key(str(trade.get("timestamp", ""))) for trade in trades})
    rows: list[dict[str, Any]] = []
    for month in months:
        selected = [trade for trade in trades if month_key(str(trade.get("timestamp", ""))) == month]
        pnls = [float(trade.get("cash_pnl", 0.0)) for trade in selected]
        gross_profit = sum(value for value in pnls if value > 0)
        gross_loss = abs(sum(value for value in pnls if value < 0))
        rows.append(
            {
                "month": month,
                "trades": len(selected),
                "cash_pnl": sum(pnls),
                "wins": sum(1 for value in pnls if value > 0),
                "losses": sum(1 for value in pnls if value < 0),
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
            }
        )
    return rows


def build_report(
    args: argparse.Namespace,
    model_path: Path,
    record_path: Path,
    version: int,
    tensor_path: Path,
    meta_path: Path,
    flat_path: Path,
    tensor_shape: Sequence[int],
    selected_samples: int,
    evaluated_samples: int,
    first_timestamp: str,
    last_timestamp: str,
    range_source_used: str,
    trades: Sequence[Mapping[str, Any]],
    counters: Mapping[str, int],
    output_dir: Path,
    prediction_path: str,
    prediction_csv_path: Path,
    trades_path: str,
    trades_csv_path: Path,
    monthly_csv_path: Path,
    side_csv_path: Path,
) -> RangeArchiveReport:
    pnls = [float(trade.get("cash_pnl", 0.0)) for trade in trades]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    balances = [float(args.initial_capital), *[float(trade.get("balance", 0.0)) for trade in trades]]
    final_balance = balances[-1]
    monthly_rows = summarize_monthly(trades)
    side_rows = summarize_side(trades)
    monthly_pnl = {str(row["month"]): float(row["cash_pnl"]) for row in monthly_rows}
    monthly_trades = {str(row["month"]): int(row["trades"]) for row in monthly_rows}
    side_pnl = {str(row["side"]): float(row["cash_pnl"]) for row in side_rows}
    side_trades = {str(row["side"]): int(row["trades"]) for row in side_rows}
    return RangeArchiveReport(
        model_id=args.model_id,
        model_version=version,
        model_path=str(model_path),
        record_path=str(record_path),
        tensor_path=str(tensor_path),
        meta_path=str(meta_path),
        flat_path=str(flat_path),
        tensor_shape=[int(value) for value in tensor_shape],
        eval_split=args.eval_split,
        selected_samples=int(selected_samples),
        evaluated_samples=int(evaluated_samples),
        evaluated_first_timestamp=first_timestamp,
        evaluated_last_timestamp=last_timestamp,
        range_source=range_source_used,
        range_bracket_mode=args.range_bracket_mode,
        range_fallback=args.range_fallback,
        trades=len(trades),
        buy_trades=side_trades.get("BUY", 0),
        sell_trades=side_trades.get("SELL", 0),
        wins=sum(1 for value in pnls if value > 0),
        losses=sum(1 for value in pnls if value < 0),
        win_rate=sum(1 for value in pnls if value > 0) / len(trades) if trades else 0.0,
        total_cash_pnl=sum(pnls),
        buy_cash_pnl=side_pnl.get("BUY", 0.0),
        sell_cash_pnl=side_pnl.get("SELL", 0.0),
        final_balance=final_balance,
        return_percent=(final_balance - float(args.initial_capital)) / float(args.initial_capital),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0),
        max_drawdown_cash=max_drawdown(balances),
        take_profits=sum(1 for trade in trades if trade.get("outcome") == "take_profit"),
        stop_losses=sum(1 for trade in trades if trade.get("outcome") == "stop_loss"),
        timeouts=sum(1 for trade in trades if trade.get("outcome") == "timeout"),
        skipped_by_model=int(counters.get("skipped_by_model", 0)),
        skipped_while_open=int(counters.get("skipped_while_open", 0)),
        skipped_range_unavailable=int(counters.get("skipped_range_unavailable", 0)),
        skipped_range_filter=int(counters.get("skipped_range_filter", 0)),
        invalid_bracket=int(counters.get("invalid_bracket", 0)),
        invalid_trade=int(counters.get("invalid_trade", 0)),
        monthly_pnl=monthly_pnl,
        monthly_trades=monthly_trades,
        side_pnl=side_pnl,
        side_trades=side_trades,
        positive_months=sum(1 for value in monthly_pnl.values() if value > 0),
        negative_months=sum(1 for value in monthly_pnl.values() if value < 0),
        buy_threshold=float(args.buy_threshold),
        sell_threshold=float(args.sell_threshold),
        min_margin=float(args.min_margin),
        top_threshold=float(args.top_threshold),
        bottom_threshold=float(args.bottom_threshold),
        min_buy_r=float(args.min_buy_r),
        min_sell_r=float(args.min_sell_r),
        min_range_4h_room=float(args.min_range_4h_room),
        min_range_1d_room=float(args.min_range_1d_room),
        min_tp_distance=float(args.min_tp_distance),
        min_sl_distance=float(args.min_sl_distance),
        max_tp_atr=float(args.max_tp_atr),
        max_sl_atr=float(args.max_sl_atr),
        hold_bars=int(args.hold_bars),
        spread_mode=args.spread_mode,
        spread_value=float(args.spread_value),
        same_bar_policy=args.same_bar_policy,
        output_json=str(output_dir / "latest.json"),
        output_html=str(output_dir / "latest.html"),
        output_predictions=prediction_path,
        output_predictions_csv=str(prediction_csv_path),
        output_trades=trades_path,
        output_trades_csv=str(trades_csv_path),
        output_monthly_csv=str(monthly_csv_path),
        output_side_csv=str(side_csv_path),
        production_status="BLOCKED — research range-aware sequence WaveNet archive only",
    )


def render_html(title: str, report: RangeArchiveReport) -> str:
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
<section class="hero"><h1>{html.escape(title)}</h1><p>Phase148A range-aware prediction/backtest archive. Research only.</p>
<div class="grid">
<div class="metric"><span>Final balance</span><strong>${report.final_balance:.2f}</strong></div>
<div class="metric"><span>Return</span><strong>{report.return_percent:.2%}</strong></div>
<div class="metric"><span>PF</span><strong>{report.profit_factor:.3f}</strong></div>
<div class="metric"><span>Trades</span><strong>{report.trades}</strong></div>
<div class="metric"><span>Max DD</span><strong>${report.max_drawdown_cash:.2f}</strong></div>
<div class="metric"><span>Range source</span><strong>{html.escape(report.range_source)}</strong></div>
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
        print("  PHASE148A RANGE-AWARE SEQUENCE WAVENET ARCHIVE")
        print("=" * 74)
        print(f"  tensor      : {tensor_path}")
        print(f"  meta        : {meta_path}")
        print(f"  flat        : {flat_path}")
        model_path, record_path, version = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["resolve_model_files"]
        ).resolve_model_files(args)
        record = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["load_record"]
        ).load_record(record_path)
        tf = require_tensorflow()
        x_all = np.load(tensor_path, mmap_mode="r")
        meta = __import__("backtest_pivot_pattern_sequence_wavenet", fromlist=["load_meta"]).load_meta(
            meta_path
        )
        load_model = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["load_model"]
        ).load_model
        model = load_model(model_path, record, meta, tuple(int(v) for v in x_all.shape[1:]))
        flat = pd.read_parquet(flat_path).reset_index(drop=True)
        selected_rows = selected_indices(int(x_all.shape[0]), int(args.max_samples))
        eval_rows, eval_name = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["eval_tensor_indices"]
        ).eval_tensor_indices(selected_rows, args)
        eval_rows = apply_max_windows(eval_rows, int(args.max_windows))
        sample_positions_all = np.asarray(meta["sample_indices"], dtype=np.int64)
        sample_positions = sample_positions_all[eval_rows]
        option_b = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["is_option_b_record"]
        ).is_option_b_record(record)
        make_predict_sequence = __import__(
            "backtest_pivot_pattern_sequence_wavenet", fromlist=["make_predict_sequence"]
        ).make_predict_sequence
        predictions = prediction_dict(
            model.predict(
                make_predict_sequence(tf, x_all, eval_rows, record, max(int(args.batch_size), 1), meta, option_b),
                verbose=0,
            )
        )
        range_context = model_context_if_needed(args, flat)
        action_prob = np.asarray(predictions["action"], dtype=np.float32)
        top_prob = np.asarray(predictions["top"], dtype=np.float32).reshape(-1)
        bottom_prob = np.asarray(predictions["bottom"], dtype=np.float32).reshape(-1)
        buy_r = np.asarray(predictions["buy_r"], dtype=np.float32).reshape(-1)
        sell_r = np.asarray(predictions["sell_r"], dtype=np.float32).reshape(-1)
        actions = selected_action(
            action_prob, float(args.buy_threshold), float(args.sell_threshold), float(args.min_margin)
        )
        balance = float(args.initial_capital)
        open_until = -1
        prediction_rows: list[dict[str, Any]] = []
        trades: list[dict[str, Any]] = []
        counters = {
            "skipped_by_model": 0,
            "skipped_while_open": 0,
            "skipped_range_unavailable": 0,
            "skipped_range_filter": 0,
            "invalid_bracket": 0,
            "invalid_trade": 0,
        }
        range_sources_seen: set[str] = set()
        for offset, row_id_raw in enumerate(sample_positions):
            row_id = int(row_id_raw)
            flat_row = flat.iloc[row_id]
            timestamp = str(flat_row.get("timestamp", ""))
            close = row_value(flat_row, "close", 0.0)
            side = int(actions[offset])
            decision_reason = "selected"
            opened_trade = 0
            range_record: dict[str, float] = {}
            range_source_used = "none"
            tp_distance = 0.0
            sl_distance = 0.0
            bracket_source = "none"
            if row_id <= open_until:
                counters["skipped_while_open"] += 1
                decision_reason = "while_open"
            elif side == ACTION_BUY and (
                bottom_prob[offset] < float(args.bottom_threshold) or buy_r[offset] < float(args.min_buy_r)
            ):
                counters["skipped_by_model"] += 1
                decision_reason = "buy_gate"
            elif side == ACTION_SELL and (
                top_prob[offset] < float(args.top_threshold) or sell_r[offset] < float(args.min_sell_r)
            ):
                counters["skipped_by_model"] += 1
                decision_reason = "sell_gate"
            elif side not in {ACTION_BUY, ACTION_SELL}:
                counters["skipped_by_model"] += 1
                decision_reason = "hold_or_none"
            else:
                try:
                    range_record, range_source_used = combined_range_record(flat_row, args, range_context)
                    range_sources_seen.add(range_source_used)
                except Exception:
                    range_record, range_source_used = {}, "error"
                if float(range_record.get("range_4h_available", 0.0)) < 0.5:
                    if args.range_fallback == "atr":
                        range_source_used = "atr_fallback"
                    else:
                        counters["skipped_range_unavailable"] += 1
                        decision_reason = "range_unavailable"
                if decision_reason == "selected" and range_source_used != "atr_fallback":
                    if not range_filter_pass(range_record, close, side, args):
                        counters["skipped_range_filter"] += 1
                        decision_reason = "range_filter"
                if decision_reason == "selected":
                    atr_value = row_value(flat_row, "h4_atr_for_risk", 0.0)
                    entry = entry_price_for_row(flat, row_id, side, args)
                    if entry is None or atr_value <= 0:
                        counters["invalid_trade"] += 1
                        decision_reason = "invalid_entry_or_atr"
                    else:
                        distances = None
                        if range_source_used == "atr_fallback":
                            atr_tp, atr_sl = atr_distances(atr_value, args)
                            distances = (atr_tp, atr_sl, "atr_fallback")
                        else:
                            distances = range_distances(range_record, side, entry, atr_value, args)
                            if distances is None and args.range_fallback == "atr":
                                atr_tp, atr_sl = atr_distances(atr_value, args)
                                distances = (atr_tp, atr_sl, "atr_fallback")
                        if distances is None:
                            counters["invalid_bracket"] += 1
                            decision_reason = "invalid_range_bracket"
                        else:
                            tp_distance, sl_distance, bracket_source = distances
                            path = trade_path(
                                flat,
                                row_id,
                                side,
                                tp_distance,
                                sl_distance,
                                int(args.hold_bars),
                                args,
                            )
                            if path is None:
                                counters["invalid_trade"] += 1
                                decision_reason = "invalid_trade_path"
                            else:
                                points, entry_row, exit_row, entry_price, tp, sl, exit_price, outcome = path
                                risk_amount = max(balance * float(args.risk_per_trade), 0.0)
                                quantity = risk_amount / sl_distance if sl_distance else 0.0
                                cash_pnl = float(points) * quantity
                                balance += cash_pnl
                                opened_trade = 1
                                trade = {
                                    "number": len(trades) + 1,
                                    "timestamp": timestamp,
                                    "side": "BUY" if side == ACTION_BUY else "SELL",
                                    "tensor_row": int(eval_rows[offset]),
                                    "sample_index": int(offset),
                                    "row_id": row_id,
                                    "entry_row_id": int(entry_row),
                                    "exit_row_id": int(exit_row),
                                    "entry": float(entry_price),
                                    "tp": float(tp),
                                    "sl": float(sl),
                                    "exit_price": float(exit_price),
                                    "tp_distance": float(tp_distance),
                                    "sl_distance": float(sl_distance),
                                    "points_pnl": float(points),
                                    "cash_pnl": float(cash_pnl),
                                    "balance": float(balance),
                                    "outcome": str(outcome),
                                    "bracket_source": bracket_source,
                                    "range_source": range_source_used,
                                    "range_4h_high_price": float(range_record.get("range_4h_high_price", 0.0)),
                                    "range_4h_low_price": float(range_record.get("range_4h_low_price", 0.0)),
                                    "range_1d_high_price": float(range_record.get("range_1d_high_price", 0.0)),
                                    "range_1d_low_price": float(range_record.get("range_1d_low_price", 0.0)),
                                    "action_sell_prob": float(action_prob[offset, 0]),
                                    "action_hold_prob": float(action_prob[offset, 1]),
                                    "action_buy_prob": float(action_prob[offset, 2]),
                                    "top_prob": float(top_prob[offset]),
                                    "bottom_prob": float(bottom_prob[offset]),
                                    "buy_r_pred": float(buy_r[offset]),
                                    "sell_r_pred": float(sell_r[offset]),
                                }
                                trades.append(trade)
                                open_until = max(open_until, int(exit_row))
                                decision_reason = "trade_opened"
                                if balance <= 0:
                                    break
            prediction_rows.append(
                {
                    "timestamp": timestamp,
                    "tensor_row": int(eval_rows[offset]),
                    "sample_index": int(offset),
                    "row_id": row_id,
                    "close": float(close),
                    "action_sell_prob": float(action_prob[offset, 0]),
                    "action_hold_prob": float(action_prob[offset, 1]),
                    "action_buy_prob": float(action_prob[offset, 2]),
                    "top_prob": float(top_prob[offset]),
                    "bottom_prob": float(bottom_prob[offset]),
                    "buy_r_pred": float(buy_r[offset]),
                    "sell_r_pred": float(sell_r[offset]),
                    "selected_action": selected_action_name(side),
                    "decision_reason": decision_reason,
                    "opened_trade": opened_trade,
                    "range_source": range_source_used,
                    "range_4h_available": float(range_record.get("range_4h_available", 0.0)),
                    "range_1d_available": float(range_record.get("range_1d_available", 0.0)),
                    "range_4h_high_price": float(range_record.get("range_4h_high_price", 0.0)),
                    "range_4h_low_price": float(range_record.get("range_4h_low_price", 0.0)),
                    "range_4h_up_room": float(range_record.get("range_4h_up_room", 0.0)),
                    "range_4h_down_room": float(range_record.get("range_4h_down_room", 0.0)),
                    "range_1d_high_price": float(range_record.get("range_1d_high_price", 0.0)),
                    "range_1d_low_price": float(range_record.get("range_1d_low_price", 0.0)),
                    "range_1d_up_room": float(range_record.get("range_1d_up_room", 0.0)),
                    "range_1d_down_room": float(range_record.get("range_1d_down_room", 0.0)),
                    "tp_distance": float(tp_distance),
                    "sl_distance": float(sl_distance),
                    "bracket_source": bracket_source,
                }
            )
        prediction_frame = pd.DataFrame(prediction_rows)
        trade_frame = pd.DataFrame(trades)
        monthly_rows = summarize_monthly(trades)
        side_rows = summarize_side(trades)
        output_prediction_parquet = output_dir / "latest_predictions.parquet"
        output_prediction_csv = output_dir / "latest_predictions.csv"
        output_trade_parquet = output_dir / "latest_trades.parquet"
        output_trade_csv = output_dir / "latest_trades.csv"
        output_monthly_csv = output_dir / "latest_monthly.csv"
        output_side_csv = output_dir / "latest_side.csv"
        prediction_path = write_frame_archive(
            prediction_frame, output_prediction_parquet, output_prediction_csv
        )
        trades_path = write_frame_archive(trade_frame, output_trade_parquet, output_trade_csv)
        write_csv(output_monthly_csv, monthly_rows)
        write_csv(output_side_csv, side_rows)
        first_time = str(flat.iloc[int(sample_positions[0])].get("timestamp", ""))
        last_time = str(flat.iloc[int(sample_positions[-1])].get("timestamp", ""))
        report = build_report(
            args,
            model_path,
            record_path,
            version,
            tensor_path,
            meta_path,
            flat_path,
            x_all.shape,
            len(selected_rows),
            len(eval_rows),
            first_time,
            last_time,
            "+".join(sorted(range_sources_seen)) if range_sources_seen else args.range_source,
            trades,
            counters,
            output_dir,
            prediction_path,
            output_prediction_csv,
            trades_path,
            output_trade_csv,
            output_monthly_csv,
            output_side_csv,
        )
        Path(report.output_html).write_text(render_html(args.report_title, report), encoding="utf-8")
        payload = {
            "args": vars(args),
            "report": asdict(report),
            "trades_preview": trades[:250],
            "files": {
                "json": report.output_json,
                "html": report.output_html,
                "predictions": report.output_predictions,
                "predictions_csv": report.output_predictions_csv,
                "trades": report.output_trades,
                "trades_csv": report.output_trades_csv,
                "monthly_csv": report.output_monthly_csv,
                "side_csv": report.output_side_csv,
            },
        }
        Path(report.output_json).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  model       : {model_path}")
        print(f"  split       : {eval_name}")
        print(f"  evaluated   : {report.evaluated_samples:,}")
        print(f"  range       : {report.range_source} / {report.range_bracket_mode}")
        print(f"  trades      : {report.trades:,}")
        print(f"  final       : ${report.final_balance:.2f}")
        print(f"  return      : {report.return_percent:.2%}")
        print(f"  PF          : {report.profit_factor:.3f}")
        print(f"  predictions : {report.output_predictions}")
        print(f"  trades csv  : {report.output_trades_csv}")
        print(f"  report      : {report.output_json}")
        print(f"  elapsed     : {time.monotonic() - started:.1f}s")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
