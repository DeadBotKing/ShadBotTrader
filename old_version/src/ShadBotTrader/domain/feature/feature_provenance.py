"""Feature lineage/provenance metadata (Phase 12, sections 41-42)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass(frozen=True)
class FeatureProvenance:
    """The lineage of a computed feature: what went into it."""

    feature_id: str
    source_dataset_id: str
    dataset_version: int
    parameters: Dict[str, Any]
    computation_version: str
    generated_at: datetime
    live_compatible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "source_dataset_id": self.source_dataset_id,
            "dataset_version": self.dataset_version,
            "parameters": dict(self.parameters),
            "computation_version": self.computation_version,
            "generated_at": self.generated_at.isoformat(),
            "live_compatible": self.live_compatible,
        }
