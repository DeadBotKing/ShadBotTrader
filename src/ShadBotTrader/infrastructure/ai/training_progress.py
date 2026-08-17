"""Training progress reporting for roll-forward model training.

The AI Platform trains one model per roll-forward fold, so a run can
involve dozens of independent fits. Without feedback the process looks
frozen. This module defines a small, framework-independent reporting
contract plus a console implementation that prints:

    * the training plan (folds, epochs, learning rate, sample counts)
    * per-epoch loss / accuracy for the current fold
    * a live progress bar with elapsed and estimated remaining time
    * a per-fold and end-of-run summary

The contract lives in the infrastructure layer next to the trainers that
use it: it describes *how* training is observed, not *what* a model is.
Domain and application code never import it.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, TextIO


@dataclass(frozen=True)
class TrainingPlanInfo:
    """Static description of a roll-forward training run."""

    model_id: str
    model_version: int
    total_folds: int
    epochs_per_fold: int
    learning_rate: float
    batch_size: int
    window_size: int
    n_features: int
    total_samples: int
    seed: int
    framework: str = ""
    framework_version: str = ""

    @property
    def total_epochs(self) -> int:
        """Total number of epochs across every fold."""
        return self.total_folds * self.epochs_per_fold


@dataclass(frozen=True)
class FoldInfo:
    """Description of a single roll-forward fold."""

    fold_index: int
    total_folds: int
    train_samples: int
    val_samples: int
    train_start: int
    train_end: int
    val_start: int
    val_end: int

    @property
    def human_index(self) -> int:
        """1-based fold number for display."""
        return self.fold_index + 1


@dataclass(frozen=True)
class EpochMetrics:
    """Metrics captured at the end of one epoch."""

    epoch: int
    total_epochs: int
    loss: Optional[float] = None
    val_loss: Optional[float] = None
    accuracy: Optional[float] = None
    val_accuracy: Optional[float] = None
    learning_rate: Optional[float] = None
    extra: Dict[str, float] = field(default_factory=dict)

    @property
    def human_epoch(self) -> int:
        """1-based epoch number for display."""
        return self.epoch + 1


class TrainingProgressReporter(Protocol):
    """Observer contract for a roll-forward training run.

    Implementations must be side-effect free with respect to training:
    a reporter may never influence weights, ordering or determinism.
    """

    def on_prepare_begin(self, rows: int, window_size: int) -> None:
        """Called before the (slow) window-building step."""

    def on_prepare_end(self, samples: int) -> None:
        """Called when the windows are ready."""

    def on_batch_end(self, fold: "FoldInfo", batch: int, total_batches: int, logs: dict) -> None:
        """Called periodically inside an epoch."""

    def on_train_begin(self, plan: TrainingPlanInfo) -> None:
        """Called once before the first fold."""

    def on_fold_begin(self, fold: FoldInfo) -> None:
        """Called before each fold starts fitting."""

    def on_epoch_end(self, fold: FoldInfo, metrics: EpochMetrics) -> None:
        """Called after every epoch of the current fold."""

    def on_fold_end(self, fold: FoldInfo, val_loss: float) -> None:
        """Called when a fold finishes."""

    def on_train_end(self, fold_losses: List[float]) -> None:
        """Called once after the last fold."""


class NullProgressReporter:
    """Reporter that does nothing (the default; keeps trainers silent)."""

    def on_prepare_begin(self, rows: int, window_size: int) -> None:
        return None

    def on_prepare_end(self, samples: int) -> None:
        return None

    def on_batch_end(self, fold: "FoldInfo", batch: int, total_batches: int, logs: dict) -> None:
        return None

    def on_train_begin(self, plan: TrainingPlanInfo) -> None:
        return None

    def on_fold_begin(self, fold: FoldInfo) -> None:
        return None

    def on_epoch_end(self, fold: FoldInfo, metrics: EpochMetrics) -> None:
        return None

    def on_fold_end(self, fold: FoldInfo, val_loss: float) -> None:
        return None

    def on_train_end(self, fold_losses: List[float]) -> None:
        return None


def format_duration(seconds: float) -> str:
    """Format a duration as ``H:MM:SS`` / ``M:SS`` / ``Ns``."""
    if seconds < 0 or seconds != seconds:  # negative or NaN
        return "--"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    if minutes:
        return f"{minutes}:{secs:02d}"
    return f"{secs}s"


def _bar(fraction: float, width: int = 28) -> str:
    """Render a text progress bar for ``fraction`` in ``[0, 1]``."""
    fraction = min(max(fraction, 0.0), 1.0)
    filled = int(round(fraction * width))
    return "#" * filled + "-" * (width - filled)


def _fmt(value: Optional[float], digits: int = 4) -> str:
    """Format an optional metric value."""
    if value is None or value != value:  # None or NaN
        return "  --  "
    return f"{value:.{digits}f}"


class ConsoleProgressReporter:
    """Prints a live, human-readable view of a roll-forward training run.

    Output per epoch::

        fold  3/93 | epoch 2/2 | loss 0.6931 val_loss 0.6926 \
acc 0.5312 val_acc 0.5000 | lr 1.5e-04
        [########--------------------]  12.4% | fold 3/93 | \
elapsed 0:14 | eta 1:42

    The ETA is derived from completed folds, so it stabilises after the
    first few folds.
    """

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        show_epochs: bool = True,
        bar_width: int = 28,
    ) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._show_epochs = show_epochs
        self._bar_width = bar_width
        self._plan: Optional[TrainingPlanInfo] = None
        self._run_start: float = 0.0
        self._fold_start: float = 0.0
        self._completed_folds: int = 0

    # -- helpers ----------------------------------------------------------
    def _write(self, text: str) -> None:
        self._stream.write(text + "\n")
        self._stream.flush()

    # -- reporter contract ------------------------------------------------
    def on_prepare_begin(self, rows: int, window_size: int) -> None:
        self._prepare_started = time.monotonic()
        self._write("")
        self._write(
            f"  preparing {rows:,} rows into windows of {window_size} " f"(this takes a moment) ..."
        )

    def on_prepare_end(self, samples: int) -> None:
        elapsed = time.monotonic() - getattr(self, "_prepare_started", time.monotonic())
        self._write(f"  {samples:,} training windows ready in {format_duration(elapsed)}")

    def on_batch_end(self, fold: "FoldInfo", batch: int, total_batches: int, logs: dict) -> None:
        """One in-place line so a long epoch visibly advances."""
        fraction = (batch + 1) / total_batches if total_batches else 1.0
        parts = [f"    batch {batch + 1:>6,}/{total_batches:,}"]
        for key in ("loss", "accuracy", "mae"):
            if key in logs:
                parts.append(f"{key} {float(logs[key]):.4f}")
        self._stream.write(
            f"\r    [{_bar(fraction, 20)}] {fraction * 100:5.1f}% | "
            + " | ".join(parts[1:] or ["running"])
            + f" | {parts[0].strip()}   "
        )
        self._stream.flush()

    def on_train_begin(self, plan: TrainingPlanInfo) -> None:
        self._plan = plan
        self._run_start = time.monotonic()
        self._completed_folds = 0

        framework = plan.framework
        if plan.framework_version:
            framework = f"{framework} {plan.framework_version}"

        self._write("")
        self._write("=" * 74)
        self._write(f"  TRAINING  {plan.model_id} v{plan.model_version}")
        self._write("=" * 74)
        self._write(f"  framework      : {framework or 'n/a'}")
        self._write(f"  learning rate  : {plan.learning_rate:g}")
        self._write(f"  epochs / fold  : {plan.epochs_per_fold}")
        self._write(f"  folds          : {plan.total_folds}  (roll-forward)")
        self._write(f"  total epochs   : {plan.total_epochs}")
        self._write(f"  batch size     : {plan.batch_size}")
        self._write(f"  window x feats : {plan.window_size} x {plan.n_features}")
        self._write(f"  samples        : {plan.total_samples}")
        self._write(f"  seed           : {plan.seed}")
        self._write("-" * 74)

    def on_fold_begin(self, fold: FoldInfo) -> None:
        self._fold_start = time.monotonic()
        if self._show_epochs:
            self._write(
                f"fold {fold.human_index:>3}/{fold.total_folds} | "
                f"train[{fold.train_start}:{fold.train_end}] "
                f"({fold.train_samples} samples) -> "
                f"val[{fold.val_start}:{fold.val_end}] ({fold.val_samples} samples)"
            )

    def on_epoch_end(self, fold: FoldInfo, metrics: EpochMetrics) -> None:
        if not self._show_epochs:
            return
        # Close the in-place batch line before writing a permanent one.
        self._stream.write("\r" + " " * 100 + "\r")
        parts = [
            f"  epoch {metrics.human_epoch}/{metrics.total_epochs}",
            f"loss {_fmt(metrics.loss)}",
            f"val_loss {_fmt(metrics.val_loss)}",
        ]
        if metrics.accuracy is not None:
            parts.append(f"acc {_fmt(metrics.accuracy)}")
        if metrics.val_accuracy is not None:
            parts.append(f"val_acc {_fmt(metrics.val_accuracy)}")
        if metrics.learning_rate is not None:
            parts.append(f"lr {metrics.learning_rate:.2e}")
        self._write(" | ".join(parts))

    def on_fold_end(self, fold: FoldInfo, val_loss: float) -> None:
        self._completed_folds += 1
        now = time.monotonic()
        elapsed = now - self._run_start
        fold_seconds = now - self._fold_start

        total = fold.total_folds
        fraction = self._completed_folds / total if total else 1.0
        per_fold = elapsed / self._completed_folds if self._completed_folds else 0.0
        eta = per_fold * (total - self._completed_folds)

        self._write(
            f"[{_bar(fraction, self._bar_width)}] {fraction * 100:5.1f}% | "
            f"fold {self._completed_folds}/{total} | "
            f"val_loss {_fmt(val_loss)} | "
            f"{fold_seconds:.1f}s/fold | "
            f"elapsed {format_duration(elapsed)} | "
            f"eta {format_duration(eta)}"
        )

    def on_train_end(self, fold_losses: List[float]) -> None:
        elapsed = time.monotonic() - self._run_start
        self._write("-" * 74)
        if fold_losses:
            best = min(fold_losses)
            worst = max(fold_losses)
            mean = sum(fold_losses) / len(fold_losses)
            self._write(
                f"  folds {len(fold_losses)} | "
                f"val_loss best {best:.4f} / mean {mean:.4f} / worst {worst:.4f}"
            )
            self._write(f"  final fold val_loss: {fold_losses[-1]:.4f}")
        self._write(f"  total training time: {format_duration(elapsed)}")
        self._write("=" * 74)
        self._write("")


def keras_progress_callback(
    reporter: TrainingProgressReporter,
    fold: FoldInfo,
    total_epochs: int,
) -> Any:
    """Build a Keras callback that forwards epoch metrics to ``reporter``.

    Imported lazily so this module stays usable without TensorFlow.
    """
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

    tf = _require_tensorflow()

    class _ProgressCallback(tf.keras.callbacks.Callback):  # type: ignore[misc,name-defined]
        def on_epoch_end(self, epoch: int, logs: Optional[Dict[str, Any]] = None) -> None:
            logs = logs or {}
            learning_rate: Optional[float] = None
            optimizer = getattr(self.model, "optimizer", None)
            if optimizer is not None:
                try:
                    learning_rate = float(
                        tf.keras.backend.get_value(optimizer.learning_rate)  # type: ignore[union-attr]
                    )
                except Exception:  # pragma: no cover - optimizer without plain lr
                    learning_rate = None

            known = {"loss", "val_loss", "accuracy", "val_accuracy"}
            reporter.on_epoch_end(
                fold,
                EpochMetrics(
                    epoch=epoch,
                    total_epochs=total_epochs,
                    loss=_as_float(logs.get("loss")),
                    val_loss=_as_float(logs.get("val_loss")),
                    accuracy=_as_float(logs.get("accuracy")),
                    val_accuracy=_as_float(logs.get("val_accuracy")),
                    learning_rate=learning_rate,
                    extra={
                        key: float(value)
                        for key, value in logs.items()
                        if key not in known and _as_float(value) is not None
                    },
                ),
            )

    return _ProgressCallback()


def _as_float(value: Any) -> Optional[float]:
    """Best-effort conversion of a Keras log value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - non-numeric log
        return None


def keras_batch_callback(
    reporter: TrainingProgressReporter,
    fold: FoldInfo,
    total_batches: int,
    every: int = 0,
) -> Any:
    """A Keras callback that reports progress inside an epoch.

    An epoch over 50,000 samples is thousands of batches and can take
    minutes. Reporting only at epoch boundaries leaves the log frozen for
    all of it, which is indistinguishable from a hang.

    ``every`` defaults to roughly 1% of the epoch so the line moves
    without drowning the log in output.
    """
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

    tf = _require_tensorflow()
    stride = every or max(1, total_batches // 100)

    class _BatchCallback(tf.keras.callbacks.Callback):  # type: ignore[misc,name-defined]
        def on_train_batch_end(self, batch: int, logs: Optional[Dict[str, Any]] = None) -> None:
            if batch % stride and batch + 1 != total_batches:
                return
            reporter.on_batch_end(fold, batch, total_batches, dict(logs or {}))

    return _BatchCallback()
