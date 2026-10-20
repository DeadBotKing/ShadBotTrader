"""Phase139A TP/SL bracket recalibration tests."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_bracket_recalibration.py"


@dataclass(frozen=True)
class Amount:
    amount: float


@dataclass(frozen=True)
class Candle:
    open: Amount
    high: Amount
    low: Amount
    close: Amount


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_bracket_recalibration", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate_row(side: float = 1.0) -> pd.Series:
    return pd.Series(
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "source_index": 0,
            "target_side": side,
            "candidate_entry_price": 100.0,
            "candidate_tp_distance": 20.0,
            "candidate_sl_distance": 10.0,
        }
    )


def test_parse_cap_options_supports_original_and_numbers():
    module = load_script()

    assert module.parse_cap_options("original,12,-1,12") == [None, 12.0]


def test_recalibrated_distances_cap_tp_sl_and_reward_risk():
    module = load_script()
    args = module.parse_args(
        [
            "--max-tp-distances",
            "12",
            "--max-sl-distances",
            "8",
            "--max-reward-risks",
            "1.0",
        ]
    )
    policy = module.BracketPolicy("test", 12.0, 8.0, 1.0)

    assert module.recalibrated_distances(candidate_row(), policy, args) == pytest.approx((8.0, 8.0))


def test_side_specific_cap_overrides_global_cap():
    module = load_script()
    args = module.parse_args(["--buy-max-tp-distance", "6"])
    policy = module.BracketPolicy("test", 12.0, None, None)

    assert module.recalibrated_distances(candidate_row(1.0), policy, args) == pytest.approx(
        (6.0, 10.0)
    )
    assert module.recalibrated_distances(candidate_row(-1.0), policy, args) == pytest.approx(
        (12.0, 10.0)
    )


def test_simulate_recalibrated_trade_hits_capped_take_profit():
    module = load_script()
    args = module.parse_args(["--spread-mode", "fixed", "--spread-value", "0"])
    policy = module.BracketPolicy("tp-cap", 5.0, None, None)
    candles = [
        Candle(Amount(100.0), Amount(100.0), Amount(100.0), Amount(100.0)),
        Candle(Amount(100.0), Amount(106.0), Amount(99.0), Amount(105.0)),
    ]

    trade = module.simulate_recalibrated_trade(candidate_row(1.0), candles, policy, args, 1, 0.0)

    assert trade is not None
    assert trade.outcome == "take_profit"
    assert trade.pnl == pytest.approx(5.0)


def test_select_best_ignores_rows_below_min_trades():
    module = load_script()
    weak = module.PolicyRow(
        policy="weak",
        max_tp_distance="original",
        max_sl_distance="original",
        max_reward_risk="original",
        samples=10,
        trades=1,
        buy_trades=1,
        sell_trades=0,
        wins=1,
        losses=0,
        timeouts=0,
        skipped_side=0,
        skipped_while_open=0,
        invalid_bracket=0,
        win_rate=1.0,
        total_pnl=100.0,
        avg_pnl=100.0,
        gross_profit=100.0,
        gross_loss=0.0,
        profit_factor=999.0,
        max_drawdown=0.0,
        coverage=0.1,
        final_balance=110.0,
        net_profit=10.0,
        return_percent=0.1,
        would_breach_zero=False,
        score=-1e18,
    )
    strong = module.PolicyRow(**{**weak.__dict__, "policy": "strong", "trades": 10, "score": 5.0})

    assert module.select_best([weak, strong]).policy == "strong"
