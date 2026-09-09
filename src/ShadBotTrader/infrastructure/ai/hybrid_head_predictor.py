"""Inference adapter for the Phase 124 hybrid XGBoost/LightGBM head."""

from __future__ import annotations

import pickle
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Mapping, cast

import numpy as np

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.prediction_target import HybridHeadForecast
from ShadBotTrader.domain.common.errors import ValidationError


@dataclass(frozen=True)
class HybridHeadPayload:
    """The model object and ordered feature contract stored in the artifact."""

    model: Any
    feature_names: list[str]
    classes: list[int]


class HybridHeadPredictor:
    """Scores one or more Phase 123 matrix rows with the saved hybrid head."""

    def __init__(self, horizon: int = 288, timeframe: str = "5M") -> None:
        self._horizon = horizon
        self._timeframe = timeframe
        self._payload: HybridHeadPayload | None = None
        self._model_key: tuple[str, int, str] | None = None

    def load_payload(self, artifact: ModelArtifact) -> HybridHeadPayload:
        """Load and cache the pickled booster payload."""
        key = (artifact.model_id.value, artifact.version.number, artifact.checksum)
        if self._payload is not None and self._model_key == key:
            return self._payload
        try:
            raw = pickle.loads(artifact.payload)
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "Could not load the hybrid head because an optional booster package is missing. "
                "Install: pip install -r requirements-boosters.txt"
            ) from exc
        except Exception as exc:
            raise ValidationError(
                f"Could not load hybrid head artifact: {type(exc).__name__}: {exc}"
            ) from exc

        model = raw.get("model") if isinstance(raw, Mapping) else None
        feature_names = raw.get("feature_names") if isinstance(raw, Mapping) else None
        has_feature_contract = isinstance(feature_names, Sequence) and not isinstance(
            feature_names, str
        )
        if model is None or not has_feature_contract:
            raise ValidationError("Hybrid head artifact must contain a model and feature_names")
        feature_sequence = cast(Sequence[Any], feature_names)
        classes = raw.get("classes") if isinstance(raw, Mapping) else None
        if classes is None:
            classes = getattr(model, "classes_", [0, 1, 2])
        class_sequence = cast(Sequence[Any], classes)
        payload = HybridHeadPayload(
            model=model,
            feature_names=[str(name) for name in feature_sequence],
            classes=[int(value) for value in class_sequence],
        )
        self._payload = payload
        self._model_key = key
        return payload

    def probabilities(
        self,
        artifact: ModelArtifact,
        rows: Sequence[Mapping[str, Any]],
    ) -> np.ndarray:
        """Return an ``N x 3`` array ordered ``sell, hold, buy``."""
        payload = self.load_payload(artifact)
        matrix = np.asarray(
            [[self._numeric(row.get(name, 0.0)) for name in payload.feature_names] for row in rows],
            dtype=np.float32,
        )
        if matrix.ndim != 2:
            raise ValidationError("Hybrid head input must be a two-dimensional matrix")
        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        raw = np.asarray(payload.model.predict_proba(matrix), dtype=np.float64)
        if raw.ndim != 2:
            raise ValidationError(f"Hybrid head predict_proba returned shape {raw.shape}")
        return self.align_probabilities(raw, payload.classes)

    def forecast(
        self,
        artifact: ModelArtifact,
        row: Mapping[str, Any],
        generated_at: str = "",
    ) -> HybridHeadForecast:
        """Score one matrix row and return a domain forecast."""
        values = self.probabilities(artifact, [row])[0]
        return HybridHeadForecast.from_vector(
            values,
            horizon=self._horizon,
            timeframe=self._timeframe,
            generated_at=generated_at,
            model_id=artifact.model_id.value,
            model_version=artifact.version.number,
        )

    @staticmethod
    def align_probabilities(raw: np.ndarray, classes: Sequence[int]) -> np.ndarray:
        """Align arbitrary booster class order to ``sell, hold, buy``."""
        if raw.ndim != 2:
            raise ValidationError(f"Expected 2D probability matrix, got shape {raw.shape}")
        aligned = np.zeros((len(raw), 3), dtype=np.float64)
        for raw_col, cls in enumerate(classes):
            if raw_col >= raw.shape[1]:
                break
            if 0 <= int(cls) < 3:
                aligned[:, int(cls)] = raw[:, raw_col]
        row_sums = aligned.sum(axis=1)
        missing = row_sums <= 0
        if np.any(missing):
            aligned[missing, :] = 1.0 / 3.0
            row_sums = aligned.sum(axis=1)
        return aligned / row_sums[:, None]

    @staticmethod
    def _numeric(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return number if np.isfinite(number) else 0.0
