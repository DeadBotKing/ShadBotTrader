"""Phase155A payoff sequence tensor builder helpers."""

from __future__ import annotations

from scripts import build_pivot_payoff_sequence_tensor as builder


def test_payoff_candidate_from_builder_args():
    args = builder.parse_args(
        [
            "--candidate-id",
            "B4",
            "--candidate-label",
            "asym",
            "--lookahead-bars",
            "24",
            "--pivot-zone-atr",
            "0.35",
            "--tp-atr",
            "1.0",
            "--sl-atr",
            "0.5",
            "--min-score-edge",
            "0.1",
        ]
    )

    candidate = builder.payoff_candidate_from_args(args)

    assert candidate.candidate_id == "B4"
    assert candidate.label == "asym"
    assert candidate.lookahead_bars == 24
    assert candidate.tp_atr == 1.0
    assert candidate.sl_atr == 0.5


def test_payoff_tensor_output_paths_use_output_name(tmp_path):
    args = builder.parse_args(
        [
            "--storage-root",
            str(tmp_path / "datasets"),
            "--output-name",
            "pivot_payoff_sequence_tensor_b4_latest",
        ]
    )

    tensor, meta, flat, json_path, html_path = builder.output_paths(args)

    assert tensor.name == "pivot_payoff_sequence_tensor_b4_latest.npy"
    assert meta.name == "pivot_payoff_sequence_tensor_b4_latest_meta.npz"
    assert flat.name == "pivot_payoff_sequence_flat_b4_latest.parquet"
    assert json_path.name == "latest.json"
    assert html_path.name == "latest.html"
