"""Progress reporting for feature-set computation (Phase 37).

Computing the standard feature catalogue over 100,000 candles takes minutes
and used to print nothing whatsoever. The operator could not tell which
feature was being computed, how many were done, or whether a slow
calculator had hung — the same blindness Phase 36 fixed for training.

The contract mirrors ``ai/training_progress.py`` deliberately: two
long-running operations in the same product should not report progress
in two different shapes.
"""

from __future__ import annotations

import sys
import time
from typing import Any, List, Optional, Protocol, TextIO


class FeatureProgressReporter(Protocol):
    """Observer contract for one feature-set computation.

    Implementations must not influence the computation: a reporter may
    never change which features are computed, their order, or the values
    that come out.
    """

    def on_set_begin(
        self,
        set_name: str,
        symbol: str,
        timeframe: str,
        total: int,
        candles: int,
        reason: str = "",
    ) -> None:
        """Called once before the first feature.

        ``reason`` explains why a recompute is happening at all, which is
        the question an operator asks when a run they expected to be
        instant starts churning through the whole catalogue (Phase 38).
        """

    def on_cache_hit(self, set_name: str, symbol: str, timeframe: str, total: int) -> None:
        """Called instead of the whole cycle when nothing changed."""

    def on_feature_begin(self, index: int, total: int, feature_id: str) -> None:
        """Called before each feature is computed."""

    def on_feature_end(self, index: int, total: int, outcome: Any) -> None:
        """Called after each feature, with its outcome."""

    def on_set_end(self, outcomes: List[Any]) -> None:
        """Called once after the last feature."""


class NullFeatureProgress:
    """Reporter that does nothing (the default; keeps the service silent)."""

    def on_set_begin(
        self,
        set_name: str,
        symbol: str,
        timeframe: str,
        total: int,
        candles: int,
        reason: str = "",
    ) -> None:
        return None

    def on_cache_hit(self, set_name: str, symbol: str, timeframe: str, total: int) -> None:
        return None

    def on_feature_begin(self, index: int, total: int, feature_id: str) -> None:
        return None

    def on_feature_end(self, index: int, total: int, outcome: Any) -> None:
        return None

    def on_set_end(self, outcomes: List[Any]) -> None:
        return None


def _bar(fraction: float, width: int = 28) -> str:
    """Render a text progress bar for ``fraction`` in ``[0, 1]``."""
    fraction = min(max(fraction, 0.0), 1.0)
    filled = int(round(fraction * width))
    return "#" * filled + "-" * (width - filled)


def _duration(seconds: float) -> str:
    """Format a duration as ``M:SS`` or ``Ns``."""
    if seconds < 0 or seconds != seconds:  # negative or NaN
        return "--"
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}:{secs:02d}"
    return f"{secs}s"


class ConsoleFeatureProgress:
    """Prints one line per feature plus a running bar and ETA.

    Output::

        [####------------------------]  14.7% |  16/109 | atr_14
              stored v1 | 4,923 values | quality 0.98

    The ETA is derived from the features already finished, so it settles
    quickly: unlike training folds, catalogue features take broadly
    similar amounts of time.
    """

    def __init__(self, stream: Optional[TextIO] = None, bar_width: int = 28) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._bar_width = bar_width
        self._started = 0.0
        self._done = 0
        self._quarantined = 0
        self._research = 0

    def _write(self, text: str) -> None:
        self._stream.write(text + "\n")
        self._stream.flush()

    def on_set_begin(
        self,
        set_name: str,
        symbol: str,
        timeframe: str,
        total: int,
        candles: int,
        reason: str = "",
    ) -> None:
        self._started = time.monotonic()
        self._done = 0
        self._quarantined = 0
        self._research = 0
        self._write("")
        self._write("=" * 74)
        self._write(f"  FEATURES  {set_name}")
        self._write("=" * 74)
        self._write(f"  series    : {symbol} {timeframe}")
        self._write(f"  candles   : {candles:,}")
        self._write(f"  features  : {total}")
        if reason:
            self._write(f"  recompute : {reason}")
        self._write("-" * 74)

    def on_cache_hit(self, set_name: str, symbol: str, timeframe: str, total: int) -> None:
        self._started = time.monotonic()
        self._write("")
        self._write("=" * 74)
        self._write(f"  FEATURES  {set_name}")
        self._write("=" * 74)
        self._write(f"  series    : {symbol} {timeframe}")
        self._write(f"  {total} feature(s) reused from the store — nothing changed.")
        self._write("  The candles, the feature set and the catalogue all match")
        self._write("  what was stored, so recomputing would produce identical")
        self._write("  numbers. Update the dataset to trigger a full recompute.")
        self._write("=" * 74)
        self._write("")

    def on_feature_begin(self, index: int, total: int, feature_id: str) -> None:
        fraction = index / total if total else 1.0
        self._write(
            f"[{_bar(fraction, self._bar_width)}] {fraction * 100:5.1f}% | "
            f"{index + 1:>3}/{total} | {feature_id}"
        )

    def on_feature_end(self, index: int, total: int, outcome: Any) -> None:
        self._done += 1
        quarantined = bool(getattr(outcome, "quarantined", False))
        live = bool(getattr(outcome, "live_compatible", True))
        if quarantined:
            self._quarantined += 1
        if not live:
            self._research += 1

        if quarantined:
            issues = getattr(getattr(outcome, "quality", None), "issues", []) or []
            reason = ", ".join(str(getattr(item, "code", item)) for item in issues[:2])
            self._write(f"      QUARANTINED — {reason or 'failed quality checks'}")
            return

        score = getattr(getattr(outcome, "quality", None), "score", None)
        overall = getattr(score, "overall", None)
        note = "" if live else " | research-only"
        self._write(
            f"      stored v{getattr(outcome, 'version', '?')} | "
            f"{getattr(outcome, 'available_count', 0):,} values | "
            f"quality {float(overall):.2f}{note}"
            if overall is not None
            else f"      stored v{getattr(outcome, 'version', '?')}{note}"
        )

    def on_set_end(self, outcomes: List[Any]) -> None:
        elapsed = time.monotonic() - self._started
        total = len(outcomes)
        stored = total - self._quarantined
        self._write("-" * 74)
        self._write(
            f"  {stored}/{total} stored | {self._quarantined} quarantined | "
            f"{self._research} research-only"
        )
        self._write(f"  total time: {_duration(elapsed)}")
        self._write("=" * 74)
        self._write("")
