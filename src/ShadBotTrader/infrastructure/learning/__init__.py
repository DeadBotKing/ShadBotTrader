"""Self-Learning infrastructure — Phase 17 implementations.

Concrete adapters for the ports in ``domain.learning.ports``:

* :class:`GridSearchGenerator` / :class:`RandomSearchGenerator` — search
* :class:`BacktestCandidateEvaluator` — scores via the Simulation Platform
* :class:`WalkForwardOptimizer` — search, validate out-of-sample, gate
* :class:`InMemoryLearningMemory` — remembers wins and failures
* :class:`ConsoleOptimisationReporter` — human-readable progress
"""

from ShadBotTrader.infrastructure.learning.backtest_evaluator import (
    BacktestCandidateEvaluator,
    default_parameter_values,
)
from ShadBotTrader.infrastructure.learning.console_reporter import (
    ConsoleOptimisationReporter,
)
from ShadBotTrader.infrastructure.learning.generators import (
    GridSearchGenerator,
    RandomSearchGenerator,
)
from ShadBotTrader.infrastructure.learning.learning_memory import (
    InMemoryExperimentRepository,
    InMemoryLearningMemory,
)
from ShadBotTrader.infrastructure.learning.optimizer import (
    OptimisationResult,
    WalkForwardOptimizer,
)

__all__ = [
    "BacktestCandidateEvaluator",
    "ConsoleOptimisationReporter",
    "GridSearchGenerator",
    "InMemoryExperimentRepository",
    "InMemoryLearningMemory",
    "OptimisationResult",
    "RandomSearchGenerator",
    "WalkForwardOptimizer",
    "default_parameter_values",
]
