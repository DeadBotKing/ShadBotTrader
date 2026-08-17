"""Parquet persistence of computed feature results (PyArrow).

Phase 37 changed the layout. It used to be::

    features/{feature_id}/v{version}.parquet

which records neither the symbol nor the timeframe. Computing ``atr_14``
for XAUUSD 5M wrote ``v1``; computing the *same* feature for XAUUSD 1H
wrote ``v2`` into the same directory. Two different quantities — one
measured over five minutes, one over an hour — sat side by side with
nothing to tell them apart, and ``load("atr_14", 1)`` could not say which
series it had returned. The layout is now::

    features/{symbol}/{timeframe}/{feature_id}/v{version}.parquet

so each (symbol, timeframe) has its own independent version sequence, and
the identity of a stored series is visible from its path.

The ``FeatureRepository`` port is frozen (Phase 26) and its methods take
only ``feature_id`` and ``version``. Rather than widen the port, the
scope is bound to the *instance*: callers create a store for the series
they are working on via :meth:`for_series`. The port keeps its shape and
the data keeps its identity.
"""

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


def _safe(part: str) -> str:
    """A path-safe form of a symbol or timeframe label."""
    cleaned = "".join(
        character
        for character in str(part).strip().upper()
        if character.isalnum() or character in "-_"
    )
    return cleaned or "UNKNOWN"


class ParquetFeatureStore(FeatureRepository):
    """Stores feature results, partitioned by symbol and timeframe.

    Layout::

        {storage_root}/features/{symbol}/{timeframe}/{feature_id}/v{n}.parquet

    Immutability: writing to an existing version raises ``FileExistsError``.
    """

    def __init__(
        self,
        storage_root: Path,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> None:
        self._storage_root = Path(storage_root)
        self._features_root = self._storage_root / "features"
        self._symbol = _safe(symbol) if symbol else None
        self._timeframe = _safe(timeframe) if timeframe else None

    # ------------------------------------------------------------ scope --
    def for_series(self, symbol: str, timeframe: str) -> "ParquetFeatureStore":
        """A store scoped to one symbol and timeframe.

        Returns a new instance rather than mutating this one: a service
        holding a store must never have the ground shift under it because
        somebody else started computing a different series.
        """
        return ParquetFeatureStore(self._storage_root, symbol, timeframe)

    @property
    def scope(self) -> Optional[tuple[str, str]]:
        """``(symbol, timeframe)``, or None when the store is unscoped."""
        if self._symbol is None or self._timeframe is None:
            return None
        return (self._symbol, self._timeframe)

    @property
    def root(self) -> Path:
        """The directory this store reads and writes."""
        if self._symbol is None or self._timeframe is None:
            return self._features_root
        return self._features_root / self._symbol / self._timeframe

    # ------------------------------------------------------------- port --
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
        # Phase 39: warm-up must survive the round trip. It is not a
        # property of the values — it is how many leading rows have no
        # honest value — and build_feature_matrix uses it to decide where
        # the matrix starts. Losing it would make a matrix loaded from the
        # store silently differ from a freshly computed one.
        table = table.replace_schema_metadata(
            {
                b"warmup": str(int(getattr(result, "warmup", 0))).encode("utf-8"),
                b"feature_id": str(feature_id).encode("utf-8"),
            }
        )
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
        return FeatureResult(
            feature_id=feature_id,
            points=points,
            warmup=_warmup_of(table),
        )

    def exists(self, feature_id: str, version: int) -> bool:
        """Return True when the version exists."""
        return self._path(feature_id, version).exists()

    def next_version(self, feature_id: str) -> int:
        """The next free version **for this symbol and timeframe**.

        Each series counts independently, so computing 5M then 1H yields
        v1 in each of their own directories rather than v1 and v2 in a
        shared one.
        """
        directory = self.root / feature_id
        if not directory.is_dir():
            return 1
        versions: List[int] = []
        for path in directory.iterdir():
            match = _VERSION_RE.match(path.name)
            if match:
                versions.append(int(match.group(1)))
        return (max(versions) + 1) if versions else 1

    def _path(self, feature_id: str, version: int) -> Path:
        return self.root / feature_id / f"v{version}.parquet"


def _warmup_of(table: "pa.Table") -> int:
    """The warm-up recorded when the feature was stored, or 0.

    Files written before Phase 39 carry no metadata; 0 is the honest
    answer for them, and the fingerprint will force a recompute anyway.
    """
    metadata = table.schema.metadata or {}
    raw = metadata.get(b"warmup")
    if raw is None:
        return 0
    try:
        return int(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 0


def _parse_iso(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Invalid timestamp value: {value!r}")
    return datetime.fromisoformat(value.strip())
