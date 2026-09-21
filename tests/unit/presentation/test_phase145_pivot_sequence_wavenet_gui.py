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
        descriptor_for(CommandKind.AUDIT_PIVOT_PATTERN_SEQUENCE_OPTION_B_INPUTS).label
        == "Audit pivot sequence Option B input health"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_SEQUENCE_FEATURE_IMPACT).label
        == "Audit pivot sequence feature impact"
    )
    assert (
        descriptor_for(CommandKind.BACKTEST_PIVOT_PATTERN_SEQUENCE_WAVENET_RANGE).label
        == "Backtest sequence WaveNet range-aware archive"
    )
    assert (
        descriptor_for(CommandKind.RUN_PIVOT_TARGET_REDESIGN_CANDIDATE_AUDIT).label
        == "Build/audit pivot target redesign candidates"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_REDESIGN).label
        == "Audit pivot payoff target redesign"
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
                "random_seed": "123",
                "zero_feature_names": "m5_pos_in_range_48,h4_ret3",
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
    assert args[args.index("--random-seed") + 1] == "123"
    assert args[args.index("--zero-feature-names") + 1] == "m5_pos_in_range_48,h4_ret3"
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


def test_audit_option_b_expanded_inputs_passes_health_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_pattern_sequence_option_b_inputs(
        Command(
            CommandKind.AUDIT_PIVOT_PATTERN_SEQUENCE_OPTION_B_INPUTS,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "branch_target_features": "180",
                "feature_augmentation_mode": "causal",
                "full_scan": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_pattern_sequence_option_b_inputs.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--branch-target-features") + 1] == "180"
    assert args[args.index("--feature-augmentation-mode") + 1] == "causal"
    assert args[args.index("--full-scan") + 1] == "1"


def test_feature_impact_audit_passes_validation_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_sequence_feature_impact(
        Command(
            CommandKind.AUDIT_PIVOT_SEQUENCE_FEATURE_IMPACT,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "model_id": "option_b",
                "eval_split": "validation",
                "max_windows": "100",
                "feature_group_filter": "source_5m",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_sequence_feature_impact.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--model-id") + 1] == "option_b"
    assert args[args.index("--eval-split") + 1] == "validation"
    assert args[args.index("--max-windows") + 1] == "100"
    assert args[args.index("--feature-group-filter") + 1] == "source_5m"


def test_range_bracket_geometry_audit_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_sequence_range_bracket_geometry(
        Command(
            CommandKind.AUDIT_PIVOT_SEQUENCE_RANGE_BRACKET_GEOMETRY,
            {
                "predictions_path": "pred.parquet",
                "flat_path": "flat.parquet",
                "split_name": "validation",
                "range_bracket_modes": "atr,range_capped",
                "min_sl_distances": "0.5,5",
                "output_dir": "out_geom",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_sequence_range_bracket_geometry.py"
    assert args[args.index("--predictions-path") + 1] == "pred.parquet"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--split-name") + 1] == "validation"
    assert args[args.index("--range-bracket-modes") + 1] == "atr,range_capped"
    assert args[args.index("--min-sl-distances") + 1] == "0.5,5"
    assert args[args.index("--output-dir") + 1] == "out_geom"


def test_option_b_seed_transfer_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.run_pivot_sequence_option_b_seed_transfer(
        Command(
            CommandKind.RUN_PIVOT_SEQUENCE_OPTION_B_SEED_TRANSFER,
            {
                "tensor_path": "seq.npy",
                "meta_path": "seq_meta.npz",
                "flat_path": "flat.parquet",
                "model_id_prefix": "seed_audit",
                "seeds": "1,2",
                "epochs": "3",
                "skip_training": "1",
                "skip_existing_models": "0",
                "output_dir": "out_seed",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_pivot_sequence_option_b_seed_transfer_validation.py"
    assert args[args.index("--tensor-path") + 1] == "seq.npy"
    assert args[args.index("--meta-path") + 1] == "seq_meta.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--model-id-prefix") + 1] == "seed_audit"
    assert args[args.index("--seeds") + 1] == "1,2"
    assert args[args.index("--epochs") + 1] == "3"
    assert args[args.index("--skip-existing-models") + 1] == "0"
    assert args[args.index("--skip-training") + 1] == "1"
    assert args[args.index("--output-dir") + 1] == "out_seed"


def test_pivot_label_target_stability_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_label_target_stability(
        Command(
            CommandKind.AUDIT_PIVOT_LABEL_TARGET_STABILITY,
            {
                "flat_path": "flat.parquet",
                "meta_path": "meta.npz",
                "max_samples": "24000",
                "sensitivity_lookahead_bars": "24,48",
                "output_dir": "out_labels",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_label_target_stability.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--meta-path") + 1] == "meta.npz"
    assert args[args.index("--max-samples") + 1] == "24000"
    assert args[args.index("--sensitivity-lookahead-bars") + 1] == "24,48"
    assert args[args.index("--output-dir") + 1] == "out_labels"


def test_pivot_target_redesign_candidate_audit_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.run_pivot_target_redesign_candidate_audit(
        Command(
            CommandKind.RUN_PIVOT_TARGET_REDESIGN_CANDIDATE_AUDIT,
            {
                "candidates": "C1:stable:24:0.75:0.25:1.0",
                "build_max_samples": "1000",
                "audit_max_samples": "500",
                "health_full_scan": "0",
                "skip_existing_tensors": "1",
                "output_dir": "out_phase153",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_pivot_target_redesign_candidate_audit.py"
    assert args[args.index("--candidates") + 1] == "C1:stable:24:0.75:0.25:1.0"
    assert args[args.index("--build-max-samples") + 1] == "1000"
    assert args[args.index("--audit-max-samples") + 1] == "500"
    assert args[args.index("--health-full-scan") + 1] == "0"
    assert args[args.index("--skip-existing-tensors") + 1] == "1"
    assert args[args.index("--output-dir") + 1] == "out_phase153"


def test_pivot_payoff_target_redesign_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_payoff_target_redesign(
        Command(
            CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_REDESIGN,
            {
                "flat_path": "flat.parquet",
                "meta_path": "meta.npz",
                "candidates": "B1:test:24:0.35:0.75:0.75:0",
                "same_bar_policy": "target_first",
                "timeout_score_mode": "close_r",
                "output_dir": "out_phase154",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_payoff_target_redesign.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--meta-path") + 1] == "meta.npz"
    assert args[args.index("--candidates") + 1] == "B1:test:24:0.35:0.75:0.75:0"
    assert args[args.index("--same-bar-policy") + 1] == "target_first"
    assert args[args.index("--timeout-score-mode") + 1] == "close_r"
    assert args[args.index("--output-dir") + 1] == "out_phase154"
