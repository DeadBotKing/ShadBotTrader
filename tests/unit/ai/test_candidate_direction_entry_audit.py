"""Phase140A candidate direction / entry audit tests."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_candidate_direction_entry.py"


@dataclass(frozen=True)
class Amount:
    amount: float


@dataclass(frozen=True)
class Candle:
    open: Amount
    high: Amount
    low: Amount
    close: Amount


def load_script():
    spec = importlib.util.spec_from_file_location("audit_candidate_direction_entry", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candle(open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(Amount(open_), Amount(high), Amount(low), Amount(close))


def buy_candidate(source_index: int = 0) -> pd.Series:
    return pd.Series(
        {
            "timestamp": "2026-01-01T08:00:00Z",
            "month": "2026-01",
            "hour": 8,
            "source_index": source_index,
            "candidate_mask": 1.0,
            "candidate_side": 1.0,
            "target_side": 1.0,
            "original_side": "BUY",
            "candidate_entry_price": 100.0,
            "candidate_take_profit": 102.0,
            "candidate_stop_loss": 98.0,
            "candidate_tp_distance": 2.0,
            "candidate_sl_distance": 2.0,
        }
    )


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01T08:00:00Z",
                "2026-01-01T08:05:00Z",
                "2026-01-01T09:00:00Z",
            ],
            "source_index": [0, 1, 5],
            "candidate_mask": [1.0, 1.0, 1.0],
            "candidate_side": [1.0, 1.0, -1.0],
            "target_side": [1.0, 1.0, -1.0],
            "candidate_entry_price": [100.0, 100.0, 100.0],
            "candidate_take_profit": [102.0, 102.0, 98.0],
            "candidate_stop_loss": [98.0, 98.0, 102.0],
            "candidate_tp_distance": [2.0, 2.0, 2.0],
            "candidate_sl_distance": [2.0, 2.0, 2.0],
        }
    )


def test_parse_entry_delays_deduplicates_and_clamps():
    module = load_script()

    assert module.parse_entry_delays("0,1,1,3") == [0, 1, 3]
    assert module.parse_entry_delays("") == [0]


def test_flipped_buy_candidate_hits_counterfactual_take_profit():
    module = load_script()
    args = module.parse_args(["--spread-mode", "fixed", "--spread-value", "0"])
    candles = [
        candle(100.0, 100.0, 100.0, 100.0),
        candle(100.0, 100.5, 97.5, 98.0),
        candle(98.0, 99.0, 97.0, 98.0),
    ]

    original, _ = module.simulate_counterfactual_trade(
        buy_candidate(), candles, "original", 0, args, 1, 0.0
    )
    flipped, _ = module.simulate_counterfactual_trade(
        buy_candidate(), candles, "flipped", 0, args, 1, 0.0
    )

    assert original is not None
    assert flipped is not None
    assert original.executed_side == "BUY"
    assert original.outcome == "stop_loss"
    assert original.pnl == pytest.approx(-2.0)
    assert flipped.executed_side == "SELL"
    assert flipped.outcome == "take_profit"
    assert flipped.pnl == pytest.approx(2.0)


def test_entry_delay_uses_delayed_candle_open():
    module = load_script()
    args = module.parse_args(["--spread-mode", "fixed", "--spread-value", "0"])
    candles = [
        candle(100.0, 100.0, 100.0, 100.0),
        candle(101.0, 101.5, 100.5, 101.0),
        candle(103.0, 103.5, 102.5, 103.0),
        candle(105.0, 107.5, 104.5, 107.0),
    ]

    trade, reason = module.simulate_counterfactual_trade(
        buy_candidate(), candles, "original", 2, args, 1, 0.0
    )

    assert reason == "ok"
    assert trade is not None
    assert trade.entry_index == 3
    assert trade.entry == pytest.approx(105.0)
    assert trade.tp == pytest.approx(107.0)


def test_chronological_scenario_skips_candidates_while_open():
    module = load_script()
    args = module.parse_args(
        [
            "--spread-mode",
            "fixed",
            "--spread-value",
            "0",
            "--max-hold-bars",
            "3",
            "--min-trades",
            "1",
        ]
    )
    frame, _ = module.prepare_frame(sample_frame(), args)
    candles = [
        candle(100.0, 100.0, 100.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
    ]

    summary, trades = module.run_scenario(frame, candles, "chronological", "original", 0, args)

    assert len(trades) == 2
    assert summary.trades == 2
    assert summary.skipped_while_open == 1


def test_build_report_identifies_flipped_lift(tmp_path):
    module = load_script()
    args = module.parse_args(["--spread-mode", "fixed", "--spread-value", "0", "--min-trades", "1"])
    frame, evaluated_rows = module.prepare_frame(sample_frame().iloc[:1], args)
    candles = [
        candle(100.0, 100.0, 100.0, 100.0),
        candle(100.0, 100.5, 97.5, 98.0),
        candle(98.0, 99.0, 97.0, 98.0),
    ]
    scenarios = [
        module.run_scenario(frame, candles, "independent", "original", 0, args),
        module.run_scenario(frame, candles, "independent", "flipped", 0, args),
        module.run_scenario(frame, candles, "chronological", "original", 0, args),
        module.run_scenario(frame, candles, "chronological", "flipped", 0, args),
    ]
    rows = [row for row, _ in scenarios]
    groups = module.build_group_rows(scenarios, 1)

    report = module.build_report(
        tmp_path / "flat.parquet", tmp_path, evaluated_rows, len(frame), rows, groups
    )

    assert report.flipped_delay0_independent_pnl > report.original_delay0_independent_pnl
    assert any("contrarian" in finding.lower() for finding in report.diagnostic_findings)


def test_main_writes_audit_outputs(tmp_path, monkeypatch):
    module = load_script()
    flat_path = tmp_path / "flat.parquet"
    out_dir = tmp_path / "out"
    flat_path.write_text("patched pandas.read_parquet", encoding="utf-8")
    monkeypatch.setattr(module.pd, "read_parquet", lambda *_args, **_kwargs: sample_frame())
    candles = [
        candle(100.0, 100.0, 100.0, 100.0),
        candle(100.0, 100.5, 97.5, 98.0),
        candle(100.0, 100.5, 97.5, 98.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
        candle(100.0, 101.0, 99.0, 100.0),
    ]
    monkeypatch.setattr(module, "load_candles", lambda *_args: candles)

    result = module.main(
        [
            "--flat-path",
            str(flat_path),
            "--output-dir",
            str(out_dir),
            "--entry-delays",
            "0,1",
            "--min-trades",
            "1",
            "--min-group-trades",
            "1",
            "--spread-mode",
            "fixed",
            "--spread-value",
            "0",
        ]
    )

    assert result == 0
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "latest.html").exists()
    assert (out_dir / "latest.csv").exists()
    assert (out_dir / "latest_groups.csv").exists()
    assert (out_dir / "best_chronological_trades.csv").exists()
