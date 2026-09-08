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
