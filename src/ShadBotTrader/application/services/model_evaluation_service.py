"""Score a saved model against a stored dataset (Phase 48).

Training reports how a model did on the data it was fitted to. That is
not the same question as "how does this model do on THIS dataset", and
the operator asked for the second one: pick a saved model, pick a
dataset, run it, and keep the numbers.

Two properties make the answer trustworthy rather than merely printed:

**The evaluation never trains.** Weights are loaded and frozen. A score
produced by a model that quietly kept learning on the test data is not
an evaluation, it is a second training run wearing a disguise.

**The matrix is rebuilt exactly as training built it.** Same window
size, same stride-1 walk, same column order. If the evaluation assembled
its input differently the number would describe a model nobody has.

Results are appended to ``run_logs/evaluations.jsonl`` — one line per
run, never overwritten — so two models on the same dataset, or one model
across three datasets, can be compared afterwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Default first-passage price move for signal labels when an old record
#: has no recorded threshold.
DEFAULT_THRESHOLD = 0.0008

#: The platform default label horizon, used under the same condition.
DEFAULT_HORIZON = 5

#: One line per evaluation, appended forever. A comparison is worthless
#: if yesterday's number was overwritten by today's.
EVALUATION_LOG = "evaluations.jsonl"


@dataclass
class EvaluationResult:
    """What one model scored on one dataset."""

    model_id: str
    role: str
    symbol: str
    timeframe: str
    version: int = 1
    rows: int = 0
    windows: int = 0
    window_size: int = 0
    feature_columns: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    baseline: Optional[float] = None
    #: Legacy field retained for the serialized result. Binary labels
    #: use the sign of the forward return and have no neutral band.
    threshold: float = 0.0
    horizon: int = 0
    threshold_assumed: bool = False
    trained_on: str = ""
    evaluated_at: str = ""
    note: str = ""
    failed: bool = False
    reason: str = ""

    @property
    def headline(self) -> str:
        """The single number that matters for this kind of model."""
        if self.role == "signal":
            accuracy = self.metrics.get("accuracy")
            if accuracy is None:
                return "n/a"
            text = f"accuracy {accuracy:.2%}"
            if self.baseline is not None:
                verdict = "BETTER" if accuracy > self.baseline else "NO BETTER"
                text += f" vs baseline {self.baseline:.2%} — {verdict}"
            return text
        mae = self.metrics.get("mae")
        return "n/a" if mae is None else f"mae {mae:.6f}"

    @property
    def is_same_dataset_it_trained_on(self) -> bool:
        """True when this is a re-score of the training data.

        Not an error — but the number means much less, so it is stated.
        """
        return bool(self.trained_on) and self.trained_on == self.timeframe

    def summary_lines(self) -> List[str]:
        if self.failed:
            return [f"FAILED: {self.reason}"]

        lines = [
            f"model    : {self.model_id} v{self.version} ({self.role})",
            f"dataset  : {self.symbol} {self.timeframe}",
            f"windows  : {self.windows:,} of {self.window_size} x {self.feature_columns}",
            *(
                [
                    f"labels   : binary SELL/BUY, first-passage threshold "
                    f"{self.threshold:.4%}, horizon unbounded"
                ]
                if self.role == "signal"
                else []
            ),
            "",
            f"result   : {self.headline}",
        ]
        for name in sorted(self.metrics):
            lines.append(f"    {name:<12}: {self.metrics[name]:.6f}")

        if self.is_same_dataset_it_trained_on:
            lines.append("")
            lines.append(
                "NOTE: this model was TRAINED on this timeframe. The score "
                "flatters it — a model always does better on data it has "
                "already seen. Evaluate on a different dataset for a real test."
            )
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "role": self.role,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "version": self.version,
            "rows": self.rows,
            "windows": self.windows,
            "window_size": self.window_size,
            "feature_columns": self.feature_columns,
            "metrics": dict(self.metrics),
            "baseline": self.baseline,
            "threshold": self.threshold,
            "horizon": self.horizon,
            "threshold_assumed": self.threshold_assumed,
            "trained_on": self.trained_on,
            "evaluated_at": self.evaluated_at,
            "note": self.note,
            "failed": self.failed,
            "reason": self.reason,
        }


class ModelEvaluationService:
    """Loads a saved model and scores it on a stored dataset."""

    def __init__(self, storage_root: str | Path, log_dir: str | Path = "run_logs") -> None:
        self._root = Path(storage_root)
        self._log_dir = Path(log_dir)

    @property
    def log_path(self) -> Path:
        return self._log_dir / EVALUATION_LOG

    # ------------------------------------------------------------ run --
    def evaluate(
        self,
        model_id: str,
        symbol: str,
        timeframe: str,
        window_size: int = 0,
        max_windows: int = 5000,
    ) -> EvaluationResult:
        """Score ``model_id`` on the stored ``symbol``/``timeframe`` data.

        ``max_windows`` caps the work: a full 49,000-window pass is
        minutes of compute for a number that stabilises long before
        then. The cap is recorded in the result so nobody mistakes a
        sample for the whole dataset.
        """
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        catalogue = ModelCatalogue(self._root)
        version = catalogue.latest_version(model_id)
        record = catalogue.read(model_id, version) if version else None

        result = EvaluationResult(
            model_id=model_id,
            role=(record.role if record else ""),
            symbol=symbol,
            timeframe=timeframe,
            version=version or 0,
            trained_on=(record.timeframe if record else ""),
            evaluated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        if record is None:
            result.failed = True
            result.reason = (
                f"No saved model called {model_id!r}. Train one first, or pick "
                f"a different model."
            )
            return result

        window_size = window_size or record.window_size or 64
        result.window_size = window_size
        result.role = record.role

        try:
            matrix = self._load_matrix(symbol, timeframe)
        except Exception as error:
            result.failed = True
            result.reason = f"{type(error).__name__}: {error}"
            return result

        if matrix is None:
            result.failed = True
            result.reason = (
                f"No training matrix for {symbol} {timeframe}. Run "
                f"'Build training dataset' for that timeframe first."
            )
            return result

        result.rows = len(matrix.rows)
        result.feature_columns = matrix.width

        try:
            self._score(result, matrix, record, max_windows)
        except Exception as error:
            result.failed = True
            result.reason = f"{type(error).__name__}: {error}"

        return result

    # -------------------------------------------------------- internals --
    def _load_matrix(self, symbol: str, timeframe: str) -> Any:
        from ShadBotTrader.application.services.training_data_service import (
            TrainingDataService,
        )

        return TrainingDataService(self._root).load_matrix(symbol, timeframe)

    def _score(
        self,
        result: EvaluationResult,
        matrix: Any,
        record: Any,
        max_windows: int,
    ) -> None:
        """Run the frozen model over the dataset and collect metrics."""
        import numpy as np

        from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
        from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
            FilesystemArtifactStore,
        )
        from ShadBotTrader.infrastructure.ai.model_roles import (
            range_model_role,
            signal_model_role,
        )
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            _deserialize_model,
        )

        artifact = FilesystemArtifactStore(self._root).load(
            ModelId(result.model_id), ModelVersion(result.version)
        )
        if artifact is None:
            raise FileNotFoundError(
                f"{result.model_id} v{result.version} is listed but its weights "
                f"are missing from datasets/models/"
            )

        model = _deserialize_model(artifact.payload)

        # Rebuild the same first-passage question the model was taught.
        recorded_threshold = float(getattr(record, "threshold", 0.0) or 0.0)
        threshold = recorded_threshold if recorded_threshold > 0 else DEFAULT_THRESHOLD
        recorded_horizon = int(getattr(record, "horizon", 0) or 0)
        result.threshold_assumed = result.role == "signal" and recorded_threshold <= 0

        if result.role == "signal":
            role = signal_model_role(
                timeframe=result.timeframe,
                window_size=result.window_size,
                threshold=threshold,
                horizon=0,
            )
            result.threshold = float(role.target.threshold)
        else:
            role = range_model_role(
                timeframe=result.timeframe,
                window_size=result.window_size,
                horizon=(recorded_horizon if recorded_horizon > 0 else DEFAULT_HORIZON),
            )
        horizon = role.horizon
        result.horizon = horizon
        rows = matrix.rows
        usable = len(rows) - result.window_size - horizon + 1
        if usable < 1:
            raise ValueError(
                f"{len(rows):,} rows cannot make a single "
                f"{result.window_size}-row window with horizon {horizon}"
            )

        step = max(1, usable // max_windows) if max_windows else 1
        starts = list(range(0, usable, step))[:max_windows] if max_windows else list(range(usable))
        result.windows = len(starts)
        if step > 1:
            result.note = f"sampled every {step} windows of {usable:,}"

        from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

        windows = np.array(
            [minmax_scale_window(rows[start : start + result.window_size]) for start in starts],
            dtype=np.float32,
        )

        predictions = model.predict(windows, verbose=0)

        if result.role == "signal":
            self._score_signal(
                result,
                predictions,
                starts,
                matrix,
                horizon,
                threshold=float(role.target.threshold),
            )
        else:
            self._score_range(result, predictions, starts, matrix, horizon)

    def _score_signal(
        self,
        result: EvaluationResult,
        predictions: Any,
        starts: Any,
        matrix: Any,
        horizon: int,
        threshold: float,
    ) -> None:
        """Accuracy against binary labels rebuilt from the matrix itself.

        ``threshold`` is the recorded first-passage price-move threshold;
        positive barrier hits are BUY and negative barrier hits are SELL.
        Starts that reach neither barrier are excluded from the score.
        """
        import numpy as np

        from ShadBotTrader.infrastructure.ai.target_builder import (
            build_signal_labels_from_closes,
        )

        columns = matrix.column_names
        if "return_1" not in columns:
            raise ValueError("the matrix has no return_1 column to rebuild signal labels")

        return_index = columns.index("return_1")
        closes = [1.0]
        for row in matrix.rows[1:]:
            closes.append(closes[-1] * (1.0 + float(row[return_index])))
        labels = build_signal_labels_from_closes(closes, threshold=threshold)
        by_start = dict(zip(labels.source_index, labels.labels, strict=True))

        predicted_all = np.argmax(np.asarray(predictions), axis=1).tolist()
        truth: List[int] = []
        predicted: List[int] = []
        for start, value in zip(starts, predicted_all, strict=False):
            target_start = start + result.window_size - 1
            if target_start not in by_start:
                continue
            truth.append(by_start[target_start])
            predicted.append(int(value))

        if not truth:
            raise ValueError("No signal windows reached either threshold before the data ended")

        result.windows = len(truth)
        correct = sum(1 for actual, guess in zip(truth, predicted, strict=True) if actual == guess)
        total = len(truth)
        result.metrics["accuracy"] = correct / total
        counts = {label: truth.count(label) for label in (0, 1)}
        result.baseline = max(counts.values()) / total
        result.metrics["sell_share"] = counts[0] / total
        result.metrics["buy_share"] = counts[1] / total

    def _score_range(
        self, result: EvaluationResult, predictions: Any, starts: Any, matrix: Any, horizon: int
    ) -> None:
        """Mean absolute error of the predicted high/low offsets."""
        import numpy as np

        columns = matrix.column_names
        needed = ("high_rel", "low_rel")
        if not all(name in columns for name in needed):
            raise ValueError("the matrix has no high_rel/low_rel columns to score against")

        high_index = columns.index("high_rel")
        low_index = columns.index("low_rel")

        truth = []
        for start in starts:
            here = start + result.window_size - 1
            window = matrix.rows[here + 1 : here + 1 + horizon]
            if not window:
                truth.append([0.0, 0.0])
                continue
            truth.append(
                [
                    max(float(row[high_index]) for row in window),
                    min(float(row[low_index]) for row in window),
                ]
            )

        expected = np.asarray(truth, dtype=np.float64)
        actual = np.asarray(predictions, dtype=np.float64)[:, : expected.shape[1]]

        result.metrics["mae"] = float(np.mean(np.abs(actual - expected)))
        result.metrics["mse"] = float(np.mean((actual - expected) ** 2))
        result.metrics["high_mae"] = float(np.mean(np.abs(actual[:, 0] - expected[:, 0])))
        result.metrics["low_mae"] = float(np.mean(np.abs(actual[:, 1] - expected[:, 1])))

    # ------------------------------------------------------------- log --
    def append_to_log(self, result: EvaluationResult) -> Path:
        """Append one evaluation, keeping every earlier one."""
        path = self.log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        return path

    def history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Past evaluations, newest last."""
        path = self.log_path
        if not path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a torn line must not hide the rest
        return entries[-limit:]
