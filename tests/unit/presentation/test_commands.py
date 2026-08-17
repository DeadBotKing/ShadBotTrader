"""Tests for the command layer (Phase 19, sections 11-13).

Commands are the GUI's way of asking for work. What matters:

* the surface is a closed, reviewable set
* a handler failure never crashes the server
* only one command runs at a time
* the GUI still performs none of the work itself
"""

import threading
import time

import pytest

from ShadBotTrader.presentation.commands import (
    Command,
    CommandBus,
    CommandKind,
    CommandResult,
    CommandStatus,
    descriptor_for,
    descriptors,
)


# ------------------------------------------------------------- commands ----
class TestCommandDefinitions:
    def test_every_kind_has_a_descriptor(self):
        """The UI must be able to render every command it can dispatch."""
        described = {item.kind for item in descriptors()}
        assert described == set(CommandKind)

    def test_descriptors_carry_help_text(self):
        for descriptor in descriptors():
            assert descriptor.label
            assert len(descriptor.description) > 20, descriptor.kind

    def test_the_requested_operations_exist(self):
        """The buttons the user asked for."""
        actions = {item.action for item in descriptors()}
        assert "fetch_market_data" in actions  # real MT5 data
        assert "compute_features" in actions  # update features
        assert "train_model" in actions  # retrain the AI
        assert "run_backtest" in actions
        assert "run_optimisation" in actions

    def test_parameter_coercion_is_forgiving(self):
        command = Command(
            CommandKind.RUN_BACKTEST,
            {"bars": "500", "capital": "12.5", "flag": "true", "junk": "abc"},
        )
        assert command.integer("bars") == 500
        assert command.number("capital") == 12.5
        assert command.flag("flag") is True
        assert command.integer("junk", 7) == 7  # bad input falls back
        assert command.integer("missing", 3) == 3

    def test_descriptor_lookup(self):
        assert descriptor_for(CommandKind.TRAIN_MODEL).label == "Retrain the model"
        with pytest.raises(KeyError):
            descriptor_for("nope")  # type: ignore[arg-type]


class TestCommandResult:
    def test_success_and_failure_tones(self):
        assert CommandResult.success(CommandKind.RUN_BACKTEST, "ok").tone == "positive"
        assert CommandResult.failure(CommandKind.RUN_BACKTEST, "bad").tone == "negative"
        assert CommandResult.rejected(CommandKind.RUN_BACKTEST, "no").tone == "negative"

    def test_rejected_is_not_a_failure_of_the_system(self):
        """A precondition that is not met is not a crash."""
        result = CommandResult.rejected(CommandKind.TRAIN_MODEL, "TensorFlow missing")
        assert result.status is CommandStatus.REJECTED
        assert not result.succeeded

    def test_to_dict_is_serialisable(self):
        import json

        payload = CommandResult.success(
            CommandKind.RUN_BACKTEST, "done", ["a", "b"], 1.25
        ).to_dict()
        assert json.dumps(payload)
        assert payload["duration_seconds"] == 1.25


# ------------------------------------------------------------------ bus ----
class TestCommandBus:
    def test_dispatch_calls_the_handler(self):
        seen = []

        def handler(command: Command) -> CommandResult:
            seen.append(command)
            return CommandResult.success(command.kind, "ran")

        bus = CommandBus({CommandKind.RUN_BACKTEST: handler})
        result = bus.dispatch(Command(CommandKind.RUN_BACKTEST))

        assert result.succeeded
        assert len(seen) == 1

    def test_unknown_command_is_rejected_not_crashed(self):
        bus = CommandBus({})
        result = bus.dispatch(Command(CommandKind.TRAIN_MODEL))
        assert result.status is CommandStatus.REJECTED
        assert "No handler" in result.message

    def test_a_raising_handler_becomes_a_failure(self):
        """A broken handler must never take the server down."""

        def handler(command: Command) -> CommandResult:
            raise RuntimeError("boom")

        bus = CommandBus({CommandKind.RUN_BACKTEST: handler})
        result = bus.dispatch(Command(CommandKind.RUN_BACKTEST))

        assert result.status is CommandStatus.FAILED
        assert "RuntimeError" in result.message
        assert "boom" in result.detail

    def test_history_is_recorded_newest_first(self):
        bus = CommandBus(
            {
                CommandKind.RUN_BACKTEST: lambda c: CommandResult.success(c.kind, "1"),
                CommandKind.RUN_OPTIMISATION: lambda c: CommandResult.success(c.kind, "2"),
            }
        )
        bus.dispatch(Command(CommandKind.RUN_BACKTEST))
        bus.dispatch(Command(CommandKind.RUN_OPTIMISATION))

        history = bus.history()
        assert len(history) == 2
        assert history[0].kind is CommandKind.RUN_OPTIMISATION

    def test_only_one_command_runs_at_a_time(self):
        """Two concurrent ingests writing one dataset would race."""
        release = threading.Event()

        def slow(command: Command) -> CommandResult:
            release.wait(timeout=5)
            return CommandResult.success(command.kind, "slow done")

        bus = CommandBus(
            {
                CommandKind.RUN_BACKTEST: slow,
                CommandKind.TRAIN_MODEL: lambda c: CommandResult.success(c.kind, "fast"),
            }
        )
        bus.dispatch_async(Command(CommandKind.RUN_BACKTEST))
        time.sleep(0.2)

        assert bus.is_busy
        blocked = bus.dispatch(Command(CommandKind.TRAIN_MODEL))
        assert blocked.status is CommandStatus.REJECTED
        assert "still running" in blocked.message

        release.set()
        bus.wait(5)
        assert not bus.is_busy

    def test_async_dispatch_returns_immediately(self):
        def slow(command: Command) -> CommandResult:
            time.sleep(0.3)
            return CommandResult.success(command.kind, "done")

        bus = CommandBus({CommandKind.RUN_BACKTEST: slow})
        started = time.monotonic()
        result = bus.dispatch_async(Command(CommandKind.RUN_BACKTEST))
        elapsed = time.monotonic() - started

        assert result.status is CommandStatus.RUNNING
        assert elapsed < 0.2  # did not block
        bus.wait(5)
        assert bus.last_result() is not None
        assert bus.last_result().succeeded

    def test_bus_clears_running_state_after_a_failure(self):
        def handler(command: Command) -> CommandResult:
            raise ValueError("bad")

        bus = CommandBus({CommandKind.RUN_BACKTEST: handler})
        bus.dispatch(Command(CommandKind.RUN_BACKTEST))
        assert not bus.is_busy  # not stuck


# ------------------------------------------- the architectural boundary ----
class TestHandlerBoundary:
    def test_handlers_delegate_and_do_not_calculate(self):
        """Phase 19 §4: no trading, AI or risk maths inside the GUI layer.

        A handler should call an application service. Arithmetic on
        prices or PnL inside the presentation layer would mean the logic
        has leaked out of the domain.
        """
        import ast
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "ShadBotTrader"
            / "presentation"
            / "commands"
            / "handlers.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))

        # No handler may define a maths-heavy helper of its own.
        forbidden_names = {
            "calculate_pnl",
            "compute_signal",
            "evaluate_risk",
            "_pnl",
            "_signal",
        }
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not (defined & forbidden_names)

    def test_command_kinds_are_a_closed_set(self):
        """The GUI cannot invent an operation."""
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        registry = CommandHandlers("test.db").registry()
        assert set(registry) <= set(CommandKind)
        # and every advertised command really has a handler
        assert {item.kind for item in descriptors()} <= set(registry)

    def test_every_handler_returns_a_result_object(self):
        """Handlers report outcomes; they do not raise at the caller."""
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        handlers = CommandHandlers("nonexistent.db", "nonexistent_dir")
        bus = CommandBus(handlers.registry())

        # a command whose preconditions cannot hold must still come back
        result = bus.dispatch(
            Command(CommandKind.RUN_BACKTEST, {"symbol": "NOPE", "timeframe": "5M"})
        )
        assert isinstance(result, CommandResult)
        assert result.status in (CommandStatus.REJECTED, CommandStatus.FAILED)


# ------------------------------------------------------- replay command ----
class TestRecordReplayCommand:
    """The button that produces the bar-by-bar player."""

    def test_it_is_offered_with_a_form(self):
        descriptor = descriptor_for(CommandKind.RECORD_REPLAY)
        names = {field.name for field in descriptor.fields}
        assert {"symbol", "timeframe", "capital", "spread"} <= names

    def test_it_refuses_politely_when_there_are_no_candles(self, tmp_path):
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        handlers = CommandHandlers(tmp_path / "x.db", tmp_path / "empty", tmp_path / "replay.html")
        result = handlers.record_replay(
            Command(CommandKind.RECORD_REPLAY, {"symbol": "NOPE", "timeframe": "5M"})
        )

        assert result.status is CommandStatus.REJECTED
        assert "Fetch data first" in result.message
        assert not (tmp_path / "replay.html").exists()

    def test_it_writes_a_player_for_stored_candles(self, tmp_path):
        from ShadBotTrader.data_cli import build_service, generate_sample
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        storage = tmp_path / "datasets"
        sample = storage / "samples" / "XAUUSD_i_5M.csv"
        generate_sample("XAUUSD_i", "5M", 120, sample)
        service, _, _ = build_service(storage)
        service.ingest("XAUUSD_i", "5M", str(sample))

        out = tmp_path / "player.html"
        handlers = CommandHandlers(tmp_path / "x.db", storage, out)
        result = handlers.record_replay(
            Command(CommandKind.RECORD_REPLAY, {"symbol": "XAUUSD_i", "timeframe": "5M"})
        )

        assert result.status is CommandStatus.SUCCEEDED, result.detail
        assert out.exists()
        markup = out.read_text(encoding="utf-8")
        assert "Backtest replay" in markup
        assert "const TAPE" in markup


# ------------------------------------------------ compute-features button ---
class TestComputeFeaturesCommand:
    """Regression: the button called a method that never existed.

    ``FeatureComputationService`` exposes ``compute_set(...)``, not
    ``compute(symbol, timeframe)``. The handler called the latter, so
    "Update features" failed for every user who pressed it. The original
    tests only exercised the "no candles stored" branch, which returns
    before reaching the broken call — that is why it stayed hidden.
    """

    def _dataset(self, tmp_path):
        from ShadBotTrader.data_cli import build_service, generate_sample

        storage = tmp_path / "datasets"
        sample = storage / "samples" / "XAUUSD_i_5M.csv"
        generate_sample("XAUUSD_i", "5M", 150, sample)
        service, _, _ = build_service(storage)
        service.ingest("XAUUSD_i", "5M", str(sample))
        return storage

    def test_it_actually_computes_the_standard_feature_set(self, tmp_path):
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        storage = self._dataset(tmp_path)
        handlers = CommandHandlers(tmp_path / "f.db", storage, tmp_path / "r.html")

        result = handlers.compute_features(
            Command(CommandKind.COMPUTE_FEATURES, {"symbol": "XAUUSD_i", "timeframe": "5M"})
        )

        assert result.status is CommandStatus.SUCCEEDED, result.detail
        assert "109" in result.message
        assert any("feature set" in line for line in result.lines)

    def test_the_definitions_reach_the_database(self, tmp_path):
        from ShadBotTrader.infrastructure.persistence import Database
        from ShadBotTrader.presentation.commands.handlers import CommandHandlers

        storage = self._dataset(tmp_path)
        database_path = tmp_path / "f.db"
        handlers = CommandHandlers(database_path, storage, tmp_path / "r.html")

        handlers.compute_features(
            Command(CommandKind.COMPUTE_FEATURES, {"symbol": "XAUUSD_i", "timeframe": "5M"})
        )

        database = Database(database_path)
        stored = database.row_count("feature_definition")
        database.close()
        assert stored == 109

    def test_the_service_contract_the_handler_relies_on_exists(self):
        """Guards the exact mismatch that caused the bug."""
        from ShadBotTrader.application.services.feature_computation_service import (
            FeatureComputationService,
        )

        assert hasattr(FeatureComputationService, "compute_set")
        assert not hasattr(FeatureComputationService, "compute")
