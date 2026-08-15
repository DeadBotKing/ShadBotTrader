"""Versioned data schemas."""

from __future__ import annotations

from typing import Any, List

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class SchemaField(ValueObject):
    """A single named field of a data schema."""

    def __init__(self, name: str, data_type: str, required: bool = True) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("SchemaField name must not be empty")
        if not data_type.strip():
            raise ValidationError(f"SchemaField {normalized} data_type must not be empty")
        self._name = normalized
        self._data_type = data_type.strip()
        self._required = required

    @property
    def name(self) -> str:
        return self._name

    @property
    def data_type(self) -> str:
        return self._data_type

    @property
    def required(self) -> bool:
        return self._required

    def _value(self) -> tuple[Any, ...]:
        return (self._name, self._data_type, self._required)

    def __str__(self) -> str:
        return f"{self._name}:{self._data_type}" + ("" if self._required else "?")


class SchemaVersion(ValueObject):
    """A schema version; breaking changes bump this value."""

    def __init__(self, number: int) -> None:
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValidationError(f"SchemaVersion must be >= 1, got {number!r}")
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    def _value(self) -> tuple[Any, ...]:
        return (self._number,)

    def __str__(self) -> str:
        return f"v{self._number}"


class DataSchema(ValueObject):
    """A named, versioned, ordered list of fields."""

    def __init__(self, name: str, version: SchemaVersion, fields: List[SchemaField]) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValidationError("DataSchema name must not be empty")
        if not fields:
            raise ValidationError(f"DataSchema {normalized} must declare at least one field")
        field_names = [field.name for field in fields]
        if len(field_names) != len(set(field_names)):
            raise ValidationError(f"DataSchema {normalized} has duplicate field names")
        self._name = normalized
        self._version = version
        self._fields = tuple(fields)

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> SchemaVersion:
        return self._version

    @property
    def fields(self) -> tuple[SchemaField, ...]:
        return self._fields

    def field_names(self) -> tuple[str, ...]:
        """The names of all fields in order."""
        return tuple(field.name for field in self._fields)

    def required_names(self) -> tuple[str, ...]:
        """The names of required fields."""
        return tuple(field.name for field in self._fields if field.required)

    def _value(self) -> tuple[Any, ...]:
        return (self._name, self._version, self._fields)

    def __str__(self) -> str:
        return f"{self._name} {self._version}"


def candle_schema_v1() -> DataSchema:
    """The canonical market-candle schema (Phase 11, section 26)."""
    return DataSchema(
        name="candle",
        version=SchemaVersion(1),
        fields=[
            SchemaField("symbol", "string"),
            SchemaField("timeframe", "string"),
            SchemaField("timestamp", "timestamp"),
            SchemaField("open", "decimal"),
            SchemaField("high", "decimal"),
            SchemaField("low", "decimal"),
            SchemaField("close", "decimal"),
            SchemaField("volume", "decimal"),
        ],
    )
