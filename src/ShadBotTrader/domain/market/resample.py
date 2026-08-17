"""Aggregate candles into a larger timeframe (Phase 39).

A broker that serves 1H bars will usually serve 1D bars too, so this is
not the primary way to obtain daily data — ``Fetch market data`` with
``1D`` in the timeframe list is. This exists for the case the operator
actually hits: years of 1H history already downloaded, and a daily model
to train today.

The aggregation itself is the only part that can be got subtly wrong, so
it is written out explicitly:

    open   = the open of the FIRST candle in the bucket
    high   = the maximum high across the bucket
    low    = the minimum low across the bucket
    close  = the close of the LAST candle in the bucket
    volume = the sum

Two rules that are easy to skip and expensive to miss:

**Incomplete buckets are dropped.** The final day of a 1H series is
almost always partial — six hours of a twenty-four hour bar. Emitting it
would hand the model a "day" whose high and low are not the day's high
and low, and the error is invisible because the row looks normal. The
caller is told how many were dropped rather than left to wonder.

**Gaps do not merge.** Candles are bucketed by calendar date in UTC, not
by counting. A weekend produces no bucket instead of silently welding
Friday to Monday.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp

#: Minutes in each timeframe this module can produce.
_TARGET_MINUTES: Dict[str, int] = {
    "1H": 60,
    "4H": 240,
    "1D": 1440,
}


@dataclass
class ResampleResult:
    """Aggregated candles plus what had to be discarded."""

    candles: List[Candle] = field(default_factory=list)
    source_count: int = 0
    dropped_incomplete: int = 0
    expected_per_bucket: int = 0

    @property
    def count(self) -> int:
        return len(self.candles)

    def summary_lines(self) -> List[str]:
        lines = [
            f"source candles : {self.source_count:,}",
            f"aggregated     : {self.count:,}",
        ]
        if self.dropped_incomplete:
            lines.append(
                f"dropped        : {self.dropped_incomplete} incomplete bucket(s) "
                f"(fewer than {self.expected_per_bucket} source candles)"
            )
        return lines


def _bucket_key(moment: datetime, target: str) -> date | datetime:
    """The bucket a candle belongs to."""
    moment = moment.astimezone(timezone.utc)
    if target == "1D":
        return moment.date()
    minutes = _TARGET_MINUTES[target]
    floored = moment.replace(minute=0, second=0, microsecond=0)
    if minutes >= 60:
        hours = minutes // 60
        floored = floored.replace(hour=(floored.hour // hours) * hours)
    return floored


def _bucket_open_time(key: date | datetime) -> datetime:
    if isinstance(key, datetime):
        return key
    return datetime(key.year, key.month, key.day, tzinfo=timezone.utc)


def resample_candles(
    candles: Sequence[Candle],
    target: str,
    source: Optional[str] = None,
    min_completeness: float = 0.5,
    drop_incomplete_last: bool = True,
) -> ResampleResult:
    """Aggregate ``candles`` into ``target`` bars.

    Args:
        min_completeness: a bucket is kept only when it holds at least
            this fraction of the candles a full bucket would have. Gold
            trades roughly 23 hours a day, so a strict 24/24 rule would
            discard every day; 0.5 keeps real days and rejects stubs.
        drop_incomplete_last: always drop a trailing partial bucket. The
            last "day" of an intraday series is the one most likely to be
            half-formed, and it is the one the model would weight most.
    """
    target = target.strip().upper()
    if target not in _TARGET_MINUTES:
        raise ValidationError(
            f"Cannot resample to {target!r}. Supported: {', '.join(sorted(_TARGET_MINUTES))}"
        )
    if not candles:
        return ResampleResult(source_count=0)

    source_label = source or str(candles[0].timeframe)
    source_minutes = _timeframe_minutes(source_label)
    target_minutes = _TARGET_MINUTES[target]
    if source_minutes >= target_minutes:
        raise ValidationError(
            f"Cannot resample {source_label} into {target}: the source must be finer."
        )

    expected = max(1, target_minutes // source_minutes)
    symbol: Symbol = candles[0].symbol
    frame = Timeframe(target)

    buckets: Dict[Any, List[Candle]] = {}
    order: List[Any] = []
    for candle in sorted(candles, key=lambda item: item.open_time.value):
        key = _bucket_key(candle.open_time.value, target)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(candle)

    result = ResampleResult(source_count=len(candles), expected_per_bucket=expected)
    threshold = max(1, int(expected * min_completeness))

    for index, key in enumerate(order):
        group = buckets[key]
        is_last = index == len(order) - 1
        if len(group) < threshold or (is_last and drop_incomplete_last and len(group) < expected):
            result.dropped_incomplete += 1
            continue

        result.candles.append(
            Candle(
                symbol=symbol,
                timeframe=frame,
                open_time=Timestamp(_bucket_open_time(key)),
                open_price=Price(group[0].open.amount),
                high=Price(max(item.high.amount for item in group)),
                low=Price(min(item.low.amount for item in group)),
                close=Price(group[-1].close.amount),
                volume=sum((item.volume for item in group), Decimal("0")),
            )
        )

    return result


def _timeframe_minutes(label: str) -> int:
    """Minutes in a timeframe label such as ``5M``, ``1H`` or ``1D``."""
    frame = Timeframe(label)
    text = str(frame).strip().upper()
    digits = "".join(character for character in text if character.isdigit())
    amount = int(digits) if digits else 1
    if text.endswith("M"):
        return amount
    if text.endswith("H"):
        return amount * 60
    if text.endswith("D"):
        return amount * 1440
    if text.endswith("W"):
        return amount * 10080
    raise ValidationError(f"Cannot express {label!r} in minutes")


def resample_span(candles: Sequence[Candle]) -> timedelta:
    """The wall-clock span a candle series covers."""
    if len(candles) < 2:
        return timedelta(0)
    return candles[-1].open_time.value - candles[0].open_time.value
