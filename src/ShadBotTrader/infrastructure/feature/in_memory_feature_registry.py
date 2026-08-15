"""In-memory feature definition registry."""

from __future__ import annotations

from typing import Dict, List, Optional

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.ports import FeatureRegistry


class InMemoryFeatureRegistry(FeatureRegistry):
    """Keeps feature definitions in memory, keyed by feature id."""

    def __init__(self) -> None:
        self._definitions: Dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        """Record a definition (latest registration wins for the id)."""
        self._definitions[definition.feature_id.value] = definition

    def get(self, feature_id: str) -> Optional[FeatureDefinition]:
        """Return the definition for ``feature_id``, or None."""
        return self._definitions.get(feature_id)

    def list_all(self) -> List[FeatureDefinition]:
        """Return all registered definitions sorted by id."""
        return [self._definitions[key] for key in sorted(self._definitions)]
