"""In-memory learning and experiment stores (Phase 17: Learning Memory).

Remembering failures matters as much as remembering wins: without it a
search re-explores the same dead ends every run.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ShadBotTrader.domain.learning.candidate import Candidate
from ShadBotTrader.domain.learning.experiment import LearningExperiment
from ShadBotTrader.domain.learning.learning_types import CandidateStatus
from ShadBotTrader.domain.learning.ports import ExperimentRepository, LearningMemory


class InMemoryLearningMemory(LearningMemory):
    """Keeps every evaluated candidate, keyed by configuration signature."""

    def __init__(self) -> None:
        self._by_signature: Dict[str, Candidate] = {}
        self._order: List[str] = []

    def remember(self, candidate: Candidate) -> None:
        signature = candidate.configuration.signature
        if signature not in self._by_signature:
            self._order.append(signature)
        self._by_signature[signature] = candidate

    def recall(self, signature: str) -> Optional[Candidate]:
        return self._by_signature.get(signature)

    def known_failures(self) -> List[Candidate]:
        return [
            candidate
            for candidate in self.all_candidates()
            if candidate.status is CandidateStatus.REJECTED
        ]

    def all_candidates(self) -> List[Candidate]:
        return [self._by_signature[signature] for signature in self._order]

    # -- reporting ---------------------------------------------------------
    def rejection_counts(self) -> Dict[str, int]:
        """Histogram of why candidates were rejected."""
        counts: Dict[str, int] = {}
        for candidate in self.known_failures():
            reason = candidate.rejection_reason
            if reason is not None:
                counts[reason.value] = counts.get(reason.value, 0) + 1
        return counts

    def promoted(self) -> List[Candidate]:
        return [
            candidate
            for candidate in self.all_candidates()
            if candidate.status is CandidateStatus.PROMOTED
        ]

    def clear(self) -> None:
        self._by_signature.clear()
        self._order.clear()

    def __len__(self) -> int:
        return len(self._by_signature)


class InMemoryExperimentRepository(ExperimentRepository):
    """Stores experiments for audit and reproducibility."""

    def __init__(self) -> None:
        self._experiments: Dict[str, LearningExperiment] = {}
        self._order: List[str] = []

    def save(self, experiment: LearningExperiment) -> None:
        if experiment.experiment_id not in self._experiments:
            self._order.append(experiment.experiment_id)
        self._experiments[experiment.experiment_id] = experiment

    def get(self, experiment_id: str) -> Optional[LearningExperiment]:
        return self._experiments.get(experiment_id)

    def list_all(self) -> List[LearningExperiment]:
        return [self._experiments[key] for key in self._order]

    def __len__(self) -> int:
        return len(self._experiments)
