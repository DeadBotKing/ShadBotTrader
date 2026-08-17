"""Reuse stored features until the candles they came from change (Phase 38).

The user's rule, stated exactly:

    "as long as the dataset has not been updated there is no need to
     recompute the features — read them from the store. But when the
     dataset IS updated, the features must be recomputed from scratch
     and stored again."

Both halves matter, and the second one is the dangerous half. EMA, MACD,
ATR and every other recursive indicator carry state forward from the
first candle. A value computed over 100,000 candles is not the value you
get by continuing from candle 99,000 — it is subtly, invisibly different.
So this module never appends: a changed series means a full recompute.

**What makes a series "changed" is a fingerprint, not a timestamp.**
Modification times lie: a file can be rewritten with identical content,
or a dataset can be edited in place. The fingerprint covers the things
that would change the numbers:

    * the candles themselves (count, first and last timestamp, and a
      digest of every OHLCV value)
    * the feature-set name and version
    * the catalogue's feature ids

If any of those differ from what was stored, the cache misses and the
caller recomputes. If they all match, the stored values are returned and
nothing is recalculated.
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.market.candle import Candle

#: Written next to the stored features for one symbol/timeframe.
FINGERPRINT_FILE = "fingerprint.json"


def _as_stored(value: Any) -> bytes:
    """The exact bytes a float takes on disk.

    Hashing the float64 form would produce a digest that changes on every
    save/load cycle, which is the bug Phase 30 hit with dataset digests.
    """
    return struct.pack("<d", float(value))


def candles_digest(candles: Sequence[Candle]) -> str:
    """A digest of every value that could change a feature.

    Covers OHLCV and the open time of every candle. Two series with the
    same digest produce the same features, so recomputation would be
    wasted work; two series with different digests must never share
    cached values.
    """
    hasher = hashlib.sha256()
    for candle in candles:
        hasher.update(candle.open_time.value.isoformat().encode("utf-8"))
        hasher.update(_as_stored(candle.open.amount))
        hasher.update(_as_stored(candle.high.amount))
        hasher.update(_as_stored(candle.low.amount))
        hasher.update(_as_stored(candle.close.amount))
        hasher.update(_as_stored(candle.volume))
    return hasher.hexdigest()[:32]


@dataclass(frozen=True)
class FeatureFingerprint:
    """What the stored features were computed from."""

    candle_count: int
    first_time: str
    last_time: str
    candles_digest: str
    feature_set_name: str
    feature_set_version: int
    feature_ids: List[str]

    @classmethod
    def of(cls, candles: Sequence[Candle], feature_set: Any) -> "FeatureFingerprint":
        ids = sorted(
            definition.feature_id.value for definition in getattr(feature_set, "definitions", [])
        )
        version = getattr(getattr(feature_set, "version", None), "number", 0)
        return cls(
            candle_count=len(candles),
            first_time=str(candles[0].open_time) if candles else "",
            last_time=str(candles[-1].open_time) if candles else "",
            candles_digest=candles_digest(candles),
            feature_set_name=str(getattr(feature_set, "name", "")),
            feature_set_version=int(version),
            feature_ids=list(ids),
        )

    def matches(self, other: Optional["FeatureFingerprint"]) -> bool:
        """True when ``other`` describes exactly the same computation."""
        if other is None:
            return False
        return (
            self.candle_count == other.candle_count
            and self.candles_digest == other.candles_digest
            and self.feature_set_name == other.feature_set_name
            and self.feature_set_version == other.feature_set_version
            and self.feature_ids == other.feature_ids
        )

    def difference(self, other: Optional["FeatureFingerprint"]) -> str:
        """A human explanation of why the cache missed."""
        if other is None:
            return "nothing has been computed for this series yet"
        if self.feature_set_name != other.feature_set_name:
            return f"feature set changed: {other.feature_set_name} -> {self.feature_set_name}"
        if self.feature_set_version != other.feature_set_version:
            return (
                f"feature set version changed: v{other.feature_set_version} "
                f"-> v{self.feature_set_version}"
            )
        if self.feature_ids != other.feature_ids:
            added = len(set(self.feature_ids) - set(other.feature_ids))
            removed = len(set(other.feature_ids) - set(self.feature_ids))
            return f"the catalogue changed: {added} added, {removed} removed"
        if self.candle_count != other.candle_count:
            return (
                f"candle count changed: {other.candle_count:,} -> {self.candle_count:,} "
                f"(the dataset was updated)"
            )
        return "the candle values changed (the dataset was updated in place)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candle_count": self.candle_count,
            "first_time": self.first_time,
            "last_time": self.last_time,
            "candles_digest": self.candles_digest,
            "feature_set_name": self.feature_set_name,
            "feature_set_version": self.feature_set_version,
            "feature_ids": list(self.feature_ids),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FeatureFingerprint":
        return cls(
            candle_count=int(payload.get("candle_count", 0)),
            first_time=str(payload.get("first_time", "")),
            last_time=str(payload.get("last_time", "")),
            candles_digest=str(payload.get("candles_digest", "")),
            feature_set_name=str(payload.get("feature_set_name", "")),
            feature_set_version=int(payload.get("feature_set_version", 0)),
            feature_ids=[str(item) for item in payload.get("feature_ids", [])],
        )


class FeatureCache:
    """Decides whether stored features may be reused for a series."""

    def __init__(self, store: Any) -> None:
        #: A ParquetFeatureStore already scoped to one symbol/timeframe.
        self._store = store

    @property
    def fingerprint_path(self) -> Path:
        return Path(self._store.root) / FINGERPRINT_FILE

    def stored_fingerprint(self) -> Optional[FeatureFingerprint]:
        path = self.fingerprint_path
        if not path.exists():
            return None
        try:
            return FeatureFingerprint.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            # A corrupt fingerprint must cause a recompute, never a crash
            # and never a silent reuse of values we can no longer vouch for.
            return None

    def write_fingerprint(self, fingerprint: FeatureFingerprint) -> Path:
        path = self.fingerprint_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(fingerprint.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    def is_fresh(self, candles: Sequence[Candle], feature_set: Any) -> bool:
        """True when the stored features still describe these candles."""
        return FeatureFingerprint.of(candles, feature_set).matches(self.stored_fingerprint())

    def reason_to_recompute(self, candles: Sequence[Candle], feature_set: Any) -> str:
        """Why a recompute is needed, or an empty string when it is not."""
        wanted = FeatureFingerprint.of(candles, feature_set)
        stored = self.stored_fingerprint()
        if wanted.matches(stored):
            return ""
        return wanted.difference(stored)

    def load_all(self, feature_set: Any) -> Optional[Dict[str, Any]]:
        """Every stored feature for this series, or None when incomplete.

        A partial cache is treated as a miss: training on a catalogue
        that is missing a column is worse than recomputing it.
        """
        results: Dict[str, Any] = {}
        for definition in getattr(feature_set, "definitions", []):
            feature_id = definition.feature_id.value
            version = self._store.next_version(feature_id) - 1
            if version < 1:
                return None
            result = self._store.load(feature_id, version)
            if result is None:
                return None
            results[feature_id] = result
        return results
