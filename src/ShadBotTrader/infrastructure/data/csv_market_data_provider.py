"""A market-data provider that reads candle CSV files."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from ShadBotTrader.domain.dataset.ports import MarketDataProvider
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord


class CsvMarketDataProvider(MarketDataProvider):
    """Reads raw candle rows from a CSV file (L0/L1 boundary).

    The CSV must contain the core candle columns (``timestamp``,
    ``open``, ``high``, ``low``, ``close``, ``volume``) and may carry
    ``symbol`` / ``timeframe``; when missing, the requested values are
    used. Every extra column is preserved inside the raw record so no
    provider information is lost.
    """

    @property
    def provider_name(self) -> str:
        return "csv"

    def fetch_candles(self, symbol: str, timeframe: str, source: str) -> List[RawCandleRecord]:
        """Read all rows from the CSV file at ``source``."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"CSV source not found: {source}")
        records: List[RawCandleRecord] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                records.append(
                    RawCandleRecord.from_mapping(
                        mapping=row,
                        default_symbol=symbol,
                        default_timeframe=timeframe,
                    )
                )
        return records
