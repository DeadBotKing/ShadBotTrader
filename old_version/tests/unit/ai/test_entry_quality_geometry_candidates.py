"""Phase183A entry quality-geometry candidate audit helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from scripts import audit_entry_quality_geometry_candidates as phase183


CANDIDATE = "Q_TEST:test_cont:1H:continuation:8:0.00:0:0:2:6:0.6:1.0:8:6:0.05:1.0:0.5:ALL"
BUY_ONLY = "Q_BUY:test_buy:1H:pullback_rejection:8:0.00:0:0:2:6:0.6:1.0:8:6:0.05:1.0:0.5:BUY"


def make_frame(rows: int = 180) -> pd.DataFrame:
    records = []
    price = 100.0
    for index in range(rows):
        wave = math.sin(index / 4.0) * 0.5
        base = price + index * 0.03 + wave
        open_ = base - 0.06
        close = base + (0.12 if index % 4 else -0.03)
        high = max(open_, close) + 0.3
        low = min(open_, close) - 0.3
        if index % 24 in {9, 10, 11}:
            high += 1.0
            close += 0.4
        if index % 31 in {15, 16}:
            low -= 0.9
            close -= 0.35
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


def test_parse_candidates_and_side_filter():
    rows = phase183.parse_candidates(CANDIDATE + ";" + BUY_ONLY)

    assert rows[0].candidate_id == "Q_TEST"
    assert rows[0].timeframe == "1H"
    assert rows[1].side_filter == "BUY"


def test_adjusted_side_specific_metrics_disables_balance_requirement():
    candidate = phase183.parse_candidates(BUY_ONLY)[0]
    args = phase183.parse_args(["--candidates", BUY_ONLY, "--min-train-events", "1"])
    frame = make_frame()
    atr = phase183.phase181b.wilder_atr(
        frame["high"].to_numpy(), frame["low"].to_numpy(), frame["close"].to_numpy()
    )
    family = phase183.to_entry_family(candidate)
    raw_events = phase183.phase181b.discover_family_events("1H", family, frame, atr, args)
    events = phase183.filter_events(raw_events, candidate.side_filter)
    idx = phase183.idx_range(0, len(frame) // 2)

    metrics, _ = phase183.phase181b.split_metrics("1H", family, frame, atr, "train", idx, events, args, None)
    adjusted = phase183.adjusted_split_metrics(metrics, candidate.side_filter, args, "train")

    assert adjusted.direction_balance_gate == 1
    assert adjusted.sell_events == 0


def test_run_writes_outputs(tmp_path: Path):
    frame = make_frame()
    h1_path = tmp_path / "h1.csv"
    frame.to_csv(h1_path, index=False)
    phase182 = {
        "selected_focus_timeframe": "1H",
        "selected_focus_family_id": "E3_CONTINUATION",
        "quality_geometry_rows": [
            {
                "timeframe": "1H",
                "family_id": "E3_CONTINUATION",
                "current_mfe_atr": 1.2,
                "current_mae_atr": 0.75,
            }
        ],
    }
    phase182_path = tmp_path / "phase182.json"
    phase181_path = tmp_path / "phase181.json"
    out = tmp_path / "out"
    phase182_path.write_text(json.dumps(phase182), encoding="utf-8")
    phase181_path.write_text(json.dumps({"symbol": "XAUUSD"}), encoding="utf-8")

    report = phase183.run(
        [
            "--phase182a-path",
            str(phase182_path),
            "--phase181b-path",
            str(phase181_path),
            "--candidates",
            CANDIDATE,
            "--h1-flat-path",
            str(h1_path),
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
            str(out),
        ]
    )

    assert report.no_training_gate == 1
    assert report.evaluated_candidates == 1
    assert (out / "latest.json").exists()
    assert (out / "latest_candidates.csv").exists()
    assert (out / "latest_geometry_comparison.csv").exists()


def test_decision_matrix_blocks_training_when_no_ready():
    candidate = phase183.CandidateSummaryRow(
        candidate_id="Q",
        label="q",
        timeframe="1H",
        family_type="continuation",
        side_filter="ALL",
        recent_window_bars=1,
        buffer_atr=0,
        trigger_horizon_bars=1,
        quality_bars=1,
        mfe_atr=1,
        mae_atr=1,
        train_events=1,
        validation_events=1,
        test_events=1,
        train_event_rate=0.1,
        validation_event_rate=0.1,
        test_event_rate=0.1,
        train_quality_pass_rate=0.1,
        validation_quality_pass_rate=0.1,
        test_quality_pass_rate=0.1,
        train_replay_profit_factor=0.5,
        validation_replay_profit_factor=0.5,
        test_replay_profit_factor=0.5,
        train_mean_score=-0.1,
        validation_mean_score=-0.1,
        test_mean_score=-0.1,
        validation_label_psi=0,
        test_label_psi=0,
        train_feature_smd=1,
        validation_feature_smd=1,
        test_feature_smd=1,
        walkforward_folds=1,
        walkforward_pass_folds=0,
        walkforward_pass_ratio=0,
        density_gate=1,
        direction_balance_gate=1,
        temporal_stability_gate=1,
        mfe_mae_gate=0,
        replay_gate=0,
        feature_separability_gate=1,
        cost_gate=1,
        quality_geometry_candidate_ready_gate=0,
        failure_reasons="[]",
        diagnostic_score=0,
    )
    matrix = phase183.decision_matrix([candidate])
    by_route = {row.route_id: row for row in matrix}

    assert by_route["ENTRY_QUALITY_GEOMETRY_MODEL_PREFLIGHT"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"
