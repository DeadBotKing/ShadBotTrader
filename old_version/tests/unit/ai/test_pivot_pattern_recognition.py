"""Phase141A pivot pattern-recognition helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_pivot_pattern_recognition.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_pivot_pattern_recognition", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def toy_ohlcv(rows: int = 80) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC")
    close = np.linspace(100.0, 105.0, rows)
    if rows >= 65:
        close[20:30] = np.linspace(105.0, 110.0, 10)
        close[30:45] = np.linspace(110.0, 98.0, 15)
        close[55:65] = np.linspace(96.0, 104.0, 10)
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
            "volume": 100,
            "h4_atr_for_risk": 4.0,
            "row_id": np.arange(rows),
        }
    )


def test_pivot_labels_mark_top_and_bottom_zones():
    module = load_script()
    frame = toy_ohlcv()
    config = module.PivotLabelConfig(
        lookahead_bars=16,
        pivot_move_atr=0.75,
        pivot_zone_atr=0.40,
        recent_window_bars=12,
        min_direction_edge=1.05,
    )

    labelled = module.label_pivot_targets(frame, config)

    assert int(labelled["target_top_zone"].sum()) > 0
    assert int(labelled["target_bottom_zone"].sum()) > 0
    assert set(labelled["target_action"].unique()) <= {
        module.ACTION_SELL,
        module.ACTION_HOLD,
        module.ACTION_BUY,
    }


def test_feature_ranking_finds_predictive_feature():
    module = load_script()
    frame = pd.DataFrame(
        {
            "target_action": [module.ACTION_SELL] * 20 + [module.ACTION_HOLD] * 20,
            "target_top_zone": [1.0] * 20 + [0.0] * 20,
            "target_bottom_zone": [0.0] * 40,
            "useful": [10.0] * 20 + [0.0] * 20,
            "noise": [1.0, 0.0] * 20,
        }
    )

    selected, ranking = module.selected_features(frame, ["noise", "useful"], 1)

    assert selected == ["useful"]
    assert ranking[0][0] == "useful"


def test_centroid_pattern_model_predicts_aligned_probabilities():
    module = load_script()
    x_train = np.array([[0.0], [0.1], [5.0], [5.1], [10.0], [10.1]])
    y_train = np.array(
        [
            module.ACTION_SELL,
            module.ACTION_SELL,
            module.ACTION_HOLD,
            module.ACTION_HOLD,
            module.ACTION_BUY,
            module.ACTION_BUY,
        ]
    )
    model = module.CentroidPatternModel().fit(x_train, y_train)

    probabilities = module.aligned_predict_proba(model, np.array([[0.05], [10.05]]))

    assert probabilities.shape == (2, 3)
    assert probabilities[0].argmax() == module.ACTION_SELL
    assert probabilities[1].argmax() == module.ACTION_BUY
    assert probabilities.sum(axis=1).tolist() == pytest.approx([1.0, 1.0])


def test_strategy_simulation_uses_next_bar_and_single_position():
    module = load_script()
    args = module.parse_args(
        [
            "--spread-mode",
            "fixed",
            "--spread-value",
            "0",
            "--risk-per-trade",
            "0.01",
            "--initial-capital",
            "100",
        ]
    )
    frame = toy_ohlcv(80).iloc[:10].copy()
    frame.loc[:, "open"] = 100.0
    frame.loc[:, "high"] = 103.0
    frame.loc[:, "low"] = 99.0
    frame.loc[:, "close"] = 101.0
    signal_frame = frame.iloc[:3].copy()
    probabilities = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ]
    )
    params = {
        "buy_threshold": 0.5,
        "sell_threshold": 0.5,
        "margin": 0.0,
        "tp_multiplier": 0.5,
        "sl_multiplier": 0.5,
        "hold_bars": 3,
    }

    result, trades = module.simulate_strategy(
        frame, signal_frame, probabilities, params, args, 100.0, 1
    )

    assert result["trades"] >= 1
    assert trades[0].entry_row_id == 1
    assert trades[0].outcome == "take_profit"
    assert trades[0].cash_pnl > 0


def test_main_writes_outputs_with_file_source(tmp_path):
    module = load_script()
    out_dir = tmp_path / "out"
    five = toy_ohlcv(1600).drop(columns=["h4_atr_for_risk", "row_id"])
    wave = 100.0 + 5.0 * np.sin(np.arange(len(five)) / 28.0)
    five["close"] = wave
    five["open"] = np.roll(wave, 1)
    five.loc[five.index[0], "open"] = wave[0]
    five["high"] = wave + 0.8
    five["low"] = wave - 0.8
    hourly = (
        five.set_index("timestamp")
        .resample("1h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    daily = (
        five.set_index("timestamp")
        .resample("1d")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    # Extend daily history so the daily rolling features have a closed prior day.
    daily = pd.concat([daily] * 30, ignore_index=True)
    daily["timestamp"] = pd.date_range("2025-12-01", periods=len(daily), freq="1d", tz="UTC")
    five_path = tmp_path / "five.csv"
    hourly_path = tmp_path / "hourly.csv"
    daily_path = tmp_path / "daily.csv"
    five.to_csv(five_path, index=False)
    hourly.to_csv(hourly_path, index=False)
    daily.to_csv(daily_path, index=False)

    result = module.main(
        [
            "--source-mode",
            "files",
            "--daily-path",
            str(daily_path),
            "--hourly-path",
            str(hourly_path),
            "--five-path",
            str(five_path),
            "--output-dir",
            str(out_dir),
            "--model-kind",
            "centroid",
            "--train-days-min",
            "2",
            "--validation-days",
            "1",
            "--test-days",
            "1",
            "--purge-hours",
            "0",
            "--lookahead-bars",
            "12",
            "--pivot-move-atr",
            "0.10",
            "--pivot-zone-atr",
            "1.00",
            "--min-direction-edge",
            "1.00",
            "--recent-window-bars",
            "8",
            "--max-features",
            "6",
            "--buy-thresholds",
            "0.3",
            "--sell-thresholds",
            "0.3",
            "--margins",
            "0",
            "--tp-multipliers",
            "0.5",
            "--sl-multipliers",
            "0.5",
            "--hold-bars",
            "6",
            "--min-validation-trades",
            "0",
            "--save-model",
            "0",
            "--save-data",
            "0",
        ]
    )

    assert result == 0
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "latest.html").exists()
    assert (out_dir / "latest_folds.csv").exists()
    assert (out_dir / "latest_trades.csv").exists()
    assert (out_dir / "latest_features.csv").exists()


def test_storage_source_reads_project_processed_parquets(tmp_path):
    module = load_script()
    storage = tmp_path / "datasets"
    five = toy_ohlcv(96).drop(columns=["h4_atr_for_risk", "row_id"])
    hourly = (
        five.set_index("timestamp")
        .resample("1h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    daily = (
        five.set_index("timestamp")
        .resample("1d")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    # Match the project's stored parquet schema: open_time instead of timestamp.
    for timeframe, frame in (("5M", five), ("1H", hourly), ("1D", daily)):
        out = frame.rename(columns={"timestamp": "open_time"})
        directory = storage / "processed" / "XAUUSD" / timeframe
        directory.mkdir(parents=True, exist_ok=True)
        out.to_parquet(directory / "v1.parquet", index=False)

    args = module.parse_args(
        [
            "--source-mode",
            "storage",
            "--symbol",
            "XAUUSD",
            "--storage-root",
            str(storage),
        ]
    )

    loaded_daily, loaded_h4, loaded_five, note = module.load_market_data(args)

    assert len(loaded_daily) == len(daily)
    assert len(loaded_five) == len(five)
    assert len(loaded_h4) > 0
    assert "Project storage datasets" in note
    assert "resampled from stored 1H" in note
