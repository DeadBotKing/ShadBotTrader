"""Simulation clock (Phase 16, sections 8-10).

CRITICAL RULE (section 9): simulated code must never call
``datetime.now()``. Every timestamp inside a simulation comes from this
clock, which only ever moves forward and only when told to. That is what
makes a run reproducible (section 10).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.timestamp import Timestamp


class SimulationClock:
    """A monotonic, explicitly-advanced clock bounded by a time window."""

    def __init__(
        self,
        start_time: Timestamp,
        end_time: Optional[Timestamp] = None,
    ) -> None:
        if end_time is not None and end_time.value < start_time.value:
            raise ValidationError("end_time must not precede start_time")
        self._start_time = start_time
        self._end_time = end_time
        self._current = start_time
        self._steps = 0

    @property
    def start_time(self) -> Timestamp:
        return self._start_time

    @property
    def end_time(self) -> Optional[Timestamp]:
        return self._end_time

    @property
    def current_time(self) -> Timestamp:
        """The only legitimate source of 'now' inside a simulation."""
        return self._current

    @property
    def steps(self) -> int:
        """How many times the clock has moved."""
        return self._steps

    @property
    def is_finished(self) -> bool:
        """True once the clock has reached the end of its window."""
        if self._end_time is None:
            return False
        return self._current.value >= self._end_time.value

    @property
    def elapsed(self) -> timedelta:
        """Time covered since the start of the window."""
        return self._current.value - self._start_time.value

    def advance_to(self, moment: Timestamp) -> None:
        """Move the clock forward to ``moment``.

        Moving backwards is rejected: a simulation that could rewind
        would be able to see the future, which breaks causality.
        """
        if moment.value < self._current.value:
            raise ValidationError(
                f"SimulationClock cannot move backwards " f"({moment} < {self._current})"
            )
        if self._end_time is not None and moment.value > self._end_time.value:
            raise ValidationError(f"SimulationClock cannot move past end_time ({moment})")
        if moment.value != self._current.value:
            self._steps += 1
        self._current = moment

    def advance_by(self, delta: timedelta) -> None:
        """Move the clock forward by ``delta``."""
        if delta < timedelta(0):
            raise ValidationError("SimulationClock cannot advance by a negative delta")
        self.advance_to(Timestamp(self._current.value + delta))

    def reset(self) -> None:
        """Return the clock to the start of its window."""
        self._current = self._start_time
        self._steps = 0

    def snapshot(self) -> "ClockSnapshot":
        """Capture the clock state for a checkpoint (section 25)."""
        return ClockSnapshot(
            current=self._current.value,
            steps=self._steps,
        )

    def restore(self, snapshot: "ClockSnapshot") -> None:
        """Restore a previously captured state (section 26)."""
        self._current = Timestamp(snapshot.current)
        self._steps = snapshot.steps

    def __str__(self) -> str:
        return f"SimulationClock({self._current})"


class ClockSnapshot:
    """Immutable capture of a clock's position."""

    def __init__(self, current: datetime, steps: int) -> None:
        self._current = current
        self._steps = steps

    @property
    def current(self) -> datetime:
        return self._current

    @property
    def steps(self) -> int:
        return self._steps
