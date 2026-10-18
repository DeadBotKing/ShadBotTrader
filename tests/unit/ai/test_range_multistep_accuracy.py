"""Phase186A range candle-by-candle forecast accuracy helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import audit_range_multistep_accuracy as phase186


def make_ohlc(rows: int = 90) -> pd.DataFrame:
    records = []
    for index in range(rows):
        base = 100.0 + index * 0.45
        span = 1.1 + (index % 7) * 0.28
        records.append(
            {
                "timestamp": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=4 * index),
                "open": base - 0.15,
                "high": base + span,
                "low": base - span * 0.85,
                "close": base + 0.08,
            }
        )
    return pd.DataFrame(records)


def write_perfect_predictions(frame: pd.DataFrame, path: Path, steps: int) -> None:
    rows = []
    for index in range(20, len(frame) - steps):
        record = {
            "timeframe": "4H",
            "timestamp": str(frame.at[index, "timestamp"]),
        }
        for step in range(1, steps + 1):
            record[f"predicted_high_{step}"] = float(frame.at[index + step, "high"])
            record[f"predicted_low_{step}"] = float(frame.at[index + step, "low"])
        rows.append(record)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_parse_range_steps_keeps_pairs_and_uses_last_timestep():
    raw = np.zeros((8, 4), dtype=float)
    raw[0] = [9.0, 9.0, 9.0, 9.0]
    raw[-1] = [0.2, -0.3, 0.5, -0.7]

    steps, layout = phase186.parse_range_steps(raw)

    assert layout == "seq2seq_last_timestep"
    assert steps == [(0.2, -0.3), (0.5, -0.7)]
    assert phase186.range_raw_pair(raw) == (0.5, -0.7)
    assert phase186.production_contract_matches(raw)


def test_parse_range_steps_scalar_layouts():
    steps, layout = phase186.parse_range_steps(np.array([0.4, -0.2]))
    assert steps == [(0.4, -0.2)]
    assert layout == "vector"

    steps, layout = phase186.parse_range_steps(np.array([[0.4, -0.2]]))
    assert steps == [(0.4, -0.2)]
    assert layout == "row_vector"


def test_parse_range_steps_rejects_odd_width_and_batch():
    with pytest.raises(RuntimeError):
        phase186.parse_range_steps(np.array([1.0, 2.0, 3.0]))
    with pytest.raises(RuntimeError):
        phase186.parse_range_steps(np.zeros((2, 8, 2)))


def test_price_conversion_atr_and_pct():
    high, low = phase186.range_output_to_prices(0.5, -0.25, 100.0, 2.0, "atr")
    assert high == pytest.approx(101.0)
    assert low == pytest.approx(99.5)

    high, low = phase186.range_output_to_prices(0.01, -0.02, 100.0, 2.0, "pct")
    assert high == pytest.approx(101.0)
    assert low == pytest.approx(98.0)


def test_step_error_is_the_specific_candle_not_the_horizon_envelope():
    high = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 110.0, 140.0])
    low = np.array([90.0, 90.0, 90.0, 90.0, 90.0, 95.0, 80.0])
    close = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 108.0, 120.0])
    open_ = close.copy()

    step1 = phase186.build_step_error_row(
        timeframe="4H",
        timestamp="t",
        row_index=4,
        step=1,
        reference_close=100.0,
        atr_reference=1.0,
        target_units="atr",
        predicted_high_raw=10.0,
        predicted_low_raw=-5.0,
        predicted_high=110.0,
        predicted_low=95.0,
        high=high,
        low=low,
        open_=open_,
        close=close,
    )
    step2 = phase186.build_step_error_row(
        timeframe="4H",
        timestamp="t",
        row_index=4,
        step=2,
        reference_close=100.0,
        atr_reference=1.0,
        target_units="atr",
        predicted_high_raw=40.0,
        predicted_low_raw=-20.0,
        predicted_high=140.0,
        predicted_low=80.0,
        high=high,
        low=low,
        open_=open_,
        close=close,
    )

    assert step1.realized_high == 110.0
    assert step1.high_price_error_atr == pytest.approx(0.0)
    assert step2.realized_high == 140.0
    assert step2.high_price_error_atr == pytest.approx(0.0)
    assert step1.realized_high != max(high[5:])


def test_horizon1_predictions_do_not_invent_later_steps(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    frame.to_csv(flat_path, index=False)
    rows = []
    for index in range(20, len(frame) - 1):
        rows.append(
            {
                "timeframe": "4H",
                "timestamp": str(frame.at[index, "timestamp"]),
                "predicted_high": float(frame.at[index + 1, "high"]),
                "predicted_low": float(frame.at[index + 1, "low"]),
            }
        )
    pd.DataFrame(rows).to_csv(pred_path, index=False)

    report = phase186.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--requested-steps",
            "5",
            "--min-rows",
            "10",
            "--min-spearman",
            "0.10",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    capability = report.capability_rows[0]
    assert capability["model_output_horizon"] == 1
    assert capability["multi_step_available"] == 0
    assert capability["missing_steps"] == "2,3,4,5"
    assert capability["capability_verdict"] == "STEP1_ONLY"
    assert capability["recursive_rollout_used"] == 0
    assert capability["envelope_metric_used"] == 0
    assert report.candle_forecast_ready_gate == 0
    assert report.summary_rows[0]["primary_failure_reason"] == "multistep_output_not_available"
    assert report.summary_rows[0]["step1_rows"] > 0
    assert report.summary_rows[0]["step1_accuracy_gate"] == 1
    assert "Only step 1 is auditable" in report.owner_answer
    assert "no model evidence" in report.owner_answer
    assert report.no_training_gate == 1
    assert report.no_paper_live_gate == 1
    by_route = {row["route_id"]: row for row in report.decision_matrix}
    assert by_route["CANDLE_BY_CANDLE_FUTURE_STEPS"]["status"] == "NOT_AVAILABLE"
    assert by_route["PAPER_OR_LIVE"]["status"] == "BLOCKED"
    missing = [row for row in report.step_summary_rows if row["step"] == 3]
    assert missing[0]["auditable"] == 0
    assert missing[0]["median_abs_high_error_atr"] is None


def test_perfect_multistep_predictions_pass_when_request_matches(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    out = tmp_path / "out"
    frame.to_csv(flat_path, index=False)
    write_perfect_predictions(frame, pred_path, 3)

    report = phase186.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--requested-steps",
            "3",
            "--min-rows",
            "10",
            "--max-median-abs-error-atr",
            "0.05",
            "--min-spearman",
            "0.50",
            "--output-dir",
            str(out),
        ]
    )

    assert report.capability_rows[0]["model_output_horizon"] == 3
    assert report.capability_rows[0]["multi_step_available"] == 1
    assert report.capability_rows[0]["all_requested_steps_emitted"] == 1
    assert report.candle_forecast_ready_gate == 1
    assert report.summary_rows[0]["primary_failure_reason"] == "none"
    assert "covers requested_steps=3" in report.owner_answer
    step2 = next(row for row in report.step_summary_rows if row["step"] == 2)
    assert step2["auditable"] == 1
    assert step2["median_abs_high_error_atr"] == pytest.approx(0.0)
    assert step2["high_within_050_atr_rate"] == pytest.approx(1.0)
    curve = [row for row in report.degradation_rows if row["auditable"] == 1]
    assert [row["step"] for row in curve] == [1, 2, 3]
    assert Path(report.output_model_capability_csv).exists()
    assert Path(report.output_step_errors_csv).exists()
    assert Path(report.output_degradation_curve_csv).exists()
    payload = json.loads((out / "latest.json").read_text(encoding="utf-8"))
    assert payload["recursive_rollout_used"] == 0
    assert payload["envelope_metric_used"] == 0
    assert payload["no_paper_live_gate"] == 1


def test_partial_multistep_fails_ready_gate_even_if_emitted_steps_are_perfect(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    frame.to_csv(flat_path, index=False)
    write_perfect_predictions(frame, pred_path, 2)

    report = phase186.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--requested-steps",
            "4",
            "--min-rows",
            "10",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert report.capability_rows[0]["capability_verdict"] == "PARTIAL_MULTISTEP"
    assert report.capability_rows[0]["missing_steps"] == "3,4"
    assert report.candle_forecast_ready_gate == 0
    assert report.summary_rows[0]["primary_failure_reason"] == "partial_multistep_output"


def test_large_error_fails_step_accuracy_even_when_ranking_survives(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    frame.to_csv(flat_path, index=False)
    rows = []
    for index in range(20, len(frame) - 1):
        rows.append(
            {
                "timeframe": "4H",
                "timestamp": str(frame.at[index, "timestamp"]),
                "predicted_high": float(frame.at[index + 1, "high"]) + 50.0,
                "predicted_low": float(frame.at[index + 1, "low"]) - 50.0,
            }
        )
    pd.DataFrame(rows).to_csv(pred_path, index=False)

    report = phase186.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--requested-steps",
            "1",
            "--min-rows",
            "10",
            "--max-median-abs-error-atr",
            "0.50",
            "--min-spearman",
            "0.0",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert report.summary_rows[0]["all_requested_steps_emitted"] == 1
    assert report.summary_rows[0]["step1_accuracy_gate"] == 0
    assert report.summary_rows[0]["primary_failure_reason"] == "step_accuracy_gate_failed"
    assert report.candle_forecast_ready_gate == 0


def test_constant_offset_fails_spearman_gate(tmp_path: Path):
    frame = make_ohlc()
    flat_path = tmp_path / "h4.csv"
    pred_path = tmp_path / "pred.csv"
    frame.to_csv(flat_path, index=False)
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    atr = phase186.wilder_atr(high, low, close)
    rows = []
    for index in range(20, len(frame) - 1):
        rows.append(
            {
                "timeframe": "4H",
                "timestamp": str(frame.at[index, "timestamp"]),
                "predicted_high": float(close[index] + 0.30 * atr[index]),
                "predicted_low": float(close[index] - 0.30 * atr[index]),
            }
        )
    pd.DataFrame(rows).to_csv(pred_path, index=False)

    report = phase186.run(
        [
            "--source-mode",
            "predictions",
            "--predictions-path",
            str(pred_path),
            "--timeframes",
            "4H",
            "--h4-flat-path",
            str(flat_path),
            "--requested-steps",
            "1",
            "--min-rows",
            "10",
            "--max-median-abs-error-atr",
            "10",
            "--min-spearman",
            "0.20",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert report.step_summary_rows[0]["step_accuracy_gate"] == 0
    assert report.step_summary_rows[0]["primary_failure_reason"] == "high_spearman_failed"
    assert "2..1" not in report.owner_answer
    assert report.candle_forecast_ready_gate == 0


def test_paper_live_stays_blocked_even_if_a_summary_is_ready():
    summary = phase186.TimeframeSummary(
        timeframe="4H",
        model_id="test",
        model_version=1,
        target_units="atr",
        model_output_horizon=3,
        requested_steps=3,
        multi_step_available=1,
        all_requested_steps_emitted=1,
        auditable_steps=3,
        measured_rows=40,
        step1_rows=40,
        step1_median_abs_high_error_atr=0.1,
        step1_median_abs_low_error_atr=0.1,
        step1_high_spearman=0.4,
        step1_low_spearman=0.4,
        step1_high_within_050_atr_rate=0.8,
        step1_low_within_050_atr_rate=0.8,
        step1_accuracy_gate=1,
        all_requested_steps_accurate=1,
        candle_forecast_ready_gate=1,
        primary_failure_reason="none",
        interpretation="ready",
    )
    capability = phase186.make_capability(
        timeframe="4H",
        source_mode="predictions",
        model_id="test",
        model_version=1,
        target_units="atr",
        record_horizon=3,
        window_size=32,
        input_scale=(-2.0, 2.0),
        keras_output_shape="",
        observed_output_shape="indexed_price_columns",
        output_layout="indexed_price_columns",
        forecast_timestep="predictions_file",
        emitted=3,
        requested=3,
        production_contract_check="not_applicable",
        rows_measured=40,
        rows_skipped=0,
        notes="test",
    )
    matrix = {row.route_id: row for row in phase186.decision_matrix([summary], [capability])}

    assert matrix["PAPER_OR_LIVE"].status == "BLOCKED"
    assert matrix["RANGE_AS_FUTURE_PRICE_ENGINE"].status == "OWNER_REVIEW_REQUIRED"
