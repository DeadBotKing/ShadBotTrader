"""Ports (contracts) of the self-learning domain — Phase 17.

    ParameterSpace -> CandidateGenerator -> Candidate
                            |
                    CandidateEvaluator      (runs a simulation)
                            |
                      PromotionGate         (out-of-sample only)
                            |
                    LearningMemory          (remembers failures)

Boundary this design protects: self-learning proposes, simulation
judges, and only the gate may approve. Nothing here can reach live
trading — a promoted candidate is a *recommendation*, and the human /
deployment step that acts on it is outside this platform.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence

from ShadBotTrader.domain.learning.candidate import Candidate, EvaluationRecord
from ShadBotTrader.domain.learning.experiment import DataWindow, LearningExperiment
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterSpace,
)


class CandidateGenerator(ABC):
    """Proposes configurations to try from a parameter space."""

    @abstractmethod
    def generate(self, space: ParameterSpace) -> List[CandidateConfiguration]:
        """Return the configurations to evaluate, deterministically."""


class CandidateEvaluator(ABC):
    """Scores one configuration over one window of market data.

    Implemented by the Simulation Platform: self-learning never runs a
    strategy itself, it asks the simulator.
    """

    @abstractmethod
    def evaluate(
        self,
        configuration: CandidateConfiguration,
        window: DataWindow,
        series: Sequence[Any],
        label: str,
    ) -> EvaluationRecord:
        """Run ``configuration`` over ``window`` and return the record."""


class LearningMemory(ABC):
    """Remembers what has already been tried (Experiment/Failure Memory)."""

    @abstractmethod
    def remember(self, candidate: Candidate) -> None:
        """Record a finished candidate and its outcome."""

    @abstractmethod
    def recall(self, signature: str) -> Optional[Candidate]:
        """Return a previously evaluated candidate by configuration."""

    @abstractmethod
    def known_failures(self) -> List[Candidate]:
        """Every candidate that was rejected, with its reason."""

    @abstractmethod
    def all_candidates(self) -> List[Candidate]:
        """Every candidate ever recorded."""


class ExperimentRepository(ABC):
    """Persists experiments for audit and reproducibility."""

    @abstractmethod
    def save(self, experiment: LearningExperiment) -> None:
        """Store or update an experiment."""

    @abstractmethod
    def get(self, experiment_id: str) -> Optional[LearningExperiment]:
        """Return an experiment by id, or None."""

    @abstractmethod
    def list_all(self) -> List[LearningExperiment]:
        """Return every stored experiment."""


class OptimisationReporter(ABC):
    """Receives progress of a parameter search."""

    @abstractmethod
    def on_search_start(self, experiment: LearningExperiment, total: int) -> None:
        """Called once before the first candidate."""

    @abstractmethod
    def on_candidate_evaluated(self, candidate: Candidate, index: int, total: int) -> None:
        """Called after each candidate finishes its in-sample run."""

    @abstractmethod
    def on_validation(self, candidate: Candidate) -> None:
        """Called after a candidate finishes walk-forward validation."""

    @abstractmethod
    def on_search_end(self, experiment: LearningExperiment, winner: Optional[Candidate]) -> None:
        """Called once the search has finished."""


class NullOptimisationReporter(OptimisationReporter):
    """A reporter that stays silent (the default)."""

    def on_search_start(self, experiment: LearningExperiment, total: int) -> None:
        return None

    def on_candidate_evaluated(self, candidate: Candidate, index: int, total: int) -> None:
        return None

    def on_validation(self, candidate: Candidate) -> None:
        return None

    def on_search_end(self, experiment: LearningExperiment, winner: Optional[Candidate]) -> None:
        return None
