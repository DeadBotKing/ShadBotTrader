"""Serve model-input features from the Parquet store (Phase 39).

Until now ``build_feature_matrix`` recomputed all 109 catalogue features
every time it built the model's input, even when "Update features" had
just written exactly those numbers to disk. On 50,000 candles that is
about two minutes of arithmetic producing a result already available.

This module closes the gap. The rule it enforces is narrow and strict:

    the store may only be used when it holds features computed from
    EXACTLY these candles, and every value must survive the round trip
    unchanged.

Two guards make that real:

**Alignment.** A stored series is accepted only when its length and its
timestamps match the candles being used. A feature file that is one bar
short, or starts an hour later, is silently the wrong data — so it is
refused rather than trusted.

**Freshness.** The Phase 38 fingerprint decides whether the stored
features belong to this candle series at all. If the dataset moved, the
cache is not consulted; the caller recomputes.

What this module deliberately does NOT do is change any arithmetic. The
scaling against close, the warm-up trim, the tail trim and the column
order all stay in ``build_feature_matrix``, shared by both paths. That
is what lets a test assert the two matrices are identical rather than
merely similar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.market.candle import Candle


@dataclass
class StoredFeatureSource:
    """Reads feature columns for one symbol/timeframe from the store.

    ``misses`` records every feature that could not be served and why,
    so a partial cache is visible instead of quietly shrinking the model
    input.
    """

    store: Any
    candles: Sequence[Candle]
    misses: Dict[str, str] = field(default_factory=dict)
    hits: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._expected = [candle.open_time.value for candle in self.candles]

    def get(self, feature_id: str) -> Optional[FeatureResult]:
        """The stored result for ``feature_id``, or None when unusable."""
        version = self.store.next_version(feature_id) - 1
        if version < 1:
            self.misses[feature_id] = "nothing stored"
            return None

        result = self.store.load(feature_id, version)
        if result is None:
            self.misses[feature_id] = f"v{version} could not be read"
            return None

        if len(result.points) != len(self._expected):
            self.misses[feature_id] = (
                f"length mismatch: stored {len(result.points)}, " f"candles {len(self._expected)}"
            )
            return None

        # Timestamps must line up bar for bar. Same length with different
        # bars is the most dangerous failure mode: it would train the
        # model on values belonging to other candles.
        for index, point in enumerate(result.points):
            if point.timestamp.value != self._expected[index]:
                self.misses[feature_id] = (
                    f"timestamp mismatch at row {index}: "
                    f"stored {point.timestamp.value}, expected {self._expected[index]}"
                )
                return None

        self.hits.append(feature_id)
        return result

    @property
    def served(self) -> int:
        return len(self.hits)

    @property
    def is_complete(self) -> bool:
        """True when nothing had to fall back to recomputation."""
        return not self.misses

    def summary(self) -> Dict[str, Any]:
        return {
            "served": self.served,
            "missed": len(self.misses),
            "complete": self.is_complete,
            "reasons": dict(list(self.misses.items())[:5]),
        }


def stored_source_for(
    storage_root: Any,
    symbol: str,
    timeframe: str,
    candles: Sequence[Candle],
    feature_set: Any,
) -> Optional[StoredFeatureSource]:
    """A source for these candles, or None when the store is not usable.

    Returns None — meaning "recompute" — when the stored features were
    not built from this exact candle series. Being conservative here is
    the whole point: a wrong feature column is far more expensive than
    two minutes of recomputation.
    """
    from ShadBotTrader.infrastructure.feature.feature_cache import FeatureCache
    from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
        ParquetFeatureStore,
    )

    store = ParquetFeatureStore(storage_root).for_series(symbol, timeframe)
    if not FeatureCache(store).is_fresh(candles, feature_set):
        return None

    return StoredFeatureSource(store=store, candles=candles)
