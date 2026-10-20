"""Durable learning memory and experiment store (Phase 17 + 20).

Remembering failures across runs is the point: without it, every search
re-explores the same dead ends. Candidates are keyed by configuration
signature, so a configuration tried last week is recognised today.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.learning.candidate import Candidate, EvaluationRecord
from ShadBotTrader.domain.learning.experiment import LearningExperiment
from ShadBotTrader.domain.learning.learning_types import CandidateStatus, RejectionReason
from ShadBotTrader.domain.learning.parameter_space import CandidateConfiguration
from ShadBotTrader.domain.learning.ports import ExperimentRepository, LearningMemory
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics
from ShadBotTrader.infrastructure.persistence.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteLearningMemory(LearningMemory):
    """Learning memory that survives restarts."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def remember(self, candidate: Candidate) -> None:
        """Store (or update) a candidate keyed by its configuration."""
        payload = {
            "candidate_id": candidate.candidate_id,
            "configuration": _jsonable(candidate.configuration.values),
            "status": candidate.status.value,
            "notes": candidate.notes,
            "in_sample": _record_payload(candidate.in_sample),
            "out_of_sample": [_record_payload(record) for record in candidate.out_of_sample],
            "penalised_folds": candidate.penalised_fold_count,
        }
        self._database.execute(
            """
            INSERT INTO learning_candidate
                (signature, candidate_id, status, in_sample, out_of_sample,
                 overfit_gap, rejection, payload, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(signature) DO UPDATE SET
                candidate_id  = excluded.candidate_id,
                status        = excluded.status,
                in_sample     = excluded.in_sample,
                out_of_sample = excluded.out_of_sample,
                overfit_gap   = excluded.overfit_gap,
                rejection     = excluded.rejection,
                payload       = excluded.payload,
                recorded_at   = excluded.recorded_at
            """,
            (
                candidate.configuration.signature,
                candidate.candidate_id,
                candidate.status.value,
                _text(candidate.in_sample_score),
                _text(candidate.out_of_sample_score),
                _text(candidate.overfit_gap),
                (
                    candidate.rejection_reason.value
                    if candidate.rejection_reason is not None
                    else None
                ),
                json.dumps(payload, default=str),
                _now(),
            ),
        )

    def recall(self, signature: str) -> Optional[Candidate]:
        row = self._database.query_one(
            "SELECT * FROM learning_candidate WHERE signature = ?", (signature,)
        )
        return _row_to_candidate(row) if row is not None else None

    def known_failures(self) -> List[Candidate]:
        rows = self._database.query(
            "SELECT * FROM learning_candidate WHERE status = ? ORDER BY recorded_at",
            (CandidateStatus.REJECTED.value,),
        )
        return [_row_to_candidate(row) for row in rows]

    def all_candidates(self) -> List[Candidate]:
        rows = self._database.query("SELECT * FROM learning_candidate ORDER BY recorded_at")
        return [_row_to_candidate(row) for row in rows]

    # -- reporting --------------------------------------------------------
    def promoted(self) -> List[Candidate]:
        rows = self._database.query(
            "SELECT * FROM learning_candidate WHERE status = ? ORDER BY recorded_at",
            (CandidateStatus.PROMOTED.value,),
        )
        return [_row_to_candidate(row) for row in rows]

    def rejection_counts(self) -> Dict[str, int]:
        rows = self._database.query("""
            SELECT rejection, COUNT(*) AS total
            FROM learning_candidate
            WHERE rejection IS NOT NULL
            GROUP BY rejection ORDER BY total DESC
            """)
        return {row["rejection"]: int(row["total"]) for row in rows}

    def already_tried(self, configuration: CandidateConfiguration) -> bool:
        """True when this exact configuration was evaluated before."""
        return self.recall(configuration.signature) is not None

    def best_recorded(self) -> Optional[Candidate]:
        """The stored candidate with the best out-of-sample score."""
        row = self._database.query_one(
            """
            SELECT * FROM learning_candidate
            WHERE out_of_sample IS NOT NULL AND status != ?
            ORDER BY CAST(out_of_sample AS REAL) DESC LIMIT 1
            """,
            (CandidateStatus.REJECTED.value,),
        )
        return _row_to_candidate(row) if row is not None else None

    def clear(self) -> None:
        self._database.execute("DELETE FROM learning_candidate")

    def __len__(self) -> int:
        row = self._database.query_one("SELECT COUNT(*) AS total FROM learning_candidate")
        return int(row["total"]) if row else 0


class SqliteExperimentRepository(ExperimentRepository):
    """Stores experiments for audit and reproducibility."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._cache: Dict[str, LearningExperiment] = {}

    def save(self, experiment: LearningExperiment) -> None:
        self._cache[experiment.experiment_id] = experiment
        plan = experiment.plan
        payload = {
            "objective": experiment.objective_name,
            "status": experiment.status.value,
            "hypothesis": experiment.hypothesis,
            "metadata": _jsonable(experiment.metadata),
            "plan": {
                "in_sample": [plan.in_sample.start, plan.in_sample.end],
                "folds": [[fold.start, fold.end] for fold in plan.folds],
            },
            "candidates": [candidate.to_dict() for candidate in experiment.candidates],
            "baseline": (
                experiment.baseline.to_dict() if experiment.baseline is not None else None
            ),
        }
        self._database.execute(
            """
            INSERT INTO learning_experiment
                (experiment_id, objective, status, hypothesis, payload, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(experiment_id) DO UPDATE SET
                objective   = excluded.objective,
                status      = excluded.status,
                hypothesis  = excluded.hypothesis,
                payload     = excluded.payload,
                recorded_at = excluded.recorded_at
            """,
            (
                experiment.experiment_id,
                experiment.objective_name,
                experiment.status.value,
                experiment.hypothesis,
                json.dumps(payload, default=str),
                _now(),
            ),
        )

    def get(self, experiment_id: str) -> Optional[LearningExperiment]:
        """Return a live experiment object from this process, if present.

        Rehydrating a full ``LearningExperiment`` from JSON would require
        reconstructing every candidate and plan; the stored payload is
        the audit record, and :meth:`stored_row` exposes it.
        """
        return self._cache.get(experiment_id)

    def list_all(self) -> List[LearningExperiment]:
        return list(self._cache.values())

    # -- durable reads ------------------------------------------------------
    def stored_row(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        row = self._database.query_one(
            "SELECT * FROM learning_experiment WHERE experiment_id = ?",
            (experiment_id,),
        )
        return dict(row) if row is not None else None

    def stored_rows(self) -> List[Dict[str, Any]]:
        rows = self._database.query("SELECT * FROM learning_experiment ORDER BY recorded_at")
        return [dict(row) for row in rows]

    def __len__(self) -> int:
        row = self._database.query_one("SELECT COUNT(*) AS total FROM learning_experiment")
        return int(row["total"]) if row else 0


# ---------------------------------------------------------------- helpers ---
def _text(value: Optional[Decimal]) -> Optional[str]:
    return str(value) if value is not None else None


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _record_payload(record: Optional[EvaluationRecord]) -> Optional[Dict[str, Any]]:
    if record is None:
        return None
    return {
        "label": record.label,
        "score": str(record.score),
        "bars": record.bars,
        "metrics": record.metrics.to_dict(),
    }


def _metrics_from_payload(data: Dict[str, Any]) -> PerformanceMetrics:
    """Rebuild metrics from a stored dict (numbers only, no None-checks lost)."""

    def number(key: str, default: str = "0") -> Decimal:
        raw = data.get(key)
        return Decimal(str(raw)) if raw not in (None, "") else Decimal(default)

    def optional_number(key: str) -> Optional[Decimal]:
        raw = data.get(key)
        return Decimal(str(raw)) if raw not in (None, "") else None

    return PerformanceMetrics(
        starting_equity=number("starting_equity"),
        final_equity=number("final_equity"),
        total_return=number("total_return"),
        total_return_percent=number("total_return_percent"),
        max_drawdown=number("max_drawdown"),
        max_drawdown_percent=number("max_drawdown_percent"),
        trade_count=int(data.get("trade_count") or 0),
        win_count=int(data.get("win_count") or 0),
        loss_count=int(data.get("loss_count") or 0),
        total_fees=number("total_fees"),
        spread_cost=number("spread_cost"),
        slippage_cost=number("slippage_cost"),
        net_profit=optional_number("net_profit"),
        net_loss=optional_number("net_loss"),
    )


def _row_to_candidate(row: Any) -> Candidate:
    """Rebuild a Candidate from its stored payload."""
    payload = json.loads(row["payload"])
    candidate = Candidate(
        payload.get("candidate_id", row["candidate_id"]),
        CandidateConfiguration(payload.get("configuration", {})),
    )

    in_sample = payload.get("in_sample")
    if in_sample is not None:
        candidate.record_in_sample(
            EvaluationRecord(
                label=in_sample["label"],
                score=Decimal(in_sample["score"]),
                metrics=_metrics_from_payload(in_sample.get("metrics", {})),
                bars=int(in_sample.get("bars") or 0),
            )
        )

    for record in payload.get("out_of_sample", []):
        candidate.record_out_of_sample(
            EvaluationRecord(
                label=record["label"],
                score=Decimal(record["score"]),
                metrics=_metrics_from_payload(record.get("metrics", {})),
                bars=int(record.get("bars") or 0),
            )
        )

    # Restore the terminal status directly: the transition guards exist to
    # protect a live run, not to re-litigate a decision already recorded.
    status = CandidateStatus(payload.get("status", row["status"]))
    candidate._status = status  # noqa: SLF001 - deliberate rehydration
    if row["rejection"]:
        candidate._rejection_reason = RejectionReason(row["rejection"])  # noqa: SLF001
    for note in payload.get("notes", []):
        candidate._notes.append(note)  # noqa: SLF001

    return candidate
