"""Equity and drawdown curves (Phase 16, sections 75-76).

The equity curve is the time series of portfolio value produced by a
simulation; the drawdown curve is derived from it. Both use ``Decimal``
throughout — these numbers describe money.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.timestamp import Timestamp


class EquityPoint(ValueObject):
    """Portfolio value at one instant."""

    def __init__(
        self,
        timestamp: Timestamp,
        equity: Decimal,
        cash: Decimal,
        realized_pnl: Decimal = Decimal("0"),
        unrealized_pnl: Decimal = Decimal("0"),
        open_positions: int = 0,
    ) -> None:
        self._timestamp = timestamp
        self._equity = equity
        self._cash = cash
        self._realized_pnl = realized_pnl
        self._unrealized_pnl = unrealized_pnl
        self._open_positions = open_positions

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def cash(self) -> Decimal:
        return self._cash

    @property
    def realized_pnl(self) -> Decimal:
        return self._realized_pnl

    @property
    def unrealized_pnl(self) -> Decimal:
        return self._unrealized_pnl

    @property
    def open_positions(self) -> int:
        return self._open_positions

    def _value(self) -> tuple[Any, ...]:
        return (self._timestamp, self._equity, self._cash)


class EquityCurve:
    """An ordered series of equity observations."""

    def __init__(self, points: Sequence[EquityPoint] = ()) -> None:
        self._points: List[EquityPoint] = list(points)

    def record(self, point: EquityPoint) -> None:
        """Append an observation; time must not move backwards."""
        if self._points and point.timestamp.value < self._points[-1].timestamp.value:
            raise ValidationError("EquityCurve points must be chronological")
        self._points.append(point)

    @property
    def points(self) -> List[EquityPoint]:
        return list(self._points)

    @property
    def is_empty(self) -> bool:
        return not self._points

    def __len__(self) -> int:
        return len(self._points)

    @property
    def starting_equity(self) -> Optional[Decimal]:
        return self._points[0].equity if self._points else None

    @property
    def final_equity(self) -> Optional[Decimal]:
        return self._points[-1].equity if self._points else None

    @property
    def peak_equity(self) -> Optional[Decimal]:
        return max((point.equity for point in self._points), default=None)

    @property
    def trough_equity(self) -> Optional[Decimal]:
        return min((point.equity for point in self._points), default=None)

    @property
    def total_return(self) -> Optional[Decimal]:
        """Final minus starting equity."""
        if not self._points:
            return None
        return self._points[-1].equity - self._points[0].equity

    @property
    def total_return_percent(self) -> Optional[Decimal]:
        """Return relative to the starting equity, in percent."""
        if not self._points:
            return None
        start = self._points[0].equity
        if start == 0:
            return None
        return (self._points[-1].equity - start) / start * Decimal("100")

    def drawdown_series(self) -> List[Decimal]:
        """Absolute drawdown from the running peak, per point."""
        series: List[Decimal] = []
        peak: Optional[Decimal] = None
        for point in self._points:
            peak = point.equity if peak is None else max(peak, point.equity)
            series.append(peak - point.equity)
        return series

    @property
    def max_drawdown(self) -> Decimal:
        """Largest peak-to-trough decline in absolute terms."""
        series = self.drawdown_series()
        return max(series) if series else Decimal("0")

    @property
    def max_drawdown_percent(self) -> Decimal:
        """Largest peak-to-trough decline as a percentage of the peak."""
        peak: Optional[Decimal] = None
        worst = Decimal("0")
        for point in self._points:
            peak = point.equity if peak is None else max(peak, point.equity)
            if peak > 0:
                decline = (peak - point.equity) / peak * Decimal("100")
                worst = max(worst, decline)
        return worst

    def returns(self) -> List[Decimal]:
        """Simple period-over-period returns between consecutive points."""
        values: List[Decimal] = []
        for previous, current in zip(self._points, self._points[1:], strict=False):
            if previous.equity != 0:
                values.append((current.equity - previous.equity) / previous.equity)
        return values
