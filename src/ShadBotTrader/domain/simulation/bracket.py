"""Take-profit / stop-loss brackets for candle simulations.

A bracket is created from the range model's predicted high and low when a
position is opened.  It is deliberately a small domain object: it knows
how to decide whether an OHLC candle touched either level, but it does not
execute an order or mutate the portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.simulation_types import SameBarPolicy
from ShadBotTrader.domain.trading.order import OrderSide


class BracketExitReason(str, Enum):
    """Why a bracket closed a position."""

    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"


@dataclass(frozen=True)
class TradeBracket:
    """The fixed target and stop attached to one position.

    ``entry_reference`` is the price known when the model decision was
    made.  The levels are not re-predicted on every later candle: doing so
    would turn a single trade into a sequence of hindsight-adjusted
    trades.
    """

    side: OrderSide
    entry_reference: Price
    take_profit: Price
    stop_loss: Price
    created_at: Timestamp
    model_high: Price
    model_low: Price
    #: The 1H Range model's reference close. It is distinct from the
    #: actual executable entry and is kept so replay can audit offsets.
    model_reference: Optional[Price] = None

    def __post_init__(self) -> None:
        for name, price in (
            ("entry_reference", self.entry_reference),
            ("take_profit", self.take_profit),
            ("stop_loss", self.stop_loss),
            ("model_high", self.model_high),
            ("model_low", self.model_low),
        ):
            if price.amount <= 0:
                raise ValidationError(f"Bracket {name} must be positive")

        if self.model_high.amount < self.model_low.amount:
            raise ValidationError("A bracket cannot be built from high below low")
        if self.model_reference is not None and self.model_reference.amount <= 0:
            raise ValidationError("Bracket model_reference must be positive")

        if self.side is OrderSide.BUY:
            valid = self.stop_loss.amount < self.entry_reference.amount < self.take_profit.amount
        else:
            valid = self.take_profit.amount < self.entry_reference.amount < self.stop_loss.amount
        if not valid:
            raise ValidationError(
                "Bracket levels must be on the correct sides of the entry "
                f"for a {self.side.value} position"
            )

    @classmethod
    def from_model_levels(
        cls,
        side: OrderSide,
        entry_reference: Price,
        predicted_high: float,
        predicted_low: float,
        created_at: Timestamp,
        model_reference: Optional[float] = None,
        reward_risk_multiplier: Optional[float] = None,
    ) -> "TradeBracket":
        """Build a bracket from the absolute high/low model forecast.

        When ``reward_risk_multiplier`` is given, the take-profit distance
        must be at least ``reward_risk_multiplier`` times the stop-loss
        distance. If the raw forecast already satisfies the condition, it
        is used unchanged; otherwise a ``ValidationError`` is raised so
        the caller can skip the trade entirely (TP is never pushed up).
        """
        high = Price(Decimal(str(predicted_high)))
        low = Price(Decimal(str(predicted_low)))
        reference = None if model_reference is None else Price(Decimal(str(model_reference)))
        target = high if side is OrderSide.BUY else low
        stop = low if side is OrderSide.BUY else high

        # Apply reward/risk condition: TP_distance >= multiplier * SL_distance
        # If the raw forecast does NOT satisfy the condition, the trade is
        # REJECTED (ValidationError) rather than moving TP artificially.
        if reward_risk_multiplier is not None and reward_risk_multiplier > 0:
            entry_amount = entry_reference.amount
            tp_distance = abs(target.amount - entry_amount)
            sl_distance = abs(entry_amount - stop.amount)
            min_tp_distance = sl_distance * Decimal(str(reward_risk_multiplier))
            if tp_distance < min_tp_distance:
                raise ValidationError(
                    f"R/R condition not met: TP distance {tp_distance} < "
                    f"{reward_risk_multiplier} x SL distance {sl_distance}"
                )

        return cls(
            side=side,
            entry_reference=entry_reference,
            take_profit=target,
            stop_loss=stop,
            created_at=created_at,
            model_high=high,
            model_low=low,
            model_reference=reference,
        )

    def trigger(
        self,
        candle: Candle,
        policy: SameBarPolicy = SameBarPolicy.STOP_FIRST,
        spread: Decimal = Decimal("0"),
    ) -> Optional[BracketExitReason]:
        """Return the first known exit touched by ``candle``.

        OHLC data does not reveal the intrabar path. If both levels are
        touched, ``policy`` makes that uncertainty explicit. The candle
        high/low are treated as mid prices, so the executable bid/ask
        includes half the configured spread.
        """
        if spread < 0:
            raise ValidationError("spread must not be negative")
        half = spread / Decimal("2")
        if self.side is OrderSide.BUY:
            # Closing a long sells at bid.
            bid_high = candle.high.amount - half
            bid_low = candle.low.amount - half
            hit_target = bid_high >= self.take_profit.amount
            hit_stop = bid_low <= self.stop_loss.amount
        else:
            # Closing a short buys at ask.
            ask_high = candle.high.amount + half
            ask_low = candle.low.amount + half
            hit_target = ask_low <= self.take_profit.amount
            hit_stop = ask_high >= self.stop_loss.amount

        if hit_target and hit_stop:
            if policy is SameBarPolicy.STOP_FIRST:
                return BracketExitReason.STOP_LOSS
            if policy is SameBarPolicy.TARGET_FIRST:
                return BracketExitReason.TAKE_PROFIT
            # SKIP_AMBIGUOUS intentionally leaves the position open.
            return None
        if hit_stop:
            return BracketExitReason.STOP_LOSS
        if hit_target:
            return BracketExitReason.TAKE_PROFIT
        return None

    def exit_price(self, reason: BracketExitReason) -> Price:
        """The level at which the triggered exit is simulated."""
        if reason is BracketExitReason.TAKE_PROFIT:
            return self.take_profit
        return self.stop_loss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "side": self.side.value,
            "entry_reference": str(self.entry_reference.amount),
            "take_profit": str(self.take_profit.amount),
            "stop_loss": str(self.stop_loss.amount),
            "model_high": str(self.model_high.amount),
            "model_low": str(self.model_low.amount),
            "model_reference": (
                None if self.model_reference is None else str(self.model_reference.amount)
            ),
            "high_offset": (
                None
                if self.model_reference is None
                else str(self.model_high.amount / self.model_reference.amount - Decimal("1"))
            ),
            "low_offset": (
                None
                if self.model_reference is None
                else str(self.model_low.amount / self.model_reference.amount - Decimal("1"))
            ),
            "created_at": str(self.created_at),
        }
