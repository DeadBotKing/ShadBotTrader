"""Phase163A 1H pivot entry feasibility helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_pivot_1h_entry_feasibility as phase163
from scripts.audit_pivot_payoff_target_redesign import resolve_atr


def make_1h_frame(rows: int = 140) -> pd.DataFrame:
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


def test_parse_grids_and_side_mapping():
    assert phase163.parse_int_grid("0,1", ()) == [0, 1]
    assert phase163.parse_float_grid("0,0.06", ()) == [0.0, 0.06]
    assert phase163.sides_for_row("reversal", True, False) == [("top", "SELL")]
    assert phase163.sides_for_row("bottom_buy", False, True) == [("bottom", "BUY")]
    assert phase163.sides_for_row("top_sell", False, True) == []


def test_build_zone_masks_finds_top_and_bottom():
    frame = make_1h_frame(30)
    atr = resolve_atr(frame)

    top, bottom, both = phase163.build_zone_masks(
        frame,
        atr,
        recent_window=12,
        zone_atr=0.20,
        top_position_threshold=0.85,
        bottom_position_threshold=0.15,
        exclude_both_zones=1,
        min_width_atr=1.0,
        max_width_atr=0.0,
    )

    assert bool(bottom[12]) is True
    assert bool(top[18]) is True
    assert not bool(both[12])


def test_spread_atr_summary_uses_full_spread():
    frame = make_1h_frame(120)
    atr = resolve_atr(frame)
    args = phase163.parse_args(["--spread-mode", "pct", "--max-median-spread-atr", "0.01"])

    row = phase163.spread_atr_for_split("validation", frame, np.arange(10, 60), atr, args, 0.06)

    assert row.rows == 50
    assert row.full_spread_atr_median > 0
    assert row.half_spread_atr_median == row.full_spread_atr_median / 2.0


def test_simulate_policy_split_returns_chronological_metrics():
    frame = make_1h_frame(140)
    atr = resolve_atr(frame)
    args = phase163.parse_args(
        [
            "--tp-atr",
            "0.5",
            "--sl-atr",
            "0.5",
            "--hold-bars",
            "6",
            "--validation-min-trades",
            "1",
            "--test-min-trades",
            "1",
        ]
    )
    top, bottom, _ = phase163.build_zone_masks(frame, atr, 12, 0.2, 0.85, 0.15, 1, 1.0, 0.0)

    row, monthly = phase163.simulate_policy_split(
        "p",
        "validation",
        frame,
        np.arange(20, 100),
        top,
        bottom,
        atr,
        "reversal",
        0,
        12,
        0.2,
        0.85,
        0.15,
        1,
        1.0,
        0.0,
        0.0,
        args,
    )

    assert row.candidate_events > 0
    assert row.independent_replays > 0
    assert row.trades > 0
    assert monthly
