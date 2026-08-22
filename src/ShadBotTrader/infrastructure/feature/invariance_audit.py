"""Runtime causality and transformer-invariance audits.

Static metadata is necessary but not sufficient for a production trading
pipeline.  A calculator can be labelled ``CAUSAL`` and still call a
full-series helper, and a transformer can silently fit on the complete
series before a chronological split.  This module provides the runtime
checks used by the integrity tests and the dashboard:

* change only candles after a cut-off and compare every earlier feature;
* compare the causal model matrix, not only one calculator at a time;
* compare transformer representations when the future is changed.

A causal result must be invariant on the unchanged prefix.  A non-causal
feature is allowed to change there; it is reported as research-only, not
silently promoted to production input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.feature.feature_set import FeatureSet
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe


@dataclass(frozen=True)
class FeatureInvarianceRow:
    """Runtime result for one calculator/feature definition."""

    feature_id: str
    declared_causal: bool
    invariant: bool
    compared_points: int = 0
    first_difference: Optional[int] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        """Whether this row is safe under its declared contract."""
        return not self.error and (self.invariant if self.declared_causal else True)


@dataclass(frozen=True)
class FeatureInvarianceReport:
    """All runtime calculator checks for one prefix mutation."""

    split_index: int
    rows: List[FeatureInvarianceRow] = field(default_factory=list)

    @property
    def causal_failures(self) -> List[FeatureInvarianceRow]:
        return [row for row in self.rows if row.declared_causal and not row.passed]

    @property
    def errors(self) -> List[FeatureInvarianceRow]:
        return [row for row in self.rows if row.error]

    @property
    def is_clean(self) -> bool:
        return not self.causal_failures and not self.errors

    def summary(self) -> Dict[str, Any]:
        return {
            "split_index": self.split_index,
            "total": len(self.rows),
            "declared_causal": sum(row.declared_causal for row in self.rows),
            "invariant": sum(row.invariant for row in self.rows),
            "causal_failures": len(self.causal_failures),
            "errors": len(self.errors),
            "clean": self.is_clean,
            "failures": {
                row.feature_id: (row.error or f"changed_at={row.first_difference}")
                for row in self.causal_failures
            },
        }


@dataclass(frozen=True)
class MatrixInvarianceResult:
    """Prefix comparison for a complete feature matrix."""

    split_index: int
    compared_rows: int
    invariant: bool
    first_difference: Optional[tuple[int, int]] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and self.invariant

    def summary(self) -> Dict[str, Any]:
        return {
            "split_index": self.split_index,
            "compared_rows": self.compared_rows,
            "invariant": self.invariant,
            "first_difference": self.first_difference,
            "error": self.error,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class TransformerInvarianceResult:
    """Prefix comparison for a fit/transform implementation."""

    split_index: int
    fit_scope: str
    invariant: bool
    compared_rows: int = 0
    first_difference: Optional[tuple[int, ...]] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        return not self.error and self.invariant

    def summary(self) -> Dict[str, Any]:
        return {
            "split_index": self.split_index,
            "fit_scope": self.fit_scope,
            "invariant": self.invariant,
            "compared_rows": self.compared_rows,
            "first_difference": self.first_difference,
            "error": self.error,
            "passed": self.passed,
        }


def _validate_split(length: int, split_index: int) -> None:
    if length < 2:
        raise ValidationError("An invariance audit needs at least two rows")
    if split_index < 1 or split_index >= length:
        raise ValidationError(f"split_index must be in [1, {length - 1}], got {split_index}")


def _value_equal(left: Any, right: Any, rtol: float, atol: float) -> bool:
    if left is None or right is None:
        return left is None and right is None
    try:
        left_float = float(left)
        right_float = float(right)
    except (TypeError, ValueError):
        return left == right
    if np.isnan(left_float) and np.isnan(right_float):
        return True
    return bool(np.isclose(left_float, right_float, rtol=rtol, atol=atol, equal_nan=True))


def mutate_future_candles(
    candles: Sequence[Candle],
    split_index: int,
    price_multiplier: Decimal = Decimal("1.37"),
) -> List[Candle]:
    """Return a valid copy whose prefix is byte-for-byte market-identical.

    The mutation is deliberately large so a future-dependent calculator
    cannot pass by numerical coincidence.  It changes only OHLCV values
    at and after ``split_index`` and preserves timestamps, symbol and
    timeframe.
    """
    _validate_split(len(candles), split_index)
    if price_multiplier <= 0:
        raise ValidationError("price_multiplier must be positive")

    mutated: List[Candle] = []
    for index, candle in enumerate(candles):
        if index < split_index:
            mutated.append(candle)
            continue

        offset = index - split_index
        # A changing multiplier alters both level and future periodic
        # structure. A uniform scale would be enough for PCA, but a
        # periodic perturbation also prevents a Fourier audit from
        # passing accidentally because its dominant frequency happened to
        # remain unchanged.
        wave = Decimal("0.35") if offset % 2 == 0 else Decimal("2.20")
        factor = price_multiplier * wave
        open_price = candle.open.amount * factor
        close = candle.close.amount * factor
        high = max(candle.high.amount * factor, open_price, close)
        low = min(candle.low.amount * factor, open_price, close)
        volume = candle.volume + Decimal("1000000")
        mutated.append(
            Candle(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                open_time=candle.open_time,
                open_price=Price(open_price),
                high=Price(high),
                low=Price(low),
                close=Price(close),
                volume=volume,
                identifier=candle.id,
            )
        )
    return mutated


def audit_feature_set_invariance(
    feature_set: FeatureSet,
    resolver: Any,
    candles: Sequence[Candle],
    symbol: Symbol,
    timeframe: Timeframe,
    split_index: int,
    mutated_candles: Optional[Sequence[Candle]] = None,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> FeatureInvarianceReport:
    """Run the unchanged-prefix test for every catalogue definition.

    The report is fail-closed for definitions declared causal.  Unsafe
    definitions are still computed when possible so the audit proves
    *why* they remain research-only, but their prefix change is not
    counted as a production failure.
    """
    candles = list(candles)
    _validate_split(len(candles), split_index)
    changed = list(mutated_candles or mutate_future_candles(candles, split_index))
    if len(changed) != len(candles):
        raise ValidationError("mutated_candles must have the same length as candles")

    original_context = FeatureInputContext(symbol, timeframe, candles)
    changed_context = FeatureInputContext(symbol, timeframe, changed)
    rows: List[FeatureInvarianceRow] = []

    for definition in feature_set.definitions:
        feature_id = definition.feature_id.value
        calculator = resolver.resolve(definition.calculator_family) if resolver else None
        if calculator is None:
            rows.append(
                FeatureInvarianceRow(
                    feature_id=feature_id,
                    declared_causal=definition.is_live_compatible,
                    invariant=False,
                    error=f"UNKNOWN_CALCULATOR_FAMILY:{definition.calculator_family}",
                )
            )
            continue

        try:
            first = calculator.compute(definition, original_context)
            second = calculator.compute(definition, changed_context)
            limit = min(split_index, len(first.points), len(second.points))
            difference: Optional[int] = None
            for index in range(limit):
                if not _value_equal(
                    first.points[index].value, second.points[index].value, rtol, atol
                ):
                    difference = index
                    break
            invariant = (
                difference is None
                and len(first.points) >= split_index
                and len(second.points) >= split_index
            )
            rows.append(
                FeatureInvarianceRow(
                    feature_id=feature_id,
                    declared_causal=definition.is_live_compatible,
                    invariant=invariant,
                    compared_points=limit,
                    first_difference=difference,
                )
            )
        except Exception as error:  # pragma: no cover - defensive audit path
            rows.append(
                FeatureInvarianceRow(
                    feature_id=feature_id,
                    declared_causal=definition.is_live_compatible,
                    invariant=False,
                    error=f"{type(error).__name__}: {error}",
                )
            )

    return FeatureInvarianceReport(split_index=split_index, rows=rows)


def audit_matrix_invariance(
    build_matrix: Callable[[Sequence[Candle]], Any],
    candles: Sequence[Candle],
    split_index: int,
    mutated_candles: Optional[Sequence[Candle]] = None,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> MatrixInvarianceResult:
    """Compare the prefix of two complete matrices built by the same path."""
    candles = list(candles)
    _validate_split(len(candles), split_index)
    changed = list(mutated_candles or mutate_future_candles(candles, split_index))
    if len(changed) != len(candles):
        raise ValidationError("mutated_candles must have the same length as candles")

    try:
        first = build_matrix(candles)
        second = build_matrix(changed)
        first_by_index = {
            int(source_index): row
            for source_index, row in zip(first.source_index, first.rows, strict=True)
            if int(source_index) < split_index
        }
        second_by_index = {
            int(source_index): row
            for source_index, row in zip(second.source_index, second.rows, strict=True)
            if int(source_index) < split_index
        }
        common = sorted(set(first_by_index) & set(second_by_index))
        if not common:
            return MatrixInvarianceResult(
                split_index=split_index,
                compared_rows=0,
                invariant=False,
                error="no common prefix rows",
            )
        if first.column_names != second.column_names:
            return MatrixInvarianceResult(
                split_index=split_index,
                compared_rows=len(common),
                invariant=False,
                error="column schema changed after future mutation",
            )

        for row_index in common:
            left = np.asarray(first_by_index[row_index], dtype=float)
            right = np.asarray(second_by_index[row_index], dtype=float)
            if left.shape != right.shape:
                return MatrixInvarianceResult(
                    split_index=split_index,
                    compared_rows=len(common),
                    invariant=False,
                    first_difference=(row_index, -1),
                    error="row width changed after future mutation",
                )
            equal = np.isclose(left, right, rtol=rtol, atol=atol, equal_nan=True)
            if not bool(np.all(equal)):
                column = int(np.flatnonzero(~equal)[0])
                return MatrixInvarianceResult(
                    split_index=split_index,
                    compared_rows=len(common),
                    invariant=False,
                    first_difference=(row_index, column),
                )
        return MatrixInvarianceResult(
            split_index=split_index,
            compared_rows=len(common),
            invariant=True,
        )
    except Exception as error:  # pragma: no cover - defensive audit path
        return MatrixInvarianceResult(
            split_index=split_index,
            compared_rows=0,
            invariant=False,
            error=f"{type(error).__name__}: {error}",
        )


def _fit_and_transform(factory: Callable[[], Any], fit_data: Any, transform_data: Any) -> Any:
    transformer = factory()
    fit_transform = getattr(transformer, "fit_transform", None)
    if callable(fit_transform):
        # Use separate fit and transform calls when a transformer exposes
        # them.  This avoids accidentally hiding a stateful implementation
        # behind a convenience method in the prefix-fit path.
        transformer.fit(fit_data)
        return transformer.transform(transform_data)
    transformer.fit(fit_data)
    return transformer.transform(transform_data)


def audit_transformer_invariance(
    transformer_factory: Callable[[], Any],
    data: Sequence[Any],
    split_index: int,
    mutate_future: Callable[[Sequence[Any], int], Sequence[Any]],
    fit_on_prefix: bool = False,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> TransformerInvarianceResult:
    """Check that a transform's train-prefix representation ignores future.

    ``fit_on_prefix=False`` audits the dangerous implementation that fits
    on the full dataset. ``fit_on_prefix=True`` audits the production
    protocol: fit only on ``data[:split_index]`` and transform the same
    prefix. The two modes make the test useful both for catching leakage
    and for proving the corrected train-only transformer workflow.
    """
    data = list(data)
    _validate_split(len(data), split_index)
    changed = list(mutate_future(data, split_index))
    if len(changed) != len(data):
        raise ValidationError("mutate_future must preserve the data length")

    scope = "train_prefix" if fit_on_prefix else "full_series"
    try:
        fit_a = data[:split_index] if fit_on_prefix else data
        fit_b = changed[:split_index] if fit_on_prefix else changed
        transformed_a = np.asarray(
            _fit_and_transform(transformer_factory, fit_a, data[:split_index]), dtype=float
        )
        transformed_b = np.asarray(
            _fit_and_transform(transformer_factory, fit_b, changed[:split_index]), dtype=float
        )
        if transformed_a.shape != transformed_b.shape:
            return TransformerInvarianceResult(
                split_index=split_index,
                fit_scope=scope,
                invariant=False,
                error="transformed prefix shapes differ",
            )
        equal = np.isclose(transformed_a, transformed_b, rtol=rtol, atol=atol, equal_nan=True)
        if bool(np.all(equal)):
            return TransformerInvarianceResult(
                split_index=split_index,
                fit_scope=scope,
                invariant=True,
                compared_rows=split_index,
            )
        first = tuple(int(value) for value in np.argwhere(~equal)[0])
        return TransformerInvarianceResult(
            split_index=split_index,
            fit_scope=scope,
            invariant=False,
            compared_rows=split_index,
            first_difference=first,
        )
    except Exception as error:  # pragma: no cover - defensive audit path
        return TransformerInvarianceResult(
            split_index=split_index,
            fit_scope=scope,
            invariant=False,
            error=f"{type(error).__name__}: {error}",
        )
