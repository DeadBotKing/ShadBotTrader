"""Phase133 walk-forward validation helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run_hybrid_walk_forward_validation.py"


def load_script():
    spec = importlib.util.spec_from_file_location("run_hybrid_walk_forward_validation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fold_months_uses_past_train_and_validation_months():
    module = load_script()
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]

    folds = module.fold_months(months, train_months_min=2, validation_months=1)

    assert folds == [
        (["2026-01", "2026-02"], ["2026-03"], "2026-04"),
        (["2026-01", "2026-02", "2026-03"], ["2026-04"], "2026-05"),
    ]


def test_apply_purge_before_removes_rows_near_future_boundary():
    module = load_script()
    frame = pd.DataFrame({"source_index": [10, 20, 30, 40]})

    purged = module.apply_purge_before(frame, boundary_source_index=40, purge_gap=15)

    assert purged["source_index"].tolist() == [10, 20]


def test_parse_thresholds_ignores_empty_tokens():
    module = load_script()

    assert module.parse_thresholds("0.4, ,0.6") == [0.4, 0.6]


def test_select_threshold_picks_best_valid_score(monkeypatch):
    module = load_script()
    args = module.parse_args(["--min-trades", "2"])
    frame = pd.DataFrame({"x": [1, 2, 3]})
    scores = [0.1, 0.2, 0.3]

    def fake_evaluate(frame, scores, threshold, args):
        summary = module.FixedBacktestSummary(
            samples=3,
            trades=3 if threshold < 0.6 else 1,
            buy_trades=1,
            sell_trades=2,
            wins=2,
            losses=1,
            timeouts=0,
            label_correct=2,
            false_positive=1,
            no_trade=0,
            ambiguous=0,
            invalid_range=0,
            invalid_bracket=0,
            win_rate=2 / 3,
            label_precision=2 / 3,
            total_pnl=10.0 if threshold == 0.5 else 2.0,
            avg_pnl=1.0,
            gross_profit=10.0,
            gross_loss=1.0,
            profit_factor=10.0,
            max_drawdown=1.0,
            coverage=1.0,
        )
        return summary, object(), [], summary.total_pnl

    monkeypatch.setattr(module, "evaluate_threshold", fake_evaluate)

    threshold, score = module.select_threshold(frame, scores, [0.4, 0.5, 0.6], args)

    assert threshold == 0.5
    assert score == pytest.approx(10.0)
