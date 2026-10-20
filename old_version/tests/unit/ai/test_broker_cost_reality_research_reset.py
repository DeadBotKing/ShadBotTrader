"""Phase169A broker cost reality / research reset helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import audit_broker_cost_reality_research_reset as phase169


def test_parse_float_grid_and_timeframes():
    assert phase169.parse_float_grid("0.2,0.5", ()) == [0.2, 0.5]
    assert phase169.parse_timeframes("5m;1h") == ["5M", "1H"]


def test_spread_atr_rows_for_frame_fixed_and_pct():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="1h", tz="UTC"),
            "open": [100, 100, 100, 100],
            "high": [101, 101, 101, 101],
            "low": [99, 99, 99, 99],
            "close": [100, 100, 100, 100],
        }
    )
    args = phase169.parse_args(["--fixed-spreads", "0.2", "--pct-spreads", "0.1", "--max-median-spread-atr", "0.2"])

    rows = phase169.spread_atr_rows_for_frame(args, "1H", frame, np.asarray([2, 2, 2, 2], dtype=float))

    fixed = next(row for row in rows if row.spread_mode == "fixed")
    pct = next(row for row in rows if row.spread_mode == "pct")
    assert fixed.full_spread_atr_median == 0.1
    assert pct.full_spread_atr_median == 0.05
    assert fixed.feasible_gate == 1


def test_summarize_spread_sample_from_bid_ask(tmp_path):
    sample = tmp_path / "spread.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="1min", tz="UTC"),
            "bid": [100.0, 100.0, 100.0],
            "ask": [100.2, 100.5, 101.0],
        }
    ).to_csv(sample, index=False)

    row = phase169.summarize_spread_sample(str(sample))

    assert row.status == "PASS"
    assert row.rows == 3
    assert row.spread_median == 0.5


def test_route_decisions_read_phase_logs(tmp_path):
    root = tmp_path / "run_logs"
    (root / "pivot_bottom_buy_execution_gap").mkdir(parents=True)
    (root / "pivot_1h_predeclared_filter_confirmation").mkdir(parents=True)
    (root / "pivot_1h_predeclared_filter_confirmation" / "latest.json").write_text(
        json.dumps({"confirmation_pass_gate": 0, "recommendation": "STOP", "selected_filter_name": "buy"}),
        encoding="utf-8",
    )
    (root / "pivot_bottom_buy_execution_gap" / "latest.json").write_text(
        json.dumps({"selected_transfer_pass_gate": 0}), encoding="utf-8"
    )
    args = phase169.parse_args(["--run-logs-root", str(root)])

    sources = phase169.phase_sources(args)
    rows = phase169.build_route_decisions(sources)

    five_m = next(row for row in rows if row.route == "5M pivot bottom-buy")
    one_h = next(row for row in rows if row.route == "1H locked breakout BRK_D1_FAST")
    assert five_m.status == "REJECTED"
    assert one_h.status == "REJECTED"


def test_choose_recommendation_stops_rejected_route_without_spread_sample():
    routes = [
        phase169.RouteDecisionRow(
            route="1H locked breakout BRK_D1_FAST",
            phase="Phase168A",
            status="REJECTED",
            decision="stop",
            evidence="{}",
            allowed_next_action="redesign",
            blocked_actions="training",
        )
    ]
    sample = phase169.SpreadSampleRow(
        path="",
        status="NOT_PROVIDED",
        rows=0,
        first_timestamp="",
        last_timestamp="",
        spread_median=0.0,
        spread_p90=0.0,
        spread_p99=0.0,
        spread_mean=0.0,
        notes="",
    )

    route_decision, cost_status, next_phase = phase169.choose_recommendation(routes, sample)

    assert route_decision == "STOP_CURRENT_PIVOT_LOCKED_ROUTES"
    assert cost_status == "BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED"
    assert "Phase170A" in next_phase
