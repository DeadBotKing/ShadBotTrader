"""Phase 123 — hybrid matrix helper tests."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_hybrid_xgboost_matrix.py"


def load_script():
    spec = importlib.util.spec_from_file_location("build_hybrid_xgboost_matrix", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_latest_closed_index_uses_only_closed_range_candles():
    module = load_script()
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_times = [base + timedelta(hours=4), base + timedelta(hours=8)]

    assert module.latest_closed_index(end_times, base + timedelta(hours=3, minutes=59)) is None
    assert module.latest_closed_index(end_times, base + timedelta(hours=4)) == 0
    assert module.latest_closed_index(end_times, base + timedelta(hours=9)) == 1


def test_timeframe_delta_supports_5m_4h_1d():
    module = load_script()

    assert module.timeframe_delta("5M") == timedelta(minutes=5)
    assert module.timeframe_delta("4H") == timedelta(hours=4)
    assert module.timeframe_delta("1D") == timedelta(days=1)


def test_select_evenly_keeps_order_and_size():
    module = load_script()

    assert module.select_evenly(list(range(10)), 4) == [0, 2, 4, 6]
    assert module.select_evenly([1, 2], 4) == [1, 2]
