"""Phase162A pivot bottom-buy execution-gap helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_pivot_bottom_buy_execution_gap as phase162
from scripts.audit_pivot_payoff_target_redesign import resolve_atr


def make_frame(rows: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC"),
            "open": [100.0] * rows,
            "high": [100.0, 101.2, 101.2, 100.5, 100.5, 100.5][:rows],
            "low": [99.8, 99.8, 99.8, 99.8, 99.8, 99.8][:rows],
            "close": [100.0] * rows,
            "h4_atr_for_risk": [1.0] * rows,
        }
    )


def test_policy_grid_and_first_hit_policy_mapping():
    assert phase162.parse_int_grid("0,1,2", ()) == [0, 1, 2]
    assert phase162.parse_float_grid("0,0.06", ()) == [0.0, 0.06]
    assert phase162.parse_policy_grid("stop_first,tp_first", ()) == ["stop_first", "tp_first"]
    assert phase162.first_hit_policy("tp_first") == "target_first"
    assert phase162.first_hit_policy("stop_first") == "stop_first"


def test_event_score_and_replay_path_use_different_entry_assumptions():
    frame = make_frame()
    args = phase162.parse_args(
        [
            "--event-lookahead-bars",
            "3",
            "--hold-bars",
            "3",
            "--spread-values",
            "0",
        ]
    )
    atr = resolve_atr(frame)

    event = phase162.event_score_path(frame, 0, 0, atr, args, "stop_first")
    replay = phase162.replay_path(frame, 0, 0, atr, args, "stop_first", 0.0)
    gaps = phase162.gap_stats(frame, 0, 0, atr, args, 0.0)

    assert event is not None
    assert replay is not None
    assert gaps is not None
    assert event.entry_row_id == 0
    assert replay.entry_row_id == 1
    assert event.outcome == "take_profit"
    assert replay.outcome == "take_profit"
    assert gaps[3] == 0.0


def test_chronological_split_quantifies_skipped_winning_event():
    frame = make_frame()
    args = phase162.parse_args(
        [
            "--event-lookahead-bars",
            "3",
            "--hold-bars",
            "3",
            "--spread-values",
            "0",
            "--validation-min-trades",
            "1",
            "--validation-min-profit-factor",
            "1.0",
        ]
    )
    atr = resolve_atr(frame)

    row, monthly, events, _ = phase162.evaluate_config_split(
        "validation",
        frame,
        np.asarray([0, 1], dtype=np.int64),
        np.asarray([0, 1], dtype=np.int64),
        np.asarray([True, True]),
        atr,
        0,
        "stop_first",
        0.0,
        args,
        20,
    )

    assert row.candidate_rows == 2
    assert row.valid_independent_replays == 2
    assert row.independent_replay_take_profits == 2
    assert row.chronological_trades == 1
    assert row.skipped_while_open == 1
    assert row.skipped_winners == 1
    assert row.pass_gate == 1
    assert monthly[0]["skipped_winners"] == 1
    assert len(events) == 2
    assert events[1].chronological_status == "skipped_while_open"
