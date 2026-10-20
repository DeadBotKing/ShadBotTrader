"""Phase126A chronological hybrid replay helpers."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "replay_hybrid_chronological_backtest.py"


def load_script():
    spec = importlib.util.spec_from_file_location("replay_hybrid_chronological_backtest", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chronological_replay_skips_signals_while_a_trade_is_open(monkeypatch):
    module = load_script()
    frame = pd.DataFrame(
        {
            "timestamp": ["t0", "t1", "t2", "t4"],
            "source_index": [0, 1, 2, 4],
            "label": [2, 2, 2, 2],
        }
    )
    probabilities = np.asarray([[0.05, 0.10, 0.85]] * len(frame), dtype=np.float64)
    thresholds = module.ThresholdSpec(0.8, 0.65, 0.05, "test")
    args = argparse.Namespace(min_4h_room=2.0, min_1d_room=5.0)

    monkeypatch.setattr(module, "range_filter_pass", lambda row, decision, h4, d1: True)

    def fake_trade(row, decision, candles, args):
        source = int(row["source_index"])
        return module.TradeResult(
            side="BUY",
            row_index=source,
            source_index=source,
            entry_index=source + 1,
            exit_index=3 if source == 0 else 5,
            entry=2000.0,
            tp=2010.0,
            sl=1990.0,
            exit_price=2010.0 if source == 0 else 1998.0,
            outcome="take_profit" if source == 0 else "stop_loss",
            pnl=10.0 if source == 0 else -2.0,
            label=2,
            label_correct=True,
        )

    monkeypatch.setattr(module, "simulate_trade", fake_trade)

    state = module.evaluate_frame_chronological(frame, probabilities, [], args, thresholds)
    result = module.finalise_state(state, [0, 1, 2, 4])

    assert result.summary.samples == 4
    assert result.summary.trades == 2
    assert result.summary.total_pnl == pytest.approx(8.0)
    assert result.counters.skipped_while_open == 2
    assert [trade.source_index for trade in result.trades] == [0, 4]


def test_chronological_summary_accounts_for_probability_no_trade():
    module = load_script()
    counters = module.ChronologicalCounters(
        no_trade_probability=3,
        skipped_while_open=2,
        ambiguous=1,
        invalid_range=4,
        invalid_bracket=5,
    )

    summary = module.summarise_chronological(20, [], counters)

    assert counters.no_trade == 15
    assert summary.trades == 0
    assert summary.no_trade == 20
    assert summary.coverage == 0.0
