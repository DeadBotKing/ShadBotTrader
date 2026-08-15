"""Tests for the Parquet feature store."""

from datetime import datetime, timezone

import pytest

from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
    ParquetFeatureStore,
)


def _result(feature_id: str = "sma_20") -> FeatureResult:
    points = [
        FeaturePoint(
            timestamp=Timestamp(datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)),
            value=None,
        ),
        FeaturePoint(
            timestamp=Timestamp(datetime(2024, 1, 2, 8, 5, tzinfo=timezone.utc)),
            value=1.5,
        ),
    ]
    return FeatureResult(feature_id=feature_id, points=points, warmup=1)


def test_roundtrip_save_and_load(tmp_path):
    store = ParquetFeatureStore(tmp_path)
    store.save("sma_20", 1, _result())
    loaded = store.load("sma_20", 1)
    assert loaded is not None
    assert loaded.points[1].value == 1.5


def test_immutability_refuses_overwrite(tmp_path):
    store = ParquetFeatureStore(tmp_path)
    store.save("sma_20", 1, _result())
    with pytest.raises(FileExistsError):
        store.save("sma_20", 1, _result())


def test_next_version_reflects_storage(tmp_path):
    store = ParquetFeatureStore(tmp_path)
    assert store.next_version("sma_20") == 1
    store.save("sma_20", 1, _result())
    assert store.next_version("sma_20") == 2
