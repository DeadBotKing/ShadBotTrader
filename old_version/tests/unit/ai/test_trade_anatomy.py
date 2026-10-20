"""Phase138A trade anatomy diagnostic tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "analyze_trade_anatomy.py"


def load_script():
    spec = importlib.util.spec_from_file_location("analyze_trade_anatomy", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-01-01T08:00:00Z",
                "2026-01-01T09:00:00Z",
                "2026-02-01T08:00:00Z",
            ],
            "source_index": [10, 20, 30],
            "candidate_mask": [1.0, 1.0, 1.0],
            "target_side": [1.0, -1.0, 1.0],
            "target_trade_win": [0.0, 1.0, 0.0],
            "target_trade_pnl": [-5.0, 7.0, -4.0],
            "target_trade_score_r": [-1.0, 1.0, -1.0],
            "target_exit_index": [14, 25, 35],
            "target_outcome_code": [-1.0, 1.0, 0.0],
            "candidate_entry_price": [100.0, 100.0, 100.0],
            "candidate_take_profit": [110.0, 90.0, 108.0],
            "candidate_stop_loss": [95.0, 105.0, 96.0],
            "candidate_tp_distance": [10.0, 10.0, 8.0],
            "candidate_sl_distance": [5.0, 5.0, 4.0],
            "candidate_reward_risk": [2.0, 2.0, 2.0],
            "range_4h_up_room": [3.0, 1.0, 2.0],
            "range_4h_down_room": [1.0, 6.0, 2.0],
            "range_1d_up_room": [4.0, 2.0, 5.0],
            "range_1d_down_room": [2.0, 8.0, 1.0],
            "range_4h_width": [25.0, 30.0, 35.0],
            "range_1d_width": [70.0, 80.0, 90.0],
            "candidate_confidence": [0.9, 0.8, 0.7],
        }
    )


def test_prepare_candidate_frame_computes_trade_anatomy_columns():
    module = load_script()
    args = module.parse_args([])

    frame = module.prepare_candidate_frame(sample_frame(), args)

    assert frame["side"].tolist() == ["BUY", "SELL", "BUY"]
    assert frame["outcome"].tolist() == ["stop_loss", "take_profit", "timeout"]
    assert frame["tp_distance_calc"].tolist() == pytest.approx([10.0, 10.0, 8.0])
    assert frame["sl_distance_calc"].tolist() == pytest.approx([5.0, 5.0, 4.0])
    assert frame["reward_risk_calc"].tolist() == pytest.approx([2.0, 2.0, 2.0])
    assert frame["hold_bars"].tolist() == pytest.approx([4.0, 5.0, 5.0])


def test_allowed_sides_filters_buy_or_sell():
    module = load_script()
    args = module.parse_args(["--allowed-sides", "SELL"])

    frame = module.prepare_candidate_frame(sample_frame(), args)

    assert frame["side"].tolist() == ["SELL"]
    assert frame["target_pnl_float"].tolist() == [7.0]


def test_summarize_subset_includes_tp_sl_rates_and_distances():
    module = load_script()
    args = module.parse_args([])
    frame = module.prepare_candidate_frame(sample_frame(), args)

    row = module.summarize_subset("all", "all", frame, len(frame))

    assert row.rows == 3
    assert row.stop_loss_rate == pytest.approx(1 / 3)
    assert row.take_profit_rate == pytest.approx(1 / 3)
    assert row.timeout_rate == pytest.approx(1 / 3)
    assert row.avg_tp_distance == pytest.approx(28 / 3)
    assert row.avg_sl_distance == pytest.approx(14 / 3)
    assert row.total_pnl == pytest.approx(-2.0)


def test_build_report_surfaces_buy_damage(tmp_path):
    module = load_script()
    args = module.parse_args([])
    frame = module.prepare_candidate_frame(sample_frame(), args)
    rows = module.build_anatomy_rows(frame, min_rows=1, bins=2)

    report = module.build_report(tmp_path / "flat.parquet", tmp_path, frame, rows)

    assert report.buy_rows == 2
    assert report.buy_total_pnl == pytest.approx(-9.0)
    assert any("BUY" in flag for flag in report.risk_flags)


def test_main_writes_outputs(tmp_path):
    module = load_script()
    flat_path = tmp_path / "flat.parquet"
    out_dir = tmp_path / "out"
    sample_frame().to_parquet(flat_path, index=False)

    result = module.main(
        [
            "--flat-path",
            str(flat_path),
            "--output-dir",
            str(out_dir),
            "--min-group-rows",
            "1",
        ]
    )

    assert result == 0
    assert (out_dir / "latest.json").exists()
    assert (out_dir / "latest.html").exists()
    assert (out_dir / "latest_anatomy.csv").exists()
