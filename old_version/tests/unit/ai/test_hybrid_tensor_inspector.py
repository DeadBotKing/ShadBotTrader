"""Phase127 tensor visual inspector helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "inspect_hybrid_telemetry_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("inspect_hybrid_telemetry_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_sample_indices_supports_aliases_and_dedupes():
    module = load_script()

    assert module.parse_sample_indices("first,middle,last,2,2", samples=9, max_samples=10) == [
        0,
        4,
        8,
        2,
    ]


def test_group_for_channel_maps_known_telemetry_prefixes():
    module = load_script()

    assert module.group_for_channel("5m_return_1") == "5M candle"
    assert module.group_for_channel("range_4h_up_room") == "4H range model"
    assert module.group_for_channel("candidate_reward_risk") == "Hybrid candidate / bracket"
    assert module.group_for_channel("rolling_48_trades_win_rate_lag") == "Lagged trade telemetry"


def test_inspector_writes_html_and_json(tmp_path):
    module = load_script()
    tensor_path = tmp_path / "tensor.npz"
    output_dir = tmp_path / "out"
    x_values = np.arange(3 * 4 * 2, dtype=np.float16).reshape(3, 4, 2)
    np.savez_compressed(
        tensor_path,
        X=x_values,
        channel_names=np.asarray(["5m_return_1", "candidate_side"], dtype=object),
        source_index=np.asarray([10, 20, 30], dtype=np.int64),
        timestamp=np.asarray(["t0", "t1", "t2"], dtype=object),
        target_trade_win=np.asarray([1, 0, 1], dtype=np.float32),
        target_trade_score_r=np.asarray([0.5, -1.0, 1.2], dtype=np.float32),
        target_trade_pnl=np.asarray([5.0, -3.0, 8.0], dtype=np.float32),
        candidate_mask=np.asarray([1, 1, 1], dtype=np.float32),
    )

    result = module.main(
        [
            "--tensor-path",
            str(tensor_path),
            "--sample-indices",
            "first,last",
            "--time-buckets",
            "4",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert result == 0
    assert (output_dir / "latest.html").exists()
    assert (output_dir / "latest.json").exists()
    assert "Hybrid Telemetry 3D Tensor Inspector" in (output_dir / "latest.html").read_text(
        encoding="utf-8"
    )
