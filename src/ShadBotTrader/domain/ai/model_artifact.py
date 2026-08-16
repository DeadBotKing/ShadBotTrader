"""Model artifact and its integrity metadata (Phase 13, sections 10-12)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.common.errors import ValidationError


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ModelArtifact:
    """A concrete model artifact (weights/serialized model) + metadata.

    The artifact bytes carry an integrity checksum (section 12). The
    AI domain is agnostic to the concrete format (``.keras`` / ``.pt`` /
    ``.onnx`` — section 10); the ``format`` field is informational.
    """

    model_id: ModelId
    version: ModelVersion
    framework: str
    framework_version: str
    format: str
    payload: bytes
    checksum: str
    size_bytes: int
    training_run_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def __post_init__(self) -> None:
        if not self.framework.strip():
            raise ValidationError("ModelArtifact framework must not be empty")
        if self.size_bytes < 0:
            raise ValidationError("ModelArtifact size_bytes must not be negative")
        if self.checksum != sha256_hex(self.payload):
            raise ValidationError(
                f"ModelArtifact checksum mismatch for {self.model_id} v{self.version.number}"
            )

    @classmethod
    def create(
        cls,
        model_id: ModelId,
        version: ModelVersion,
        framework: str,
        framework_version: str,
        format: str,
        payload: bytes,
        training_run_id: str = "",
    ) -> "ModelArtifact":
        """Build an artifact and compute its checksum."""
        return cls(
            model_id=model_id,
            version=version,
            framework=framework,
            framework_version=framework_version,
            format=format,
            payload=payload,
            checksum=sha256_hex(payload),
            size_bytes=len(payload),
            training_run_id=training_run_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the artifact metadata as a JSON-serialisable mapping."""
        return {
            "model_id": self.model_id.value,
            "version": self.version.number,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "format": self.format,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "training_run_id": self.training_run_id,
            "created_at": self.created_at.isoformat(),
        }
