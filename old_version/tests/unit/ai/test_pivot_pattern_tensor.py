"""Phase142A pivot-pattern tensor builder tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_pivot_pattern_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("build_pivot_pattern_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sample_indices_start_at_complete_window_and_stride():
    module = load_script()

    indices = module.sample_indices(rows=10, tensor_window=4, sample_stride=2, max_samples=0)

    assert indices.tolist() == [3, 5, 7, 9]


def test_build_tensor_array_uses_past_window_only():
    module = load_script()
    frame = pd.DataFrame(
        {
            "a": np.arange(6, dtype=np.float32),
            "b": np.arange(10, 16, dtype=np.float32),
        }
    )

    tensor = module.build_tensor_array(frame, ["a", "b"], [2, 4], 3, "float32")

    assert tensor.shape == (2, 3, 2)
    assert tensor[0, :, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert tensor[1, :, 1].tolist() == pytest.approx([12.0, 13.0, 14.0])


def test_target_r_values_are_directional_and_clipped():
    module = load_script()
    frame = pd.DataFrame(
        {
            "future_up_r": [2.0, 0.5, 10.0],
            "future_down_r": [0.5, 2.0, 1.0],
        }
    )

    assert module.target_buy_r(frame).tolist() == pytest.approx([1.5, -1.5, 3.0])
    assert module.target_sell_r(frame).tolist() == pytest.approx([-1.5, 1.5, -3.0])


def test_tensor_report_records_stored_and_keras_shapes(tmp_path):
    module = load_script()
    args = module.parse_args(["--tensor-window", "4", "--dtype", "float32"])
    frame = pd.DataFrame(
        {
            "target_available": [1.0, 1.0],
            "target_action": [module.ACTION_SELL if hasattr(module, "ACTION_SELL") else 0, 2],
        }
    )
    tensor = np.zeros((2, 4, 3), dtype=np.float32)

    report = module.build_report(
        args,
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(2)),
        frame,
        ["a", "b", "c"],
        tensor,
        tmp_path / "x.npz",
        tmp_path / "x.parquet",
        tmp_path / "x.json",
        tmp_path / "x.html",
        "note",
        [],
    )

    assert report.stored_x_shape == [2, 4, 3]
    assert report.keras_batch_shape == "[batch, 4, 3]"
