"""فاز ۶۲ — پیچ‌های معماری و ولیدیشن در GUI.

سه مسیر داشبورد اسکریپت آموزش را اجرا می‌کنند: Train a model ·
Retrain a saved model · Find best learning rate. هر سه باید
``--n-layers``/``--n-blocks``/``--val-size`` را فقط وقتی کاربر مقدار
داده پاس بدهند (0 = پیش‌فرض/auto — فلگ ارسال نمی‌شود).
"""

from __future__ import annotations

import sys
import types

import pytest

from ShadBotTrader.presentation.commands import Command, CommandKind, CommandResult, CommandStatus
from ShadBotTrader.presentation.commands.handlers import (
    AccountCommandHandlers,
    descriptor_for,
)


@pytest.fixture
def gui(monkeypatch, tmp_path):
    """CommandHandlers با TF جعلی و لیست دیتاست جعلی — بدون subprocess."""
    monkeypatch.setitem(sys.modules, "tensorflow", types.ModuleType("tensorflow"))
    monkeypatch.setattr(
        "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
        lambda root: ["5M"],
    )
    # train_dual_models/optimise روی زیرکلاس Account زندگی می‌کنند
    return AccountCommandHandlers(tmp_path / "x.db", tmp_path / "storage")


def _capture(monkeypatch, handlers):
    captured = {}

    def fake_run_script(command, arguments, success_message, started, **kwargs):
        captured["args"] = list(arguments)
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(handlers, "_run_script", fake_run_script)
    return captured


def test_train_descriptor_has_architecture_fields():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_DUAL_MODELS).fields}
    assert {"n_layers", "n_blocks", "val_size"} <= fields


def test_train_descriptor_has_trend_score_loss_field():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_DUAL_MODELS).fields}
    assert "trend_score_loss" in fields


def test_train_descriptor_has_trend_signal_class_weight_field():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_DUAL_MODELS).fields}
    assert "class_weight" in fields


def test_train_descriptor_has_monitor_metric_field():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_DUAL_MODELS).fields}
    assert "monitor_metric" in fields


def test_retrain_descriptor_has_architecture_fields():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_MODEL).fields}
    assert {"n_layers", "n_blocks", "val_size"} <= fields


def test_optimise_descriptor_has_architecture_fields():
    fields = {field.name for field in descriptor_for(CommandKind.OPTIMISE_LEARNING_RATE).fields}
    assert {"n_layers", "n_blocks"} <= fields


def test_train_dual_models_passes_knobs(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)
    result = gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {
                "model": "signal",
                "dataset": "5M",
                "window": "150",
                "n_layers": "4",
                "n_blocks": "2",
                "val_size": "300",
            },
        )
    )
    assert result.status is CommandStatus.SUCCEEDED
    args = captured["args"]
    assert args[args.index("--n-layers") + 1] == "4"
    assert args[args.index("--n-blocks") + 1] == "2"
    assert args[args.index("--val-size") + 1] == "300"


def test_train_dual_models_omits_flags_when_zero(gui, monkeypatch):
    """0 = پیش‌فرض/auto — فلگ نباید به اسکریپت برسد."""
    captured = _capture(monkeypatch, gui)
    gui.train_dual_models(
        Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "signal", "dataset": "5M"})
    )
    args = captured["args"]
    assert "--n-layers" not in args
    assert "--n-blocks" not in args
    assert "--val-size" not in args


def test_train_dual_models_passes_trend_score_mae_loss(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "trend_score", "dataset": "5M", "trend_score_loss": "mae"},
        )
    )

    args = captured["args"]
    assert args[args.index("--trend-score-loss") + 1] == "mae"


def test_train_dual_models_ignores_trend_score_loss_for_other_roles(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "signal", "dataset": "5M", "trend_score_loss": "mae"},
        )
    )

    assert "--trend-score-loss" not in captured["args"]


def test_train_dual_models_passes_trend_signal_class_weight(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "trend_signal", "dataset": "5M", "class_weight": "auto"},
        )
    )

    args = captured["args"]
    assert args[args.index("--class-weight") + 1] == "auto"


def test_train_dual_models_passes_trend_signal_monitor_metric(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {
                "model": "trend_signal",
                "dataset": "5M",
                "monitor_metric": "val_buy_sell_f1",
            },
        )
    )

    args = captured["args"]
    assert args[args.index("--monitor-metric") + 1] == "val_buy_sell_f1"


def test_train_dual_models_ignores_invalid_monitor_metric_for_range(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "range", "dataset": "5M", "monitor_metric": "val_buy_sell_f1"},
        )
    )

    assert "--monitor-metric" not in captured["args"]


def test_train_dual_models_ignores_class_weight_for_other_roles(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "signal", "dataset": "5M", "class_weight": "auto"},
        )
    )

    assert "--class-weight" not in captured["args"]


def test_retrain_passes_knobs(gui, monkeypatch, tmp_path):
    """Retrain به یک record ذخیره‌شده نیاز دارد — کاتالوگ minimal می‌سازیم."""
    storage = tmp_path / "storage"
    models = storage / "models" / "gold_signal_5m"
    models.mkdir(parents=True)
    (models / "v1_training.json").write_text(
        '{"model_id": "gold_signal_5m", "version": 1, "role": "signal", '
        '"symbol": "XAUUSD", "timeframe": "5M", "window_size": 150, '
        '"feature_columns": 177, "epochs": 10, "threshold": 0.006, '
        '"horizon": 0, "headline_metric": "val_loss 0.9"}',
        encoding="utf-8",
    )
    captured = _capture(monkeypatch, gui)
    gui._storage_root = storage  # noqa: SLF001 — تست
    result = gui.train_model(
        Command(
            CommandKind.TRAIN_MODEL,
            {
                "saved_model": "gold_signal_5m",
                "dataset": "5M",
                "resume": "0",
                "n_layers": "4",
                "n_blocks": "2",
            },
        )
    )
    assert result.status is CommandStatus.SUCCEEDED
    args = captured["args"]
    assert args[args.index("--n-layers") + 1] == "4"
    assert args[args.index("--n-blocks") + 1] == "2"
    assert "--resume" not in args


def test_optimise_passes_architecture(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)
    gui.optimise_learning_rate(
        Command(
            CommandKind.OPTIMISE_LEARNING_RATE,
            {"model": "signal", "dataset": "5M", "n_layers": "4", "n_blocks": "2"},
        )
    )
    args = captured["args"]
    assert args[args.index("--n-layers") + 1] == "4"
    assert args[args.index("--n-blocks") + 1] == "2"


def test_optimise_passes_trend_score_mae_loss(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.optimise_learning_rate(
        Command(
            CommandKind.OPTIMISE_LEARNING_RATE,
            {"model": "trend_score", "dataset": "5M", "trend_score_loss": "mae"},
        )
    )

    args = captured["args"]
    assert args[args.index("--signal-timeframe") + 1] == "5M"
    assert args[args.index("--trend-score-loss") + 1] == "mae"


def test_train_trend_signal_booster_descriptor_exists():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_TREND_SIGNAL_BOOSTER).fields}
    assert {"booster", "output_mode", "summary_mode", "window", "label_horizon"} <= fields


def test_train_trend_signal_booster_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_trend_signal_booster(
        Command(
            CommandKind.TRAIN_TREND_SIGNAL_BOOSTER,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "booster": "lightgbm",
                "output_mode": "buy",
                "summary_mode": "basic",
                "window": "288",
                "label_horizon": "288",
                "atr_mult": "0.5",
                "train_ratio": "80",
                "folds": "3",
                "val_size": "2000",
                "class_weight": "auto",
                "n_estimators": "25",
                "booster_lr": "0.03",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_trend_signal_boosters.py"
    assert args[args.index("--booster") + 1] == "lightgbm"
    assert args[args.index("--output-mode") + 1] == "buy"
    assert args[args.index("--summary-mode") + 1] == "basic"
    assert args[args.index("--val-size") + 1] == "2000"
    assert args[args.index("--n-estimators") + 1] == "25"


def test_calibrate_trend_signal_boosters_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS).fields
    }
    assert {"buy_model_id", "sell_model_id", "threshold_min", "min_side_trades"} <= fields


def test_calibrate_trend_signal_boosters_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.calibrate_trend_signal_boosters(
        Command(
            CommandKind.CALIBRATE_TREND_SIGNAL_BOOSTERS,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "booster": "lightgbm",
                "summary_mode": "basic",
                "buy_model_id": "gold_buy_lightgbm_basic_5m",
                "sell_model_id": "gold_sell_lightgbm_basic_5m",
                "threshold_min": "0.40",
                "threshold_max": "0.90",
                "min_side_trades": "25",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/calibrate_trend_signal_boosters.py"
    assert args[args.index("--buy-model-id") + 1] == "gold_buy_lightgbm_basic_5m"
    assert args[args.index("--sell-model-id") + 1] == "gold_sell_lightgbm_basic_5m"
    assert args[args.index("--threshold-min") + 1] == "0.4"
    assert args[args.index("--min-side-trades") + 1] == "25"


def test_build_hybrid_xgboost_matrix_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BUILD_HYBRID_XGBOOST_MATRIX).fields
    }
    assert {"include_wavenet", "include_range", "range_1d_model_id", "range_4h_model_id"} <= fields


def test_build_hybrid_xgboost_matrix_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.build_hybrid_xgboost_matrix(
        Command(
            CommandKind.BUILD_HYBRID_XGBOOST_MATRIX,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "window": "288",
                "label_horizon": "288",
                "booster": "lightgbm",
                "range_1d_model_id": "gold_range_1d",
                "range_4h_model_id": "gold_range_4h",
                "include_wavenet": "1",
                "require_range": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/build_hybrid_xgboost_matrix.py"
    assert args[args.index("--include-wavenet") + 1] == "1"
    assert args[args.index("--require-range") + 1] == "1"
    assert args[args.index("--range-1d-model-id") + 1] == "gold_range_1d"
    assert args[args.index("--range-4h-model-id") + 1] == "gold_range_4h"


def test_backtest_hybrid_xgboost_head_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD).fields
    }
    assert {"model_id", "threshold_min", "score_metric", "max_hold_bars"} <= fields


def test_backtest_hybrid_xgboost_head_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_hybrid_xgboost_head(
        Command(
            CommandKind.BACKTEST_HYBRID_XGBOOST_HEAD,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "eval_frac": "0.25",
                "threshold_min": "0.45",
                "score_metric": "profit_factor",
                "max_hold_bars": "48",
                "spread_mode": "fixed",
                "spread_value": "1.8",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_hybrid_xgboost_head.py"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--eval-frac") + 1] == "0.25"
    assert args[args.index("--score-metric") + 1] == "profit_factor"
    assert args[args.index("--spread-mode") + 1] == "fixed"


def test_check_hybrid_significance_descriptor_exists():
    fields = {field.name for field in descriptor_for(CommandKind.CHECK_HYBRID_SIGNIFICANCE).fields}
    assert {"model_id", "trials", "seed", "white_check", "candidate_rows_path"} <= fields


def test_check_hybrid_significance_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.check_hybrid_significance(
        Command(
            CommandKind.CHECK_HYBRID_SIGNIFICANCE,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "trials": "250",
                "seed": "123",
                "buy_threshold": "0.80",
                "sell_threshold": "0.65",
                "white_check": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_significance_check.py"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--trials") + 1] == "250"
    assert args[args.index("--seed") + 1] == "123"
    assert args[args.index("--buy-threshold") + 1] == "0.8"
    assert args[args.index("--sell-threshold") + 1] == "0.65"
    assert args[args.index("--white-check") + 1] == "1"


def test_audit_hybrid_range_aware_decisions_descriptor_exists():
    fields = {
        field.name
        for field in descriptor_for(CommandKind.AUDIT_HYBRID_RANGE_AWARE_DECISIONS).fields
    }
    assert {"model_id", "min_4h_room", "min_1d_room", "base_quantity"} <= fields


def test_audit_hybrid_range_aware_decisions_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.audit_hybrid_range_aware_decisions(
        Command(
            CommandKind.AUDIT_HYBRID_RANGE_AWARE_DECISIONS,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "eval_frac": "0.30",
                "buy_threshold": "0.80",
                "sell_threshold": "0.65",
                "min_4h_room": "2",
                "base_quantity": "0.5",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_hybrid_range_aware_decisions.py"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--eval-frac") + 1] == "0.3"
    assert args[args.index("--buy-threshold") + 1] == "0.8"
    assert args[args.index("--sell-threshold") + 1] == "0.65"
    assert args[args.index("--min-4h-room") + 1] == "2.0"
    assert args[args.index("--base-quantity") + 1] == "0.5"


def test_report_hybrid_full_backtest_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.REPORT_HYBRID_FULL_BACKTEST).fields
    }
    assert {
        "model_id",
        "source_mode",
        "stream_chunk_size",
        "stream_wavenet",
        "eval_frac",
        "max_hold_bars",
        "initial_capital",
        "units",
    } <= fields


def test_report_hybrid_full_backtest_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.report_hybrid_full_backtest(
        Command(
            CommandKind.REPORT_HYBRID_FULL_BACKTEST,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "source_mode": "stream",
                "stream_chunk_size": "500",
                "stream_wavenet": "neutral",
                "eval_frac": "1.0",
                "min_4h_room": "2",
                "same_bar_policy": "stop_first",
                "initial_capital": "100",
                "units": "0.1",
                "report_title": "Full report",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/report_hybrid_full_backtest.py"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--source-mode") + 1] == "stream"
    assert args[args.index("--stream-chunk-size") + 1] == "500"
    assert args[args.index("--stream-wavenet") + 1] == "neutral"
    assert args[args.index("--eval-frac") + 1] == "1.0"
    assert args[args.index("--min-4h-room") + 1] == "2.0"
    assert args[args.index("--same-bar-policy") + 1] == "stop_first"
    assert args[args.index("--initial-capital") + 1] == "100.0"
    assert args[args.index("--units") + 1] == "0.1"
    assert args[args.index("--report-title") + 1] == "Full report"


def test_replay_hybrid_chronological_descriptor_exists():
    fields = {
        field.name
        for field in descriptor_for(CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST).fields
    }
    assert {"source_mode", "stream_chunk_size", "stream_wavenet", "initial_capital"} <= fields


def test_replay_hybrid_chronological_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.replay_hybrid_chronological_backtest(
        Command(
            CommandKind.REPLAY_HYBRID_CHRONOLOGICAL_BACKTEST,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "source_mode": "stream",
                "stream_chunk_size": "250",
                "stream_wavenet": "neutral",
                "initial_capital": "100",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/replay_hybrid_chronological_backtest.py"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--source-mode") + 1] == "stream"
    assert args[args.index("--stream-chunk-size") + 1] == "250"
    assert args[args.index("--stream-wavenet") + 1] == "neutral"
    assert args[args.index("--initial-capital") + 1] == "100.0"
    assert args[args.index("--units") + 1] == "0.1"


def test_build_hybrid_telemetry_tensor_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR).fields
    }
    assert {
        "source_mode",
        "tensor_window",
        "safe_lag_bars",
        "telemetry_lag_mode",
        "sample_stride",
        "include_htf_context",
        "same_bar_policy",
    } <= fields


def test_build_hybrid_telemetry_tensor_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.build_hybrid_telemetry_tensor(
        Command(
            CommandKind.BUILD_HYBRID_TELEMETRY_TENSOR,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "source_mode": "matrix",
                "model_id": "gold_hybrid_lightgbm_head_5m",
                "tensor_window": "150",
                "safe_lag_bars": "48",
                "telemetry_lag_mode": "fixed",
                "sample_stride": "2",
                "max_tensor_mb": "256",
                "include_htf_context": "1",
                "same_bar_policy": "tp_first",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/build_hybrid_telemetry_tensor.py"
    assert args[args.index("--source-mode") + 1] == "matrix"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--tensor-window") + 1] == "150"
    assert args[args.index("--safe-lag-bars") + 1] == "48"
    assert args[args.index("--telemetry-lag-mode") + 1] == "fixed"
    assert args[args.index("--sample-stride") + 1] == "2"
    assert args[args.index("--max-tensor-mb") + 1] == "256.0"
    assert args[args.index("--include-htf-context") + 1] == "1"
    assert args[args.index("--same-bar-policy") + 1] == "tp_first"


def test_inspect_hybrid_telemetry_tensor_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.INSPECT_HYBRID_TELEMETRY_TENSOR).fields
    }
    assert {"tensor_path", "flat_path", "sample_indices", "time_buckets", "max_samples"} <= fields


def test_inspect_hybrid_telemetry_tensor_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.inspect_hybrid_telemetry_tensor(
        Command(
            CommandKind.INSPECT_HYBRID_TELEMETRY_TENSOR,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "sample_indices": "first,10,last",
                "time_buckets": "60",
                "max_samples": "3",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/inspect_hybrid_telemetry_tensor.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--sample-indices") + 1] == "first,10,last"
    assert args[args.index("--time-buckets") + 1] == "60"
    assert args[args.index("--max-samples") + 1] == "3"


def test_train_hybrid_meta_labeler_descriptor_exists():
    fields = {field.name for field in descriptor_for(CommandKind.TRAIN_HYBRID_META_LABELER).fields}
    assert {"flat_path", "task", "booster", "candidate_only", "meta_threshold"} <= fields


def test_train_hybrid_meta_labeler_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_hybrid_meta_labeler(
        Command(
            CommandKind.TRAIN_HYBRID_META_LABELER,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "task": "classifier",
                "booster": "lightgbm",
                "flat_path": "telemetry.parquet",
                "meta_threshold": "0.60",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_hybrid_meta_labeler.py"
    assert args[args.index("--flat-path") + 1] == "telemetry.parquet"
    assert args[args.index("--task") + 1] == "classifier"
    assert args[args.index("--booster") + 1] == "lightgbm"
    assert args[args.index("--meta-threshold") + 1] == "0.6"


def test_backtest_hybrid_meta_labeler_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_HYBRID_META_LABELER).fields
    }
    assert {"flat_path", "meta_model_id", "meta_threshold", "initial_capital", "units"} <= fields


def test_backtest_hybrid_meta_labeler_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_hybrid_meta_labeler(
        Command(
            CommandKind.BACKTEST_HYBRID_META_LABELER,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "telemetry.parquet",
                "meta_model_id": "gold_hybrid_meta_lightgbm_5m",
                "meta_threshold": "0.61",
                "initial_capital": "100",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_hybrid_meta_labeler.py"
    assert args[args.index("--flat-path") + 1] == "telemetry.parquet"
    assert args[args.index("--meta-model-id") + 1] == "gold_hybrid_meta_lightgbm_5m"
    assert args[args.index("--meta-threshold") + 1] == "0.61"
    assert args[args.index("--initial-capital") + 1] == "100.0"
    assert args[args.index("--units") + 1] == "0.1"


def test_train_hybrid_telemetry_wavenet_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET).fields
    }
    assert {"tensor_path", "task", "purge_gap", "n_layers", "n_blocks"} <= fields


def test_train_hybrid_telemetry_wavenet_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_hybrid_telemetry_wavenet(
        Command(
            CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "task": "multihead",
                "purge_gap": "336",
                "n_layers": "5",
                "n_blocks": "2",
                "epochs": "7",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_hybrid_telemetry_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--task") + 1] == "multihead"
    assert args[args.index("--purge-gap") + 1] == "336"
    assert args[args.index("--n-layers") + 1] == "5"
    assert args[args.index("--n-blocks") + 1] == "2"
    assert args[args.index("--epochs") + 1] == "7"


def test_backtest_hybrid_telemetry_wavenet_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET).fields
    }
    assert {"tensor_path", "flat_path", "decision_mode", "meta_threshold"} <= fields


def test_backtest_hybrid_telemetry_wavenet_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_hybrid_telemetry_wavenet(
        Command(
            CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "model_id": "gold_hybrid_telemetry_wavenet_5m",
                "decision_mode": "both",
                "meta_threshold": "0.60",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_hybrid_telemetry_wavenet.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_telemetry_wavenet_5m"
    assert args[args.index("--decision-mode") + 1] == "both"
    assert args[args.index("--meta-threshold") + 1] == "0.6"
    assert args[args.index("--units") + 1] == "0.1"


def test_train_hybrid_telemetry_tsmixer_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER).fields
    }
    assert {"tensor_path", "task", "mixer_layers", "time_hidden_units", "purge_gap"} <= fields


def test_train_hybrid_telemetry_tsmixer_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_hybrid_telemetry_tsmixer(
        Command(
            CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "task": "multihead",
                "mixer_layers": "3",
                "time_hidden_units": "32",
                "feature_hidden_units": "64",
                "epochs": "5",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_hybrid_telemetry_tsmixer.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--task") + 1] == "multihead"
    assert args[args.index("--mixer-layers") + 1] == "3"
    assert args[args.index("--time-hidden-units") + 1] == "32"
    assert args[args.index("--feature-hidden-units") + 1] == "64"
    assert args[args.index("--epochs") + 1] == "5"


def test_backtest_hybrid_telemetry_tsmixer_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER).fields
    }
    assert {"tensor_path", "flat_path", "decision_mode", "meta_threshold"} <= fields


def test_backtest_hybrid_telemetry_tsmixer_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_hybrid_telemetry_tsmixer(
        Command(
            CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "model_id": "gold_hybrid_telemetry_tsmixer_5m",
                "decision_mode": "both",
                "meta_threshold": "0.60",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_hybrid_telemetry_tsmixer.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_telemetry_tsmixer_5m"
    assert args[args.index("--decision-mode") + 1] == "both"
    assert args[args.index("--meta-threshold") + 1] == "0.6"
    assert args[args.index("--units") + 1] == "0.1"


def test_train_hybrid_telemetry_patchtst_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST).fields
    }
    assert {"tensor_path", "patch_len", "stride", "d_model", "layers", "heads"} <= fields


def test_train_hybrid_telemetry_patchtst_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_hybrid_telemetry_patchtst(
        Command(
            CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "task": "multihead",
                "patch_len": "16",
                "stride": "8",
                "d_model": "64",
                "layers": "3",
                "heads": "4",
                "epochs": "5",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_hybrid_telemetry_patchtst.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--task") + 1] == "multihead"
    assert args[args.index("--patch-len") + 1] == "16"
    assert args[args.index("--stride") + 1] == "8"
    assert args[args.index("--d-model") + 1] == "64"
    assert args[args.index("--layers") + 1] == "3"
    assert args[args.index("--heads") + 1] == "4"
    assert args[args.index("--epochs") + 1] == "5"


def test_backtest_hybrid_telemetry_patchtst_descriptor_exists():
    fields = {
        field.name
        for field in descriptor_for(CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST).fields
    }
    assert {"tensor_path", "flat_path", "decision_mode", "meta_threshold"} <= fields


def test_backtest_hybrid_telemetry_patchtst_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_hybrid_telemetry_patchtst(
        Command(
            CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "model_id": "gold_hybrid_telemetry_patchtst_5m",
                "decision_mode": "both",
                "meta_threshold": "0.60",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_hybrid_telemetry_patchtst.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--model-id") + 1] == "gold_hybrid_telemetry_patchtst_5m"
    assert args[args.index("--decision-mode") + 1] == "both"
    assert args[args.index("--meta-threshold") + 1] == "0.6"
    assert args[args.index("--units") + 1] == "0.1"


def test_backtest_meta_filtered_hybrid_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_META_FILTERED_HYBRID).fields
    }
    assert {"candidates", "decision_modes", "meta_thresholds", "score_metric"} <= fields


def test_backtest_meta_filtered_hybrid_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_meta_filtered_hybrid(
        Command(
            CommandKind.BACKTEST_META_FILTERED_HYBRID,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "tensor_path": "tensor.npz",
                "candidates": "base,gold_hybrid_meta_lightgbm_5m",
                "decision_modes": "meta,both",
                "meta_thresholds": "record,0.60",
                "score_metric": "drawdown_adjusted",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_meta_filtered_hybrid.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--candidates") + 1] == "base,gold_hybrid_meta_lightgbm_5m"
    assert args[args.index("--decision-modes") + 1] == "meta,both"
    assert args[args.index("--meta-thresholds") + 1] == "record,0.60"
    assert args[args.index("--score-metric") + 1] == "drawdown_adjusted"
    assert args[args.index("--units") + 1] == "0.1"


def test_run_hybrid_walk_forward_validation_descriptor_exists():
    fields = {
        field.name
        for field in descriptor_for(CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION).fields
    }
    assert {"flat_path", "train_months_min", "validation_months", "purge_gap_bars"} <= fields


def test_run_hybrid_walk_forward_validation_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.run_hybrid_walk_forward_validation(
        Command(
            CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "booster": "lightgbm",
                "start_month": "2026-01",
                "train_months_min": "3",
                "validation_months": "1",
                "purge_gap_bars": "336",
                "meta_thresholds": "0.50,0.60",
                "units": "0.1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_hybrid_walk_forward_validation.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--booster") + 1] == "lightgbm"
    assert args[args.index("--start-month") + 1] == "2026-01"
    assert args[args.index("--train-months-min") + 1] == "3"
    assert args[args.index("--validation-months") + 1] == "1"
    assert args[args.index("--purge-gap-bars") + 1] == "336"
    assert args[args.index("--meta-thresholds") + 1] == "0.50,0.60"
    assert args[args.index("--units") + 1] == "0.1"


def test_run_hybrid_tensor_walk_forward_validation_descriptor_exists():
    fields = {
        field.name
        for field in descriptor_for(CommandKind.RUN_HYBRID_TENSOR_WALK_FORWARD_VALIDATION).fields
    }
    assert {
        "tensor_path",
        "flat_path",
        "decision_modes",
        "score_thresholds",
        "allow_no_trade",
        "min_validation_score",
        "min_validation_profit_factor",
        "max_validation_drawdown",
        "train_months_min",
        "validation_months",
        "epochs",
    } <= fields


def test_run_hybrid_tensor_walk_forward_validation_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.run_hybrid_tensor_walk_forward_validation(
        Command(
            CommandKind.RUN_HYBRID_TENSOR_WALK_FORWARD_VALIDATION,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "tensor_path": "tensor.npz",
                "flat_path": "flat.parquet",
                "task": "multihead",
                "decision_modes": "score,both",
                "score_thresholds": "0,0.05,0.10",
                "allow_no_trade": "1",
                "min_validation_score": "0",
                "min_validation_profit_factor": "1.10",
                "max_validation_drawdown": "120",
                "train_months_min": "3",
                "validation_months": "1",
                "epochs": "12",
                "max_folds": "1",
                "verbose": "0",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_hybrid_tensor_walk_forward_validation.py"
    assert args[args.index("--tensor-path") + 1] == "tensor.npz"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--task") + 1] == "multihead"
    assert args[args.index("--decision-modes") + 1] == "score,both"
    assert args[args.index("--score-thresholds") + 1] == "0,0.05,0.10"
    assert args[args.index("--allow-no-trade") + 1] == "1"
    assert args[args.index("--min-validation-score") + 1] == "0.0"
    assert args[args.index("--min-validation-profit-factor") + 1] == "1.1"
    assert args[args.index("--max-validation-drawdown") + 1] == "120.0"
    assert args[args.index("--epochs") + 1] == "12"
    assert args[args.index("--max-folds") + 1] == "1"
    assert args[args.index("--verbose") + 1] == "0"


def test_analyze_tensor_failure_regimes_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.ANALYZE_TENSOR_FAILURE_REGIMES).fields
    }
    assert {
        "flat_path",
        "walk_forward_json",
        "candidate_only",
        "min_group_rows",
        "top_n",
        "quantile_bins",
    } <= fields


def test_analyze_tensor_failure_regimes_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.analyze_tensor_failure_regimes(
        Command(
            CommandKind.ANALYZE_TENSOR_FAILURE_REGIMES,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "walk_forward_json": "wf.json",
                "candidate_only": "1",
                "min_group_rows": "12",
                "top_n": "7",
                "quantile_bins": "4",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/analyze_tensor_failure_regimes.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--walk-forward-json") + 1] == "wf.json"
    assert args[args.index("--candidate-only") + 1] == "1"
    assert args[args.index("--min-group-rows") + 1] == "12"
    assert args[args.index("--top-n") + 1] == "7"
    assert args[args.index("--quantile-bins") + 1] == "4"


def test_backtest_regime_filtered_hybrid_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_REGIME_FILTERED_HYBRID).fields
    }
    assert {
        "flat_path",
        "allowed_sides",
        "buy_min_confidence",
        "sell_min_confidence",
        "buy_min_side_4h_room",
        "sell_min_side_4h_room",
        "max_range_4h_width",
    } <= fields


def test_backtest_regime_filtered_hybrid_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_regime_filtered_hybrid(
        Command(
            CommandKind.BACKTEST_REGIME_FILTERED_HYBRID,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "allowed_sides": "SELL",
                "sell_allowed_hours": "8,9",
                "buy_min_confidence": "0.98",
                "sell_min_confidence": "0.70",
                "max_range_4h_width": "30",
                "block_specialist_conflict": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_regime_filtered_hybrid.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--allowed-sides") + 1] == "SELL"
    assert args[args.index("--sell-allowed-hours") + 1] == "8,9"
    assert args[args.index("--buy-min-confidence") + 1] == "0.98"
    assert args[args.index("--sell-min-confidence") + 1] == "0.7"
    assert args[args.index("--max-range-4h-width") + 1] == "30.0"
    assert args[args.index("--block-specialist-conflict") + 1] == "1"


def test_analyze_trade_anatomy_descriptor_exists():
    fields = {field.name for field in descriptor_for(CommandKind.ANALYZE_TRADE_ANATOMY).fields}
    assert {
        "flat_path",
        "candidate_only",
        "start_month",
        "end_month",
        "allowed_sides",
        "min_group_rows",
        "quantile_bins",
        "top_n",
    } <= fields


def test_analyze_trade_anatomy_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.analyze_trade_anatomy(
        Command(
            CommandKind.ANALYZE_TRADE_ANATOMY,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "candidate_only": "1",
                "start_month": "2026-01",
                "end_month": "2026-08",
                "allowed_sides": "BUY,SELL",
                "min_group_rows": "11",
                "quantile_bins": "4",
                "top_n": "9",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/analyze_trade_anatomy.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--candidate-only") + 1] == "1"
    assert args[args.index("--start-month") + 1] == "2026-01"
    assert args[args.index("--end-month") + 1] == "2026-08"
    assert args[args.index("--allowed-sides") + 1] == "BUY,SELL"
    assert args[args.index("--min-group-rows") + 1] == "11"
    assert args[args.index("--quantile-bins") + 1] == "4"
    assert args[args.index("--top-n") + 1] == "9"


def test_backtest_bracket_recalibration_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.BACKTEST_BRACKET_RECALIBRATION).fields
    }
    assert {
        "flat_path",
        "max_tp_distances",
        "max_sl_distances",
        "max_reward_risks",
        "buy_max_tp_distance",
        "sell_max_tp_distance",
        "same_bar_policy",
    } <= fields


def test_backtest_bracket_recalibration_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.backtest_bracket_recalibration(
        Command(
            CommandKind.BACKTEST_BRACKET_RECALIBRATION,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "allowed_sides": "BUY,SELL",
                "max_tp_distances": "original,12",
                "max_sl_distances": "original,20",
                "max_reward_risks": "original,1.0",
                "buy_max_tp_distance": "14",
                "sell_max_sl_distance": "23.56",
                "same_bar_policy": "tp_first",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/backtest_bracket_recalibration.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--max-tp-distances") + 1] == "original,12"
    assert args[args.index("--max-sl-distances") + 1] == "original,20"
    assert args[args.index("--max-reward-risks") + 1] == "original,1.0"
    assert args[args.index("--buy-max-tp-distance") + 1] == "14.0"
    assert args[args.index("--sell-max-sl-distance") + 1] == "23.56"
    assert args[args.index("--same-bar-policy") + 1] == "tp_first"


def test_audit_candidate_direction_entry_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.AUDIT_CANDIDATE_DIRECTION_ENTRY).fields
    }
    assert {
        "flat_path",
        "candidate_only",
        "allowed_sides",
        "entry_delays",
        "side_modes",
        "execution_modes",
        "same_bar_policy",
        "min_group_trades",
    } <= fields


def test_audit_candidate_direction_entry_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.audit_candidate_direction_entry(
        Command(
            CommandKind.AUDIT_CANDIDATE_DIRECTION_ENTRY,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "flat_path": "flat.parquet",
                "candidate_only": "1",
                "allowed_sides": "BUY,SELL",
                "entry_delays": "0,1,2,3",
                "side_modes": "original,flipped",
                "execution_modes": "independent,chronological",
                "same_bar_policy": "tp_first",
                "min_group_trades": "3",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/audit_candidate_direction_entry.py"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--candidate-only") + 1] == "1"
    assert args[args.index("--allowed-sides") + 1] == "BUY,SELL"
    assert args[args.index("--entry-delays") + 1] == "0,1,2,3"
    assert args[args.index("--side-modes") + 1] == "original,flipped"
    assert args[args.index("--execution-modes") + 1] == "independent,chronological"
    assert args[args.index("--same-bar-policy") + 1] == "tp_first"
    assert args[args.index("--min-group-trades") + 1] == "3"


def test_train_pivot_pattern_recognition_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.TRAIN_PIVOT_PATTERN_RECOGNITION).fields
    }
    assert {
        "source_mode",
        "yahoo_symbol",
        "five_timeframe",
        "hourly_timeframe",
        "h4_timeframe",
        "daily_timeframe",
        "daily_path",
        "five_path",
        "model_kind",
        "lookahead_bars",
        "pivot_move_atr",
        "max_features",
        "risk_per_trade",
    } <= fields


def test_train_pivot_pattern_recognition_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_pivot_pattern_recognition(
        Command(
            CommandKind.TRAIN_PIVOT_PATTERN_RECOGNITION,
            {
                "symbol": "XAUUSD",
                "source_mode": "yahoo",
                "yahoo_symbol": "GC=F",
                "model_kind": "centroid",
                "lookahead_bars": "36",
                "pivot_move_atr": "0.8",
                "max_features": "12",
                "risk_per_trade": "0.005",
                "save_model": "0",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/train_pivot_pattern_recognition.py"
    assert args[args.index("--source-mode") + 1] == "yahoo"
    assert args[args.index("--yahoo-symbol") + 1] == "GC=F"
    assert args[args.index("--model-kind") + 1] == "centroid"
    assert args[args.index("--lookahead-bars") + 1] == "36"
    assert args[args.index("--pivot-move-atr") + 1] == "0.8"
    assert args[args.index("--max-features") + 1] == "12"
    assert args[args.index("--risk-per-trade") + 1] == "0.005"
    assert args[args.index("--save-model") + 1] == "0"


def test_train_pivot_pattern_recognition_defaults_to_storage(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.train_pivot_pattern_recognition(
        Command(CommandKind.TRAIN_PIVOT_PATTERN_RECOGNITION, {"symbol": "XAUUSD"})
    )

    args = captured["args"]
    assert args[args.index("--source-mode") + 1] == "storage"
    assert args[args.index("--five-timeframe") + 1] == "5M"
    assert args[args.index("--hourly-timeframe") + 1] == "1H"
    assert args[args.index("--h4-timeframe") + 1] == "4H"
    assert args[args.index("--daily-timeframe") + 1] == "1D"


def test_validate_production_hybrid_stack_descriptor_exists():
    fields = {
        field.name for field in descriptor_for(CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK).fields
    }
    assert {"config_path", "mode", "position_size_units", "kill_switch_enabled"} <= fields


def test_validate_production_hybrid_stack_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.validate_production_hybrid_stack(
        Command(
            CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "config_path": "configs/hybrid_production_stack.json",
                "mode": "paper_shadow",
                "base_model_id": "gold_hybrid_lightgbm_head_5m",
                "position_size_units": "0.1",
                "write_config": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/validate_production_hybrid_stack.py"
    assert args[args.index("--config-path") + 1] == "configs/hybrid_production_stack.json"
    assert args[args.index("--mode") + 1] == "paper_shadow"
    assert args[args.index("--base-model-id") + 1] == "gold_hybrid_lightgbm_head_5m"
    assert args[args.index("--position-size-units") + 1] == "0.1"
    assert args[args.index("--write-config") + 1] == "1"


def test_run_hybrid_paper_shadow_descriptor_exists():
    fields = {field.name for field in descriptor_for(CommandKind.RUN_HYBRID_PAPER_SHADOW).fields}
    assert {"config_path", "flat_path", "allow_validation_fail", "max_windows"} <= fields


def test_run_hybrid_paper_shadow_passes_gui_args(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)

    gui.run_hybrid_paper_shadow(
        Command(
            CommandKind.RUN_HYBRID_PAPER_SHADOW,
            {
                "config_path": "configs/hybrid_production_stack.json",
                "flat_path": "flat.parquet",
                "eval_frac": "0.5",
                "max_windows": "100",
                "allow_validation_fail": "1",
            },
        )
    )

    args = captured["args"]
    assert args[0] == "scripts/run_hybrid_paper_shadow.py"
    assert args[args.index("--config-path") + 1] == "configs/hybrid_production_stack.json"
    assert args[args.index("--flat-path") + 1] == "flat.parquet"
    assert args[args.index("--eval-frac") + 1] == "0.5"
    assert args[args.index("--max-windows") + 1] == "100"
    assert args[args.index("--allow-validation-fail") + 1] == "1"
