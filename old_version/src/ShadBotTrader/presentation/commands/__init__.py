"""Commands: the GUI's way of asking the platform to do something.

Phase 19 §3 lists "Command Dispatch" as a GUI responsibility and §12-13
define the path::

    Controller -> Command Bus -> Command Handler -> Application Service

The GUI expresses *intent*; the application services do the work. A
handler that started calculating something itself would violate §4.
"""

from ShadBotTrader.presentation.commands.bus import CommandBus
from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandDescriptor,
    CommandField,
    CommandKind,
    CommandResult,
    CommandStatus,
)
from ShadBotTrader.presentation.commands.handlers import (
    CommandHandlers,
    descriptor_for,
    descriptors,
)

__all__ = [
    "Command",
    "CommandBus",
    "CommandDescriptor",
    "CommandField",
    "CommandHandlers",
    "CommandKind",
    "CommandResult",
    "CommandStatus",
    "descriptor_for",
    "descriptors",
]
