"""Parameter space and candidate configurations (Phase 17: Parameter Search).

A ``ParameterSpace`` declares which knobs may be tuned and what values
they may take. Enumeration is deterministic — the same space always
yields the same ordered set of configurations, so a search is
reproducible.
"""

from __future__ import annotations

import itertools
import random
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Mapping, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class ParameterGrid(ValueObject):
    """The discrete values one parameter may take."""

    def __init__(self, name: str, values: Sequence[Any]) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("Parameter name must not be empty")
        if not values:
            raise ValidationError(f"Parameter '{normalized}' needs at least one value")
        self._name = normalized
        self._values = list(values)

    @property
    def name(self) -> str:
        return self._name

    @property
    def values(self) -> List[Any]:
        return list(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def _value(self) -> tuple[Any, ...]:
        return (self._name, tuple(str(value) for value in self._values))


class CandidateConfiguration(ValueObject):
    """One concrete point in the parameter space.

    Immutable and hashable by content, so identical configurations are
    recognised as the same candidate across experiments.
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values: Dict[str, Any] = dict(values)

    @property
    def values(self) -> Dict[str, Any]:
        return dict(self._values)

    def get(self, name: str, default: Any = None) -> Any:
        return self._values.get(name, default)

    def decimal(self, name: str, default: str = "0") -> Decimal:
        """Read a parameter as an exact Decimal."""
        raw = self._values.get(name, default)
        if isinstance(raw, Decimal):
            return raw
        return Decimal(str(raw))

    def merged_with(self, other: Mapping[str, Any]) -> "CandidateConfiguration":
        """Return a copy overlaid with ``other``."""
        combined = dict(self._values)
        combined.update(other)
        return CandidateConfiguration(combined)

    @property
    def signature(self) -> str:
        """A stable, human-readable identity for this configuration."""
        parts = [f"{key}={self._values[key]}" for key in sorted(self._values)]
        return ",".join(parts)

    def _value(self) -> tuple[Any, ...]:
        return tuple(sorted((key, str(value)) for key, value in self._values.items()))

    def __str__(self) -> str:
        return self.signature


class ParameterSpace:
    """The full set of configurations a search may explore."""

    def __init__(self, grids: Sequence[ParameterGrid] = ()) -> None:
        names = [grid.name for grid in grids]
        if len(names) != len(set(names)):
            raise ValidationError("Duplicate parameter names in a ParameterSpace")
        self._grids = list(grids)

    @classmethod
    def from_dict(cls, mapping: Mapping[str, Sequence[Any]]) -> "ParameterSpace":
        """Build a space from ``{name: [values]}``, sorted by name."""
        return cls([ParameterGrid(name, mapping[name]) for name in sorted(mapping)])

    @property
    def grids(self) -> List[ParameterGrid]:
        return list(self._grids)

    @property
    def names(self) -> List[str]:
        return [grid.name for grid in self._grids]

    @property
    def size(self) -> int:
        """Number of configurations in the full grid."""
        total = 1
        for grid in self._grids:
            total *= len(grid)
        return total if self._grids else 0

    def grid_configurations(self) -> Iterator[CandidateConfiguration]:
        """Every combination, in a deterministic order."""
        if not self._grids:
            return iter(())
        names = [grid.name for grid in self._grids]
        products = itertools.product(*(grid.values for grid in self._grids))
        return (
            CandidateConfiguration(dict(zip(names, combination, strict=True)))
            for combination in products
        )

    def random_configurations(
        self,
        count: int,
        seed: int = 42,
    ) -> List[CandidateConfiguration]:
        """``count`` distinct random points, reproducible for a given seed."""
        if count < 1:
            raise ValidationError("count must be >= 1")
        if not self._grids:
            return []

        rng = random.Random(seed)
        seen: set[str] = set()
        picked: List[CandidateConfiguration] = []
        # Bounded attempts: a small space can be exhausted before `count`.
        attempts = 0
        limit = max(count * 20, 100)

        while len(picked) < count and attempts < limit:
            attempts += 1
            values = {grid.name: rng.choice(grid.values) for grid in self._grids}
            configuration = CandidateConfiguration(values)
            if configuration.signature in seen:
                continue
            seen.add(configuration.signature)
            picked.append(configuration)

        return picked
