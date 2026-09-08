"""Phase 109 — trend_signal threshold calibration helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from ShadBotTrader.infrastructure.ai.model_catalogue import ModelRecord

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "calibrate_trend_signal_thresholds.py"


def load_script():
    spec = importlib.util.spec_from_file_location("calibrate_trend_signal_thresholds", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_decide_action_respects_threshold_and_margin():
    module = load_script()

    assert module.decide_action([0.1, 0.2, 0.7], 0.6, 0.6, 0.1) == module.CLASS_BUY
    assert module.decide_action([0.7, 0.2, 0.1], 0.6, 0.6, 0.1) == module.CLASS_SELL
    assert module.decide_action([0.1, 0.6, 0.7], 0.6, 0.6, 0.2) is None


def test_calibration_grid_selects_best_threshold_pair():
    module = load_script()
    y_true = [module.CLASS_BUY, module.CLASS_BUY, module.CLASS_SELL, module.CLASS_HOLD]
    probs = [
        [0.05, 0.10, 0.85],
        [0.10, 0.20, 0.70],
        [0.80, 0.10, 0.10],
        [0.20, 0.70, 0.10],
    ]

    rows = module.calibrate_grid(
        y_true,
        probs,
        threshold_values=[0.6, 0.8],
        min_margin=0.0,
        min_trades=1,
        precision_floor=0.0,
    )
    best = module.select_best(rows)

    assert best is not None
    assert best.action_precision == pytest.approx(1.0)
    assert best.action_f1 > 0


def test_model_record_roundtrip_keeps_decision_thresholds():
    record = ModelRecord(
        model_id="gold_trend_signal_5m",
        role="signal",
        symbol="XAUUSD",
        timeframe="5M",
        decision_thresholds={"buy_prob": 0.7, "sell_prob": 0.65},
    )

    restored = ModelRecord.from_dict(record.to_dict())

    assert restored.decision_thresholds == {"buy_prob": 0.7, "sell_prob": 0.65}
