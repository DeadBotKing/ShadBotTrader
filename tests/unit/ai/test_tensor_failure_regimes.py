"""Phase136A tensor failure/regime diagnostic tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "analyze_tensor_failure_regimes.py"


def load_script():
    spec = importlib.util.spec_from_file_location("analyze_tensor_failure_regimes", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-07-01T00:00:00Z",
                "2026-07-01T01:00:00Z",
                "2026-08-01T00:00:00Z",
                "2026-08-01T01:00:00Z",
            ],
            "candidate_mask": [1.0, 1.0, 1.0, 0.0],
            "target_side": [1.0, -1.0, -1.0, 1.0],
            "target_trade_win": [1.0, 0.0, 1.0, 0.0],
            "target_trade_pnl": [10.0, -4.0, 3.0, -2.0],
            "target_trade_score_r": [1.0, -1.0, 0.4, -0.5],
            "target_outcome_code": [1.0, -1.0, 1.0, -1.0],
            "range_4h_up_room": [5.0, 2.0, 1.0, 4.0],
            "range_4h_down_room": [1.0, 8.0, 6.0, 2.0],
            "range_1d_up_room": [10.0, 2.0, 1.0, 5.0],
            "range_1d_down_room": [2.0, 12.0, 7.0, 3.0],
            "candidate_confidence": [0.8, 0.7, 0.9, 0.6],
            "candidate_reward_risk": [1.5, 1.2, 2.0, 1.0],
            "candidate_tp_distance": [6.0, 5.0, 7.0, 4.0],
            "candidate_sl_distance": [3.0, 4.0, 3.5, 4.0],
            "booster_entropy": [0.1, 0.2, 0.3, 0.4],
            "booster_action_margin": [0.5, 0.2, 0.3, 0.1],
            "specialist_max_prob": [0.9, 0.8, 0.7, 0.6],
            "specialist_conflict": [0.0, 1.0, 0.0, 1.0],
            "candidate_valid_range": [1.0, 1.0, 1.0, 0.0],
            "candidate_valid_bracket": [1.0, 1.0, 1.0, 0.0],
        }
    )


def test_prepare_candidate_frame_adds_side_aware_context():
    module = load_script()

    frame = module.prepare_candidate_frame(sample_frame(), "1")

    assert frame["month"].tolist() == ["2026-07", "2026-07", "2026-08"]
    assert frame["side"].tolist() == ["BUY", "SELL", "SELL"]
    assert frame["side_4h_room"].tolist() == pytest.approx([5.0, 8.0, 6.0])
    assert frame["outcome"].tolist() == ["take_profit", "stop_loss", "take_profit"]


def test_summarize_subset_computes_profit_factor_and_drawdown():
    module = load_script()
    frame = module.prepare_candidate_frame(sample_frame(), "1")

    row = module.summarize_subset("all", "all", frame, len(frame))

    assert row.rows == 3
    assert row.wins == 2
    assert row.total_pnl == pytest.approx(9.0)
    assert row.profit_factor == pytest.approx(13.0 / 4.0)
    assert row.max_drawdown == pytest.approx(4.0)


def test_build_transfer_rows_marks_positive_validation_failure():
    module = load_script()
    payload = {
        "folds": [
            {
                "fold": 1,
                "test_month": "2026-08",
                "validation_months": "2026-07",
                "selected_decision_mode": "both",
                "selected_meta_threshold": 0.7,
                "selected_score_threshold": -0.1,
                "selected_validation_score": 60.0,
                "selected_validation_profit_factor": 1.4,
                "selected_validation_max_drawdown": 40.0,
                "selected_validation_trades": 20,
                "no_trade_selected": 0,
                "base_total_pnl": -200.0,
                "tensor_total_pnl": -32.0,
                "tensor_profit_factor": 0.76,
                "tensor_trades": 35,
                "tensor_max_drawdown": 86.0,
            }
        ]
    }

    rows = module.build_transfer_rows(payload)

    assert rows[0].transfer_status == "positive_validation_failed_test"
    assert rows[0].transfer_delta == pytest.approx(-92.0)


def test_main_writes_diagnostic_files(tmp_path):
    module = load_script()
    flat_path = tmp_path / "flat.parquet"
    wf_path = tmp_path / "wf.json"
    out_dir = tmp_path / "out"
    sample_frame().to_parquet(flat_path, index=False)
    wf_path.write_text(
        '{"folds":[{"fold":1,"test_month":"2026-08","validation_months":"2026-07",'
        '"selected_decision_mode":"no_trade","selected_validation_status":"no_trade:test",'
        '"no_trade_selected":1,"tensor_total_pnl":0,"tensor_trades":0}]}',
        encoding="utf-8",
    )

    result = module.main(
        [
            "--flat-path",
            str(flat_path),
            "--walk-forward-json",
            str(wf_path),
            "--output-dir",
            str(out_dir),
            "--min-group-rows",
            "1",
        ]
    )

    assert result == 0
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "latest.html").exists()
    assert (out_dir / "latest_regimes.csv").exists()
    assert (out_dir / "latest_transfer.csv").exists()
