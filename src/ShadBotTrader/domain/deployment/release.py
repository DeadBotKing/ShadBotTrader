"""Release identity and deployment environments (Phase 24, §3, 9-10, 18).

Two ideas the phase document insists on:

**Everything important is versioned** (§9). A deployment is not "the
code" — it is a specific application version, against a specific schema
version, with specific model and dataset versions. When a live run
misbehaves, the first question is always "which combination is this?",
and that must be answerable from the artefact itself.

**Environments are separated** (§3). Development must not reach
production resources, and test data must never be production data. The
environment is therefore explicit and carries its own safety rules
rather than living in someone's memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.common.errors import ValidationError


class Environment(str, Enum):
    """Where a deployment is running (Phase 24, section 3)."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        return self is Environment.PRODUCTION

    @property
    def allows_real_money(self) -> bool:
        """Only production may ever touch a live account.

        Encoded here rather than checked ad hoc, so the rule cannot be
        forgotten at a call site.
        """
        return self is Environment.PRODUCTION

    @property
    def requires_confirmation(self) -> bool:
        """Deploying here should not be a one-keystroke accident."""
        return self in (Environment.PRODUCTION, Environment.STAGING)

    @classmethod
    def parse(cls, value: str) -> "Environment":
        cleaned = (value or "").strip().lower()
        for member in cls:
            if member.value == cleaned:
                return member
        known = ", ".join(member.value for member in cls)
        raise ValidationError(f"Unknown environment '{value}'. Known: {known}")


@dataclass(frozen=True)
class ReleaseVersion:
    """A semantic application version (Phase 24, section 10)."""

    major: int
    minor: int
    patch: int
    build: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("major", self.major),
            ("minor", self.minor),
            ("patch", self.patch),
        ):
            if value < 0:
                raise ValidationError(f"{name} must not be negative")

    @classmethod
    def parse(cls, text: str) -> "ReleaseVersion":
        """Parse ``1.2.3`` or ``1.2.3+abc123``."""
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValidationError("version must not be empty")

        build = ""
        if "+" in cleaned:
            cleaned, build = cleaned.split("+", 1)

        parts = cleaned.split(".")
        if len(parts) != 3:
            raise ValidationError(f"version must look like MAJOR.MINOR.PATCH, got '{text}'")
        try:
            numbers = [int(part) for part in parts]
        except ValueError as error:
            raise ValidationError(f"version components must be integers: '{text}'") from error

        return cls(major=numbers[0], minor=numbers[1], patch=numbers[2], build=build)

    def bump_patch(self) -> "ReleaseVersion":
        return ReleaseVersion(self.major, self.minor, self.patch + 1)

    def bump_minor(self) -> "ReleaseVersion":
        return ReleaseVersion(self.major, self.minor + 1, 0)

    def bump_major(self) -> "ReleaseVersion":
        return ReleaseVersion(self.major + 1, 0, 0)

    @property
    def core(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __str__(self) -> str:
        return f"{self.core}+{self.build}" if self.build else self.core

    def __lt__(self, other: "ReleaseVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


@dataclass(frozen=True)
class DeploymentManifest:
    """Exactly what is deployed, and against what (Phase 24, section 9).

    Model and dataset versions are part of the manifest because they
    change behaviour as surely as the code does. A rollback that
    restores the code but leaves a new model in place has not rolled
    anything back.
    """

    version: ReleaseVersion
    environment: Environment
    schema_version: int
    python_version: str
    deployed_at: str = ""
    git_commit: str = ""
    model_versions: Dict[str, int] = field(default_factory=dict)
    dataset_revision: Optional[int] = None
    notes: str = ""

    @classmethod
    def create(
        cls,
        version: ReleaseVersion,
        environment: Environment,
        schema_version: int,
        python_version: str = "",
        git_commit: str = "",
        model_versions: Optional[Dict[str, int]] = None,
        dataset_revision: Optional[int] = None,
        notes: str = "",
    ) -> "DeploymentManifest":
        import sys

        return cls(
            version=version,
            environment=environment,
            schema_version=schema_version,
            python_version=python_version or ".".join(str(n) for n in sys.version_info[:3]),
            deployed_at=datetime.now(timezone.utc).isoformat(),
            git_commit=git_commit,
            model_versions=dict(model_versions or {}),
            dataset_revision=dataset_revision,
            notes=notes,
        )

    @property
    def identity(self) -> str:
        """One line that identifies this deployment uniquely enough."""
        parts = [f"v{self.version}", self.environment.value, f"schema{self.schema_version}"]
        if self.git_commit:
            parts.append(self.git_commit[:8])
        return " · ".join(parts)

    def warnings(self) -> List[str]:
        """Things an operator should see before trusting this deployment."""
        messages: List[str] = []
        if self.environment.is_production and not self.git_commit:
            messages.append(
                "Production deployment has no git commit recorded — it cannot "
                "be traced back to source."
            )
        if self.environment.is_production and self.version.major == 0:
            messages.append(f"Deploying a pre-1.0 version ({self.version}) to production.")
        if not self.model_versions:
            messages.append("No model versions recorded; a rollback cannot restore them.")
        return messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": str(self.version),
            "environment": self.environment.value,
            "schema_version": self.schema_version,
            "python_version": self.python_version,
            "deployed_at": self.deployed_at,
            "git_commit": self.git_commit,
            "model_versions": dict(self.model_versions),
            "dataset_revision": self.dataset_revision,
            "notes": self.notes,
            "identity": self.identity,
            "warnings": self.warnings(),
        }


class ShutdownPhase(str, Enum):
    """Ordered steps of a safe shutdown (Phase 24, section 34)."""

    RUNNING = "running"
    #: Stop taking new work, finish what is in flight.
    DRAINING = "draining"
    #: Persist state so a restart resumes rather than restarts.
    PERSISTING = "persisting"
    STOPPED = "stopped"


@dataclass
class ShutdownPlan:
    """Tracks a graceful stop.

    Order matters and is enforced: refusing new work must happen before
    persisting, or the state written is already stale. Skipping the
    drain is how a deployment kills a half-executed order.
    """

    phase: ShutdownPhase = ShutdownPhase.RUNNING
    reason: str = ""
    in_flight: int = 0
    steps: List[str] = field(default_factory=list)

    @property
    def accepting_work(self) -> bool:
        return self.phase is ShutdownPhase.RUNNING

    @property
    def is_stopped(self) -> bool:
        return self.phase is ShutdownPhase.STOPPED

    def begin_drain(self, reason: str = "") -> None:
        if self.phase is not ShutdownPhase.RUNNING:
            raise ValidationError(f"Cannot start draining from {self.phase.value}")
        self.phase = ShutdownPhase.DRAINING
        self.reason = reason
        self.steps.append("stopped accepting new work")

    def complete_work(self) -> None:
        """Mark in-flight work as finished."""
        if self.phase is not ShutdownPhase.DRAINING:
            raise ValidationError("Work can only be drained while draining")
        self.in_flight = 0
        self.steps.append("in-flight work completed")

    def persist(self) -> None:
        if self.phase is not ShutdownPhase.DRAINING:
            raise ValidationError(
                "State must be persisted after draining, not before — "
                "otherwise the saved state is already out of date."
            )
        if self.in_flight > 0:
            raise ValidationError(
                f"{self.in_flight} operation(s) still in flight; drain them first."
            )
        self.phase = ShutdownPhase.PERSISTING
        self.steps.append("state persisted")

    def finish(self) -> None:
        if self.phase not in (ShutdownPhase.PERSISTING, ShutdownPhase.DRAINING):
            raise ValidationError(f"Cannot finish shutdown from {self.phase.value}")
        self.phase = ShutdownPhase.STOPPED
        self.steps.append("stopped")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase.value,
            "reason": self.reason,
            "in_flight": self.in_flight,
            "steps": list(self.steps),
            "accepting_work": self.accepting_work,
        }
