"""Phase152A pivot label/target stability helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_label_target_stability.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_label_target_stability", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_action_psi_is_zero_for_equal_distributions():
    module = load_script()
    dist = {"SELL": 0.2, "HOLD": 0.6, "BUY": 0.2}

    assert module.action_psi(dist, dist) == 0.0


def test_action_psi_detects_drift():
    module = load_script()

    value = module.action_psi(
        {"SELL": 0.6, "HOLD": 0.2, "BUY": 0.2},
        {"SELL": 0.2, "HOLD": 0.6, "BUY": 0.2},
    )

    assert value > 0.0


def test_split_summary_computes_class_rates():
    module = load_script()
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"], utc=True),
            "target_action": [0, 1, 2],
            "target_top_zone": [1.0, 0.0, 0.0],
            "target_bottom_zone": [0.0, 0.0, 1.0],
            "future_up_r": [0.1, 0.2, 0.3],
            "future_down_r": [0.3, 0.2, 0.1],
            "target_buy_r": [-0.2, 0.0, 0.2],
            "target_sell_r": [0.2, 0.0, -0.2],
        }
    )

    row = module.split_summary(
        "train", frame, {"SELL": 1 / 3, "HOLD": 1 / 3, "BUY": 1 / 3}, frame
    )

    assert row.rows == 3
    assert np.isclose(row.sell_rate, 1 / 3)
    assert np.isclose(row.buy_rate, 1 / 3)
    assert row.action_psi_vs_train == 0.0


def test_sensitivity_configs_respects_limit():
    module = load_script()
    args = module.parse_args(
        [
            "--sensitivity-lookahead-bars",
            "24,48",
            "--sensitivity-pivot-move-atrs",
            "0.5,0.75",
            "--sensitivity-pivot-zone-atrs",
            "0.25",
            "--sensitivity-min-direction-edges",
            "1.0,1.1",
            "--max-sensitivity-combinations",
            "3",
        ]
    )

    configs = module.sensitivity_configs(args)

    assert len(configs) == 3
