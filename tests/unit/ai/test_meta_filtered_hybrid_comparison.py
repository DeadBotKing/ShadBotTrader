"""Phase132 meta-filtered hybrid comparison helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_meta_filtered_hybrid.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_meta_filtered_hybrid", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_candidates_reuses_last_version():
    module = load_script()

    specs = module.parse_candidates("base,a,b", "0,2")

    assert [(spec.model_id, spec.version) for spec in specs] == [("base", 0), ("a", 2), ("b", 2)]


def test_parse_threshold_options_support_record_token():
    module = load_script()

    values = module.parse_float_options("record,0.55,0.65", allow_record=True)

    assert values == [None, 0.55, 0.65]


def test_score_value_supports_drawdown_adjusted():
    module = load_script()
    summary = module.FixedBacktestSummary(
        samples=10,
        trades=2,
        buy_trades=1,
        sell_trades=1,
        wins=1,
        losses=1,
        timeouts=0,
        label_correct=1,
        false_positive=1,
        no_trade=8,
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
        win_rate=0.5,
        label_precision=0.5,
        total_pnl=25.0,
        avg_pnl=12.5,
        gross_profit=40.0,
        gross_loss=15.0,
        profit_factor=2.666,
        max_drawdown=10.0,
        coverage=0.2,
    )

    assert module.score_value(summary, {"final_balance": 125.0}, "total_pnl") == 25.0
    assert module.score_value(summary, {"final_balance": 125.0}, "final_balance") == 125.0
    assert module.score_value(summary, {"final_balance": 125.0}, "drawdown_adjusted") == 15.0


def test_best_replay_keeps_original_summary_for_html_rendering():
    module = load_script()
    row = module.skipped_row(module.CandidateSpec("base", 0), "")
    summary = module.FixedBacktestSummary(
        samples=1,
        trades=0,
        buy_trades=0,
        sell_trades=0,
        wins=0,
        losses=0,
        timeouts=0,
        label_correct=0,
        false_positive=0,
        no_trade=1,
        ambiguous=0,
        invalid_range=0,
        invalid_bracket=0,
        win_rate=0.0,
        label_precision=0.0,
        total_pnl=0.0,
        avg_pnl=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        profit_factor=0.0,
        max_drawdown=0.0,
        coverage=0.0,
    )

    replay = module.BestReplay(row, summary, [], [], object())

    assert replay.summary is summary


def test_select_best_ignores_skipped_and_low_trade_rows():
    module = load_script()
    base = dict(
        candidate="a",
        model_id="a",
        version=1,
        model_type="flat",
        decision_mode="meta",
        meta_threshold=0.55,
        score_threshold=0.0,
        status="ok",
        warning="",
        samples=100,
        trades=20,
        buy_trades=10,
        sell_trades=10,
        wins=12,
        losses=8,
        timeouts=0,
        skipped_by_filter=0,
        skipped_while_open=0,
        win_rate=0.6,
        label_precision=0.6,
        total_pnl=10.0,
        avg_pnl=0.5,
        profit_factor=1.2,
        max_drawdown=5.0,
        coverage=0.2,
        final_balance=101.0,
        net_profit=1.0,
        return_percent=0.01,
        would_breach_zero=False,
        score=10.0,
    )
    weak = module.ComparisonRow(**{**base, "candidate": "weak", "trades": 1, "score": 999.0})
    strong = module.ComparisonRow(**{**base, "candidate": "strong", "score": 20.0})
    skipped = module.skipped_row(module.CandidateSpec("missing", 0), "missing")

    best = module.select_best([weak, strong, skipped], min_trades=10)

    assert best is strong
