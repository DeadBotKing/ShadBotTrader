"""Phase147A Option B grouped sequence WaveNet helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_pivot_pattern_sequence_wavenet_option_b.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_pivot_pattern_sequence_wavenet_option_b", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_option_b_groups_split_feature_groups():
    module = load_script()
    meta = {
        "feature_names": np.asarray(["m5_ret1", "session_hour_sin", "src5m_alpha", "h4_ret1", "d1_ret1"], dtype=object),
        "feature_groups": np.asarray(["generated_5m", "session", "source_5m", "closed_4h", "closed_1d"], dtype=object),
    }

    groups = module.option_b_groups(meta)

    assert groups.m5_context.tolist() == [0, 1]
    assert groups.source_5m.tolist() == [2]
    assert groups.htf_context.tolist() == [3, 4]


def test_grouped_batch_normalizes_and_splits():
    module = load_script()
    x = np.arange(2 * 3 * 5, dtype=np.float32).reshape(2, 3, 5)
    groups = module.OptionBGroups(
        m5_context=np.asarray([0, 1], dtype=np.int32),
        source_5m=np.asarray([2], dtype=np.int32),
        htf_context=np.asarray([3, 4], dtype=np.int32),
    )
    mean = np.zeros((1, 1, 5), dtype=np.float32)
    std = np.ones((1, 1, 5), dtype=np.float32)

    batch = module.grouped_batch(x, groups, mean, std)

    assert batch["m5_context_input"].shape == (2, 3, 2)
    assert batch["source_5m_input"].shape == (2, 3, 1)
    assert batch["htf_context_input"].shape == (2, 3, 2)
    np.testing.assert_allclose(batch["source_5m_input"][:, :, 0], x[:, :, 2])
