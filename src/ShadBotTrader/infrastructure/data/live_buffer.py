"""Rolling live-market buffer (Phase 30 §5).

Every five minutes the platform fetches one 5M candle and one 1H candle.
This buffer keeps the most recent ``capacity`` candles per timeframe and
maintains itself: oldest out, newest in, always in chronological order.

Three behaviours matter more than the ring itself:

**Replace, never duplicate.** The current 1H bar is re-fetched twelve
times before it closes. Appending it twelve times would fabricate twelve
hours of history. A candle whose timestamp is already present *updates*
that slot.

**Reject the past.** A candle older than the newest one is refused
rather than inserted out of order — a broker hiccup must not silently
corrupt the series the model reads.

**Prove the window.** The buffer holds 800 candles so that, after
feature warm-up, at least 500 usable rows remain. It verifies that at
runtime instead of assuming it; if warm-up ever eats too much, it says
so rather than handing the model a short input.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle

#: Candles retained per timeframe (Phase 30 §5).
DEFAULT_CAPACITY = 800

#: Rows the models consume.
REQUIRED_WINDOW = 500


@dataclass(frozen=True)
class BufferState:
    """What the buffer currently holds, for logging and health checks."""

    timeframe: str
    size: int
    capacity: int
    oldest: Optional[str]
    newest: Optional[str]
    accepted: int
    replaced: int
    rejected: int

    @property
    def is_full(self) -> bool:
        return self.size >= self.capacity

    def to_dict(self) -> Dict[str, object]:
        return {
            "timeframe": self.timeframe,
            "size": self.size,
            "capacity": self.capacity,
            "oldest": self.oldest,
            "newest": self.newest,
            "accepted": self.accepted,
            "replaced": self.replaced,
            "rejected": self.rejected,
            "full": self.is_full,
        }


class RollingCandleBuffer:
    """A fixed-size, chronologically ordered candle window for one timeframe."""

    def __init__(self, timeframe: str, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity < REQUIRED_WINDOW:
            raise ValidationError(
                f"capacity must be at least {REQUIRED_WINDOW} — the models "
                f"consume {REQUIRED_WINDOW}-row windows, and feature warm-up "
                f"consumes more on top of that."
            )
        self._timeframe = timeframe
        self._capacity = capacity
        self._candles: Deque[Candle] = deque(maxlen=capacity)
        self._accepted = 0
        self._replaced = 0
        self._rejected = 0

    # ----------------------------------------------------------- state --
    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return len(self._candles)

    @property
    def is_full(self) -> bool:
        return len(self._candles) >= self._capacity

    @property
    def candles(self) -> List[Candle]:
        """A snapshot, oldest first."""
        return list(self._candles)

    @property
    def newest(self) -> Optional[Candle]:
        return self._candles[-1] if self._candles else None

    @property
    def oldest(self) -> Optional[Candle]:
        return self._candles[0] if self._candles else None

    def state(self) -> BufferState:
        return BufferState(
            timeframe=self._timeframe,
            size=self.size,
            capacity=self._capacity,
            oldest=str(self.oldest.open_time) if self.oldest else None,
            newest=str(self.newest.open_time) if self.newest else None,
            accepted=self._accepted,
            replaced=self._replaced,
            rejected=self._rejected,
        )

    # ---------------------------------------------------------- updates --
    def push(self, candle: Candle) -> str:
        """Add or update one candle. Returns what happened.

        ``"appended"``  a genuinely new bar
        ``"replaced"``  the same bar, refreshed (an unclosed candle)
        ``"rejected"``  older than the newest — refused, not inserted
        """
        newest = self.newest

        if newest is None:
            self._candles.append(candle)
            self._accepted += 1
            return "appended"

        incoming = candle.open_time.value
        latest = newest.open_time.value

        if incoming == latest:
            # Same bar, newer values: the live candle is still forming.
            self._candles[-1] = candle
            self._replaced += 1
            return "replaced"

        if incoming < latest:
            # Out-of-order data. Update in place when we already know the
            # slot; otherwise refuse rather than break the ordering.
            for position, existing in enumerate(self._candles):
                if existing.open_time.value == incoming:
                    self._candles[position] = candle
                    self._replaced += 1
                    return "replaced"
            self._rejected += 1
            return "rejected"

        self._candles.append(candle)  # deque evicts the oldest for us
        self._accepted += 1
        return "appended"

    def extend(self, candles: Iterable[Candle]) -> Dict[str, int]:
        """Push many candles, reporting the tally of each outcome."""
        tally = {"appended": 0, "replaced": 0, "rejected": 0}
        for candle in sorted(candles, key=lambda item: item.open_time.value):
            tally[self.push(candle)] += 1
        return tally

    def clear(self) -> None:
        self._candles.clear()

    # ----------------------------------------------------------- checks --
    def has_enough_for_window(self, warmup: int, window: int = REQUIRED_WINDOW) -> bool:
        """True when ``window`` usable rows survive a ``warmup``-row warm-up."""
        return self.size - warmup >= window

    def shortfall(self, warmup: int, window: int = REQUIRED_WINDOW) -> int:
        """How many candles are missing for a full window (0 when fine)."""
        missing = window + warmup - self.size
        return max(missing, 0)

    def explain_shortfall(self, warmup: int, window: int = REQUIRED_WINDOW) -> str:
        """A message that says what to do, not just that something failed."""
        missing = self.shortfall(warmup, window)
        if missing == 0:
            return ""
        return (
            f"{self._timeframe}: {self.size} candles buffered, but feature "
            f"warm-up consumes {warmup} and the model needs {window} rows. "
            f"Short by {missing}. Increase the buffer capacity to at least "
            f"{window + warmup}, or wait for more candles."
        )


class LiveMarketData:
    """Both timeframes together — the live counterpart of the dataset.

    The trading loop fetches one 5M candle and one 1H candle every five
    minutes and pushes them here; everything downstream reads from this.
    """

    def __init__(
        self,
        timeframes: Sequence[str] = ("5M", "1H", "1D"),
        capacity: int = DEFAULT_CAPACITY,
    ) -> None:
        if not timeframes:
            raise ValidationError("At least one timeframe is required")
        self._buffers: Dict[str, RollingCandleBuffer] = {
            timeframe: RollingCandleBuffer(timeframe, capacity) for timeframe in timeframes
        }

    def buffer(self, timeframe: str) -> RollingCandleBuffer:
        buffer = self._buffers.get(timeframe)
        if buffer is None:
            raise ValidationError(
                f"No buffer for timeframe '{timeframe}'. "
                f"Known: {', '.join(sorted(self._buffers))}"
            )
        return buffer

    @property
    def timeframes(self) -> List[str]:
        return sorted(self._buffers)

    def push(self, timeframe: str, candle: Candle) -> str:
        return self.buffer(timeframe).push(candle)

    def prime(self, timeframe: str, candles: Iterable[Candle]) -> Dict[str, int]:
        """Fill a buffer from history — the cold-start path."""
        return self.buffer(timeframe).extend(candles)

    def states(self) -> Dict[str, Dict[str, object]]:
        return {name: buffer.state().to_dict() for name, buffer in self._buffers.items()}

    def ready(self, warmup: int, window: int = REQUIRED_WINDOW) -> bool:
        """True only when every timeframe can produce a full window."""
        return all(
            buffer.has_enough_for_window(warmup, window) for buffer in self._buffers.values()
        )

    def blocking_reasons(self, warmup: int, window: int = REQUIRED_WINDOW) -> List[str]:
        """Why the platform cannot predict yet — empty when it can."""
        return [
            message
            for buffer in self._buffers.values()
            if (message := buffer.explain_shortfall(warmup, window))
        ]
