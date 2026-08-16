"""Filesystem persistence of model artifacts (with checksums)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.ports import ModelArtifactStore


class FilesystemArtifactStore(ModelArtifactStore):
    """Stores artifacts as ``models/{model_id}/v{version}.bin`` + metadata JSON.

    Immutability: writing to an existing version raises ``FileExistsError``.
    Loading re-verifies the checksum so corrupted artifacts are detected.
    """

    def __init__(self, storage_root: Path) -> None:
        self._root = Path(storage_root) / "models"

    def save(self, artifact: ModelArtifact) -> None:
        payload_path, metadata_path = self._paths(artifact.model_id, artifact.version)
        if payload_path.exists():
            raise FileExistsError(f"Refusing to overwrite model artifact: {payload_path}")
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_bytes(artifact.payload)
        metadata_path.write_text(
            json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )

    def load(self, model_id: ModelId, version: ModelVersion) -> Optional[ModelArtifact]:
        payload_path, metadata_path = self._paths(model_id, version)
        if not payload_path.exists() or not metadata_path.exists():
            return None
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        payload = payload_path.read_bytes()
        artifact = ModelArtifact(
            model_id=ModelId(metadata["model_id"]),
            version=ModelVersion(metadata["version"]),
            framework=metadata["framework"],
            framework_version=metadata["framework_version"],
            format=metadata["format"],
            payload=payload,
            checksum=metadata["checksum"],
            size_bytes=metadata["size_bytes"],
            training_run_id=metadata.get("training_run_id", ""),
        )
        # constructor re-verifies checksum — corruption raises ValidationError
        return artifact

    def exists(self, model_id: ModelId, version: ModelVersion) -> bool:
        payload_path, _ = self._paths(model_id, version)
        return payload_path.exists()

    def _paths(self, model_id: ModelId, version: ModelVersion) -> tuple[Path, Path]:
        directory = self._root / model_id.value
        return (
            directory / f"v{version.number}.bin",
            directory / f"v{version.number}.json",
        )
