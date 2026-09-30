"""Phase156A payoff prediction threshold calibration helpers."""

from __future__ import annotations

from scripts import audit_pivot_payoff_prediction_thresholds as phase156


def test_parse_phase156_default_candidate_specs():
    candidates = phase156.parse_candidate_specs("B4,B2")

    assert [candidate.candidate_id for candidate in candidates] == ["B4", "B2"]
    assert candidates[0].model_id == "gold_pivot_payoff_option_b_b4_5m"
    assert candidates[0].tensor_name == "pivot_payoff_sequence_tensor_b4_latest"


def test_parse_phase156_explicit_candidate_spec():
    candidates = phase156.parse_candidate_specs("X:model_x:tensor_x")

    assert candidates[0].candidate_id == "X"
    assert candidates[0].model_id == "model_x"
    assert candidates[0].tensor_name == "tensor_x"


def test_parse_r_grid_accepts_none_without_negative_argv():
    values = phase156.parse_r_grid("none,0,0.25", ())

    assert values == [-999.0, 0.0, 0.25]


def test_threshold_grid_cross_product_can_be_capped():
    args = phase156.parse_args(
        [
            "--buy-thresholds",
            "0.1,0.2",
            "--sell-thresholds",
            "0.1",
            "--margins",
            "0,0.05",
            "--min-buy-r-values",
            "none",
            "--min-sell-r-values",
            "none",
            "--max-policies",
            "3",
        ]
    )

    grid = phase156.threshold_grid(args)

    assert len(grid) == 3
    assert grid[0] == (0.1, 0.1, 0.0, -999.0, -999.0)
