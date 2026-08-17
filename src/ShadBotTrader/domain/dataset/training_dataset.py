"""Training-dataset identity and manifest (Phase 30 §4).

The training dataset is the one permanent, auditable thing the models
learn from, so what produced it has to be recorded: how many candles, on
which timeframes, how many feature columns, when it was refreshed, and a
digest of the numbers themselves.

The digest is what makes "the features were recomputed from scratch"
verifiable rather than a claim. Two builds of the same candles must
produce the same digest; if they do not, something upstream changed and
the models are about to learn from a different world.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError

#: Candles the training dataset targets, per timeframe (Phase 30 §1).
DEFAULT_TARGET_CANDLES = 100_000

#: Model input height.
DEFAULT_WINDOW_ROWS = 500


@dataclass(frozen=True)
class DatasetSpec:
    """What a training dataset is supposed to contain."""

    symbol: str
    timeframes: Sequence[str] = ("5M", "1H", "1D")
    target_candles: int = DEFAULT_TARGET_CANDLES
    window_rows: int = DEFAULT_WINDOW_ROWS

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValidationError("symbol must not be empty")
        if not self.timeframes:
            raise ValidationError("at least one timeframe is required")
        if self.target_candles < self.window_rows * 2:
            raise ValidationError(
                f"target_candles ({self.target_candles}) must be at least twice "
                f"the window ({self.window_rows}); otherwise roll-forward has "
                f"almost nothing to walk across."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframes": list(self.timeframes),
            "target_candles": self.target_candles,
            "window_rows": self.window_rows,
        }


@dataclass(frozen=True)
class TimeframeSlice:
    """What was actually built for one timeframe.

    ``requested`` and ``candles`` are kept apart on purpose: brokers do
    not always have 100,000 bars of history, and rounding the shortfall
    away would hide it.
    """

    timeframe: str
    requested: int
    candles: int
    feature_rows: int
    feature_columns: int
    warmup_dropped: int
    skipped_features: List[str] = field(default_factory=list)
    #: Rows cut from the tail for forward-looking columns (Phase 35).
    tail_dropped: int = 0
    #: Features dropped as columns because they had an interior hole.
    holed_features: List[str] = field(default_factory=list)
    #: True when the kept rows are consecutive candles (Phase 35).
    contiguous: bool = True
    first_time: str = ""
    last_time: str = ""
    digest: str = ""

    @property
    def is_complete(self) -> bool:
        """True when the broker supplied everything that was asked for."""
        return self.candles >= self.requested

    @property
    def shortfall(self) -> int:
        return max(self.requested - self.candles, 0)

    def usable_windows(self, window_rows: int, horizon: int) -> int:
        """Stride-1 windows this slice yields."""
        return max(self.feature_rows - window_rows - horizon + 1, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeframe": self.timeframe,
            "requested": self.requested,
            "candles": self.candles,
            "shortfall": self.shortfall,
            "complete": self.is_complete,
            "feature_rows": self.feature_rows,
            "feature_columns": self.feature_columns,
            "warmup_dropped": self.warmup_dropped,
            "skipped_features": list(self.skipped_features),
            "tail_dropped": self.tail_dropped,
            "holed_features": list(self.holed_features),
            "contiguous": self.contiguous,
            "first_time": self.first_time,
            "last_time": self.last_time,
            "digest": self.digest,
        }


@dataclass(frozen=True)
class DatasetManifest:
    """The record of one dataset build or refresh."""

    spec: DatasetSpec
    slices: Dict[str, TimeframeSlice]
    built_at: str = ""
    revision: int = 1
    note: str = ""

    @classmethod
    def create(
        cls,
        spec: DatasetSpec,
        slices: Dict[str, TimeframeSlice],
        revision: int = 1,
        note: str = "",
    ) -> "DatasetManifest":
        return cls(
            spec=spec,
            slices=dict(slices),
            built_at=datetime.now(timezone.utc).isoformat(),
            revision=revision,
            note=note,
        )

    @property
    def is_complete(self) -> bool:
        return all(item.is_complete for item in self.slices.values())

    @property
    def total_candles(self) -> int:
        return sum(item.candles for item in self.slices.values())

    def slice_for(self, timeframe: str) -> Optional[TimeframeSlice]:
        return self.slices.get(timeframe)

    def warnings(self) -> List[str]:
        """Everything a human should know before trusting this dataset."""
        messages: List[str] = []
        for item in self.slices.values():
            if not item.is_complete:
                messages.append(
                    f"{item.timeframe}: got {item.candles:,} of "
                    f"{item.requested:,} candles (short by {item.shortfall:,}). "
                    f"Broker history depth is the usual cause."
                )
            if item.skipped_features:
                messages.append(
                    f"{item.timeframe}: {len(item.skipped_features)} feature(s) "
                    f"could not be computed and were left out."
                )
            if item.holed_features:
                messages.append(
                    f"{item.timeframe}: {len(item.holed_features)} feature(s) had "
                    f"a gap after their warm-up and were dropped as columns "
                    f"rather than costing interior rows."
                )
            if not item.contiguous:
                messages.append(
                    f"{item.timeframe}: the stored rows are NOT consecutive "
                    f"candles. Roll-forward would step across missing market. "
                    f"Rebuild after repairing the candle history."
                )
            windows = item.usable_windows(self.spec.window_rows, horizon=5)
            if windows < 1000:
                messages.append(
                    f"{item.timeframe}: only {windows:,} training windows "
                    f"available — the models will underfit."
                )
        return messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "built_at": self.built_at,
            "revision": self.revision,
            "note": self.note,
            "complete": self.is_complete,
            "total_candles": self.total_candles,
            "slices": {name: item.to_dict() for name, item in self.slices.items()},
            "warnings": self.warnings(),
        }


def _as_stored(value: float) -> str:
    """Represent a value exactly as it will exist on disk.

    Matrices are persisted as float32. Hashing the float64 value instead
    would produce a digest that changes on every save/load cycle and so
    could never verify that a stored dataset is intact.

    Rounding to N decimal places does not solve this: the round-trip
    error is relative (~6e-8), so any fixed precision sits on a rounding
    boundary for some value and flips. Casting through float32 — the
    exact transformation storage applies — is lossless by construction.
    """
    import struct

    number = float(value)
    if number != number:  # NaN
        return "nan"
    # struct packs the IEEE-754 single-precision form: the bytes that
    # will actually be written to disk.
    return struct.pack("<f", number).hex()


def matrix_digest(rows: Sequence[Sequence[float]], sample: int = 200) -> str:
    """A short, stable digest of a feature matrix.

    Hashes the shape plus an evenly spread sample of rows rather than
    every value: enough to detect a changed computation, cheap enough to
    run on 100,000 rows.

    Values are hashed in their float32 storage form, so the digest of a
    freshly computed matrix equals the digest of the same matrix read
    back from disk. That equality is the whole point: it is what makes
    "the features were recomputed correctly" checkable instead of a
    claim.
    """
    if not rows:
        return "empty"

    hasher = hashlib.sha256()
    hasher.update(f"{len(rows)}x{len(rows[0])}".encode())

    step = max(len(rows) // sample, 1)
    for index in range(0, len(rows), step):
        hasher.update("".join(_as_stored(value) for value in rows[index]).encode())

    return hasher.hexdigest()[:16]
