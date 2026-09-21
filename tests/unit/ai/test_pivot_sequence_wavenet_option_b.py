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


def test_grouped_batch_can_expand_each_branch_to_target_features():
    module = load_script()
    x = np.arange(2 * 5 * 6, dtype=np.float32).reshape(2, 5, 6)
    groups = module.OptionBGroups(
        m5_context=np.asarray([0, 1], dtype=np.int32),
        source_5m=np.asarray([2, 3], dtype=np.int32),
        htf_context=np.asarray([4, 5], dtype=np.int32),
    )
    mean = np.zeros((1, 1, 6), dtype=np.float32)
    std = np.ones((1, 1, 6), dtype=np.float32)

    batch = module.grouped_batch(
        x,
        groups,
        mean,
        std,
        branch_target_features=8,
        feature_augmentation_mode="causal",
        feature_augmentation_clip=8.0,
    )

    assert batch["m5_context_input"].shape == (2, 5, 8)
    assert batch["source_5m_input"].shape == (2, 5, 8)
    assert batch["htf_context_input"].shape == (2, 5, 8)
    assert np.max(np.abs(batch["m5_context_input"])) <= 8.0


def test_zero_feature_empty_flags_are_powershell_safe():
    module = load_script()

    args = module.parse_args([
        "--zero-feature-names",
        "--zero-feature-file",
        "--zero-feature-groups",
    ])

    assert args.zero_feature_names == ""
    assert args.zero_feature_file == ""
    assert args.zero_feature_groups == ""



def test_scoped_target_meta_ignores_scalar_target_metadata():
    module = load_script()
    meta = {
        "target_action": np.asarray([0, 1, 2, 1], dtype=np.int64),
        "target_top_zone": np.asarray([1, 0, 0, 0], dtype=np.float32),
        "target_bottom_zone": np.asarray([0, 0, 1, 0], dtype=np.float32),
        "target_buy_r": np.asarray([0.0, 0.1, 1.0, 0.0], dtype=np.float32),
        "target_sell_r": np.asarray([1.0, 0.1, 0.0, 0.0], dtype=np.float32),
        "target_mode": np.asarray(["first_hit_payoff"], dtype=object),
    }

    scoped = module.scoped_target_meta(meta, np.asarray([0, 2], dtype=np.int64), expected_rows=4)

    assert scoped["target_action"].tolist() == [0, 2]
    assert "target_mode" not in scoped



def test_parse_args_records_random_seed_default_and_override():
    module = load_script()

    default_args = module.parse_args([])
    custom_args = module.parse_args(["--random-seed", "123"])

    assert default_args.random_seed == 20260919
    assert custom_args.random_seed == 123



def test_option_b_report_accepts_random_seed():
    module = load_script()

    report = module.OptionBReport(
        model_id="m",
        version=1,
        tensor_path="x.npy",
        meta_path="x.npz",
        samples=1,
        train_rows=1,
        validation_rows=1,
        test_rows=1,
        stored_x_shape=[1, 2, 3],
        keras_input_shapes={},
        metrics={},
        architecture_features=[],
        feature_count=3,
        m5_context_feature_count=1,
        source_5m_feature_count=1,
        htf_feature_count=1,
        branch_target_features=0,
        feature_augmentation_mode="off",
        feature_augmentation_clip=8.0,
        random_seed=123,
        zeroed_feature_count=0,
        zeroed_feature_names=[],
        zeroed_feature_groups=[],
        model_path="m.keras",
        record_path="m.json",
        architecture_json_path="a.json",
        model_summary_path="s.txt",
        epoch_checkpoint_path="c.keras",
        batch_log_path="b.jsonl",
        nonfinite_input_values=0,
        output_json="latest.json",
        output_html="latest.html",
        production_status="blocked",
    )

    assert report.random_seed == 123
