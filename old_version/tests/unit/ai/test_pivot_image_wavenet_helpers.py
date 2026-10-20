"""Phase144A advanced pivot image WaveNet helper tests without TensorFlow."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_pivot_pattern_image_wavenet.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_pivot_pattern_image_wavenet", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_int_list_deduplicates_and_defaults():
    module = load_script()

    assert module.parse_int_list("1,2,4,4,8", [3]) == [1, 2, 4, 8]
    assert module.parse_int_list("", [3, 5]) == [3, 5]


def test_parse_args_defaults_to_advanced_wavenet_settings():
    module = load_script()

    args = module.parse_args([])

    assert args.model_id == "gold_pivot_pattern_image_wavenet_5m"
    assert args.activation == "tanh"
    assert args.spatial_kernels == "1,3,5"
    assert args.temporal_kernels == "3,5,9"
    assert args.dilations == "1,2,4,8,16,32"
    assert args.residual_blocks == 2
    assert args.checkpoint_each_epoch == "1"
