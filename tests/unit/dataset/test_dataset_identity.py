"""Tests for DatasetId and DatasetVersion."""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId
from ShadBotTrader.domain.dataset.dataset_version import DatasetVersion


def test_dataset_id_equality_and_label():
    first = DatasetId("csv", DataKind.MARKET_CANDLE, "XAUUSD_i", "5M", "L1_raw")
    second = DatasetId("csv", DataKind.MARKET_CANDLE, "xauusd_i", "5m", "L1_raw")
    assert first == second  # symbol/timeframe normalized
    assert first.label == "csv.market_candle.XAUUSD_I.5M.L1_raw"


def test_dataset_id_rejects_empty_parts():
    with pytest.raises(ValidationError):
        DatasetId("", DataKind.MARKET_CANDLE, "XAUUSD_i", "5M", "L1_raw")
    with pytest.raises(ValidationError):
        DatasetId("csv", DataKind.MARKET_CANDLE, "", "5M", "L1_raw")


def test_dataset_version_monotonic():
    version = DatasetVersion(1)
    assert version.next().number == 2
    assert version == DatasetVersion(1)


def test_dataset_version_rejects_invalid():
    with pytest.raises(ValidationError):
        DatasetVersion(0)
    with pytest.raises(ValidationError):
        DatasetVersion(-1)
    with pytest.raises(ValidationError):
        DatasetVersion(1.5)  # type: ignore[arg-type]
