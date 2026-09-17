"""Phase144 advanced image WaveNet GUI command coverage."""

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


def test_train_advanced_image_wavenet_descriptor_exists():
    descriptor = descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_IMAGE_WAVENET)

    assert descriptor.label == "Train advanced pivot image WaveNet"
    fields = {field.name for field in descriptor.fields}
    assert {
        "spatial_kernels",
        "temporal_kernels",
        "dilations",
        "residual_blocks",
        "attention_heads",
        "se_ratio",
        "activation",
    } <= fields


def test_train_advanced_image_wavenet_passes_architecture_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.train_pivot_pattern_image_wavenet(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_IMAGE_WAVENET,
            {
                "tensor_path": "image.npy",
                "meta_path": "image_meta.npz",
                "activation": "tanh",
                "spatial_kernels": "1,3,5",
                "temporal_kernels": "3,5,9",
                "dilations": "1,2,4,8",
                "residual_blocks": "2",
                "checkpoint_each_epoch": "1",
                "batch_log_every": "1",
                "loader_mode": "stream",
                "stream_chunk_size": "128",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_image_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "image.npy"
    assert args[args.index("--meta-path") + 1] == "image_meta.npz"
    assert args[args.index("--activation") + 1] == "tanh"
    assert args[args.index("--spatial-kernels") + 1] == "1,3,5"
    assert args[args.index("--temporal-kernels") + 1] == "3,5,9"
    assert args[args.index("--dilations") + 1] == "1,2,4,8"
    assert args[args.index("--residual-blocks") + 1] == "2"
    assert args[args.index("--checkpoint-each-epoch") + 1] == "1"
    assert args[args.index("--batch-log-every") + 1] == "1"
    assert args[args.index("--loader-mode") + 1] == "stream"
    assert args[args.index("--stream-chunk-size") + 1] == "128"
