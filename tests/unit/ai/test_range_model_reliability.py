"""Phase185A range model reliability audit helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import audit_range_model_reliability as phase185


def make_ohlc(rows: int = 80) -> pd.DataFrame:
    records = []
    for index in range(rows):
        base = 100.0 + index * 0.4
        open_ = base - 0.1
        close = base + 0.1
        high = base + 1.0 + (index % 5) * 0.05
        low = base - 1.0 - (index % 3) * 0.04
        records.append(
            {
                "timestamp": pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(hours=4 * index),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    return pd.DataFrame(records)


def make_predictions(frame: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    rows = []
    for index in range(15, len(frame) - horizon):
        close = float(frame.at[index, "close"])
        future_high = float(frame.loc[index + 1 : index + horizon, "high"].max())
        future_low = float(frame.loc[index + 1 : index + horizon, "low"].min())
        rows.append(
            {
                "timeframe": "4H",
                "timestamp": str(frame.at[index, "timestamp"]),
                "predicted_high": future_high + 0.1,
                "predicted_low": future_low - 0.1,
            }
        )
    return pd.DataFrame(rows)


def test_calibration_and_summary_from_prediction_rows(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    frame.to_csv(flat_path, index=False)
    make_predictions(frame).to_csv(pred_path, index=False)

    report = phase185.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--h4-horizon",
            "3",
            "--min-coherent-rate",
            "0.90",
            "--max-median-abs-error-atr",
            "0.30",
            "--min-abs-spearman",
            "0.0",
            "--min-monotonicity",
            "0.0",
            "--min-decision-quality-lift",
            "-1",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert report.evaluated_timeframes == 1
    assert report.summary_rows[0]["timeframe"] == "4H"
    assert report.summary_rows[0]["rows"] > 0
    assert report.calibration_rows
    assert Path(report.output_forecast_errors_csv).exists()


def test_summary_gate_failure_for_incoherent_rows():
    high = np.array([10, 11, 12, 13, 14], dtype=float)
    low = np.array([9, 9, 10, 11, 12], dtype=float)
    row = phase185.build_forecast_row(
        "4H",
        "2025-01-01 00:00:00+00:00",
        0,
        2,
        10.0,
        1.0,
        9.5,
        10.5,
        high,
        low,
        0,
    )
    args = phase185.parse_args(["--min-coherent-rate", "0.98"])
    cal = phase185.calibration_bins("4H", [row], 3)
    summary = phase185.summary_row("4H", "predictions", "test", 0, "unknown", 2, [row], cal, args)

    assert summary.coherent_rate == 0.0
    assert summary.coherence_gate == 0
    assert summary.range_reliability_gate == 0


def test_decision_matrix_blocks_tp_sl_when_not_reliable():
    row = phase185.SummaryRow(
        timeframe="4H",
        source_mode="predictions",
        model_id="test",
        model_version=0,
        target_units="unknown",
        horizon_bars=3,
        rows=10,
        coherent_rate=1,
        high_coherent_rate=1,
        low_coherent_rate=1,
        median_abs_high_error_atr=2,
        median_abs_low_error_atr=2,
        p90_abs_high_error_atr=3,
        p90_abs_low_error_atr=3,
        high_bias_atr=0,
        low_bias_atr=0,
        high_rmse_atr=2,
        low_rmse_atr=2,
        up_spearman=0,
        down_spearman=0,
        width_spearman=0,
        up_monotonicity=0,
        down_monotonicity=0,
        decision_proxy_trades=0,
        decision_proxy_rate=0,
        decision_proxy_quality_rate=0,
        decision_proxy_mean_score=0,
        baseline_buy_quality_rate=0,
        baseline_sell_quality_rate=0,
        coherence_gate=1,
        error_gate=0,
        ranking_gate=0,
        calibration_gate=0,
        decision_utility_gate=0,
        range_reliability_gate=0,
        primary_failure_reason="error_gate_failed",
    )
    matrix = phase185.decision_matrix([row])
    by_route = {item.route_id: item for item in matrix}

    assert by_route["RANGE_AS_TP_SL_ENGINE"].status == "BLOCKED"
    assert by_route["PAPER_OR_LIVE"].status == "BLOCKED"


def test_output_json_is_valid(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    out = tmp_path / "out"
    frame.to_csv(flat_path, index=False)
    make_predictions(frame).to_csv(pred_path, index=False)

    phase185.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--h4-horizon",
            "3",
            "--output-dir",
            str(out),
        ]
    )

    payload = json.loads((out / "latest.json").read_text(encoding="utf-8"))
    assert payload["source_mode"] == "predictions"
    assert payload["no_training_gate"] == 1
