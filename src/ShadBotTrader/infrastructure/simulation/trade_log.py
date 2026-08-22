"""Flat per-trade audit logs for model-driven backtests.

The replay tape is the source of truth, but a CSV is easier to inspect and
send for review.  This module flattens each completed round trip into one
row containing the Signal probabilities, Range forecast, executable
bracket, fills, fees and net result.  It never recomputes a trading result.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Mapping

from ShadBotTrader.domain.simulation.replay import ReplayTape

TRADE_LOG_FIELDS = (
    "run_id",
    "symbol",
    "timeframe",
    "trade_number",
    "direction",
    "signal_class",
    "sell_probability",
    "buy_probability",
    "signal_confidence",
    "directional_confidence",
    "signal_timeframe",
    "signal_generated_at",
    "range_reference_close",
    "predicted_high",
    "predicted_low",
    "range_high_offset",
    "range_low_offset",
    "range_horizon",
    "range_timeframe",
    "range_generated_at",
    "reward_risk",
    "move_fraction",
    "entry_bar",
    "entry_time",
    "entry_price",
    "entry_reference",
    "take_profit",
    "stop_loss",
    "exit_bar",
    "exit_time",
    "exit_price",
    "exit_reason",
    "bars_held",
    "quantity",
    "realized_pnl",
    "entry_fees",
    "exit_fees",
    "fees",
    "net_pnl",
    "net_pnl_percent_initial",
    "result",
    "engine",
    "configured_spread",
    "configured_commission_rate",
    "configured_slippage_rate",
    "configured_quantity",
    "test_ratio",
)


def _get(mapping: Mapping[str, Any], key: str) -> Any:
    """Read a value while treating absent metadata as an empty field."""
    return mapping.get(key, "")


def _float_text(value: Any) -> Any:
    """Keep empty values empty and make numbers CSV-friendly."""
    if value is None:
        return ""
    return value


def trade_log_rows(
    tape: ReplayTape,
    run_metadata: Mapping[str, Any] | None = None,
) -> list[Dict[str, Any]]:
    """Flatten the completed trades in ``tape`` into audit rows."""
    metadata = dict(run_metadata or {})
    rows: list[Dict[str, Any]] = []
    starting_equity = float(tape.starting_equity)

    for number, trade in enumerate(tape.round_trips(), start=1):
        entry = trade.get("entry_metadata") or {}
        bracket = trade.get("bracket") or {}
        net_pnl = trade.get("net_pnl")
        net_percent: float | str = ""
        if net_pnl is not None and starting_equity:
            net_percent = float(net_pnl) / starting_equity * 100.0

        rows.append(
            {
                "run_id": tape.session_id,
                "symbol": tape.symbol,
                "timeframe": tape.timeframe,
                "trade_number": number,
                "direction": trade.get("direction", ""),
                "signal_class": _get(entry, "signal_class"),
                "sell_probability": _get(entry, "sell_probability"),
                "buy_probability": _get(entry, "buy_probability"),
                "signal_confidence": _get(entry, "confidence"),
                "directional_confidence": _get(entry, "directional_confidence"),
                "signal_timeframe": _get(entry, "signal_timeframe"),
                "signal_generated_at": _get(entry, "signal_generated_at"),
                "range_reference_close": _get(entry, "range_reference_close")
                or _get(bracket, "model_reference"),
                "predicted_high": _get(entry, "predicted_high") or _get(bracket, "model_high"),
                "predicted_low": _get(entry, "predicted_low") or _get(bracket, "model_low"),
                "range_high_offset": _get(entry, "range_high_offset")
                or _get(bracket, "high_offset"),
                "range_low_offset": _get(entry, "range_low_offset") or _get(bracket, "low_offset"),
                "range_horizon": _get(entry, "range_horizon"),
                "range_timeframe": _get(entry, "range_timeframe"),
                "range_generated_at": _get(entry, "range_generated_at"),
                "reward_risk": _get(entry, "reward_risk"),
                "move_fraction": _get(entry, "move_fraction"),
                "entry_bar": trade.get("entry_bar", ""),
                "entry_time": trade.get("entry_time", ""),
                "entry_price": trade.get("entry_price", ""),
                "entry_reference": _get(bracket, "entry_reference"),
                "take_profit": _get(bracket, "take_profit"),
                "stop_loss": _get(bracket, "stop_loss"),
                "exit_bar": trade.get("exit_bar", ""),
                "exit_time": trade.get("exit_time", ""),
                "exit_price": trade.get("exit_price", ""),
                "exit_reason": trade.get("exit_reason", ""),
                "bars_held": trade.get("bars_held", ""),
                "quantity": trade.get("quantity", ""),
                "realized_pnl": trade.get("realized_pnl", ""),
                "entry_fees": trade.get("entry_fees", ""),
                "exit_fees": trade.get("exit_fees", ""),
                "fees": trade.get("fees", ""),
                "net_pnl": net_pnl if net_pnl is not None else "",
                "net_pnl_percent_initial": net_percent,
                "result": trade.get("result", ""),
                "engine": metadata.get("engine", ""),
                "configured_spread": metadata.get("spread", ""),
                "configured_commission_rate": metadata.get("commission_rate", ""),
                "configured_slippage_rate": metadata.get("slippage_rate", ""),
                "configured_quantity": metadata.get("quantity", ""),
                "test_ratio": metadata.get("test_ratio", ""),
            }
        )

    return rows


def write_trade_log(
    tape: ReplayTape,
    path: str | Path = "run_logs/backtest_trades.csv",
    run_metadata: Mapping[str, Any] | None = None,
) -> Path:
    """Write one auditable CSV row for every completed trade."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = trade_log_rows(tape, run_metadata)

    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_LOG_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _float_text(row.get(key, "")) for key in TRADE_LOG_FIELDS})
    return destination
