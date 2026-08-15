"""The raw, unvalidated market-data record (L0/L1 boundary)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class RawCandleRecord:
    """A single raw candle row exactly as it arrived from a provider.

    All fields are strings on purpose: raw data is stored *before* any
    validation or typing, so it preserves what the provider sent and can
    be replayed or re-validated later.
    """

    symbol: str
    timeframe: str
    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    extra: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Return the record as a flat, JSON-serialisable mapping."""
        data: Dict[str, Any] = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        data.update(self.extra)
        return data

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, Any],
        default_symbol: str,
        default_timeframe: str,
    ) -> "RawCandleRecord":
        """Build a record from a provider row, filling symbol/timeframe.

        The symbol and timeframe default to the requested values when the
        provider row does not carry them explicitly.
        """
        data = {str(key): value for key, value in mapping.items()}
        extra = {key: value for key, value in data.items() if key not in _CORE_FIELDS}
        core = {key: _as_text(data.get(key, "")) for key in _CORE_FIELDS}
        return cls(
            symbol=core["symbol"] or default_symbol,
            timeframe=core["timeframe"] or default_timeframe,
            timestamp=core["timestamp"],
            open=core["open"],
            high=core["high"],
            low=core["low"],
            close=core["close"],
            volume=core["volume"],
            extra=extra,
        )


_CORE_FIELDS = ("symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
