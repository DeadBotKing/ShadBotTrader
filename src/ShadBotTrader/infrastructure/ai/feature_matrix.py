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

**Rows are only ever removed from the ends (Phase 35).** SMA-200 has
nothing to say about candle 7, so the first rows go — that is warm-up.
Forward-looking catalogue columns (``chikou``, ``*_target_p1``) have no
value for the last few candles either, so the tail goes too. Both cuts
keep the survivors consecutive.

A hole in the *middle* is a different animal: dropping those rows would
silently glue candle 4,000 to candle 4,010, and the stride-1
roll-forward would step across ten minutes of market it never saw. So a
feature with an interior hole loses its **column**, is recorded in
``holed_features``, and every kept row stays contiguous.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

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
#: whole moving-average / band family is covered without listing every id.
#:
#: Extended in Phase 50 to cover the new adaptive-filter and Ehlers families
#: added alongside the 180-feature causal catalogue.
_PRICE_SCALED = (
    # ── Original MA / band families ──────────────────────────────────────
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
    "donchian_upper",
    "donchian_lower",
    "donchian_mid",
    "envelope",
    "ichimoku",
    "spana",
    "spanb",
    "tenkan",
    "kijun",
    "psar",
    "pivot",
    "vwap",
    "supertrend",
    # ── Adaptive filters (Phase 50) ───────────────────────────────────────
    "kalman_price",     # absolute price level from Kalman filter
    "sg_smooth",        # Savitzky-Golay smoothed price
    "supersmoother",    # Ehlers SuperSmoother output (price level)
    "gaussian1",        # Gaussian 1-pole output (price level)
    "gaussian2",        # Gaussian 2-pole output (price level)
    "gaussian3",        # Gaussian 3-pole output (price level)
    "frama_",           # FRAMA output (price level); frama_distance is excluded below
    "hull_ma",          # Hull MA output (price level); hull_distance excluded below
    "mcginley",         # McGinley Dynamic output (price level)
    "vidya_",           # VIDYA output (price level); vidya_distance excluded below
    "laguerre_filter",  # Laguerre filter output (price level)
    "decycler",         # Decycler = price - HP component (price level)
    "chandelier_long",  # Chandelier Exit level (price)
)

#: Explicitly NOT price-scaled: these are already dimensionless ratios,
#: oscillators, or distances expressed as a fraction of price.
#:
#: Suffix "_distance" marks features that output (price - filter) / filter,
#: i.e. already a ratio. Scaling them again would divide a ratio by price,
#: producing a nonsense unit.
_NEVER_SCALED = (
    # ── Original exclusions ───────────────────────────────────────────────
    "percent",
    "pct",
    "ratio",
    "osc",
    "index",
    "rsi",
    "stoch",
    # ── Distance / relative features (already ratios) ─────────────────────
    "_distance",        # e.g. kama_distance, frama_distance, hull_distance …
    "kalman_gain",      # Kalman gain ∈ [0, 1]
    "kalman_residual",  # innovation = price - prediction (already Δprice, small)
    "sg_slope",         # slope of SG polynomial (Δprice/bar, already relative)
    # ── Width / position features (already dimensionless) ─────────────────
    "donchian_width",   # (high - low) / close → already ratio
    "keltner_width",    # keltner channel width / close → already ratio
    "bb_width",         # Bollinger width / close → already ratio
    "squeeze_intensity",# bb_width - keltner_width → ratio
    # ── Decycler oscillator (% difference) ────────────────────────────────
    "decycler_osc",     # 100 × (fast_dec - slow_dec) / slow_dec → ratio
)


def is_price_scaled(feature_id: str) -> bool:
    """True when a feature's values are absolute prices."""
    lowered = feature_id.lower()
    if any(token in lowered for token in _NEVER_SCALED):
        return False
    return any(token in lowered for token in _PRICE_SCALED)


class FeatureSource(Protocol):
    """Supplies already-computed feature columns (Phase 39).

    Implemented by :class:`StoredFeatureSource`, which reads the Parquet
    store. Returning ``None`` for a feature means "not available" and the
    caller records it as skipped rather than inventing a column.
    """

    def get(self, feature_id: str):  # pragma: no cover - protocol
        """The stored result for ``feature_id``, or None."""


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
    #: Features removed because they had a hole *inside* the kept range.
    #: Keeping them would have cost interior rows and broken continuity.
    holed_features: List[str] = field(default_factory=list)
    #: Rows cut from the tail because a forward-looking column has no
    #: value there. Contiguity-safe, exactly like the warm-up cut.
    dropped_tail: int = 0
    #: Features intentionally blocked by the Stage 1 causality audit.
    excluded_features: Dict[str, str] = field(default_factory=dict)

    @property
    def is_contiguous(self) -> bool:
        """True when the kept rows are consecutive candles.

        The stride-1 roll-forward assumes row ``i+1`` is the very next
        candle after row ``i``. This is the property that guarantees it.
        """
        return all(
            later == earlier + 1
            for earlier, later in zip(self.source_index, self.source_index[1:], strict=False)
        )

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
            "dropped_tail": self.dropped_tail,
            "holed_features": len(self.holed_features),
            "excluded_features": len(self.excluded_features),
            "excluded_reasons": dict(self.excluded_features),
            "contiguous": self.is_contiguous,
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


def _is_usable(value: Optional[float]) -> bool:
    """True when a feature actually produced a number for this bar."""
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _first_valid_index(values: Sequence[Optional[float]]) -> Optional[int]:
    """Index of the first honest value, or None when there is none."""
    for index, value in enumerate(values):
        if _is_usable(value):
            return index
    return None


def _last_valid_index(values: Sequence[Optional[float]]) -> Optional[int]:
    """Index of the last honest value, or None when there is none.

    Non-causal catalogue columns (a close shifted one bar forward) are
    undefined at the tail for exactly the same structural reason warm-up
    columns are undefined at the head.
    """
    for index in range(len(values) - 1, -1, -1):
        if _is_usable(values[index]):
            return index
    return None


def _has_hole(values: Sequence[Optional[float]], start: int, stop: int) -> bool:
    """True when any value inside ``[start, stop)`` is missing.

    A gap here is neither warm-up nor a forward shift — the feature was
    already producing values, stopped, and started again. That usually
    means a division by a zero range or a NaN leaking out of a recursive
    indicator, and it is the one case that would cost interior rows.
    """
    return any(not _is_usable(value) for value in values[start:stop])


def build_feature_matrix(
    candles: Sequence[Candle],
    symbol: Symbol,
    timeframe: Timeframe,
    feature_set=None,
    resolver=None,
    include_features: bool = True,
    source: Optional["FeatureSource"] = None,
    #: When true, non-causal or unknown features never enter model input.
    causal_only: bool = False,
) -> FeatureMatrix:
    """Build the model input matrix for ``candles``.

    When ``include_features`` is False (or no resolver is supplied) only
    the six raw OHLCV columns are produced. That path exists so the
    pipeline stays runnable and testable without the whole Feature
    Platform wired up — it is a reduced input, never a fabricated one.

    Rows inside any feature's warm-up window are dropped, because a
    feature that has not seen enough history has no value, and inventing
    one would be training on fiction.

    ``source`` (Phase 39) supplies already-computed feature columns —
    normally from the Parquet store — instead of running every
    calculator again. It changes WHERE the numbers come from and nothing
    else: the scaling, the warm-up trim, the tail trim and the column
    order below are shared by both paths, which is what makes a loaded
    matrix byte-identical to a computed one.

    ``causal_only=True`` is the model/live path. It enforces the feature
    contract and records every excluded feature with its leakage reason;
    the broader feature catalogue remains available for research.
    """
    if not candles:
        raise ValidationError("Cannot build a feature matrix from zero candles")

    column_names: List[str] = list(CANDLE_COLUMNS)
    feature_columns: Dict[str, List[Optional[float]]] = {}
    skipped: List[str] = []
    excluded: Dict[str, str] = {}
    warmup = 0

    if include_features and feature_set is not None:
        context = FeatureInputContext(symbol=symbol, timeframe=timeframe, candles=list(candles))
        for definition in feature_set.definitions:
            feature_id = definition.feature_id.value
            if causal_only and not definition.is_live_compatible:
                excluded[feature_id] = (
                    definition.leakage_reason or f"causality={definition.causality.value}"
                )
                continue

            if source is not None:
                result = source.get(feature_id)
            elif resolver is not None:
                calculator = resolver.resolve(definition.calculator_family)
                if calculator is None:
                    if causal_only:
                        excluded[feature_id] = (
                            f"UNKNOWN_CALCULATOR_FAMILY:{definition.calculator_family}"
                        )
                    else:
                        skipped.append(feature_id)
                    continue
                try:
                    result = calculator.compute(definition, context)
                except Exception:
                    # A single misbehaving calculator must not destroy
                    # the whole matrix; it is recorded and left out.
                    skipped.append(feature_id)
                    continue
            else:
                break

            if result is None:
                skipped.append(feature_id)
                continue

            values = [point.value for point in result.points]
            if len(values) != len(candles):
                skipped.append(feature_id)
                continue

            feature_columns[feature_id] = values
            warmup = max(warmup, result.warmup)
            column_names.append(feature_id)

    # Phase 35: rows may only be cut from the FRONT. A feature whose
    # first honest value arrives later than the shared warm-up simply
    # pushes the start further out; a feature with a hole after that
    # point loses its column instead, because removing interior rows
    # would break the one-candle-per-row contract the roll-forward and
    # every timestamp alignment depend on.
    feature_ids = column_names[len(CANDLE_COLUMNS) :]
    start = warmup
    stop = len(candles)
    holed: List[str] = []

    for feature_id in feature_ids:
        values = feature_columns[feature_id]
        first_valid = _first_valid_index(values)
        last_valid = _last_valid_index(values)
        if first_valid is None or last_valid is None:
            holed.append(feature_id)  # never produced a usable value
            continue
        start = max(start, first_valid)
        stop = min(stop, last_valid + 1)

    for feature_id in feature_ids:
        if feature_id in holed:
            continue
        if _has_hole(feature_columns[feature_id], start, stop):
            holed.append(feature_id)

    kept_features = [feature_id for feature_id in feature_ids if feature_id not in holed]
    column_names = list(CANDLE_COLUMNS) + kept_features

    rows: List[List[float]] = []
    source_index: List[int] = []

    for index in range(start, max(stop, start)):
        close = float(candles[index].close.amount)
        row = _candle_columns(candles, index)

        for feature_id in kept_features:
            numeric = float(feature_columns[feature_id][index])  # type: ignore[arg-type]
            if is_price_scaled(feature_id) and close:
                # Ratio against the close: stationary across price regimes.
                numeric = numeric / close - 1.0
            row.append(numeric)

        rows.append(row)
        source_index.append(index)

    return FeatureMatrix(
        rows=rows,
        column_names=column_names,
        source_index=source_index,
        dropped_warmup=start,
        skipped_features=skipped,
        holed_features=holed,
        dropped_tail=max(len(candles) - max(stop, start), 0),
        excluded_features=excluded,
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
