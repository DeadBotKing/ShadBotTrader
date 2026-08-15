"""Tests for DataSchema and the candle schema."""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.data_schema import (
    DataSchema,
    SchemaField,
    SchemaVersion,
    candle_schema_v1,
)


def test_candle_schema_v1_has_required_fields():
    schema = candle_schema_v1()
    assert schema.name == "candle"
    assert schema.version == SchemaVersion(1)
    assert set(schema.required_names()) == {
        "symbol",
        "timeframe",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }


def test_schema_rejects_duplicate_field_names():
    with pytest.raises(ValidationError):
        DataSchema(
            name="bad",
            version=SchemaVersion(1),
            fields=[SchemaField("a", "string"), SchemaField("a", "string")],
        )


def test_schema_rejects_empty_fields():
    with pytest.raises(ValidationError):
        DataSchema(name="bad", version=SchemaVersion(1), fields=[])


def test_schema_equality_by_value():
    first = DataSchema("x", SchemaVersion(1), [SchemaField("a", "string")])
    second = DataSchema("x", SchemaVersion(1), [SchemaField("a", "string")])
    assert first == second
