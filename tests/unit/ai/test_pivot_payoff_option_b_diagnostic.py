"""Phase155A payoff Option B diagnostic wrapper helpers."""

from __future__ import annotations

from pathlib import Path

from scripts import run_pivot_payoff_option_b_diagnostic as phase155


def test_phase155_default_candidates_are_b4_then_b2():
    candidates = phase155.parse_candidates(phase155.DEFAULT_CANDIDATES)

    assert [candidate.candidate_id for candidate in candidates] == ["B4", "B2"]
    assert phase155.output_name(candidates[0]) == "pivot_payoff_sequence_tensor_b4_latest"
    assert phase155.model_id(phase155.parse_args([]), candidates[0]) == "gold_pivot_payoff_option_b_b4_5m"


def test_phase155_build_and_backtest_commands_use_candidate_paths(tmp_path):
    args = phase155.parse_args(
        [
            "--storage-root",
            str(tmp_path / "datasets"),
            "--output-dir",
            str(tmp_path / "logs"),
            "--candidates",
            "B4:asym:24:0.35:1.0:0.5:0.1",
            "--train-max-samples",
            "500",
            "--epochs",
            "3",
        ]
    )
    candidate = phase155.parse_candidates(args.candidates)[0]
    root = Path(args.output_dir) / phase155.safe_slug(candidate.candidate_id)

    build = phase155.build_command(args, candidate, root / "build")
    train = phase155.train_command(args, candidate, root / "train")
    backtest = phase155.backtest_command(args, candidate, "validation", root / "validation")

    assert build[2] == "scripts/build_pivot_payoff_sequence_tensor.py"
    assert build[build.index("--output-name") + 1] == "pivot_payoff_sequence_tensor_b4_latest"
    assert build[build.index("--tp-atr") + 1] == "1.0"
    assert build[build.index("--sl-atr") + 1] == "0.5"
    assert train[2] == "scripts/train_pivot_pattern_sequence_wavenet_option_b.py"
    assert train[train.index("--model-id") + 1] == "gold_pivot_payoff_option_b_b4_5m"
    assert train[train.index("--max-samples") + 1] == "500"
    assert train[train.index("--epochs") + 1] == "3"
    assert train[train.index("--class-weight") + 1] == "off"
    assert backtest[2] == "scripts/backtest_pivot_pattern_sequence_wavenet.py"
    assert backtest[backtest.index("--eval-split") + 1] == "validation"
    assert backtest[backtest.index("--model-id") + 1] == "gold_pivot_payoff_option_b_b4_5m"
