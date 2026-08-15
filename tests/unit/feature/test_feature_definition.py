"""Tests for FeatureId, FeatureDefinition and FeatureSet."""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.feature.feature_definition import (
    FeatureDefinition,
    FeatureId,
)
from ShadBotTrader.domain.feature.feature_set import FeatureSet, FeatureSetVersion
from ShadBotTrader.domain.feature.feature_types import (
    Causality,
    FeatureType,
    FeatureValueType,
)


def _definition(feature_id: str, **kwargs) -> FeatureDefinition:
    defaults = {
        "feature_id": FeatureId(feature_id),
        "name": feature_id,
        "feature_type": FeatureType.TREND,
        "value_type": FeatureValueType.SCALAR,
        "parameters": {"period": 20},
        "lookback": 19,
        "computation_version": "1",
    }
    defaults.update(kwargs)
    return FeatureDefinition(**defaults)


def test_feature_id_normalizes():
    assert FeatureId("SMA 20").value == "sma_20"
    assert FeatureId("sma_20") == FeatureId("SMA_20")


def test_feature_id_rejects_empty():
    with pytest.raises(ValidationError):
        FeatureId("   ")


def test_definition_requires_parameters():
    with pytest.raises(ValidationError):
        _definition("sma_20", parameters={})


def test_non_causal_definition_is_not_live_compatible():
    definition = _definition("centered_20", causality=Causality.NON_CAUSAL)
    assert definition.is_live_compatible is False


def test_feature_set_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        FeatureSet(
            name="dup",
            version=FeatureSetVersion(1),
            definitions=[_definition("sma_20"), _definition("sma_20")],
        )


def test_feature_set_feature_ids_order():
    feature_set = FeatureSet(
        name="fx",
        version=FeatureSetVersion(1),
        definitions=[_definition("sma_20"), _definition("rsi_14")],
    )
    assert feature_set.feature_ids == ["sma_20", "rsi_14"]
