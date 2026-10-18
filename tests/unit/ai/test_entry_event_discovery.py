"""Phase181B entry-event discovery helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from scripts import audit_entry_event_discovery as phase181b


E1_ONLY = "E1_TEST:breakout_entry:breakout:12:0.00:0.0:0:4:8:0.8:0.6:12:8:0.10:1.00:0.45"


def make_frame(rows: int = 180) -> pd.DataFrame:
    records = []
    price = 100.0
    for index in range(rows):
        drift = 0.04 * index
        wave = math.sin(index / 5.0) * 0.8
        base = price + drift + wave
        open_ = base - 0.05
        close = base + (0.12 if index % 3 else -0.04)
        high = max(open_, close) + 0.35
        low = min(open_, close) - 0.35
        # Force periodic follow-through breakouts after setup candidates.
        if index % 30 in {13, 14, 15}:
            high += 1.1
            close += 0.55
        if index % 45 in {22, 23, 24}:
            low -= 1.0
            close -= 0.45
        records.append(
            {
                "timestamp": pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(hours=index),
                "open": open_,
                "high": max(high, open_, close),
                "low": min(low, open_, close),
                "close": close,
            }
        )
    return pd.DataFrame(records)


def test_canonical_timeframe_and_family_parse():
    assert phase181b.canonical_timeframe("H1") == "1H"
    assert phase181b.canonical_timeframe("4") == "4H"
    assert phase181b.canonical_timeframe("1") == "1D"

    families = phase181b.parse_families(E1_ONLY)

    assert families[0].family_id == "E1_TEST"
    assert families[0].family_type == "breakout"
    assert families[0].trigger_horizon_bars == 4


def test_breakout_discovery_creates_triggered_events(tmp_path: Path):
    frame = make_frame()
    path = tmp_path / "h1.csv"
    frame.to_csv(path, index=False)
    args = phase181b.parse_args(
        [
            "--timeframes",
            "1H",
            "--h1-flat-path",
            str(path),
            "--families",
            E1_ONLY,
            "--spread-value",
            "0.01",
            "--max-median-spread-atr",
            "10",
            "--min-train-events",
            "1",
            "--min-validation-events",
            "1",
            "--min-test-events",
            "1",
            "--min-side-events",
            "0",
        ]
    )
    loaded = phase181b.read_ohlc_frame(path)
    atr = phase181b.wilder_atr(
        loaded["high"].to_numpy(), loaded["low"].to_numpy(), loaded["close"].to_numpy()
    )
    family = phase181b.parse_families(E1_ONLY)[0]

    events = phase181b.discover_family_events("1H", family, loaded, atr, args)

    assert events
    assert any(event.trigger_gate for event in events)
    assert all(event.setup_gate == 1 for event in events)
    assert {event.side for event in events}.issubset({phase181b.SIDE_BUY, phase181b.SIDE_SELL})


def test_run_writes_entry_discovery_outputs(tmp_path: Path):
    frame = make_frame()
    h1_path = tmp_path / "h1.csv"
    frame.to_csv(h1_path, index=False)
    output_dir = tmp_path / "out"

    report = phase181b.run(
        [
            "--symbol",
            "XAUUSD",
            "--timeframes",
            "1H",
            "--h1-flat-path",
            str(h1_path),
            "--families",
            E1_ONLY,
            "--spread-value",
            "0.01",
            "--max-median-spread-atr",
            "10",
            "--min-train-events",
            "1",
            "--min-validation-events",
            "1",
            "--min-test-events",
            "1",
            "--min-side-events",
            "0",
            "--min-quality-pass-rate",
            "0",
            "--min-mfe-mae-ratio",
            "0",
            "--min-replay-profit-factor",
            "0",
            "--min-feature-separability",
            "0",
            "--min-direction-balance",
            "0",
            "--max-label-psi",
            "999",
            "--max-event-rate",
            "1",
            "--min-walkforward-folds",
            "1",
            "--min-walkforward-pass-ratio",
            "0",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert report.no_training_gate == 1
    assert report.no_paper_live_gate == 1
    payload = json.loads((output_dir / "latest.json").read_text(encoding="utf-8"))
    assert payload["evaluated_families"] == 1
    assert payload["family_rows"]
    assert (output_dir / "latest_events.csv").exists()
    assert (output_dir / "latest_replay.csv").exists()
    assert (output_dir / "latest_feature_separability.csv").exists()
    assert (output_dir / "latest_decision_matrix.csv").exists()


def test_decision_matrix_blocks_paper_live():
    matrix = phase181b.decision_matrix([])
    by_route = {row.route_id: row for row in matrix}

    assert by_route["ENTRY_EVENT_MODEL_TRAINING"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
