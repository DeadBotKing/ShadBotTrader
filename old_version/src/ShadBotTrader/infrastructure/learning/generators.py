"""Candidate generators (Phase 17: Parameter Search)."""

from __future__ import annotations

from typing import List, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.ports import CandidateGenerator


class GridSearchGenerator(CandidateGenerator):
    """Enumerates the full parameter grid, optionally capped.

    Exhaustive and deterministic. The cap exists because a grid grows
    multiplicatively: four parameters with five values each is already
    625 backtests.
    """

    def __init__(self, max_candidates: Optional[int] = None) -> None:
        if max_candidates is not None and max_candidates < 1:
            raise ValidationError("max_candidates must be >= 1")
        self._max_candidates = max_candidates

    def generate(self, space: ParameterSpace) -> List[CandidateConfiguration]:
        configurations = list(space.grid_configurations())
        if self._max_candidates is not None:
            return configurations[: self._max_candidates]
        return configurations


class RandomSearchGenerator(CandidateGenerator):
    """Samples the space at random, reproducibly for a given seed.

    Usually finds a good region faster than a grid when only a few of
    the parameters actually matter.
    """

    def __init__(self, count: int = 20, seed: int = 42) -> None:
        if count < 1:
            raise ValidationError("count must be >= 1")
        self._count = count
        self._seed = seed

    @property
    def seed(self) -> int:
        return self._seed

    def generate(self, space: ParameterSpace) -> List[CandidateConfiguration]:
        return space.random_configurations(self._count, seed=self._seed)
