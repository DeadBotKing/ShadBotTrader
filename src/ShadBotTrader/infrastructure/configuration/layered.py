"""Layered configuration with secret protection (Phase 21, §4-5, 18-30).

Configuration arrives from several places and they must combine in a
**deterministic** order (§5):

    1. built-in defaults
    2. base configuration file
    3. environment-specific file
    4. local file            (developer overrides, never committed)
    5. environment variables
    6. runtime overrides     (CLI flags)

Later sources win. Mappings merge key by key; scalars and lists are
replaced outright — a half-merged list is nobody's intent.

**Secrets never appear in output.** §20 requires redaction in logs,
exports, error reports and project snapshots, so redaction lives in the
config object itself rather than at each call site. A rule applied in
one place cannot be forgotten in another.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ShadBotTrader.infrastructure.configuration.configuration import ConfigurationError

#: Marker shown instead of a secret value.
REDACTED = "***REDACTED***"

#: Key fragments that mark a value as secret (§21). Substring matching
#: is deliberate: ``broker_api_key`` and ``api_key`` must both be caught.
SECRET_PATTERNS: Tuple[str, ...] = (
    "secret",
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "auth",
)

#: Prefix for environment variables that feed configuration.
ENV_PREFIX = "SHADBOT_"

#: Officially supported environments (§6).
ENVIRONMENTS: Tuple[str, ...] = ("development", "testing", "staging", "production")


def is_secret_key(key: str) -> bool:
    """True when a key name marks its value as sensitive (§21)."""
    lowered = key.lower()
    return any(pattern in lowered for pattern in SECRET_PATTERNS)


def _coerce(text: str) -> Any:
    """Turn an environment-variable string into a typed value.

    Environment variables are always strings, but ``true`` and ``8080``
    mean a bool and an int. Anything unrecognised stays a string rather
    than being force-parsed into something surprising.
    """
    lowered = text.strip().lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "none", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    if text.startswith(("[", "{")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> Dict[str, Any]:
    """Merge ``overlay`` onto ``base`` (§30).

    Nested mappings merge recursively; every other type is replaced.
    Merging lists element-wise would silently blend two different
    intentions into a third nobody wrote.
    """
    result: Dict[str, Any] = dict(base)
    for key, value in overlay.items():
        existing = result.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            result[key] = deep_merge(existing, value)
        else:
            result[key] = value
    return result


def flatten(values: Mapping[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten a nested mapping into dot-separated keys."""
    flat: Dict[str, Any] = {}
    for key, value in values.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            flat.update(flatten(value, path))
        else:
            flat[path] = value
    return flat


def redact(values: Mapping[str, Any]) -> Dict[str, Any]:
    """A copy with every secret value replaced (§20)."""
    safe: Dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            safe[key] = redact(value)
        elif is_secret_key(key) and value is not None:
            safe[key] = REDACTED
        else:
            safe[key] = value
    return safe


@dataclass(frozen=True)
class SourceRecord:
    """Where one layer of configuration came from — for diagnosis."""

    name: str
    origin: str
    keys: int
    applied: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "origin": self.origin,
            "keys": self.keys,
            "applied": self.applied,
        }


@dataclass
class ValidationRule:
    """One constraint on one key (§23-26)."""

    key: str
    required: bool = False
    expected_type: Optional[type] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    allowed: Optional[Sequence[Any]] = None

    def check(self, present: bool, value: Any) -> Optional[str]:
        """Return a problem description, or None when the value is fine."""
        if not present:
            return f"{self.key}: required but missing" if self.required else None

        if self.expected_type is not None and not isinstance(value, self.expected_type):
            # bool is a subclass of int; treating them as interchangeable
            # turns `debug: true` into `debug: 1` without anyone noticing.
            if not (self.expected_type is float and isinstance(value, int)):
                return (
                    f"{self.key}: expected {self.expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if self.minimum is not None and value < self.minimum:
                return f"{self.key}: {value} is below the minimum {self.minimum}"
            if self.maximum is not None and value > self.maximum:
                return f"{self.key}: {value} is above the maximum {self.maximum}"

        if self.allowed is not None and value not in self.allowed:
            options = ", ".join(str(item) for item in self.allowed)
            return f"{self.key}: {value!r} is not one of [{options}]"

        return None


class LayeredConfiguration:
    """Configuration assembled from ordered sources, with redaction."""

    def __init__(
        self,
        values: Optional[Mapping[str, Any]] = None,
        sources: Optional[Sequence[SourceRecord]] = None,
        environment: str = "development",
    ) -> None:
        self._values: Dict[str, Any] = dict(values or {})
        self._sources: List[SourceRecord] = list(sources or [])
        self._environment = environment

    # ------------------------------------------------------------ access --
    @property
    def environment(self) -> str:
        return self._environment

    @property
    def sources(self) -> List[SourceRecord]:
        return list(self._sources)

    def get(self, path: str, default: Any = None) -> Any:
        """Read a dot-separated key."""
        node: Any = self._values
        for part in path.split("."):
            if not isinstance(node, Mapping) or part not in node:
                return default
            node = node[part]
        return node

    def require(self, path: str) -> Any:
        """Read a key that must exist."""
        sentinel = object()
        value = self.get(path, sentinel)
        if value is sentinel:
            raise ConfigurationError(
                f"Missing required configuration: {path} " f"(environment: {self._environment})"
            )
        return value

    def get_str(self, path: str, default: str = "") -> str:
        value = self.get(path, default)
        return default if value is None else str(value)

    def get_int(self, path: str, default: int = 0) -> int:
        value = self.get(path, default)
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise ConfigurationError(f"{path}: expected an integer, got {value!r}") from error

    def get_float(self, path: str, default: float = 0.0) -> float:
        value = self.get(path, default)
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ConfigurationError(f"{path}: expected a number, got {value!r}") from error

    def get_bool(self, path: str, default: bool = False) -> bool:
        value = self.get(path, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def has(self, path: str) -> bool:
        sentinel = object()
        return self.get(path, sentinel) is not sentinel

    # ----------------------------------------------------------- secrets --
    def secret(self, path: str) -> Optional[str]:
        """Read a secret. Never logged, never exported."""
        value = self.get(path)
        return None if value is None else str(value)

    def secret_keys(self) -> List[str]:
        """Every key detected as sensitive (§21)."""
        return sorted(key for key in flatten(self._values) if is_secret_key(key))

    def as_dict(self, reveal_secrets: bool = False) -> Dict[str, Any]:
        """The whole tree. Secrets are redacted unless explicitly revealed."""
        return dict(self._values) if reveal_secrets else redact(self._values)

    def to_json(self) -> str:
        """Serialised safely — this is what may reach a log or a report."""
        return json.dumps(self.as_dict(), indent=2, sort_keys=True, default=str)

    def __repr__(self) -> str:
        # Never let an accidental repr() leak a broker password.
        return (
            f"LayeredConfiguration(environment={self._environment!r}, "
            f"keys={len(flatten(self._values))}, secrets_redacted=True)"
        )

    # -------------------------------------------------------- validation --
    def validate(self, rules: Sequence[ValidationRule]) -> List[str]:
        """Check every rule and return all problems, not just the first.

        Reporting one error per run turns a five-key mistake into five
        runs (§28).
        """
        problems: List[str] = []
        for rule in rules:
            sentinel = object()
            value = self.get(rule.key, sentinel)
            problem = rule.check(value is not sentinel, value)
            if problem:
                problems.append(problem)
        return problems

    def validate_or_raise(self, rules: Sequence[ValidationRule]) -> None:
        problems = self.validate(rules)
        if problems:
            listed = "\n  - ".join(problems)
            raise ConfigurationError(
                f"Configuration is invalid ({len(problems)} problem(s)):\n  - {listed}"
            )

    def with_overrides(self, overrides: Mapping[str, Any]) -> "LayeredConfiguration":
        """A new configuration with runtime overrides applied (§5, layer 6)."""
        nested: Dict[str, Any] = {}
        for key, value in overrides.items():
            node = nested
            parts = key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

        return LayeredConfiguration(
            values=deep_merge(self._values, nested),
            sources=[
                *self._sources,
                SourceRecord("runtime", "overrides", len(overrides)),
            ],
            environment=self._environment,
        )


class ConfigurationLoader:
    """Assembles a :class:`LayeredConfiguration` from ordered sources."""

    def __init__(
        self,
        config_root: str | Path = "configs",
        environment: Optional[str] = None,
        env_prefix: str = ENV_PREFIX,
    ) -> None:
        self._root = Path(config_root)
        self._prefix = env_prefix
        self._environment = self._resolve_environment(environment)

    @property
    def environment(self) -> str:
        return self._environment

    def _resolve_environment(self, explicit: Optional[str]) -> str:
        chosen = explicit or os.environ.get(f"{self._prefix}ENV") or "development"
        cleaned = chosen.strip().lower()
        if cleaned not in ENVIRONMENTS:
            known = ", ".join(ENVIRONMENTS)
            raise ConfigurationError(f"Unknown environment '{chosen}'. Supported: {known}")
        return cleaned

    def load(
        self,
        defaults: Optional[Mapping[str, Any]] = None,
        overrides: Optional[Mapping[str, Any]] = None,
    ) -> LayeredConfiguration:
        """Build the configuration, applying every layer in order."""
        values: Dict[str, Any] = {}
        sources: List[SourceRecord] = []

        if defaults:
            values = deep_merge(values, defaults)
            sources.append(SourceRecord("defaults", "built-in", len(flatten(defaults))))

        for name, path in (
            ("base", self._root / "base.yaml"),
            ("environment", self._root / f"{self._environment}.yaml"),
            ("local", self._root / "local.yaml"),
        ):
            loaded = self._load_file(path)
            if loaded is None:
                sources.append(SourceRecord(name, str(path), 0, applied=False))
                continue
            values = deep_merge(values, loaded)
            sources.append(SourceRecord(name, str(path), len(flatten(loaded))))

        env_values = self._load_environment()
        if env_values:
            values = deep_merge(values, env_values)
            sources.append(SourceRecord("env", f"{self._prefix}*", len(flatten(env_values))))

        if overrides:
            nested: Dict[str, Any] = {}
            for key, value in overrides.items():
                node = nested
                parts = key.split(".")
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = value
            values = deep_merge(values, nested)
            sources.append(SourceRecord("runtime", "overrides", len(overrides)))

        values.setdefault("environment", self._environment)
        return LayeredConfiguration(values, sources, self._environment)

    def _load_file(self, path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ConfigurationError(f"Cannot read {path}: {error}") from error

        try:
            if path.suffix in (".yaml", ".yml"):
                import yaml

                loaded = yaml.safe_load(text) or {}
            else:
                loaded = json.loads(text)
        except Exception as error:
            raise ConfigurationError(f"{path} is not valid: {error}") from error

        if not isinstance(loaded, Mapping):
            raise ConfigurationError(f"{path} must contain a mapping at the top level")
        return dict(loaded)

    def _load_environment(self) -> Dict[str, Any]:
        """Read ``SHADBOT_A__B=value`` into ``{"a": {"b": value}}``.

        A double underscore separates levels; a single underscore is
        ordinary in key names like ``max_positions``.
        """
        nested: Dict[str, Any] = {}
        for raw_key, raw_value in os.environ.items():
            if not raw_key.startswith(self._prefix):
                continue
            trimmed = raw_key[len(self._prefix) :]
            if not trimmed or trimmed == "ENV":
                continue

            parts = [part.lower() for part in re.split(r"__", trimmed) if part]
            if not parts:
                continue

            node = nested
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = _coerce(raw_value)
        return nested


def default_rules() -> List[ValidationRule]:
    """Constraints that apply to every ShadBotTrader deployment."""
    return [
        ValidationRule("environment", required=True, allowed=list(ENVIRONMENTS)),
        ValidationRule("logging.level", allowed=["DEBUG", "INFO", "WARNING", "ERROR"]),
        ValidationRule("trading.max_open_positions", expected_type=int, minimum=0),
        ValidationRule("trading.base_quantity", expected_type=float, minimum=0.0),
        ValidationRule("simulation.spread", expected_type=float, minimum=0.0),
    ]
