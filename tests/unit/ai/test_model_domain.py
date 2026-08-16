"""Tests for model identity, definition and artifact integrity."""

import pytest

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact, sha256_hex
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.common.errors import ValidationError


def _definition() -> ModelDefinition:
    return ModelDefinition(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        name="Gold direction classifier",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={"window_size": 16},
    )


def test_model_id_normalizes():
    assert ModelId("Gold Direction").value == "gold_direction"
    assert ModelId("gold_direction") == ModelId("GOLD_DIRECTION")


def test_model_version_monotonic():
    assert ModelVersion(1).next() == ModelVersion(2)
    with pytest.raises(ValidationError):
        ModelVersion(0)


def test_definition_requires_target_and_features():
    with pytest.raises(ValidationError):
        ModelDefinition(
            model_id=ModelId("m"),
            version=ModelVersion(1),
            name="m",
            model_type=ModelType.CLASSIFICATION,
            family=ModelFamily.WAVENET,
            feature_set_name="",
            feature_set_version=1,
            target_name="direction",
            hyperparameters={},
        )


def test_artifact_checksum_verified():
    payload = b"model weights here"
    artifact = ModelArtifact.create(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        framework="tensorflow",
        framework_version="2.21",
        format="keras",
        payload=payload,
    )
    assert artifact.checksum == sha256_hex(payload)
    assert artifact.size_bytes == len(payload)


def test_artifact_tamper_detected():
    payload = b"weights"
    artifact = ModelArtifact.create(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        framework="tensorflow",
        framework_version="2.21",
        format="keras",
        payload=payload,
    )
    with pytest.raises(ValidationError):
        ModelArtifact(
            model_id=artifact.model_id,
            version=artifact.version,
            framework=artifact.framework,
            framework_version=artifact.framework_version,
            format=artifact.format,
            payload=b"TAMPERED",
            checksum=artifact.checksum,  # mismatch -> ValidationError
            size_bytes=len(b"TAMPERED"),
        )
