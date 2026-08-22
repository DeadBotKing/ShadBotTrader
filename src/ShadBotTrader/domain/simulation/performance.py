"""Performance metrics of a simulation run (Phase 16, section 74).

Every metric is computed from observed data — the equity curve and the
realised trades — never estimated. When a metric is undefined for the
data at hand (for example Sharpe with fewer than two observations) the
value is ``None`` rather than a misleading zero.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.value_object import ValueObject


class TradeRecord(ValueObject):
    """One completed round trip, used for trade-level statistics."""

    def __init__(
        self,
        symbol: str,
        realized_pnl: Decimal,
        fees: Decimal = Decimal("0"),
        opened_at: str = "",
        closed_at: str = "",
    ) -> None:
        self._symbol = symbol
        self._realized_pnl = realized_pnl
        self._fees = fees
        self._opened_at = opened_at
        self._closed_at = closed_at

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def realized_pnl(self) -> Decimal:
        """Gross PnL of the round trip."""
        return self._realized_pnl

    @property
    def fees(self) -> Decimal:
        return self._fees

    @property
    def net_pnl(self) -> Decimal:
        return self._realized_pnl - self._fees

    @property
    def is_win(self) -> bool:
        return self.net_pnl > 0

    @property
    def is_loss(self) -> bool:
        return self.net_pnl < 0

    @property
    def opened_at(self) -> str:
        return self._opened_at

    @property
    def closed_at(self) -> str:
        return self._closed_at

    def _value(self) -> tuple[Any, ...]:
        return (self._symbol, self._realized_pnl, self._fees, self._closed_at)


class PerformanceMetrics(ValueObject):
    """Aggregated performance of a simulation session."""

    def __init__(
        self,
        starting_equity: Decimal,
        final_equity: Decimal,
        total_return: Decimal,
        total_return_percent: Decimal,
        max_drawdown: Decimal,
        max_drawdown_percent: Decimal,
        trade_count: int = 0,
        win_count: int = 0,
        loss_count: int = 0,
        gross_profit: Decimal = Decimal("0"),
        gross_loss: Decimal = Decimal("0"),
        total_fees: Decimal = Decimal("0"),
        spread_cost: Decimal = Decimal("0"),
        slippage_cost: Decimal = Decimal("0"),
        sharpe: Optional[Decimal] = None,
        volatility: Optional[Decimal] = None,
    ) -> None:
        self._starting_equity = starting_equity
        self._final_equity = final_equity
        self._total_return = total_return
        self._total_return_percent = total_return_percent
        self._max_drawdown = max_drawdown
        self._max_drawdown_percent = max_drawdown_percent
        self._trade_count = trade_count
        self._win_count = win_count
        self._loss_count = loss_count
        self._gross_profit = gross_profit
        self._gross_loss = gross_loss
        self._total_fees = total_fees
        self._spread_cost = spread_cost
        self._slippage_cost = slippage_cost
        self._sharpe = sharpe
        self._volatility = volatility

    # -- capital ----------------------------------------------------------
    @property
    def starting_equity(self) -> Decimal:
        return self._starting_equity

    @property
    def final_equity(self) -> Decimal:
        return self._final_equity

    @property
    def total_return(self) -> Decimal:
        return self._total_return

    @property
    def total_return_percent(self) -> Decimal:
        return self._total_return_percent

    # -- risk --------------------------------------------------------------
    @property
    def max_drawdown(self) -> Decimal:
        return self._max_drawdown

    @property
    def max_drawdown_percent(self) -> Decimal:
        return self._max_drawdown_percent

    @property
    def volatility(self) -> Optional[Decimal]:
        return self._volatility

    @property
    def sharpe(self) -> Optional[Decimal]:
        return self._sharpe

    @property
    def recovery_factor(self) -> Optional[Decimal]:
        """Net return divided by the worst drawdown."""
        if self._max_drawdown == 0:
            return None
        return self._total_return / self._max_drawdown

    # -- trades -------------------------------------------------------------
    @property
    def trade_count(self) -> int:
        return self._trade_count

    @property
    def win_count(self) -> int:
        return self._win_count

    @property
    def loss_count(self) -> int:
        return self._loss_count

    @property
    def hit_rate(self) -> Optional[Decimal]:
        """Share of winning trades, or None when nothing traded."""
        if self._trade_count == 0:
            return None
        return Decimal(self._win_count) / Decimal(self._trade_count)

    @property
    def profit_factor(self) -> Optional[Decimal]:
        """Gross profit divided by gross loss.

        None when there were no losses (the ratio would be infinite) or
        no trades at all.
        """
        if self._gross_loss == 0:
            return None
        return self._gross_profit / self._gross_loss

    @property
    def average_win(self) -> Optional[Decimal]:
        if self._win_count == 0:
            return None
        return self._gross_profit / Decimal(self._win_count)

    @property
    def average_loss(self) -> Optional[Decimal]:
        if self._loss_count == 0:
            return None
        return self._gross_loss / Decimal(self._loss_count)

    @property
    def expectancy(self) -> Optional[Decimal]:
        """Average net PnL per trade."""
        if self._trade_count == 0:
            return None
        return (self._gross_profit - self._gross_loss) / Decimal(self._trade_count)

    @property
    def gross_profit(self) -> Decimal:
        return self._gross_profit

    @property
    def gross_loss(self) -> Decimal:
        return self._gross_loss

    @property
    def total_fees(self) -> Decimal:
        return self._total_fees

    @property
    def spread_cost(self) -> Decimal:
        return self._spread_cost

    @property
    def slippage_cost(self) -> Decimal:
        return self._slippage_cost

    def to_dict(self) -> Dict[str, Any]:
        """A flat, serialisable view for reporting."""

        def show(value: Optional[Decimal]) -> Optional[str]:
            return str(value) if value is not None else None

        return {
            "starting_equity": str(self._starting_equity),
            "final_equity": str(self._final_equity),
            "total_return": str(self._total_return),
            "total_return_percent": str(self._total_return_percent),
            "max_drawdown": str(self._max_drawdown),
            "max_drawdown_percent": str(self._max_drawdown_percent),
            "trade_count": self._trade_count,
            "win_count": self._win_count,
            "loss_count": self._loss_count,
            "hit_rate": show(self.hit_rate),
            "profit_factor": show(self.profit_factor),
            "expectancy": show(self.expectancy),
            "recovery_factor": show(self.recovery_factor),
            "sharpe": show(self._sharpe),
            "volatility": show(self._volatility),
            "total_fees": str(self._total_fees),
            "spread_cost": str(self._spread_cost),
            "slippage_cost": str(self._slippage_cost),
        }

    def _value(self) -> tuple[Any, ...]:
        return (
            self._starting_equity,
            self._final_equity,
            self._max_drawdown,
            self._trade_count,
            self._win_count,
        )


def summarise_trades(trades: Sequence[TradeRecord]) -> Dict[str, Decimal]:
    """Aggregate gross profit, gross loss and fees over ``trades``."""
    gross_profit = Decimal("0")
    gross_loss = Decimal("0")
    fees = Decimal("0")
    wins = 0
    losses = 0

    for trade in trades:
        fees += trade.fees
        net = trade.net_pnl
        if net > 0:
            gross_profit += net
            wins += 1
        elif net < 0:
            gross_loss += -net
            losses += 1

    return {
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "fees": fees,
        "wins": Decimal(wins),
        "losses": Decimal(losses),
    }


def standard_deviation(values: List[Decimal]) -> Optional[Decimal]:
    """Sample standard deviation, or None with fewer than two values."""
    if len(values) < 2:
        return None
    mean = sum(values) / Decimal(len(values))
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
    return variance.sqrt()


def sharpe_ratio(returns: List[Decimal]) -> Optional[Decimal]:
    """Sharpe of a return series (risk-free rate assumed zero).

    Returns None when the series is too short or has no dispersion —
    reporting a number in those cases would be meaningless.
    """
    deviation = standard_deviation(returns)
    if deviation is None or deviation == 0:
        return None
    mean = sum(returns) / Decimal(len(returns))
    return mean / deviation
