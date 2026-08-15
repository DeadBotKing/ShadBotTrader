"""Canonicalises validated records into domain candles (L3)."""

from __future__ import annotations

from datetime import timezone
from typing import List

from ShadBotTrader.domain.dataset.pipeline import (
    CandleNormalizerPort,
    NormalizationResult,
    ValidatedCandleRecord,
)
from ShadBotTrader.domain.dataset.quality_report import IssueSeverity, QualityIssue
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp

_SEPARATOR_TABLE = {"/": "", "\\": "", "-": ""}


class CandleNormalizer(CandleNormalizerPort):
    """Canonicalises validated records (L2 → L3).

    Normalization performed:

    * symbol canonicalisation: uppercase, separators removed
      (``EUR/USD`` → ``EURUSD``, matching Phase 11 section 9)
    * timeframe canonicalisation via the :class:`Timeframe` value object
    * every timestamp converted to UTC
    * exact ``Decimal`` prices preserved (no float conversion)
    """

    def normalize(self, records: List[ValidatedCandleRecord]) -> NormalizationResult:
        """Convert every validated record into a domain candle."""
        candles: List[Candle] = []
        issues: List[QualityIssue] = []
        for record in records:
            candle = self._normalize_one(record)
            if candle is None:
                issues.append(
                    QualityIssue(
                        code="NORMALIZATION_FAILED",
                        severity=IssueSeverity.CRITICAL,
                        message=f"Could not normalize row at {record.open_time.isoformat()}",
                    )
                )
            else:
                candles.append(candle)
        return NormalizationResult(candles=candles, issues=issues)

    def _normalize_one(self, record: ValidatedCandleRecord) -> Candle | None:
        try:
            symbol = Symbol(self.canonical_symbol(record.symbol))
            timeframe = Timeframe(record.timeframe)
            open_time = Timestamp(record.open_time.astimezone(timezone.utc))
            return Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=open_time,
                open_price=Price(record.open),
                high=Price(record.high),
                low=Price(record.low),
                close=Price(record.close),
                volume=record.volume,
            )
        except Exception:
            # Domain invariants (e.g. Timeframe parsing) can still reject
            # a record; the caller flags it without crashing the batch.
            return None

    @staticmethod
    def canonical_symbol(symbol: str) -> str:
        """Return the canonical form of a symbol label."""
        value = symbol.strip().upper()
        for separator, replacement in _SEPARATOR_TABLE.items():
            value = value.replace(separator, replacement)
        return value
