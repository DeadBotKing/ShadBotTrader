"""Tests for the model registry and filesystem artifact store."""

import pytest

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
    FilesystemArtifactStore,
)
from ShadBotTrader.infrastructure.ai.in_memory_model_registry import (
    InMemoryModelRegistry,
)


def _definition(version: int = 1) -> ModelDefinition:
    return ModelDefinition(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(version),
        name="Gold direction",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={"window_size": 16},
    )


def test_registry_latest_version():
    registry = InMemoryModelRegistry()
    registry.register(_definition(1))
    registry.register(_definition(2))
    assert registry.latest_version(ModelId("gold_direction")) == ModelVersion(2)
    assert registry.get(ModelId("gold_direction"), ModelVersion(1)).version.number == 1


def test_artifact_store_roundtrip_and_immutability(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    artifact = ModelArtifact.create(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        framework="tensorflow",
        framework_version="2.21",
        format="keras",
        payload=b"model bytes",
    )
    store.save(artifact)
    loaded = store.load(ModelId("gold_direction"), ModelVersion(1))
    assert loaded is not None
    assert loaded.payload == b"model bytes"
    assert loaded.checksum == artifact.checksum

    with pytest.raises(FileExistsError):
        store.save(artifact)


def test_artifact_store_missing_returns_none(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    assert store.load(ModelId("nope"), ModelVersion(1)) is None
