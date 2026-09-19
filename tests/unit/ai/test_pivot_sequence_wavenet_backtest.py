"""Phase146A sequence WaveNet backtest helper tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "backtest_pivot_pattern_sequence_wavenet.py"


def load_script():
    spec = importlib.util.spec_from_file_location("backtest_pivot_pattern_sequence_wavenet", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eval_tensor_indices_uses_purged_test_split():
    module = load_script()
    selected_rows = np.arange(100, dtype=np.int64)
    args = module.parse_args(
        [
            "--eval-split",
            "test",
            "--train-frac",
            "0.70",
            "--val-frac",
            "0.15",
            "--purge-gap",
            "2",
        ]
    )

    indices, name = module.eval_tensor_indices(selected_rows, args)

    assert name == "test"
    assert indices[0] == 87
    assert indices[-1] == 99


def test_apply_max_windows_downsamples_chronologically():
    module = load_script()
    indices = np.arange(10, dtype=np.int64)

    result = module.apply_max_windows(indices, 3)

    assert result.tolist() == [0, 3, 6]


def test_monthly_stats_groups_trade_pnl():
    module = load_script()
    trade = module.BacktestTrade(
        number=1,
        timestamp="2026-01-05 00:00:00+00:00",
        side="BUY",
        tensor_row=1,
        sample_index=0,
        row_id=1,
        entry_row_id=2,
        exit_row_id=3,
        entry=1.0,
        tp=2.0,
        sl=0.5,
        exit_price=2.0,
        points_pnl=1.0,
        cash_pnl=3.5,
        balance=103.5,
        outcome="take_profit",
        action_sell_prob=0.1,
        action_hold_prob=0.2,
        action_buy_prob=0.7,
        top_prob=0.1,
        bottom_prob=0.8,
        buy_r_pred=0.2,
        sell_r_pred=-0.1,
    )

    pnl, counts = module.monthly_stats([trade])

    assert pnl == {"2026-01": 3.5}
    assert counts == {"2026-01": 1}


def test_load_model_uses_unsafe_deserialization_for_project_lambda_layers(tmp_path, monkeypatch):
    module = load_script()
    model_path = tmp_path / "v1_model.keras"
    model_path.write_text("placeholder", encoding="utf-8")
    captured = {}

    class FakeModels:
        @staticmethod
        def load_model(path, **kwargs):
            captured["path"] = path
            captured["kwargs"] = kwargs
            return "model"

    class FakeKeras:
        models = FakeModels()

    class FakeTF:
        keras = FakeKeras()

    monkeypatch.setattr(module, "require_tensorflow", lambda: FakeTF())

    result = module.load_model(model_path)

    assert result == "model"
    assert captured["path"] == model_path
    assert captured["kwargs"] == {"safe_mode": False, "compile": False}


def test_load_model_rebuilds_when_lambda_shape_inference_fails(tmp_path, monkeypatch):
    module = load_script()
    model_path = tmp_path / "v1_model.keras"
    model_path.write_text("placeholder", encoding="utf-8")
    calls = {"rebuilt": 0}

    class FakeModels:
        @staticmethod
        def load_model(path, **kwargs):
            raise NotImplementedError("Lambda output shape")

    class FakeKeras:
        models = FakeModels()

    class FakeTF:
        keras = FakeKeras()

    monkeypatch.setattr(module, "require_tensorflow", lambda: FakeTF())

    def fake_rebuild(tf, path, record, meta, input_shape):
        calls["rebuilt"] += 1
        assert path == model_path
        assert input_shape == (100, 140)
        return "rebuilt-model"

    monkeypatch.setattr(module, "rebuild_model_from_record", fake_rebuild)

    result = module.load_model(model_path, {"payload": {}}, {"feature_names": []}, (100, 140))

    assert result == "rebuilt-model"
    assert calls["rebuilt"] == 1
