"""Phase168A 1H predeclared filter confirmation helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import replay_pivot_1h_predeclared_filter_confirmation as phase168
from scripts.audit_pivot_1h_entry_feasibility import build_zone_masks
from scripts.audit_pivot_payoff_target_redesign import resolve_atr
from scripts.replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs


def make_frame(rows: int = 180) -> pd.DataFrame:
    close = np.full(rows, 100.0)
    close[::12] = 91.0
    close[6::12] = 109.0
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=rows, freq="1h", tz="UTC"),
            "open": close,
            "high": np.full(rows, 110.0),
            "low": np.full(rows, 90.0),
            "close": close,
            "atr": np.full(rows, 10.0),
        }
    )


def test_parse_filter_list_accepts_predeclared_combo():
    filters = phase168.parse_filter_list("none,max_spread_atr_0.10,buy_leg_only+max_spread_atr_0.10")

    assert filters == ["none", "max_spread_atr_0.10", "buy_leg_only+max_spread_atr_0.10"]


def test_parse_filter_list_rejects_unknown():
    with pytest.raises(RuntimeError):
        phase168.parse_filter_list("made_up_filter")


def test_apply_predeclared_filter_combines_buy_and_spread():
    frame = make_frame(60)
    atr = np.full(60, 10.0)
    top = np.ones(60, dtype=bool)
    bottom = np.ones(60, dtype=bool)
    args = phase168.parse_args(["--spread-value", "0.2"])

    idx, top2, bottom2 = phase168.apply_predeclared_filter(
        "buy_leg_only+max_spread_atr_0.10",
        np.arange(10, 20),
        top,
        bottom,
        frame,
        atr,
        {"q50": 10.0, "q75": 10.0},
        args,
        0.2,
    )

    assert idx.tolist() == list(range(10, 20))
    assert top2.any()
    assert not bottom2.any()


def make_filter_fold(filter_name: str, fold: int, fold_pass: int, test_pass: int, pnl: float, pf: float) -> phase168.FilterFoldRow:
    return phase168.FilterFoldRow(
        filter_name=filter_name,
        fold=fold,
        train_trades=10,
        train_profit_factor=1.2,
        train_total_cash_pnl=1.0,
        train_final_balance=101.0,
        train_positive_month_ratio=0.5,
        train_worst_month_pnl=-1.0,
        train_pass_gate=1,
        validation_trades=10,
        validation_profit_factor=1.2,
        validation_total_cash_pnl=1.0,
        validation_final_balance=101.0,
        validation_positive_month_ratio=0.5,
        validation_worst_month_pnl=-1.0,
        validation_pass_gate=1,
        test_trades=10,
        test_profit_factor=pf,
        test_total_cash_pnl=pnl,
        test_final_balance=100.0 + pnl,
        test_positive_month_ratio=0.5,
        test_worst_month_pnl=-1.0,
        test_max_drawdown_cash=2.0,
        test_pass_gate=test_pass,
        monthly_stability_gate=1,
        fold_transfer_pass_gate=fold_pass,
        stress_transfer_pass_gate=0,
        fold_pass_gate=fold_pass,
        failure_reasons="[]",
    )


def test_summarize_filter_compares_against_baseline():
    args = phase168.parse_args(["--min-folds", "2", "--min-fold-pass-ratio", "0.5", "--min-test-pass-ratio", "0.5"])
    baseline_rows = [make_filter_fold("none", 1, 0, 1, 1.0, 1.2), make_filter_fold("none", 2, 0, 0, -1.0, 0.8)]
    baseline = phase168.summarize_filter("none", baseline_rows, None, args)
    rows = [make_filter_fold("buy_leg_only", 1, 1, 1, 2.0, 1.4), make_filter_fold("buy_leg_only", 2, 0, 1, 1.0, 1.1)]

    summary = phase168.summarize_filter("buy_leg_only", rows, baseline, args)

    assert summary.fold_pass_ratio == 0.5
    assert summary.test_pass_ratio == 1.0
    assert summary.delta_fold_pass_ratio_vs_baseline == 0.5
    assert summary.pass_gate == 1


def test_replay_filter_fold_runs_on_small_fixture():
    frame = make_frame(180)
    atr = resolve_atr(frame)
    args = phase168.parse_args(
        [
            "--recent-window-bars",
            "12",
            "--pivot-zone-atr",
            "0.2",
            "--tp-atr",
            "0.5",
            "--sl-atr",
            "0.5",
            "--hold-bars",
            "6",
            "--spread-value",
            "0",
            "--fold-train-bars",
            "60",
            "--fold-validation-bars",
            "30",
            "--fold-test-bars",
            "30",
            "--purge-gap",
            "0",
            "--train-min-trades",
            "1",
            "--validation-min-trades",
            "1",
            "--test-min-trades",
            "1",
            "--min-positive-month-ratio",
            "0",
        ]
    )
    top, bottom, _ = build_zone_masks(frame, atr, 12, 0.2, 0.85, 0.15, 1, 1.0, 0.0)
    spec = build_fold_specs(180, 60, 30, 30, 30, 0, 1)[0]

    fold_row, split_rows, trade_rows, monthly_rows, stress_rows = phase168.replay_filter_fold(
        "none", spec, frame, top, bottom, atr, {"q50": 10.0, "q75": 10.0}, args
    )

    assert fold_row.filter_name == "none"
    assert len(split_rows) == 3
    assert isinstance(trade_rows, list)
    assert isinstance(monthly_rows, list)
    assert stress_rows
