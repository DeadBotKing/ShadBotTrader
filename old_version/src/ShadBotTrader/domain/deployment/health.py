"""Health, readiness and liveness (Phase 24, sections 38-42).

The phase document separates three questions that are easy to conflate:

* **liveness**  — is the process still alive? (restart it if not)
* **readiness** — is it ready to accept work? (route work elsewhere if not)
* **health**    — is every dependency behaving?

They are distinct on purpose. A platform that has just started is *alive*
but not *ready*; one whose broker connection dropped is alive and ready
to serve a dashboard but must not trade. Collapsing them into a single
boolean is how a deployment ends up trading on a half-initialised system.

Dependencies are also classified (section 42): a failed **critical**
dependency makes the system unhealthy, while a failed **optional** one
degrades it. TensorFlow being absent should not stop the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List


class HealthStatus(str, Enum):
    """Overall verdict, ordered from best to worst."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

    @property
    def is_serving(self) -> bool:
        """Degraded still serves; unhealthy does not."""
        return self is not HealthStatus.UNHEALTHY


class DependencyKind(str, Enum):
    """How much a dependency matters (Phase 24, section 42)."""

    #: Without it the platform cannot do its job.
    CRITICAL = "critical"
    #: Its absence removes a capability but the rest keeps working.
    OPTIONAL = "optional"


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one dependency check."""

    name: str
    kind: DependencyKind
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0

    @property
    def blocks_service(self) -> bool:
        """A failed critical check takes the whole system down."""
        return not self.passed and self.kind is DependencyKind.CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "passed": self.passed,
            "detail": self.detail,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class HealthReport:
    """Everything the probes found, in one auditable object."""

    checks: List[CheckResult] = field(default_factory=list)
    checked_at: str = ""
    version: str = ""
    environment: str = ""

    @property
    def status(self) -> HealthStatus:
        if any(check.blocks_service for check in self.checks):
            return HealthStatus.UNHEALTHY
        if any(not check.passed for check in self.checks):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    @property
    def is_live(self) -> bool:
        """Liveness: the process answered at all (section 40)."""
        return True

    @property
    def is_ready(self) -> bool:
        """Readiness: every critical dependency is up (section 39)."""
        return not any(check.blocks_service for check in self.checks)

    @property
    def failures(self) -> List[CheckResult]:
        return [check for check in self.checks if not check.passed]

    def summary_lines(self) -> List[str]:
        lines = [f"status: {self.status.value}"]
        for check in self.checks:
            mark = "ok  " if check.passed else "FAIL"
            lines.append(f"  [{mark}] {check.name:<22} ({check.kind.value}) {check.detail}")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "live": self.is_live,
            "ready": self.is_ready,
            "version": self.version,
            "environment": self.environment,
            "checked_at": self.checked_at,
            "checks": [check.to_dict() for check in self.checks],
            "failures": [check.name for check in self.failures],
        }


class HealthMonitor:
    """Runs registered dependency checks and assembles a report.

    A check that raises is recorded as a failure rather than propagating:
    a health endpoint that itself crashes tells an operator nothing.
    """

    def __init__(self, version: str = "", environment: str = "") -> None:
        self._checks: List[tuple[str, DependencyKind, Callable[[], Any]]] = []
        self._version = version
        self._environment = environment

    def register(
        self,
        name: str,
        check: Callable[[], Any],
        kind: DependencyKind = DependencyKind.CRITICAL,
    ) -> "HealthMonitor":
        """Add a check. Returns self so registrations can chain."""
        self._checks.append((name, kind, check))
        return self

    @property
    def registered(self) -> List[str]:
        return [name for name, _, _ in self._checks]

    def run(self) -> HealthReport:
        """Execute every check; never raises."""
        import time

        results: List[CheckResult] = []
        for name, kind, check in self._checks:
            started = time.monotonic()
            try:
                outcome = check()
                passed = bool(outcome) if not isinstance(outcome, tuple) else bool(outcome[0])
                detail = "" if not isinstance(outcome, tuple) else str(outcome[1])
            except Exception as error:
                passed = False
                detail = f"{type(error).__name__}: {error}"
            results.append(
                CheckResult(
                    name=name,
                    kind=kind,
                    passed=passed,
                    detail=detail,
                    duration_ms=(time.monotonic() - started) * 1000.0,
                )
            )

        return HealthReport(
            checks=results,
            checked_at=datetime.now(timezone.utc).isoformat(),
            version=self._version,
            environment=self._environment,
        )
