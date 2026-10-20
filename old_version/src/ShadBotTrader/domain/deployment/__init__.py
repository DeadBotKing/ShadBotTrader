"""Deployment domain — Phase 24.

Everything needed to run the platform as a controlled, reversible,
observable service:

* :mod:`health`  — liveness, readiness and dependency classification
* :mod:`release` — versions, environments, manifests and safe shutdown
"""

from ShadBotTrader.domain.deployment.health import (
    CheckResult,
    DependencyKind,
    HealthMonitor,
    HealthReport,
    HealthStatus,
)
from ShadBotTrader.domain.deployment.release import (
    DeploymentManifest,
    Environment,
    ReleaseVersion,
    ShutdownPhase,
    ShutdownPlan,
)

__all__ = [
    "CheckResult",
    "DependencyKind",
    "DeploymentManifest",
    "Environment",
    "HealthMonitor",
    "HealthReport",
    "HealthStatus",
    "ReleaseVersion",
    "ShutdownPhase",
    "ShutdownPlan",
]
