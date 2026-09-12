"""Phase131 telemetry PatchTST helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TRAIN_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "train_hybrid_telemetry_patchtst.py"
)
BACKTEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_telemetry_patchtst.py"
)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_patch_count_matches_patch_len_and_stride():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_patchtst")

    assert module.patch_count(time_steps=150, patch_len=16, stride=8) == 17
    assert module.patch_count(time_steps=288, patch_len=16, stride=8) == 35


def test_patch_validation_rejects_invalid_lengths():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_patchtst")

    with pytest.raises(RuntimeError, match="patch-len"):
        module.validate_patch_args(time_steps=10, patch_len=16, stride=4)
    with pytest.raises(RuntimeError, match="stride"):
        module.validate_patch_args(time_steps=10, patch_len=4, stride=0)


def test_patchtst_parser_defaults_to_multihead_model():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_patchtst")

    args = module.parse_args([])

    assert args.model_id == "gold_hybrid_telemetry_patchtst_5m"
    assert args.task == "multihead"
    assert args.patch_len == 16
    assert args.stride == 8


def test_monitor_name_matches_task_defaults():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_patchtst")

    assert (
        module.monitor_name(SimpleNamespace(task="classifier", monitor_metric="auto")) == "val_ap"
    )
    assert (
        module.monitor_name(SimpleNamespace(task="regressor", monitor_metric="auto")) == "val_mae"
    )
    assert (
        module.monitor_name(SimpleNamespace(task="multihead", monitor_metric="auto")) == "val_loss"
    )


def test_backtest_parser_uses_patchtst_defaults():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_telemetry_patchtst")

    args = module.parse_args([])

    assert args.model_id == "gold_hybrid_telemetry_patchtst_5m"
    assert args.decision_mode == "meta"
    assert str(args.output_dir).endswith("hybrid_telemetry_patchtst_backtest")
