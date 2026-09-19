"""Phase145 sequence tensor/WaveNet GUI command coverage."""

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


def test_phase145_descriptors_exist():
    assert (
        descriptor_for(CommandKind.BUILD_PIVOT_PATTERN_SEQUENCE_TENSOR).label
        == "Build pivot sequence tensor"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_PATTERN_SEQUENCE_TENSOR).label
        == "Audit pivot sequence tensor health"
    )
    assert (
        descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_SEQUENCE_WAVENET).label
        == "Train pivot sequence WaveNet"
    )
    assert (
        descriptor_for(CommandKind.BACKTEST_PIVOT_PATTERN_SEQUENCE_WAVENET).label
        == "Backtest pivot sequence WaveNet PnL"
    )
    assert (
        descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_SEQUENCE_WAVENET_OPTION_B).label
        == "Train pivot sequence WaveNet Option B"
    )
    assert (
        descriptor_for(CommandKind.BACKTEST_PIVOT_PATTERN_SEQUENCE_WAVENET_RANGE).label
        == "Backtest sequence WaveNet range-aware archive"
    )


def test_build_sequence_tensor_passes_option_a_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.build_pivot_pattern_sequence_tensor(
        Command(
            CommandKind.BUILD_PIVOT_PATTERN_SEQUENCE_TENSOR,
            {"window_size": "100", "include_source_5m_features": "1", "max_features": "0"},
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/build_pivot_pattern_sequence_tensor.py"
    assert args[args.index("--source-mode") + 1] == "storage"
    assert args[args.index("--window-size") + 1] == "100"
    assert args[args.index("--include-source-5m-features") + 1] == "1"
    assert "--source-5m-feature-path" in args
    assert args[args.index("--source-5m-feature-path") + 1] == ""
    assert args[args.index("--max-features") + 1] == "0"


def test_audit_sequence_tensor_passes_health_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_pattern_sequence_tensor(
        Command(
            CommandKind.AUDIT_PIVOT_PATTERN_SEQUENCE_TENSOR,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "flat_path": "seq_flat.parquet",
                "full_scan": "1",
                "chunk_size": "128",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_pattern_sequence_tensor.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--flat-path") + 1] == "seq_flat.parquet"
    assert args[args.index("--full-scan") + 1] == "1"
    assert args[args.index("--chunk-size") + 1] == "128"


def test_train_sequence_wavenet_passes_stream_and_architecture_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.train_pivot_pattern_sequence_wavenet(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_SEQUENCE_WAVENET,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "loader_mode": "stream",
                "stream_chunk_size": "128",
                "activation": "tanh",
                "temporal_kernels": "3,5,9",
                "dilations": "1,2,4,8",
                "batch_log_every": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_sequence_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--loader-mode") + 1] == "stream"
    assert args[args.index("--stream-chunk-size") + 1] == "128"
    assert args[args.index("--activation") + 1] == "tanh"
    assert args[args.index("--temporal-kernels") + 1] == "3,5,9"
    assert args[args.index("--dilations") + 1] == "1,2,4,8"
    assert args[args.index("--batch-log-every") + 1] == "1"


def test_backtest_sequence_wavenet_passes_phase146_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.backtest_pivot_pattern_sequence_wavenet(
        Command(
            CommandKind.BACKTEST_PIVOT_PATTERN_SEQUENCE_WAVENET,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "flat_path": "seq_flat.parquet",
                "eval_split": "test",
                "top_threshold": "0",
                "bottom_threshold": "0",
                "tp_multiplier": "0.75",
                "sl_multiplier": "0.75",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_pivot_pattern_sequence_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--flat-path") + 1] == "seq_flat.parquet"
    assert args[args.index("--eval-split") + 1] == "test"
    assert args[args.index("--top-threshold") + 1] == "0.0"
    assert args[args.index("--bottom-threshold") + 1] == "0.0"
    assert args[args.index("--tp-multiplier") + 1] == "0.75"
    assert args[args.index("--sl-multiplier") + 1] == "0.75"


def test_train_sequence_wavenet_option_b_passes_grouped_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.train_pivot_pattern_sequence_wavenet_option_b(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_SEQUENCE_WAVENET_OPTION_B,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "model_id": "option_b",
                "max_samples": "24000",
                "branch_target_features": "180",
                "feature_augmentation_mode": "causal",
                "feature_augmentation_clip": "8",
                "temporal_kernels": "3,5,9",
                "dilations": "1,2,4,8",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_sequence_wavenet_option_b.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--model-id") + 1] == "option_b"
    assert args[args.index("--max-samples") + 1] == "24000"
    assert args[args.index("--branch-target-features") + 1] == "180"
    assert args[args.index("--feature-augmentation-mode") + 1] == "causal"
    assert args[args.index("--feature-augmentation-clip") + 1] == "8.0"
    assert args[args.index("--temporal-kernels") + 1] == "3,5,9"
    assert args[args.index("--dilations") + 1] == "1,2,4,8"


def test_range_archive_backtest_passes_step4_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.backtest_pivot_pattern_sequence_wavenet_range(
        Command(
            CommandKind.BACKTEST_PIVOT_PATTERN_SEQUENCE_WAVENET_RANGE,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "flat_path": "seq_flat.parquet",
                "model_id": "option_b",
                "range_source": "flat",
                "range_bracket_mode": "range_capped",
                "max_samples": "0",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_pivot_pattern_sequence_wavenet_range.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--flat-path") + 1] == "seq_flat.parquet"
    assert args[args.index("--model-id") + 1] == "option_b"
    assert args[args.index("--range-source") + 1] == "flat"
    assert args[args.index("--range-bracket-mode") + 1] == "range_capped"
    assert args[args.index("--max-samples") + 1] == "0"
