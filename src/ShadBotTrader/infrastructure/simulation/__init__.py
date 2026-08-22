"""Simulation infrastructure — Phase 16 implementations.

Concrete adapters for the ports in ``domain.simulation.ports``:

* :class:`CandleMarketDataProvider` — replays a historical candle series
* :class:`MomentumPredictionSource` — deterministic baseline predictions
* :class:`ModelPredictionSource` — the trained Phase 29 signal model
* :class:`ScriptedPredictionSource` — fixed schedule, for tests/scenarios
* :class:`BacktestEngine` — orchestrates the whole trading chain
* :class:`ConsoleSimulationReporter` — plan, progress and results
* :class:`ConsoleReplayPlayer` — bar-by-bar replay of a recorded run
"""

from ShadBotTrader.infrastructure.simulation.backtest_engine import (
    BacktestEngine,
    BacktestResult,
)
from ShadBotTrader.infrastructure.simulation.candle_data_provider import (
    CandleMarketDataProvider,
)
from ShadBotTrader.infrastructure.simulation.console_replay import (
    ConsoleReplayPlayer,
    summarise_tape,
)
from ShadBotTrader.infrastructure.simulation.console_reporter import (
    ConsoleSimulationReporter,
)
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)
from ShadBotTrader.infrastructure.simulation.model_prediction_source import (
    ModelPredictionSource,
)
from ShadBotTrader.infrastructure.simulation.prediction_sources import (
    MomentumPredictionSource,
    ScriptedPredictionSource,
)
from ShadBotTrader.infrastructure.simulation.trade_log import (
    trade_log_rows,
    write_trade_log,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "CandleMarketDataProvider",
    "ConsoleReplayPlayer",
    "ConsoleSimulationReporter",
    "DualModelPredictionSource",
    "ModelPredictionSource",
    "MomentumPredictionSource",
    "ScriptedPredictionSource",
    "summarise_tape",
    "trade_log_rows",
    "write_trade_log",
]
