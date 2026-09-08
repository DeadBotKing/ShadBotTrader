"""Phase 120 — trend_signal booster script helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_trend_signal_boosters.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_trend_signal_boosters", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_labels_for_buy_and_sell_specialists():
    module = load_script()

    labels = [module.CLASS_SELL, module.CLASS_HOLD, module.CLASS_BUY]

    assert module.labels_for_mode(labels, "buy").tolist() == [0, 0, 1]
    assert module.labels_for_mode(labels, "sell").tolist() == [1, 0, 0]
    assert module.labels_for_mode(labels, "multiclass").tolist() == labels


def test_aligned_predict_proba_restores_missing_class_columns():
    module = load_script()

    class Model:
        classes_ = np.asarray([0, 2])

        def predict_proba(self, _x):
            return np.asarray([[0.7, 0.3], [0.2, 0.8]])

    aligned = module.aligned_predict_proba(Model(), np.zeros((2, 1)), output_units=3)

    assert aligned.shape == (2, 3)
    assert aligned[:, 1].tolist() == [0.0, 0.0]
    assert aligned[0, 0] == 0.7
    assert aligned[1, 2] == 0.8
