"""Phase147C Option B expanded input health helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "audit_pivot_pattern_sequence_option_b_inputs.py"


def load_script():
    spec = importlib.util.spec_from_file_location("audit_pivot_pattern_sequence_option_b_inputs", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_update_scan_counts_nonfinite_values():
    module = load_script()
    scan = module.update_scan(module.empty_scan(), np.asarray([[[1.0, np.nan, -2.0]]]))

    assert scan.scanned_cells == 3
    assert scan.nonfinite_cells == 1
    assert scan.min_value == -2.0
    assert scan.max_value == 1.0
    assert scan.max_abs == 2.0


def test_validate_report_fails_when_branch_exceeds_clip():
    module = load_script()
    report = module.OptionBInputHealthReport(
        status="PENDING",
        symbol="XAUUSD",
        timeframe="5M",
        tensor_path="x.npy",
        meta_path="m.npz",
        stored_x_shape=[10, 100, 140],
        selected_x_shape=[10, 100, 140],
        train_rows=6,
        validation_rows=2,
        test_rows=2,
        raw_m5_context_features=35,
        raw_source_5m_features=83,
        raw_htf_context_features=22,
        branch_target_features=180,
        feature_augmentation_mode="causal",
        feature_augmentation_clip=8.0,
        keras_input_shapes={
            "m5_context_input": "[batch, 100, 180]",
            "source_5m_input": "[batch, 100, 180]",
            "htf_context_input": "[batch, 100, 180]",
        },
        target_action_counts={"SELL": 1, "HOLD": 8, "BUY": 1},
        scaler_nonfinite_input_values=0,
        scaler_mean_finite=True,
        scaler_std_finite=True,
        scanned_samples=10,
        scan={
            "m5_context_input": module.BranchScan(1, 0, -9.0, 9.0, 9.0, 1),
            "source_5m_input": module.BranchScan(1, 0, -1.0, 1.0, 1.0, 1),
            "htf_context_input": module.BranchScan(1, 0, -1.0, 1.0, 1.0, 1),
        },
        warnings=[],
        errors=[],
        output_json="latest.json",
        output_html="latest.html",
        production_status="BLOCKED",
    )

    errors, warnings = module.validate_report(report)

    assert any("max_abs" in error for error in errors)
    assert warnings == []
