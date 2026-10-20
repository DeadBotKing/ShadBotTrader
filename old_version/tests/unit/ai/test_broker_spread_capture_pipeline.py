"""Phase170A broker spread capture / cost pipeline helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import capture_broker_spread_cost_pipeline as phase170


def test_session_and_weekday_labels():
    assert phase170.session_utc("2026-01-05T01:00:00Z") == "asia"
    assert phase170.session_utc("2026-01-05T08:00:00Z") == "london_morning"
    assert phase170.session_utc("2026-01-05T14:00:00Z") == "london_ny_overlap"
    assert phase170.weekday_utc("2026-01-05T14:00:00Z") == "Monday"


def test_normalize_sample_from_bid_ask():
    sample = phase170.normalize_sample(
        {"timestamp": "2026-01-01T00:00:00Z", "bid": 100.0, "ask": 100.2, "point": 0.01, "digits": 2},
        "csv",
        "XAUUSD",
        "XAUUSD_i",
        0.01,
        2,
    )

    assert sample is not None
    assert round(sample.spread_price, 6) == 0.2
    assert round(sample.spread_points, 6) == 20.0
    assert sample.broker_symbol == "XAUUSD_i"


def test_normalize_sample_rejects_invalid_mt5_epoch_tick():
    sample = phase170.normalize_sample(
        {"timestamp": "1970-01-01T00:00:00Z", "bid": 0.0, "ask": 0.0, "point": 0.01, "digits": 2},
        "mt5",
        "XAUUSD",
        "XAUUSD_i",
        0.01,
        2,
    )

    assert sample is None


def test_load_csv_samples_supports_spread_column(tmp_path):
    path = tmp_path / "spread.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=3, freq="1h", tz="UTC"),
            "spread": [0.2, 0.5, 1.0],
            "point": [0.01, 0.01, 0.01],
        }
    ).to_csv(path, index=False)
    args = phase170.parse_args(["--source-mode", "csv", "--sample-path", str(path)])

    samples = phase170.load_csv_samples(args)

    assert len(samples) == 3
    assert samples[1].spread_price == 0.5
    assert samples[1].spread_points == 50.0


def test_spread_summary_by_session():
    samples = [
        phase170.SpreadSample("2026-01-01T01:00:00+00:00", "csv", "X", "X", 0, 0, 0, 0.01, 2, 0.2, 20, "asia", "Thursday", ""),
        phase170.SpreadSample("2026-01-01T08:00:00+00:00", "csv", "X", "X", 0, 0, 0, 0.01, 2, 0.5, 50, "london_morning", "Thursday", ""),
        phase170.SpreadSample("2026-01-01T09:00:00+00:00", "csv", "X", "X", 0, 0, 0, 0.01, 2, 1.0, 100, "london_morning", "Thursday", ""),
    ]

    rows = phase170.spread_summary(samples, "session", lambda sample: sample.session_utc)
    london = next(row for row in rows if row.bucket == "london_morning")

    assert london.rows == 2
    assert london.spread_price_median == 0.75
    assert london.spread_points_median == 75.0


def test_timeframe_cost_rows_uses_sample_spread(tmp_path):
    path = tmp_path / "h1.csv"
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=120, freq="1h", tz="UTC"),
            "open": [100.0] * 120,
            "high": [101.0] * 120,
            "low": [99.0] * 120,
            "close": [100.0] * 120,
            "atr": [2.0] * 120,
        }
    ).to_csv(path, index=False)
    samples = [
        phase170.SpreadSample("2026-01-01T01:00:00+00:00", "csv", "X", "X", 0, 0, 0, 0.01, 2, 0.2, 20, "asia", "Thursday", ""),
        phase170.SpreadSample("2026-01-01T02:00:00+00:00", "csv", "X", "X", 0, 0, 0, 0.01, 2, 0.4, 40, "asia", "Thursday", ""),
    ]
    args = phase170.parse_args(["--timeframes", "1H", "--h1-flat-path", str(path), "--max-median-spread-atr", "0.2"])

    rows = phase170.timeframe_cost_rows(args, samples)

    assert rows[0].status == "PASS"
    assert rows[0].sample_spread_median == 0.30000000000000004
    assert rows[0].median_spread_atr_median == 0.15000000000000002
    assert rows[0].feasible_gate == 1
