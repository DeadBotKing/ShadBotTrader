"""Backtest engine (Phase 16, sections 2, 21-23).

Orchestrates the platforms that already exist — it does not reimplement
any of them::

    MarketEvent -> PredictionSource -> Strategy -> RiskGate -> Intent
                -> IntentResolver -> SimulatedVenue -> Fills
                -> PortfolioLedger -> EquityPoint

Guarantees:

* time comes only from the ``SimulationClock`` (section 9)
* events are drained from a totally-ordered queue (section 18)
* ``step()`` processes exactly one event, for debugging (section 23)
* the same data + configuration + seed reproduce the run (section 10)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.clock import SimulationClock
from ShadBotTrader.domain.simulation.equity_curve import EquityCurve, EquityPoint
from ShadBotTrader.domain.simulation.market_event import MarketEvent, SimulationEventQueue
from ShadBotTrader.domain.simulation.performance import (
    PerformanceMetrics,
    TradeRecord,
    sharpe_ratio,
    standard_deviation,
    summarise_trades,
)
from ShadBotTrader.domain.simulation.ports import (
    NullSimulationReporter,
    PredictionSource,
    SimulationMarketDataProvider,
    SimulationReporter,
)
from ShadBotTrader.domain.simulation.session import (
    SimulationConfiguration,
    SimulationSession,
)
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.execution.portfolio_ledger import InMemoryPortfolioLedger


@dataclass(frozen=True)
class BacktestResult:
    """Everything a finished run produced."""

    session: SimulationSession
    metrics: PerformanceMetrics
    equity_curve: EquityCurve
    trades: List[TradeRecord]
    bars_processed: int
    intents_created: int
    fills: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session.session_id,
            "status": self.session.status.value,
            "bars_processed": self.bars_processed,
            "intents_created": self.intents_created,
            "fills": self.fills,
            **self.metrics.to_dict(),
        }


class BacktestEngine:
    """Drives the trading chain over historical market events."""

    def __init__(
        self,
        session: SimulationSession,
        data_provider: SimulationMarketDataProvider,
        prediction_source: PredictionSource,
        trading_service: TradingDecisionService,
        execution_service: ExecutionService,
        ledger: InMemoryPortfolioLedger,
        timeframe: Timeframe,
        model_id: str = "gold_direction",
        reporter: Optional[SimulationReporter] = None,
    ) -> None:
        self._session = session
        self._data = data_provider
        self._predictions = prediction_source
        self._trading = trading_service
        self._execution = execution_service
        self._ledger = ledger
        self._timeframe = timeframe
        self._model_id = model_id
        self._reporter = reporter or NullSimulationReporter()

        events = data_provider.events()
        start = events[0].event_time if events else session.start_time
        end = events[-1].event_time if events else session.end_time
        self._clock = SimulationClock(start_time=start, end_time=end)

        self._queue = SimulationEventQueue()
        self._queue.push_all(events)

        self._equity_curve = EquityCurve()
        self._trades: List[TradeRecord] = []
        self._bars = 0
        self._intents = 0
        self._fills = 0
        self._last_realized = Decimal("0")
        self._last_fees = Decimal("0")
        self._open_bar: Optional[str] = None

    # -- state -------------------------------------------------------------
    @property
    def clock(self) -> SimulationClock:
        return self._clock

    @property
    def session(self) -> SimulationSession:
        return self._session

    @property
    def equity_curve(self) -> EquityCurve:
        return self._equity_curve

    @property
    def pending_events(self) -> int:
        return len(self._queue)

    # -- execution ---------------------------------------------------------
    def step(self) -> Optional[MarketEvent]:
        """Process exactly one event and return it (section 23)."""
        if self._queue.is_empty:
            return None

        event = self._queue.pop()
        self._clock.advance_to(event.event_time)
        self._process(event)
        self._session.count_event()
        return event

    def run(self) -> BacktestResult:
        """Run the whole session to completion."""
        config = self._session.configuration
        self._session.start()
        self._reporter.on_session_start(self._session)

        try:
            while not self._queue.is_empty:
                event = self.step()
                if event is not None:
                    self._reporter.on_step(event, str(self._current_equity()))
            self._session.complete()
        except Exception as error:  # pragma: no cover - defensive
            self._session.fail(str(error))
            raise

        metrics = self._metrics(config)
        self._reporter.on_session_end(self._session, metrics, list(self._trades))

        return BacktestResult(
            session=self._session,
            metrics=metrics,
            equity_curve=self._equity_curve,
            trades=list(self._trades),
            bars_processed=self._bars,
            intents_created=self._intents,
            fills=self._fills,
        )

    # -- one bar -----------------------------------------------------------
    def _process(self, event: MarketEvent) -> None:
        candle = event.candle
        if candle is None:
            return

        self._bars += 1
        observe = getattr(self._predictions, "observe", None)
        if callable(observe):
            observe(event)

        position = self._ledger.position(event.symbol)
        warmup_done = self._bars > self._session.configuration.warmup_bars

        if warmup_done:
            value = self._predictions.predict(event)
            if value is not None:
                self._trade_bar(event, value, position)

        self._record_equity(event, candle.close)

    def _trade_bar(self, event: MarketEvent, value: float, position: Any) -> None:
        now = self._clock.current_time

        strategy_context = StrategyContext(
            timestamp=now,
            symbol=event.symbol,
            timeframe=self._timeframe,
            predictions=[
                PredictionView(
                    model_id=self._model_id,
                    model_version=1,
                    value=value,
                    confidence=self._predictions.confidence(event),
                    generated_at=now,
                )
            ],
            portfolio=PortfolioView(
                equity=self._ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=0 if position.is_flat else 1,
            ),
        )

        outcome = self._trading.evaluate(strategy_context)
        if outcome.intent is None:
            return

        self._intents += 1

        quote = self._data.quote_at(event.symbol, event.event_time)
        if quote is None:
            return

        execution_context = ExecutionContext(
            timestamp=now,
            quote=quote,
            position=position,
            equity=self._ledger.cash.amount,
            currency=self._session.configuration.base_currency,
        )

        was_flat = position.is_flat
        result = self._execution.execute(outcome.intent, execution_context)
        if not result.executed:
            return

        self._fills += 1
        self._capture_trade(event, was_flat)

    def _capture_trade(self, event: MarketEvent, was_flat: bool) -> None:
        """Turn a realised PnL change into a completed TradeRecord."""
        if was_flat:
            self._open_bar = str(self._clock.current_time)

        realized = self._ledger.realized_pnl.amount
        fees = self._ledger.total_fees.amount
        delta = realized - self._last_realized
        fee_delta = fees - self._last_fees

        if delta != 0:
            self._trades.append(
                TradeRecord(
                    symbol=str(event.symbol),
                    realized_pnl=delta,
                    fees=fee_delta,
                    opened_at=self._open_bar or "",
                    closed_at=str(self._clock.current_time),
                )
            )
            self._open_bar = None

        self._last_realized = realized
        self._last_fees = fees

    def _record_equity(self, event: MarketEvent, close: Price) -> None:
        prices = {str(event.symbol): close}
        equity = self._ledger.equity(prices)
        position = self._ledger.position(event.symbol)

        self._equity_curve.record(
            EquityPoint(
                timestamp=self._clock.current_time,
                equity=equity.amount,
                cash=self._ledger.cash.amount,
                realized_pnl=self._ledger.realized_pnl.amount,
                unrealized_pnl=self._ledger.unrealized_pnl(prices).amount,
                open_positions=0 if position.is_flat else 1,
            )
        )

    def _current_equity(self) -> Decimal:
        final = self._equity_curve.final_equity
        return final if final is not None else self._ledger.cash.amount

    # -- reporting -----------------------------------------------------------
    def _metrics(self, config: SimulationConfiguration) -> PerformanceMetrics:
        curve = self._equity_curve
        starting = curve.starting_equity or config.initial_capital
        final = curve.final_equity or starting
        summary = summarise_trades(self._trades)
        returns = curve.returns()

        return PerformanceMetrics(
            starting_equity=starting,
            final_equity=final,
            total_return=curve.total_return or Decimal("0"),
            total_return_percent=curve.total_return_percent or Decimal("0"),
            max_drawdown=curve.max_drawdown,
            max_drawdown_percent=curve.max_drawdown_percent,
            trade_count=len(self._trades),
            win_count=int(summary["wins"]),
            loss_count=int(summary["losses"]),
            gross_profit=summary["gross_profit"],
            gross_loss=summary["gross_loss"],
            total_fees=self._ledger.total_fees.amount,
            sharpe=sharpe_ratio(returns),
            volatility=standard_deviation(returns),
        )
