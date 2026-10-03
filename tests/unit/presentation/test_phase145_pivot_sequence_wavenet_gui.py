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
    assert (
        descriptor_for(CommandKind.RUN_PIVOT_PAYOFF_OPTION_B_DIAGNOSTIC).label
        == "Run payoff-target Option B diagnostic"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_PAYOFF_PREDICTION_THRESHOLDS).label
        == "Audit payoff prediction thresholds"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_LEARNABILITY).label
        == "Audit payoff target learnability"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_ZONE_CANDIDATE_REFRAME).label
        == "Audit pivot-zone candidate reframe"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_CANDIDATE_GEOMETRY_TIGHTENING).label
        == "Audit pivot candidate geometry tightening"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_CANDIDATE_SIDE_MAPPING).label
        == "Audit pivot candidate side mapping"
    )
    assert (
        descriptor_for(CommandKind.REPLAY_PIVOT_BOTTOM_BUY_CANDIDATE).label
        == "Replay pivot bottom-buy candidate"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_BOTTOM_BUY_EXECUTION_GAP).label
        == "Audit pivot bottom-buy execution gap"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_1H_ENTRY_FEASIBILITY).label
        == "Audit 1H pivot entry feasibility"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_1H_SPREAD_BRACKET_SENSITIVITY).label
        == "Audit 1H spread/bracket sensitivity"
    )
    assert (
        descriptor_for(CommandKind.REPLAY_PIVOT_1H_FIXED_SPREAD_CANDIDATE_LOCKDOWN).label
        == "Replay 1H fixed-spread candidate lockdown"
    )
    assert (
        descriptor_for(CommandKind.REPLAY_PIVOT_1H_LOCKED_CANDIDATE_WALK_FORWARD).label
        == "Replay 1H locked candidate walk-forward"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_PIVOT_1H_LOCKED_CANDIDATE_REGIME_FAILURES).label
        == "Audit 1H locked candidate regime failures"
    )
    assert (
        descriptor_for(CommandKind.REPLAY_PIVOT_1H_PREDECLARED_FILTER_CONFIRMATION).label
        == "Replay 1H predeclared filter confirmation"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_BROKER_COST_REALITY_RESEARCH_RESET).label
        == "Audit broker cost reality / research reset"
    )
    assert (
        descriptor_for(CommandKind.CAPTURE_BROKER_SPREAD_COST_PIPELINE).label
        == "Capture broker spread / cost pipeline"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_RESEARCH_ROUTE_REDESIGN_DECISION_MATRIX).label
        == "Audit research route redesign matrix"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_FAMILY).label
        == "Audit broker-cost-aware 1H target family"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_LEARNABILITY).label
        == "Audit broker-cost-aware 1H target learnability"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_HYBRID_REGIME_FIRST_TARGET_REDESIGN).label
        == "Audit hybrid/regime-first target redesign"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_HYBRID_REGIME_WALKFORWARD_FAILURES).label
        == "Audit hybrid/regime walk-forward failures"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE).label
        == "Audit target-definition walk-forward root cause"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_WALKFORWARD_TARGET_FAMILY_REDESIGN_CANDIDATES).label
        == "Audit walk-forward target-family redesign candidates"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_POST_FAILURE_RESEARCH_ROUTE_RESET).label
        == "Audit post-failure research route reset"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_HIGHER_TIMEFRAME_COST_FEASIBILITY).label
        == "Audit 4H/1D broker-cost feasibility"
    )
    assert (
        descriptor_for(CommandKind.AUDIT_HIGHER_TIMEFRAME_TARGET_FAILURES).label
        == "Audit higher-timeframe target failures"
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


def test_pivot_payoff_option_b_diagnostic_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.run_pivot_payoff_option_b_diagnostic(
        Command(
            CommandKind.RUN_PIVOT_PAYOFF_OPTION_B_DIAGNOSTIC,
            {
                "candidates": "B4:asym:24:0.35:1.0:0.5:0.1",
                "build_max_samples": "1000",
                "train_max_samples": "500",
                "epochs": "3",
                "skip_training": "1",
                "output_dir": "out_phase155",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_pivot_payoff_option_b_diagnostic.py"
    assert args[args.index("--candidates") + 1] == "B4:asym:24:0.35:1.0:0.5:0.1"
    assert args[args.index("--build-max-samples") + 1] == "1000"
    assert args[args.index("--train-max-samples") + 1] == "500"
    assert args[args.index("--epochs") + 1] == "3"
    assert args[args.index("--skip-training") + 1] == "1"
    assert args[args.index("--output-dir") + 1] == "out_phase155"


def test_pivot_payoff_prediction_threshold_audit_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_payoff_prediction_thresholds(
        Command(
            CommandKind.AUDIT_PIVOT_PAYOFF_PREDICTION_THRESHOLDS,
            {
                "candidates": "B4,B2",
                "buy_thresholds": "0.1,0.2",
                "sell_thresholds": "0.1,0.2",
                "margins": "0,0.05",
                "output_dir": "out_phase156",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_payoff_prediction_thresholds.py"
    assert args[args.index("--candidates") + 1] == "B4,B2"
    assert args[args.index("--buy-thresholds") + 1] == "0.1,0.2"
    assert args[args.index("--sell-thresholds") + 1] == "0.1,0.2"
    assert args[args.index("--margins") + 1] == "0,0.05"
    assert args[args.index("--output-dir") + 1] == "out_phase156"


def test_pivot_payoff_target_learnability_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_payoff_target_learnability(
        Command(
            CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_LEARNABILITY,
            {
                "candidates": "B4,B2",
                "max_samples": "1000",
                "summary_mode": "last",
                "output_dir": "out_phase157",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_payoff_target_learnability.py"
    assert args[args.index("--candidates") + 1] == "B4,B2"
    assert args[args.index("--max-samples") + 1] == "1000"
    assert args[args.index("--summary-mode") + 1] == "last"
    assert args[args.index("--output-dir") + 1] == "out_phase157"


def test_pivot_zone_candidate_reframe_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_zone_candidate_reframe(
        Command(
            CommandKind.AUDIT_PIVOT_ZONE_CANDIDATE_REFRAME,
            {
                "candidates": "B4,B2",
                "max_samples": "1000",
                "summary_mode": "last",
                "min_validation_events": "50",
                "output_dir": "out_phase158",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_zone_candidate_reframe.py"
    assert args[args.index("--candidates") + 1] == "B4,B2"
    assert args[args.index("--max-samples") + 1] == "1000"
    assert args[args.index("--summary-mode") + 1] == "last"
    assert args[args.index("--min-validation-events") + 1] == "50"
    assert args[args.index("--output-dir") + 1] == "out_phase158"


def test_pivot_candidate_geometry_tightening_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_candidate_geometry_tightening(
        Command(
            CommandKind.AUDIT_PIVOT_CANDIDATE_GEOMETRY_TIGHTENING,
            {
                "targets": "B4:24:1.0:0.5",
                "recent_window_bars": "24,48",
                "pivot_zone_atrs": "0.05,0.10",
                "top_position_thresholds": "0.90",
                "output_dir": "out_phase159",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_candidate_geometry_tightening.py"
    assert args[args.index("--targets") + 1] == "B4:24:1.0:0.5"
    assert args[args.index("--recent-window-bars") + 1] == "24,48"
    assert args[args.index("--pivot-zone-atrs") + 1] == "0.05,0.10"
    assert args[args.index("--top-position-thresholds") + 1] == "0.90"
    assert args[args.index("--output-dir") + 1] == "out_phase159"


def test_pivot_candidate_side_mapping_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_candidate_side_mapping(
        Command(
            CommandKind.AUDIT_PIVOT_CANDIDATE_SIDE_MAPPING,
            {
                "geometry_grid_path": "grid.csv",
                "side_mappings": "reversal,breakout",
                "entry_delays": "0,1",
                "output_dir": "out_phase160",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_candidate_side_mapping.py"
    assert args[args.index("--geometry-grid-path") + 1] == "grid.csv"
    assert args[args.index("--side-mappings") + 1] == "reversal,breakout"
    assert args[args.index("--entry-delays") + 1] == "0,1"
    assert args[args.index("--output-dir") + 1] == "out_phase160"


def test_pivot_bottom_buy_replay_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.replay_pivot_bottom_buy_candidate(
        Command(
            CommandKind.REPLAY_PIVOT_BOTTOM_BUY_CANDIDATE,
            {
                "flat_path": "flat.parquet",
                "target_id": "B2",
                "pivot_zone_atr": "0.05",
                "bottom_position_threshold": "0.15",
                "output_dir": "out_phase161",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/replay_pivot_bottom_buy_candidate.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--target-id") + 1] == "B2"
    assert args[args.index("--pivot-zone-atr") + 1] == "0.05"
    assert args[args.index("--bottom-position-threshold") + 1] == "0.15"
    assert args[args.index("--output-dir") + 1] == "out_phase161"


def test_pivot_bottom_buy_execution_gap_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_bottom_buy_execution_gap(
        Command(
            CommandKind.AUDIT_PIVOT_BOTTOM_BUY_EXECUTION_GAP,
            {
                "flat_path": "flat.parquet",
                "entry_delays": "0,2",
                "same_bar_policies": "stop_first,tp_first",
                "spread_values": "0,0.06",
                "output_dir": "out_phase162",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_bottom_buy_execution_gap.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--entry-delays") + 1] == "0,2"
    assert args[args.index("--same-bar-policies") + 1] == "stop_first,tp_first"
    assert args[args.index("--spread-values") + 1] == "0,0.06"
    assert args[args.index("--output-dir") + 1] == "out_phase162"


def test_pivot_1h_entry_feasibility_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_1h_entry_feasibility(
        Command(
            CommandKind.AUDIT_PIVOT_1H_ENTRY_FEASIBILITY,
            {
                "flat_path": "one_hour.parquet",
                "recent_window_bars": "24",
                "spread_values": "0,0.06",
                "selection_spread_value": "0.06",
                "output_dir": "out_phase163",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_1h_entry_feasibility.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--recent-window-bars") + 1] == "24"
    assert args[args.index("--spread-values") + 1] == "0,0.06"
    assert args[args.index("--selection-spread-value") + 1] == "0.06"
    assert args[args.index("--output-dir") + 1] == "out_phase163"


def test_pivot_1h_spread_bracket_sensitivity_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_1h_spread_bracket_sensitivity(
        Command(
            CommandKind.AUDIT_PIVOT_1H_SPREAD_BRACKET_SENSITIVITY,
            {
                "flat_path": "one_hour.parquet",
                "fixed_spreads": "0,0.5,1.0",
                "pct_spreads": "0,0.03,0.06",
                "brackets": "B:2.0:1.0",
                "output_dir": "out_phase164",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_1h_spread_bracket_sensitivity.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--fixed-spreads") + 1] == "0,0.5,1.0"
    assert args[args.index("--pct-spreads") + 1] == "0,0.03,0.06"
    assert args[args.index("--brackets") + 1] == "B:2.0:1.0"
    assert args[args.index("--output-dir") + 1] == "out_phase164"


def test_pivot_1h_candidate_lockdown_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.replay_pivot_1h_fixed_spread_candidate_lockdown(
        Command(
            CommandKind.REPLAY_PIVOT_1H_FIXED_SPREAD_CANDIDATE_LOCKDOWN,
            {
                "flat_path": "one_hour.parquet",
                "policy_key": "BRK_D1_FAST",
                "spread_value": "0.2",
                "stress_spreads": "0.2,0.5",
                "output_dir": "out_phase165",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/replay_pivot_1h_fixed_spread_candidate_lockdown.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--policy-key") + 1] == "BRK_D1_FAST"
    assert args[args.index("--spread-value") + 1] == "0.2"
    assert args[args.index("--stress-spreads") + 1] == "0.2,0.5"
    assert args[args.index("--output-dir") + 1] == "out_phase165"


def test_pivot_1h_locked_candidate_walk_forward_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.replay_pivot_1h_locked_candidate_walk_forward(
        Command(
            CommandKind.REPLAY_PIVOT_1H_LOCKED_CANDIDATE_WALK_FORWARD,
            {
                "flat_path": "one_hour.parquet",
                "fold_train_bars": "1000",
                "fold_validation_bars": "200",
                "fold_test_bars": "200",
                "fold_step_bars": "200",
                "output_dir": "out_phase166",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/replay_pivot_1h_locked_candidate_walk_forward.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--fold-train-bars") + 1] == "1000"
    assert args[args.index("--fold-validation-bars") + 1] == "200"
    assert args[args.index("--fold-test-bars") + 1] == "200"
    assert args[args.index("--fold-step-bars") + 1] == "200"
    assert args[args.index("--output-dir") + 1] == "out_phase166"


def test_pivot_1h_locked_candidate_regime_failures_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_pivot_1h_locked_candidate_regime_failures(
        Command(
            CommandKind.AUDIT_PIVOT_1H_LOCKED_CANDIDATE_REGIME_FAILURES,
            {
                "flat_path": "one_hour.parquet",
                "diagnostic_filters": "none,min_atr_q50",
                "fold_train_bars": "1000",
                "output_dir": "out_phase167",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_pivot_1h_locked_candidate_regime_failures.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--diagnostic-filters") + 1] == "none,min_atr_q50"
    assert args[args.index("--fold-train-bars") + 1] == "1000"
    assert args[args.index("--output-dir") + 1] == "out_phase167"


def test_pivot_1h_predeclared_filter_confirmation_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.replay_pivot_1h_predeclared_filter_confirmation(
        Command(
            CommandKind.REPLAY_PIVOT_1H_PREDECLARED_FILTER_CONFIRMATION,
            {
                "flat_path": "one_hour.parquet",
                "filters": "none,buy_leg_only",
                "fold_train_bars": "1000",
                "output_dir": "out_phase168",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/replay_pivot_1h_predeclared_filter_confirmation.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--filters") + 1] == "none,buy_leg_only"
    assert args[args.index("--fold-train-bars") + 1] == "1000"
    assert args[args.index("--output-dir") + 1] == "out_phase168"


def test_broker_cost_reality_research_reset_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_broker_cost_reality_research_reset(
        Command(
            CommandKind.AUDIT_BROKER_COST_REALITY_RESEARCH_RESET,
            {
                "timeframes": "5M,1H",
                "m5_flat_path": "m5.parquet",
                "h1_flat_path": "h1.parquet",
                "fixed_spreads": "0.2,0.5",
                "output_dir": "out_phase169",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_broker_cost_reality_research_reset.py"
    assert args[args.index("--timeframes") + 1] == "5M,1H"
    assert args[args.index("--m5-flat-path") + 1] == "m5.parquet"
    assert args[args.index("--h1-flat-path") + 1] == "h1.parquet"
    assert args[args.index("--fixed-spreads") + 1] == "0.2,0.5"
    assert args[args.index("--output-dir") + 1] == "out_phase169"


def test_broker_spread_capture_pipeline_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.capture_broker_spread_cost_pipeline(
        Command(
            CommandKind.CAPTURE_BROKER_SPREAD_COST_PIPELINE,
            {
                "source_mode": "csv",
                "sample_path": "spread.csv",
                "broker_symbol": "XAUUSD_i",
                "duration_seconds": "10",
                "output_dir": "out_phase170",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/capture_broker_spread_cost_pipeline.py"
    assert args[args.index("--source-mode") + 1] == "csv"
    assert args[args.index("--sample-path") + 1] == "spread.csv"
    assert args[args.index("--broker-symbol") + 1] == "XAUUSD_i"
    assert args[args.index("--duration-seconds") + 1] == "10.0"
    assert args[args.index("--output-dir") + 1] == "out_phase170"


def test_research_route_redesign_decision_matrix_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_research_route_redesign_decision_matrix(
        Command(
            CommandKind.AUDIT_RESEARCH_ROUTE_REDESIGN_DECISION_MATRIX,
            {
                "phase170_path": "p170.json",
                "phase168_path": "p168.json",
                "manual_broker_spread_median": "0.39",
                "output_dir": "out_phase171",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_research_route_redesign_decision_matrix.py"
    assert args[args.index("--phase170-path") + 1] == "p170.json"
    assert args[args.index("--phase168-path") + 1] == "p168.json"
    assert args[args.index("--manual-broker-spread-median") + 1] == "0.39"
    assert args[args.index("--output-dir") + 1] == "out_phase171"


def test_broker_cost_aware_1h_target_family_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_broker_cost_aware_1h_target_family(
        Command(
            CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_FAMILY,
            {
                "flat_path": "one_hour.parquet",
                "families": "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24",
                "spread_value": "0.4",
                "stress_spread_value": "0.5",
                "output_dir": "out_phase172",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_broker_cost_aware_1h_target_family.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--families") + 1] == "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24"
    assert args[args.index("--spread-value") + 1] == "0.4"
    assert args[args.index("--stress-spread-value") + 1] == "0.5"
    assert args[args.index("--output-dir") + 1] == "out_phase172"


def test_broker_cost_aware_1h_target_learnability_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_broker_cost_aware_1h_target_learnability(
        Command(
            CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_LEARNABILITY,
            {
                "flat_path": "one_hour.parquet",
                "families": "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24",
                "spread_value": "0.4",
                "min_ap_lift": "0.02",
                "output_dir": "out_phase173",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_broker_cost_aware_1h_target_learnability.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--families") + 1] == "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24"
    assert args[args.index("--spread-value") + 1] == "0.4"
    assert args[args.index("--min-ap-lift") + 1] == "0.02"
    assert args[args.index("--output-dir") + 1] == "out_phase173"


def test_hybrid_regime_first_target_redesign_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_hybrid_regime_first_target_redesign(
        Command(
            CommandKind.AUDIT_HYBRID_REGIME_FIRST_TARGET_REDESIGN,
            {
                "flat_path": "one_hour.parquet",
                "families": "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24",
                "regime_rules": "ALL;SELL_ONLY",
                "spread_value": "0.4",
                "min_train_independent_pf": "0.90",
                "output_dir": "out_phase174",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_hybrid_regime_first_target_redesign.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--families") + 1] == "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:2:1:24"
    assert args[args.index("--regime-rules") + 1] == "ALL;SELL_ONLY"
    assert args[args.index("--spread-value") + 1] == "0.4"
    assert args[args.index("--min-train-independent-pf") + 1] == "0.9"
    assert args[args.index("--output-dir") + 1] == "out_phase174"


def test_hybrid_regime_walkforward_failures_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_hybrid_regime_walkforward_failures(
        Command(
            CommandKind.AUDIT_HYBRID_REGIME_WALKFORWARD_FAILURES,
            {
                "phase174_path": "phase174.json",
                "min_ap_lift": "0.02",
                "min_train_independent_pf": "0.90",
                "output_dir": "out_phase175",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_hybrid_regime_walkforward_failure_attribution.py"
    assert args[args.index("--phase174-path") + 1] == "phase174.json"
    assert args[args.index("--min-ap-lift") + 1] == "0.02"
    assert args[args.index("--min-train-independent-pf") + 1] == "0.9"
    assert args[args.index("--output-dir") + 1] == "out_phase175"


def test_target_definition_walkforward_root_cause_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_target_definition_walkforward_root_cause(
        Command(
            CommandKind.AUDIT_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE,
            {
                "phase174_path": "phase174.json",
                "phase175_path": "phase175.json",
                "output_dir": "out_phase176",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_target_definition_walkforward_root_cause_redesign.py"
    assert args[args.index("--phase174-path") + 1] == "phase174.json"
    assert args[args.index("--phase175-path") + 1] == "phase175.json"
    assert args[args.index("--output-dir") + 1] == "out_phase176"


def test_walkforward_target_family_redesign_candidates_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_walkforward_target_family_redesign_candidates(
        Command(
            CommandKind.AUDIT_WALKFORWARD_TARGET_FAMILY_REDESIGN_CANDIDATES,
            {
                "flat_path": "one_hour.parquet",
                "families": "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:1.5:1:12",
                "spread_value": "0.4",
                "min_train_events": "20",
                "output_dir": "out_phase177",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_walkforward_target_family_redesign_candidates.py"
    assert args[args.index("--timeframe") + 1] == "1H"
    assert args[args.index("--flat-path") + 1] == "one_hour.parquet"
    assert args[args.index("--families") + 1] == "F:label:breakout:1:24:0.1:0.85:0.15:1:1:0:1.5:1:12"
    assert args[args.index("--spread-value") + 1] == "0.4"
    assert args[args.index("--min-train-events") + 1] == "20"
    assert args[args.index("--output-dir") + 1] == "out_phase177"


def test_post_failure_research_route_reset_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_post_failure_research_route_reset(
        Command(
            CommandKind.AUDIT_POST_FAILURE_RESEARCH_ROUTE_RESET,
            {
                "phase173_path": "p173.json",
                "phase177_path": "p177.json",
                "manual_broker_spread_median": "0.39",
                "output_dir": "out_phase178",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_post_failure_research_route_reset.py"
    assert args[args.index("--phase173-path") + 1] == "p173.json"
    assert args[args.index("--phase177-path") + 1] == "p177.json"
    assert args[args.index("--manual-broker-spread-median") + 1] == "0.39"
    assert args[args.index("--output-dir") + 1] == "out_phase178"


def test_higher_timeframe_cost_feasibility_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_higher_timeframe_cost_feasibility(
        Command(
            CommandKind.AUDIT_HIGHER_TIMEFRAME_COST_FEASIBILITY,
            {
                "timeframes": "4H,1D",
                "h4_flat_path": "h4.parquet",
                "d1_flat_path": "d1.parquet",
                "spread_value": "0.4",
                "max_median_spread_atr": "0.08",
                "output_dir": "out_phase179",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_higher_timeframe_cost_feasibility.py"
    assert args[args.index("--timeframes") + 1] == "4H,1D"
    assert args[args.index("--h4-flat-path") + 1] == "h4.parquet"
    assert args[args.index("--d1-flat-path") + 1] == "d1.parquet"
    assert args[args.index("--spread-value") + 1] == "0.4"
    assert args[args.index("--max-median-spread-atr") + 1] == "0.08"
    assert args[args.index("--output-dir") + 1] == "out_phase179"


def test_higher_timeframe_target_failures_passes_gui_args(gui, monkeypatch):
    captured = capture(monkeypatch, gui)

    gui.audit_higher_timeframe_target_failures(
        Command(
            CommandKind.AUDIT_HIGHER_TIMEFRAME_TARGET_FAILURES,
            {
                "phase179_path": "phase179.json",
                "output_dir": "out_phase180",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_higher_timeframe_target_failure_attribution.py"
    assert args[args.index("--phase179-path") + 1] == "phase179.json"
    assert args[args.index("--output-dir") + 1] == "out_phase180"
