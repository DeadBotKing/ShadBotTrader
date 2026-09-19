"""Phase148A range-aware sequence archive helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_pivot_pattern_sequence_wavenet_range.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_pivot_pattern_sequence_wavenet_range", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_flat_range_record_reads_src5m_prefixed_columns():
    module = load_script()
    row = pd.Series(
        {
            "src5m_range_4h_available": 1.0,
            "src5m_range_4h_high_price": 105.0,
            "src5m_range_4h_low_price": 95.0,
            "src5m_range_1d_available": 1.0,
            "src5m_range_1d_high_price": 110.0,
            "src5m_range_1d_low_price": 90.0,
        }
    )

    record = module.flat_range_record(row)

    assert record["range_4h_available"] == 1.0
    assert record["range_4h_high_price"] == 105.0
    assert record["range_1d_low_price"] == 90.0


def test_range_distances_buy_uses_high_and_low_with_caps():
    module = load_script()
    args = module.parse_args(
        [
            "--range-bracket-mode",
            "range_capped",
            "--max-tp-atr",
            "2",
            "--max-sl-atr",
            "1.25",
            "--use-1d-tp-cap",
            "1",
        ]
    )
    record = {
        "range_4h_high_price": 110.0,
        "range_4h_low_price": 94.0,
        "range_1d_high_price": 108.0,
    }

    distances = module.range_distances(record, module.ACTION_BUY, entry=100.0, atr_value=3.0, args=args)

    assert distances == (6.0, 3.75, "range")


def test_range_filter_uses_directional_room():
    module = load_script()
    args = module.parse_args(["--min-range-4h-room", "4", "--min-range-1d-room", "2"])
    record = {
        "range_4h_available": 1.0,
        "range_1d_available": 1.0,
        "range_4h_high_price": 106.0,
        "range_1d_high_price": 103.0,
    }

    assert module.range_filter_pass(record, 100.0, module.ACTION_BUY, args)
    assert not module.range_filter_pass(record, 100.0, module.ACTION_SELL, args)
