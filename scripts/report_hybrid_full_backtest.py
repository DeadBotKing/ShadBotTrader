"""Full-history fixed-threshold report for the hybrid range-aware backtest.

This Phase 116 companion script does not search thresholds. It loads the saved
Phase 125 threshold, evaluates the hybrid head over every selected 5M matrix row,
simulates the same 4H/1D range TP/SL logic used by Phase 125, and writes an HTML
report that the dashboard/operator can open.
"""

# ruff: noqa: E402,E501

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
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
from backtest_hybrid_xgboost_head import (
    CLASS_NAMES,
    TradeResult,
    aligned_predict_proba,
    decide_action,
    default_matrix_path,
    eval_slice_indices,
    load_candles,
    load_head,
    max_drawdown,
    range_filter_pass,
    safe_div,
    simulate_trade,
)

from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue, ModelRecord

DEFAULT_STORAGE = REPO_ROOT / "datasets"
DEFAULT_OUTPUT_DIR = Path("run_logs/hybrid_full_backtest")


@dataclass(frozen=True)
class ThresholdSpec:
    buy_threshold: float
    sell_threshold: float
    min_margin: float
    source: str


@dataclass(frozen=True)
class DetailedTrade:
    number: int
    timestamp: str
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
    equity: float
    label: str
    label_correct: int


@dataclass(frozen=True)
class FixedBacktestSummary:
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


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    trades: int
    wins: int
    losses: int
    total_pnl: float
    profit_factor: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an HTML report for the fixed-threshold hybrid 5M backtest.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument(
        "--source-mode",
        choices=("matrix", "stream"),
        default="matrix",
        help="matrix = read an existing hybrid matrix; stream = build/evaluate rows in chunks.",
    )
    parser.add_argument("--matrix-path", default="")
    parser.add_argument("--model-id", default="gold_hybrid_lightgbm_head_5m")
    parser.add_argument("--model-version", type=int, default=0, help="0 = latest")
    parser.add_argument("--eval-frac", type=float, default=1.0)
    parser.add_argument("--max-windows", type=int, default=0, help="0 = all selected rows")
    parser.add_argument("--window", type=int, default=288)
    parser.add_argument("--label-horizon", type=int, default=288)
    parser.add_argument("--atr-mult", type=float, default=0.5)
    parser.add_argument("--train-ratio", type=float, default=80.0)
    parser.add_argument(
        "--stream-scope",
        choices=("all", "holdout", "last-fold", "auto"),
        default="all",
        help="Scope used only by --source-mode stream.",
    )
    parser.add_argument("--stream-chunk-size", type=int, default=2000)
    parser.add_argument(
        "--stream-wavenet",
        choices=("neutral", "batch"),
        default="neutral",
        help="neutral is memory-safe; batch runs WaveNet in small chunks if installed.",
    )
    parser.add_argument("--booster", default="lightgbm")
    parser.add_argument("--summary-mode", default="basic")
    parser.add_argument("--include-specialists", choices=("0", "1"), default="1")
    parser.add_argument("--include-multiclass-booster", choices=("0", "1"), default="1")
    parser.add_argument("--include-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--require-wavenet", choices=("0", "1"), default="0")
    parser.add_argument("--buy-model-id", default="")
    parser.add_argument("--sell-model-id", default="")
    parser.add_argument("--multiclass-model-id", default="")
    parser.add_argument("--wavenet-model-id", default="gold_trend_signal_5m")
    parser.add_argument("--range-1d-model-id", default="gold_range_1d")
    parser.add_argument("--range-4h-model-id", default="gold_range_4h")
    parser.add_argument("--buy-model-version", type=int, default=0)
    parser.add_argument("--sell-model-version", type=int, default=0)
    parser.add_argument("--multiclass-model-version", type=int, default=0)
    parser.add_argument("--wavenet-model-version", type=int, default=0)
    parser.add_argument("--range-1d-version", type=int, default=0)
    parser.add_argument("--range-4h-version", type=int, default=0)
    parser.add_argument("--buy-threshold", type=float, default=-1.0)
    parser.add_argument("--sell-threshold", type=float, default=-1.0)
    parser.add_argument("--min-margin", type=float, default=-1.0)
    parser.add_argument("--max-hold-bars", type=int, default=48)
    parser.add_argument("--min-4h-room", type=float, default=2.0)
    parser.add_argument("--min-1d-room", type=float, default=5.0)
    parser.add_argument("--min-tp-distance", type=float, default=2.0)
    parser.add_argument("--min-sl-distance", type=float, default=2.0)
    parser.add_argument("--spread-mode", choices=("pct", "fixed"), default="pct")
    parser.add_argument("--spread-value", type=float, default=0.06)
    parser.add_argument("--slippage", type=float, default=0.0)
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument(
        "--units",
        type=float,
        default=1.0,
        help="Cash PnL multiplier; 1 means one XAUUSD price-dollar move = $1 PnL.",
    )
    parser.add_argument(
        "--same-bar-policy", choices=("stop_first", "tp_first"), default="stop_first"
    )
    parser.add_argument("--storage-root", default=str(DEFAULT_STORAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--report-title",
        default="Hybrid range-aware full 5M backtest",
    )
    return parser.parse_args(argv)


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def load_record(storage_root: Path, model_id: str, version: int) -> tuple[ModelRecord, int]:
    catalogue = ModelCatalogue(storage_root)
    resolved = version if version > 0 else catalogue.latest_version(model_id)
    if resolved < 1:
        raise RuntimeError(f"No saved model record found for {model_id}")
    record = catalogue.read(model_id, resolved)
    if record is None:
        raise RuntimeError(f"No model record found for {model_id} v{resolved}")
    return record, resolved


def resolve_thresholds(args: argparse.Namespace, record: ModelRecord) -> ThresholdSpec:
    buy = _finite_or_none(args.buy_threshold)
    sell = _finite_or_none(args.sell_threshold)
    margin = _finite_or_none(args.min_margin)
    if buy is not None and sell is not None and buy >= 0 and sell >= 0:
        return ThresholdSpec(buy, sell, max(0.0, margin or 0.0), "cli")

    stored = record.decision_thresholds or {}
    buy = _finite_or_none(stored.get("buy_prob"))
    sell = _finite_or_none(stored.get("sell_prob"))
    stored_margin = _finite_or_none(stored.get("min_margin"))
    if buy is None or sell is None:
        raise RuntimeError(
            f"Model {record.model_id} v{record.version} has no saved decision_thresholds. "
            "Run Phase125 with --save-record 1 first."
        )
    return ThresholdSpec(
        buy_threshold=buy,
        sell_threshold=sell,
        min_margin=max(0.0, stored_margin if margin is None or margin < 0 else margin),
        source=f"model_record:{record.model_id}:v{record.version}",
    )


def evaluate_fixed_thresholds(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    candles: Sequence[Any],
    args: argparse.Namespace,
    thresholds: ThresholdSpec,
) -> tuple[FixedBacktestSummary, list[DetailedTrade]]:
    trades: list[TradeResult] = []
    detailed: list[DetailedTrade] = []
    no_trade = ambiguous = invalid_range = invalid_bracket = 0
    for offset, (row_index, row) in enumerate(frame.iterrows()):
        decision = decide_action(
            probabilities[offset],
            thresholds.buy_threshold,
            thresholds.sell_threshold,
            thresholds.min_margin,
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
        equity = sum(item.pnl for item in trades)
        detailed.append(_detail_trade(len(detailed) + 1, str(row["timestamp"]), trade, equity))
        if len(detailed) and len(detailed) % 1000 == 0:
            print(f"  trades      : {len(detailed):,} processed up to matrix row {row_index}")

    summary = summarise(frame, trades, no_trade, ambiguous, invalid_range, invalid_bracket)
    return summary, detailed


def _detail_trade(number: int, timestamp: str, trade: TradeResult, equity: float) -> DetailedTrade:
    return DetailedTrade(
        number=number,
        timestamp=timestamp,
        side=trade.side,
        row_index=trade.row_index,
        source_index=trade.source_index,
        entry_index=trade.entry_index,
        exit_index=trade.exit_index,
        entry=trade.entry,
        tp=trade.tp,
        sl=trade.sl,
        exit_price=trade.exit_price,
        outcome=trade.outcome,
        pnl=trade.pnl,
        equity=equity,
        label=CLASS_NAMES.get(trade.label, str(trade.label)),
        label_correct=int(trade.label_correct),
    )


def summarise_counts(
    samples: int,
    trades: Sequence[TradeResult],
    no_trade: int,
    ambiguous: int,
    invalid_range: int,
    invalid_bracket: int,
) -> FixedBacktestSummary:
    pnls = [trade.pnl for trade in trades]
    gross_profit = sum(pnl for pnl in pnls if pnl > 0)
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
    wins = sum(1 for trade in trades if trade.pnl > 0)
    losses = sum(1 for trade in trades if trade.pnl < 0)
    label_correct = sum(1 for trade in trades if trade.label_correct)
    total = sum(pnls)
    return FixedBacktestSummary(
        samples=samples,
        trades=len(trades),
        buy_trades=sum(1 for trade in trades if trade.side == "BUY"),
        sell_trades=sum(1 for trade in trades if trade.side == "SELL"),
        wins=wins,
        losses=losses,
        timeouts=sum(1 for trade in trades if trade.outcome == "timeout"),
        label_correct=label_correct,
        false_positive=len(trades) - label_correct,
        no_trade=no_trade,
        ambiguous=ambiguous,
        invalid_range=invalid_range,
        invalid_bracket=invalid_bracket,
        win_rate=safe_div(wins, len(trades)),
        label_precision=safe_div(label_correct, len(trades)),
        total_pnl=total,
        avg_pnl=safe_div(total, len(trades)),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=(
            safe_div(gross_profit, gross_loss) if gross_loss else (999.0 if gross_profit else 0.0)
        ),
        max_drawdown=max_drawdown(pnls),
        coverage=safe_div(len(trades), samples),
    )


def summarise(
    frame: pd.DataFrame,
    trades: Sequence[TradeResult],
    no_trade: int,
    ambiguous: int,
    invalid_range: int,
    invalid_bracket: int,
) -> FixedBacktestSummary:
    return summarise_counts(len(frame), trades, no_trade, ambiguous, invalid_range, invalid_bracket)


def monthly_summary(trades: Sequence[DetailedTrade]) -> list[MonthlySummary]:
    buckets: dict[str, list[DetailedTrade]] = {}
    for trade in trades:
        month = str(pd.to_datetime(trade.timestamp, utc=True).to_period("M"))
        buckets.setdefault(month, []).append(trade)
    rows: list[MonthlySummary] = []
    for month, items in sorted(buckets.items()):
        pnls = [item.pnl for item in items]
        gross_profit = sum(pnl for pnl in pnls if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0))
        rows.append(
            MonthlySummary(
                month=month,
                trades=len(items),
                wins=sum(1 for item in items if item.pnl > 0),
                losses=sum(1 for item in items if item.pnl < 0),
                total_pnl=sum(pnls),
                profit_factor=(
                    safe_div(gross_profit, gross_loss)
                    if gross_loss
                    else (999.0 if gross_profit else 0.0)
                ),
            )
        )
    return rows


def write_csv(path: Path, rows: Sequence[DetailedTrade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def account_summary(
    summary: FixedBacktestSummary, initial_capital: float, units: float
) -> dict[str, Any]:
    multiplier = max(float(units), 0.0)
    initial = float(initial_capital)
    final = initial + summary.total_pnl * multiplier
    max_drawdown_cash = summary.max_drawdown * multiplier
    return {
        "initial_capital": initial,
        "units": multiplier,
        "final_balance": final,
        "net_profit": final - initial,
        "return_percent": safe_div(final - initial, initial),
        "max_drawdown_cash": max_drawdown_cash,
        "would_breach_zero": initial - max_drawdown_cash <= 0,
        "note": "final_balance = initial_capital + total_pnl * units; margin calls are not simulated",
    }


def replay_candles_for_indices(
    candles: Sequence[Any], source_indices: Sequence[int], trades: Sequence[DetailedTrade]
) -> list[dict[str, Any]]:
    if not source_indices:
        return []
    first = min(source_indices)
    last = max(source_indices)
    if trades:
        first = min(
            first, *(trade.entry_index for trade in trades), *(trade.exit_index for trade in trades)
        )
        last = max(
            last, *(trade.entry_index for trade in trades), *(trade.exit_index for trade in trades)
        )
    first = max(0, first - 20)
    last = min(len(candles) - 1, last + 20)
    rows: list[dict[str, Any]] = []
    for index in range(first, last + 1):
        candle = candles[index]
        rows.append(
            {
                "index": index,
                "time": str(candle.open_time.value),
                "open": float(candle.open.amount),
                "high": float(candle.high.amount),
                "low": float(candle.low.amount),
                "close": float(candle.close.amount),
            }
        )
    return rows


def replay_candles(
    candles: Sequence[Any], frame: pd.DataFrame, trades: Sequence[DetailedTrade]
) -> list[dict[str, Any]]:
    if len(frame) == 0:
        return []
    source_indices = [int(value) for value in frame["source_index"].tolist()]
    return replay_candles_for_indices(candles, source_indices, trades)


def replay_trade_payload(
    trades: Sequence[DetailedTrade], initial_capital: float, units: float
) -> list[dict[str, Any]]:
    initial = float(initial_capital)
    multiplier = max(float(units), 0.0)
    return [
        {
            **asdict(trade),
            "cash_pnl": trade.pnl * multiplier,
            "balance_after": initial + trade.equity * multiplier,
        }
        for trade in trades
    ]


def equity_svg(trades: Sequence[DetailedTrade], width: int = 920, height: int = 260) -> str:
    values = [0.0, *[trade.equity for trade in trades]]
    if len(values) == 1:
        values.append(0.0)
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-9:
        low -= 1.0
        high += 1.0
    pad = 18
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    points = []
    for index, value in enumerate(values):
        x = pad + inner_w * index / max(len(values) - 1, 1)
        y = pad + inner_h * (high - value) / (high - low)
        points.append(f"{x:.2f},{y:.2f}")
    zero_y = pad + inner_h * (high - 0.0) / (high - low)
    color = "#16a34a" if values[-1] >= 0 else "#dc2626"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        'role="img" aria-label="equity curve">'
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="12" fill="#0f172a" />'
        f'<line x1="{pad}" y1="{zero_y:.2f}" x2="{width-pad}" y2="{zero_y:.2f}" '
        'stroke="#64748b" stroke-width="1" stroke-dasharray="4 4" />'
        f'<polyline fill="none" stroke="{color}" stroke-width="3" '
        f'points="{" ".join(points)}" />'
        f'<text x="{pad}" y="16" fill="#cbd5e1" font-size="12">max {high:.2f}</text>'
        f'<text x="{pad}" y="{height - 6}" fill="#cbd5e1" font-size="12">min {low:.2f}</text>'
        "</svg>"
    )


REPLAY_JS = r"""
(function () {
  const dataEl = document.getElementById('replay-data');
  const slider = document.getElementById('replay-slider');
  const info = document.getElementById('replay-info');
  const chart = document.getElementById('replay-chart');
  if (!dataEl || !slider || !info || !chart) return;
  let data = {};
  try {
    data = JSON.parse(dataEl.textContent || '{}');
  } catch (error) {
    info.textContent = 'Replay JSON parse failed: ' + error.message;
    chart.innerHTML = '<rect x="0" y="0" width="980" height="390" rx="12" fill="#020617"/><text x="26" y="40" fill="#ef4444" font-size="14">Replay JSON parse failed</text>';
    return;
  }
  const candles = data.candles || [];
  const trades = data.trades || [];
  if (candles.length === 0) {
    info.textContent = 'No replay candles were written.';
    chart.innerHTML = '<rect x="0" y="0" width="980" height="390" rx="12" fill="#020617"/><text x="26" y="40" fill="#facc15" font-size="14">No candles in replay data</text>';
    return;
  }
  slider.max = String(candles.length - 1);
  slider.value = '0';

  function fmt(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return 'n/a';
    return Number(value).toFixed(digits);
  }
  function balanceAt(globalIndex) {
    let balance = Number(data.initial_capital || 0);
    for (const trade of trades) {
      if (Number(trade.exit_index) <= globalIndex) balance += Number(trade.cash_pnl || 0);
    }
    return balance;
  }
  function activeTrade(globalIndex) {
    for (const trade of trades) {
      if (Number(trade.entry_index) <= globalIndex && globalIndex <= Number(trade.exit_index)) {
        return trade;
      }
    }
    return null;
  }
  function tradesInView(first, last) {
    return trades.filter(t => Number(t.entry_index) <= last && Number(t.exit_index) >= first);
  }
  function yFor(price, low, high, pad, innerH) {
    return pad + innerH * (high - price) / Math.max(high - low, 0.000001);
  }
  function render() {
    const pos = Number(slider.value || 0);
    const candle = candles[pos];
    const globalIndex = Number(candle.index);
    const start = Math.max(0, pos - 70);
    const end = Math.min(candles.length - 1, pos + 20);
    const view = candles.slice(start, end + 1);
    const firstGlobal = Number(view[0].index);
    const lastGlobal = Number(view[view.length - 1].index);
    const viewTrades = tradesInView(firstGlobal, lastGlobal);
    let low = Math.min(...view.map(c => Number(c.low)));
    let high = Math.max(...view.map(c => Number(c.high)));
    for (const trade of viewTrades) {
      low = Math.min(low, Number(trade.tp), Number(trade.sl), Number(trade.entry));
      high = Math.max(high, Number(trade.tp), Number(trade.sl), Number(trade.entry));
    }
    const pad = 26, width = 980, height = 390;
    const innerW = width - 2 * pad, innerH = height - 2 * pad;
    const step = innerW / Math.max(view.length, 1);
    let svg = `<rect x="0" y="0" width="${width}" height="${height}" rx="12" fill="#020617"/>`;
    svg += `<text x="${pad}" y="18" fill="#cbd5e1" font-size="12">${fmt(high,2)}</text>`;
    svg += `<text x="${pad}" y="${height - 8}" fill="#cbd5e1" font-size="12">${fmt(low,2)}</text>`;
    for (let i = 0; i < view.length; i++) {
      const c = view[i];
      const x = pad + i * step + step / 2;
      const o = Number(c.open), h = Number(c.high), l = Number(c.low), cl = Number(c.close);
      const up = cl >= o;
      const color = up ? '#22c55e' : '#ef4444';
      const yH = yFor(h, low, high, pad, innerH);
      const yL = yFor(l, low, high, pad, innerH);
      const yO = yFor(o, low, high, pad, innerH);
      const yC = yFor(cl, low, high, pad, innerH);
      svg += `<line x1="${x}" y1="${yH}" x2="${x}" y2="${yL}" stroke="${color}" stroke-width="1"/>`;
      svg += `<rect x="${x - Math.max(step * 0.28, 1)}" y="${Math.min(yO,yC)}" width="${Math.max(step * 0.56, 2)}" height="${Math.max(Math.abs(yC-yO), 2)}" fill="${color}" opacity="0.85"/>`;
    }
    const currentX = pad + (pos - start) * step + step / 2;
    svg += `<line x1="${currentX}" y1="${pad}" x2="${currentX}" y2="${height - pad}" stroke="#38bdf8" stroke-width="2"/>`;
    const active = activeTrade(globalIndex);
    if (active) {
      const yTP = yFor(Number(active.tp), low, high, pad, innerH);
      const ySL = yFor(Number(active.sl), low, high, pad, innerH);
      const yEntry = yFor(Number(active.entry), low, high, pad, innerH);
      svg += `<line x1="${pad}" y1="${yTP}" x2="${width-pad}" y2="${yTP}" stroke="#22c55e" stroke-width="2" stroke-dasharray="6 4"/>`;
      svg += `<line x1="${pad}" y1="${ySL}" x2="${width-pad}" y2="${ySL}" stroke="#ef4444" stroke-width="2" stroke-dasharray="6 4"/>`;
      svg += `<line x1="${pad}" y1="${yEntry}" x2="${width-pad}" y2="${yEntry}" stroke="#facc15" stroke-width="2" stroke-dasharray="4 3"/>`;
    }
    for (const trade of viewTrades) {
      const entryOffset = candles.findIndex(c => Number(c.index) === Number(trade.entry_index));
      const exitOffset = candles.findIndex(c => Number(c.index) === Number(trade.exit_index));
      if (entryOffset >= start && entryOffset <= end) {
        const x = pad + (entryOffset - start) * step + step / 2;
        const y = yFor(Number(trade.entry), low, high, pad, innerH);
        const color = trade.side === 'BUY' ? '#22c55e' : '#ef4444';
        svg += `<circle cx="${x}" cy="${y}" r="5" fill="${color}" stroke="#fff" stroke-width="1"/>`;
      }
      if (exitOffset >= start && exitOffset <= end) {
        const x = pad + (exitOffset - start) * step + step / 2;
        const y = yFor(Number(trade.exit_price), low, high, pad, innerH);
        svg += `<rect x="${x-4}" y="${y-4}" width="8" height="8" fill="#e2e8f0"/>`;
      }
    }
    chart.innerHTML = svg;
    const bal = balanceAt(globalIndex);
    info.innerHTML = `
      <b>bar</b> ${globalIndex} · ${candle.time}<br/>
      OHLC: ${fmt(candle.open,2)} / ${fmt(candle.high,2)} / ${fmt(candle.low,2)} / ${fmt(candle.close,2)}<br/>
      <b>balance after closed trades</b>: $${fmt(bal,2)}
      ${active ? `<br/><b>active trade</b>: #${active.number} ${active.side} entry ${fmt(active.entry,2)} TP ${fmt(active.tp,2)} SL ${fmt(active.sl,2)} exit ${active.outcome} pnl $${fmt(active.cash_pnl,2)}` : '<br/>active trade: none'}
    `;
  }
  slider.addEventListener('input', render);
  const prev = document.getElementById('replay-prev');
  const next = document.getElementById('replay-next');
  if (prev) {
    prev.addEventListener('click', function () {
      slider.value = String(Math.max(0, Number(slider.value) - 1));
      render();
    });
  }
  if (next) {
    next.addEventListener('click', function () {
      slider.value = String(Math.min(candles.length - 1, Number(slider.value) + 1));
      render();
    });
  }
  render();
})();
"""


def script_json(payload: Mapping[str, Any]) -> str:
    """JSON safe for embedding inside a raw ``<script>`` block."""

    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def render_html(
    title: str,
    args: argparse.Namespace,
    matrix_path: Path,
    model_version: int,
    thresholds: ThresholdSpec,
    summary: FixedBacktestSummary,
    trades: Sequence[DetailedTrade],
    monthly: Sequence[MonthlySummary],
    candle_rows: Sequence[dict[str, Any]] = (),
) -> str:
    account = account_summary(summary, args.initial_capital, args.units)
    cards = [
        ("Samples", f"{summary.samples:,}"),
        ("Trades", f"{summary.trades:,}"),
        ("BUY / SELL", f"{summary.buy_trades:,} / {summary.sell_trades:,}"),
        ("Total PnL", f"{summary.total_pnl:+.2f}"),
        ("Initial / Final", f"${account['initial_capital']:.2f} → ${account['final_balance']:.2f}"),
        ("Return", f"{account['return_percent']:.2%}"),
        ("Units", f"{account['units']:.4g}"),
        ("Profit factor", f"{summary.profit_factor:.3f}"),
        ("Win rate", f"{summary.win_rate:.2%}"),
        ("Label precision", f"{summary.label_precision:.2%}"),
        ("Max drawdown", f"{summary.max_drawdown:.2f}"),
        ("Coverage", f"{summary.coverage:.2%}"),
    ]
    cards_html = "".join(
        f'<section class="card"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></section>'
        for label, value in cards
    )
    monthly_html = "".join(
        "<tr>"
        f"<td>{html.escape(row.month)}</td>"
        f"<td>{row.trades:,}</td>"
        f"<td>{row.wins:,}</td>"
        f"<td>{row.losses:,}</td>"
        f"<td>{row.total_pnl:+.2f}</td>"
        f"<td>{row.profit_factor:.3f}</td>"
        "</tr>"
        for row in monthly
    )
    recent_html = "".join(
        "<tr>"
        f"<td>{trade.number}</td>"
        f"<td>{html.escape(trade.timestamp)}</td>"
        f"<td>{html.escape(trade.side)}</td>"
        f"<td>{trade.entry:.2f}</td>"
        f"<td>{trade.tp:.2f}</td>"
        f"<td>{trade.sl:.2f}</td>"
        f"<td>{html.escape(trade.outcome)}</td>"
        f"<td>{trade.pnl:+.2f}</td>"
        f"<td>{trade.equity:+.2f}</td>"
        "</tr>"
        for trade in trades[-80:]
    )
    warning = (
        "این گزارش fixed-threshold است، نه جستجوی threshold. اگر matrix شامل دورهٔ "
        "training باشد، این full-history diagnostic است و جایگزین out-of-sample نیست."
    )
    account_note = (
        "هشدار سرمایه: با units=1، max drawdown cash از سرمایه اولیه بیشتر می‌شود؛ "
        "در اجرای واقعی باید size کوچک‌تر یا risk sizing داشته باشیم."
        if account["would_breach_zero"]
        else "Capital check: simulated closed-balance did not breach zero with this units setting."
    )
    replay_data = {
        "candles": list(candle_rows),
        "trades": replay_trade_payload(trades, args.initial_capital, args.units),
        **account,
    }
    replay_section = f"""
<section class="panel">
<h2>Replay کندل‌به‌کندل</h2>
<p class="meta">دایره = ورود، مربع = خروج، خط زرد = entry، خط سبز = TP، خط قرمز = SL.</p>
<div class="replay-bar">
  <button id="replay-prev" type="button">◀ قبلی</button>
  <input id="replay-slider" type="range" min="0" value="0" />
  <button id="replay-next" type="button">بعدی ▶</button>
</div>
<div id="replay-info" class="replay-info"></div>
<svg id="replay-chart" viewBox="0 0 980 390" width="100%" height="390" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="980" height="390" rx="12" fill="#020617"/><text x="26" y="40" fill="#cbd5e1" font-size="14">Loading replay...</text></svg>
<script id="replay-data" type="application/json">{script_json(replay_data)}</script>
<script>{REPLAY_JS}</script>
</section>
"""
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: dark; --bg:#020617; --panel:#0f172a; --muted:#94a3b8; --text:#e2e8f0; --accent:#38bdf8; --good:#22c55e; --bad:#ef4444; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: Tahoma, Arial, sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
h1 {{ margin: 0 0 8px; font-size: 28px; }}
.meta, .warning {{ color: var(--muted); margin: 8px 0 18px; }}
.warning {{ border: 1px solid #f59e0b; color:#fde68a; border-radius:12px; padding:12px; background:#451a03; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin:20px 0; }}
.card {{ background:var(--panel); border:1px solid #1e293b; border-radius:14px; padding:14px; }}
.card span {{ display:block; color:var(--muted); font-size:12px; }}
.card strong {{ display:block; direction:ltr; text-align:left; font-size:22px; margin-top:6px; }}
.panel {{ background:var(--panel); border:1px solid #1e293b; border-radius:14px; padding:18px; margin:18px 0; overflow:auto; }}
pre {{ direction:ltr; text-align:left; color:#cbd5e1; white-space:pre-wrap; }}
table {{ width:100%; border-collapse:collapse; direction:ltr; text-align:left; font-size:13px; }}
th, td {{ padding:8px 10px; border-bottom:1px solid #1e293b; }}
th {{ color:#bae6fd; position:sticky; top:0; background:#0f172a; }}
.positive {{ color:var(--good); }} .negative {{ color:var(--bad); }}
.replay-bar {{ display:flex; gap:10px; align-items:center; direction:ltr; }}
.replay-bar input {{ flex:1; }}
.replay-bar button {{ background:#1e293b; color:var(--text); border:1px solid #334155; border-radius:8px; padding:8px 12px; }}
.replay-info {{ direction:ltr; text-align:left; background:#020617; border:1px solid #1e293b; border-radius:10px; padding:10px; margin:12px 0; color:#cbd5e1; }}
</style>
</head>
<body>
<main>
<h1>{html.escape(title)}</h1>
<p class="meta">Generated for {html.escape(args.symbol)} {html.escape(args.timeframe)} · model v{model_version} · matrix: {html.escape(str(matrix_path))}</p>
<p class="warning">{html.escape(warning)}</p>
<p class="warning">{html.escape(account_note)}</p>
<div class="grid">{cards_html}</div>
<section class="panel">
<h2>Equity curve</h2>
{equity_svg(trades)}
</section>
{replay_section}
<section class="panel">
<h2>Threshold / config</h2>
<pre>{html.escape(json.dumps({"thresholds": asdict(thresholds), "config": {"max_hold_bars": args.max_hold_bars, "min_4h_room": args.min_4h_room, "min_1d_room": args.min_1d_room, "min_tp_distance": args.min_tp_distance, "min_sl_distance": args.min_sl_distance, "spread_mode": args.spread_mode, "spread_value": args.spread_value, "slippage": args.slippage, "same_bar_policy": args.same_bar_policy}}, indent=2, ensure_ascii=False))}</pre>
</section>
<section class="panel">
<h2>Monthly breakdown</h2>
<table><thead><tr><th>month</th><th>trades</th><th>wins</th><th>losses</th><th>total pnl</th><th>PF</th></tr></thead><tbody>{monthly_html}</tbody></table>
</section>
<section class="panel">
<h2>Recent trades آخرین ۸۰ معامله</h2>
<table><thead><tr><th>#</th><th>timestamp</th><th>side</th><th>entry</th><th>TP</th><th>SL</th><th>outcome</th><th>pnl</th><th>equity</th></tr></thead><tbody>{recent_html}</tbody></table>
</section>
</main>
</body>
</html>
"""


def neutral_wavenet_features(frame: pd.DataFrame) -> None:
    frame["wavenet_sell_prob"] = 1.0 / 3.0
    frame["wavenet_hold_prob"] = 1.0 / 3.0
    frame["wavenet_buy_prob"] = 1.0 / 3.0
    frame["wavenet_action_margin"] = 0.0
    frame["wavenet_entropy"] = 1.0


def entropy3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    probs = np.vstack([a, b, c]).T.astype(np.float64)
    probs = np.clip(probs, 1e-12, 1.0)
    return -np.sum(probs * np.log(probs), axis=1) / np.log(3.0)


def add_entropy_columns(frame: pd.DataFrame) -> None:
    if {"booster_sell_prob", "booster_hold_prob", "booster_buy_prob"}.issubset(frame.columns):
        frame["booster_entropy"] = entropy3(
            frame["booster_sell_prob"].to_numpy(),
            frame["booster_hold_prob"].to_numpy(),
            frame["booster_buy_prob"].to_numpy(),
        )
    if {"wavenet_sell_prob", "wavenet_hold_prob", "wavenet_buy_prob"}.issubset(frame.columns):
        frame["wavenet_entropy"] = entropy3(
            frame["wavenet_sell_prob"].to_numpy(),
            frame["wavenet_hold_prob"].to_numpy(),
            frame["wavenet_buy_prob"].to_numpy(),
        )


def fill_missing_model_features(frame: pd.DataFrame, features: Sequence[str]) -> None:
    defaults = {
        "wavenet_sell_prob": 1.0 / 3.0,
        "wavenet_hold_prob": 1.0 / 3.0,
        "wavenet_buy_prob": 1.0 / 3.0,
        "wavenet_action_margin": 0.0,
        "wavenet_entropy": 1.0,
    }
    for feature in features:
        if feature not in frame.columns:
            frame[feature] = defaults.get(feature, 0.0)


def select_stream_positions(
    args: argparse.Namespace, dataset: Any, candles_count: int
) -> list[int]:
    from build_hybrid_xgboost_matrix import selected_positions

    stream_args = argparse.Namespace(**vars(args))
    stream_args.scope = args.stream_scope
    positions = selected_positions(stream_args, dataset, candles_count)
    if args.eval_frac < 1.0:
        indices = eval_slice_indices(len(positions), args.eval_frac, args.max_windows)
        return [positions[int(index)] for index in indices]
    if args.max_windows > 0:
        step = max(1, len(positions) // args.max_windows)
        return positions[::step][: args.max_windows]
    return positions


def build_stream_chunk(
    args: argparse.Namespace,
    dataset: Any,
    role: Any,
    signal_candles: Sequence[Any],
    positions: Sequence[int],
    range_1d_provider: Any,
    range_4h_provider: Any,
    features: Sequence[str],
    warnings: list[str],
) -> pd.DataFrame:
    from build_hybrid_xgboost_matrix import add_booster_features, add_wavenet_features

    from ShadBotTrader.infrastructure.ai.tabular_window_summary import summarise_windows

    sample_ends = [dataset.sample_ends[position] for position in positions]
    original_indices = [int(dataset.dropped_warmup) + int(sample_end) for sample_end in sample_ends]
    labels = [
        int(round(dataset.series[sample_end][dataset.target_columns[0]]))
        for sample_end in sample_ends
    ]
    timestamps = [str(signal_candles[index].open_time.value) for index in original_indices]
    closes = [float(signal_candles[index].close.amount) for index in original_indices]
    summary = summarise_windows(
        series=dataset.series,
        feature_count=dataset.feature_count,
        column_names=dataset.column_names,
        sample_ends=sample_ends,
        window_size=role.window_size,
        mode=args.summary_mode,
    )
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "source_index": original_indices,
            "sample_end": sample_ends,
            "label": labels,
            "close": closes,
        }
    )
    add_booster_features(frame, args, summary.values, warnings)
    if args.stream_wavenet == "batch":
        wavenet_args = argparse.Namespace(**vars(args))
        wavenet_args.include_wavenet = "1"
        wavenet_args.require_wavenet = "0"
        add_wavenet_features(frame, wavenet_args, dataset, positions, warnings)
    if "wavenet_sell_prob" not in frame.columns:
        neutral_wavenet_features(frame)

    range_rows = []
    for original_index in original_indices:
        candle = signal_candles[original_index]
        row = {}
        row.update(
            range_1d_provider.forecast_for_signal(
                candle.open_time.value, float(candle.close.amount)
            )
        )
        row.update(
            range_4h_provider.forecast_for_signal(
                candle.open_time.value, float(candle.close.amount)
            )
        )
        range_rows.append(row)
    range_frame = pd.DataFrame(range_rows).fillna(0.0)
    for column in range_frame.columns:
        frame[column] = range_frame[column].to_numpy(dtype=float)

    add_entropy_columns(frame)
    fill_missing_model_features(frame, features)
    return frame


def evaluate_stream_frame(
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    candles: Sequence[Any],
    args: argparse.Namespace,
    thresholds: ThresholdSpec,
    counters: dict[str, int],
    trades: list[TradeResult],
    detailed: list[DetailedTrade],
    equity: float,
) -> float:
    for offset, (_, row) in enumerate(frame.iterrows()):
        decision = decide_action(
            probabilities[offset],
            thresholds.buy_threshold,
            thresholds.sell_threshold,
            thresholds.min_margin,
        )
        if decision == -1:
            counters["ambiguous"] += 1
            counters["no_trade"] += 1
            continue
        if decision is None:
            counters["no_trade"] += 1
            continue
        if not range_filter_pass(row, decision, args.min_4h_room, args.min_1d_room):
            counters["invalid_range"] += 1
            counters["no_trade"] += 1
            continue
        trade = simulate_trade(row, decision, candles, args)
        if trade is None:
            counters["invalid_bracket"] += 1
            counters["no_trade"] += 1
            continue
        trades.append(trade)
        equity += trade.pnl
        detailed.append(_detail_trade(len(detailed) + 1, str(row["timestamp"]), trade, equity))
    return equity


def evaluate_streaming_full(
    args: argparse.Namespace,
    model: Any,
    features: Sequence[str],
    thresholds: ThresholdSpec,
) -> tuple[FixedBacktestSummary, list[DetailedTrade], Sequence[Any], list[int], int]:
    from build_hybrid_xgboost_matrix import (
        RangeFeatureConfig,
        RangeFeatureProvider,
        prepare_trend_dataset,
    )

    storage_root = Path(args.storage_root)
    signal_candles = load_candles(storage_root, args.symbol, args.timeframe)
    role, dataset = prepare_trend_dataset(args, signal_candles)
    positions = select_stream_positions(args, dataset, len(signal_candles))
    if not positions:
        raise RuntimeError("No stream positions selected for full backtest")

    range_1d_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("1d", "1D", args.range_1d_model_id, args.range_1d_version, True),
    )
    range_4h_provider = RangeFeatureProvider(
        storage_root,
        args.symbol,
        RangeFeatureConfig("4h", "4H", args.range_4h_model_id, args.range_4h_version, True),
    )

    counters = {"no_trade": 0, "ambiguous": 0, "invalid_range": 0, "invalid_bracket": 0}
    trades: list[TradeResult] = []
    detailed: list[DetailedTrade] = []
    source_indices: list[int] = []
    equity = 0.0
    chunk_size = max(int(args.stream_chunk_size), 50)
    warnings: list[str] = []
    for start in range(0, len(positions), chunk_size):
        chunk_positions = positions[start : start + chunk_size]
        frame = build_stream_chunk(
            args,
            dataset,
            role,
            signal_candles,
            chunk_positions,
            range_1d_provider,
            range_4h_provider,
            features,
            warnings,
        )
        source_indices.extend(int(value) for value in frame["source_index"].tolist())
        x_values = (
            frame[list(features)]
            .replace([np.inf, -np.inf], 0.0)
            .fillna(0.0)
            .to_numpy(dtype=np.float32)
        )
        probabilities = aligned_predict_proba(model, x_values)
        equity = evaluate_stream_frame(
            frame,
            probabilities,
            signal_candles,
            args,
            thresholds,
            counters,
            trades,
            detailed,
            equity,
        )
        print(
            f"  streamed   : {min(start + chunk_size, len(positions)):,}/{len(positions):,} rows; "
            f"trades={len(trades):,}"
        )

    for warning in warnings[:10]:
        print(f"  [!] {warning}")
    summary = summarise_counts(
        len(positions),
        trades,
        counters["no_trade"],
        counters["ambiguous"],
        counters["invalid_range"],
        counters["invalid_bracket"],
    )
    return summary, detailed, signal_candles, source_indices, len(positions)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    storage_root = Path(args.storage_root)
    matrix_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else default_matrix_path(storage_root, args.symbol, args.timeframe)
    )
    try:
        rule("HYBRID FULL 5M BACKTEST REPORT")
        print(f"  matrix      : {matrix_path}")
        print(f"  model       : {args.model_id}")
        print(f"  eval frac   : {args.eval_frac:.2f}")

        record, version = load_record(storage_root, args.model_id, args.model_version)
        thresholds = resolve_thresholds(args, record)
        print(
            "  thresholds  : "
            f"buy={thresholds.buy_threshold:.3f} "
            f"sell={thresholds.sell_threshold:.3f} "
            f"margin={thresholds.min_margin:.3f} ({thresholds.source})"
        )
        model, features, loaded_version = load_head(storage_root, args.model_id, version)
        source_rows = 0
        evaluated_rows = 0
        matrix_label = matrix_path
        if args.source_mode == "stream":
            matrix_label = Path(f"stream_{args.symbol}_{args.timeframe}_{args.stream_scope}")
            summary, trades, candles, source_indices, source_rows = evaluate_streaming_full(
                args, model, features, thresholds
            )
            evaluated_rows = summary.samples
            candle_rows = replay_candles_for_indices(candles, source_indices, trades)
        else:
            full_frame = pd.read_parquet(matrix_path)
            missing = [name for name in features if name not in full_frame.columns]
            if missing:
                raise RuntimeError(f"Hybrid matrix is missing model feature columns: {missing[:5]}")
            indices = eval_slice_indices(len(full_frame), args.eval_frac, args.max_windows)
            frame = full_frame.iloc[indices].copy()
            x_values = (
                frame[features]
                .replace([np.inf, -np.inf], 0.0)
                .fillna(0.0)
                .to_numpy(dtype=np.float32)
            )
            probabilities = aligned_predict_proba(model, x_values)
            candles = load_candles(storage_root, args.symbol, args.timeframe)
            summary, trades = evaluate_fixed_thresholds(
                frame, probabilities, candles, args, thresholds
            )
            source_rows = len(full_frame)
            evaluated_rows = len(frame)
            candle_rows = replay_candles(candles, frame, trades)
        monthly = monthly_summary(trades)
        account = account_summary(summary, args.initial_capital, args.units)

        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / "latest.csv"
        json_path = out_dir / "latest.json"
        html_path = out_dir / "latest.html"
        write_csv(csv_path, trades)
        html_path.write_text(
            render_html(
                args.report_title,
                args,
                matrix_label,
                loaded_version,
                thresholds,
                summary,
                trades,
                monthly,
                candle_rows,
            ),
            encoding="utf-8",
        )
        files = {"csv": str(csv_path), "json": str(json_path), "html": str(html_path)}
        payload = {
            "args": vars(args),
            "model_version": loaded_version,
            "matrix_rows": source_rows,
            "evaluated_rows": evaluated_rows,
            "thresholds": asdict(thresholds),
            "summary": asdict(summary),
            "account": account,
            "monthly": [asdict(row) for row in monthly],
            "replay": {
                "candles": len(candle_rows),
                "trades": len(trades),
                "html_controls": "slider candle-by-candle with entry/exit/TP/SL markers",
            },
            "files": files,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        rule("FULL BACKTEST SUMMARY")
        print(f"  rows        : {summary.samples:,}/{source_rows:,}")
        print(f"  trades      : {summary.trades:,} ({summary.coverage:.2%})")
        print(f"  buy/sell    : {summary.buy_trades:,} / {summary.sell_trades:,}")
        print(f"  win rate    : {summary.win_rate:.2%}")
        print(f"  label prec. : {summary.label_precision:.2%}")
        print(f"  total pnl   : {summary.total_pnl:+.2f}")
        print(f"  avg pnl     : {summary.avg_pnl:+.4f}")
        print(f"  profit fact.: {summary.profit_factor:.3f}")
        print(f"  max DD      : {summary.max_drawdown:.2f}")
        print(
            f"  initial/final: ${account['initial_capital']:.2f} -> ${account['final_balance']:.2f}"
        )
        print(f"  cash max DD : ${account['max_drawdown_cash']:.2f}")
        print(f"  html report : {html_path}")
        print(f"  json report : {json_path}")
        return 0
    except Exception as error:
        print(f"\n[X] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
