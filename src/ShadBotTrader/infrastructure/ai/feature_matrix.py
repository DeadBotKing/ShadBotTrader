"""Turn OHLCV + the 109-feature catalogue into a model input matrix.

Phase 29 §3. The Feature Platform built in Phase 12 was never connected
to the AI Platform — the trainer used four hand-written columns. This
module is that connection.

Two rules shape every column:

**Stationarity.** Price-valued features (moving averages, bands,
envelopes) are divided by the current close before entering the model.
An absolute level teaches the network the price range of its training
set; a ratio teaches it market structure. Bounded oscillators (RSI,
stochastic) already are stationary and pass through untouched.

**No invented data.** A feature needing k bars of history is undefined
for the first k rows. Those rows are dropped, never zero-filled.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe

#: Raw market prices, expressed relative to the current close (Phase 30
#: §2). The catalogue's ``*_filter`` columns are wavelet-smoothed prices,
#: not these — the real, unfiltered market values were missing from the
#: model input entirely until Phase 30 added them back.
RAW_PRICE_COLUMNS: Tuple[str, ...] = (
    "open_rel",
    "high_rel",
    "low_rel",
    "close_rel",
    "hl2_rel",
    "hlc3_rel",
    "ohlc4_rel",
    "volume_raw_log",
)

#: Candle-derived columns: shape of the bar rather than its level.
BASE_COLUMNS: Tuple[str, ...] = (
    "return_1",
    "range_pct",
    "body_pct",
    "upper_wick_pct",
    "lower_wick_pct",
    "volume_log",
)

#: Everything that comes from the candle itself, before the catalogue.
CANDLE_COLUMNS: Tuple[str, ...] = RAW_PRICE_COLUMNS + BASE_COLUMNS

#: Feature id fragments whose values live on the price scale and must be
#: converted to a ratio against the close. Matched as substrings so the
#: whole moving-average / band family is covered without listing 109 ids.
_PRICE_SCALED = (
    "sma_",
    "ema_",
    "wma_",
    "dema_",
    "tema_",
    "hma_",
    "vwma_",
    "kama_",
    "trima_",
    "_filter",
    "bollinger_upper",
    "bollinger_lower",
    "bollinger_middle",
    "keltner",
    "donchian",
    "envelope",
    "ichimoku",
    "psar",
    "pivot",
    "vwap",
    "supertrend",
)

#: Explicitly NOT price-scaled even though the name may look like it.
_NEVER_SCALED = ("percent", "pct", "ratio", "osc", "index", "rsi", "stoch")


def is_price_scaled(feature_id: str) -> bool:
    """True when a feature's values are absolute prices."""
    lowered = feature_id.lower()
    if any(token in lowered for token in _NEVER_SCALED):
        return False
    return any(token in lowered for token in _PRICE_SCALED)


@dataclass(frozen=True)
class FeatureMatrix:
    """A numeric matrix aligned one row per candle.

    ``source_index`` maps each row back to its candle in the original
    series, which is what lets labels and features be reconciled without
    an off-by-one shift.
    """

    rows: List[List[float]]
    column_names: List[str]
    source_index: List[int]
    dropped_warmup: int = 0
    skipped_features: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def is_empty(self) -> bool:
        return not self.rows

    @property
    def width(self) -> int:
        return len(self.column_names)

    def summary(self) -> Dict[str, object]:
        return {
            "rows": len(self.rows),
            "columns": self.width,
            "dropped_warmup": self.dropped_warmup,
            "skipped_features": len(self.skipped_features),
        }


def _candle_columns(candles: Sequence[Candle], index: int) -> List[float]:
    """All 14 candle-derived columns for one bar (Phase 30 §2).

    The first eight are the raw market prices the user asked for, each
    divided by the current close so the value describes market structure
    rather than the price level. ``close_rel`` is identically zero by
    construction; it is kept so the column set is stable and explicit
    rather than silently missing the close.
    """
    candle = candles[index]
    close = float(candle.close.amount)
    high = float(candle.high.amount)
    low = float(candle.low.amount)
    open_ = float(candle.open.amount)
    volume = max(float(candle.volume), 0.0)

    if close <= 0:
        raise ValidationError(f"Candle {index} has a non-positive close")

    hl2 = (high + low) / 2.0
    hlc3 = (high + low + close) / 3.0
    ohlc4 = (open_ + high + low + close) / 4.0

    raw = [
        open_ / close - 1.0,
        high / close - 1.0,
        low / close - 1.0,
        close / close - 1.0,  # always 0.0 — kept for an explicit column set
        hl2 / close - 1.0,
        hlc3 / close - 1.0,
        ohlc4 / close - 1.0,
        math.log1p(volume),
    ]

    previous_close = float(candles[index - 1].close.amount) if index > 0 else close
    return_1 = (close - previous_close) / previous_close if previous_close else 0.0
    body_top = max(open_, close)
    body_bottom = min(open_, close)

    derived = [
        return_1,
        (high - low) / close,
        (close - open_) / close,
        (high - body_top) / close,
        (body_bottom - low) / close,
        math.log1p(volume),
    ]

    return raw + derived


def build_feature_matrix(
    candles: Sequence[Candle],
    symbol: Symbol,
    timeframe: Timeframe,
    feature_set=None,
    resolver=None,
    include_features: bool = True,
) -> FeatureMatrix:
    """Build the model input matrix for ``candles``.

    When ``include_features`` is False (or no resolver is supplied) only
    the six raw OHLCV columns are produced. That path exists so the
    pipeline stays runnable and testable without the whole Feature
    Platform wired up — it is a reduced input, never a fabricated one.

    Rows inside any feature's warm-up window are dropped, because a
    feature that has not seen enough history has no value, and inventing
    one would be training on fiction.
    """
    if not candles:
        raise ValidationError("Cannot build a feature matrix from zero candles")

    column_names: List[str] = list(CANDLE_COLUMNS)
    feature_columns: Dict[str, List[Optional[float]]] = {}
    skipped: List[str] = []
    warmup = 0

    if include_features and feature_set is not None and resolver is not None:
        context = FeatureInputContext(symbol=symbol, timeframe=timeframe, candles=list(candles))
        for definition in feature_set.definitions:
            feature_id = definition.feature_id.value
            calculator = resolver.resolve(definition.calculator_family)
            if calculator is None:
                skipped.append(feature_id)
                continue
            try:
                result = calculator.compute(definition, context)
            except Exception:
                # A single misbehaving calculator must not destroy the
                # whole matrix; it is recorded and left out.
                skipped.append(feature_id)
                continue

            values = [point.value for point in result.points]
            if len(values) != len(candles):
                skipped.append(feature_id)
                continue

            feature_columns[feature_id] = values
            warmup = max(warmup, result.warmup)
            column_names.append(feature_id)

    rows: List[List[float]] = []
    source_index: List[int] = []

    for index in range(len(candles)):
        if index < warmup:
            continue  # inside some feature's warm-up: no honest value exists

        close = float(candles[index].close.amount)
        row = _candle_columns(candles, index)

        usable = True
        for feature_id in column_names[len(CANDLE_COLUMNS) :]:
            value = feature_columns[feature_id][index]
            if value is None or not math.isfinite(float(value)):
                usable = False
                break
            numeric = float(value)
            if is_price_scaled(feature_id) and close:
                # Ratio against the close: stationary across price regimes.
                numeric = numeric / close - 1.0
            row.append(numeric)

        if not usable:
            continue

        rows.append(row)
        source_index.append(index)

    return FeatureMatrix(
        rows=rows,
        column_names=column_names,
        source_index=source_index,
        dropped_warmup=warmup,
        skipped_features=skipped,
    )


def attach_targets(
    matrix: FeatureMatrix,
    targets: Sequence[Sequence[float]],
    target_source_index: Sequence[int],
    target_names: Sequence[str],
) -> Tuple[List[List[float]], List[str], List[int]]:
    """Join a feature matrix to its labels on the original candle index.

    Features drop rows at the start (warm-up) and labels drop rows at the
    end (incomplete future window). Joining on the shared candle index is
    the only way to guarantee row ``i`` of the result carries the label
    that genuinely belongs to it.

    Returns ``(series, column_names, kept_source_index)`` where the last
    ``len(target_names)`` columns are the targets.
    """
    if len(targets) != len(target_source_index):
        raise ValidationError("targets and target_source_index must be the same length")

    by_index = {index: values for index, values in zip(target_source_index, targets, strict=True)}

    series: List[List[float]] = []
    kept: List[int] = []
    for row, index in zip(matrix.rows, matrix.source_index, strict=True):
        label = by_index.get(index)
        if label is None:
            continue  # no label for this bar (it is inside the final horizon)
        series.append(list(row) + [float(value) for value in label])
        kept.append(index)

    return series, list(matrix.column_names) + list(target_names), kept
