"""Phase145A sequence tensor health audit tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_pattern_sequence_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_pattern_sequence_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sequence_health_scan_detects_finite_clip_bounds():
    module = load_script()
    tensor = np.asarray([[[0.0, 1.0], [-2.0, 8.0]]], dtype=np.float16)

    scan = module.scan_tensor(tensor, chunk_size=1, full_scan="1", max_scan_samples=0)

    assert scan.scanned_cells == 4
    assert scan.nonfinite_cells == 0
    assert scan.max_abs == 8.0
    assert scan.chunks == 1


def test_sequence_health_validation_passes_on_valid_3d_tensor():
    module = load_script()
    tensor = np.zeros((3, 2, 4), dtype=np.float16)
    meta = {
        "sample_indices": np.asarray([1, 2, 3], dtype=np.int64),
        "timestamp": np.asarray(
            ["2026-01-01T00:05:00Z", "2026-01-01T00:10:00Z", "2026-01-01T00:15:00Z"],
            dtype=object,
        ),
        "window_size": np.asarray([2], dtype=np.int32),
        "target_action": np.asarray([0, 1, 2], dtype=np.int64),
        "target_top_zone": np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
        "target_bottom_zone": np.asarray([0.0, 0.0, 1.0], dtype=np.float32),
        "target_buy_r": np.asarray([0.1, 0.0, 0.2], dtype=np.float32),
        "target_sell_r": np.asarray([0.2, 0.0, 0.1], dtype=np.float32),
        "feature_names": np.asarray(["m5_a", "src5m_b", "h4_c", "session_d"], dtype=object),
        "feature_groups": np.asarray(
            ["generated_5m", "source_5m", "closed_4h", "session"], dtype=object
        ),
        "feature_center": np.zeros(4, dtype=np.float32),
        "feature_scale": np.ones(4, dtype=np.float32),
        "feature_clip": np.asarray([8.0], dtype=np.float32),
        "nonfinite_feature_values": np.asarray([0], dtype=np.int64),
        "source_5m_feature_path": np.asarray(["source.parquet"], dtype=object),
        "source_5m_numeric_candidate_count": np.asarray([1], dtype=np.int64),
    }
    flat = pd.DataFrame(index=range(4))
    args = module.parse_args(["--full-scan", "1", "--chunk-size", "2"])
    builder_report = {"report": {"stored_x_shape": [3, 2, 4], "source_5m_feature_count": 1}}

    errors, warnings, scan = module.validate_tensor(tensor, meta, flat, builder_report, args)

    assert errors == []
    assert warnings == []
    assert scan.nonfinite_cells == 0


def test_sequence_health_validation_fails_on_4d_tensor():
    module = load_script()
    tensor = np.zeros((3, 2, 4, 1), dtype=np.float16)
    meta = {"sample_indices": np.asarray([1, 2, 3], dtype=np.int64), "timestamp": np.asarray([])}
    flat = pd.DataFrame(index=range(4))
    args = module.parse_args([])

    errors, _warnings, _scan = module.validate_tensor(tensor, meta, flat, {}, args)

    assert any("rank must be 3" in error for error in errors)

