"""Command-line interface for the Execution Platform (Sprint P5).

Inspect execution and portfolio accounting without writing code::

    python -m ShadBotTrader.execution_cli quote --mid 2000 --spread 2
    python -m ShadBotTrader.execution_cli execute --side buy --quantity 2
    python -m ShadBotTrader.execution_cli pnl --entry 2000 --exit 2100 --quantity 2
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import IntentType
from ShadBotTrader.domain.strategy.trading_intent import (
    PricePolicy,
    QuantityPolicy,
    TradingIntent,
)
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    InMemoryExecutionJournal,
    InMemoryPortfolioLedger,
    SimulatedExecutionVenue,
)


def cmd_quote(args: argparse.Namespace) -> int:
    """Show how a mid price and spread become tradable prices."""
    now = Timestamp(datetime.now(timezone.utc))
    quote = MarketQuote.from_mid(
        Symbol(args.symbol),
        Price(Decimal(str(args.mid))),
        Decimal(str(args.spread)),
        now,
    )
    print(f"{args.symbol} quote")
    print(f"  bid    : {quote.bid}   <- a SELL executes here")
    print(f"  mid    : {quote.mid}")
    print(f"  ask    : {quote.ask}   <- a BUY executes here")
    print(f"  spread : {quote.spread}")
    return 0


def cmd_pnl(args: argparse.Namespace) -> int:
    """Show the accounting of a round trip, fill by fill."""
    from ShadBotTrader.domain.execution.fill import Fill
    from ShadBotTrader.domain.execution.money import Money

    now = Timestamp(datetime.now(timezone.utc))
    symbol = Symbol(args.symbol)
    quantity = Decimal(str(args.quantity))
    fee = Decimal(str(args.fee))
    long_side = args.side == "buy"

    state = PositionState.flat(symbol, currency=args.currency)
    open_fill = Fill(
        fill_id="open",
        order_id="o1",
        symbol=symbol,
        side=OrderSide.BUY if long_side else OrderSide.SELL,
        quantity=quantity,
        price=Price(Decimal(str(args.entry))),
        executed_at=now,
        fee=Money(fee, args.currency) if fee > 0 else None,
    )
    state, _ = state.apply_fill(open_fill)
    print(f"open  : {state}")

    close_fill = Fill(
        fill_id="close",
        order_id="o2",
        symbol=symbol,
        side=OrderSide.SELL if long_side else OrderSide.BUY,
        quantity=quantity,
        price=Price(Decimal(str(args.exit))),
        executed_at=now,
        fee=Money(fee, args.currency) if fee > 0 else None,
    )
    state, realized = state.apply_fill(close_fill)

    print(f"close : {state}")
    print()
    print(f"  realised (gross) : {realized}")
    print(f"  fees             : {state.total_fees}")
    print(f"  realised (net)   : {state.net_realized_pnl}")
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    """Execute a single synthetic intent and show the resulting book."""
    now = Timestamp(datetime.now(timezone.utc))
    symbol = Symbol(args.symbol)
    quote = MarketQuote.from_mid(
        symbol, Price(Decimal(str(args.mid))), Decimal(str(args.spread)), now
    )

    ledger = InMemoryPortfolioLedger(currency=args.currency, starting_cash=Decimal(str(args.cash)))
    venue = SimulatedExecutionVenue(
        slippage_rate=Decimal(str(args.slippage)),
        commission_rate=Decimal(str(args.commission)),
        currency=args.currency,
    )
    journal = InMemoryExecutionJournal()
    service = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=venue,
        ledger=ledger,
        journal=journal,
    )

    side = OrderSide.BUY if args.side == "buy" else OrderSide.SELL
    intent = TradingIntent(
        intent_id="cli:intent:1",
        decision_id="cli:decision:1",
        strategy_id=StrategyId("cli"),
        strategy_version=StrategyVersion(1),
        symbol=symbol,
        intent_type=IntentType.ENTER_POSITION,
        side=side,
        quantity_policy=QuantityPolicy.fixed(Decimal(str(args.quantity))),
        price_policy=PricePolicy.market(),
        timestamp=now,
        expires_at=Timestamp(now.value + timedelta(seconds=60)),
    )

    context = ExecutionContext(
        timestamp=now,
        quote=quote,
        position=PositionState.flat(symbol, currency=args.currency),
        equity=Decimal(str(args.cash)),
        available_liquidity=Decimal(str(args.liquidity)) if args.liquidity else None,
        currency=args.currency,
    )

    outcome = service.execute(intent, context)

    print(f"=== {args.symbol} ===")
    print(f"quote      : bid {quote.bid} / ask {quote.ask}")
    print(f"intent     : {side.value} {args.quantity}")

    if outcome.order is None:
        print("order      : not resolved")
    else:
        print(f"order      : {outcome.order.order_type.value} {outcome.order.quantity}")

    result = outcome.result
    if result is None:
        print("execution  : (none)")
    elif not result.is_successful:
        reason = result.rejection_reason
        print(f"execution  : REJECTED ({reason.value if reason else 'unknown'})")
        print(f"             {result.message}")
    else:
        print(f"execution  : {result.status.value}")
        print(f"             filled {result.filled_quantity} @ {result.average_fill_price}")
        if result.remaining_quantity > 0:
            print(f"             remaining {result.remaining_quantity}")
        fees = result.total_fees
        if fees is not None:
            print(f"             fees {fees}")

    position = ledger.position(symbol)
    print(f"position   : {'flat' if position.is_flat else position}")
    print(f"cash       : {ledger.cash}")
    if not position.is_flat:
        marked = ledger.equity({str(symbol): quote.mid})
        print(f"equity     : {marked} (marked at mid {quote.mid})")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Execution Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    quote = subparsers.add_parser("quote", help="show bid/mid/ask for a spread")
    quote.add_argument("--symbol", default="XAUUSD_i")
    quote.add_argument("--mid", type=float, default=2000.0)
    quote.add_argument("--spread", type=float, default=2.0)
    quote.set_defaults(func=cmd_quote)

    pnl = subparsers.add_parser("pnl", help="account a round trip")
    pnl.add_argument("--symbol", default="XAUUSD_i")
    pnl.add_argument("--side", choices=("buy", "sell"), default="buy")
    pnl.add_argument("--entry", type=float, default=2000.0)
    pnl.add_argument("--exit", type=float, default=2100.0)
    pnl.add_argument("--quantity", type=float, default=1.0)
    pnl.add_argument("--fee", type=float, default=0.0)
    pnl.add_argument("--currency", default="USD")
    pnl.set_defaults(func=cmd_pnl)

    execute = subparsers.add_parser("execute", help="execute one synthetic intent")
    execute.add_argument("--symbol", default="XAUUSD_i")
    execute.add_argument("--side", choices=("buy", "sell"), default="buy")
    execute.add_argument("--quantity", type=float, default=2.0)
    execute.add_argument("--mid", type=float, default=2000.0)
    execute.add_argument("--spread", type=float, default=2.0)
    execute.add_argument("--slippage", type=float, default=0.0)
    execute.add_argument("--commission", type=float, default=0.0)
    execute.add_argument("--liquidity", type=float, default=None)
    execute.add_argument("--cash", type=float, default=100000.0)
    execute.add_argument("--currency", default="USD")
    execute.set_defaults(func=cmd_execute)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
