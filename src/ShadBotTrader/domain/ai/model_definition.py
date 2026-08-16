"""Model definition (Phase 13, section 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.common.errors import ValidationError


@dataclass(frozen=True)
class ModelDefinition:
    """The full, immutable definition of a model version.

    Binds a model id and version to its type, architecture family,
    feature set, target, hyperparameters and training policy. This is
    the contract every trainer must fulfil.
    """

    model_id: ModelId
    version: ModelVersion
    name: str
    model_type: ModelType
    family: ModelFamily
    feature_set_name: str
    feature_set_version: int
    target_name: str
    hyperparameters: Dict[str, Any]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("ModelDefinition name must not be empty")
        if not self.feature_set_name.strip():
            raise ValidationError("ModelDefinition feature_set_name must not be empty")
        if self.feature_set_version < 1:
            raise ValidationError("ModelDefinition feature_set_version must be >= 1")
        if not self.target_name.strip():
            raise ValidationError("ModelDefinition target_name must not be empty")
        object.__setattr__(self, "hyperparameters", dict(self.hyperparameters))
        object.__setattr__(self, "input_schema", dict(self.input_schema))
        object.__setattr__(self, "output_schema", dict(self.output_schema))
