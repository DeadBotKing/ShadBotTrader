"""Feature identity and definition (Phase 12, sections 4-9, 21-24)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.feature.feature_types import (
    Causality,
    FeatureType,
    FeatureValueType,
    ModelScope,
)


class FeatureId(ValueObject):
    """The implementation-independent identity of a feature.

    The id is a normalized, lowercase snake label such as ``sma_20``.
    Two definitions with the same id are the same feature even if the
    underlying computation changes over time (section 5).
    """

    def __init__(self, value: str) -> None:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValidationError("FeatureId must not be empty")
        self._id = normalized

    @property
    def value(self) -> str:
        return self._id

    def _value(self) -> Tuple[Any, ...]:
        return (self._id,)

    def __str__(self) -> str:
        return self._id


@dataclass(frozen=True)
class FeatureDefinition:
    """The full definition of a feature.

    Includes identity, semantics, parameterisation, lookback (warmup),
    computation version, causality and value type. This descriptor is
    the contract every calculator must fulfil.
    """

    feature_id: FeatureId
    name: str
    feature_type: FeatureType
    value_type: FeatureValueType
    parameters: Mapping[str, Any]
    lookback: int
    computation_version: str
    causality: Causality = Causality.CAUSAL
    description: str = ""
    family: str = ""
    #: Explicit future dependency, in candles.  This is metadata for
    #: auditing; a non-causal family can still have zero here (for example
    #: a full-series PCA fit).
    forward_lookahead: int = 0
    #: Human-readable reason a feature is unsafe for live/model input.
    leakage_reason: str = ""
    #: Which model(s) this feature is appropriate for.
    #: BOTH = هر دو، SIGNAL = فقط 5M signal، RANGE = فقط 1D range
    model_scope: ModelScope = ModelScope.BOTH

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("FeatureDefinition name must not be empty")
        if self.lookback < 0:
            raise ValidationError("FeatureDefinition lookback must be >= 0")
        if self.forward_lookahead < 0:
            raise ValidationError("FeatureDefinition forward_lookahead must be >= 0")
        if not self.computation_version.strip():
            raise ValidationError("FeatureDefinition computation_version must not be empty")
        if not self.parameters:
            raise ValidationError(f"FeatureDefinition {self.feature_id} must declare parameters")
        object.__setattr__(self, "parameters", dict(self.parameters))

    @property
    def is_live_compatible(self) -> bool:
        """True only when the definition has no future dependency."""
        return (
            self.causality is Causality.CAUSAL
            and self.forward_lookahead == 0
            and not self.leakage_reason
        )

    @property
    def is_causal(self) -> bool:
        """Alias used by the Stage 1 causality audit."""
        return self.is_live_compatible

    @property
    def calculator_family(self) -> str:
        """The calculator family that computes this feature.

        Explicit ``family`` wins; otherwise the leading part of the
        feature id is used (e.g. ``sma`` for ``sma_20``).
        """
        return self.family or self.feature_id.value.split("_", 1)[0]
