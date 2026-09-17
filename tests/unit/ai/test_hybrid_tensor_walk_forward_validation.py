"""Phase133B tensor walk-forward validation helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "run_hybrid_tensor_walk_forward_validation.py"
)


def load_script():
    spec = importlib.util.spec_from_file_location(
        "run_hybrid_tensor_walk_forward_validation", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_args_accepts_negative_score_threshold_grid():
    module = load_script()

    args = module.parse_args(["--score-thresholds", "-0.25,-0.10,0,0.05"])

    assert args.score_thresholds == "-0.25,-0.10,0,0.05"
    assert module.parse_float_options(args.score_thresholds, 0.0) == [
        -0.25,
        -0.10,
        0.0,
        0.05,
    ]
    assert args.meta_threshold == pytest.approx(args.default_meta_threshold)
    assert args.score_threshold == pytest.approx(args.default_score_threshold)


def test_threshold_grid_avoids_score_mode_meta_duplicates():
    module = load_script()

    grid = module.threshold_grid(
        ["score", "both"],
        [0.55, 0.60],
        [0.0, 0.05],
    )

    score_rows = [row for row in grid if row.decision_mode == "score"]
    both_rows = [row for row in grid if row.decision_mode == "both"]
    assert [(row.meta_threshold, row.score_threshold) for row in score_rows] == [
        (0.55, 0.0),
        (0.55, 0.05),
    ]
    assert len(both_rows) == 4


def test_tensor_index_frame_extracts_months_and_candidate_mask():
    module = load_script()
    data = {
        "source_index": np.asarray([10, 20], dtype=np.int64),
        "timestamp": np.asarray(["2026-07-01T00:00:00Z", "2026-08-01T00:00:00Z"]),
        "candidate_mask": np.asarray([1.0, 0.0], dtype=np.float32),
    }

    frame = module.tensor_index_frame(data)

    assert frame["tensor_index"].tolist() == [0, 1]
    assert frame["month"].tolist() == ["2026-07", "2026-08"]
    assert frame["candidate_mask"].tolist() == [1.0, 0.0]


def test_select_threshold_uses_only_thresholds_with_min_trades(monkeypatch):
    module = load_script()
    args = module.parse_args(["--min-trades", "2"])
    grid = [
        module.TelemetryWaveNetThresholds(0.55, 0.0, "score", "test"),
        module.TelemetryWaveNetThresholds(0.55, 0.05, "score", "test"),
        module.TelemetryWaveNetThresholds(0.55, 0.10, "score", "test"),
    ]

    def fake_evaluate(*call_args):
        thresholds = call_args[5]
        trades = 1 if thresholds.score_threshold == 0.10 else 3
        pnl = 10.0 if thresholds.score_threshold == 0.05 else 2.0
        summary = module.FixedBacktestSummary(
            samples=10,
            trades=trades,
            buy_trades=1,
            sell_trades=2,
            wins=2,
            losses=1,
            timeouts=0,
            label_correct=2,
            false_positive=1,
            no_trade=7,
            ambiguous=0,
            invalid_range=0,
            invalid_bracket=0,
            win_rate=2 / 3,
            label_precision=2 / 3,
            total_pnl=pnl,
            avg_pnl=pnl / max(trades, 1),
            gross_profit=12.0,
            gross_loss=2.0,
            profit_factor=6.0,
            max_drawdown=1.0,
            coverage=0.3,
        )
        return summary, object(), [], pnl

    monkeypatch.setattr(module, "evaluate_threshold", fake_evaluate)

    choice = module.select_threshold(
        np.asarray([1, 2, 3]),
        np.asarray([1, 1, 1], dtype=np.float32),
        np.asarray([0.5, 0.6, 0.7]),
        np.asarray([0.0, 0.1, 0.2]),
        {},
        grid,
        args,
    )

    assert choice.score_threshold == pytest.approx(0.05)
    assert choice.validation_score == pytest.approx(10.0)
    assert choice.validation_status == "ok"


def test_apply_purge_before_removes_rows_near_boundary():
    module = load_script()
    frame = pd.DataFrame({"source_index": [10, 20, 30, 40], "tensor_index": [0, 1, 2, 3]})

    purged = module.apply_purge_before(frame, boundary_source_index=40, purge_gap=15)

    assert purged["source_index"].tolist() == [10, 20]


def test_select_threshold_can_choose_no_trade_when_validation_score_is_negative(monkeypatch):
    module = load_script()
    args = module.parse_args(
        [
            "--min-trades",
            "2",
            "--allow-no-trade",
            "1",
            "--min-validation-score",
            "0",
        ]
    )
    grid = [module.TelemetryWaveNetThresholds(0.55, 0.0, "score", "test")]

    def fake_evaluate(*call_args):
        summary = module.FixedBacktestSummary(
            samples=10,
            trades=3,
            buy_trades=1,
            sell_trades=2,
            wins=1,
            losses=2,
            timeouts=0,
            label_correct=1,
            false_positive=2,
            no_trade=7,
            ambiguous=0,
            invalid_range=0,
            invalid_bracket=0,
            win_rate=1 / 3,
            label_precision=1 / 3,
            total_pnl=-5.0,
            avg_pnl=-5.0 / 3,
            gross_profit=2.0,
            gross_loss=7.0,
            profit_factor=2 / 7,
            max_drawdown=5.0,
            coverage=0.3,
        )
        return summary, object(), [], -5.0

    monkeypatch.setattr(module, "evaluate_threshold", fake_evaluate)

    choice = module.select_threshold(
        np.asarray([1, 2, 3]),
        np.asarray([1, 1, 1], dtype=np.float32),
        np.asarray([0.5, 0.6, 0.7]),
        np.asarray([0.0, 0.1, 0.2]),
        {},
        grid,
        args,
    )

    assert choice.decision_mode == "no_trade"
    assert choice.validation_status == "no_trade:validation_score_below_min"
    assert choice.validation_score == pytest.approx(-5.0)


def test_no_trade_summary_marks_all_samples_as_no_trade():
    module = load_script()

    summary = module.no_trade_summary(12)
    counters = module.no_trade_counters(12)

    assert summary.samples == 12
    assert summary.trades == 0
    assert summary.no_trade == 12
    assert counters.skipped_by_wavenet == 12
