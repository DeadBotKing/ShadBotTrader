"""Learning experiments and walk-forward windows (Phase 17).

An experiment is one controlled comparison: a baseline, a set of
candidates, and the windows they are all measured over. Splitting the
data into an in-sample window and several out-of-sample folds is what
makes the comparison honest.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.learning.candidate import Candidate
from ShadBotTrader.domain.learning.learning_types import ExperimentStatus


class DataWindow(ValueObject):
    """A half-open slice ``[start, end)`` of a candle series."""

    def __init__(self, label: str, start: int, end: int) -> None:
        if start < 0:
            raise ValidationError("window start must be >= 0")
        if end <= start:
            raise ValidationError(f"window '{label}' must be non-empty ({start}..{end})")
        self._label = label
        self._start = start
        self._end = end

    @property
    def label(self) -> str:
        return self._label

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def size(self) -> int:
        return self._end - self._start

    def slice(self, series: Sequence[Any]) -> List[Any]:
        """Extract this window from ``series``."""
        return list(series[self._start : self._end])

    def _value(self) -> tuple[Any, ...]:
        return (self._label, self._start, self._end)

    def __str__(self) -> str:
        return f"{self._label}[{self._start}:{self._end}]"


class WalkForwardPlan:
    """An in-sample window followed by non-overlapping validation folds.

    This is the anti-overfitting device: parameters are chosen on the
    in-sample window only, then judged on folds the search never saw.
    """

    def __init__(self, in_sample: DataWindow, folds: Sequence[DataWindow]) -> None:
        if not folds:
            raise ValidationError("A walk-forward plan needs at least one validation fold")
        for fold in folds:
            if fold.start < in_sample.end:
                raise ValidationError(
                    f"Validation fold {fold} overlaps the in-sample window "
                    f"{in_sample} — that would leak training data"
                )
        self._in_sample = in_sample
        self._folds = list(folds)

    @classmethod
    def split(
        cls,
        total: int,
        in_sample_ratio: float = 0.5,
        fold_count: int = 3,
    ) -> "WalkForwardPlan":
        """Split ``total`` bars into an in-sample head and equal folds."""
        if total < 2:
            raise ValidationError("Not enough data to split")
        if not 0 < in_sample_ratio < 1:
            raise ValidationError("in_sample_ratio must be in (0, 1)")
        if fold_count < 1:
            raise ValidationError("fold_count must be >= 1")

        boundary = int(total * in_sample_ratio)
        remaining = total - boundary
        if boundary < 1 or remaining < fold_count:
            raise ValidationError(
                f"Cannot split {total} bars into an in-sample window and " f"{fold_count} folds"
            )

        in_sample = DataWindow("in_sample", 0, boundary)
        size = remaining // fold_count
        folds: List[DataWindow] = []
        cursor = boundary
        for index in range(fold_count):
            # the last fold absorbs the remainder so no data is discarded
            end = total if index == fold_count - 1 else cursor + size
            folds.append(DataWindow(f"fold_{index + 1}", cursor, end))
            cursor = end

        return cls(in_sample, folds)

    @property
    def in_sample(self) -> DataWindow:
        return self._in_sample

    @property
    def folds(self) -> List[DataWindow]:
        return list(self._folds)

    @property
    def fold_count(self) -> int:
        return len(self._folds)

    def __str__(self) -> str:
        folds = ", ".join(str(fold) for fold in self._folds)
        return f"{self._in_sample} -> {folds}"


class LearningExperiment:
    """One controlled comparison of candidates against a baseline."""

    def __init__(
        self,
        experiment_id: str,
        objective_name: str,
        plan: WalkForwardPlan,
        hypothesis: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not experiment_id.strip():
            raise ValidationError("experiment_id must not be empty")
        self._experiment_id = experiment_id.strip()
        self._objective_name = objective_name
        self._plan = plan
        self._hypothesis = hypothesis
        self._metadata: Dict[str, Any] = dict(metadata or {})
        self._status = ExperimentStatus.CREATED
        self._candidates: List[Candidate] = []
        self._baseline: Optional[Candidate] = None
        self._failure_reason = ""

    @property
    def experiment_id(self) -> str:
        return self._experiment_id

    @property
    def objective_name(self) -> str:
        return self._objective_name

    @property
    def plan(self) -> WalkForwardPlan:
        return self._plan

    @property
    def hypothesis(self) -> str:
        return self._hypothesis

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def status(self) -> ExperimentStatus:
        return self._status

    @property
    def candidates(self) -> List[Candidate]:
        return list(self._candidates)

    @property
    def baseline(self) -> Optional[Candidate]:
        return self._baseline

    @property
    def failure_reason(self) -> str:
        return self._failure_reason

    def set_baseline(self, candidate: Candidate) -> None:
        self._baseline = candidate

    def add_candidate(self, candidate: Candidate) -> None:
        self._candidates.append(candidate)

    def start(self) -> None:
        if self._status is not ExperimentStatus.CREATED:
            raise ValidationError(f"Cannot start an experiment in state '{self._status.value}'")
        self._status = ExperimentStatus.RUNNING

    def complete(self) -> None:
        if self._status is not ExperimentStatus.RUNNING:
            raise ValidationError(f"Cannot complete an experiment in state '{self._status.value}'")
        self._status = ExperimentStatus.COMPLETED

    def fail(self, reason: str) -> None:
        self._status = ExperimentStatus.FAILED
        self._failure_reason = reason
