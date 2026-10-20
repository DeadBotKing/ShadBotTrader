"""Phase143A pivot image tensor health audit tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_pattern_image_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_pattern_image_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_clean_dataset(tmp_path: Path) -> tuple[Path, Path, Path]:
    tensor_path = tmp_path / "tensor.npy"
    meta_path = tmp_path / "meta.npz"
    flat_path = tmp_path / "flat.parquet"
    tensor = np.zeros((4, 3, 2, 2), dtype=np.float16)
    tensor[:, :, :, :] = 0.5
    np.save(tensor_path, tensor)
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=6, freq="5min", tz="UTC"),
            "open": [100.0] * 6,
            "high": [101.0] * 6,
            "low": [99.0] * 6,
            "close": [100.5] * 6,
        }
    ).to_parquet(flat_path, index=False)
    np.savez(
        meta_path,
        sample_indices=np.array([2, 3, 4, 5], dtype=np.int64),
        timestamp=np.array(
            [
                "2026-01-01T00:10:00Z",
                "2026-01-01T00:15:00Z",
                "2026-01-01T00:20:00Z",
                "2026-01-01T00:25:00Z",
            ],
            dtype=object,
        ),
        target_action=np.array([0, 1, 2, 1], dtype=np.int64),
        target_top_zone=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        target_bottom_zone=np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32),
        target_buy_r=np.array([-1.0, 0.0, 1.0, 0.0], dtype=np.float32),
        target_sell_r=np.array([1.0, 0.0, -1.0, 0.0], dtype=np.float32),
        feature_5m_names=np.array(["__5m_bias__", "m5_a"], dtype=object),
        feature_htf_names=np.array(["__htf_bias__", "h4_a"], dtype=object),
        feature_5m_center=np.zeros((1, 1), dtype=np.float32),
        feature_5m_scale=np.ones((1, 1), dtype=np.float32),
        feature_htf_center=np.zeros((1, 1), dtype=np.float32),
        feature_htf_scale=np.ones((1, 1), dtype=np.float32),
        axis_normalization=np.array(["robust"], dtype=object),
        feature_clip=np.array([8.0], dtype=np.float32),
        interaction_clip=np.array([32.0], dtype=np.float32),
        nonfinite_feature_values=np.array([0], dtype=np.int64),
        nonfinite_interaction_values=np.array([0], dtype=np.int64),
        window_size=np.array([3], dtype=np.int32),
    )
    return tensor_path, meta_path, flat_path


def test_health_audit_passes_clean_tensor(tmp_path):
    module = load_script()
    tensor_path, meta_path, flat_path = write_clean_dataset(tmp_path)
    out_dir = tmp_path / "out"

    result = module.main(
        [
            "--tensor-path",
            str(tensor_path),
            "--meta-path",
            str(meta_path),
            "--flat-path",
            str(flat_path),
            "--builder-report",
            str(tmp_path / "missing.json"),
            "--output-dir",
            str(out_dir),
        ]
    )

    assert result == 0
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "latest.html").exists()


def test_health_audit_fails_nonfinite_tensor(tmp_path):
    module = load_script()
    tensor_path, meta_path, flat_path = write_clean_dataset(tmp_path)
    tensor = np.load(tensor_path)
    tensor[0, 0, 0, 0] = np.inf
    np.save(tensor_path, tensor)

    result = module.main(
        [
            "--tensor-path",
            str(tensor_path),
            "--meta-path",
            str(meta_path),
            "--flat-path",
            str(flat_path),
            "--builder-report",
            str(tmp_path / "missing.json"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert result == 1


def test_health_audit_fails_when_max_abs_exceeds_clip(tmp_path):
    module = load_script()
    tensor_path, meta_path, flat_path = write_clean_dataset(tmp_path)
    tensor = np.load(tensor_path)
    tensor[0, 0, 0, 0] = 40.0
    np.save(tensor_path, tensor)

    result = module.main(
        [
            "--tensor-path",
            str(tensor_path),
            "--meta-path",
            str(meta_path),
            "--flat-path",
            str(flat_path),
            "--builder-report",
            str(tmp_path / "missing.json"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert result == 1
