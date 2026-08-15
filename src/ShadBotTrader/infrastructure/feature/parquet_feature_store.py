"""Parquet persistence of computed feature results (PyArrow)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureRepository
from ShadBotTrader.domain.market.timestamp import Timestamp

_VERSION_RE = re.compile(r"^v(\d+)\.parquet$")


class ParquetFeatureStore(FeatureRepository):
    """Stores feature results as ``features/{feature_id}/v{version}.parquet``.

    Immutability: writing to an existing version raises ``FileExistsError``.
    """

    def __init__(self, storage_root: Path) -> None:
        self._root = Path(storage_root) / "features"

    def save(self, feature_id: str, version: int, result: FeatureResult) -> None:
        """Persist a feature result immutably."""
        rows = [
            {
                "timestamp": point.timestamp.value.isoformat(),
                "value": point.value,
            }
            for point in result.points
        ]
        table = pa.Table.from_pylist(rows)
        path = self._path(feature_id, version)
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing feature version: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path)

    def load(self, feature_id: str, version: int) -> Optional[FeatureResult]:
        """Load a feature result from storage."""
        path = self._path(feature_id, version)
        if not path.exists():
            return None
        table = pq.read_table(path)
        points: List[FeaturePoint] = []
        for row in table.to_pylist():
            value = row["value"]
            points.append(
                FeaturePoint(
                    timestamp=Timestamp(_parse_iso(row["timestamp"])),
                    value=None if value is None else float(value),
                )
            )
        return FeatureResult(feature_id=feature_id, points=points)

    def exists(self, feature_id: str, version: int) -> bool:
        """Return True when the version exists."""
        return self._path(feature_id, version).exists()

    def next_version(self, feature_id: str) -> int:
        """Return the next available version for ``feature_id``."""
        directory = self._root / feature_id
        if not directory.is_dir():
            return 1
        versions: List[int] = []
        for path in directory.iterdir():
            match = _VERSION_RE.match(path.name)
            if match:
                versions.append(int(match.group(1)))
        return (max(versions) + 1) if versions else 1

    def _path(self, feature_id: str, version: int) -> Path:
        return self._root / feature_id / f"v{version}.parquet"


def _parse_iso(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Invalid timestamp value: {value!r}")
    return datetime.fromisoformat(value.strip())
