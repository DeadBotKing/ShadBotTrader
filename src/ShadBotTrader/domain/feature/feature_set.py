"""Feature set and its version (Phase 12, sections 10-12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition


class FeatureSetVersion(ValueObject):
    """A monotonic version number for a feature set."""

    def __init__(self, number: int) -> None:
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValidationError(f"FeatureSetVersion must be >= 1, got {number!r}")
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    def _value(self) -> Tuple[Any, ...]:
        return (self._number,)

    def __str__(self) -> str:
        return str(self._number)


@dataclass(frozen=True)
class FeatureSet:
    """A named, versioned collection of feature definitions.

    Changing any feature or parameter inside the set is a tracked change
    and must produce a new version (section 12).
    """

    name: str
    version: FeatureSetVersion
    definitions: List[FeatureDefinition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("FeatureSet name must not be empty")
        ids = [definition.feature_id.value for definition in self.definitions]
        if len(ids) != len(set(ids)):
            raise ValidationError(f"FeatureSet {self.name} contains duplicate feature ids")

    @property
    def feature_ids(self) -> List[str]:
        """The ordered feature ids of this set."""
        return [definition.feature_id.value for definition in self.definitions]
