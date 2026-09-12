"""Phase130 telemetry TSMixer helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

TRAIN_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_hybrid_telemetry_tsmixer.py"
BACKTEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_telemetry_tsmixer.py"
)
WAVENET_BACKTEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_telemetry_wavenet.py"
)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tsmixer_parser_defaults_to_multihead_model():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_tsmixer")

    args = module.parse_args([])

    assert args.model_id == "gold_hybrid_telemetry_tsmixer_5m"
    assert args.task == "multihead"
    assert args.mixer_layers == 4


def test_monitor_name_matches_task_defaults():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_tsmixer")

    assert (
        module.monitor_name(SimpleNamespace(task="classifier", monitor_metric="auto")) == "val_ap"
    )
    assert (
        module.monitor_name(SimpleNamespace(task="regressor", monitor_metric="auto")) == "val_mae"
    )
    assert (
        module.monitor_name(SimpleNamespace(task="multihead", monitor_metric="auto")) == "val_loss"
    )


def test_backtest_parser_uses_tsmixer_defaults():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_telemetry_tsmixer")

    args = module.parse_args([])

    assert args.model_id == "gold_hybrid_telemetry_tsmixer_5m"
    assert args.decision_mode == "meta"
    assert str(args.output_dir).endswith("hybrid_telemetry_tsmixer_backtest")


def test_tsmixer_block_requires_positive_hidden_units_in_args():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_telemetry_tsmixer")

    args = module.parse_args(["--mixer-layers", "2", "--time-hidden-units", "16"])

    assert max(args.mixer_layers, 1) == 2
    assert max(args.time_hidden_units, 1) == 16


def test_backtest_reuses_gate_modes():
    module = load_script(WAVENET_BACKTEST_SCRIPT, "backtest_hybrid_telemetry_wavenet")
    thresholds = module.TelemetryWaveNetThresholds(0.55, 0.10, "both", "test")

    assert module.passes_gate(0.60, 0.20, thresholds)
    assert not module.passes_gate(0.60, 0.05, thresholds)
    assert not module.passes_gate(0.50, 0.20, thresholds)
