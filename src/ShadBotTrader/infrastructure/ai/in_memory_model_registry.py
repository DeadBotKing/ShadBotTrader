"""In-memory model registry."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.ports import ModelRegistry


class InMemoryModelRegistry(ModelRegistry):
    """Keeps model definitions in memory, keyed by (model_id, version)."""

    def __init__(self) -> None:
        self._definitions: Dict[tuple[str, int], ModelDefinition] = {}
        self._by_model: Dict[str, List[int]] = defaultdict(list)

    def register(self, definition: ModelDefinition) -> None:
        key = (definition.model_id.value, definition.version.number)
        self._definitions[key] = definition
        versions = self._by_model[definition.model_id.value]
        if definition.version.number not in versions:
            versions.append(definition.version.number)
            versions.sort()

    def get(self, model_id: ModelId, version: ModelVersion) -> Optional[ModelDefinition]:
        return self._definitions.get((model_id.value, version.number))

    def latest_version(self, model_id: ModelId) -> Optional[ModelVersion]:
        versions = self._by_model.get(model_id.value)
        if not versions:
            return None
        return ModelVersion(versions[-1])

    def list_all(self) -> List[ModelDefinition]:
        return sorted(
            self._definitions.values(),
            key=lambda definition: (
                definition.model_id.value,
                definition.version.number,
            ),
        )
