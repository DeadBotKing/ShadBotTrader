"""Phase172A broker-cost-aware 1H target family helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_broker_cost_aware_1h_target_family as phase172
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


def test_parse_families_parses_full_spec():
    families = phase172.parse_families("F:label:breakout:1:24:0.05:0.85:0.15:1:1.0:0:2.0:1.0:24")

    assert families[0].family_id == "F"
    assert families[0].side_mapping == "breakout"
    assert families[0].tp_atr == 2.0
    assert families[0].hold_bars == 24


def test_label_distribution_and_psi():
    events = [
        phase172.EventOutcome("F", 1, 1, 2, 3, "t", "top", "BUY", phase172.LABEL_POSITIVE, 1, 1, "take_profit", 1, "fixed", 0.4, 1.5, 1, 24),
        phase172.EventOutcome("F", 2, 2, 3, 4, "t", "bottom", "SELL", phase172.LABEL_NEGATIVE, -1, -1, "stop_loss", 1, "fixed", 0.4, 1.5, 1, 24),
    ]

    dist = phase172.action_distribution(events)

    assert dist[phase172.LABEL_POSITIVE] == 0.5
    assert dist[phase172.LABEL_NEGATIVE] == 0.5
    assert phase172.label_psi(dist, dist) == 0.0


def test_evaluate_family_events_and_split_metrics():
    frame = make_frame()
    atr = resolve_atr(frame)
    family = phase172.parse_families("F:label:breakout:0:12:0.2:0.85:0.15:1:1.0:0:0.5:0.5:6")[0]
    args = phase172.parse_args(["--spread-value", "0", "--min-train-events", "1", "--min-validation-events", "1", "--min-test-events", "1"])
    top, bottom, _ = build_zone_masks(frame, atr, 12, 0.2, 0.85, 0.15, 1, 1.0, 0.0)

    events = phase172.evaluate_family_events(family, frame, atr, top, bottom, args, 0.0)
    metrics = phase172.split_metrics(family, "train", np.arange(0, 60), events, frame, args, None)

    assert events
    assert metrics.candidate_events > 0
    assert 0.0 <= metrics.positive_rate <= 1.0


def test_family_summary_ready_gate_can_be_computed():
    frame = make_frame()
    atr = resolve_atr(frame)
    family = phase172.parse_families("F:label:breakout:0:12:0.2:0.85:0.15:1:1.0:0:0.5:0.5:6")[0]
    args = phase172.parse_args(
        [
            "--spread-value", "0",
            "--stress-spread-value", "0",
            "--fold-train-bars", "60",
            "--fold-validation-bars", "30",
            "--fold-test-bars", "30",
            "--fold-step-bars", "30",
            "--purge-gap", "0",
            "--min-train-events", "1",
            "--min-validation-events", "1",
            "--min-test-events", "1",
            "--min-positive-rate", "0",
            "--max-positive-rate", "1",
            "--min-walkforward-folds", "1",
            "--min-walkforward-pass-ratio", "0",
        ]
    )
    rows, _events = phase172.family_static_rows(family, frame, atr, args, 0.0)
    stress_rows, _ = phase172.family_static_rows(family, frame, atr, args, 0.0)
    wf = phase172.walk_forward_rows(family, frame, atr, args)

    summary = phase172.build_family_summary(family, rows, wf, next(row for row in stress_rows if row.split == "test"), args)

    assert summary.family_id == "F"
    assert summary.walkforward_folds >= 1
    assert summary.density_gate in {0, 1}
