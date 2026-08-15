"""In-memory dataset catalog implementing DatasetRepository."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from ShadBotTrader.domain.dataset.dataset_descriptor import DatasetDescriptor
from ShadBotTrader.domain.dataset.dataset_identity import DatasetId
from ShadBotTrader.domain.dataset.ports import DatasetRepository


class InMemoryDatasetRepository(DatasetRepository):
    """Keeps dataset descriptors in memory, keyed by dataset identity.

    Version history is preserved: ``register`` appends to the history of
    a dataset and ``get`` returns the latest version.
    """

    def __init__(self) -> None:
        self._history: Dict[str, List[DatasetDescriptor]] = defaultdict(list)

    def register(self, descriptor: DatasetDescriptor) -> None:
        """Append ``descriptor`` to its dataset's version history."""
        self._history[descriptor.dataset_id.label].append(descriptor)

    def get(self, dataset_id: DatasetId) -> Optional[DatasetDescriptor]:
        """Return the latest descriptor for ``dataset_id``, if any."""
        history = self._history.get(dataset_id.label)
        if not history:
            return None
        return max(history, key=lambda descriptor: descriptor.version.number)

    def list_all(self) -> List[DatasetDescriptor]:
        """Return every registered descriptor, newest first."""
        descriptors = [descriptor for history in self._history.values() for descriptor in history]
        return sorted(descriptors, key=lambda descriptor: descriptor.created_at, reverse=True)

    def next_version(self, dataset_id: DatasetId) -> int:
        """Return the next version number for ``dataset_id``."""
        history = self._history.get(dataset_id.label)
        if not history:
            return 1
        latest = max(descriptor.version.number for descriptor in history)
        return latest + 1
