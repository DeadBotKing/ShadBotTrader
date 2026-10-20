"""Computational contracts that the range lane got wrong or must not regress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window
from ShadBotTrader.infrastructure.ai.dual_predictor import reduce_range_band, split_range_pairs
from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import range_huber_delta
from ShadBotTrader.presentation.gateway.range_forecast_inspector import (
    build_range_path_points,
)
from ShadBotTrader.infrastructure.ai.feature_matrix import _candle_columns
from ShadBotTrader.infrastructure.ai.target_builder import (
    build_range_labels,
    build_range_labels_seq2seq,
    wilder_atr_series,
)
from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator
from scripts.audit_range_model_reliability import (
    prediction_is_effectively_constant as reliability_constant,
)
from scripts.audit_range_multistep_accuracy import (
    StepErrorRow,
    calibration_bins,
    prediction_is_effectively_constant,
    range_raw_pair,
)


def candle(index: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe("4H"),
        open_time=Timestamp(datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=4 * index)),
        open_price=Price(open_),
        high=Price(high),
        low=Price(low),
        close=Price(close),
        volume=Decimal("1"),
    )


def test_scalar_range_label_is_the_horizon_envelope_not_candle_k():
    candles = [
        candle(0, 100, 101, 99, 100),
        candle(1, 100, 110, 98, 105),
        candle(2, 105, 140, 90, 120),
        candle(3, 120, 121, 119, 120),
    ]

    envelope = build_range_labels(candles, horizon=2, units="pct")
    seq = build_range_labels_seq2seq(candles, horizon=2, units="pct")

    assert envelope.high_offset[0] == (140 - 100) / 100
    assert seq.high_seq[0][0] == (110 - 100) / 100
    assert seq.high_seq[0][1] == (140 - 100) / 100
    assert envelope.high_offset[0] != seq.high_seq[0][0]
    assert envelope.high_offset[0] == max(seq.high_seq[0])


def test_seq2seq_window_label_uses_the_same_row_not_a_shifted_row():
    series = []
    for index in range(8):
        series.append([float(index), 1000.0 + index, -index])
    generator = WindowGenerator(
        series=series,
        target_columns=[1, 2],
        window_size=3,
        horizon=0,
        seq2seq=True,
        scale=False,
    )

    window, label = generator.window_at(2)
    end = 2 + 3 - 1

    assert window[-1][0] == float(end)
    assert label[-1] == [1000.0 + end, -float(end)]
    assert label[0] == [1000.0 + (end - 2), -float(end - 2)]


def test_production_collapse_discards_later_candle_pairs():
    raw = np.zeros((8, 4))
    raw[-1] = [0.2, -0.2, 1.5, -0.9]

    assert range_raw_pair(raw) == (1.5, -0.9)


def test_float_noise_constant_is_not_a_calibration_curve():
    base = 0.27565264701843
    rows = []
    for index, noise in enumerate((0.0, 1e-15, -2e-15, 3e-14, -1e-14, 2e-15, 0.0, 4e-15)):
        rows.append(
            StepErrorRow(
                timeframe="4H",
                timestamp=str(index),
                row_index=index,
                step=1,
                reference_close=100.0,
                atr_reference=1.0,
                target_units="atr",
                predicted_high_raw=base + noise,
                predicted_low_raw=-0.27,
                predicted_high=100.0 + base + noise,
                predicted_low=99.73,
                predicted_width=base + noise + 0.27,
                realized_high=101.0 + index,
                realized_low=99.0,
                realized_open=100.0,
                realized_close=100.2,
                predicted_high_offset_atr=base + noise,
                predicted_low_offset_atr=-0.27,
                realized_high_offset_atr=1.0 + index,
                realized_low_offset_atr=-1.0,
                high_price_error_atr=0.0,
                low_price_error_atr=0.0,
                high_abs_error_atr=0.0,
                low_abs_error_atr=0.0,
                width_error_atr=0.0,
                down_room_error_atr=0.0,
                derived_midpoint_error_atr=0.0,
                pair_coherent=1,
                high_covered=1,
                low_covered=1,
                candle_contained=1,
                close_inside_pred=1,
                atr_regime="atr_mid",
            )
        )

    assert pd.Series([row.predicted_high_offset_atr for row in rows]).nunique() > 1
    assert prediction_is_effectively_constant(pd.Series([row.predicted_high_offset_atr for row in rows]))
    assert calibration_bins("4H", 1, rows, 5) == []
    assert reliability_constant(pd.Series([base + 1e-14, base - 1e-14, base]))


def test_huber_delta_0005_is_outside_the_quadratic_zone_for_atr_residuals():
    delta = 0.005
    residuals = (0.21, 0.50, 0.89)
    assert all(abs(value) > delta for value in residuals)
    sample = np.abs(np.random.default_rng(1).normal(0.22, 0.18, 20000))
    assert float(np.mean(sample <= delta)) < 0.02
    assert range_huber_delta("pct") == 0.005
    assert range_huber_delta("atr") == 1.0
    assert all(abs(value) <= range_huber_delta("atr") for value in residuals)


def test_pair_mae_average_is_identical_to_flat_mae():
    error = np.random.default_rng(2).normal(size=(32, 10))
    flat = float(np.mean(np.abs(error)))
    pairs = [float(np.mean(np.abs(error[:, 2 * k : 2 * k + 2]))) for k in range(5)]
    assert float(np.mean(pairs)) == pytest.approx(flat)


def test_row_vector_band_uses_the_envelope_not_the_first_pair():
    raw = np.array([[0.2, -0.2, 1.5, -0.9]])
    high, low, reduction = reduce_range_band(split_range_pairs(raw[0]))
    assert (high, low, reduction) == (1.5, -0.9, "envelope_max_min")
    from scripts.audit_range_multistep_accuracy import range_raw_pair

    assert range_raw_pair(raw) == (1.5, -0.9)


def test_trainer_records_atr_units_without_compiling():
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

    trainer = WavenetTrainer(
        series=[[0.0, 0.0]],
        target_column=1,
        window_size=2,
        target_units="atr",
    )
    assert trainer._target_units == "atr"


def test_inspector_does_not_index_past_emitted_pairs():
    points, warning, emitted = build_range_path_points(
        [0.4, -0.2],
        requested_horizon=5,
        reference_close=2000.0,
        target_units="atr",
        atr_reference=3.0,
    )
    assert emitted == 1
    assert len(points) == 1
    assert points[0]["k"] == 1
    assert points[0]["high"] == pytest.approx(2000.0 + 0.4 * 3.0)
    assert "record horizon is 5" in warning
    assert "emits 1" in warning


def test_audit_atr_matches_training_atr_but_feature_ewm_seed_does_not():
    high = np.array([10, 11, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18], dtype=float)
    low = high - 1.5
    close = high - 0.4
    label = np.array(wilder_atr_series(high.tolist(), low.tolist(), close.tolist(), period=14))
    from scripts.audit_range_multistep_accuracy import wilder_atr

    assert np.max(np.abs(label - wilder_atr(high, low, close, period=14))) == 0.0

    frame = pd.DataFrame({"high": high, "low": low, "close": close})
    previous = frame["close"].shift(1)
    true_range = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - previous).abs(), (frame["low"] - previous).abs()],
        axis=1,
    ).max(axis=1)
    feature = true_range.ewm(alpha=1.0 / 14, adjust=False, min_periods=14).mean()
    assert abs(float(feature.iloc[13]) - float(label[13])) > 1e-6


def test_close_rel_is_dead_and_volume_columns_are_duplicated():
    bars = [candle(index, 100 + index, 102 + index, 99 + index, 101 + index) for index in range(4)]
    row = _candle_columns(bars, 2)

    assert row[3] == 0.0
    assert row[7] == row[13]
    scaled = minmax_scale_window([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    assert scaled == [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
