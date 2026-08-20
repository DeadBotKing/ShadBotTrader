"""What models exist on disk, and what each was trained on (Phase 40).

Two problems this closes.

**Training never saved anything.** ``run_dual_models.py`` fitted a
network, printed a prediction and exited. Nothing reached
``datasets/models/``, so "Retrain the model" had nothing to retrain and
yesterday's run could not be compared with today's. Every training run
since Phase 29 was discarded the moment the process ended.

**A model id did not say what it was trained on.** ``gold_range_1h``
implies 1H by convention only. The user asked for the opposite: the file
itself should record which kind of model it is and which dataset taught
it, so picking one from a list is an informed choice rather than a guess
from a filename.

Every saved model therefore carries a sidecar record:

    role       range | signal
    timeframe  the dataset it was trained on (5M / 1H / 1D)
    symbol     the instrument
    rows       how many dataset rows it saw
    metrics    the final fold's val_loss / val_mae / val_accuracy

The record is what fills the dropdowns. It is written next to the
artifact, so deleting a model directory removes its entry too and the
list can never advertise a model that is not there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Filename of the sidecar written beside every trained artifact.
RECORD_FILE = "training.json"


@dataclass
class ModelRecord:
    """One trained model, described by what produced it."""

    model_id: str
    role: str
    symbol: str
    timeframe: str
    version: int = 1
    rows: int = 0
    windows: int = 0
    window_size: int = 0
    feature_columns: int = 0
    epochs: int = 0
    folds: int = 0
    #: For signal models, the first-passage price-move threshold used to
    #: build BUY/SELL labels (0.0015 == 0.15%). For range models it is
    #: zero. This is separate from the probability threshold used by the
    #: backtest strategy.
    threshold: float = 0.0
    #: Learning rate used by the optimizer for this saved model.
    learning_rate: float = 0.0
    #: How many candles ahead the label looks. Recorded for the same
    #: reason: the evaluator must rebuild the exact question.
    horizon: int = 0
    trained_at: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    note: str = ""

    @property
    def threshold_percent(self) -> str:
        """The binary first-passage price threshold as a human percent."""
        if self.role != "signal" or self.threshold <= 0:
            return "n/a"
        return f"{self.threshold:.4%}"

    @property
    def label(self) -> str:
        """A human choice for a dropdown, e.g. ``gold_range_1d — range on 1D``."""
        return f"{self.model_id} — {self.role} trained on {self.timeframe}"

    @property
    def headline_metric(self) -> str:
        """The single number that matters for this kind of model."""
        if self.role == "signal":
            value = self.metrics.get("val_accuracy")
            return "n/a" if value is None else f"val_accuracy {value:.1%}"
        value = self.metrics.get("val_mae")
        return "n/a" if value is None else f"val_mae {value:.6f}"

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
            "epochs": self.epochs,
            "folds": self.folds,
            "threshold": self.threshold,
            "learning_rate": self.learning_rate,
            "horizon": self.horizon,
            "trained_at": self.trained_at,
            "metrics": dict(self.metrics),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ModelRecord":
        return cls(
            model_id=str(payload.get("model_id", "")),
            role=str(payload.get("role", "")),
            symbol=str(payload.get("symbol", "")),
            timeframe=str(payload.get("timeframe", "")),
            version=int(payload.get("version", 1)),
            rows=int(payload.get("rows", 0)),
            windows=int(payload.get("windows", 0)),
            window_size=int(payload.get("window_size", 0)),
            feature_columns=int(payload.get("feature_columns", 0)),
            epochs=int(payload.get("epochs", 0)),
            folds=int(payload.get("folds", 0)),
            threshold=float(payload.get("threshold", 0.0) or 0.0),
            learning_rate=float(payload.get("learning_rate", 0.0) or 0.0),
            horizon=int(payload.get("horizon", 0) or 0),
            trained_at=str(payload.get("trained_at", "")),
            metrics={
                str(key): float(value) for key, value in (payload.get("metrics") or {}).items()
            },
            note=str(payload.get("note", "")),
        )

    def summary_lines(self) -> List[str]:
        return [
            f"model     : {self.model_id} v{self.version}",
            f"role      : {self.role}",
            f"dataset   : {self.symbol} {self.timeframe}",
            f"trained   : {self.rows:,} rows, {self.windows:,} windows, "
            f"{self.epochs} epoch(s) x {self.folds} fold(s)",
            f"quality   : {self.headline_metric}",
            *([f"learning : {self.learning_rate:.2e}"] if self.learning_rate > 0 else []),
            *(
                [
                    f"labels    : binary SELL/BUY, first-passage threshold "
                    f"{self.threshold_percent}, horizon unbounded"
                ]
                if self.role == "signal"
                else []
            ),
            f"at        : {self.trained_at}",
        ]


class ModelCatalogue:
    """Reads and writes the training record beside each artifact."""

    def __init__(self, storage_root: str | Path) -> None:
        self._root = Path(storage_root) / "models"

    @property
    def root(self) -> Path:
        return self._root

    def record_path(self, model_id: str, version: int = 1) -> Path:
        return self._root / model_id / f"v{version}_{RECORD_FILE}"

    def write(self, record: ModelRecord) -> Path:
        path = self.record_path(record.model_id, record.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not record.trained_at:
            record.trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path.write_text(
            json.dumps(record.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    def read(self, model_id: str, version: int = 1) -> Optional[ModelRecord]:
        path = self.record_path(model_id, version)
        if not path.exists():
            return None
        try:
            return ModelRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            # An unreadable record must not hide the model or crash the
            # dashboard; it is simply not offered as a choice.
            return None

    def latest_version(self, model_id: str) -> int:
        """The highest version stored for a model, or 0 when absent."""
        directory = self._root / model_id
        if not directory.is_dir():
            return 0
        versions = []
        for path in directory.glob(f"v*_{RECORD_FILE}"):
            stem = path.name.split("_", 1)[0]
            if stem.startswith("v") and stem[1:].isdigit():
                versions.append(int(stem[1:]))
        return max(versions, default=0)

    def next_version(self, model_id: str) -> int:
        return self.latest_version(model_id) + 1

    def list_all(self) -> List[ModelRecord]:
        """Every trained model, newest first.

        Only the latest version of each model is listed: the dropdown
        answers "which model do I retrain", and older versions are
        history rather than choices.
        """
        if not self._root.is_dir():
            return []

        records: List[ModelRecord] = []
        for directory in sorted(self._root.iterdir()):
            if not directory.is_dir():
                continue
            version = self.latest_version(directory.name)
            if not version:
                continue
            record = self.read(directory.name, version)
            if record is not None:
                records.append(record)

        return sorted(records, key=lambda item: item.trained_at, reverse=True)

    def choices(self) -> List[str]:
        """Model ids for a dropdown, newest first."""
        return [record.model_id for record in self.list_all()]
