"""Command bus (Phase 19, section 13).

Routes a dispatched command to its handler and keeps a short history so
the dashboard can report what happened.

Commands run in a background thread: retraining a model or ingesting
5,000 bars takes far longer than an HTTP request should, and blocking
the server would make the UI appear frozen. Only one command runs at a
time — two concurrent ingests writing the same dataset would race.
"""

from __future__ import annotations

import threading
import traceback
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from ShadBotTrader.presentation.commands.commands import (
    Command,
    CommandKind,
    CommandResult,
    CommandStatus,
)
from ShadBotTrader.presentation.commands.handlers import CommandHandlers, Handler


class CommandBus:
    """Dispatches commands to handlers, one at a time, off the request thread."""

    def __init__(
        self,
        handlers: Optional[Dict[CommandKind, Handler]] = None,
        history_size: int = 20,
    ) -> None:
        self._handlers: Dict[CommandKind, Handler] = dict(handlers or {})
        self._history: Deque[CommandResult] = deque(maxlen=history_size)
        self._lock = threading.Lock()
        self._running: Optional[CommandKind] = None
        self._started_at: Optional[datetime] = None
        self._thread: Optional[threading.Thread] = None

    @classmethod
    def with_defaults(
        cls,
        database_path: str,
        storage_root: str = "datasets",
    ) -> "CommandBus":
        """A bus wired to the standard handlers."""
        return cls(CommandHandlers(database_path, storage_root).registry())

    # -- state ----------------------------------------------------------------
    @property
    def is_busy(self) -> bool:
        with self._lock:
            return self._running is not None

    @property
    def running(self) -> Optional[CommandKind]:
        with self._lock:
            return self._running

    @property
    def running_for_seconds(self) -> float:
        with self._lock:
            if self._started_at is None:
                return 0.0
            return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    def history(self) -> List[CommandResult]:
        """Most recent results first."""
        with self._lock:
            return list(reversed(self._history))

    def last_result(self) -> Optional[CommandResult]:
        with self._lock:
            return self._history[-1] if self._history else None

    # -- dispatch --------------------------------------------------------------
    def dispatch(self, command: Command) -> CommandResult:
        """Run a command and wait for it (used by tests and the CLI)."""
        handler = self._handlers.get(command.kind)
        if handler is None:
            return CommandResult.rejected(
                command.kind, f"No handler registered for '{command.kind.value}'"
            )

        with self._lock:
            if self._running is not None:
                return CommandResult.rejected(
                    command.kind,
                    f"'{self._running.value}' is still running — one at a time.",
                )
            self._running = command.kind
            self._started_at = datetime.now(timezone.utc)

        try:
            result = handler(command)
        except Exception as error:  # a handler must never kill the server
            result = CommandResult.failure(
                command.kind,
                f"{type(error).__name__}: {error}",
                traceback.format_exc()[-1500:],
            )
        finally:
            with self._lock:
                self._running = None
                self._started_at = None

        with self._lock:
            self._history.append(result)
        return result

    def dispatch_async(self, command: Command) -> CommandResult:
        """Start a command in the background and return immediately."""
        if command.kind not in self._handlers:
            return CommandResult.rejected(
                command.kind, f"No handler registered for '{command.kind.value}'"
            )

        with self._lock:
            if self._running is not None:
                return CommandResult.rejected(
                    command.kind,
                    f"'{self._running.value}' is still running — wait for it to finish.",
                )

        thread = threading.Thread(
            target=self.dispatch,
            args=(command,),
            daemon=True,
            name=f"command-{command.kind.value}",
        )
        self._thread = thread
        thread.start()

        return CommandResult(
            kind=command.kind,
            status=CommandStatus.RUNNING,
            message="Started — refresh to see the result.",
        )

    def wait(self, timeout: float = 300.0) -> None:
        """Block until the running command finishes (tests use this)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def register(self, kind: CommandKind, handler: Handler) -> None:
        self._handlers[kind] = handler

    @property
    def known_kinds(self) -> List[CommandKind]:
        return list(self._handlers)
