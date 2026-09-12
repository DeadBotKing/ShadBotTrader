"""Phase127 telemetry tensor helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_hybrid_telemetry_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("build_hybrid_telemetry_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_lagged_telemetry_respects_fixed_safe_lag():
    module = load_script()
    events = [
        module.TargetEvent(10, 12, module.CLASS_BUY, 5.0, 0.5, 1, "take_profit"),
        module.TargetEvent(20, 22, module.CLASS_SELL, -3.0, -1.0, 0, "stop_loss"),
    ]

    telemetry = module.build_lagged_telemetry([30, 68], events, safe_lag_bars=48, mode="fixed")

    assert telemetry.loc[0, "lagged_trade_count"] == 0
    assert telemetry.loc[1, "lagged_trade_count"] == 2
    assert telemetry.loc[1, "rolling_12_trades_win_rate_lag"] == pytest.approx(0.5)


def test_lagged_telemetry_exit_closed_mode_uses_exit_index():
    module = load_script()
    events = [
        module.TargetEvent(10, 100, module.CLASS_BUY, 7.0, 1.0, 1, "take_profit"),
        module.TargetEvent(20, 40, module.CLASS_SELL, -2.0, -1.0, 0, "stop_loss"),
    ]

    telemetry = module.build_lagged_telemetry(
        [39, 41, 101], events, safe_lag_bars=48, mode="exit_closed"
    )

    assert telemetry.loc[0, "lagged_trade_count"] == 0
    assert telemetry.loc[1, "lagged_trade_count"] == 1
    assert telemetry.loc[2, "lagged_trade_count"] == 2


def test_tensor_windows_use_only_past_rows_and_requested_stride():
    module = load_script()
    frame = pd.DataFrame(
        {
            "timestamp": [f"t{i}" for i in range(6)],
            "source_index": list(range(6)),
            "label": [0, 1, 2, 0, 1, 2],
            "close": [2000.0] * 6,
            "feature_a": np.arange(6, dtype=np.float32),
            "feature_b": np.arange(10, 16, dtype=np.float32),
            "target_trade_win": [0, 1, 0, 1, 0, 1],
            "target_trade_score_r": [0.0] * 6,
            "target_trade_pnl": [0.0] * 6,
            "target_side": [0.0] * 6,
            "target_exit_index": [-1, 2, -1, 4, -1, 5],
            "target_outcome_code": [0.0] * 6,
            "candidate_mask": [0, 1, 0, 1, 0, 1],
        }
    )
    args = module.parse_args(["--tensor-window", "3", "--sample-stride", "2"])

    tensor, targets, indices = module.build_tensor(frame, ["feature_a", "feature_b"], args)

    assert indices.tolist() == [2, 4]
    assert tensor.shape == (2, 3, 2)
    assert tensor[0, :, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert targets["source_index"].tolist() == [2, 4]


def test_latest_closed_accepts_iso_timestamp_strings():
    module = load_script()
    end_times = [
        pd.Timestamp("2026-01-01T04:00:00Z"),
        pd.Timestamp("2026-01-01T08:00:00Z"),
    ]

    assert module.latest_closed(end_times, "2026-01-01T03:59:00+00:00") is None
    assert module.latest_closed(end_times, "2026-01-01T04:00:00+00:00") == 0
    assert module.latest_closed(end_times, "2026-01-01T09:00:00+00:00") == 1


def test_phase127_parse_args_has_same_bar_policy_default():
    module = load_script()

    args = module.parse_args([])
    custom = module.parse_args(["--same-bar-policy", "tp_first"])

    assert args.same_bar_policy == "stop_first"
    assert custom.same_bar_policy == "tp_first"


def test_stream_lagged_telemetry_can_be_recomputed_globally_across_chunks():
    module = load_script()
    frame = pd.DataFrame(
        {
            "source_index": [10, 68],
            "candidate_mask": [1.0, 0.0],
            "target_side": [1.0, 0.0],
            "target_exit_index": [12.0, -1.0],
            "target_trade_pnl": [5.0, 0.0],
            "target_trade_score_r": [1.0, 0.0],
            "target_trade_win": [1.0, 0.0],
            "target_outcome_code": [1.0, 0.0],
            "lagged_trade_count": [0.0, 0.0],
        }
    )
    args = module.parse_args(["--safe-lag-bars", "48", "--telemetry-lag-mode", "fixed"])

    recomputed = module.recompute_lagged_telemetry(frame, args)

    assert recomputed.loc[0, "lagged_trade_count"] == 0.0
    assert recomputed.loc[1, "lagged_trade_count"] == 1.0
    assert recomputed.loc[1, "last_closed_trade_pnl_lag"] == pytest.approx(5.0)
    assert recomputed.loc[1, "rolling_12_trades_win_rate_lag"] == pytest.approx(1.0)
