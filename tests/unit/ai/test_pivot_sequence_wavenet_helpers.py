"""Phase145A sequence WaveNet helper tests without TensorFlow."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_pivot_pattern_sequence_wavenet.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_pivot_pattern_sequence_wavenet", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_grouped_indices_uses_feature_groups():
    module = load_script()
    meta = {
        "feature_names": np.array(["m5_a", "h4_a", "d1_a", "src5m_extra", "other"], dtype=object),
        "feature_groups": np.array(
            ["generated_5m", "closed_4h", "closed_1d", "source_5m", "other"], dtype=object
        ),
    }

    m5, htf, all_idx = module.grouped_indices(meta)

    assert m5.tolist() == [0, 3]
    assert htf.tolist() == [1, 2]
    assert all_idx.tolist() == [0, 1, 2, 3, 4]


def test_streaming_sequence_scaler_matches_memory_scaler():
    module = load_script()
    x = np.arange(6 * 3 * 2, dtype=np.float32).reshape(6, 3, 2)
    rows = np.array([0, 1, 2, 3], dtype=np.int64)

    _normalized, memory_mean, memory_std, _bad = module.normalize_train_only_sequence(
        x[rows], range(4)
    )
    stream_mean, stream_std, stream_bad = module.compute_streaming_scaler_sequence(x, rows, 2)

    assert stream_bad == 0
    np.testing.assert_allclose(stream_mean, memory_mean, rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(stream_std, memory_std, rtol=1e-6, atol=1e-6)


def test_parse_args_defaults_to_stream_and_tanh():
    module = load_script()

    args = module.parse_args([])

    assert args.model_id == "gold_pivot_pattern_sequence_wavenet_5m"
    assert args.loader_mode == "stream"
    assert args.activation == "tanh"
    assert args.temporal_kernels == "3,5,9"
    assert args.dilations == "1,2,4,8,16,32"
