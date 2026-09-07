"""Phase 107 — trend_signal audit script and GUI wiring."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ShadBotTrader.presentation.commands import Command, CommandKind, CommandResult, CommandStatus
from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers, descriptor_for

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_trend_signal_5m.py"


def load_script():
    spec = importlib.util.spec_from_file_location("evaluate_trend_signal_5m", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_exposes_phase107_metrics_helpers():
    module = load_script()

    metrics = module.classification_metrics([0, 1, 2, 2], [0, 2, 2, 1])

    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 0, 1], [0, 1, 1]]
    assert metrics["per_class"]["buy"]["support"] == 2
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert 0.0 <= metrics["balanced_accuracy"] <= 1.0


def test_average_precision_is_reported_without_sklearn():
    module = load_script()

    ap = module.average_precision([0, 2, 2, 1], [0.1, 0.9, 0.8, 0.7], positive=2)

    assert ap == 1.0


def test_model_scoring_refuses_window_mismatch_before_predicting():
    module = load_script()

    reason = module.model_input_mismatch((None, 150, 179), window_size=288, feature_count=179)

    assert "window=150" in reason
    assert "window=288" in reason


def test_model_scoring_refuses_feature_mismatch_before_predicting():
    module = load_script()

    reason = module.model_input_mismatch((None, 288, 177), window_size=288, feature_count=179)

    assert "177 features" in reason
    assert "179" in reason


def test_audit_command_has_gui_fields():
    fields = {field.name for field in descriptor_for(CommandKind.AUDIT_TREND_SIGNAL).fields}

    assert {
        "symbol",
        "dataset",
        "window",
        "label_horizon",
        "atr_mult",
        "folds",
        "val_size",
        "model_id",
        "max_windows",
    } <= fields


def test_audit_command_passes_expected_script_args(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
        lambda root: ["5M", "1D"],
    )
    handler = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path / "datasets")
    captured = {}

    def fake_run_script(command, arguments, success_message, started, **kwargs):
        captured["args"] = list(arguments)
        captured["timeout"] = kwargs.get("timeout")
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(handler, "_run_script", fake_run_script)

    result = handler.audit_trend_signal(
        Command(
            CommandKind.AUDIT_TREND_SIGNAL,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "window": "288",
                "label_horizon": "288",
                "atr_mult": "0.5",
                "folds": "3",
                "val_size": "400",
                "model_id": "gold_trend_signal_5m",
                "max_windows": "1234",
                "timeout_minutes": "15",
            },
        )
    )

    args = captured["args"]
    assert result.status is CommandStatus.SUCCEEDED
    assert args[0] == "scripts/evaluate_trend_signal_5m.py"
    assert args[args.index("--timeframe") + 1] == "5M"
    assert args[args.index("--window") + 1] == "288"
    assert args[args.index("--label-horizon") + 1] == "288"
    assert args[args.index("--atr-mult") + 1] == "0.5"
    assert args[args.index("--val-size") + 1] == "400"
    assert args[args.index("--model-id") + 1] == "gold_trend_signal_5m"
    assert captured["timeout"] == 15 * 60
