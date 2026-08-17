"""Candle continuity and a market calendar learned from the data (Phase 33).

Appending new candles to a stored history is where a dataset quietly
breaks. If the last stored bar is Monday 10 July and the first new bar is
Thursday 13 July, two trading days are missing — and nothing downstream
will ever notice. Features are computed over the joined series, the model
learns from a discontinuity that never happened in the market, and the
backtest looks fine.

The hard part is telling a **real** gap from a **normal** one. Markets
close at weekends and on holidays, so "no candle on Saturday" is not
missing data. Rather than hard-coding a calendar (which is wrong for
crypto, wrong for a broker in another timezone, and stale within a year),
this module *learns* the trading rhythm from the history it already has:

    if the last 200 Saturdays had no candles, Saturday is a closed day

That adapts to any instrument and any broker automatically, and it is
falsifiable: the evidence is right there in the stored data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.timeframe import Timeframe, TimeframeUnit

#: A weekday is treated as closed when this share of its occurrences had
#: no candles at all. Deliberately strict: mislabelling a trading day as
#: a holiday would hide genuinely missing data.
CLOSED_DAY_THRESHOLD = 0.9

#: Minimum observations of a weekday before any judgement is made.
MIN_OBSERVATIONS = 3


def timeframe_delta(timeframe: Timeframe) -> timedelta:
    """The nominal spacing between two consecutive candles."""
    if timeframe.unit is TimeframeUnit.MINUTE:
        return timedelta(minutes=timeframe.amount)
    if timeframe.unit is TimeframeUnit.HOUR:
        return timedelta(hours=timeframe.amount)
    return timedelta(days=timeframe.amount)


@dataclass
class MarketCalendar:
    """Which weekdays this instrument actually trades on.

    Learned from observed candles rather than declared, so it fits any
    broker and any asset class without configuration.
    """

    closed_weekdays: Set[int] = field(default_factory=set)
    observed_days: int = 0
    evidence: Dict[int, Tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def learn(cls, candles: Sequence[Candle]) -> "MarketCalendar":
        """Infer the trading rhythm from a candle history.

        A weekday counts as closed when almost every occurrence of it in
        the history carried no candle at all.
        """
        if not candles:
            return cls()

        ordered = sorted(candles, key=lambda candle: candle.open_time.value)
        first = ordered[0].open_time.value.date()
        last = ordered[-1].open_time.value.date()

        with_candles: Set[Any] = {candle.open_time.value.date() for candle in ordered}

        seen: Dict[int, int] = defaultdict(int)
        traded: Dict[int, int] = defaultdict(int)
        cursor = first
        while cursor <= last:
            seen[cursor.weekday()] += 1
            if cursor in with_candles:
                traded[cursor.weekday()] += 1
            cursor += timedelta(days=1)

        closed: Set[int] = set()
        evidence: Dict[int, Tuple[int, int]] = {}
        for weekday in range(7):
            total = seen.get(weekday, 0)
            active = traded.get(weekday, 0)
            evidence[weekday] = (active, total)
            if total < MIN_OBSERVATIONS:
                continue
            if (total - active) / total >= CLOSED_DAY_THRESHOLD:
                closed.add(weekday)

        return cls(
            closed_weekdays=closed,
            observed_days=(last - first).days + 1,
            evidence=evidence,
        )

    def is_closed(self, moment: datetime) -> bool:
        return moment.weekday() in self.closed_weekdays

    def is_open(self, moment: datetime) -> bool:
        return not self.is_closed(moment)

    @property
    def is_confident(self) -> bool:
        """True once there is enough history to trust the pattern."""
        return self.observed_days >= 14

    def expected_slots(
        self,
        start: datetime,
        end: datetime,
        timeframe: Timeframe,
    ) -> int:
        """How many candles *should* exist strictly between two moments.

        Slots falling on closed days are not counted, which is what makes
        a weekend gap read as zero missing candles.
        """
        if end <= start:
            return 0

        step = timeframe_delta(timeframe)
        expected = 0
        cursor = start + step
        # Guard against a pathological range producing an endless loop.
        limit = 500_000
        while cursor < end and expected < limit:
            if self.is_open(cursor):
                expected += 1
            cursor += step
        return expected

    def describe(self) -> str:
        if not self.closed_weekdays:
            return "trades every day (no closed weekday detected)"
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        closed = ", ".join(names[day] for day in sorted(self.closed_weekdays))
        return f"closed on {closed}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "closed_weekdays": sorted(self.closed_weekdays),
            "observed_days": self.observed_days,
            "confident": self.is_confident,
            "description": self.describe(),
        }


@dataclass
class Gap:
    """A stretch of missing candles."""

    after: datetime
    before: datetime
    missing: int
    timeframe: str

    @property
    def duration(self) -> timedelta:
        return self.before - self.after

    def describe(self) -> str:
        return (
            f"{self.missing} candle(s) missing between "
            f"{self.after.isoformat()} and {self.before.isoformat()}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "after": self.after.isoformat(),
            "before": self.before.isoformat(),
            "missing": self.missing,
            "hours": round(self.duration.total_seconds() / 3600, 2),
            "timeframe": self.timeframe,
        }


@dataclass
class ContinuityReport:
    """Whether a series joins up, and where it does not."""

    timeframe: str
    candle_count: int = 0
    duplicates: int = 0
    out_of_order: int = 0
    gaps: List[Gap] = field(default_factory=list)
    calendar: MarketCalendar = field(default_factory=MarketCalendar)
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None

    @property
    def is_continuous(self) -> bool:
        return not self.gaps and not self.duplicates and not self.out_of_order

    @property
    def missing_candles(self) -> int:
        return sum(gap.missing for gap in self.gaps)

    @property
    def largest_gap(self) -> Optional[Gap]:
        return max(self.gaps, key=lambda gap: gap.missing) if self.gaps else None

    def summary_lines(self) -> List[str]:
        lines = [
            f"candles      : {self.candle_count:,}",
            f"calendar     : {self.calendar.describe()}",
        ]
        if self.first_time and self.last_time:
            lines.append(
                f"range        : {self.first_time.isoformat()} .. " f"{self.last_time.isoformat()}"
            )
        if self.is_continuous:
            lines.append("continuity   : OK — no gaps, duplicates or disorder")
            return lines

        if self.duplicates:
            lines.append(f"duplicates   : {self.duplicates}")
        if self.out_of_order:
            lines.append(f"out of order : {self.out_of_order}")
        if self.gaps:
            lines.append(
                f"gaps         : {len(self.gaps)} " f"({self.missing_candles:,} candles missing)"
            )
            for gap in self.gaps[:5]:
                lines.append(f"   - {gap.describe()}")
            if len(self.gaps) > 5:
                lines.append(f"   ... and {len(self.gaps) - 5} more")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "candle_count": self.candle_count,
            "continuous": self.is_continuous,
            "duplicates": self.duplicates,
            "out_of_order": self.out_of_order,
            "gap_count": len(self.gaps),
            "missing_candles": self.missing_candles,
            "gaps": [gap.to_dict() for gap in self.gaps],
            "calendar": self.calendar.to_dict(),
            "first_time": self.first_time.isoformat() if self.first_time else None,
            "last_time": self.last_time.isoformat() if self.last_time else None,
        }


def analyse_continuity(
    candles: Sequence[Candle],
    timeframe: Timeframe,
    calendar: Optional[MarketCalendar] = None,
    tolerance: int = 0,
) -> ContinuityReport:
    """Check that a candle series joins up end to end.

    ``tolerance`` allows a small number of missing candles to pass
    without being reported — brokers occasionally drop a single bar and
    treating that as corruption would block every update.
    """
    report = ContinuityReport(timeframe=str(timeframe))
    if not candles:
        return report

    ordered = sorted(candles, key=lambda candle: candle.open_time.value)
    report.candle_count = len(ordered)
    report.first_time = ordered[0].open_time.value
    report.last_time = ordered[-1].open_time.value
    report.calendar = calendar or MarketCalendar.learn(ordered)

    # Disorder is measured on the ORIGINAL sequence: sorting hides it.
    previous_raw: Optional[datetime] = None
    for candle in candles:
        current = candle.open_time.value
        if previous_raw is not None and current < previous_raw:
            report.out_of_order += 1
        previous_raw = current

    seen: Set[datetime] = set()
    for candle in ordered:
        moment = candle.open_time.value
        if moment in seen:
            report.duplicates += 1
        seen.add(moment)

    step = timeframe_delta(timeframe)
    for earlier_candle, later_candle in zip(ordered, ordered[1:], strict=False):
        earlier = earlier_candle.open_time.value
        later = later_candle.open_time.value
        if later - earlier <= step:
            continue  # consecutive, or a duplicate already counted

        missing = report.calendar.expected_slots(earlier, later, timeframe)
        if missing > tolerance:
            report.gaps.append(
                Gap(
                    after=earlier,
                    before=later,
                    missing=missing,
                    timeframe=str(timeframe),
                )
            )

    return report


def check_join(
    existing: Sequence[Candle],
    incoming: Sequence[Candle],
    timeframe: Timeframe,
    calendar: Optional[MarketCalendar] = None,
    tolerance: int = 0,
) -> Optional[Gap]:
    """The gap between the end of ``existing`` and the start of ``incoming``.

    This is the check that matters when updating a dataset a month later:
    the last stored candle must be immediately followed by the first new
    one, allowing for closed market days. Returns ``None`` when they join
    cleanly.
    """
    if not existing or not incoming:
        return None

    last_stored = max(candle.open_time.value for candle in existing)
    first_new = min(candle.open_time.value for candle in incoming)

    if first_new <= last_stored:
        return None  # overlap, not a gap — the caller de-duplicates

    step = timeframe_delta(timeframe)
    if first_new - last_stored <= step:
        return None

    market = calendar or MarketCalendar.learn(existing)
    missing = market.expected_slots(last_stored, first_new, timeframe)
    if missing <= tolerance:
        return None

    return Gap(
        after=last_stored,
        before=first_new,
        missing=missing,
        timeframe=str(timeframe),
    )


def merge_candles(
    existing: Sequence[Candle],
    incoming: Sequence[Candle],
    max_candles: Optional[int] = None,
) -> List[Candle]:
    """Combine two series into one ordered, de-duplicated history.

    Where both contain the same timestamp the **incoming** candle wins:
    a re-fetched bar is a correction, and the newest read of a bar that
    was still forming is the accurate one.

    ``max_candles`` keeps only the most recent N, which is how a rolling
    100,000-candle dataset stays bounded.
    """
    if max_candles is not None and max_candles < 1:
        raise ValidationError("max_candles must be >= 1")

    by_time: Dict[datetime, Candle] = {candle.open_time.value: candle for candle in existing}
    for candle in incoming:
        by_time[candle.open_time.value] = candle

    merged = [by_time[key] for key in sorted(by_time)]
    if max_candles is not None and len(merged) > max_candles:
        merged = merged[-max_candles:]
    return merged
