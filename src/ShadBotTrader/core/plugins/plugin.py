"""Plugin contract: metadata plus a lifecycle-aware extension point."""

from __future__ import annotations

from dataclasses import dataclass

from ShadBotTrader.core.errors import PluginError
from ShadBotTrader.core.services.base_service import BaseService


@dataclass(frozen=True)
class PluginMetadata:
    """Static identity of a plugin."""

    name: str
    version: str
    description: str = ""
    api_version: str = "1.0"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise PluginError("Plugin name must not be empty")
        if not self.version.strip():
            raise PluginError("Plugin version must not be empty")


class Plugin(BaseService):
    """Base class for every pluggable capability of the platform."""

    def __init__(self, metadata: PluginMetadata) -> None:
        super().__init__(name=metadata.name)
        self._metadata = metadata

    @property
    def metadata(self) -> PluginMetadata:
        """The static metadata of this plugin."""
        return self._metadata
