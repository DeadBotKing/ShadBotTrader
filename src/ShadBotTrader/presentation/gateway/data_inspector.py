"""Read-only inspection of what is actually stored (Phase 34).

After a fetch, a feature computation or a dataset build, the operator
needs to answer three questions without opening a terminal:

    how many candles are stored, and over what period?
    what do those candles look like?
    which columns exist, and are any of them broken?

This gateway answers them by reading the stores. It is a **Gateway** in
the Phase 19 sense: it queries and shapes data for display, and performs
no computation of its own — the numbers it reports are the numbers that
were written, not numbers it derived.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe

#: Candles sent to the chart. Enough to see structure, few enough that
#: the page stays a page rather than a download.
DEFAULT_CHART_CANDLES = 5000


@dataclass(frozen=True)
class ColumnInfo:
    """One column of a stored matrix, described honestly."""

    name: str
    kind: str
    non_null: int
    total: int
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    sample: Optional[float] = None

    @property
    def coverage(self) -> float:
        return (self.non_null / self.total * 100.0) if self.total else 0.0

    @property
    def is_complete(self) -> bool:
        return self.non_null == self.total

    @property
    def is_constant(self) -> bool:
        """A column that never varies teaches a model nothing."""
        if self.minimum is None or self.maximum is None:
            return False
        return self.minimum == self.maximum

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "non_null": self.non_null,
            "total": self.total,
            "coverage": round(self.coverage, 2),
            "complete": self.is_complete,
            "constant": self.is_constant,
            "min": self.minimum,
            "max": self.maximum,
            "sample": self.sample,
        }


@dataclass
class CandleSetInfo:
    """What is stored for one symbol and timeframe."""

    symbol: str
    timeframe: str
    count: int = 0
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None
    continuity: Optional[Dict[str, Any]] = None
    chart: List[Dict[str, Any]] = field(default_factory=list)
    price_low: Optional[float] = None
    price_high: Optional[float] = None

    @property
    def exists(self) -> bool:
        return self.count > 0

    @property
    def span_days(self) -> Optional[float]:
        if self.first_time is None or self.last_time is None:
            return None
        return (self.last_time - self.first_time).total_seconds() / 86400.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "count": self.count,
            "exists": self.exists,
            "first_time": self.first_time.isoformat() if self.first_time else None,
            "last_time": self.last_time.isoformat() if self.last_time else None,
            "span_days": round(self.span_days, 1) if self.span_days else None,
            "price_low": self.price_low,
            "price_high": self.price_high,
            "continuity": self.continuity,
            "chart": self.chart,
        }


@dataclass
class MatrixInfo:
    """A stored feature matrix, summarised column by column."""

    symbol: str
    timeframe: str
    rows: int = 0
    columns: List[ColumnInfo] = field(default_factory=list)
    digest: str = ""
    built_at: str = ""
    revision: Optional[int] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return self.rows > 0

    @property
    def column_count(self) -> int:
        return len(self.columns)

    @property
    def incomplete_columns(self) -> List[ColumnInfo]:
        return [column for column in self.columns if not column.is_complete]

    @property
    def constant_columns(self) -> List[ColumnInfo]:
        return [column for column in self.columns if column.is_constant]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "rows": self.rows,
            "exists": self.exists,
            "column_count": self.column_count,
            "digest": self.digest,
            "built_at": self.built_at,
            "revision": self.revision,
            "warnings": list(self.warnings),
            "incomplete": [c.name for c in self.incomplete_columns],
            "constant": [c.name for c in self.constant_columns],
            "columns": [column.to_dict() for column in self.columns],
        }


class DataInspector:
    """Reads the candle store, the feature store and the training matrix."""

    def __init__(
        self,
        storage_root: str | Path = "datasets",
        chart_candles: int = DEFAULT_CHART_CANDLES,
    ) -> None:
        self._root = Path(storage_root)
        self._chart_candles = chart_candles

    # ---------------------------------------------------------- candles --
    def candles(
        self,
        symbol: str,
        timeframe: str,
        chart_candles: Optional[int] = None,
    ) -> CandleSetInfo:
        """Everything known about one stored candle series."""
        from ShadBotTrader.infrastructure.data.parquet_candle_store import (
            ParquetCandleStore,
        )

        info = CandleSetInfo(symbol=symbol, timeframe=timeframe)
        try:
            stored: Sequence[Candle] = ParquetCandleStore(self._root).query(
                Symbol(symbol), Timeframe(timeframe)
            )
        except Exception:
            # Nothing stored yet, or an unreadable store: an empty result
            # is the honest answer, not an exception in a dashboard.
            return info

        if not stored:
            return info

        ordered = sorted(stored, key=lambda candle: candle.open_time.value)
        info.count = len(ordered)
        info.first_time = ordered[0].open_time.value
        info.last_time = ordered[-1].open_time.value

        window = ordered[-(chart_candles or self._chart_candles) :]
        chart_offset = len(ordered) - len(window)
        info.chart = [
            {
                "i": chart_offset + index,  # فاز ۸۴: اندیس سراسری برای رسم سیگنال
                "t": candle.open_time.value.isoformat(),
                "o": float(candle.open.amount),
                "h": float(candle.high.amount),
                "l": float(candle.low.amount),
                "c": float(candle.close.amount),
                "v": float(candle.volume),
            }
            for index, candle in enumerate(window)
        ]
        info.price_low = min(float(candle.low.amount) for candle in window)
        info.price_high = max(float(candle.high.amount) for candle in window)

        try:
            from ShadBotTrader.domain.dataset.continuity import analyse_continuity

            report = analyse_continuity(ordered, Timeframe(timeframe), tolerance=2)
            info.continuity = report.to_dict()
        except Exception:
            info.continuity = None

        return info

    def available_series(self) -> List[Dict[str, str]]:
        """Every symbol/timeframe pair with stored candles."""
        processed = self._root / "processed"
        if not processed.is_dir():
            return []

        found: List[Dict[str, str]] = []
        for symbol_dir in sorted(processed.iterdir()):
            if not symbol_dir.is_dir():
                continue
            for timeframe_dir in sorted(symbol_dir.iterdir()):
                if not timeframe_dir.is_dir():
                    continue
                if any(timeframe_dir.glob("v*.parquet")):
                    found.append({"symbol": symbol_dir.name, "timeframe": timeframe_dir.name})
        return found

    # --------------------------------------------------------- features --
    def features(self, limit: int = 200) -> Dict[str, Any]:
        """Which catalogue features have been computed and stored."""
        directory = self._root / "features"
        if not directory.is_dir():
            return {"exists": False, "count": 0, "features": []}

        entries: List[Dict[str, Any]] = []

        def collect(feature_dir: Path, series: str) -> None:
            versions = sorted(
                int(path.stem[1:])
                for path in feature_dir.glob("v*.parquet")
                if path.stem[1:].isdigit()
            )
            if not versions:
                return
            newest = feature_dir / f"v{versions[-1]}.parquet"
            entries.append(
                {
                    "feature_id": feature_dir.name,
                    "series": series,
                    "versions": len(versions),
                    "latest_version": versions[-1],
                    "size_kb": round(newest.stat().st_size / 1024, 1),
                }
            )

        # Phase 37 layout: features/{symbol}/{timeframe}/{feature_id}/.
        # Anything directly under features/ is pre-Phase-37 data whose
        # series is unknown — it is listed as such rather than hidden.
        for entry in sorted(directory.iterdir()):
            if not entry.is_dir():
                continue
            if list(entry.glob("v*.parquet")):
                collect(entry, "legacy (no timeframe recorded)")
                continue
            for timeframe_dir in sorted(entry.iterdir()):
                if not timeframe_dir.is_dir():
                    continue
                for feature_dir in sorted(timeframe_dir.iterdir()):
                    if feature_dir.is_dir():
                        collect(feature_dir, f"{entry.name} {timeframe_dir.name}")

        return {
            "exists": bool(entries),
            "count": len(entries),
            "features": entries[:limit],
            "truncated": len(entries) > limit,
        }

    def feature_values(self, feature_id: str, points: int = 300) -> Dict[str, Any]:
        """The most recent values of one computed feature."""
        from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
            ParquetFeatureStore,
        )

        store = ParquetFeatureStore(self._root)
        directory = self._root / "features" / feature_id
        if not directory.is_dir():
            return {"exists": False, "feature_id": feature_id}

        versions = sorted(
            int(path.stem[1:]) for path in directory.glob("v*.parquet") if path.stem[1:].isdigit()
        )
        if not versions:
            return {"exists": False, "feature_id": feature_id}

        result = store.load(feature_id, versions[-1])
        if result is None:
            return {"exists": False, "feature_id": feature_id}

        recent = result.points[-points:]
        values = [point.value for point in recent if point.value is not None]
        return {
            "exists": True,
            "feature_id": feature_id,
            "version": versions[-1],
            "total_points": len(result.points),
            "available": result.available_count,
            "missing": len(result.points) - result.available_count,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "series": [
                {"t": point.timestamp.value.isoformat(), "v": point.value} for point in recent
            ],
        }

    # ---------------------------------------------------- training data --
    def training_matrix(self, symbol: str, timeframe: str) -> MatrixInfo:
        """Column-by-column description of a stored training matrix."""
        from ShadBotTrader.application.services.training_data_service import (
            TrainingDataService,
        )

        info = MatrixInfo(symbol=symbol, timeframe=timeframe)
        service = TrainingDataService(self._root)

        try:
            stored = service.load_matrix(symbol, timeframe)
        except Exception:
            return info
        if stored is None or not stored.rows:
            return info

        info.rows = len(stored.rows)
        info.columns = _describe_columns(stored.rows, stored.column_names)

        manifest = service.load_manifest(symbol)
        if manifest:
            info.built_at = str(manifest.get("built_at", ""))
            info.revision = manifest.get("revision")
            info.warnings = list(manifest.get("warnings", []))
            slice_info = (manifest.get("slices") or {}).get(timeframe) or {}
            info.digest = str(slice_info.get("digest", ""))

        return info

    def training_summary(self, symbol: str) -> Dict[str, Any]:
        from ShadBotTrader.application.services.training_data_service import (
            TrainingDataService,
        )

        try:
            return TrainingDataService(self._root).summary(symbol)
        except Exception:
            return {"exists": False, "symbol": symbol}


def _describe_columns(rows: Sequence[Sequence[float]], names: Sequence[str]) -> List[ColumnInfo]:
    """Summarise each column: coverage, range and a sample value.

    Scanning every cell of a 100,000 x 123 matrix would make the page
    slow for no benefit, so an evenly spread sample is used and the row
    total is reported honestly alongside it.
    """
    import math

    if not rows:
        return []

    width = len(rows[0])
    step = max(len(rows) // 2000, 1)
    sampled = rows[::step]
    total = len(sampled)

    described: List[ColumnInfo] = []
    for index in range(width):
        name = names[index] if index < len(names) else f"column_{index}"
        values: List[float] = []
        for row in sampled:
            if index >= len(row):
                continue
            value = row[index]
            if value is None:
                continue
            numeric = float(value)
            if math.isfinite(numeric):
                values.append(numeric)

        described.append(
            ColumnInfo(
                name=name,
                kind=_classify(name),
                non_null=len(values),
                total=total,
                minimum=min(values) if values else None,
                maximum=max(values) if values else None,
                sample=values[-1] if values else None,
            )
        )
    return described


def _classify(name: str) -> str:
    """Which group a column belongs to, for display only."""
    lowered = name.lower()
    if lowered.endswith("_rel") or lowered == "volume_raw_log":
        return "raw price"
    if lowered in (
        "return_1",
        "range_pct",
        "body_pct",
        "upper_wick_pct",
        "lower_wick_pct",
        "volume_log",
    ):
        return "candle shape"
    if lowered.startswith(("future_", "signal_")):
        return "target"
    return "feature"
