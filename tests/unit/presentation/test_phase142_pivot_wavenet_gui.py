"""Phase142 pivot tensor/WaveNet GUI command coverage."""

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
        captured["timeout"] = kwargs.get("timeout")
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(handlers, "_run_script", fake_run_script)
    return captured


def test_phase142_descriptors_exist():
    assert (
        descriptor_for(CommandKind.BUILD_PIVOT_PATTERN_TENSOR).label == "Build pivot pattern tensor"
    )
    assert (
        descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_WAVENET).label
        == "Train pivot WaveNet pattern model"
    )
    assert (
        descriptor_for(CommandKind.BACKTEST_PIVOT_PATTERN_WAVENET).label
        == "Backtest pivot WaveNet pattern model"
    )
    assert (
        descriptor_for(CommandKind.RUN_PIVOT_PATTERN_WAVENET_WALK_FORWARD).label
        == "Run pivot WaveNet walk-forward"
    )


def test_build_pivot_pattern_tensor_passes_storage_and_shape_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.build_pivot_pattern_tensor(
        Command(
            CommandKind.BUILD_PIVOT_PATTERN_TENSOR,
            {"symbol": "XAUUSD", "tensor_window": "288", "dtype": "float16"},
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/build_pivot_pattern_tensor.py"
    assert args[args.index("--source-mode") + 1] == "storage"
    assert args[args.index("--tensor-window") + 1] == "288"
    assert args[args.index("--dtype") + 1] == "float16"


def test_train_pivot_wavenet_passes_keras_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.train_pivot_pattern_wavenet(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_WAVENET,
            {"tensor_path": "tensor.npz", "epochs": "7", "filters": "16", "n_layers": "3"},
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--epochs") + 1] == "7"
    assert args[args.index("--filters") + 1] == "16"
    assert args[args.index("--n-layers") + 1] == "3"


def test_backtest_pivot_wavenet_passes_replay_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.backtest_pivot_pattern_wavenet(
        Command(
            CommandKind.BACKTEST_PIVOT_PATTERN_WAVENET,
            {"tensor_path": "tensor.npz", "flat_path": "flat.parquet", "eval_frac": "0.25"},
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_pivot_pattern_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--eval-frac") + 1] == "0.25"


def test_pivot_wavenet_walk_forward_passes_fold_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.run_pivot_pattern_wavenet_walk_forward(
        Command(
            CommandKind.RUN_PIVOT_PATTERN_WAVENET_WALK_FORWARD,
            {
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "max_folds": "2",
                "epochs": "5",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_pivot_pattern_wavenet_walk_forward.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--max-folds") + 1] == "2"
    assert args[args.index("--epochs") + 1] == "5"
