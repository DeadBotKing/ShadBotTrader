"""Phase164A 1H spread/bracket sensitivity helpers."""

from __future__ import annotations

from scripts import audit_pivot_1h_spread_bracket_sensitivity as phase164


def test_parse_candidate_policies_and_brackets():
    policies = phase164.parse_candidate_policies("P:breakout:1:24:0.05:0.85:0.15:1:1.0:0")
    brackets = phase164.parse_brackets("B:2.0:1.0")

    assert policies[0].policy_key == "P"
    assert policies[0].side_mapping == "breakout"
    assert policies[0].entry_delay_bars == 1
    assert policies[0].recent_window_bars == 24
    assert brackets[0].bracket_id == "B"
    assert brackets[0].tp_atr == 2.0
    assert brackets[0].sl_atr == 1.0


def make_row(spread: float, val_pnl: float, test_pnl: float, transfer: int) -> phase164.SensitivityRow:
    return phase164.SensitivityRow(
        config_id=f"cfg-{spread}",
        policy_key="P",
        side_mapping="breakout",
        entry_delay_bars=1,
        recent_window_bars=24,
        pivot_zone_atr=0.05,
        top_position_threshold=0.85,
        bottom_position_threshold=0.15,
        exclude_both_zones=1,
        min_range_width_atr=1.0,
        max_range_width_atr=0.0,
        bracket_id="B",
        tp_atr=2.0,
        sl_atr=1.0,
        hold_bars=24,
        spread_mode="fixed",
        spread_value=spread,
        train_trades=10,
        train_profit_factor=1.0,
        train_total_cash_pnl=0.0,
        train_final_balance=100.0,
        validation_trades=10,
        validation_candidate_event_rate=0.1,
        validation_profit_factor=1.2 if val_pnl >= 0 else 0.8,
        validation_total_cash_pnl=val_pnl,
        validation_final_balance=100.0 + val_pnl,
        validation_independent_mean_atr=0.1,
        validation_skipped_winners=1,
        validation_skipped_losers=1,
        test_trades=10,
        test_candidate_event_rate=0.1,
        test_profit_factor=1.2 if test_pnl >= 0 else 0.8,
        test_total_cash_pnl=test_pnl,
        test_final_balance=100.0 + test_pnl,
        test_independent_mean_atr=0.1,
        test_skipped_winners=1,
        test_skipped_losers=1,
        validation_pass_gate=1 if val_pnl >= 0 else 0,
        test_pass_gate=1 if test_pnl >= 0 else 0,
        transfer_pass_gate=transfer,
        validation_score=val_pnl,
        warnings="[]",
    )


def test_break_even_rows_find_max_transfer_spread():
    rows = [
        make_row(0.0, 10.0, 5.0, 1),
        make_row(0.5, 4.0, 1.0, 1),
        make_row(1.0, -1.0, 2.0, 0),
        make_row(1.5, -2.0, -3.0, 0),
    ]

    result = phase164.build_break_even_rows(rows)[0]

    assert result.max_transfer_pass_spread == 0.5
    assert result.max_both_nonnegative_spread == 0.5
    assert result.first_validation_negative_spread == 1.0
    assert result.first_test_negative_spread == 1.5


def test_validation_score_modes():
    row = make_row(0.0, 3.0, 1.0, 1)

    assert phase164.validation_score(row, "cash_pnl") == 3.0
    assert phase164.validation_score(row, "profit_factor") == row.validation_profit_factor
    assert phase164.validation_score(row, "independent_mean_atr") == row.validation_independent_mean_atr
