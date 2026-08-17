"""Plugin lifecycle manager and deterministic discovery (Phase 9, §13-14, 19).

The manager owns *operational state*: it validates, loads, initialises,
starts and stops plugins, and records why any of that failed.

Two rules shape it:

**A failed plugin must expose its reason** (§18). Swallowing the cause
turns a five-second fix into an afternoon of guessing, so every failure
is stored on the record and surfaced in the status report.

**Discovery is deterministic** (§14). The manager never scans a folder
and imports whatever it finds — that is arbitrary code execution. It
loads only what was explicitly configured or declared as an entry point.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, Dict, List, Optional, Sequence

from ShadBotTrader.core.errors import PluginError
from ShadBotTrader.core.plugins.plugin import Plugin, PluginMetadata
from ShadBotTrader.core.plugins.registry import (
    _ALLOWED,
    PluginRecord,
    PluginRegistry,
    PluginState,
)

#: Entry-point group external packages advertise plugins under.
ENTRY_POINT_GROUP = "shadbottrader.plugins"


class PluginManager:
    """Drives plugins through their lifecycle (Phase 9, §13)."""

    def __init__(self, registry: Optional[PluginRegistry] = None) -> None:
        self._registry = registry or PluginRegistry()
        self._events: List[Dict[str, Any]] = []

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def events(self) -> List[Dict[str, Any]]:
        """Every transition, for auditing a startup that went wrong."""
        return list(self._events)

    # -------------------------------------------------------- discovery --
    def discover_builtin(
        self,
        metadata: PluginMetadata,
        factory: Callable[[], Plugin],
        priority: int = 100,
        dependencies: Optional[Sequence[str]] = None,
    ) -> PluginRecord:
        """Register a plugin compiled into the platform."""
        record = self._registry.register(
            metadata, factory, priority, dependencies, source="builtin"
        )
        self._log("discovered", record)
        return record

    def discover_configured(self, entries: Sequence[Dict[str, Any]]) -> List[PluginRecord]:
        """Load plugins named explicitly in configuration.

        Each entry needs ``module`` and ``factory``; nothing is imported
        that the configuration did not name.
        """
        discovered: List[PluginRecord] = []
        for entry in entries:
            name = str(entry.get("name", "")).strip()
            module_path = str(entry.get("module", "")).strip()
            factory_name = str(entry.get("factory", "")).strip()

            if not module_path or not factory_name:
                raise PluginError(f"Plugin entry '{name or '?'}' needs both 'module' and 'factory'")

            try:
                module = importlib.import_module(module_path)
                factory = getattr(module, factory_name)
            except (ImportError, AttributeError) as error:
                # Record the failure instead of aborting the whole startup:
                # one broken plugin must not take the platform down.
                metadata = PluginMetadata(
                    name=name or module_path,
                    version=str(entry.get("version", "0.0.0")),
                    description=str(entry.get("description", "")),
                )
                record = self._registry.register(
                    metadata, lambda: None, source="configured"  # type: ignore[arg-type,return-value]
                )
                self._fail(record, f"cannot import {module_path}.{factory_name}: {error}")
                discovered.append(record)
                continue

            metadata = PluginMetadata(
                name=name or getattr(factory, "__name__", module_path),
                version=str(entry.get("version", "1.0.0")),
                description=str(entry.get("description", "")),
                api_version=str(entry.get("api_version", "1.0")),
            )
            record = self._registry.register(
                metadata,
                factory,
                priority=int(entry.get("priority", 100)),
                dependencies=entry.get("dependencies", []),
                source="configured",
            )
            self._log("discovered", record)
            discovered.append(record)
        return discovered

    def discover_entry_points(self, group: str = ENTRY_POINT_GROUP) -> List[PluginRecord]:
        """Load plugins advertised by installed packages (§16).

        Entry points are declarative: a package states what it provides
        in its own metadata, so nothing unexpected is imported.
        """
        from importlib.metadata import entry_points

        discovered: List[PluginRecord] = []
        try:
            found = entry_points(group=group)
        except TypeError:  # pragma: no cover - very old importlib
            found = entry_points().get(group, [])  # type: ignore[attr-defined]

        for entry in found:
            try:
                factory = entry.load()
            except Exception as error:  # a bad package must not stop startup
                metadata = PluginMetadata(name=entry.name, version="0.0.0")
                record = self._registry.register(
                    metadata, lambda: None, source="entry_point"  # type: ignore[arg-type,return-value]
                )
                self._fail(record, f"entry point failed to load: {error}")
                discovered.append(record)
                continue

            metadata = PluginMetadata(
                name=entry.name,
                version=getattr(factory, "plugin_version", "1.0.0"),
                api_version=getattr(factory, "api_version", "1.0"),
            )
            record = self._registry.register(metadata, factory, source="entry_point")
            self._log("discovered", record)
            discovered.append(record)
        return discovered

    # -------------------------------------------------------- lifecycle --
    def validate(self, name: str) -> bool:
        """Check a plugin and move it to VALIDATED or FAILED."""
        record = self._registry.resolve(name)
        problems = self._registry.validate(name)
        if problems:
            self._fail(record, "; ".join(problems))
            return False
        self._transition(record, PluginState.VALIDATED)
        return True

    def load(self, name: str) -> bool:
        """Instantiate the plugin."""
        record = self._registry.resolve(name)
        if record.state is PluginState.DISCOVERED and not self.validate(name):
            return False
        if record.has_failed:
            return False

        try:
            instance = record.factory()
        except Exception as error:
            self._fail(record, f"factory raised: {type(error).__name__}: {error}")
            return False

        if not isinstance(instance, Plugin):
            self._fail(
                record,
                f"factory returned {type(instance).__name__}, not a Plugin subclass",
            )
            return False

        record.instance = instance
        self._transition(record, PluginState.LOADED)
        return True

    def initialize(self, name: str) -> bool:
        record = self._registry.resolve(name)
        if record.state is PluginState.DISCOVERED or record.state is PluginState.VALIDATED:
            if not self.load(name):
                return False
        if record.has_failed or record.instance is None:
            return False

        try:
            initialise = getattr(record.instance, "initialize", None)
            if callable(initialise):
                initialise()
        except Exception as error:
            self._fail(record, f"initialize failed: {error}")
            return False

        self._transition(record, PluginState.INITIALIZED)
        return True

    def start(self, name: str) -> bool:
        record = self._registry.resolve(name)
        if record.state in (
            PluginState.DISCOVERED,
            PluginState.VALIDATED,
            PluginState.LOADED,
        ) and not self.initialize(name):
            return False
        if record.has_failed or record.instance is None:
            return False

        try:
            starter = getattr(record.instance, "start", None)
            if callable(starter):
                starter()
        except Exception as error:
            self._fail(record, f"start failed: {error}")
            return False

        self._transition(record, PluginState.STARTED)
        self._transition(record, PluginState.ACTIVE)
        return True

    def stop(self, name: str) -> bool:
        record = self._registry.resolve(name)
        if not record.state.is_running:
            return True  # already stopped: not an error

        self._transition(record, PluginState.STOPPING)
        try:
            stopper = getattr(record.instance, "stop", None)
            if callable(stopper):
                stopper()
        except Exception as error:
            self._fail(record, f"stop failed: {error}")
            return False

        self._transition(record, PluginState.STOPPED)
        return True

    def unload(self, name: str) -> bool:
        """Stop the plugin and drop its instance."""
        if not self.stop(name):
            return False
        record = self._registry.resolve(name)
        record.instance = None
        return True

    # ------------------------------------------------------------- bulk --
    def start_all(self) -> Dict[str, bool]:
        """Start every plugin in dependency order (§26).

        A plugin whose dependency failed is not started: running it would
        mean running against something that is not there.
        """
        results: Dict[str, bool] = {}
        for record in self._registry.load_order():
            unmet = [
                dependency
                for dependency in record.dependencies
                if not results.get(dependency, False)
            ]
            if unmet:
                self._fail(record, f"dependency not running: {', '.join(unmet)}")
                results[record.name] = False
                continue
            results[record.name] = self.start(record.name)
        return results

    def stop_all(self) -> Dict[str, bool]:
        """Stop everything in reverse dependency order."""
        results: Dict[str, bool] = {}
        for record in reversed(self._registry.load_order()):
            results[record.name] = self.stop(record.name)
        return results

    # ----------------------------------------------------------- health --
    def health(self) -> Dict[str, Any]:
        """Operational state of every plugin (§13)."""
        records = self._registry.list_all()
        return {
            "total": len(records),
            "active": sum(1 for record in records if record.state.is_running),
            "failed": sum(1 for record in records if record.has_failed),
            "plugins": [record.to_dict() for record in records],
            "failures": {
                record.name: record.failure_reason for record in records if record.has_failed
            },
        }

    # -------------------------------------------------------- internals --
    def _transition(self, record: PluginRecord, target: PluginState) -> None:
        allowed = _ALLOWED.get(record.state, ())
        if target not in allowed:
            raise PluginError(
                f"Plugin '{record.name}' cannot go from {record.state.value} " f"to {target.value}"
            )
        record.state = target
        self._log(target.value, record)

    def _fail(self, record: PluginRecord, reason: str) -> None:
        """Mark a plugin failed, keeping the reason (§18)."""
        record.state = PluginState.FAILED
        record.failure_reason = reason
        self._log("failed", record, reason)

    def _log(self, event: str, record: PluginRecord, detail: str = "") -> None:
        self._events.append({"event": event, "plugin": record.name, "detail": detail})
