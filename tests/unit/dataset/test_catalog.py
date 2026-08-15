"""Tests for the in-memory dataset catalog."""

from ShadBotTrader.domain.dataset.data_layer import DataLayer
from ShadBotTrader.domain.dataset.data_schema import candle_schema_v1
from ShadBotTrader.domain.dataset.dataset_descriptor import DatasetDescriptor
from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId
from ShadBotTrader.domain.dataset.dataset_version import DatasetVersion
from ShadBotTrader.infrastructure.data.in_memory_dataset_catalog import (
    InMemoryDatasetRepository,
)


def _id() -> DatasetId:
    return DatasetId("csv", DataKind.MARKET_CANDLE, "XAUUSD_i", "5M", DataLayer.RAW.value)


def _descriptor(version: int) -> DatasetDescriptor:
    return DatasetDescriptor(
        dataset_id=_id(),
        version=DatasetVersion(version),
        schema=candle_schema_v1(),
        layer=DataLayer.RAW,
        row_count=10,
    )


def test_next_version_starts_at_one():
    catalog = InMemoryDatasetRepository()
    assert catalog.next_version(_id()) == 1
    catalog.register(_descriptor(1))
    assert catalog.next_version(_id()) == 2


def test_get_returns_latest_version():
    catalog = InMemoryDatasetRepository()
    catalog.register(_descriptor(1))
    catalog.register(_descriptor(2))
    assert catalog.get(_id()).version.number == 2


def test_list_all_returns_registered():
    catalog = InMemoryDatasetRepository()
    catalog.register(_descriptor(1))
    assert len(catalog.list_all()) == 1
