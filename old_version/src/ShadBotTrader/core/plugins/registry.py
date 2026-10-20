"""Plugin registry, states and lifecycle manager (Phase 9, §12-14, 18-27).

The phase document draws a line the implementation must keep:

    PluginRegistry answers  "what plugins are registered?"
    PluginManager  answers  "what is their operational state?"

Two separate concerns, two separate objects. Merging them produces a
class that both owns a catalogue and mutates lifecycle, and neither
question can then be answered without side effects.

Discovery is **deterministic** (§14). Arbitrary Python files are never
imported just because they happen to sit in a directory: that is remote
code execution dressed up as a feature. Only explicitly configured
plugins, declared entry points and registered built-ins are loaded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

from ShadBotTrader.core.errors import PluginError
from ShadBotTrader.core.plugins.plugin import Plugin, PluginMetadata

#: API version this host implements. A plugin built against a different
#: major version is refused rather than loaded and hoped for.
HOST_API_VERSION = "1.0"


class PluginState(str, Enum):
    """Lifecycle states from Phase 9 §18, in order."""

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

    @property
    def is_running(self) -> bool:
        return self in (PluginState.STARTED, PluginState.ACTIVE)

    @property
    def is_terminal(self) -> bool:
        return self in (PluginState.STOPPED, PluginState.FAILED)


#: Which transitions the manager permits. A state machine that allows
#: anything is not a state machine.
_ALLOWED: Dict[PluginState, tuple[PluginState, ...]] = {
    PluginState.DISCOVERED: (PluginState.VALIDATED, PluginState.FAILED),
    PluginState.VALIDATED: (PluginState.LOADED, PluginState.FAILED),
    PluginState.LOADED: (PluginState.INITIALIZED, PluginState.FAILED),
    PluginState.INITIALIZED: (PluginState.STARTED, PluginState.FAILED),
    PluginState.STARTED: (PluginState.ACTIVE, PluginState.STOPPING, PluginState.FAILED),
    PluginState.ACTIVE: (PluginState.STOPPING, PluginState.FAILED),
    PluginState.STOPPING: (PluginState.STOPPED, PluginState.FAILED),
    PluginState.STOPPED: (PluginState.INITIALIZED, PluginState.FAILED),
    PluginState.FAILED: (),
}


@dataclass
class PluginRecord:
    """A registered plugin plus everything known about it."""

    metadata: PluginMetadata
    factory: Callable[[], Plugin]
    state: PluginState = PluginState.DISCOVERED
    instance: Optional[Plugin] = None
    failure_reason: str = ""
    priority: int = 100
    dependencies: List[str] = field(default_factory=list)
    source: str = "builtin"

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def has_failed(self) -> bool:
        return self.state is PluginState.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.metadata.version,
            "api_version": self.metadata.api_version,
            "state": self.state.value,
            "priority": self.priority,
            "dependencies": list(self.dependencies),
            "source": self.source,
            "failure_reason": self.failure_reason,
        }


class PluginRegistry:
    """The catalogue of known plugins (Phase 9, §12).

    Pure bookkeeping: it never starts or stops anything. Duplicate names
    are refused, because two plugins answering to one id makes
    ``resolve()`` ambiguous and the ambiguity would surface far from its
    cause.
    """

    def __init__(self) -> None:
        self._records: Dict[str, PluginRecord] = {}

    def register(
        self,
        metadata: PluginMetadata,
        factory: Callable[[], Plugin],
        priority: int = 100,
        dependencies: Optional[Sequence[str]] = None,
        source: str = "builtin",
    ) -> PluginRecord:
        """Add a plugin to the catalogue."""
        if metadata.name in self._records:
            raise PluginError(
                f"A plugin named '{metadata.name}' is already registered. "
                f"Plugin names must be unique."
            )

        record = PluginRecord(
            metadata=metadata,
            factory=factory,
            priority=priority,
            dependencies=list(dependencies or []),
            source=source,
        )
        self._records[metadata.name] = record
        return record

    def unregister(self, name: str) -> None:
        """Remove a plugin. Refuses while it is still running."""
        record = self._records.get(name)
        if record is None:
            raise PluginError(f"No plugin named '{name}' is registered")
        if record.state.is_running:
            raise PluginError(
                f"Plugin '{name}' is {record.state.value}; stop it before unregistering."
            )
        del self._records[name]

    def has(self, name: str) -> bool:
        return name in self._records

    def resolve(self, name: str) -> PluginRecord:
        """Return one plugin, or fail with the list of known names."""
        record = self._records.get(name)
        if record is None:
            known = ", ".join(sorted(self._records)) or "none"
            raise PluginError(f"No plugin named '{name}'. Registered: {known}")
        return record

    def find(self, state: Optional[PluginState] = None) -> List[PluginRecord]:
        """Every plugin, optionally filtered by state, in load order."""
        records = list(self._records.values())
        if state is not None:
            records = [record for record in records if record.state is state]
        return sorted(records, key=lambda item: (item.priority, item.name))

    def list_all(self) -> List[PluginRecord]:
        return self.find()

    @property
    def names(self) -> List[str]:
        return sorted(self._records)

    def __len__(self) -> int:
        return len(self._records)

    # ----------------------------------------------------------- checks --
    def validate(self, name: str) -> List[str]:
        """Problems that would stop this plugin loading. Empty means fine."""
        record = self.resolve(name)
        problems: List[str] = []

        host_major = HOST_API_VERSION.split(".")[0]
        plugin_major = record.metadata.api_version.split(".")[0]
        if plugin_major != host_major:
            problems.append(
                f"api_version {record.metadata.api_version} is incompatible "
                f"with host {HOST_API_VERSION}"
            )

        for dependency in record.dependencies:
            if dependency not in self._records:
                problems.append(f"missing dependency: {dependency}")

        return problems

    def validate_all(self) -> Dict[str, List[str]]:
        """Every plugin's problems, keyed by name (only failures listed)."""
        report: Dict[str, List[str]] = {}
        for name in self._records:
            problems = self.validate(name)
            if problems:
                report[name] = problems

        cycle = self.detect_cycle()
        if cycle:
            joined = " -> ".join(cycle)
            for name in cycle[:-1]:
                report.setdefault(name, []).append(f"circular dependency: {joined}")
        return report

    # ------------------------------------------------------ dependencies --
    def detect_cycle(self) -> List[str]:
        """Return one dependency cycle, or an empty list (§25).

        A cycle is reported rather than raised: the caller usually wants
        to show every problem at once, not stop at the first.
        """
        visiting: set[str] = set()
        done: set[str] = set()
        path: List[str] = []

        def walk(name: str) -> List[str]:
            if name in done or name not in self._records:
                return []
            if name in visiting:
                start = path.index(name)
                return path[start:] + [name]

            visiting.add(name)
            path.append(name)
            for dependency in self._records[name].dependencies:
                cycle = walk(dependency)
                if cycle:
                    return cycle
            path.pop()
            visiting.discard(name)
            done.add(name)
            return []

        for name in sorted(self._records):
            cycle = walk(name)
            if cycle:
                return cycle
        return []

    def load_order(self) -> List[PluginRecord]:
        """Dependencies first, then priority, then name (§26-27).

        Raises on a cycle: an order cannot exist, and returning a
        partial one would start plugins whose dependencies are missing.
        """
        cycle = self.detect_cycle()
        if cycle:
            raise PluginError(f"Circular plugin dependency: {' -> '.join(cycle)}")

        ordered: List[PluginRecord] = []
        placed: set[str] = set()

        def place(name: str) -> None:
            if name in placed or name not in self._records:
                return
            record = self._records[name]
            for dependency in sorted(record.dependencies):
                place(dependency)
            placed.add(name)
            ordered.append(record)

        for record in sorted(self._records.values(), key=lambda item: (item.priority, item.name)):
            place(record.name)
        return ordered
