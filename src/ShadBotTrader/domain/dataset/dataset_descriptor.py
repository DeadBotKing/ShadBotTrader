"""The dataset catalog entry (aggregate root of the dataset domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ShadBotTrader.domain.dataset.data_layer import DataLayer
from ShadBotTrader.domain.dataset.data_schema import DataSchema
from ShadBotTrader.domain.dataset.dataset_identity import DatasetId
from ShadBotTrader.domain.dataset.dataset_version import DatasetVersion
from ShadBotTrader.domain.dataset.quality_report import QualityReport


class DatasetStatus(str, Enum):
    """The lifecycle status of a dataset."""

    ACTIVE = "active"
    QUARANTINED = "quarantined"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class DatasetDescriptor:
    """A catalog entry describing one dataset version.

    The descriptor is the runtime face of a dataset: identity, version,
    schema, time range, quality and status.
    """

    dataset_id: DatasetId
    version: DatasetVersion
    schema: DataSchema
    layer: DataLayer
    status: DatasetStatus = DatasetStatus.ACTIVE
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    row_count: int = 0
    quality: Optional[QualityReport] = None
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def to_dict(self) -> dict:
        """Return the descriptor as a JSON-serialisable mapping."""
        return {
            "dataset_id": self.dataset_id.label,
            "version": self.version.number,
            "schema": str(self.schema),
            "layer": self.layer.value,
            "status": self.status.value,
            "time_start": self.time_start.isoformat() if self.time_start else None,
            "time_end": self.time_end.isoformat() if self.time_end else None,
            "row_count": self.row_count,
            "quality": self.quality.to_dict() if self.quality else None,
            "created_at": self.created_at.isoformat(),
        }
