"""Typed configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from ShadBotTrader.core.errors import ShadBotTraderError

_MISSING = object()


class ConfigurationError(ShadBotTraderError):
    """Raised when configuration is missing, malformed or invalid."""


class Configuration:
    """An immutable, read-only configuration tree with typed accessors.

    Keys are dot-separated paths, e.g. ``logging.level``.
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = dict(values)

    def get(self, path: str, default: Any = _MISSING) -> Any:
        """Return the raw value at ``path`` or ``default`` if absent."""
        keys = path.split(".")
        node: Any = self._values
        for key in keys:
            if not isinstance(node, Mapping) or key not in node:
                if default is _MISSING:
                    raise ConfigurationError(f"Missing configuration key: {path}")
                return default
            node = node[key]
        return node

    def get_str(self, path: str, default: str | None = None) -> str:
        """Return a string value at ``path``."""
        value = self.get(path, default)
        if value is None:
            if default is not None:
                return default
            raise ConfigurationError(f"Missing configuration key: {path}")
        if not isinstance(value, str):
            raise ConfigurationError(f"Configuration key {path} must be a string")
        return value

    def get_int(self, path: str, default: int | None = None) -> int:
        """Return an integer value at ``path``."""
        value = self.get(path, default)
        if value is None:
            if default is not None:
                return default
            raise ConfigurationError(f"Missing configuration key: {path}")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigurationError(f"Configuration key {path} must be an integer")
        return value

    def get_float(self, path: str, default: float | None = None) -> float:
        """Return a float value at ``path``."""
        value = self.get(path, default)
        if value is None:
            if default is not None:
                return default
            raise ConfigurationError(f"Missing configuration key: {path}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(f"Configuration key {path} must be a number")
        return float(value)

    def get_bool(self, path: str, default: bool | None = None) -> bool:
        """Return a boolean value at ``path``."""
        value = self.get(path, default)
        if value is None:
            if default is not None:
                return default
            raise ConfigurationError(f"Missing configuration key: {path}")
        if not isinstance(value, bool):
            raise ConfigurationError(f"Configuration key {path} must be a boolean")
        return value

    def section(self, path: str) -> "Configuration":
        """Return the nested mapping at ``path`` as a Configuration."""
        value = self.get(path)
        if not isinstance(value, Mapping):
            raise ConfigurationError(f"Configuration key {path} must be a section")
        return Configuration(value)

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the raw values."""
        return dict(self._values)

    def __contains__(self, path: str) -> bool:
        try:
            self.get(path)
            return True
        except ConfigurationError:
            return False


class YamlConfigurationLoader:
    """Loads a :class:`Configuration` from a YAML file."""

    def load(self, path: Path | str) -> Configuration:
        """Load and validate the YAML file at ``path``."""
        file_path = Path(path)
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Invalid YAML in {file_path}") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigurationError(f"Configuration root must be a mapping: {file_path}")
        return Configuration(data)
