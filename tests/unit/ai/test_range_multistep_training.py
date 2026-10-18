"""Phase187A protected multistep range training plan."""

from __future__ import annotations

import pytest

from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set
from scripts import train_range_multistep as phase187


def test_default_ids_do_not_touch_production_range_models():
    plan = phase187.training_plan(phase187.parse_args(["--dry-run"]))

    ids = [row["model_id"] for row in plan]
    assert ids == ["gold_range_multistep_4h", "gold_range_multistep_1d"]
    assert phase187.PROTECTED_RANGE_IDS.isdisjoint(ids)
    assert all(row["horizon"] == 5 for row in plan)
    assert all(row["output_width"] == 10 for row in plan)
    assert all(row["option_b_used"] == 0 for row in plan)
    assert all(row["architecture"] == "range_wavenet_seq2seq" for row in plan)
    assert all(row["seq2seq"] is True for row in plan)


def test_protected_and_ambiguous_ids_are_refused():
    with pytest.raises(RuntimeError, match="protected"):
        phase187.resolved_model_id("4H", "gold_range")
    with pytest.raises(RuntimeError, match="multistep"):
        phase187.resolved_model_id("4H", "gold_experiment")


def test_horizon_below_two_is_refused():
    with pytest.raises(RuntimeError, match="horizon"):
        phase187.run(["--timeframes", "4H", "--horizon", "1", "--dry-run"])


def test_dry_run_writes_nothing(tmp_path):
    plan = phase187.run(
        [
            "--timeframes",
            "4H",
            "--horizon",
            "5",
            "--storage-root",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert plan[0]["model_id"] == "gold_range_multistep_4h"
    assert not (tmp_path / "models").exists()


def test_causal_signal_features_are_the_only_causal_features_excluded_from_range():
    signal_only = []
    for definition in standard_feature_set().definitions:
        if definition.is_live_compatible and definition.model_scope.value == "signal":
            signal_only.append(definition.feature_id.value)

    assert signal_only == [
        "session_asian",
        "session_london",
        "session_ny",
        "session_overlap",
        "hour_sin",
        "hour_cos",
    ]
