"""Durable portfolio ledger (Phase 15 accounting + Phase 20 persistence).

Positions, fills and transactions survive a restart, and — more
importantly — the position can be **rebuilt from the stored fills**.
That is the real test of an accounting system: the current state must be
a consequence of recorded events, not a number someone remembered.

Accounting semantics are unchanged from ``InMemoryPortfolioLedger``:
this class delegates every calculation to the same ``PositionState``
domain object and only adds storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from ShadBotTrader.domain.execution.execution_types import TransactionType
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.ports import PortfolioLedger
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.persistence.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqlitePortfolioLedger(PortfolioLedger):
    """A portfolio ledger backed by SQLite.

    ``load()`` restores a previous session; ``rebuild_from_fills()``
    recomputes every position from the stored fill history, which is the
    authoritative reconstruction path.
    """

    def __init__(
        self,
        database: Database,
        session_id: str = "default",
        currency: str = "USD",
        starting_cash: Decimal = Decimal("0"),
        autoload: bool = True,
    ) -> None:
        self._database = database
        self._session_id = session_id
        self._currency = currency.strip().upper()
        self._starting_cash = starting_cash
        self._positions: Dict[str, PositionState] = {}
        self._cash = Money(starting_cash, self._currency)

        if autoload:
            self.load()

    # -- identity -------------------------------------------------------------
    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def currency(self) -> str:
        return self._currency

    # -- ledger contract ------------------------------------------------------
    def apply(self, result: ExecutionResult) -> PositionState:
        """Fold every fill into the position and persist the outcome."""
        if not result.fills:
            return PositionState.flat(Symbol("UNKNOWN"), currency=self._currency)

        symbol = result.fills[0].symbol
        key = str(symbol)
        state = self._positions.get(key) or PositionState.flat(symbol, currency=self._currency)

        for fill in result.fills:
            state, realized = state.apply_fill(fill)
            self._store_fill(fill)
            self._book(fill, realized)

        self._positions[key] = state
        self._store_position(state)
        return state

    def position(self, symbol: Symbol) -> PositionState:
        return self._positions.get(str(symbol)) or PositionState.flat(
            symbol, currency=self._currency
        )

    def positions(self) -> List[PositionState]:
        """Every non-flat position."""
        return [state for state in self._positions.values() if not state.is_flat]

    # -- reporting -------------------------------------------------------------
    @property
    def cash(self) -> Money:
        return self._cash

    @property
    def realized_pnl(self) -> Money:
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
        return self.realized_pnl.subtract(self.total_fees)

    def unrealized_pnl(self, prices: Dict[str, Price]) -> Money:
        total = Money.zero(self._currency)
        for key, state in self._positions.items():
            price = prices.get(key)
            if price is not None:
                total = total.add(state.unrealized_pnl(price))
        return total

    def equity(self, prices: Dict[str, Price]) -> Money:
        return self._cash.add(self.unrealized_pnl(prices))

    def all_positions(self) -> List[PositionState]:
        return list(self._positions.values())

    # -- persistence ------------------------------------------------------------
    def load(self) -> None:
        """Restore the session's positions and cash from storage."""
        rows = self._database.query(
            "SELECT * FROM portfolio_position WHERE session_id = ?",
            (self._session_id,),
        )
        self._positions = {}
        for row in rows:
            symbol = Symbol(row["symbol"])
            average = row["average_price"]
            self._positions[row["symbol"]] = PositionState(
                symbol=symbol,
                signed_quantity=Decimal(row["signed_quantity"]),
                average_entry_price=Price(Decimal(average)) if average else None,
                realized_pnl=Money(Decimal(row["realized_pnl"]), row["currency"]),
                total_fees=Money(Decimal(row["total_fees"]), row["currency"]),
                currency=row["currency"],
            )
        self._cash = self._compute_cash()

    def rebuild_from_fills(self) -> Dict[str, PositionState]:
        """Recompute every position by replaying the stored fills.

        The result must equal the incrementally maintained state; a
        divergence means the books are wrong, which is worth being able
        to detect.
        """
        rows = self._database.query(
            "SELECT * FROM portfolio_fill WHERE session_id = ? ORDER BY id",
            (self._session_id,),
        )
        rebuilt: Dict[str, PositionState] = {}
        for row in rows:
            symbol = Symbol(row["symbol"])
            key = row["symbol"]
            state = rebuilt.get(key) or PositionState.flat(symbol, currency=row["currency"])
            fill = Fill(
                fill_id=row["fill_id"],
                order_id=row["order_id"],
                symbol=symbol,
                side=OrderSide(row["side"]),
                quantity=Decimal(row["quantity"]),
                price=Price(Decimal(row["price"])),
                executed_at=Timestamp(datetime.fromisoformat(row["executed_at"])),
                fee=Money(Decimal(row["fee"]), row["currency"]) if row["fee"] else None,
            )
            state, _ = state.apply_fill(fill)
            rebuilt[key] = state
        return rebuilt

    def stored_fills(self) -> List[Dict[str, object]]:
        rows = self._database.query(
            "SELECT * FROM portfolio_fill WHERE session_id = ? ORDER BY id",
            (self._session_id,),
        )
        return [dict(row) for row in rows]

    def transactions(self) -> List[Dict[str, object]]:
        rows = self._database.query(
            "SELECT * FROM portfolio_transaction WHERE session_id = ? ORDER BY id",
            (self._session_id,),
        )
        return [dict(row) for row in rows]

    def sessions(self) -> List[str]:
        rows = self._database.query(
            "SELECT DISTINCT session_id FROM portfolio_position ORDER BY session_id"
        )
        return [row["session_id"] for row in rows]

    # -- internals ---------------------------------------------------------------
    def _store_fill(self, fill: Fill) -> None:
        self._database.execute(
            """
            INSERT INTO portfolio_fill
                (session_id, fill_id, order_id, symbol, side, quantity, price,
                 fee, currency, executed_at, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._session_id,
                fill.fill_id,
                fill.order_id,
                str(fill.symbol),
                fill.side.value,
                str(fill.quantity),
                str(fill.price.amount),
                str(fill.fee.amount) if fill.fee is not None else None,
                self._currency,
                str(fill.executed_at),
                _now(),
            ),
        )

    def _book(self, fill: Fill, realized: Money) -> None:
        """Record the money movements a fill caused."""
        if not realized.is_zero:
            self._store_transaction(
                f"txn:pnl:{fill.fill_id}",
                TransactionType.TRADE,
                realized,
                fill,
            )
            self._cash = self._cash.add(realized)

        if fill.fee is not None and not fill.fee.is_zero:
            self._store_transaction(
                f"txn:fee:{fill.fill_id}",
                TransactionType.FEE,
                fill.fee.negate(),
                fill,
            )
            self._cash = self._cash.subtract(fill.fee)

    def _store_transaction(
        self,
        transaction_id: str,
        transaction_type: TransactionType,
        amount: Money,
        fill: Fill,
    ) -> None:
        self._database.execute(
            """
            INSERT INTO portfolio_transaction
                (session_id, transaction_id, transaction_type, amount, currency,
                 reference, symbol, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._session_id,
                transaction_id,
                transaction_type.value,
                str(amount.amount),
                amount.currency,
                fill.fill_id,
                str(fill.symbol),
                str(fill.executed_at),
            ),
        )

    def _store_position(self, state: PositionState) -> None:
        average = state.average_entry_price
        self._database.execute(
            """
            INSERT INTO portfolio_position
                (session_id, symbol, signed_quantity, average_price,
                 realized_pnl, total_fees, currency, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, symbol) DO UPDATE SET
                signed_quantity = excluded.signed_quantity,
                average_price   = excluded.average_price,
                realized_pnl    = excluded.realized_pnl,
                total_fees      = excluded.total_fees,
                updated_at      = excluded.updated_at
            """,
            (
                self._session_id,
                str(state.symbol),
                str(state.signed_quantity),
                str(average.amount) if average is not None else None,
                str(state.realized_pnl.amount),
                str(state.total_fees.amount),
                state.currency,
                _now(),
            ),
        )

    def _compute_cash(self) -> Money:
        """Starting cash plus every recorded transaction."""
        row = self._database.query_one(
            "SELECT COUNT(*) AS total FROM portfolio_transaction WHERE session_id = ?",
            (self._session_id,),
        )
        if row is None or int(row["total"]) == 0:
            return Money(self._starting_cash, self._currency)

        total = Money(self._starting_cash, self._currency)
        for entry in self.transactions():
            total = total.add(Money(Decimal(str(entry["amount"])), str(entry["currency"])))
        return total


def load_ledger(
    database: Database,
    session_id: str,
    currency: str = "USD",
    starting_cash: Decimal = Decimal("0"),
) -> Optional[SqlitePortfolioLedger]:
    """Reopen a stored session, or None when it does not exist."""
    row = database.query_one(
        "SELECT COUNT(*) AS total FROM portfolio_position WHERE session_id = ?",
        (session_id,),
    )
    if row is None or int(row["total"]) == 0:
        return None
    return SqlitePortfolioLedger(
        database, session_id=session_id, currency=currency, starting_cash=starting_cash
    )
