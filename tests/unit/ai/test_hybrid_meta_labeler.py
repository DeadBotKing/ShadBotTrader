"""Phase128 hybrid meta-labeler helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TRAIN_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_hybrid_meta_labeler.py"
BACKTEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_meta_labeler.py"
)


def load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_average_precision_orders_scores_descending():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_meta_labeler")

    ap = module.average_precision(np.array([1, 0, 1]), np.array([0.9, 0.8, 0.7]))

    assert ap == pytest.approx((1.0 + 2.0 / 3.0) / 2.0)


def test_feature_columns_exclude_targets_and_identity():
    module = load_script(TRAIN_SCRIPT, "train_hybrid_meta_labeler")
    frame = pd.DataFrame(
        {
            "timestamp": ["t"],
            "source_index": [1],
            "target_trade_win": [1],
            "candidate_mask": [1],
            "feature_a": [0.1],
            "feature_b": [0.2],
        }
    )

    assert module.feature_columns(frame) == ["feature_a", "feature_b"]


def test_meta_backtest_skips_while_position_is_open():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_meta_labeler")
    frame = pd.DataFrame(
        {
            "timestamp": ["t0", "t1", "t4"],
            "source_index": [0, 1, 4],
            "candidate_mask": [1, 1, 1],
            "target_exit_index": [3, 3, 5],
            "target_side": [1, 1, -1],
            "target_trade_pnl": [10.0, 8.0, -2.0],
            "target_trade_win": [1, 1, 0],
            "target_outcome_code": [1, 1, -1],
            "candidate_entry_price": [2000.0, 2001.0, 2002.0],
            "candidate_take_profit": [2010.0, 2011.0, 1990.0],
            "candidate_stop_loss": [1990.0, 1991.0, 2010.0],
        }
    )

    summary, counters, trades = module.backtest(
        frame,
        np.array([0.9, 0.9, 0.9]),
        module.MetaThresholdSpec(0.55, 0.0, "test"),
    )

    assert summary.trades == 2
    assert counters.skipped_while_open == 1
    assert summary.total_pnl == pytest.approx(8.0)
    assert [trade.source_index for trade in trades] == [0, 4]


def test_meta_backtest_can_use_score_threshold_for_regressor():
    module = load_script(BACKTEST_SCRIPT, "backtest_hybrid_meta_labeler")
    frame = pd.DataFrame(
        {
            "timestamp": ["t0", "t1"],
            "source_index": [0, 4],
            "candidate_mask": [1, 1],
            "target_exit_index": [1, 5],
            "target_side": [1, 1],
            "target_trade_pnl": [5.0, 7.0],
            "target_trade_win": [1, 1],
            "target_outcome_code": [1, 1],
            "candidate_entry_price": [2000.0, 2001.0],
            "candidate_take_profit": [2010.0, 2011.0],
            "candidate_stop_loss": [1990.0, 1991.0],
        }
    )

    summary, counters, _ = module.backtest(
        frame,
        np.array([0.05, 0.30]),
        module.MetaThresholdSpec(0.90, 0.10, "test"),
        task="regressor",
    )

    assert summary.trades == 1
    assert counters.skipped_by_meta == 1
    assert summary.total_pnl == pytest.approx(7.0)
