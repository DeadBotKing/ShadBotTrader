"""Phase 124 — hybrid XGBoost head helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_hybrid_xgboost_head.py"


def load_script():
    spec = importlib.util.spec_from_file_location("train_hybrid_xgboost_head", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_feature_columns_drop_identity_and_price_levels():
    module = load_script()
    frame = pd.DataFrame(
        {
            "timestamp": ["t"],
            "label": [2],
            "close": [3500.0],
            "range_1d_high_price": [3510.0],
            "range_1d_up_room_pct": [0.01],
            "buy_specialist_prob": [0.7],
        }
    )

    columns = module.feature_columns(frame, drop_price_levels=True)

    assert "timestamp" not in columns
    assert "label" not in columns
    assert "close" not in columns
    assert "range_1d_high_price" not in columns
    assert columns == ["range_1d_up_room_pct", "buy_specialist_prob"]


def test_split_indices_keeps_chronological_order():
    module = load_script()

    train, val = module.split_indices(10, 0.6, min_samples=5)

    assert train.tolist() == [0, 1, 2, 3, 4, 5]
    assert val.tolist() == [6, 7, 8, 9]


def test_split_indices_rejects_tiny_matrix():
    module = load_script()

    with pytest.raises(RuntimeError):
        module.split_indices(4, 0.7, min_samples=5)
