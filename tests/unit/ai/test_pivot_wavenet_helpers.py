"""Phase142A/B pivot WaveNet helper tests without TensorFlow."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
TRAIN_SCRIPT = SCRIPTS / "train_pivot_pattern_wavenet.py"
BACKTEST_SCRIPT = SCRIPTS / "backtest_pivot_pattern_wavenet.py"
WF_SCRIPT = SCRIPTS / "run_pivot_pattern_wavenet_walk_forward.py"


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def toy_flat(rows: int = 20) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC"),
            "open": [100.0] * rows,
            "high": [103.0] * rows,
            "low": [99.0] * rows,
            "close": [101.0] * rows,
            "volume": [1.0] * rows,
            "h4_atr_for_risk": [4.0] * rows,
        }
    )


def test_split_indices_respects_purge_gap():
    module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_wavenet")

    train, validation, test = module.split_indices(100, 0.6, 0.2, 5)

    assert train[0] == 0
    assert train[-1] == 59
    assert validation[0] == 65
    assert test[0] == 85


def test_normalize_train_only_uses_train_statistics():
    module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_wavenet")
    x = np.arange(4 * 3 * 2, dtype=np.float32).reshape(4, 3, 2)

    normalized, mean, std = module.normalize_train_only(x, [0, 1])

    assert normalized.shape == x.shape
    assert mean.shape == (1, 1, 2)
    assert std.shape == (1, 1, 2)
    assert float(normalized[:2].mean()) == pytest.approx(0.0, abs=1e-6)


def test_selected_action_uses_threshold_and_margin():
    module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_wavenet")
    probabilities = np.array(
        [
            [0.10, 0.20, 0.70],
            [0.70, 0.20, 0.10],
            [0.45, 0.35, 0.50],
        ],
        dtype=np.float32,
    )

    selected = module.selected_action(probabilities, 0.55, 0.55, 0.05)

    assert selected.tolist() == [2, 0, -1]


def test_backtest_runs_from_prediction_arrays():
    train_module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_wavenet")
    backtest = load_script(BACKTEST_SCRIPT, "backtest_pivot_pattern_wavenet")
    args = backtest.parse_args(
        [
            "--spread-mode",
            "fixed",
            "--spread-value",
            "0",
            "--buy-threshold",
            "0.5",
            "--sell-threshold",
            "0.5",
            "--min-margin",
            "0",
            "--bottom-threshold",
            "0.5",
            "--top-threshold",
            "0.5",
            "--tp-multiplier",
            "0.5",
            "--sl-multiplier",
            "0.5",
            "--hold-bars",
            "3",
        ]
    )
    flat = toy_flat(12)
    sample_positions = np.array([0, 4, 8], dtype=np.int64)
    predictions = {
        "action": np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        "top": np.array([[0.1], [0.9], [0.1]]),
        "bottom": np.array([[0.9], [0.1], [0.1]]),
        "buy_r": np.array([[1.0], [0.0], [0.0]]),
        "sell_r": np.array([[0.0], [1.0], [0.0]]),
    }

    report, trades = backtest.run_backtest(
        flat, sample_positions, predictions, args, {"payload": {}}
    )

    assert report.evaluated_samples == 3
    assert len(trades) == 2
    assert {trade.side for trade in trades} == {"BUY", "SELL"}
    assert report.trades == 2
    assert report.skipped_by_model == 1
    assert train_module.selected_action(predictions["action"], 0.5, 0.5, 0).tolist() == [2, 0, -1]


def test_walk_forward_parameter_grid_contains_side_and_risk_controls():
    module = load_script(WF_SCRIPT, "run_pivot_pattern_wavenet_walk_forward")
    args = module.parse_args(
        [
            "--buy-thresholds",
            "0.5",
            "--sell-thresholds",
            "0.6",
            "--margins",
            "0.1",
            "--top-thresholds",
            "0.7",
            "--bottom-thresholds",
            "0.8",
            "--min-r-values",
            "0.0",
            "--tp-multipliers",
            "1.0",
            "--sl-multipliers",
            "0.5",
            "--hold-bars",
            "24",
        ]
    )

    grid = module.parameter_grid(args)

    assert grid == [
        {
            "buy_threshold": 0.5,
            "sell_threshold": 0.6,
            "min_margin": 0.1,
            "top_threshold": 0.7,
            "bottom_threshold": 0.8,
            "min_buy_r": 0.0,
            "min_sell_r": 0.0,
            "tp_multiplier": 1.0,
            "sl_multiplier": 0.5,
            "hold_bars": 24,
        }
    ]
