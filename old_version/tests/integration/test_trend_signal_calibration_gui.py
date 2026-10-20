"""Phase 109 — GUI wiring for trend_signal threshold calibration."""

from __future__ import annotations

from ShadBotTrader.presentation.commands import Command, CommandKind, CommandResult, CommandStatus
from ShadBotTrader.presentation.commands.handlers import AccountCommandHandlers, descriptor_for


def test_calibration_command_has_gui_fields():
    fields = {field.name for field in descriptor_for(CommandKind.CALIBRATE_TREND_SIGNAL).fields}

    assert {
        "symbol",
        "dataset",
        "model_id",
        "window",
        "label_horizon",
        "atr_mult",
        "train_ratio",
        "scope",
        "threshold_min",
        "threshold_max",
        "threshold_step",
        "min_margin",
        "min_trades",
        "precision_floor",
        "max_windows",
        "save_record",
    } <= fields


def test_calibration_command_passes_expected_script_args(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
        lambda root: ["5M"],
    )
    handler = AccountCommandHandlers(tmp_path / "db.sqlite", tmp_path / "datasets")
    captured = {}

    def fake_run_script(command, arguments, success_message, started, **kwargs):
        captured["args"] = list(arguments)
        captured["timeout"] = kwargs.get("timeout")
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(handler, "_run_script", fake_run_script)

    result = handler.calibrate_trend_signal(
        Command(
            CommandKind.CALIBRATE_TREND_SIGNAL,
            {
                "symbol": "XAUUSD",
                "dataset": "5M",
                "model_id": "gold_trend_signal_5m",
                "window": "288",
                "label_horizon": "288",
                "atr_mult": "0.5",
                "train_ratio": "80",
                "scope": "holdout",
                "threshold_min": "0.4",
                "threshold_max": "0.9",
                "threshold_step": "0.1",
                "min_margin": "0.05",
                "min_trades": "25",
                "precision_floor": "0.45",
                "max_windows": "777",
                "save_record": "1",
                "timeout_minutes": "20",
            },
        )
    )

    args = captured["args"]
    assert result.status is CommandStatus.SUCCEEDED
    assert args[0] == "scripts/calibrate_trend_signal_thresholds.py"
    assert args[args.index("--scope") + 1] == "holdout"
    assert args[args.index("--threshold-min") + 1] == "0.4"
    assert args[args.index("--threshold-step") + 1] == "0.1"
    assert args[args.index("--precision-floor") + 1] == "0.45"
    assert args[args.index("--save-record") + 1] == "1"
    assert captured["timeout"] == 20 * 60
