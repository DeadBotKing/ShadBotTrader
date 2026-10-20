"""The application shutdown sequence."""

from __future__ import annotations

import logging

from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleManager
from ShadBotTrader.core.result import Result


class Shutdown:
    """Runs the shutdown sequence: transition the lifecycle into STOPPED."""

    def __init__(self, lifecycle: LifecycleManager, logger: logging.Logger) -> None:
        self._lifecycle = lifecycle
        self._logger = logger

    def run(self) -> Result[None]:
        """Stop every registered component and report the outcome."""
        self._logger.info("Stopping application lifecycle")
        try:
            self._lifecycle.stop()
        except Exception as exc:
            self._logger.exception("Shutdown failed")
            return Result.fail(exc)
        self._logger.info("Application lifecycle stopped")
        return Result.ok(None)
