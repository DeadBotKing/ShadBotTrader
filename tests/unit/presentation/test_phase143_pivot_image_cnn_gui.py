"""Phase143 image tensor/CNN GUI command coverage."""

from __future__ import annotations

import sys
import types

import pytest

from ShadBotTrader.presentation.commands import Command, CommandKind, CommandResult, CommandStatus
from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers, descriptor_for


@pytest.fixture
def gui(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "tensorflow", types.ModuleType("tensorflow"))
    monkeypatch.setattr(
        "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
        lambda root: ["5M", "1H", "4H", "1D"],
    )
    return AccountCommandHandlers(tmp_path / "x.db", tmp_path / "datasets")


def capture(monkeypatch, handlers):
    captured = {}

    def fake_run_script(command, arguments, success_message, started, **kwargs):
        captured["args"] = list(arguments)
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(handlers, "_run_script", fake_run_script)
    return captured


def test_phase143_descriptors_exist():
    assert (
        descriptor_for(CommandKind.BUILD_PIVOT_PATTERN_IMAGE_TENSOR).label
        == "Build pivot image tensor"
    )
    assert (
        descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_IMAGE_CNN).label == "Train pivot image CNN"
    )


def test_build_image_tensor_passes_4d_shape_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.build_pivot_pattern_image_tensor(
        Command(
            CommandKind.BUILD_PIVOT_PATTERN_IMAGE_TENSOR,
            {"window_size": "100", "max_5m_features": "24", "max_htf_features": "16"},
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/build_pivot_pattern_image_tensor.py"
    assert args[args.index("--source-mode") + 1] == "storage"
    assert args[args.index("--window-size") + 1] == "100"
    assert args[args.index("--max-5m-features") + 1] == "24"
    assert args[args.index("--max-htf-features") + 1] == "16"
    assert args[args.index("--axis-normalization") + 1] == "robust"
    assert args[args.index("--feature-clip") + 1] == "8.0"
    assert args[args.index("--interaction-clip") + 1] == "32.0"


def test_train_image_cnn_passes_conv_kind_and_tensor_paths(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.train_pivot_pattern_image_cnn(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_IMAGE_CNN,
            {
                "tensor_path": "image.npy",
                "meta_path": "image_meta.npz",
                "model_kind": "conv3d",
                "epochs": "9",
                "loader_mode": "stream",
                "stream_chunk_size": "128",
                "checkpoint_each_epoch": "1",
                "batch_log_every": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_image_cnn.py"
    assert args[args.index("--tensor-path") + 1] == "image.npy"
    assert args[args.index("--meta-path") + 1] == "image_meta.npz"
    assert args[args.index("--model-kind") + 1] == "conv3d"
    assert args[args.index("--epochs") + 1] == "9"
    assert args[args.index("--loader-mode") + 1] == "stream"
    assert args[args.index("--stream-chunk-size") + 1] == "128"
    assert args[args.index("--checkpoint-each-epoch") + 1] == "1"
    assert args[args.index("--batch-log-every") + 1] == "1"


def test_audit_image_tensor_descriptor_exists():
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_PATTERN_IMAGE_TENSOR).label
        == "Audit pivot image tensor health"
    )


def test_audit_image_tensor_passes_health_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_pattern_image_tensor(
        Command(
            CommandKind.AUDIT_PIVOT_PATTERN_IMAGE_TENSOR,
            {
                "tensor_path": "image.npy",
                "meta_path": "image_meta.npz",
                "flat_path": "image_flat.parquet",
                "full_scan": "1",
                "chunk_size": "128",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_pattern_image_tensor.py"
    assert args[args.index("--tensor-path") + 1] == "image.npy"
    assert args[args.index("--meta-path") + 1] == "image_meta.npz"
    assert args[args.index("--flat-path") + 1] == "image_flat.parquet"
    assert args[args.index("--full-scan") + 1] == "1"
    assert args[args.index("--chunk-size") + 1] == "128"
