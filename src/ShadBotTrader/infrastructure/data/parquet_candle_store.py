"""Parquet storage for raw and normalized candle data (PyArrow)."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from ShadBotTrader.domain.dataset.data_layer import DataLayer
from ShadBotTrader.domain.dataset.dataset_identity import DatasetId
from ShadBotTrader.domain.dataset.ports import CandleRepository
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp

_VERSION_RE = re.compile(r"^v(\d+)\.parquet$")

_LAYER_DIR = {
    DataLayer.RAW: "raw",
    DataLayer.NORMALIZED: "processed",
}


class ParquetCandleStore(CandleRepository):
    """Persists candles as Parquet files partitioned by symbol/timeframe.

    Layout::

        {storage_root}/{raw|processed}/{symbol}/{timeframe}/v{version}.parquet

    Raw immutability is enforced here: writing to a version that already
    exists raises ``FileExistsError``, so a previous version can never be
    silently overwritten. Analytical prices are stored as float64 (the
    exact ``Decimal`` semantics remain a domain concern in memory).
    """

    def __init__(self, storage_root: Path) -> None:
        self._root = Path(storage_root)

    # ------------------------------------------------------------ ports

    def save_raw(self, dataset_id: DatasetId, version: int, records: List[RawCandleRecord]) -> None:
        """Persist raw records as an immutable Parquet file."""
        rows = [record.to_dict() for record in records]
        table = pa.Table.from_pylist(rows)
        self._write(dataset_id, DataLayer.RAW, version, table)

    def save_normalized(self, dataset_id: DatasetId, version: int, candles: List[Candle]) -> None:
        """Persist normalized candles as a Parquet file."""
        rows = [
            {
                "symbol": str(candle.symbol),
                "timeframe": str(candle.timeframe),
                "open_time": candle.open_time.value.isoformat(),
                "open": float(candle.open.amount),
                "high": float(candle.high.amount),
                "low": float(candle.low.amount),
                "close": float(candle.close.amount),
                "volume": float(candle.volume),
            }
            for candle in candles
        ]
        table = pa.Table.from_pylist(rows)
        self._write(dataset_id, DataLayer.NORMALIZED, version, table)

    def next_version(self, dataset_id: DatasetId) -> int:
        """Return the next available version, considering persisted files.

        The raw directory is the source of truth for version numbers:
        every previously ingested version exists there as
        ``v{n}.parquet``. The next version is ``max(n) + 1``, or 1 when
        nothing has been persisted yet.
        """
        directory = self._layer_dir(dataset_id, DataLayer.RAW)
        if not directory.is_dir():
            return 1
        versions: List[int] = []
        for path in directory.iterdir():
            match = _VERSION_RE.match(path.name)
            if match:
                versions.append(int(match.group(1)))
        return (max(versions) + 1) if versions else 1

    def query(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Candle]:
        """Read the latest normalized version for symbol/timeframe."""
        version = self._latest_version(str(symbol), str(timeframe))
        if version is None:
            return []
        path = self._version_path(str(symbol), str(timeframe), DataLayer.NORMALIZED, version)
        table = pq.read_table(path)
        candles: List[Candle] = []
        for row in table.to_pylist():
            open_time = _parse_iso(row["open_time"])
            if open_time is None:
                continue
            if start is not None and open_time < start:
                continue
            if end is not None and open_time > end:
                continue
            candles.append(
                Candle(
                    symbol=Symbol(row["symbol"]),
                    timeframe=Timeframe(row["timeframe"]),
                    open_time=Timestamp(open_time),
                    open_price=Price(str(row["open"])),
                    high=Price(str(row["high"])),
                    low=Price(str(row["low"])),
                    close=Price(str(row["close"])),
                    volume=Decimal(str(row["volume"])),
                )
            )
        return candles

    # --------------------------------------------------------- storage

    def _layer_dir(self, dataset_id: DatasetId, layer: DataLayer) -> Path:
        return (
            self._root
            / _LAYER_DIR[layer]
            / _canonical_symbol(dataset_id.symbol)
            / dataset_id.timeframe
        )

    def _write(
        self, dataset_id: DatasetId, layer: DataLayer, version: int, table: pa.Table
    ) -> None:
        path = self._version_path(dataset_id.symbol, dataset_id.timeframe, layer, version)
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing dataset version: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path)

    def _version_path(self, symbol: str, timeframe: str, layer: DataLayer, version: int) -> Path:
        return (
            self._root
            / _LAYER_DIR[layer]
            / _canonical_symbol(symbol)
            / timeframe
            / f"v{version}.parquet"
        )

    def _latest_version(self, symbol: str, timeframe: str) -> Optional[int]:
        directory = self._root / "processed" / _canonical_symbol(symbol) / timeframe
        if not directory.is_dir():
            return None
        versions: List[int] = []
        for path in directory.iterdir():
            match = _VERSION_RE.match(path.name)
            if match:
                versions.append(int(match.group(1)))
        return max(versions) if versions else None


def _canonical_symbol(symbol: str) -> str:
    """Return the canonical (upper, separator-free) symbol label."""
    value = symbol.strip().upper()
    for separator in ("/", "\\", "-"):
        value = value.replace(separator, "")
    return value


def _parse_iso(value: object) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("+00:00"):
        text = text[: -len("+00:00")] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed
