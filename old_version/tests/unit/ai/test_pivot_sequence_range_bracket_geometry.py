"""Phase150A range-bracket geometry audit helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_sequence_range_bracket_geometry.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_sequence_range_bracket_geometry", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_policies_includes_atr_control_and_range_policy():
    module = load_script()
    args = module.parse_args(
        [
            "--range-bracket-modes",
            "atr,range_capped",
            "--min-tp-distances",
            "0.5",
            "--min-sl-distances",
            "0.5",
            "--max-tp-atrs",
            "2",
            "--max-sl-atrs",
            "1.25",
        ]
    )

    policies = module.build_policies(args)

    assert any(policy.range_bracket_mode == "atr" for policy in policies)
    assert any(policy.range_bracket_mode == "range_capped" for policy in policies)


def test_replay_policy_runs_atr_control_without_range_values():
    module = load_script()
    args = module.parse_args(
        [
            "--range-bracket-modes",
            "atr",
            "--min-tp-distances",
            "0.5",
            "--min-sl-distances",
            "0.5",
            "--min-trades",
            "1",
            "--hold-bars",
            "2",
            "--spread-mode",
            "fixed",
            "--spread-value",
            "0",
        ]
    )
    policy = module.BracketPolicy(
        range_bracket_mode="atr",
        range_fallback="skip",
        use_1d_tp_cap="0",
        min_tp_distance=0.5,
        min_sl_distance=0.5,
        max_tp_atr=0.0,
        max_sl_atr=0.0,
        min_range_4h_room=0.0,
        min_range_1d_room=0.0,
        same_bar_policy="stop_first",
    )
    flat = pd.DataFrame(
        [
            {"timestamp": "t0", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "h4_atr_for_risk": 2.0},
            {"timestamp": "t1", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "h4_atr_for_risk": 2.0},
            {"timestamp": "t2", "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "h4_atr_for_risk": 2.0},
        ]
    )
    predictions = pd.DataFrame(
        [
            {
                "timestamp": "t0",
                "row_id": 0,
                "selected_action": "BUY",
                "close": 100.0,
                "range_4h_available": 0.0,
            }
        ]
    )

    summary, trades = module.replay_policy(predictions, flat, policy, args)

    assert summary.trades == 1
    assert summary.take_profits == 1
    assert trades[0]["bracket_source"] == "atr"


def test_range_policy_counts_invalid_brackets_when_range_is_wrong_side():
    module = load_script()
    args = module.parse_args(["--min-trades", "1"])
    policy = module.BracketPolicy(
        range_bracket_mode="range_capped",
        range_fallback="skip",
        use_1d_tp_cap="1",
        min_tp_distance=0.5,
        min_sl_distance=0.5,
        max_tp_atr=2.0,
        max_sl_atr=1.25,
        min_range_4h_room=0.0,
        min_range_1d_room=0.0,
        same_bar_policy="stop_first",
    )
    flat = pd.DataFrame(
        [
            {"timestamp": "t0", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "h4_atr_for_risk": 2.0},
            {"timestamp": "t1", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "h4_atr_for_risk": 2.0},
        ]
    )
    predictions = pd.DataFrame(
        [
            {
                "timestamp": "t0",
                "row_id": 0,
                "selected_action": "BUY",
                "close": 100.0,
                "range_4h_available": 1.0,
                "range_4h_high_price": 99.0,
                "range_4h_low_price": 95.0,
                "range_1d_high_price": 99.0,
                "range_1d_low_price": 90.0,
            }
        ]
    )

    summary, trades = module.replay_policy(predictions, flat, policy, args)

    assert summary.trades == 0
    assert summary.skipped_range_filter == 1
    assert trades == []
