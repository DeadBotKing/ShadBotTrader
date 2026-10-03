"""Phase167A 1H locked candidate regime/failure attribution helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import audit_pivot_1h_locked_candidate_regime_failures as phase167
from scripts.audit_pivot_1h_entry_feasibility import build_zone_masks
from scripts.audit_pivot_payoff_target_redesign import resolve_atr
from scripts.replay_pivot_1h_locked_candidate_walk_forward import build_fold_specs, replay_fold


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


def test_regime_classifiers():
    assert phase167.classify_atr_regime(1.0, 2.0, 3.0, 4.0) == "atr_q1_low"
    assert phase167.classify_atr_regime(3.5, 2.0, 3.0, 4.0) == "atr_q3_mid_high"
    assert phase167.classify_atr_regime(5.0, 2.0, 3.0, 4.0) == "atr_q4_high"
    assert phase167.classify_spread_atr(0.01) == "spread_atr_le_0.02"
    assert phase167.classify_spread_atr(0.07) == "spread_atr_0.05_0.10"
    assert phase167.classify_spread_atr(0.30) == "spread_atr_gt_0.20"


def test_aggregate_trade_rows_by_side():
    rows = [
        {"fold": 1, "split": "test", "side": "BUY", "cash_pnl": 2.0, "atr_score": 1.0, "outcome": "take_profit"},
        {"fold": 1, "split": "test", "side": "BUY", "cash_pnl": -1.0, "atr_score": -1.0, "outcome": "stop_loss"},
        {"fold": 1, "split": "test", "side": "SELL", "cash_pnl": 3.0, "atr_score": 1.0, "outcome": "take_profit"},
    ]

    agg = phase167.aggregate_trade_rows(rows, "side", ("fold", "split", "side"))
    buy = next(row for row in agg if row.side == "BUY")

    assert buy.trades == 2
    assert buy.total_cash_pnl == 1.0
    assert buy.profit_factor == 2.0


def test_filter_indices_and_masks_min_atr_and_buy_leg():
    frame = make_frame(60)
    atr = np.arange(60, dtype=float) + 1.0
    top = np.ones(60, dtype=bool)
    bottom = np.ones(60, dtype=bool)
    args = phase167.parse_args(["--spread-value", "0.2"])

    idx, _top, _bottom = phase167.filter_indices_and_masks(
        "min_atr_q50",
        np.arange(10, 20),
        top,
        bottom,
        frame,
        atr,
        {"q25": 5, "q50": 15, "q75": 30},
        args,
    )
    assert idx.min() >= 14

    _idx, top2, bottom2 = phase167.filter_indices_and_masks(
        "buy_leg_only",
        np.arange(10, 20),
        top,
        bottom,
        frame,
        atr,
        {"q25": 5, "q50": 15, "q75": 30},
        args,
    )
    assert top2.any()
    assert not bottom2.any()


def test_phase167_small_fold_replay_produces_trade_rows():
    frame = make_frame(180)
    atr = resolve_atr(frame)
    args = phase167.parse_args(
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

    fold_row, _split_rows, trades, _months, _stress = replay_fold(spec, frame, top, bottom, atr, args)

    assert fold_row.fold == 1
    assert isinstance(trades, list)
