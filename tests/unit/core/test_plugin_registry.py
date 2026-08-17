"""Tests for the plugin registry and manager (Phase 9).

The registry answers "what is registered"; the manager answers "what is
running". Most of these tests are about the failure paths, because a
plugin system that only works when every plugin is well-behaved is not a
plugin system.
"""

import pytest

from ShadBotTrader.core.errors import PluginError
from ShadBotTrader.core.plugins import (
    Plugin,
    PluginManager,
    PluginMetadata,
    PluginRegistry,
    PluginState,
)


class Demo(Plugin):
    """A plugin that records what happened to it."""

    def __init__(self, name: str = "demo", fail_on: str = "") -> None:
        super().__init__(PluginMetadata(name=name, version="1.0.0"))
        self.calls: list[str] = []
        self._fail_on = fail_on

    def initialize(self) -> None:
        self.calls.append("initialize")
        if self._fail_on == "initialize":
            raise RuntimeError("initialize exploded")

    def start(self) -> None:
        self.calls.append("start")
        if self._fail_on == "start":
            raise RuntimeError("start exploded")

    def stop(self) -> None:
        self.calls.append("stop")
        if self._fail_on == "stop":
            raise RuntimeError("stop exploded")


def meta(name: str, api_version: str = "1.0") -> PluginMetadata:
    return PluginMetadata(name=name, version="1.0.0", api_version=api_version)


# ------------------------------------------------------------- registry ---
class TestRegistry:
    def test_a_plugin_can_be_registered_and_resolved(self):
        registry = PluginRegistry()
        registry.register(meta("data"), lambda: Demo("data"))

        assert registry.has("data")
        assert registry.resolve("data").name == "data"
        assert len(registry) == 1

    def test_duplicate_names_are_refused(self):
        """Two plugins with one id makes resolve() ambiguous."""
        registry = PluginRegistry()
        registry.register(meta("data"), lambda: Demo("data"))

        with pytest.raises(PluginError, match="already registered"):
            registry.register(meta("data"), lambda: Demo("data"))

    def test_resolving_an_unknown_plugin_lists_what_exists(self):
        registry = PluginRegistry()
        registry.register(meta("data"), lambda: Demo("data"))

        with pytest.raises(PluginError) as error:
            registry.resolve("nope")
        assert "data" in str(error.value)

    def test_a_running_plugin_cannot_be_unregistered(self):
        manager = PluginManager()
        manager.discover_builtin(meta("data"), lambda: Demo("data"))
        manager.start("data")

        with pytest.raises(PluginError, match="stop it before"):
            manager.registry.unregister("data")

    def test_a_stopped_plugin_can_be_unregistered(self):
        manager = PluginManager()
        manager.discover_builtin(meta("data"), lambda: Demo("data"))
        manager.start("data")
        manager.stop("data")

        manager.registry.unregister("data")
        assert not manager.registry.has("data")

    def test_an_incompatible_api_version_is_reported(self):
        registry = PluginRegistry()
        registry.register(meta("old", api_version="2.0"), lambda: Demo("old"))

        problems = registry.validate("old")

        assert any("incompatible" in problem for problem in problems)

    def test_a_missing_dependency_is_reported(self):
        registry = PluginRegistry()
        registry.register(meta("ai"), lambda: Demo("ai"), dependencies=["data"])

        assert any("missing dependency" in p for p in registry.validate("ai"))

    def test_plugins_are_listed_by_priority_then_name(self):
        registry = PluginRegistry()
        registry.register(meta("z"), lambda: Demo("z"), priority=10)
        registry.register(meta("a"), lambda: Demo("a"), priority=50)

        assert [record.name for record in registry.find()] == ["z", "a"]


# --------------------------------------------------------- dependencies ---
class TestDependencies:
    def test_dependencies_load_before_dependents(self):
        registry = PluginRegistry()
        registry.register(meta("ui"), lambda: Demo("ui"), dependencies=["ai"])
        registry.register(meta("ai"), lambda: Demo("ai"), dependencies=["data"])
        registry.register(meta("data"), lambda: Demo("data"))

        order = [record.name for record in registry.load_order()]

        assert order.index("data") < order.index("ai") < order.index("ui")

    def test_a_cycle_is_detected(self):
        registry = PluginRegistry()
        registry.register(meta("a"), lambda: Demo("a"), dependencies=["b"])
        registry.register(meta("b"), lambda: Demo("b"), dependencies=["a"])

        cycle = registry.detect_cycle()

        assert cycle and cycle[0] == cycle[-1]

    def test_load_order_refuses_a_cycle(self):
        """A partial order would start plugins whose deps are missing."""
        registry = PluginRegistry()
        registry.register(meta("a"), lambda: Demo("a"), dependencies=["b"])
        registry.register(meta("b"), lambda: Demo("b"), dependencies=["a"])

        with pytest.raises(PluginError, match="Circular"):
            registry.load_order()

    def test_no_cycle_reports_empty(self):
        registry = PluginRegistry()
        registry.register(meta("a"), lambda: Demo("a"))
        registry.register(meta("b"), lambda: Demo("b"), dependencies=["a"])

        assert registry.detect_cycle() == []

    def test_validate_all_surfaces_every_problem_at_once(self):
        registry = PluginRegistry()
        registry.register(meta("bad_api", api_version="9.0"), lambda: Demo("bad_api"))
        registry.register(meta("orphan"), lambda: Demo("orphan"), dependencies=["ghost"])

        report = registry.validate_all()

        assert "bad_api" in report and "orphan" in report


# -------------------------------------------------------------- manager ---
class TestManager:
    def test_the_full_lifecycle_runs_in_order(self):
        manager = PluginManager()
        instance = Demo("data")
        manager.discover_builtin(meta("data"), lambda: instance)

        assert manager.start("data")

        record = manager.registry.resolve("data")
        assert record.state is PluginState.ACTIVE
        assert instance.calls == ["initialize", "start"]

    def test_stopping_moves_through_stopping_to_stopped(self):
        manager = PluginManager()
        instance = Demo("data")
        manager.discover_builtin(meta("data"), lambda: instance)
        manager.start("data")

        assert manager.stop("data")
        assert manager.registry.resolve("data").state is PluginState.STOPPED
        assert instance.calls[-1] == "stop"

    def test_stopping_something_already_stopped_is_not_an_error(self):
        manager = PluginManager()
        manager.discover_builtin(meta("data"), lambda: Demo("data"))

        assert manager.stop("data") is True

    def test_a_failing_factory_records_the_reason(self):
        """§18: a failed plugin must expose why."""

        def explode():
            raise RuntimeError("no database")

        manager = PluginManager()
        manager.discover_builtin(meta("broken"), explode)

        assert not manager.start("broken")
        record = manager.registry.resolve("broken")
        assert record.state is PluginState.FAILED
        assert "no database" in record.failure_reason

    def test_a_factory_returning_the_wrong_type_fails_clearly(self):
        manager = PluginManager()
        manager.discover_builtin(meta("wrong"), lambda: "not a plugin")

        assert not manager.load("wrong")
        assert "not a Plugin" in manager.registry.resolve("wrong").failure_reason

    def test_a_failure_during_start_is_captured(self):
        manager = PluginManager()
        manager.discover_builtin(meta("bad"), lambda: Demo("bad", fail_on="start"))

        assert not manager.start("bad")
        assert "start failed" in manager.registry.resolve("bad").failure_reason

    def test_an_incompatible_plugin_never_loads(self):
        manager = PluginManager()
        manager.discover_builtin(meta("old", api_version="2.0"), lambda: Demo("old"))

        assert not manager.start("old")
        assert manager.registry.resolve("old").state is PluginState.FAILED

    def test_start_all_respects_dependency_order(self):
        started: list[str] = []

        def make(name):
            def factory():
                plugin = Demo(name)
                original = plugin.start

                def tracked():
                    started.append(name)
                    original()

                plugin.start = tracked  # type: ignore[method-assign]
                return plugin

            return factory

        manager = PluginManager()
        manager.discover_builtin(meta("ui"), make("ui"), dependencies=["ai"])
        manager.discover_builtin(meta("ai"), make("ai"), dependencies=["data"])
        manager.discover_builtin(meta("data"), make("data"))

        results = manager.start_all()

        assert all(results.values())
        assert started == ["data", "ai", "ui"]

    def test_a_dependent_is_not_started_when_its_dependency_failed(self):
        """Running against something that is not there is worse than not running."""

        def explode():
            raise RuntimeError("down")

        manager = PluginManager()
        manager.discover_builtin(meta("data"), explode)
        manager.discover_builtin(meta("ai"), lambda: Demo("ai"), dependencies=["data"])

        results = manager.start_all()

        assert results == {"data": False, "ai": False}
        assert "dependency not running" in manager.registry.resolve("ai").failure_reason

    def test_stop_all_reverses_the_order(self):
        stopped: list[str] = []

        def make(name):
            def factory():
                plugin = Demo(name)
                plugin.stop = lambda: stopped.append(name)  # type: ignore[method-assign]
                return plugin

            return factory

        manager = PluginManager()
        manager.discover_builtin(meta("data"), make("data"))
        manager.discover_builtin(meta("ai"), make("ai"), dependencies=["data"])
        manager.start_all()

        manager.stop_all()

        assert stopped == ["ai", "data"]

    def test_health_summarises_the_operational_state(self):
        manager = PluginManager()
        manager.discover_builtin(meta("good"), lambda: Demo("good"))
        manager.discover_builtin(meta("bad"), lambda: Demo("bad", fail_on="start"))
        manager.start_all()

        health = manager.health()

        assert health["total"] == 2
        assert health["active"] == 1
        assert health["failed"] == 1
        assert "bad" in health["failures"]

    def test_transitions_are_recorded_for_auditing(self):
        manager = PluginManager()
        manager.discover_builtin(meta("data"), lambda: Demo("data"))
        manager.start("data")

        events = [event["event"] for event in manager.events]

        assert "discovered" in events
        assert "active" in events


# ------------------------------------------------------------ discovery ---
class TestDiscovery:
    def test_a_configured_plugin_is_imported_by_name(self):
        manager = PluginManager()

        records = manager.discover_configured(
            [
                {
                    "name": "counter",
                    "module": "collections",
                    "factory": "Counter",
                    "version": "1.0.0",
                }
            ]
        )

        assert len(records) == 1
        assert manager.registry.has("counter")

    def test_an_unimportable_plugin_fails_without_stopping_startup(self):
        """One broken plugin must not take the platform down."""
        manager = PluginManager()

        records = manager.discover_configured(
            [{"name": "ghost", "module": "no.such.module", "factory": "build"}]
        )

        assert records[0].state is PluginState.FAILED
        assert "cannot import" in records[0].failure_reason

    def test_an_entry_missing_its_module_is_refused(self):
        manager = PluginManager()

        with pytest.raises(PluginError, match="module"):
            manager.discover_configured([{"name": "half"}])

    def test_entry_point_discovery_does_not_crash_without_plugins(self):
        """Deterministic discovery: nothing installed means nothing loaded."""
        manager = PluginManager()

        assert manager.discover_entry_points("shadbottrader.nonexistent") == []
