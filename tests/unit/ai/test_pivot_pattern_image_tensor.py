"""Phase143A 4D pivot image tensor tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_pivot_pattern_image_tensor.py"
TRAIN_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_pivot_pattern_image_cnn.py"


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_image_tensor_sample_indices_roll_forward_stride_one():
    module = load_script(SCRIPT, "build_pivot_pattern_image_tensor")

    indices = module.sample_indices(rows=8, window_size=3, sample_stride=1, max_samples=0)

    assert indices.tolist() == [2, 3, 4, 5, 6, 7]


def test_image_tensor_cell_is_5m_htf_interaction(tmp_path):
    module = load_script(SCRIPT, "build_pivot_pattern_image_tensor")
    five = module.add_bias(np.array([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]], dtype=np.float32))
    htf = module.add_bias(np.array([[10.0], [20.0], [30.0]], dtype=np.float32))
    out = tmp_path / "x.npy"

    tensor = module.build_image_tensor_memmap(
        five, htf, np.array([1, 2]), out, 2, "float32", 8, 1000.0
    )

    assert tensor.shape == (2, 2, 3, 2)
    # sample 0, timestep 0: [bias,2,3] outer [bias,10]
    np.testing.assert_allclose(tensor[0, 0], np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]]))
    # sample 1, timestep 1: [bias,6,7] outer [bias,30]
    np.testing.assert_allclose(tensor[1, 1], np.array([[1.0, 30.0], [6.0, 180.0], [7.0, 210.0]]))


def test_image_tensor_report_shapes(tmp_path):
    module = load_script(SCRIPT, "build_pivot_pattern_image_tensor")
    args = module.parse_args(
        ["--window-size", "10", "--max-5m-features", "2", "--max-htf-features", "3"]
    )
    frame = pd.DataFrame({"target_action": [0, 1, 2]})

    report = module.build_report(
        args,
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(3)),
        frame,
        [5, 10, 3, 4],
        tmp_path / "x.npy",
        tmp_path / "m.npz",
        tmp_path / "f.parquet",
        tmp_path / "r.json",
        tmp_path / "r.html",
        "note",
        ["f1", "f2"],
        ["h1", "h2", "h3"],
        0,
        0,
    )

    assert report.stored_x_shape == [5, 10, 3, 4]
    assert report.conv2d_batch_shape == "[batch, 10, 3, 4]"
    assert report.conv3d_batch_shape == "[batch, 10, 3, 4, 1]"


def test_image_cnn_expands_only_for_conv3d():
    module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_image_cnn")
    x = np.zeros((4, 10, 3, 2), dtype=np.float32)

    assert module.maybe_expand_conv3d(x, "conv2d").shape == (4, 10, 3, 2)
    assert module.maybe_expand_conv3d(x, "conv3d").shape == (4, 10, 3, 2, 1)


def test_image_cnn_split_indices_has_purge_gap():
    module = load_script(TRAIN_SCRIPT, "train_pivot_pattern_image_cnn")

    train, validation, test = module.split_indices(100, 0.6, 0.2, 5)

    assert train[-1] == 59
    assert validation[0] == 65
    assert test[0] == 85


def test_axis_normalize_sanitizes_inf_nan_and_clips():
    module = load_script(SCRIPT, "build_pivot_pattern_image_tensor")
    values = np.array(
        [[1.0, np.nan], [2.0, np.inf], [1000.0, -np.inf]],
        dtype=np.float32,
    )

    normalized, center, scale, nonfinite = module.axis_normalize(values, "robust", 2.0)

    assert nonfinite == 3
    assert np.isfinite(normalized).all()
    assert np.isfinite(center).all()
    assert np.isfinite(scale).all()
    assert float(normalized.max()) <= 2.0
    assert float(normalized.min()) >= -2.0


def test_streaming_scaler_matches_memory_scaler():
    from train_pivot_pattern_image_cnn import compute_streaming_scaler, normalize_train_only

    x = np.arange(6 * 3 * 2 * 2, dtype=np.float32).reshape(6, 3, 2, 2)
    indices = np.array([0, 1, 2, 3], dtype=np.int64)

    _normalized, memory_mean, memory_std, _memory_bad = normalize_train_only(x[indices], range(4))
    stream_mean, stream_std, stream_bad = compute_streaming_scaler(x, indices, chunk_size=2)

    assert stream_bad == 0
    np.testing.assert_allclose(stream_mean, memory_mean, rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(stream_std, memory_std, rtol=1e-6, atol=1e-6)
