"""Replay tape of a simulation run (Phase 16, sections 22-23, 74-76).

Section 23 requires a simulation to be *inspectable* step by step. The
metrics of a finished run answer "how much"; a replay answers "where and
why": which bar the position was opened on, at what price it was closed,
and what that round trip actually produced.

Nothing here computes trading logic. The tape is a recording of what the
engine already did — one ``ReplayBar`` per processed market event, plus a
``TradeMarker`` for every real fill. It is deliberately free of any
rendering concern so a console, an HTML player or a test can consume the
very same data.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject

#: What a fill did to the position it touched.
MARKER_ENTRY = "entry"
MARKER_EXIT = "exit"
MARKER_ADJUST = "adjust"

_KINDS = (MARKER_ENTRY, MARKER_EXIT, MARKER_ADJUST)


def _number(value: Optional[Decimal]) -> Optional[float]:
    """Decimal -> float for transport, keeping ``None`` meaningful."""
    return None if value is None else float(value)


class TradeMarker(ValueObject):
    """One real fill, placed on the bar it happened on.

    ``realized_pnl`` is only filled in when the fill actually crystallised
    profit or loss (a reduction or a close). For an entry it stays
    ``None`` — an open position has no result yet, and reporting zero
    would read like a break-even trade.
    """

    def __init__(
        self,
        bar_index: int,
        timestamp: str,
        side: str,
        kind: str,
        price: Decimal,
        quantity: Decimal,
        position_after: Decimal,
        realized_pnl: Optional[Decimal] = None,
        fees: Decimal = Decimal("0"),
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if bar_index < 0:
            raise ValidationError("bar_index must not be negative")
        if kind not in _KINDS:
            raise ValidationError(f"marker kind must be one of {_KINDS}")
        if quantity <= 0:
            raise ValidationError("marker quantity must be positive")

        self._bar_index = bar_index
        self._timestamp = timestamp
        self._side = side
        self._kind = kind
        self._price = price
        self._quantity = quantity
        self._position_after = position_after
        self._realized_pnl = realized_pnl
        self._fees = fees
        self._reason = reason
        self._metadata = dict(metadata or {})

    @property
    def metadata(self) -> Dict[str, Any]:
        """Structured audit fields such as bracket TP/SL levels."""
        return dict(self._metadata)

    @property
    def bar_index(self) -> int:
        return self._bar_index

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @property
    def side(self) -> str:
        """``buy`` or ``sell`` — the direction of the fill itself."""
        return self._side

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def price(self) -> Decimal:
        return self._price

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def position_after(self) -> Decimal:
        return self._position_after

    @property
    def realized_pnl(self) -> Optional[Decimal]:
        return self._realized_pnl

    @property
    def fees(self) -> Decimal:
        return self._fees

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def net_pnl(self) -> Optional[Decimal]:
        """Realised PnL after the fees of this fill."""
        if self._realized_pnl is None:
            return None
        return self._realized_pnl - self._fees

    @property
    def is_closing(self) -> bool:
        return self._kind == MARKER_EXIT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bar": self._bar_index,
            "time": self._timestamp,
            "side": self._side,
            "kind": self._kind,
            "price": float(self._price),
            "quantity": float(self._quantity),
            "position_after": float(self._position_after),
            "realized_pnl": _number(self._realized_pnl),
            "net_pnl": _number(self.net_pnl),
            "fees": float(self._fees),
            "reason": self._reason,
            "metadata": dict(self._metadata),
        }

    def _value(self) -> Tuple[Any, ...]:
        return (
            self._bar_index,
            self._side,
            self._kind,
            self._price,
            self._quantity,
            self._realized_pnl,
        )


class ReplayBar(ValueObject):
    """One processed bar with the portfolio state it left behind."""

    def __init__(
        self,
        index: int,
        timestamp: str,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
        equity: Decimal,
        cash: Decimal,
        position: Decimal,
        prediction: Optional[float] = None,
        markers: Sequence[TradeMarker] = (),
    ) -> None:
        self._index = index
        self._timestamp = timestamp
        self._open = open_price
        self._high = high
        self._low = low
        self._close = close
        self._volume = volume
        self._equity = equity
        self._cash = cash
        self._position = position
        self._prediction = prediction
        self._markers: Tuple[TradeMarker, ...] = tuple(markers)

    @property
    def index(self) -> int:
        return self._index

    @property
    def timestamp(self) -> str:
        return self._timestamp

    @property
    def open(self) -> Decimal:
        return self._open

    @property
    def high(self) -> Decimal:
        return self._high

    @property
    def low(self) -> Decimal:
        return self._low

    @property
    def close(self) -> Decimal:
        return self._close

    @property
    def volume(self) -> Decimal:
        return self._volume

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def cash(self) -> Decimal:
        return self._cash

    @property
    def position(self) -> Decimal:
        """Signed position size held after this bar."""
        return self._position

    @property
    def prediction(self) -> Optional[float]:
        """Model output for this bar, or ``None`` during warmup."""
        return self._prediction

    @property
    def markers(self) -> Tuple[TradeMarker, ...]:
        return self._markers

    def to_dict(self) -> Dict[str, Any]:
        return {
            "i": self._index,
            "t": self._timestamp,
            "o": float(self._open),
            "h": float(self._high),
            "l": float(self._low),
            "c": float(self._close),
            "v": float(self._volume),
            "eq": float(self._equity),
            "cash": float(self._cash),
            "pos": float(self._position),
            "p": self._prediction,
        }

    def _value(self) -> Tuple[Any, ...]:
        return (self._index, self._timestamp, self._close, self._equity, self._position)


class ReplayTape(ValueObject):
    """The full recording of a run: every bar, in order, with its fills."""

    def __init__(
        self,
        session_id: str,
        symbol: str,
        timeframe: str,
        starting_equity: Decimal,
        bars: Sequence[ReplayBar],
    ) -> None:
        self._session_id = session_id
        self._symbol = symbol
        self._timeframe = timeframe
        self._starting_equity = starting_equity
        self._bars: Tuple[ReplayBar, ...] = tuple(bars)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def starting_equity(self) -> Decimal:
        return self._starting_equity

    @property
    def bars(self) -> Tuple[ReplayBar, ...]:
        return self._bars

    @property
    def is_empty(self) -> bool:
        return not self._bars

    @property
    def markers(self) -> List[TradeMarker]:
        """Every fill of the run, in chronological order."""
        return [marker for bar in self._bars for marker in bar.markers]

    @property
    def closing_markers(self) -> List[TradeMarker]:
        """Only the fills that closed a position — the ones with a result."""
        return [marker for marker in self.markers if marker.is_closing]

    @property
    def final_equity(self) -> Optional[Decimal]:
        return self._bars[-1].equity if self._bars else None

    def round_trips(self) -> List[Dict[str, Any]]:
        """Pair every entry with the fill that closed it.

        Walks the tape once and emits one row per completed round trip:
        where it opened, where it closed, how long it was held and what it
        produced. A position still open at the end of the data produces no
        row — it has no result to report yet.
        """
        trips: List[Dict[str, Any]] = []
        open_marker: Optional[TradeMarker] = None

        for marker in self.markers:
            if marker.kind == MARKER_ENTRY:
                open_marker = marker
                continue
            if marker.kind == MARKER_EXIT and open_marker is not None:
                direction = "long" if open_marker.side == "buy" else "short"
                # A round trip pays commission on both entry and exit.
                # ``TradeMarker.net_pnl`` is intentionally per-fill, so
                # combine the two marker fees here for the trade-level
                # replay result.
                total_fees = open_marker.fees + marker.fees
                net = None if marker.realized_pnl is None else marker.realized_pnl - total_fees
                bracket = dict(open_marker.metadata)
                if not bracket:
                    bracket = dict(marker.metadata)
                trips.append(
                    {
                        "direction": direction,
                        "entry_bar": open_marker.bar_index,
                        "entry_time": open_marker.timestamp,
                        "entry_price": float(open_marker.price),
                        "exit_bar": marker.bar_index,
                        "exit_time": marker.timestamp,
                        "exit_price": float(marker.price),
                        "quantity": float(marker.quantity),
                        "bars_held": marker.bar_index - open_marker.bar_index,
                        "realized_pnl": _number(marker.realized_pnl),
                        "fees": float(total_fees),
                        "entry_fees": float(open_marker.fees),
                        "exit_fees": float(marker.fees),
                        "net_pnl": _number(net),
                        "exit_reason": marker.metadata.get("bracket_exit_reason", "")
                        or marker.reason,
                        "entry_metadata": dict(open_marker.metadata),
                        "bracket": bracket,
                        "result": (
                            "win"
                            if (net is not None and net > 0)
                            else "loss" if net is not None else "open"
                        ),
                    }
                )
                open_marker = None

        return trips

    def open_position_at_end(self) -> Optional[Dict[str, Any]]:
        """The entry that never got closed, if the run ended mid-trade."""
        entries = [marker for marker in self.markers if marker.kind == MARKER_ENTRY]
        if not entries or not self._bars:
            return None
        if self._bars[-1].position == 0:
            return None
        last = entries[-1]
        return {
            "direction": "long" if last.side == "buy" else "short",
            "entry_bar": last.bar_index,
            "entry_time": last.timestamp,
            "entry_price": float(last.price),
            "quantity": float(last.quantity),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self._session_id,
            "symbol": self._symbol,
            "timeframe": self._timeframe,
            "starting_equity": float(self._starting_equity),
            "final_equity": _number(self.final_equity),
            "bar_count": len(self._bars),
            "bars": [bar.to_dict() for bar in self._bars],
            "markers": [marker.to_dict() for marker in self.markers],
            "round_trips": self.round_trips(),
            "open_position": self.open_position_at_end(),
        }

    def _value(self) -> Tuple[Any, ...]:
        return (self._session_id, self._symbol, self._timeframe, self._bars)


class ReplayRecorder:
    """Collects bars and fills while a simulation runs.

    Mutable by nature — it is a recorder — but it produces an immutable
    ``ReplayTape``. Recording is optional: a parameter sweep running
    hundreds of simulations should not pay for a tape nobody reads.
    """

    def __init__(self, session_id: str, symbol: str, timeframe: str, starting_equity: Decimal):
        self._session_id = session_id
        self._symbol = symbol
        self._timeframe = timeframe
        self._starting_equity = starting_equity
        self._bars: List[ReplayBar] = []
        self._pending: List[TradeMarker] = []

    def mark(self, marker: TradeMarker) -> None:
        """Attach a fill to the bar currently being processed."""
        self._pending.append(marker)

    def record_bar(
        self,
        index: int,
        timestamp: str,
        open_price: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
        equity: Decimal,
        cash: Decimal,
        position: Decimal,
        prediction: Optional[float] = None,
    ) -> ReplayBar:
        """Close off the current bar, consuming any pending fills."""
        bar = ReplayBar(
            index=index,
            timestamp=timestamp,
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            equity=equity,
            cash=cash,
            position=position,
            prediction=prediction,
            markers=tuple(self._pending),
        )
        self._pending.clear()
        self._bars.append(bar)
        return bar

    @property
    def bar_count(self) -> int:
        return len(self._bars)

    def build(self) -> ReplayTape:
        return ReplayTape(
            session_id=self._session_id,
            symbol=self._symbol,
            timeframe=self._timeframe,
            starting_equity=self._starting_equity,
            bars=tuple(self._bars),
        )
