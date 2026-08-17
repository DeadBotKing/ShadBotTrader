"""Build, store and refresh the training dataset (Phase 30 §4).

Composition root for the permanent side of Phase 30:

    ingest candles (5M + 1H)
        -> compute every feature over the whole series
        -> store the flat matrix (npz) + manifest (json)
        -> hand a stride-1 window generator to the trainers

The weekly refresh recomputes features **from scratch** rather than
appending. Many indicators are recursive — EMA, MACD, ATR — so a value
computed from a truncated history is subtly wrong in a way no test would
notice. A full recompute costs about two minutes per 100k candles, which
is nothing next to silently corrupt inputs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.training_dataset import (
    DatasetManifest,
    DatasetSpec,
    TimeframeSlice,
    matrix_digest,
)
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix

#: How often the dataset is expected to be refreshed (Phase 30 §4.2).
REFRESH_INTERVAL_DAYS = 7


@dataclass
class StoredMatrix:
    """A feature matrix loaded back from disk."""

    rows: List[List[float]]
    column_names: List[str]
    source_index: List[int]
    timeframe: str
    warmup_dropped: int = 0

    @property
    def width(self) -> int:
        return len(self.column_names)

    def __len__(self) -> int:
        return len(self.rows)


class TrainingDataService:
    """Owns the on-disk training dataset."""

    def __init__(
        self,
        storage_root: Path,
        feature_set: Any = None,
        resolver: Any = None,
        use_stored_features: bool = True,
    ) -> None:
        self._root = Path(storage_root)
        self._dataset_root = self._root / "training"
        self._feature_set = feature_set
        self._resolver = resolver
        self._use_stored = use_stored_features
        #: Whether the last slice came from the store or was recomputed.
        self.last_source = "computed"

    # ------------------------------------------------------------ paths --
    @property
    def dataset_root(self) -> Path:
        return self._dataset_root

    def matrix_path(self, symbol: str, timeframe: str) -> Path:
        return self._dataset_root / symbol / f"{timeframe}_matrix.npz"

    def manifest_path(self, symbol: str) -> Path:
        return self._dataset_root / symbol / "manifest.json"

    # ------------------------------------------------------------ build --
    def build_slice(
        self,
        candles: Sequence[Candle],
        symbol: str,
        timeframe: str,
        requested: int,
    ) -> tuple[TimeframeSlice, List[List[float]], List[str], List[int]]:
        """Compute every feature over ``candles`` and describe the result."""
        if not candles:
            raise ValidationError(f"No candles supplied for {symbol} {timeframe}")

        # Phase 39: prefer the stored features. stored_source_for returns
        # None unless the store holds columns built from exactly these
        # candles, so this is an optimisation that cannot change the
        # numbers — a regression test asserts the two matrices are
        # byte-identical.
        source = None
        self.last_source = "computed"
        if self._feature_set is not None and self._use_stored:
            from ShadBotTrader.infrastructure.ai.stored_feature_source import (
                stored_source_for,
            )

            source = stored_source_for(self._root, symbol, timeframe, candles, self._feature_set)
            if source is not None:
                self.last_source = "stored"

        matrix = build_feature_matrix(
            candles=candles,
            symbol=Symbol(symbol),
            timeframe=Timeframe(timeframe),
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=self._feature_set is not None
            and (self._resolver is not None or source is not None),
            source=source,
        )
        if source is not None and not source.is_complete:
            # A partial cache would quietly narrow the model input.
            # Recompute the whole thing instead.
            self.last_source = "computed (stored set was incomplete)"
            matrix = build_feature_matrix(
                candles=candles,
                symbol=Symbol(symbol),
                timeframe=Timeframe(timeframe),
                feature_set=self._feature_set,
                resolver=self._resolver,
                include_features=self._resolver is not None,
            )
        if matrix.is_empty:
            raise ValidationError(
                f"{timeframe}: every row was consumed by feature warm-up. " f"Supply more candles."
            )

        slice_record = TimeframeSlice(
            timeframe=timeframe,
            requested=requested,
            candles=len(candles),
            feature_rows=len(matrix),
            feature_columns=matrix.width,
            warmup_dropped=matrix.dropped_warmup,
            skipped_features=list(matrix.skipped_features),
            tail_dropped=matrix.dropped_tail,
            holed_features=list(matrix.holed_features),
            contiguous=matrix.is_contiguous,
            first_time=str(candles[0].open_time),
            last_time=str(candles[-1].open_time),
            digest=matrix_digest(matrix.rows),
        )
        return slice_record, matrix.rows, matrix.column_names, matrix.source_index

    def save_matrix(
        self,
        symbol: str,
        timeframe: str,
        rows: Sequence[Sequence[float]],
        column_names: Sequence[str],
        source_index: Sequence[int],
    ) -> Path:
        """Persist a feature matrix so training never recomputes it."""
        import numpy as np

        path = self.matrix_path(symbol, timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            rows=np.array(rows, dtype=np.float32),
            columns=np.array(list(column_names), dtype=object),
            source_index=np.array(list(source_index), dtype=np.int64),
        )
        return path

    def load_matrix(self, symbol: str, timeframe: str) -> Optional[StoredMatrix]:
        """Read a stored matrix back, or None when it was never built."""
        import numpy as np

        path = self.matrix_path(symbol, timeframe)
        if not path.exists():
            return None

        payload = np.load(path, allow_pickle=True)
        return StoredMatrix(
            rows=payload["rows"].tolist(),
            column_names=[str(name) for name in payload["columns"].tolist()],
            source_index=payload["source_index"].tolist(),
            timeframe=timeframe,
        )

    def build(
        self,
        spec: DatasetSpec,
        candles_by_timeframe: Dict[str, Sequence[Candle]],
        revision: int = 1,
        note: str = "",
    ) -> DatasetManifest:
        """Build (or rebuild) the dataset for every timeframe in ``spec``."""
        slices: Dict[str, TimeframeSlice] = {}

        for timeframe in spec.timeframes:
            candles = candles_by_timeframe.get(timeframe)
            if not candles:
                raise ValidationError(
                    f"No candles supplied for {timeframe}. The dataset covers "
                    f"{', '.join(spec.timeframes)} and all of them are required."
                )

            record, rows, columns, source_index = self.build_slice(
                candles, spec.symbol, timeframe, spec.target_candles
            )
            self.save_matrix(spec.symbol, timeframe, rows, columns, source_index)
            slices[timeframe] = record

        manifest = DatasetManifest.create(spec, slices, revision=revision, note=note)
        self.save_manifest(manifest)
        return manifest

    # --------------------------------------------------------- manifest --
    def save_manifest(self, manifest: DatasetManifest) -> Path:
        path = self.manifest_path(manifest.spec.symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_manifest(self, symbol: str) -> Optional[Dict[str, Any]]:
        path = self.manifest_path(symbol)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # ---------------------------------------------------------- refresh --
    def days_since_refresh(self, symbol: str) -> Optional[float]:
        """Age of the dataset in days, or None when it does not exist."""
        manifest = self.load_manifest(symbol)
        if not manifest or not manifest.get("built_at"):
            return None
        built = datetime.fromisoformat(manifest["built_at"])
        if built.tzinfo is None:
            built = built.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - built).total_seconds() / 86400.0

    def is_refresh_due(self, symbol: str, interval_days: int = REFRESH_INTERVAL_DAYS) -> bool:
        """True when the dataset has never been built, or is older than the interval."""
        age = self.days_since_refresh(symbol)
        return age is None or age >= interval_days

    def next_refresh_at(
        self, symbol: str, interval_days: int = REFRESH_INTERVAL_DAYS
    ) -> Optional[str]:
        manifest = self.load_manifest(symbol)
        if not manifest or not manifest.get("built_at"):
            return None
        built = datetime.fromisoformat(manifest["built_at"])
        if built.tzinfo is None:
            built = built.replace(tzinfo=timezone.utc)
        return (built + timedelta(days=interval_days)).isoformat()

    def refresh(
        self,
        spec: DatasetSpec,
        candles_by_timeframe: Dict[str, Sequence[Candle]],
        note: str = "weekly refresh",
    ) -> DatasetManifest:
        """Rebuild the dataset, recomputing every feature from scratch.

        Deliberately identical to :meth:`build` except for the revision
        bump: incremental feature updates would corrupt recursive
        indicators (Phase 30 §4.2).
        """
        previous = self.load_manifest(spec.symbol)
        revision = int(previous.get("revision", 0)) + 1 if previous else 1
        return self.build(spec, candles_by_timeframe, revision=revision, note=note)

    # ----------------------------------------------------------- access --
    def window_generator(
        self,
        symbol: str,
        timeframe: str,
        target_columns: Sequence[int],
        window_size: int = 500,
        horizon: int = 5,
        stride: int = 1,
        classification: bool = False,
    ):
        """A stride-1 window generator over the stored matrix.

        This is how the trainers read the dataset: lazily, one batch at a
        time, never materialising 24 GB of overlapping windows.
        """
        from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator

        stored = self.load_matrix(symbol, timeframe)
        if stored is None:
            raise ValidationError(
                f"No stored matrix for {symbol} {timeframe}. Build the dataset "
                f"first: python scripts/run_training_dataset.py --build"
            )

        return WindowGenerator(
            series=stored.rows,
            target_columns=target_columns,
            window_size=window_size,
            horizon=horizon,
            stride=stride,
            classification=classification,
        )

    def summary(self, symbol: str) -> Dict[str, Any]:
        """Everything a human needs to judge the dataset's state."""
        manifest = self.load_manifest(symbol)
        if manifest is None:
            return {"exists": False, "symbol": symbol}

        age = self.days_since_refresh(symbol)
        return {
            "exists": True,
            "symbol": symbol,
            "revision": manifest.get("revision"),
            "built_at": manifest.get("built_at"),
            "age_days": None if age is None else round(age, 2),
            "refresh_due": self.is_refresh_due(symbol),
            "next_refresh_at": self.next_refresh_at(symbol),
            "complete": manifest.get("complete"),
            "total_candles": manifest.get("total_candles"),
            "slices": manifest.get("slices", {}),
            "warnings": manifest.get("warnings", []),
        }
