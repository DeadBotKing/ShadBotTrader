"""In-memory portfolio ledger (Phase 15, sections 13, 19-27).

Owns the financial state: positions, realized PnL, fees and the
transaction history. It consumes real fills only — it never infers
anything from a trading intent (section 24).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.execution.execution_types import TransactionType
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.ports import ReportingLedger
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp


class Transaction:
    """One recorded financial movement (Phase 15, section 19)."""

    def __init__(
        self,
        transaction_id: str,
        transaction_type: TransactionType,
        amount: Money,
        timestamp: Timestamp,
        reference: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._transaction_id = transaction_id
        self._transaction_type = transaction_type
        self._amount = amount
        self._timestamp = timestamp
        self._reference = reference
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def amount(self) -> Money:
        return self._amount

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def reference(self) -> str:
        return self._reference

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def __str__(self) -> str:
        return f"{self._transaction_type.value} {self._amount} ({self._reference})"


class InMemoryPortfolioLedger(ReportingLedger):
    """Tracks positions and PnL by folding fills, one symbol at a time."""

    def __init__(self, currency: str = "USD", starting_cash: Decimal = Decimal("0")) -> None:
        self._currency = currency.strip().upper()
        self._positions: Dict[str, PositionState] = {}
        self._transactions: List[Transaction] = []
        self._starting_cash = starting_cash
        self._cash = Money(starting_cash, self._currency)

    # -- ledger contract ---------------------------------------------------
    def apply(self, result: ExecutionResult) -> PositionState:
        """Fold every fill of ``result`` into the matching position."""
        if not result.fills:
            return self._flat(result)

        key = str(result.fills[0].symbol)
        state = self._positions.get(key) or PositionState.flat(
            result.fills[0].symbol, currency=self._currency
        )

        for fill in result.fills:
            state, realized = state.apply_fill(fill)
            self._record_fill(fill, realized)

        self._positions[key] = state
        return state

    def position(self, symbol: Symbol) -> PositionState:
        return self._positions.get(str(symbol)) or PositionState.flat(
            symbol, currency=self._currency
        )

    def positions(self) -> List[PositionState]:
        """Every non-flat position."""
        return [state for state in self._positions.values() if not state.is_flat]

    # -- reporting ---------------------------------------------------------
    @property
    def currency(self) -> str:
        return self._currency

    @property
    def cash(self) -> Money:
        """Cash after realized PnL and fees (Phase 15, section 11)."""
        return self._cash

    @property
    def transactions(self) -> List[Transaction]:
        return list(self._transactions)

    @property
    def realized_pnl(self) -> Money:
        """Gross realized PnL across every symbol."""
        total = Money.zero(self._currency)
        for state in self._positions.values():
            total = total.add(state.realized_pnl)
        return total

    @property
    def total_fees(self) -> Money:
        total = Money.zero(self._currency)
        for state in self._positions.values():
            total = total.add(state.total_fees)
        return total

    @property
    def net_realized_pnl(self) -> Money:
        """Realized PnL after fees."""
        return self.realized_pnl.subtract(self.total_fees)

    def unrealized_pnl(self, prices: Dict[str, Price]) -> Money:
        """Mark every open position against ``prices`` (section 26)."""
        total = Money.zero(self._currency)
        for key, state in self._positions.items():
            price = prices.get(key)
            if price is not None:
                total = total.add(state.unrealized_pnl(price))
        return total

    def equity(self, prices: Dict[str, Price]) -> Money:
        """Cash plus unrealized PnL (Phase 15, section 12)."""
        return self._cash.add(self.unrealized_pnl(prices))

    def all_positions(self) -> List[PositionState]:
        """Every tracked position, including closed (flat) ones."""
        return list(self._positions.values())

    # -- helpers -----------------------------------------------------------
    def _record_fill(self, fill: Fill, realized: Money) -> None:
        if not realized.is_zero:
            self._transactions.append(
                Transaction(
                    transaction_id=f"txn:pnl:{fill.fill_id}",
                    transaction_type=TransactionType.TRADE,
                    amount=realized,
                    timestamp=fill.executed_at,
                    reference=fill.fill_id,
                    metadata={"symbol": str(fill.symbol)},
                )
            )
            self._cash = self._cash.add(realized)

        if fill.fee is not None and not fill.fee.is_zero:
            self._transactions.append(
                Transaction(
                    transaction_id=f"txn:fee:{fill.fill_id}",
                    transaction_type=TransactionType.FEE,
                    amount=fill.fee.negate(),
                    timestamp=fill.executed_at,
                    reference=fill.fill_id,
                    metadata={"symbol": str(fill.symbol)},
                )
            )
            self._cash = self._cash.subtract(fill.fee)

    def _flat(self, result: ExecutionResult) -> PositionState:
        """A neutral state for a result that produced no fills."""
        from ShadBotTrader.domain.market.symbol import Symbol as _Symbol

        return PositionState.flat(_Symbol("UNKNOWN"), currency=self._currency)
