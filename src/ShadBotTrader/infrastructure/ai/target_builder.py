"""Label the future for both Phase 29 models.

Every label here looks forward by construction, which is exactly where
time-series projects leak. Three rules are enforced and individually
tested (Phase 29 §4):

R1  The label for row ``t`` is computed from bars ``t+1 .. t+N``. Row
    ``t`` contributes only ``close[t]``, which is known when the
    decision is made.
R2  The final ``N`` rows have an incomplete future window and are
    **dropped**. Padding or clipping them would invent outcomes the
    market never produced — the classic mistake that makes a backtest
    look profitable and live trading lose money.
R3  Target columns never enter the feature matrix (enforced downstream
    by ``drop_target_column``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ShadBotTrader.domain.ai.prediction_target import SignalClass
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle


@dataclass(frozen=True)
class RangeLabels:
    """Future high/low offsets, aligned to the rows that survived R2."""

    high_offset: List[float]
    low_offset: List[float]
    #: Index in the ORIGINAL candle series each label belongs to.
    source_index: List[int]

    def __len__(self) -> int:
        return len(self.high_offset)

    @property
    def is_empty(self) -> bool:
        return not self.high_offset


@dataclass(frozen=True)
class SignalLabels:
    """Three-class labels, aligned to the rows that survived R2."""

    labels: List[int]
    source_index: List[int]
    #: Forward return that produced each label, kept for auditing.
    forward_return: List[float]

    def __len__(self) -> int:
        return len(self.labels)

    @property
    def is_empty(self) -> bool:
        return not self.labels

    def distribution(self) -> dict[str, int]:
        """How many of each class — the first thing to check on real data."""
        counts = {item.label: 0 for item in SignalClass}
        for value in self.labels:
            counts[SignalClass.from_index(value).label] += 1
        return counts

    def is_degenerate(self, minimum_share: float = 0.02) -> bool:
        """True when some class is effectively absent.

        A model trained on a series that is 99% HOLD will learn to
        answer HOLD forever and score well doing it. Detecting that is
        more useful than reporting a flattering accuracy.
        """
        if not self.labels:
            return True
        total = len(self.labels)
        return any(count / total < minimum_share for count in self.distribution().values())


def _validate(candles: Sequence[Candle], horizon: int) -> None:
    if horizon < 1:
        raise ValidationError("horizon must be >= 1 candle")
    if len(candles) <= horizon:
        raise ValidationError(
            f"Need more than {horizon} candles to label a {horizon}-candle "
            f"horizon; got {len(candles)}."
        )


def build_range_labels(candles: Sequence[Candle], horizon: int = 5) -> RangeLabels:
    """Label the highest high and lowest low of the next ``horizon`` bars.

    Offsets are fractions of the current close, so the target does not
    drift with the price level (Phase 29 §2.1).
    """
    _validate(candles, horizon)

    highs: List[float] = []
    lows: List[float] = []
    indices: List[int] = []

    # R2: stop at len - horizon so every window is complete.
    for index in range(len(candles) - horizon):
        close = float(candles[index].close.amount)
        if close <= 0:
            raise ValidationError(f"Candle {index} has a non-positive close")

        # R1: the window starts at index + 1 — the current bar is excluded.
        window = candles[index + 1 : index + 1 + horizon]
        future_high = max(float(candle.high.amount) for candle in window)
        future_low = min(float(candle.low.amount) for candle in window)

        highs.append((future_high - close) / close)
        lows.append((future_low - close) / close)
        indices.append(index)

    return RangeLabels(high_offset=highs, low_offset=lows, source_index=indices)


def build_signal_labels(
    candles: Sequence[Candle],
    horizon: int = 5,
    threshold: float = 0.0008,
) -> SignalLabels:
    """Label each bar sell / hold / buy over the next ``horizon`` bars.

    The label is driven by the forward return of the close. Moves inside
    the neutral band become HOLD, which is what stops the model from
    being forced to trade noise.

    ``threshold`` must exceed the round-trip cost, otherwise the model is
    trained to chase moves that cannot survive spread and commission.
    """
    _validate(candles, horizon)
    if threshold <= 0:
        raise ValidationError("threshold must be positive")

    labels: List[int] = []
    indices: List[int] = []
    returns: List[float] = []

    for index in range(len(candles) - horizon):
        close = float(candles[index].close.amount)
        if close <= 0:
            raise ValidationError(f"Candle {index} has a non-positive close")

        future_close = float(candles[index + horizon].close.amount)
        forward = (future_close - close) / close

        if forward > threshold:
            label = SignalClass.BUY
        elif forward < -threshold:
            label = SignalClass.SELL
        else:
            label = SignalClass.HOLD

        labels.append(int(label))
        indices.append(index)
        returns.append(forward)

    return SignalLabels(labels=labels, source_index=indices, forward_return=returns)


def usable_row_count(total_candles: int, horizon: int) -> int:
    """Rows that survive R2 — how much training data a horizon leaves."""
    return max(total_candles - horizon, 0)


def align_to_labels(
    rows: Sequence[Sequence[float]],
    source_index: Sequence[int],
) -> Tuple[List[List[float]], List[int]]:
    """Keep only the feature rows that have a label, preserving order.

    Feature computation and labelling each drop rows for their own
    reasons (warm-up at the start, incomplete future at the end). This
    is the single place the two are reconciled, so a mismatch cannot
    silently shift labels against features by one bar.
    """
    available = {index: row for index, row in enumerate(rows)}
    aligned: List[List[float]] = []
    kept: List[int] = []
    for position, index in enumerate(source_index):
        row = available.get(index)
        if row is None:
            continue
        aligned.append(list(row))
        kept.append(position)
    return aligned, kept
