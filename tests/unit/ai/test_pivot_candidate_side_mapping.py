"""Phase160A pivot candidate side-mapping helpers."""

from __future__ import annotations

from scripts import audit_pivot_candidate_side_mapping as phase160


def test_side_for_event_mapping_modes():
    assert phase160.side_for_event("reversal", "top") == "SELL"
    assert phase160.side_for_event("reversal", "bottom") == "BUY"
    assert phase160.side_for_event("breakout", "top") == "BUY"
    assert phase160.side_for_event("breakout", "bottom") == "SELL"
    assert phase160.side_for_event("top_sell", "bottom") is None
    assert phase160.side_for_event("all_buy", "top") == "BUY"


def test_policy_from_grid_row_parses_numeric_fields():
    row = {
        "policy_id": "p",
        "target_id": "B2",
        "lookahead_bars": "24",
        "tp_atr": "1.0",
        "sl_atr": "0.75",
        "recent_window_bars": "48",
        "pivot_zone_atr": "0.05",
        "top_position_threshold": "0.85",
        "bottom_position_threshold": "0.15",
        "exclude_both_zones": "1",
        "min_range_width_atr": "1.0",
        "max_range_width_atr": "0.0",
    }

    policy = phase160.policy_from_grid_row(row)

    assert policy.target_id == "B2"
    assert policy.lookahead_bars == 24
    assert policy.tp_atr == 1.0
    assert policy.exclude_both_zones == 1


def test_parse_int_grid_for_entry_delays():
    assert phase160.parse_int_grid("0,1,2,3", ()) == [0, 1, 2, 3]


def test_fallback_policies_use_target_specs():
    args = phase160.parse_args(["--fallback-targets", "B4:24:1.0:0.5"])

    policies = phase160.fallback_policies(args)

    assert len(policies) == 1
    assert policies[0].target_id == "B4"
    assert policies[0].tp_atr == 1.0
    assert policies[0].sl_atr == 0.5
