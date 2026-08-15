"""Validates raw candle records into typed, range-checked records (L2)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List

from ShadBotTrader.domain.dataset.data_schema import DataSchema, candle_schema_v1
from ShadBotTrader.domain.dataset.pipeline import (
    CandleValidatorPort,
    ValidatedCandleRecord,
    ValidationResult,
)
from ShadBotTrader.domain.dataset.quality_report import IssueSeverity, QualityIssue
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord


class CandleValidator(CandleValidatorPort):
    """Checks raw records against the candle schema (L2).

    Checks performed per record:

    * required fields present and non-empty
    * prices and volume parse as non-negative decimals
    * prices are positive
    * ``high >= low``, ``high >= open/close``, ``low <= open/close``
    * timestamps parse and carry timezone information

    Duplicate detection by ``(symbol, timeframe, timestamp)`` is a
    separate quality concern handled by the quality analyzer.
    """

    def __init__(self, schema: DataSchema | None = None) -> None:
        self._schema = schema or candle_schema_v1()

    @property
    def schema(self) -> DataSchema:
        return self._schema

    def validate(self, records: List[RawCandleRecord]) -> ValidationResult:
        """Validate every raw record, skipping invalid ones."""
        valid: List[ValidatedCandleRecord] = []
        issues: List[QualityIssue] = []
        for record in records:
            result = self._validate_one(record)
            if result is None:
                continue
            if isinstance(result, QualityIssue):
                issues.append(result)
            else:
                valid.append(result)
        return ValidationResult(records=valid, issues=issues)

    def _validate_one(self, record: RawCandleRecord) -> ValidatedCandleRecord | QualityIssue | None:
        missing = [
            name
            for name in ("timestamp", "open", "high", "low", "close", "volume")
            if not getattr(record, name)
        ]
        if missing:
            return QualityIssue(
                code="MISSING_REQUIRED_FIELDS",
                severity=IssueSeverity.CRITICAL,
                message=f"Missing required fields: {', '.join(missing)}",
            )

        prices = self._parse_prices(record)
        if prices is None:
            return QualityIssue(
                code="INVALID_PRICE",
                severity=IssueSeverity.CRITICAL,
                message=f"Non-numeric or non-positive price on row at {record.timestamp!r}",
            )
        open_price, high, low, close = prices

        try:
            volume = Decimal(record.volume)
        except (InvalidOperation, ValueError):
            volume = None
        if volume is None or volume < 0:
            return QualityIssue(
                code="INVALID_VOLUME",
                severity=IssueSeverity.CRITICAL,
                message=f"Invalid volume {record.volume!r} on row at {record.timestamp!r}",
            )

        open_time = self._parse_timestamp(record.timestamp)
        if open_time is None:
            return QualityIssue(
                code="INVALID_TIMESTAMP",
                severity=IssueSeverity.CRITICAL,
                message=f"Invalid timestamp {record.timestamp!r}",
            )

        if high < low:
            return QualityIssue(
                code="HIGH_LOW_VIOLATION",
                severity=IssueSeverity.CRITICAL,
                message=f"high < low on row at {record.timestamp!r}",
            )
        if high < max(open_price, close):
            return QualityIssue(
                code="HIGH_RANGE_VIOLATION",
                severity=IssueSeverity.CRITICAL,
                message=f"high < max(open, close) on row at {record.timestamp!r}",
            )
        if low > min(open_price, close):
            return QualityIssue(
                code="LOW_RANGE_VIOLATION",
                severity=IssueSeverity.CRITICAL,
                message=f"low > min(open, close) on row at {record.timestamp!r}",
            )

        return ValidatedCandleRecord(
            symbol=record.symbol.strip(),
            timeframe=record.timeframe.strip(),
            open_time=open_time,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

    @staticmethod
    def _parse_prices(record: RawCandleRecord) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
        try:
            open_price = Decimal(record.open)
            high = Decimal(record.high)
            low = Decimal(record.low)
            close = Decimal(record.close)
        except (InvalidOperation, ValueError):
            return None
        if min(open_price, high, low, close) <= 0:
            return None
        return open_price, high, low, close

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        text = value.strip().replace("Z", "+00:00")
        if " " in text and "T" not in text:
            text = text.replace(" ", "T", 1)
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
