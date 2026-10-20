"""Phase149A sequence feature impact helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_sequence_feature_impact.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_sequence_feature_impact", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_recommendation_thresholds():
    module = load_script()

    assert module.recommendation(0.01, 0.005, 0.005) == "DROP_CANDIDATE"
    assert module.recommendation(-0.01, 0.005, 0.005) == "KEEP_IMPORTANT"
    assert module.recommendation(0.0, 0.005, 0.005) == "NEUTRAL"


def test_composite_score_rewards_accuracy_and_ap_penalizes_mae():
    module = load_script()
    metrics = {
        "validation_action_accuracy": 0.7,
        "validation_top_ap": 0.4,
        "validation_bottom_ap": 0.2,
        "validation_buy_r_mae": 0.6,
        "validation_sell_r_mae": 0.4,
    }

    value = module.composite_score(metrics, "validation")

    assert round(value, 6) == round(0.7 + 0.2 + 0.1 - 0.15 - 0.1, 6)


def test_matching_feature_indices_filters_groups():
    module = load_script()
    groups = ["generated_5m", "source_5m", "closed_4h", "source_5m"]

    assert module.matching_feature_indices(groups, "source_5m").tolist() == [1, 3]
    assert module.matching_feature_indices(groups, "all").tolist() == [0, 1, 2, 3]
