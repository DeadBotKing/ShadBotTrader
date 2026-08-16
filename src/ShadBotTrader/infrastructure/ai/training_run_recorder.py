"""In-memory training-run ledger."""

from __future__ import annotations

from typing import Dict, List, Optional

from ShadBotTrader.domain.ai.model_identity import ModelId
from ShadBotTrader.domain.ai.ports import TrainingRunRepository
from ShadBotTrader.domain.ai.training_run import TrainingRun


class InMemoryTrainingRunRepository(TrainingRunRepository):
    """Keeps training runs in memory, keyed by run id."""

    def __init__(self) -> None:
        self._runs: Dict[str, TrainingRun] = {}

    def record(self, run: TrainingRun) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> Optional[TrainingRun]:
        return self._runs.get(run_id)

    def list_for_model(self, model_id: ModelId) -> List[TrainingRun]:
        return sorted(
            (run for run in self._runs.values() if run.model_id == model_id),
            key=lambda run: run.started_at,
        )
