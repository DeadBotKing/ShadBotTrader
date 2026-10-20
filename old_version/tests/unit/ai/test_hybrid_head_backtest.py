"""Phase 125 — hybrid head range backtest helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_hybrid_xgboost_head.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_hybrid_xgboost_head", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_decide_action_respects_probabilities_and_margin():
    module = load_script()

    assert module.decide_action([0.2, 0.1, 0.7], 0.6, 0.6, 0.1) == module.CLASS_BUY
    assert module.decide_action([0.7, 0.1, 0.2], 0.6, 0.6, 0.1) == module.CLASS_SELL
    assert module.decide_action([0.4, 0.3, 0.5], 0.6, 0.6, 0.0) is None


def test_eval_slice_indices_uses_last_rows():
    module = load_script()

    assert module.eval_slice_indices(10, 0.3, 0).tolist() == [7, 8, 9]
    assert module.eval_slice_indices(10, 1.0, 4).tolist() == [0, 2, 4, 6]


def test_spread_abs_supports_pct_and_fixed():
    module = load_script()

    assert module.spread_abs(2000.0, "pct", 0.06) == 1.2
    assert module.spread_abs(2000.0, "fixed", 1.5) == 1.5
