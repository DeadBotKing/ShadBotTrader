"""Durable model, dataset, feature and training-run registries (Phase 20)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.ai.ports import ModelRegistry, TrainingRunRepository
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.domain.dataset.dataset_descriptor import DatasetDescriptor
from ShadBotTrader.domain.dataset.dataset_identity import DatasetId
from ShadBotTrader.domain.dataset.ports import DatasetRepository
from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.ports import FeatureRegistry
from ShadBotTrader.infrastructure.persistence.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteModelRegistry(ModelRegistry):
    """Model catalogue backed by SQLite."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def register(self, definition: ModelDefinition) -> None:
        payload = {
            "name": definition.name,
            "model_type": definition.model_type.value,
            "family": definition.family.value,
            "feature_set_name": definition.feature_set_name,
            "feature_set_version": definition.feature_set_version,
            "target_name": definition.target_name,
            "hyperparameters": _jsonable(definition.hyperparameters),
            "input_schema": _jsonable(definition.input_schema),
            "output_schema": _jsonable(definition.output_schema),
            "description": definition.description,
        }
        self._database.execute(
            """
            INSERT INTO ai_model
                (model_id, version, name, model_type, family, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_id, version) DO UPDATE SET
                name       = excluded.name,
                model_type = excluded.model_type,
                family     = excluded.family,
                payload    = excluded.payload
            """,
            (
                definition.model_id.value,
                definition.version.number,
                definition.name,
                definition.model_type.value,
                definition.family.value,
                json.dumps(payload, default=str),
                _now(),
            ),
        )

    def get(self, model_id: ModelId, version: ModelVersion) -> Optional[ModelDefinition]:
        row = self._database.query_one(
            "SELECT * FROM ai_model WHERE model_id = ? AND version = ?",
            (model_id.value, version.number),
        )
        return _row_to_model(row) if row is not None else None

    def latest_version(self, model_id: ModelId) -> Optional[ModelVersion]:
        row = self._database.query_one(
            "SELECT MAX(version) AS version FROM ai_model WHERE model_id = ?",
            (model_id.value,),
        )
        if row is None or row["version"] is None:
            return None
        return ModelVersion(int(row["version"]))

    def list_all(self) -> List[ModelDefinition]:
        rows = self._database.query("SELECT * FROM ai_model ORDER BY model_id, version")
        return [_row_to_model(row) for row in rows]


class SqliteTrainingRunRepository(TrainingRunRepository):
    """Training-run history backed by SQLite (reproducibility record)."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def record(self, run: TrainingRun) -> None:
        payload = {
            "dataset_version": run.dataset_version,
            "feature_set_name": run.feature_set_name,
            "feature_set_version": run.feature_set_version,
            "hyperparameters": _jsonable(run.hyperparameters),
        }
        self._database.execute(
            """
            INSERT INTO ai_training_run
                (run_id, model_id, model_version, seed, payload, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload = excluded.payload
            """,
            (
                run.run_id,
                run.model_id.value,
                run.model_version.number,
                run.seed,
                json.dumps(payload, default=str),
                run.started_at.isoformat(),
            ),
        )

    def get(self, run_id: str) -> Optional[TrainingRun]:
        row = self._database.query_one("SELECT * FROM ai_training_run WHERE run_id = ?", (run_id,))
        return _row_to_run(row) if row is not None else None

    def list_for_model(self, model_id: ModelId) -> List[TrainingRun]:
        rows = self._database.query(
            "SELECT * FROM ai_training_run WHERE model_id = ? ORDER BY started_at",
            (model_id.value,),
        )
        return [_row_to_run(row) for row in rows]


class SqliteDatasetRepository(DatasetRepository):
    """Dataset catalogue backed by SQLite."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def register(self, descriptor: DatasetDescriptor) -> None:
        dataset_id = descriptor.dataset_id
        payload = {
            "label": dataset_id.label,
            "status": descriptor.status.value,
            "row_count": descriptor.row_count,
            "layer": descriptor.layer.value,
            "time_start": (descriptor.time_start.isoformat() if descriptor.time_start else None),
            "time_end": descriptor.time_end.isoformat() if descriptor.time_end else None,
        }
        self._database.execute(
            """
            INSERT INTO market_dataset
                (dataset_key, version, provider, kind, symbol, timeframe, layer,
                 status, row_count, time_start, time_end, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_key, version) DO UPDATE SET
                status    = excluded.status,
                row_count = excluded.row_count,
                payload   = excluded.payload
            """,
            (
                dataset_id.label,
                descriptor.version.number,
                dataset_id.provider,
                dataset_id.kind.value,
                dataset_id.symbol,
                dataset_id.timeframe,
                descriptor.layer.value,
                descriptor.status.value,
                descriptor.row_count,
                payload["time_start"],
                payload["time_end"],
                json.dumps(payload, default=str),
                descriptor.created_at.isoformat(),
            ),
        )

    def get(self, dataset_id: DatasetId) -> Optional[DatasetDescriptor]:
        """Not rehydrated: the Parquet store owns dataset reconstruction.

        The rows here are the durable *catalogue*; use :meth:`stored_rows`
        to read them. Returning a half-built descriptor would be worse
        than returning nothing.
        """
        return None

    def list_all(self) -> List[DatasetDescriptor]:
        return []

    def next_version(self, dataset_id: DatasetId) -> int:
        row = self._database.query_one(
            "SELECT MAX(version) AS version FROM market_dataset WHERE dataset_key = ?",
            (dataset_id.label,),
        )
        if row is None or row["version"] is None:
            return 1
        return int(row["version"]) + 1

    # -- durable reads -------------------------------------------------------
    def stored_rows(self) -> List[Dict[str, Any]]:
        rows = self._database.query(
            "SELECT * FROM market_dataset ORDER BY symbol, timeframe, version"
        )
        return [dict(row) for row in rows]

    def symbols(self) -> List[str]:
        rows = self._database.query("SELECT DISTINCT symbol FROM market_dataset ORDER BY symbol")
        return [row["symbol"] for row in rows]


class SqliteFeatureRegistry(FeatureRegistry):
    """Feature catalogue backed by SQLite."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._cache: Dict[str, FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> None:
        # ``feature_id`` is a value object; the string form is the key.
        key = definition.feature_id.value
        self._cache[key] = definition
        payload = {"feature_id": key, "name": definition.name}
        self._database.execute(
            """
            INSERT INTO feature_definition (feature_id, name, payload, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(feature_id) DO UPDATE SET
                name    = excluded.name,
                payload = excluded.payload
            """,
            (key, definition.name, json.dumps(payload, default=str), _now()),
        )

    def get(self, feature_id: str) -> Optional[FeatureDefinition]:
        return self._cache.get(feature_id)

    def list_all(self) -> List[FeatureDefinition]:
        return list(self._cache.values())

    def stored_ids(self) -> List[str]:
        """Feature ids recorded in the database, across all runs."""
        rows = self._database.query("SELECT feature_id FROM feature_definition ORDER BY feature_id")
        return [row["feature_id"] for row in rows]


# ---------------------------------------------------------------- helpers ---
def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _row_to_model(row: Any) -> ModelDefinition:
    payload = json.loads(row["payload"])
    return ModelDefinition(
        model_id=ModelId(row["model_id"]),
        version=ModelVersion(int(row["version"])),
        name=payload["name"],
        model_type=ModelType(payload["model_type"]),
        family=ModelFamily(payload["family"]),
        feature_set_name=payload["feature_set_name"],
        feature_set_version=int(payload["feature_set_version"]),
        target_name=payload["target_name"],
        hyperparameters=payload.get("hyperparameters", {}),
        input_schema=payload.get("input_schema", {}),
        output_schema=payload.get("output_schema", {}),
        description=payload.get("description", ""),
    )


def _row_to_run(row: Any) -> TrainingRun:
    payload = json.loads(row["payload"])
    return TrainingRun(
        run_id=row["run_id"],
        model_id=ModelId(row["model_id"]),
        model_version=ModelVersion(int(row["model_version"])),
        dataset_version=int(payload.get("dataset_version", 1)),
        feature_set_name=payload.get("feature_set_name", ""),
        feature_set_version=int(payload.get("feature_set_version", 1)),
        seed=int(row["seed"]),
        hyperparameters=payload.get("hyperparameters", {}),
        started_at=datetime.fromisoformat(row["started_at"]),
    )
