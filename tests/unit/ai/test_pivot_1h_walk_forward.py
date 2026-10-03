"""Phase166A 1H locked candidate walk-forward helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import replay_pivot_1h_locked_candidate_walk_forward as phase166
from scripts.audit_pivot_1h_entry_feasibility import build_zone_masks
from scripts.audit_pivot_payoff_target_redesign import resolve_atr


def make_frame(rows: int = 180) -> pd.DataFrame:
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


def test_build_fold_specs_respects_purge_and_step():
    specs = phase166.build_fold_specs(
        total_rows=100,
        train_bars=30,
        validation_bars=10,
        test_bars=10,
        step_bars=20,
        purge_gap=2,
    )

    assert len(specs) == 3
    assert specs[0].train_start == 0
    assert specs[0].train_end == 30
    assert specs[0].validation_start == 32
    assert specs[0].test_start == 44
    assert specs[1].train_start == 20


def test_fold_monthly_gate_uses_all_splits():
    args = phase166.parse_args(["--min-positive-month-ratio", "0.5", "--max-worst-month-loss", "10"])
    summary = type("S", (), {"positive_month_ratio": 0.5, "worst_month_pnl": -1.0})()
    bad = type("S", (), {"positive_month_ratio": 0.4, "worst_month_pnl": -1.0})()

    assert phase166.fold_monthly_gate(summary, summary, summary, args) == 1
    assert phase166.fold_monthly_gate(summary, bad, summary, args) == 0


def test_replay_fold_returns_fold_row_and_exports():
    frame = make_frame(180)
    atr = resolve_atr(frame)
    args = phase166.parse_args(
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
            "--fold-train-bars",
            "60",
            "--fold-validation-bars",
            "30",
            "--fold-test-bars",
            "30",
            "--purge-gap",
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
    spec = phase166.build_fold_specs(180, 60, 30, 30, 30, 0, 1)[0]

    fold_row, split_rows, trade_rows, monthly_rows, stress_rows = phase166.replay_fold(
        spec,
        frame,
        top,
        bottom,
        atr,
        args,
    )

    assert fold_row.fold == 1
    assert len(split_rows) == 3
    assert isinstance(trade_rows, list)
    assert isinstance(monthly_rows, list)
    assert stress_rows
