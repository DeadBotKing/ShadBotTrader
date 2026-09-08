"""Phase 122 — booster specialist threshold calibration helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "calibrate_trend_signal_boosters.py"


def load_script():
    spec = importlib.util.spec_from_file_location("calibrate_trend_signal_boosters", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_decide_pair_respects_threshold_and_margin():
    module = load_script()

    assert module.decide_pair(0.7, 0.2, 0.6, 0.6, 0.1) == module.CLASS_BUY
    assert module.decide_pair(0.2, 0.7, 0.6, 0.6, 0.1) == module.CLASS_SELL
    assert module.decide_pair(0.65, 0.65, 0.6, 0.6, 0.0) == -1
    assert module.decide_pair(0.65, 0.64, 0.6, 0.6, 0.05) is None


def test_calibrate_grid_selects_threshold_pair_with_both_sides():
    module = load_script()
    y_true = [module.CLASS_BUY, module.CLASS_BUY, module.CLASS_SELL, module.CLASS_HOLD]
    buy_probs = [0.80, 0.70, 0.10, 0.30]
    sell_probs = [0.10, 0.20, 0.90, 0.30]

    rows = module.calibrate_grid(
        y_true,
        buy_probs,
        sell_probs,
        thresholds=[0.5, 0.75],
        min_margin=0.0,
        min_trades=1,
        min_side_trades=1,
        precision_floor=0.0,
    )
    best = module.select_best(rows)

    assert best is not None
    assert best.buy_trades > 0
    assert best.sell_trades > 0
    assert best.action_precision == 1.0
    assert best.action_f1 > 0
