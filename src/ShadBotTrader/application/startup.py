"""The application startup sequence."""

from __future__ import annotations

import logging

from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleManager
from ShadBotTrader.core.result import Result


class Startup:
    """Runs the startup sequence: transition the lifecycle into RUNNING."""

    def __init__(self, lifecycle: LifecycleManager, logger: logging.Logger) -> None:
        self._lifecycle = lifecycle
        self._logger = logger

    def run(self) -> Result[None]:
        """Start every registered component and report the outcome."""
        self._logger.info("Starting application lifecycle")
        try:
            self._lifecycle.start()
        except Exception as exc:
            self._logger.exception("Startup failed")
            return Result.fail(exc)
        self._logger.info("Application lifecycle started")
        return Result.ok(None)
