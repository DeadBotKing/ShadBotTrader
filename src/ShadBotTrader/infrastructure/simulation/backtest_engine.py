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

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.execution.ports import ReportingLedger
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.bracket import BracketExitReason, TradeBracket
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
from ShadBotTrader.domain.simulation.replay import (
    MARKER_ADJUST,
    MARKER_ENTRY,
    MARKER_EXIT,
    ReplayRecorder,
    ReplayTape,
    TradeMarker,
)
from ShadBotTrader.domain.simulation.session import (
    SimulationConfiguration,
    SimulationSession,
)
from ShadBotTrader.domain.simulation.simulation_types import EntryTiming
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)


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
    #: Count of exits selected by the OHLC bracket policy.
    bracket_exit_counts: Dict[str, int] = field(default_factory=dict)
    #: Bar-by-bar recording, present only when the run was asked to record
    #: one (``record_replay=True``). A sweep of hundreds of simulations
    #: should not pay for a tape nobody reads.
    tape: Optional[ReplayTape] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session.session_id,
            "status": self.session.status.value,
            "bars_processed": self.bars_processed,
            "intents_created": self.intents_created,
            "fills": self.fills,
            "bracket_exit_counts": dict(self.bracket_exit_counts),
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
        ledger: ReportingLedger,
        timeframe: Timeframe,
        model_id: str = "gold_direction",
        reporter: Optional[SimulationReporter] = None,
        record_replay: bool = False,
        entry_timing: EntryTiming = EntryTiming.SIGNAL_CLOSE,
        bracket_provider: Any = None,
        exit_trading_service: Optional[TradingDecisionService] = None,
        filter_zero_bar: bool = False,
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
        self._entry_timing = (
            entry_timing if isinstance(entry_timing, EntryTiming) else EntryTiming(entry_timing)
        )
        self._bracket_provider = bracket_provider
        self._exit_trading = exit_trading_service
        self._pending_entry: Optional[Dict[str, Any]] = None
        self._bracket: Optional[TradeBracket] = None
        self._filter_zero_bar = filter_zero_bar
        self._open_bar_index: Optional[int] = None
        self._bracket_exit_counts: Dict[str, int] = {
            BracketExitReason.TAKE_PROFIT.value: 0,
            BracketExitReason.STOP_LOSS.value: 0,
        }

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
        # Fees belong to the whole round trip.  The old implementation
        # attached only the closing-fill fee to TradeRecord, so opening
        # commissions disappeared from gross/net trade statistics even
        # though they were deducted from cash and final equity.
        self._open_trade_fees = Decimal("0")
        self._open_trade_realized = Decimal("0")
        self._spread_cost = Decimal("0")
        self._slippage_cost = Decimal("0")
        self._open_bar: Optional[str] = None

        self._recorder: Optional[ReplayRecorder] = None
        if record_replay:
            symbol = str(data_provider.events()[0].symbol) if events else ""
            self._recorder = ReplayRecorder(
                session_id=session.session_id,
                symbol=symbol,
                timeframe=str(timeframe),
                starting_equity=session.configuration.initial_capital,
            )
        self._last_prediction: Optional[float] = None

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

    @property
    def tape(self) -> Optional[ReplayTape]:
        """The replay recorded so far, or None when recording is off.

        Available mid-run too, so a caller driving ``step()`` by hand can
        watch the tape grow.
        """
        return self._recorder.build() if self._recorder is not None else None

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
            bracket_exit_counts=dict(self._bracket_exit_counts),
            tape=self.tape,
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

        self._last_prediction = None
        warmup_done = self._bars > self._session.configuration.warmup_bars

        if self._bracket_provider is not None:
            # A bracketed run is position-led: an open trade is managed by
            # its fixed TP/SL and later model signals are ignored until the
            # position is closed.  This is the requested HOLD/TP/SL flow.
            self._execute_pending_entry(event)
            if self._check_bracket(event):
                self._record_equity(event, candle.close)
                self._record_replay_bar(event)
                return

            position = self._ledger.position(event.symbol)
            if position.is_flat and warmup_done:
                value = self._predictions.predict(event)
                self._last_prediction = value
                if value is not None:
                    self._trade_bar(event, value, position)
        else:
            # Backward-compatible single-model baseline path.
            position = self._ledger.position(event.symbol)
            if warmup_done:
                value = self._predictions.predict(event)
                self._last_prediction = value
                if value is not None:
                    self._trade_bar(event, value, position)

        self._record_equity(event, candle.close)
        self._record_replay_bar(event)

    def _trade_bar(self, event: MarketEvent, value: float, position: Any) -> None:
        """Evaluate a signal and either fill it or schedule next-open entry."""
        now = self._clock.current_time
        metadata: Dict[str, Any] = {}
        signal_forecast = getattr(self._predictions, "last_signal_forecast", None)
        range_forecast = getattr(self._predictions, "last_range_forecast", None)
        if signal_forecast is not None:
            metadata["signal_forecast"] = signal_forecast
        if range_forecast is not None:
            metadata["range_forecast"] = range_forecast

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
                    metadata=metadata,
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
        if (
            self._entry_timing is EntryTiming.NEXT_OPEN
            and outcome.intent.intent_type.value == "enter_position"
        ):
            # Keep the already-approved intent and the model's already-made
            # range forecast.  Re-running the model on the next bar would
            # change the trade it is meant to explain.
            self._pending_entry = {"outcome": outcome, "event": event}
            return

        quote = self._quote_for_event(event, opening=False)
        if quote is None:
            return
        bracket = None
        if self._bracket_provider is not None and event.candle is not None:
            entry_price = quote.ask if outcome.intent.side.value == "buy" else quote.bid
            bracket = self._bracket_provider.bracket_for(event, outcome.intent.side, entry_price)
            if bracket is None:
                return
        if self._execute_outcome(event, outcome, position, quote, bracket=bracket):
            self._bracket = bracket

    def _execute_outcome(
        self,
        event: MarketEvent,
        outcome: Any,
        position: Any,
        quote: Any,
        bracket: Optional[TradeBracket] = None,
    ) -> bool:
        """Execute one approved outcome and record its fill."""
        execution_context = ExecutionContext(
            timestamp=self._clock.current_time,
            quote=quote,
            position=position,
            equity=self._ledger.cash.amount,
            currency=self._session.configuration.base_currency,
        )
        was_flat = position.is_flat
        result = self._execution.execute(outcome.intent, execution_context)
        if not result.executed:
            return False

        self._capture_execution_costs(result, quote)
        self._fills += 1
        realized_delta, fee_delta, was_filtered = self._capture_trade(event, was_flat)
        # اگه trade توسط filter_zero_bar فیلتر شد،
        # marker هم نباید در tape ثبت بشه — وگرنه round_trips != trades
        if not was_filtered:
            self._mark_fill(
                event,
                outcome=result,
                realized=realized_delta,
                fees=fee_delta,
                bracket=bracket,
            )
        return True

    def _capture_execution_costs(self, outcome: Any, quote: Any) -> None:
        """Separate spread and adverse slippage from commission fees."""
        execution = outcome.result
        if execution is None:
            return
        for fill in execution.fills:
            touch = quote.ask if fill.side.value == "buy" else quote.bid
            self._spread_cost += fill.quantity * abs(touch.amount - quote.mid.amount)
            self._slippage_cost += fill.quantity * abs(fill.price.amount - touch.amount)

    def _quote_for_event(
        self,
        event: MarketEvent,
        opening: bool = False,
        explicit_mid: Optional[Price] = None,
    ) -> Any:
        """Ask a candle provider for close/open/explicit-level pricing."""
        if explicit_mid is not None:
            quote_for = getattr(self._data, "quote_for", None)
            if callable(quote_for) and event.candle is not None:
                return quote_for(event.candle, mid=explicit_mid)
            return self._data.quote_at(event.symbol, event.event_time)

        if opening and event.candle is not None:
            quote_for = getattr(self._data, "quote_for", None)
            if callable(quote_for):
                return quote_for(event.candle, mid=event.candle.open)
        return self._data.quote_at(event.symbol, event.event_time)

    def _execute_pending_entry(self, event: MarketEvent) -> None:
        """Fill an intent created on the preceding signal bar at this open."""
        pending = self._pending_entry
        if pending is None:
            return
        self._pending_entry = None
        outcome = pending["outcome"]
        intent = outcome.intent
        position = self._ledger.position(event.symbol)
        if not position.is_flat:
            return
        quote = self._quote_for_event(event, opening=True)
        if quote is None:
            return
        # The bracket is attached only after the actual entry fill, but a
        # next-open gap that invalidates both levels must not create an
        # unprotected position.
        provider = self._bracket_provider
        bracket = None
        if provider is not None and event.candle is not None:
            bracket = provider.bracket_for(
                event, intent.side, quote.ask if intent.side.value == "buy" else quote.bid
            )
            if bracket is None:
                return
        if self._execute_outcome(event, outcome, position, quote, bracket=bracket):
            self._bracket = bracket

    def _check_bracket(self, event: MarketEvent) -> bool:
        """Close the open position when its TP/SL is touched."""
        bracket = self._bracket
        if bracket is None or event.candle is None:
            return False
        position = self._ledger.position(event.symbol)
        if position.is_flat:
            self._bracket = None
            return False

        reason = bracket.trigger(
            event.candle,
            self._session.configuration.same_bar_policy,
            spread=self._session.configuration.spread,
        )
        if reason is None:
            return False

        exit_service = self._exit_trading
        if exit_service is None:
            return False
        timestamp = self._clock.current_time
        context = StrategyContext(
            timestamp=timestamp,
            symbol=event.symbol,
            timeframe=self._timeframe,
            portfolio=PortfolioView(
                equity=self._ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=1,
            ),
            metadata={
                "bracket_exit_reason": reason.value,
                "take_profit": str(bracket.take_profit.amount),
                "stop_loss": str(bracket.stop_loss.amount),
            },
        )
        outcome = exit_service.evaluate(context)
        if outcome.intent is None:
            return False
        self._intents += 1

        level = bracket.exit_price(reason)
        # Make the executable side's touch equal the bracket level.  The
        # venue may still apply configured slippage and commission.
        spread = getattr(self._data, "_spread", Decimal("0"))
        half = spread / Decimal("2")
        if position.is_long:
            mid = Price(level.amount + half)  # sell hits bid == level
        else:
            mid_amount = level.amount - half  # buy lifts ask == level
            if mid_amount <= 0:
                return False
            mid = Price(mid_amount)
        quote = self._quote_for_event(event, explicit_mid=mid)
        if quote is None:
            return False

        if self._execute_outcome(event, outcome, position, quote, bracket=bracket):
            self._bracket_exit_counts[reason.value] += 1
            self._bracket = None
            return True
        return False

    def _mark_fill(
        self,
        event: MarketEvent,
        outcome: Any,
        realized: Decimal,
        fees: Decimal,
        bracket: Optional[TradeBracket] = None,
    ) -> None:
        """Record the fill on the replay tape, if one is being recorded."""
        recorder = self._recorder
        execution = outcome.result
        if recorder is None or execution is None:
            return

        average = execution.average_fill_price
        if average is None:
            return

        position_after = self._ledger.position(event.symbol).signed_quantity
        if position_after == 0:
            kind = MARKER_EXIT
        elif outcome.intent is not None and outcome.intent.intent_type.value == "exit_position":
            # A partial exit still leaves exposure behind.
            kind = MARKER_ADJUST
        elif realized != 0:
            kind = MARKER_ADJUST
        else:
            kind = MARKER_ENTRY

        # Strategy context contains the exact Signal probabilities and
        # Range forecast that approved this entry. Keep primitive values
        # only so the tape remains JSON/CSV serialisable.
        decision_metadata: Dict[str, Any] = {}
        if outcome.intent is not None:
            decision_metadata = {
                key: value
                for key, value in outcome.intent.context.items()
                if isinstance(value, (str, int, float, bool)) or value is None
            }

        bracket_metadata: Dict[str, Any] = {}
        if bracket is not None:
            bracket_metadata = {
                "bracket_side": bracket.side.value,
                "entry_reference": str(bracket.entry_reference.amount),
                "take_profit": str(bracket.take_profit.amount),
                "stop_loss": str(bracket.stop_loss.amount),
                "model_high": str(bracket.model_high.amount),
                "model_low": str(bracket.model_low.amount),
                "model_reference": (
                    None if bracket.model_reference is None else str(bracket.model_reference.amount)
                ),
                "high_offset": (
                    None
                    if bracket.model_reference is None
                    else str(
                        bracket.model_high.amount / bracket.model_reference.amount - Decimal("1")
                    )
                ),
                "low_offset": (
                    None
                    if bracket.model_reference is None
                    else str(
                        bracket.model_low.amount / bracket.model_reference.amount - Decimal("1")
                    )
                ),
            }

        fill_reason = outcome.intent.reason if outcome.intent is not None else ""
        if kind == MARKER_EXIT and outcome.intent is not None:
            fill_reason = str(outcome.intent.context.get("bracket_exit_reason", fill_reason))

        recorder.mark(
            TradeMarker(
                bar_index=self._bars - 1,
                timestamp=str(self._clock.current_time),
                side=outcome.order.side.value if outcome.order is not None else "",
                kind=kind,
                price=average.amount,
                quantity=execution.filled_quantity,
                position_after=position_after,
                realized_pnl=realized if kind != MARKER_ENTRY else None,
                fees=fees,
                reason=fill_reason,
                metadata={**decision_metadata, **bracket_metadata},
            )
        )

    def _record_replay_bar(self, event: MarketEvent) -> None:
        """Append the finished bar to the tape."""
        recorder = self._recorder
        candle = event.candle
        if recorder is None or candle is None:
            return

        point = self._equity_curve.points[-1] if self._equity_curve.points else None
        recorder.record_bar(
            index=self._bars - 1,
            timestamp=str(self._clock.current_time),
            open_price=candle.open.amount,
            high=candle.high.amount,
            low=candle.low.amount,
            close=candle.close.amount,
            volume=candle.volume,
            equity=point.equity if point is not None else self._ledger.cash.amount,
            cash=self._ledger.cash.amount,
            position=self._ledger.position(event.symbol).signed_quantity,
            prediction=self._last_prediction,
        )

    def _capture_trade(self, event: MarketEvent, was_flat: bool) -> tuple[Decimal, Decimal, bool]:
        """Turn a realised PnL change into a completed TradeRecord.

        Returns the realised PnL and the fees this fill alone produced, so
        the caller can attach them to the replay tape without recomputing.
        """
        if was_flat:
            self._open_bar = str(self._clock.current_time)
            self._open_bar_index = self._bars

        realized = self._ledger.realized_pnl.amount
        fees = self._ledger.total_fees.amount
        delta = realized - self._last_realized
        fee_delta = fees - self._last_fees

        # The entry fill has no realised PnL yet, but its commission must
        # stay attached to this trade until the eventual exit.  Otherwise
        # total equity includes the fee while TradeRecord/expectancy do
        # not, creating the exact gap seen in the dashboard report.
        if was_flat:
            self._open_trade_fees = fee_delta
            self._open_trade_realized = Decimal("0")
        else:
            self._open_trade_fees += fee_delta
            self._open_trade_realized += delta

        position_after = self._ledger.position(event.symbol)
        if not was_flat and position_after.is_flat:
            # Calculate bars held for this trade
            bars_held = self._bars - (self._open_bar_index or self._bars)
            # A zero-PnL close is still a completed trade and must be
            # counted.  For the normal full-fill path this is one entry
            # plus one exit, with both commissions included.
            # When filter_zero_bar is enabled, skip trades that were
            # opened and closed on the same bar (0-bar trades).
            if self._filter_zero_bar and bars_held == 0:
                # Skip recording this trade but still update accounting.
                # was_filtered=True signals _execute_outcome to skip _mark_fill
                # so tape.round_trips() stays in sync with self._trades.
                self._open_bar = None
                self._open_bar_index = None
                self._open_trade_fees = Decimal("0")
                self._open_trade_realized = Decimal("0")
                self._last_realized = realized
                self._last_fees = fees
                return delta, fee_delta, True   # ← filtered

            self._trades.append(
                TradeRecord(
                    symbol=str(event.symbol),
                    realized_pnl=self._open_trade_realized,
                    fees=self._open_trade_fees,
                    opened_at=self._open_bar or "",
                    closed_at=str(self._clock.current_time),
                )
            )
            self._open_bar = None
            self._open_bar_index = None
            self._open_trade_fees = Decimal("0")
            self._open_trade_realized = Decimal("0")

        self._last_realized = realized
        self._last_fees = fees
        return delta, fee_delta, False   # ← not filtered

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
            spread_cost=self._spread_cost,
            slippage_cost=self._slippage_cost,
            net_profit=summary["net_profit"],
            net_loss=summary["net_loss"],
            sharpe=sharpe_ratio(returns),
            volatility=standard_deviation(returns),
        )
