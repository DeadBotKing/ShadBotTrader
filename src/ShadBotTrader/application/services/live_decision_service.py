"""The five-minute live decision loop (Phase 31).

This is the piece that was missing: everything else existed, but nothing
joined it up. One tick does exactly this:

    fetch 1 x 5M candle and 1 x 1H candle
        -> push into the 800-candle rolling buffers
        -> recompute features over each buffer
        -> take the newest 500 rows -> (500, 123)
        -> range model  (1H)  -> predicted high / low
        -> signal model (5M)  -> buy / sell / hold + probabilities
        -> DualModelStrategy   -> signal
        -> risk gate           -> intent
        -> execution           -> fill

Design rule: **a tick must never raise.** A five-minute loop that crashes
on a broker hiccup is worse than one that skips a tick and says why, so
every failure becomes a ``TickResult`` with a reason attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.ai.live_matrix import LiveMatrixBuilder
from ShadBotTrader.infrastructure.data.live_buffer import LiveMarketData
from ShadBotTrader.infrastructure.trading.dual_model_strategy import (
    RANGE_FORECAST_KEY,
    SIGNAL_FORECAST_KEY,
)


@dataclass
class TickResult:
    """Everything one tick produced — including why it did nothing."""

    timestamp: str
    status: str  # "traded" | "no_trade" | "skipped" | "failed"
    reason: str = ""
    signal_forecast: Optional[SignalForecast] = None
    range_forecast: Optional[RangeForecast] = None
    signal_type: str = ""
    decision: str = ""
    executed: bool = False
    filled_quantity: Optional[Decimal] = None
    fill_price: Optional[Decimal] = None
    buffer_states: Dict[str, Any] = field(default_factory=dict)

    @property
    def acted(self) -> bool:
        return self.status == "traded"

    def summary_lines(self) -> List[str]:
        """A few human-readable lines for a console or the dashboard."""
        lines = [f"[{self.status}] {self.reason}" if self.reason else f"[{self.status}]"]
        if self.signal_forecast is not None:
            signal = self.signal_forecast
            lines.append(
                f"  signal : sell {signal.sell_probability:.1%} | "
                f"hold {signal.hold_probability:.1%} | "
                f"buy {signal.buy_probability:.1%} -> {signal.describe()}"
            )
        if self.range_forecast is not None:
            extremes = self.range_forecast
            ratio = extremes.reward_risk()
            lines.append(
                f"  range  : high {extremes.predicted_high:.2f} | "
                f"low {extremes.predicted_low:.2f} | "
                f"r/r {'n/a' if ratio is None else f'{ratio:.2f}'}"
            )
        if self.executed:
            lines.append(f"  filled : {self.filled_quantity} @ {self.fill_price}")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "reason": self.reason,
            "signal": self.signal_forecast.to_dict() if self.signal_forecast else None,
            "range": self.range_forecast.to_dict() if self.range_forecast else None,
            "signal_type": self.signal_type,
            "decision": self.decision,
            "executed": self.executed,
            "filled_quantity": (
                None if self.filled_quantity is None else str(self.filled_quantity)
            ),
            "fill_price": None if self.fill_price is None else str(self.fill_price),
            "buffers": self.buffer_states,
        }


class LiveDecisionService:
    """Runs one live tick end to end."""

    def __init__(
        self,
        symbol: str,
        market: LiveMarketData,
        matrix_builder: LiveMatrixBuilder,
        trading_service: Any,
        execution_service: Any = None,
        ledger: Any = None,
        range_predictor: Any = None,
        signal_predictor: Any = None,
        range_artifact: Any = None,
        signal_artifact: Any = None,
        signal_timeframe: str = "5M",
        range_timeframe: str = "1H",
    ) -> None:
        self._symbol = symbol
        self._market = market
        self._builder = matrix_builder
        self._trading = trading_service
        self._execution = execution_service
        self._ledger = ledger
        self._range_predictor = range_predictor
        self._signal_predictor = signal_predictor
        self._range_artifact = range_artifact
        self._signal_artifact = signal_artifact
        self._signal_timeframe = signal_timeframe
        self._range_timeframe = range_timeframe
        self._history: List[TickResult] = []

    @property
    def history(self) -> List[TickResult]:
        return list(self._history)

    # ------------------------------------------------------------- data --
    def ingest(self, timeframe: str, candle: Candle) -> str:
        """Push one candle into its buffer, returning what happened."""
        return self._market.push(timeframe, candle)

    def prime(self, timeframe: str, candles: Sequence[Candle]) -> Dict[str, int]:
        return self._market.prime(timeframe, candles)

    # ------------------------------------------------------------- tick --
    def tick(
        self,
        now: Optional[datetime] = None,
        equity: Decimal = Decimal("100"),
    ) -> TickResult:
        """Run one decision cycle. Never raises."""
        moment = now or datetime.now(timezone.utc)
        result = TickResult(timestamp=moment.isoformat(), status="skipped")
        result.buffer_states = self._market.states()

        try:
            return self._tick(moment, equity, result)
        except Exception as error:  # a loop must survive a bad tick
            result.status = "failed"
            result.reason = f"{type(error).__name__}: {error}"
            self._history.append(result)
            return result

    def _tick(
        self,
        moment: datetime,
        equity: Decimal,
        result: TickResult,
    ) -> TickResult:
        # --- 1. build the model inputs ---------------------------------
        signal_window, reason = self._builder.try_build(self._market.buffer(self._signal_timeframe))
        if signal_window is None:
            result.reason = reason
            self._history.append(result)
            return result

        range_window = None
        if self._range_timeframe in self._market.timeframes:
            range_window, range_reason = self._builder.try_build(
                self._market.buffer(self._range_timeframe)
            )
            if range_window is None and self._range_predictor is not None:
                result.reason = range_reason
                self._history.append(result)
                return result

        # --- 2. ask both models ----------------------------------------
        signal_forecast = self._predict_signal(signal_window)
        if signal_forecast is None:
            result.reason = "no signal model available"
            self._history.append(result)
            return result
        result.signal_forecast = signal_forecast

        if range_window is not None:
            result.range_forecast = self._predict_range(range_window)

        # --- 3. strategy -> risk gate -> intent -------------------------
        timestamp = Timestamp(moment)
        position_quantity = Decimal("0")
        if self._ledger is not None:
            position_quantity = self._ledger.position(Symbol(self._symbol)).signed_quantity

        context = StrategyContext(
            timestamp=timestamp,
            symbol=Symbol(self._symbol),
            timeframe=Timeframe(self._signal_timeframe),
            predictions=[
                PredictionView(
                    model_id="dual_model",
                    model_version=1,
                    value=signal_forecast.directional_confidence,
                    confidence=signal_forecast.confidence,
                    generated_at=timestamp,
                    metadata={
                        SIGNAL_FORECAST_KEY: signal_forecast,
                        RANGE_FORECAST_KEY: result.range_forecast,
                    },
                )
            ],
            portfolio=PortfolioView(
                equity=equity,
                open_position_quantity=position_quantity,
                open_position_count=0 if position_quantity == 0 else 1,
            ),
        )

        outcome = self._trading.evaluate(context)
        result.signal_type = outcome.signal.signal_type.value if outcome.signal else ""
        result.decision = outcome.decision.decision_type.value if outcome.decision else ""

        if outcome.intent is None:
            result.status = "no_trade"
            result.reason = (
                outcome.rejected_reason
                or (outcome.signal.reason if outcome.signal else "")
                or "no intent produced"
            )
            self._history.append(result)
            return result

        # --- 4. execute --------------------------------------------------
        if self._execution is None:
            result.status = "no_trade"
            result.reason = "intent produced but no execution venue is configured"
            self._history.append(result)
            return result

        execution_outcome = self._execute(outcome.intent, signal_window, timestamp, equity)
        if execution_outcome is None or not execution_outcome.executed:
            result.status = "no_trade"
            result.reason = (
                execution_outcome.rejected_reason
                if execution_outcome is not None
                else "execution produced no result"
            )
            self._history.append(result)
            return result

        fill_result = execution_outcome.result
        result.status = "traded"
        result.executed = True
        result.filled_quantity = fill_result.filled_quantity
        average = fill_result.average_fill_price
        result.fill_price = average.amount if average is not None else None
        result.reason = outcome.signal.reason if outcome.signal else ""

        self._history.append(result)
        return result

    # -------------------------------------------------------- internals --
    def _predict_signal(self, window: Any) -> Optional[SignalForecast]:
        if self._signal_predictor is None or self._signal_artifact is None:
            return None
        return self._signal_predictor.forecast(
            self._signal_artifact,
            window.rows,
            generated_at=window.last_timestamp,
        )

    def _predict_range(self, window: Any) -> Optional[RangeForecast]:
        if self._range_predictor is None or self._range_artifact is None:
            return None
        return self._range_predictor.forecast(
            self._range_artifact,
            window.rows,
            reference_close=window.reference_close,
            generated_at=window.last_timestamp,
        )

    def _execute(
        self,
        intent: Any,
        window: Any,
        timestamp: Timestamp,
        equity: Decimal,
    ) -> Any:
        from ShadBotTrader.domain.execution.market_view import (
            ExecutionContext,
            MarketQuote,
        )
        from ShadBotTrader.domain.market.price import Price

        close = Decimal(str(window.reference_close))
        quote = MarketQuote.from_mid(
            symbol=Symbol(self._symbol),
            mid=Price(close),
            spread=Decimal("4"),
            timestamp=timestamp,
        )
        position = self._ledger.position(Symbol(self._symbol)) if self._ledger is not None else None
        if position is None:
            return None

        context = ExecutionContext(
            timestamp=timestamp,
            quote=quote,
            position=position,
            equity=equity,
            currency="USD",
        )
        return self._execution.execute(intent, context)
