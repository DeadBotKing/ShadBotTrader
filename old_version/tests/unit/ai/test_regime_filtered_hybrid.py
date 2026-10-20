"""Phase137A regime-filtered hybrid replay tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_regime_filtered_hybrid.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_regime_filtered_hybrid", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": ["2026-07-01T08:00:00Z", "2026-07-01T09:00:00Z"],
            "source_index": [1, 2],
            "label": [2, 0],
            "close": [2000.0, 2001.0],
            "candidate_mask": [1.0, 1.0],
            "target_side": [1.0, -1.0],
            "target_trade_win": [0.0, 1.0],
            "target_trade_score_r": [-1.0, 1.0],
            "target_trade_pnl": [-5.0, 7.0],
            "target_exit_index": [4, 5],
            "target_outcome_code": [-1.0, 1.0],
            "candidate_entry_price": [2000.0, 2001.0],
            "candidate_take_profit": [2005.0, 1995.0],
            "candidate_stop_loss": [1995.0, 2006.0],
            "candidate_confidence": [0.95, 0.75],
            "candidate_reward_risk": [1.0, 1.5],
            "candidate_sl_distance": [5.0, 5.0],
            "range_4h_up_room": [3.0, 1.0],
            "range_4h_down_room": [1.0, 6.0],
            "range_1d_up_room": [4.0, 2.0],
            "range_1d_down_room": [2.0, 8.0],
            "range_4h_width": [25.0, 25.0],
            "range_1d_width": [70.0, 70.0],
            "specialist_conflict": [0.0, 0.0],
            "booster_entropy": [0.2, 0.2],
            "booster_action_margin": [0.3, 0.3],
            "specialist_max_prob": [0.8, 0.8],
        }
    )


def test_default_filter_keeps_buy_and_sell_candidates():
    module = load_script()
    args = module.parse_args([])
    frame = module.prepare_frame(sample_frame())

    filtered, reasons = module.apply_regime_filter(frame, args)

    assert reasons["kept"] == 2
    assert filtered["candidate_mask"].tolist() == [1.0, 1.0]


def test_sell_only_filter_is_a_test_not_a_permanent_buy_removal():
    module = load_script()
    args = module.parse_args(["--allowed-sides", "SELL"])
    frame = module.prepare_frame(sample_frame())

    filtered, reasons = module.apply_regime_filter(frame, args)

    assert reasons["side_not_allowed"] == 1
    assert reasons["kept"] == 1
    assert filtered["candidate_mask"].tolist() == [0.0, 1.0]


def test_buy_strict_filter_can_block_only_weak_buy_without_blocking_sell():
    module = load_script()
    args = module.parse_args(["--buy-min-side-1d-room", "10"])
    frame = module.prepare_frame(sample_frame())

    filtered, reasons = module.apply_regime_filter(frame, args)

    assert reasons["side_1d_room_below_min"] == 1
    assert reasons["kept"] == 1
    assert filtered["candidate_mask"].tolist() == [0.0, 1.0]


def test_parse_hours_ignores_invalid_values():
    module = load_script()

    assert module.parse_hours("8,9,abc,25,-1") == {8, 9}
