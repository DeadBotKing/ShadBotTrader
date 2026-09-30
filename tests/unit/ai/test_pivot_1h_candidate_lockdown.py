"""Phase165A 1H fixed-spread candidate lockdown helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import replay_pivot_1h_fixed_spread_candidate_lockdown as phase165
from scripts.audit_pivot_1h_entry_feasibility import build_zone_masks
from scripts.audit_pivot_payoff_target_redesign import resolve_atr


def make_frame(rows: int = 140) -> pd.DataFrame:
    close = np.full(rows, 100.0)
    close[::12] = 91.0
    close[6::12] = 109.0
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="1h", tz="UTC"),
            "open": close,
            "high": np.full(rows, 110.0),
            "low": np.full(rows, 90.0),
            "close": close,
            "atr": np.full(rows, 10.0),
        }
    )


def test_profit_factor_handles_no_loss_and_mixed_values():
    assert phase165.profit_factor([1.0, 2.0]) == 999.0
    assert phase165.profit_factor([]) == 0.0
    assert phase165.profit_factor([2.0, -1.0]) == 2.0


def test_monthly_dicts_aggregates_trade_pnl():
    trades = [
        phase165.Locked1HTrade(
            number=1,
            split="test",
            timestamp="2026-01-01 00:00:00+00:00",
            candidate_row_id=1,
            signal_row_id=2,
            entry_row_id=3,
            exit_row_id=4,
            zone="top",
            side="BUY",
            entry=100,
            tp=101,
            sl=99,
            exit_price=101,
            points_pnl=1,
            atr_score=0.1,
            cash_pnl=2,
            balance=102,
            outcome="take_profit",
            tp_distance=1,
            sl_distance=1,
            risk_amount=1,
            atr_value=10,
            spread_mode="fixed",
            spread_value=0.2,
            bracket_id="B",
            hold_bars=24,
        ),
        phase165.Locked1HTrade(
            number=2,
            split="test",
            timestamp="2026-01-02 00:00:00+00:00",
            candidate_row_id=5,
            signal_row_id=6,
            entry_row_id=7,
            exit_row_id=8,
            zone="bottom",
            side="SELL",
            entry=100,
            tp=99,
            sl=101,
            exit_price=101,
            points_pnl=-1,
            atr_score=-0.1,
            cash_pnl=-1,
            balance=101,
            outcome="stop_loss",
            tp_distance=1,
            sl_distance=1,
            risk_amount=1,
            atr_value=10,
            spread_mode="fixed",
            spread_value=0.2,
            bracket_id="B",
            hold_bars=24,
        ),
    ]

    pnl, counts = phase165.monthly_dicts(trades)

    assert pnl == {"2026-01": 1.0}
    assert counts == {"2026-01": 2}


def test_simulate_locked_split_returns_summary_and_trades():
    frame = make_frame()
    atr = resolve_atr(frame)
    args = phase165.parse_args(
        [
            "--recent-window-bars",
            "12",
            "--pivot-zone-atr",
            "0.2",
            "--tp-atr",
            "0.5",
            "--sl-atr",
            "0.5",
            "--hold-bars",
            "6",
            "--spread-value",
            "0",
            "--train-min-trades",
            "1",
            "--validation-min-trades",
            "1",
            "--test-min-trades",
            "1",
            "--min-positive-month-ratio",
            "0",
        ]
    )
    top, bottom, _ = build_zone_masks(frame, atr, 12, 0.2, 0.85, 0.15, 1, 1.0, 0.0)

    summary, trades, monthly = phase165.simulate_locked_split(
        "validation",
        frame,
        np.arange(20, 100),
        top,
        bottom,
        atr,
        args,
        0.0,
        collect_trades=True,
    )

    assert summary.candidate_events > 0
    assert summary.trades > 0
    assert trades
    assert monthly
    assert summary.independent_replays >= summary.trades


def test_split_gate_requires_monthly_ratio_and_profit_factor():
    args = phase165.parse_args(
        [
            "--validation-min-trades",
            "10",
            "--validation-min-profit-factor",
            "1.1",
            "--min-positive-month-ratio",
            "0.5",
        ]
    )
    good = {
        "trades": 12,
        "profit_factor": 1.2,
        "final_balance": 105,
        "candidate_event_rate": 0.1,
        "positive_month_ratio": 0.6,
        "worst_month_pnl": -1,
    }
    bad = {**good, "positive_month_ratio": 0.25}

    assert phase165.split_gate("validation", good, args) == 1
    assert phase165.split_gate("validation", bad, args) == 0
