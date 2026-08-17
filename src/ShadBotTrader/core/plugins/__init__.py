"""Plugin architecture — Phase 9.

PluginRegistry  "what plugins are registered?"
PluginManager   "what is their operational state?"
"""

from ShadBotTrader.core.plugins.manager import ENTRY_POINT_GROUP, PluginManager
from ShadBotTrader.core.plugins.plugin import Plugin, PluginMetadata
from ShadBotTrader.core.plugins.registry import (
    HOST_API_VERSION,
    PluginRecord,
    PluginRegistry,
    PluginState,
)

__all__ = [
    "ENTRY_POINT_GROUP",
    "HOST_API_VERSION",
    "Plugin",
    "PluginManager",
    "PluginMetadata",
    "PluginRecord",
    "PluginRegistry",
    "PluginState",
]
