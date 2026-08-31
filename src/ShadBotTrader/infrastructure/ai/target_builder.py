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
    """Future high/low offsets, aligned to rows with complete futures.

    ``units`` declares the normalization of the offsets:

    * ``"pct"`` — fraction of the current close (legacy models);
    * ``"atr"`` — multiples of ATR(period) at the current candle
      (فاز ۹۵). The constant-offset collapse of the pct target came
      from a scale-blind input plus a scale-blind target; ATR units
      give the model a volatility-scaled, regime-aware question.
    """

    high_offset: List[float]
    low_offset: List[float]
    source_index: List[int]
    units: str = "pct"

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


def wilder_atr_series(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> List[float]:
    """Causal Wilder ATR for every candle (فاز ۹۵).

    TR[0] = high−low; TR[t] = max(high−low, |high−close[t−1]|, |low−close[t−1]|).
    For the first ``period`` candles the ATR is the expanding mean of the
    TRs seen so far (a total, causal definition); from candle ``period``
    on it is the classic Wilder smoothing
    ``atr = (prev·(period−1) + TR) / period`` seeded with the mean of the
    first ``period`` TRs.

    Training labels and inference must both call **this** function so the
    normalization at label time and the de-normalization at forecast time
    agree exactly.
    """
    if period < 1:
        raise ValidationError("ATR period must be >= 1")
    n = len(closes)
    if not (len(highs) == len(lows) == n):
        raise ValidationError("highs, lows and closes must have equal length")
    if n == 0:
        return []

    atr: List[float] = []
    tr_sum = 0.0
    previous_close: Optional[float] = None
    for index in range(n):
        high = float(highs[index])
        low = float(lows[index])
        close = float(closes[index])
        true_range = high - low
        if previous_close is not None:
            true_range = max(
                true_range,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        previous_close = close

        if index < period:
            tr_sum += true_range
            atr.append(tr_sum / (index + 1))
        else:
            smoothed = (atr[index - 1] * (period - 1) + true_range) / period
            atr.append(smoothed)
    return atr


def atr_from_candles(candles: Sequence[Candle], period: int = 14) -> Optional[float]:
    """ATR of the **last** candle of ``candles`` (causal — uses only history).

    Returns ``None`` for an empty slice. This is the value that de-normalizes
    an ATR-unit forecast back into dollars at inference time; it must be
    computed on candles up to and including the reference candle, never beyond.
    """
    if not candles:
        return None
    highs = [float(candle.high.amount) for candle in candles]
    lows = [float(candle.low.amount) for candle in candles]
    closes = [float(candle.close.amount) for candle in candles]
    return wilder_atr_series(highs, lows, closes, period=period)[-1]


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


def build_range_labels(
    candles: Sequence[Candle],
    horizon: int = 5,
    units: str = "atr",
    atr_period: int = 14,
) -> RangeLabels:
    """Label the highest high and lowest low of the next N bars.

    ``units="atr"`` (فاز ۹۵): offsets are ATR multiples,
    ``(high[t+k] − close[t]) / ATR_period[t]``. ``units="pct"`` keeps the
    legacy fraction-of-close target for comparisons and old models.
    """
    _validate(candles, horizon)
    if units not in ("pct", "atr"):
        raise ValidationError(f"Unknown range target units: {units!r} (use 'pct' or 'atr')")
    highs: List[float] = []
    lows: List[float] = []
    indices: List[int] = []

    close_series = [float(candle.close.amount) for candle in candles]
    high_series = [float(candle.high.amount) for candle in candles]
    low_series = [float(candle.low.amount) for candle in candles]
    atr = (
        wilder_atr_series(high_series, low_series, close_series, period=atr_period)
        if units == "atr"
        else None
    )

    for index in range(len(candles) - horizon):
        close = close_series[index]
        if close <= 0:
            raise ValidationError(f"Candle {index} has a non-positive close")
        window = candles[index + 1 : index + 1 + horizon]
        future_high = max(float(candle.high.amount) for candle in window)
        future_low = min(float(candle.low.amount) for candle in window)
        if units == "atr":
            scale = atr[index]
            if scale is None or scale <= 0:
                raise ValidationError(
                    f"ATR is zero at candle {index}; cannot build ATR-normalized "
                    "labels from a flat price series"
                )
            highs.append((future_high - close) / scale)
            lows.append((future_low - close) / scale)
        else:
            highs.append((future_high - close) / close)
            lows.append((future_low - close) / close)
        indices.append(index)

    return RangeLabels(high_offset=highs, low_offset=lows, source_index=indices, units=units)


def build_range_labels_seq2seq(
    candles: Sequence[Candle],
    horizon: int = 5,
    units: str = "atr",
    atr_period: int = 14,
) -> "RangeLabelsSeq2Seq":
    """Seq2seq targets: برای هر کندل t، offset هر k=1..horizon.

    فاز ۵۵: بجای یک scalar، برای هر کندل در window یه target داریم.
    این gradient flow رو 75× قوی‌تر میکنه و collapse رو جلوگیری میکنه.

    فاز ۹۵ — units="atr" (پیش‌فرض جدید):
      high_seq[t][k] = (high[t+k] − close[t]) / ATR_period[t]
      low_seq[t][k]  = (low[t+k]  − close[t]) / ATR_period[t]
      → مدل «چند ATR» پیش‌بینی میکنه، نه درصد خام. چون ATR خودش جزو
      فیچرهای ورودی هست، مدل میتونه رابطهٔ رژیم بازار → دامنهٔ حرکت رو
      یاد بگیره و خروجی دیگه برای همهٔ کندل‌ها ثابت نمیمونه.
      در مصرف: price = close + mult × ATR_14(همان کندل).

    units="pct" (رفتار قدیمی):
      high_seq[t][k] = (high[t+k] − close[t]) / close[t]

    horizon=1 (پیشنهاد نهایی):
      high_seq[t][0] = high و low فردا (دقیق‌ترین حالت)
      → target واضح، بدون accumulation error

    horizon=N (عمومی):
      high_seq[t, k] برای k=1..N

    Loss فقط روی آخرین horizon timestep seq اعمال میشه (با وزن بیشتر).
    """
    _validate(candles, horizon)
    if units not in ("pct", "atr"):
        raise ValidationError(f"Unknown range target units: {units!r} (use 'pct' or 'atr')")

    # برای هر کندل t، offsets تا horizon کندل بعد
    high_seqs: List[List[float]] = []
    low_seqs: List[List[float]] = []
    indices: List[int] = []

    close_series = [float(candle.close.amount) for candle in candles]
    high_series = [float(candle.high.amount) for candle in candles]
    low_series = [float(candle.low.amount) for candle in candles]
    atr = (
        wilder_atr_series(high_series, low_series, close_series, period=atr_period)
        if units == "atr"
        else None
    )

    n = len(candles)
    for t in range(n - horizon):
        close_t = close_series[t]
        if close_t <= 0:
            raise ValidationError(f"Candle {t} has non-positive close")
        if units == "atr":
            scale = atr[t]
            if scale is None or scale <= 0:
                raise ValidationError(
                    f"ATR is zero at candle {t}; cannot build ATR-normalized "
                    "labels from a flat price series"
                )
        else:
            scale = close_t
        h_seq = []
        l_seq = []
        for k in range(1, horizon + 1):
            future = candles[t + k]
            h_seq.append((float(future.high.amount) - close_t) / scale)
            l_seq.append((float(future.low.amount) - close_t) / scale)
        high_seqs.append(h_seq)
        low_seqs.append(l_seq)
        indices.append(t)

    return RangeLabelsSeq2Seq(
        high_seq=high_seqs,
        low_seq=low_seqs,
        source_index=indices,
        horizon=horizon,
        units=units,
    )


@dataclass(frozen=True)
class RangeLabelsSeq2Seq:
    """Seq2seq range labels: برای هر کندل t، offset هر k=1..horizon.

    ``units``: ``"atr"`` = ضرایب ATR (فاز ۹۵) یا ``"pct"`` = کسری از close (قدیمی).
    """

    high_seq: List[List[float]]  # shape [N, horizon]
    low_seq: List[List[float]]  # shape [N, horizon]
    source_index: List[int]
    horizon: int
    units: str = "pct"

    def __len__(self) -> int:
        return len(self.high_seq)

    @property
    def is_empty(self) -> bool:
        return not self.high_seq

    def to_flat_targets(self) -> List[List[float]]:
        """[high_1, low_1, high_2, low_2, ..., high_H, low_H] برای هر کندل."""
        result = []
        for h_seq, l_seq in zip(self.high_seq, self.low_seq, strict=True):
            flat = []
            for high_value, low_value in zip(h_seq, l_seq, strict=True):
                flat.append(high_value)
                flat.append(low_value)
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


def seq2seq_label_profile(
    series: Sequence[Sequence[float]],
    target_columns: Sequence[int],
    val_size: int = 0,
) -> Dict[str, Dict[str, List[float]]]:
    """Median of each step's high/low label, train vs the most recent rows.

    فاز ۹۵-د: منحنی «اقلیم» لیبل‌ها بر حسب k. چون خروجی استنتاج از
    آخرین موقعیت پنجره می‌آید، یک مدلِ بی‌اطلاع دقیقاً به همین پروفایل
    می‌رسد (میانه = بهینهٔ MAE). مقایسهٔ خروجی مدل با این پروفایل مشخص
    می‌کند منحنی پیش‌بینی «حقیقت داده»ست یا فقط میانگینِ بدون مهارت.

    ``series`` rows are ``features + flat targets`` as produced by
    ``attach_targets``; ``target_columns`` is ``[h1, l1, h2, l2, ...]``.
    """
    if not series or not target_columns:
        return {}
    pairs = len(target_columns) // 2
    if pairs == 0 or len(target_columns) % 2 != 0:
        return {}

    cut = max(len(series) - max(int(val_size), 0), 0)
    segments = {"train": series[:cut], "recent": series[cut:]}

    def _median(rows: Sequence[Sequence[float]], column: int) -> float:
        values = sorted(float(row[column]) for row in rows)
        middle = len(values) // 2
        if len(values) % 2:
            return values[middle]
        return (values[middle - 1] + values[middle]) / 2.0

    profile: Dict[str, Dict[str, List[float]]] = {}
    for name, rows in segments.items():
        if not rows:
            continue
        profile[name] = {
            "high": [_median(rows, target_columns[2 * k]) for k in range(pairs)],
            "low": [_median(rows, target_columns[2 * k + 1]) for k in range(pairs)],
        }
    return profile
