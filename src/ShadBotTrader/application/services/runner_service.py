"""Continuous supervised runner (Phase 24, §33-37).

Turns the one-shot live tick into something that can be left running:

    every `interval` seconds
        -> health check
        -> one decision tick
        -> record the outcome
    on SIGINT / SIGTERM
        -> drain, persist, stop

Four rules from the phase document shape this:

* **Trading safety (§33).** A deployment must not interrupt active
  trading. The runner refuses to stop mid-tick; it finishes the cycle
  first.
* **Safe shutdown (§34).** Stop accepting work, finish what is in
  flight, persist, then exit — in that order.
* **State persistence (§35).** A restart resumes from a recorded state
  rather than pretending nothing happened.
* **Process management (§37).** Failures are counted, not fatal. A
  consecutive-failure ceiling stops a runner that is failing every
  cycle, because retrying forever hides an outage.
"""

from __future__ import annotations

import json
import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ShadBotTrader.domain.deployment.health import HealthMonitor, HealthStatus
from ShadBotTrader.domain.deployment.release import ShutdownPlan


@dataclass
class RunnerState:
    """What the runner has done — persisted so a restart can resume."""

    started_at: str = ""
    last_tick_at: str = ""
    cycles: int = 0
    trades: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    last_status: str = ""
    last_reason: str = ""
    stopped_at: str = ""
    stop_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "last_tick_at": self.last_tick_at,
            "cycles": self.cycles,
            "trades": self.trades,
            "failures": self.failures,
            "consecutive_failures": self.consecutive_failures,
            "last_status": self.last_status,
            "last_reason": self.last_reason,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RunnerState":
        state = cls()
        for key, value in payload.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


@dataclass
class RunnerConfig:
    """How the runner behaves."""

    interval_seconds: float = 300.0
    max_cycles: Optional[int] = None
    max_consecutive_failures: int = 5
    require_healthy: bool = True
    state_path: Optional[str] = None
    #: Take a database backup every N cycles (0 disables).
    backup_every: int = 0

    @property
    def runs_forever(self) -> bool:
        return self.max_cycles is None


class RunnerService:
    """Supervises repeated execution of a tick function."""

    def __init__(
        self,
        tick: Callable[[], Any],
        config: Optional[RunnerConfig] = None,
        monitor: Optional[HealthMonitor] = None,
        backup: Optional[Any] = None,
        on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._tick = tick
        self._config = config or RunnerConfig()
        self._monitor = monitor
        self._backup = backup
        self._on_event = on_event

        self._state = RunnerState()
        self._plan = ShutdownPlan()
        self._stop_requested = threading.Event()
        self._tick_in_progress = threading.Lock()
        self._results: List[Any] = []

    # ------------------------------------------------------------- state --
    @property
    def state(self) -> RunnerState:
        return self._state

    @property
    def shutdown(self) -> ShutdownPlan:
        return self._plan

    @property
    def results(self) -> List[Any]:
        return list(self._results)

    @property
    def is_stopping(self) -> bool:
        return self._stop_requested.is_set()

    # ------------------------------------------------------------ control --
    def request_stop(self, reason: str = "requested") -> None:
        """Ask the runner to stop after the current cycle finishes.

        Deliberately does not interrupt a tick in progress: §33 forbids
        cutting into active trading, and a half-executed order is far
        worse than a five-minute delay.
        """
        if not self._stop_requested.is_set():
            self._stop_requested.set()
            self._state.stop_reason = reason
            self._emit("stop_requested", {"reason": reason})

    def install_signal_handlers(self) -> None:
        """Convert SIGINT/SIGTERM into a graceful stop."""

        def handler(signum: int, _frame: Any) -> None:
            self.request_stop(f"signal {signal.Signals(signum).name}")

        for received in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(received, handler)
            except (ValueError, OSError):  # pragma: no cover - non-main thread
                pass

    # --------------------------------------------------------------- run --
    def run(self) -> RunnerState:
        """Run until stopped, the cycle limit is reached, or failures pile up."""
        self._state.started_at = _now()
        self._load_state()
        self._emit("started", {"interval": self._config.interval_seconds})

        try:
            while not self._should_stop():
                self._run_cycle()
                if self._should_stop():
                    break
                self._sleep_between_cycles()
        finally:
            self._graceful_stop()

        return self._state

    def run_once(self) -> Any:
        """Execute exactly one cycle — used by tests and manual runs."""
        return self._run_cycle()

    # ------------------------------------------------------------ cycle --
    def _run_cycle(self) -> Any:
        with self._tick_in_progress:
            self._plan.in_flight = 1
            self._state.cycles += 1
            self._state.last_tick_at = _now()

            try:
                if self._config.require_healthy and not self._health_allows_work():
                    self._state.last_status = "unhealthy"
                    self._state.last_reason = "health check refused the cycle"
                    self._record_failure()
                    return None

                result = self._tick()
                self._results.append(result)
                self._note_result(result)
                self._state.consecutive_failures = 0
                self._maybe_backup()
                return result

            except Exception as error:
                self._state.last_status = "failed"
                self._state.last_reason = f"{type(error).__name__}: {error}"
                self._record_failure()
                self._emit("cycle_failed", {"error": self._state.last_reason})
                return None

            finally:
                self._plan.in_flight = 0
                self._save_state()

    def _note_result(self, result: Any) -> None:
        status = getattr(result, "status", "ok")
        self._state.last_status = str(status)
        self._state.last_reason = str(getattr(result, "reason", ""))
        if getattr(result, "acted", False):
            self._state.trades += 1
        self._emit("cycle_complete", {"status": self._state.last_status})

    def _record_failure(self) -> None:
        self._state.failures += 1
        self._state.consecutive_failures += 1
        if self._state.consecutive_failures >= self._config.max_consecutive_failures:
            # Retrying forever hides an outage instead of surfacing it.
            self.request_stop(f"{self._state.consecutive_failures} consecutive failures")

    def _health_allows_work(self) -> bool:
        if self._monitor is None:
            return True
        report = self._monitor.run()
        if report.status is HealthStatus.UNHEALTHY:
            self._emit("unhealthy", {"failures": [c.name for c in report.failures]})
            return False
        return True

    def _maybe_backup(self) -> None:
        if not self._backup or self._config.backup_every <= 0:
            return
        if self._state.cycles % self._config.backup_every:
            return
        try:
            record = self._backup.create(note=f"cycle {self._state.cycles}")
            self._emit("backup", {"path": record.path, "rows": record.total_rows})
        except Exception as error:  # a backup failure must not stop trading
            self._emit("backup_failed", {"error": str(error)})

    # --------------------------------------------------------- lifecycle --
    def _should_stop(self) -> bool:
        if self._stop_requested.is_set():
            return True
        limit = self._config.max_cycles
        return limit is not None and self._state.cycles >= limit

    def _sleep_between_cycles(self) -> None:
        """Wait, but wake immediately when a stop is requested."""
        self._stop_requested.wait(timeout=self._config.interval_seconds)

    def _graceful_stop(self) -> None:
        """Drain, persist, stop — in that order (§34)."""
        if self._plan.is_stopped:
            return

        reason = self._state.stop_reason or "completed"
        if self._plan.accepting_work:
            self._plan.begin_drain(reason)

        # Wait for a tick that is still running rather than cutting it off.
        with self._tick_in_progress:
            self._plan.complete_work()

        self._plan.persist()
        self._state.stopped_at = _now()
        self._save_state()
        self._plan.finish()
        self._emit("stopped", {"reason": reason, "cycles": self._state.cycles})

    # ----------------------------------------------------------- storage --
    def _load_state(self) -> None:
        path = self._state_path()
        if path is None or not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return  # a damaged state file must not stop the runner

        previous = RunnerState.from_dict(payload)
        # Carry the counters forward; this run gets a fresh start time.
        self._state.cycles = previous.cycles
        self._state.trades = previous.trades
        self._state.failures = previous.failures
        self._emit(
            "state_restored",
            {"cycles": previous.cycles, "trades": previous.trades},
        )

    def _save_state(self) -> None:
        path = self._state_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")
        except OSError:
            pass  # never let state persistence break the loop

    def _state_path(self) -> Optional[Path]:
        return Path(self._config.state_path) if self._config.state_path else None

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if self._on_event is not None:
            try:
                self._on_event(event, payload)
            except Exception:
                pass  # an observer must never break the runner

    def summary(self) -> Dict[str, Any]:
        return {
            "state": self._state.to_dict(),
            "shutdown": self._plan.to_dict(),
            "config": {
                "interval_seconds": self._config.interval_seconds,
                "max_cycles": self._config.max_cycles,
                "backup_every": self._config.backup_every,
            },
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sleep_until_next_interval(interval_seconds: float) -> None:  # pragma: no cover
    """Align to the next interval boundary (e.g. the next 5-minute mark)."""
    now = time.time()
    time.sleep(interval_seconds - (now % interval_seconds))
