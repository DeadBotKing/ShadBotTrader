"""Phase 113 — random significance check helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_significance_check.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_significance_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_trade(module, side: str, row_index: int, pnl: float):
    return module.TradeResult(
        side=side,
        row_index=row_index,
        source_index=row_index,
        entry_index=row_index + 1,
        exit_index=row_index + 2,
        entry=2000.0,
        tp=2005.0 if side == "BUY" else 1995.0,
        sl=1995.0 if side == "BUY" else 2005.0,
        exit_price=2000.0 + pnl if side == "BUY" else 2000.0 - pnl,
        outcome="take_profit" if pnl > 0 else "stop_loss",
        pnl=pnl,
        label=module.CLASS_BUY if side == "BUY" else module.CLASS_SELL,
        label_correct=True,
    )


def test_distribution_stats_uses_plus_one_monte_carlo_p_value():
    module = load_script()

    stats = module.distribution_stats([1.0, 2.0, 5.0], observed=4.0)

    assert stats.trials == 3
    assert stats.better_or_equal_observed == 1
    assert stats.p_value == 0.5
    assert stats.p95 >= stats.p50


def test_sample_random_trades_matches_side_counts_without_duplicate_rows():
    module = load_script()
    rng = module.np.random.default_rng(7)
    pools = {
        module.CLASS_BUY: [make_trade(module, "BUY", index, 1.0) for index in range(10)],
        module.CLASS_SELL: [make_trade(module, "SELL", index + 20, -1.0) for index in range(10)],
    }

    sampled = module.sample_random_trades(rng, pools, buy_count=3, sell_count=4)

    assert sum(1 for trade in sampled if trade.side == "BUY") == 3
    assert sum(1 for trade in sampled if trade.side == "SELL") == 4
    assert len({trade.row_index for trade in sampled}) == 7


def test_load_candidate_profiles_keeps_only_valid_scored_rows(tmp_path):
    module = load_script()
    path = tmp_path / "phase125.json"
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "buy_threshold": 0.8,
                        "sell_threshold": 0.65,
                        "min_margin": 0.05,
                        "trades": 325,
                        "buy_trades": 160,
                        "sell_trades": 165,
                        "score": 291.15,
                        "total_pnl": 291.15,
                        "profit_factor": 1.247,
                    },
                    {
                        "buy_threshold": 0.95,
                        "sell_threshold": 0.80,
                        "min_margin": 0.05,
                        "trades": 40,
                        "buy_trades": 17,
                        "sell_trades": 23,
                        "score": -1.0,
                        "total_pnl": -71.47,
                        "profit_factor": 0.60,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    profiles = module.load_candidate_profiles(path, max_candidates=0)

    assert len(profiles) == 1
    assert profiles[0].buy_threshold == 0.8
    assert profiles[0].sell_trades == 165
