"""Build causal future targets for the range and binary signal models.

The signal target is a first-passage event with a candle-path guard:
for each starting candle, price must first reach the configured BUY or
SELL threshold without violating the starting candle's opposite extreme.
A HOLD label is never created.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ShadBotTrader.domain.ai.prediction_target import SignalClass
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle


@dataclass(frozen=True)
class RangeLabels:
    """Future high/low offsets, aligned to rows with complete futures."""

    high_offset: List[float]
    low_offset: List[float]
    source_index: List[int]

    def __len__(self) -> int:
        return len(self.high_offset)

    @property
    def is_empty(self) -> bool:
        return not self.high_offset


@dataclass(frozen=True)
class SignalLabels:
    """Binary labels created by the first valid threshold event."""

    labels: List[int]
    source_index: List[int]
    forward_return: List[float]
    hit_index: List[int]
    bars_to_hit: List[int]

    def __len__(self) -> int:
        return len(self.labels)

    @property
    def is_empty(self) -> bool:
        return not self.labels

    def distribution(self) -> Dict[str, int]:
        counts = {item.label: 0 for item in SignalClass}
        for value in self.labels:
            counts[SignalClass.from_index(value).label] += 1
        return counts

    def is_degenerate(self, minimum_share: float = 0.02) -> bool:
        if not self.labels:
            return True
        total = len(self.labels)
        return any(count / total < minimum_share for count in self.distribution().values())


class _ExtremaIndex:
    """Segment tree for earliest future values crossing a threshold."""

    def __init__(self, values: Sequence[float], want_max: bool) -> None:
        self._values = list(values)
        self._want_max = want_max
        neutral = float("-inf") if want_max else float("inf")
        size = 1
        while size < len(self._values):
            size *= 2
        self._size = size
        self._tree = [neutral] * (2 * size)
        self._tree[size : size + len(self._values)] = self._values
        for index in range(size - 1, 0, -1):
            left, right = self._tree[index * 2 : index * 2 + 2]
            self._tree[index] = max(left, right) if want_max else min(left, right)

    def _crosses(self, value: float, threshold: float, strict: bool) -> bool:
        if self._want_max:
            return value > threshold if strict else value >= threshold
        return value < threshold if strict else value <= threshold

    def _can_contain(self, node_value: float, threshold: float, strict: bool) -> bool:
        return self._crosses(node_value, threshold, strict)

    def first_crossing(
        self,
        start: int,
        stop: int,
        threshold: float,
        strict: bool = False,
    ) -> Optional[int]:
        """Earliest index in ``[start, stop)`` crossing the threshold."""
        if start >= stop or start >= len(self._values):
            return None
        stop = min(stop, len(self._values))

        def visit(node: int, left: int, right: int) -> Optional[int]:
            if right <= start or left >= stop:
                return None
            if left + 1 == right:
                return left if self._can_contain(self._tree[node], threshold, strict) else None
            if left >= start and right <= stop:
                if not self._can_contain(self._tree[node], threshold, strict):
                    return None
            middle = (left + right) // 2
            found = visit(node * 2, left, middle)
            return found if found is not None else visit(node * 2 + 1, middle, right)

        result = visit(1, 0, self._size)
        return result if result is not None and result < stop else None


def _validate(candles: Sequence[Candle], horizon: int) -> None:
    if horizon < 1:
        raise ValidationError("horizon must be >= 1 candle")
    if len(candles) <= horizon:
        raise ValidationError(
            f"Need more than {horizon} candles to label a {horizon}-candle "
            f"horizon; got {len(candles)}."
        )


def build_range_labels(candles: Sequence[Candle], horizon: int = 5) -> RangeLabels:
    """Label the highest high and lowest low of the next N bars."""
    _validate(candles, horizon)
    highs: List[float] = []
    lows: List[float] = []
    indices: List[int] = []

    for index in range(len(candles) - horizon):
        close = float(candles[index].close.amount)
        if close <= 0:
            raise ValidationError(f"Candle {index} has a non-positive close")
        window = candles[index + 1 : index + 1 + horizon]
        future_high = max(float(candle.high.amount) for candle in window)
        future_low = min(float(candle.low.amount) for candle in window)
        highs.append((future_high - close) / close)
        lows.append((future_low - close) / close)
        indices.append(index)

    return RangeLabels(high_offset=highs, low_offset=lows, source_index=indices)


def build_range_labels_seq2seq(
    candles: Sequence[Candle],
    horizon: int = 5,
) -> "RangeLabelsSeq2Seq":
    """Seq2seq targets: برای هر کندل t، high و low در t+1 .. t+horizon.

    فاز ۵۵: بجای یک scalar، برای هر کندل در window یه target داریم.
    این gradient flow رو 75× قوی‌تر می‌کنه و collapse رو جلوگیری می‌کنه.

    horizon=1 (پیشنهاد نهایی):
      high_seq[t][0] = (high[t+1] - close[t]) / close[t]
      low_seq[t][0]  = (low[t+1]  - close[t]) / close[t]
      → پیش‌بینی high و low فردا (دقیق‌ترین حالت)
      → target واضح، بدون accumulation error

    horizon=N (عمومی):
      high_seq[t, k] = (high[t+k] - close[t]) / close[t]   k=1..N
      low_seq[t, k]  = (low[t+k]  - close[t]) / close[t]   k=1..N

    Loss فقط روی آخرین horizon timestep seq اعمال میشه (با وزن بیشتر).
    """
    _validate(candles, horizon)

    # برای هر کندل t، offsets تا horizon کندل بعد
    high_seqs: List[List[float]] = []
    low_seqs: List[List[float]] = []
    indices: List[int] = []

    n = len(candles)
    for t in range(n - horizon):
        close_t = float(candles[t].close.amount)
        if close_t <= 0:
            raise ValidationError(f"Candle {t} has non-positive close")
        h_seq = []
        l_seq = []
        for k in range(1, horizon + 1):
            future = candles[t + k]
            h_seq.append((float(future.high.amount)  - close_t) / close_t)
            l_seq.append((float(future.low.amount)   - close_t) / close_t)
        high_seqs.append(h_seq)
        low_seqs.append(l_seq)
        indices.append(t)

    return RangeLabelsSeq2Seq(
        high_seq=high_seqs,
        low_seq=low_seqs,
        source_index=indices,
        horizon=horizon,
    )


@dataclass(frozen=True)
class RangeLabelsSeq2Seq:
    """Seq2seq range labels: برای هر کندل t، offset هر k=1..horizon."""

    high_seq: List[List[float]]   # shape [N, horizon]
    low_seq:  List[List[float]]   # shape [N, horizon]
    source_index: List[int]
    horizon: int

    def __len__(self) -> int:
        return len(self.high_seq)

    @property
    def is_empty(self) -> bool:
        return not self.high_seq

    def to_flat_targets(self) -> List[List[float]]:
        """[high_1, low_1, high_2, low_2, ..., high_H, low_H] برای هر کندل."""
        result = []
        for h_seq, l_seq in zip(self.high_seq, self.low_seq):
            flat = []
            for h, l in zip(h_seq, l_seq):
                flat.append(h)
                flat.append(l)
            result.append(flat)
        return result

    def target_names(self) -> List[str]:
        names = []
        for k in range(1, self.horizon + 1):
            names.append(f"future_high_offset_{k}")
            names.append(f"future_low_offset_{k}")
        return names


def build_signal_labels_from_candles(
    candles: Sequence[Candle],
    threshold: float = 0.0008,
    max_lookahead: Optional[int] = None,
) -> SignalLabels:
    """Build path-aware labels from full OHLC candles.

    BUY is valid only if the first future Close reaching the upper target
    occurs before any future Low falls below the starting candle's Low.
    SELL is the exact inverse: the lower target must occur before any
    future High rises above the starting candle's High.
    """
    if not candles:
        raise ValidationError("candles must not be empty")
    if threshold <= 0:
        raise ValidationError("threshold must be positive")
    if max_lookahead is not None and max_lookahead < 1:
        raise ValidationError("max_lookahead must be >= 1 when provided")

    closes = [float(candle.close.amount) for candle in candles]
    highs = [float(candle.high.amount) for candle in candles]
    lows = [float(candle.low.amount) for candle in candles]
    return _build_first_passage_labels(closes, highs, lows, threshold, max_lookahead)


def _build_first_passage_labels(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    threshold: float,
    max_lookahead: Optional[int],
) -> SignalLabels:
    if not closes:
        raise ValidationError("closes must not be empty")
    if len(closes) != len(highs) or len(closes) != len(lows):
        raise ValidationError("closes, highs and lows must have equal length")
    if threshold <= 0:
        raise ValidationError("threshold must be positive")
    if any(close <= 0 for close in closes):
        raise ValidationError("all candle closes must be positive")

    close_max = _ExtremaIndex(closes, want_max=True)
    close_min = _ExtremaIndex(closes, want_max=False)
    high_max = _ExtremaIndex(highs, want_max=True)
    low_min = _ExtremaIndex(lows, want_max=False)

    labels: Dict[int, int] = {}
    hits: Dict[int, int] = {}
    returns: Dict[int, float] = {}
    distances: Dict[int, int] = {}
    total = len(closes)

    for start in range(total - 1):
        stop = total if max_lookahead is None else min(total, start + max_lookahead + 1)
        upper = closes[start] * (1.0 + threshold)
        lower = closes[start] * (1.0 - threshold)

        buy_hit = close_max.first_crossing(start + 1, stop, upper)
        buy_invalid = low_min.first_crossing(start + 1, stop, lows[start], strict=True)
        if buy_hit is not None and buy_invalid is not None and buy_invalid <= buy_hit:
            buy_hit = None

        sell_hit = close_min.first_crossing(start + 1, stop, lower)
        sell_invalid = high_max.first_crossing(start + 1, stop, highs[start], strict=True)
        if sell_hit is not None and sell_invalid is not None and sell_invalid <= sell_hit:
            sell_hit = None

        candidates = [(index, SignalClass.BUY) for index in (buy_hit,) if index is not None] + [
            (index, SignalClass.SELL) for index in (sell_hit,) if index is not None
        ]
        if not candidates:
            continue

        hit_index, label = min(candidates, key=lambda item: item[0])
        labels[start] = int(label)
        hits[start] = hit_index
        returns[start] = (closes[hit_index] - closes[start]) / closes[start]
        distances[start] = hit_index - start

    source_index = sorted(labels)
    return SignalLabels(
        labels=[labels[index] for index in source_index],
        source_index=source_index,
        forward_return=[returns[index] for index in source_index],
        hit_index=[hits[index] for index in source_index],
        bars_to_hit=[distances[index] for index in source_index],
    )


def build_signal_labels_from_closes(
    closes: Sequence[float],
    threshold: float = 0.0008,
    max_lookahead: Optional[int] = None,
) -> SignalLabels:
    """Build first-passage labels from closes when OHLC guards are absent.

    Evaluation matrices do not retain absolute candle highs/lows, so this
    fallback uses the close series for both path guards. Live/training
    dataset construction should call :func:`build_signal_labels_from_candles`.
    """
    return _build_first_passage_labels(
        closes,
        highs=closes,
        lows=closes,
        threshold=threshold,
        max_lookahead=max_lookahead,
    )


def build_signal_labels_from_ohlc(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    threshold: float = 0.0008,
    max_lookahead: Optional[int] = None,
) -> SignalLabels:
    """Build path-aware first-passage labels from reconstructed OHLC series.

    مثل training: از high و low واقعی هر کندل استفاده میکنه.
    برای evaluate که matrix داره (high_rel, low_rel).
    """
    return _build_first_passage_labels(
        closes,
        highs=highs,
        lows=lows,
        threshold=threshold,
        max_lookahead=max_lookahead,
    )


def build_signal_labels(
    candles: Sequence[Candle],
    horizon: int = 0,
    threshold: float = 0.0008,
    max_lookahead: Optional[int] = None,
) -> SignalLabels:
    """Build path-aware binary labels from OHLC candles.

    With the default zero horizon, search continues until a barrier is
    hit or the series ends. ``horizon`` remains a compatibility alias for
    a finite maximum lookahead.
    """
    if max_lookahead is None and horizon > 0:
        max_lookahead = horizon
    return build_signal_labels_from_candles(
        candles, threshold=threshold, max_lookahead=max_lookahead
    )


def usable_row_count(total_candles: int, horizon: int) -> int:
    """Rows that survive a finite horizon; retained for range callers."""
    return max(total_candles - horizon, 0)


def align_to_labels(
    rows: Sequence[Sequence[float]],
    source_index: Sequence[int],
) -> Tuple[List[List[float]], List[int]]:
    """Keep feature rows matching the original candle indices."""
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
