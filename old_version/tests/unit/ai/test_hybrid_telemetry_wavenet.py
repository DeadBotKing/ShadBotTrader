"""Phase129 telemetry WaveNet/TCN helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TRAIN_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_hybrid_telemetry_wavenet.py"
BACKTEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_telemetry_wavenet.py"
)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_split_indices_applies_purge_gap_between_sets():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_wavenet")

    train, val, test = module.split_indices(100, train_frac=0.60, val_frac=0.20, purge_gap=5)

    assert train[-1] == 59
    assert val[0] == 65
    assert test[0] == 85


def test_normalize_train_only_uses_training_slice_statistics():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_wavenet")
    x_values = np.arange(24, dtype=np.float32).reshape(4, 3, 2)

    normalized, mean, std = module.normalize_train_only(x_values, [0, 1])

    assert mean.shape == (1, 1, 2)
    assert std.shape == (1, 1, 2)
    assert float(np.mean(normalized[[0, 1]])) == pytest.approx(0.0, abs=1e-6)


def test_selected_indices_can_keep_only_candidates():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_wavenet")
    mask = np.asarray([0, 1] * 60, dtype=np.float32)
    data = {"X": np.zeros((120, 2, 1)), "candidate_mask": mask}

    indices = module.selected_indices(data, candidate_only="1", max_samples=0)

    assert indices.tolist() == list(range(1, 120, 2))


def test_wavenet_backtest_gate_modes():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_telemetry_wavenet")

    assert module.passes_gate(0.60, -0.1, module.TelemetryWaveNetThresholds(0.55, 0.0, "meta", "t"))
    assert not module.passes_gate(
        0.60, -0.1, module.TelemetryWaveNetThresholds(0.55, 0.0, "both", "t")
    )
    assert module.passes_gate(0.10, 0.2, module.TelemetryWaveNetThresholds(0.55, 0.0, "score", "t"))


def test_wavenet_backtest_skips_while_position_is_open():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_telemetry_wavenet")
    flat = pd.DataFrame(
        {
            "timestamp": ["t0", "t1", "t4"],
            "source_index": [0, 1, 4],
            "target_exit_index": [3, 3, 5],
            "target_side": [1, 1, -1],
            "target_trade_pnl": [10.0, 8.0, -2.0],
            "target_trade_win": [1, 1, 0],
            "target_outcome_code": [1, 1, -1],
            "candidate_entry_price": [2000.0, 2001.0, 2002.0],
            "candidate_take_profit": [2010.0, 2011.0, 1990.0],
            "candidate_stop_loss": [1990.0, 1991.0, 2010.0],
        }
    )
    flat_by_source = {int(row["source_index"]): row for _, row in flat.iterrows()}

    summary, counters, trades = module.backtest(
        np.array([0, 1, 4]),
        np.array([1, 1, 1], dtype=np.float32),
        np.array([0.9, 0.9, 0.9]),
        np.array([0.1, 0.1, 0.1]),
        flat_by_source,
        module.TelemetryWaveNetThresholds(0.55, 0.0, "meta", "test"),
    )

    assert summary.trades == 2
    assert counters.skipped_while_open == 1
    assert summary.total_pnl == pytest.approx(8.0)
    assert [trade.source_index for trade in trades] == [0, 4]
