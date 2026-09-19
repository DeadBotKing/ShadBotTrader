"""Phase145A sequence tensor builder tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_pivot_pattern_sequence_tensor.py"


def load_script():
    spec = importlib.util.spec_from_file_location("build_pivot_pattern_sequence_tensor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sequence_sample_indices_stride_one():
    module = load_script()

    indices = module.sample_indices(rows=7, window_size=3, sample_stride=1, max_samples=0)

    assert indices.tolist() == [2, 3, 4, 5, 6]


def test_build_sequence_tensor_memmap_uses_past_window(tmp_path):
    module = load_script()
    values = np.arange(6 * 2, dtype=np.float32).reshape(6, 2)
    out = tmp_path / "x.npy"

    tensor = module.build_sequence_tensor_memmap(values, np.array([2, 4]), out, 3, "float32", 4)

    assert tensor.shape == (2, 3, 2)
    np.testing.assert_allclose(tensor[0], values[0:3])
    np.testing.assert_allclose(tensor[1], values[2:5])


def test_merge_source_features_adds_numeric_src5m_columns():
    module = load_script()
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=2, freq="5min", tz="UTC"),
            "m5_ret1": [0.1, 0.2],
        }
    )
    source = pd.DataFrame(
        {
            "open_time": pd.date_range("2026-01-01", periods=2, freq="5min", tz="UTC"),
            "open": [1.0, 2.0],
            "custom_feature": [10.0, 11.0],
            "source_index": [100, 101],
            "symbol": ["XAUUSD", "XAUUSD"],
        }
    )

    merged, columns = module.merge_source_features(frame, module.normalize_timestamp_column(source))

    assert columns == ["src5m_custom_feature"]
    assert merged["src5m_custom_feature"].tolist() == [10.0, 11.0]


def test_source_feature_path_flag_allows_missing_empty_value():
    module = load_script()

    args = module.parse_args(["--source-5m-feature-path", "--max-features", "0"])

    assert args.source_5m_feature_path == ""
    assert args.max_features == 0


def test_read_source_features_auto_prefers_hybrid_telemetry_flat(tmp_path, monkeypatch):
    module = load_script()
    root = tmp_path / "datasets"
    five_dir = root / "processed" / "XAUUSD" / "5M"
    five_dir.mkdir(parents=True)
    timestamps = pd.date_range("2026-01-01", periods=2, freq="5min", tz="UTC")
    (five_dir / "v1.parquet").touch()
    (five_dir / "hybrid_telemetry_flat_latest.parquet").touch()

    def fake_read_table(path):
        if path.name == "hybrid_telemetry_flat_latest.parquet":
            return pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "source_index": [10, 11],
                    "feature_alpha": [0.1, 0.2],
                    "target_trade_win": [1.0, 0.0],
                }
            )
        return pd.DataFrame(
            {
                "open_time": timestamps,
                "open": [1.0, 2.0],
                "high": [2.0, 3.0],
                "low": [0.5, 1.5],
                "close": [1.5, 2.5],
            }
        )

    monkeypatch.setattr(module, "read_table", fake_read_table)
    args = module.parse_args(["--storage-root", str(root), "--symbol", "XAUUSD"])

    source = module.read_source_5m_frame(args)

    assert source.path.endswith("hybrid_telemetry_flat_latest.parquet")
    assert source.numeric_candidate_count == 1
    assert module.source_feature_columns(source.frame) == ["feature_alpha"]


def test_build_report_records_sequence_shape(tmp_path):
    module = load_script()
    args = module.parse_args(["--window-size", "4"])
    frame = pd.DataFrame({"target_action": [0, 1, 2]})

    report = module.build_report(
        args,
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(1)),
        pd.DataFrame(index=range(3)),
        frame,
        [5, 4, 7],
        tmp_path / "x.npy",
        tmp_path / "m.npz",
        tmp_path / "f.parquet",
        tmp_path / "r.json",
        tmp_path / "r.html",
        "note",
        ["a", "b", "c"],
        2,
        1,
        module.SourceFeatureRead(None, "", 0, 0),
        0,
    )

    assert report.stored_x_shape == [5, 4, 7]
    assert report.keras_batch_shape == "[batch, 4, 7]"
