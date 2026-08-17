"""Application service: assemble and run a backtest.

Phase 16, section 2 — the Simulation Platform *orchestrates* the other
platforms rather than duplicating them. This service is the composition
root that wires a historical dataset to the very same trading, risk,
execution and portfolio components used in live operation. If a backtest
passes here, it exercised production logic.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence

from ShadBotTrader.application.persistence_context import PersistenceContext
from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.ports import ExecutionJournal, ReportingLedger
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.ports import PredictionSource, SimulationReporter
from ShadBotTrader.domain.simulation.session import (
    SimulationConfiguration,
    SimulationSession,
)
from ShadBotTrader.domain.strategy.ports import DecisionJournal
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.simulation.backtest_engine import (
    BacktestEngine,
    BacktestResult,
)
from ShadBotTrader.infrastructure.simulation.candle_data_provider import (
    CandleMarketDataProvider,
)
from ShadBotTrader.infrastructure.simulation.prediction_sources import (
    MomentumPredictionSource,
)
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)


class BacktestService:
    """Builds a fully wired backtest from a candle series."""

    def __init__(
        self,
        configuration: Optional[SimulationConfiguration] = None,
        risk_policy: Optional[RiskPolicy] = None,
        base_quantity: Decimal = Decimal("1"),
        strategy_min_confidence: float = 0.55,
        allow_reversal: bool = False,
        persistence: Optional[PersistenceContext] = None,
    ) -> None:
        self._configuration = configuration or SimulationConfiguration()
        self._risk_policy = risk_policy or RiskPolicy()
        self._base_quantity = base_quantity
        self._strategy_min_confidence = strategy_min_confidence
        self._allow_reversal = allow_reversal
        # Defaults to in-memory: a backtest sweep must not write to disk
        # unless the caller explicitly asked for it.
        self._persistence = persistence or PersistenceContext()

        # exposed so a caller can inspect the books after a run
        self.ledger: Optional[ReportingLedger] = None
        self.decision_journal: Optional[DecisionJournal] = None
        self.execution_journal: Optional[ExecutionJournal] = None

    def build(
        self,
        session_id: str,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: Sequence[Candle],
        prediction_source: Optional[PredictionSource] = None,
        reporter: Optional[SimulationReporter] = None,
        record_replay: bool = False,
    ) -> BacktestEngine:
        """Wire every component and return the ready engine."""
        if not candles:
            raise ValueError("A backtest needs at least one candle")

        config = self._configuration
        ordered = sorted(candles, key=lambda candle: candle.open_time.value)
        start: Timestamp = ordered[0].open_time
        end: Timestamp = ordered[-1].open_time

        data_provider = CandleMarketDataProvider(
            symbol=symbol, candles=ordered, spread=config.spread
        )

        self._persistence.currency = config.base_currency
        ledger = self._persistence.portfolio_ledger(config.initial_capital)
        decision_journal = self._persistence.decision_journal()
        execution_journal = self._persistence.execution_journal()

        trading = TradingDecisionService(
            strategies=[AiDirectionalStrategy(min_confidence=self._strategy_min_confidence)],
            decision_engine=PositionAwareDecisionEngine(allow_reversal=self._allow_reversal),
            risk_gate=PolicyRiskGate(self._risk_policy),
            intent_factory=DefaultIntentFactory(base_quantity=self._base_quantity),
            validator=DefaultSignalValidator(max_signal_age_seconds=86400),
            journal=decision_journal,
        )

        execution = ExecutionService(
            resolver=DefaultIntentResolver(),
            venue=SimulatedExecutionVenue(
                slippage_rate=config.slippage_rate,
                commission_rate=config.commission_rate,
                currency=config.base_currency,
            ),
            ledger=ledger,
            journal=execution_journal,
        )

        session = SimulationSession(
            session_id=session_id,
            configuration=config,
            start_time=start,
            end_time=end,
            strategy_id="ai_directional",
        )

        self.ledger = ledger
        self.decision_journal = decision_journal
        self.execution_journal = execution_journal

        return BacktestEngine(
            session=session,
            data_provider=data_provider,
            prediction_source=prediction_source or MomentumPredictionSource(),
            trading_service=trading,
            execution_service=execution,
            ledger=ledger,
            timeframe=timeframe,
            reporter=reporter,
            record_replay=record_replay,
        )

    def run(
        self,
        session_id: str,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: Sequence[Candle],
        prediction_source: Optional[PredictionSource] = None,
        reporter: Optional[SimulationReporter] = None,
        record_replay: bool = False,
    ) -> BacktestResult:
        """Build and immediately run a backtest."""
        engine = self.build(
            session_id=session_id,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            prediction_source=prediction_source,
            reporter=reporter,
            record_replay=record_replay,
        )
        return engine.run()
