"""Simulation infrastructure — Phase 16 implementations.

Concrete adapters for the ports in ``domain.simulation.ports``:

* :class:`CandleMarketDataProvider` — replays a historical candle series
* :class:`MomentumPredictionSource` — deterministic baseline predictions
* :class:`ScriptedPredictionSource` — fixed schedule, for tests/scenarios
* :class:`BacktestEngine` — orchestrates the whole trading chain
* :class:`ConsoleSimulationReporter` — plan, progress and results
"""

from ShadBotTrader.infrastructure.simulation.backtest_engine import (
    BacktestEngine,
    BacktestResult,
)
from ShadBotTrader.infrastructure.simulation.candle_data_provider import (
    CandleMarketDataProvider,
)
from ShadBotTrader.infrastructure.simulation.console_reporter import (
    ConsoleSimulationReporter,
)
from ShadBotTrader.infrastructure.simulation.prediction_sources import (
    MomentumPredictionSource,
    ScriptedPredictionSource,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "CandleMarketDataProvider",
    "ConsoleSimulationReporter",
    "MomentumPredictionSource",
    "ScriptedPredictionSource",
]
