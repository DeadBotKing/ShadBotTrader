"""فاز ۸۰ — horizon رنج در GUI (Train/Retrain).

سه مسیر داشبورد که run_dual_models.py را اجرا می‌کنند باید
``--horizon`` را برای range پاس بدهند (۱ = پیش‌فرض، پاس نمی‌شود).
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
    monkeypatch.setitem(sys.modules, "tensorflow", types.ModuleType("tensorflow"))
    monkeypatch.setattr(
        "ShadBotTrader.presentation.commands.handlers.stored_dataset_choices",
        lambda root: ["1H"],
    )
    return AccountCommandHandlers(tmp_path / "x.db", tmp_path / "storage")


def _capture(monkeypatch, gui):
    captured = {}

    def fake_run_script(command, arguments, success_message, started, **kwargs):
        captured["args"] = list(arguments)
        return CommandResult(command.kind, CommandStatus.SUCCEEDED, success_message)

    monkeypatch.setattr(gui, "_run_script", fake_run_script)
    return captured


def test_train_descriptor_has_range_horizon():
    fields = {f.name for f in descriptor_for(CommandKind.TRAIN_DUAL_MODELS).fields}
    assert "range_horizon" in fields


def test_retrain_descriptor_has_range_horizon():
    fields = {f.name for f in descriptor_for(CommandKind.TRAIN_MODEL).fields}
    assert "range_horizon" in fields


def test_train_passes_horizon_for_range(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)
    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "range", "dataset": "1H", "range_horizon": "12"},
        )
    )
    args = captured["args"]
    assert args[args.index("--horizon") + 1] == "12"


def test_train_omits_horizon_when_1(gui, monkeypatch):
    captured = _capture(monkeypatch, gui)
    gui.train_dual_models(
        Command(CommandKind.TRAIN_DUAL_MODELS, {"model": "range", "dataset": "1H"})
    )
    assert "--horizon" not in captured["args"]


def test_train_ignores_horizon_for_signal(gui, monkeypatch):
    """horizon برای سیگنال معنا ندارد (first-passage بی‌کران است)."""
    captured = _capture(monkeypatch, gui)
    gui.train_dual_models(
        Command(
            CommandKind.TRAIN_DUAL_MODELS,
            {"model": "signal", "dataset": "1H", "range_horizon": "12"},
        )
    )
    assert "--horizon" not in captured["args"]
