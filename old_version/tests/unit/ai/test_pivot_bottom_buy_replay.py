"""Phase161A pivot bottom-buy replay helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import replay_pivot_bottom_buy_candidate as phase161


def test_bottom_buy_mask_requires_bottom_position_and_width():
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=4, freq="5min", tz="UTC"),
            "open": [100, 100, 100, 100],
            "high": [110, 110, 110, 110],
            "low": [90, 90, 90, 90],
            "close": [91, 100, 109, 92],
            "h4_atr_for_risk": [10, 10, 10, 10],
        }
    )
    args = phase161.parse_args(
        [
            "--recent-window-bars",
            "2",
            "--pivot-zone-atr",
            "0.2",
            "--bottom-position-threshold",
            "0.15",
            "--min-range-width-atr",
            "1.0",
        ]
    )

    mask = phase161.build_bottom_buy_mask(frame, np.asarray([0, 1, 2, 3]), args)

    assert mask.tolist() == [True, False, False, True]


def test_monthly_stats_sums_trade_pnl():
    trades = [
        phase161.PivotBottomBuyTrade(
            number=1,
            split="test",
            timestamp="2026-07-01 00:00:00+00:00",
            candidate_row_id=1,
            entry_row_id=2,
            exit_row_id=3,
            side="BUY",
            entry=100,
            tp=101,
            sl=99,
            exit_price=101,
            points_pnl=1,
            cash_pnl=2,
            balance=102,
            outcome="take_profit",
            tp_distance=1,
            sl_distance=1,
            risk_amount=1,
            atr_value=1,
            recent_window_bars=48,
            pivot_zone_atr=0.05,
            bottom_position=0.15,
            min_range_width_atr=1,
            entry_delay_bars=0,
        ),
        phase161.PivotBottomBuyTrade(
            number=2,
            split="test",
            timestamp="2026-07-02 00:00:00+00:00",
            candidate_row_id=4,
            entry_row_id=5,
            exit_row_id=6,
            side="BUY",
            entry=100,
            tp=101,
            sl=99,
            exit_price=99,
            points_pnl=-1,
            cash_pnl=-1,
            balance=101,
            outcome="stop_loss",
            tp_distance=1,
            sl_distance=1,
            risk_amount=1,
            atr_value=1,
            recent_window_bars=48,
            pivot_zone_atr=0.05,
            bottom_position=0.15,
            min_range_width_atr=1,
            entry_delay_bars=0,
        ),
    ]

    pnl, counts = phase161.monthly_stats(trades)

    assert pnl == {"2026-07": 1.0}
    assert counts == {"2026-07": 2}


def test_max_drawdown_from_balance_path():
    assert phase161.max_drawdown([100, 110, 105, 120, 90]) == 30
