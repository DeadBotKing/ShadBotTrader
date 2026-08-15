"""The start -> run -> stop execution cycle of an application."""

from __future__ import annotations

from ShadBotTrader.application.app import Application
from ShadBotTrader.application.application_state import ApplicationState
from ShadBotTrader.application.shutdown import Shutdown
from ShadBotTrader.application.startup import Startup


class Runtime:
    """Executes the full start/run/stop cycle of an application."""

    def __init__(self, application: Application) -> None:
        self._application = application
        self._logger = application.logger

    def run(self) -> int:
        """Start the app, run it, shut it down and return an exit code.

        The foundation phase has no long-running workload, so the runtime
        performs a complete start -> stop cycle and returns 0. Blocking
        execution (scheduler / trading loop) is introduced in a later
        phase.
        """
        self._logger.info("Starting")
        self._application.transition(ApplicationState.STARTING)

        startup = Startup(self._application.lifecycle, self._logger).run()
        if startup.is_failure:
            self._application.transition(ApplicationState.FAILED)
            return 1

        self._application.transition(ApplicationState.RUNNING)

        exit_code = 0
        try:
            # Nothing long-running exists yet; the cycle completes here.
            return exit_code
        finally:
            self._application.transition(ApplicationState.STOPPING)
            shutdown = Shutdown(self._application.lifecycle, self._logger).run()
            if shutdown.is_failure:
                self._application.transition(ApplicationState.FAILED)
                exit_code = 1
            else:
                self._application.transition(ApplicationState.STOPPED)
                self._logger.info("Shutdown complete")
        return exit_code
