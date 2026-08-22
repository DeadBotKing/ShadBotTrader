"""Stage 1 causality audit for model/live Feature inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.feature.feature_set import FeatureSet


@dataclass(frozen=True)
class FeatureAuditRow:
    """One auditable feature decision."""

    feature_id: str
    allowed: bool
    reason: str
    forward_lookahead: int
    family: str


@dataclass(frozen=True)
class CausalityAuditReport:
    """Complete allow/block report for a feature set."""

    rows: List[FeatureAuditRow]

    @property
    def allowed(self) -> List[str]:
        return [row.feature_id for row in self.rows if row.allowed]

    @property
    def excluded(self) -> Dict[str, str]:
        return {row.feature_id: row.reason for row in self.rows if not row.allowed}

    @property
    def is_clean(self) -> bool:
        return not self.excluded

    def summary(self) -> Dict[str, Any]:
        return {
            "total": len(self.rows),
            "allowed": len(self.allowed),
            "excluded": len(self.excluded),
            "excluded_features": dict(self.excluded),
            "clean": self.is_clean,
        }


def audit_feature_set(
    feature_set: FeatureSet,
    resolver: Optional[Any] = None,
) -> CausalityAuditReport:
    """Audit a catalog without computing any feature values.

    Unknown calculator families are blocked when a resolver is supplied.
    This is intentionally a fail-closed report: an unclassified feature
    must be promoted to the causal model set explicitly.
    """
    rows: List[FeatureAuditRow] = []
    for definition in feature_set.definitions:
        feature_id = definition.feature_id.value
        family = definition.calculator_family
        if not definition.is_live_compatible:
            reason = definition.leakage_reason or f"causality={definition.causality.value}"
            if definition.forward_lookahead:
                reason += f"; lookahead={definition.forward_lookahead}"
            rows.append(
                FeatureAuditRow(
                    feature_id=feature_id,
                    allowed=False,
                    reason=reason,
                    forward_lookahead=definition.forward_lookahead,
                    family=family,
                )
            )
            continue
        if resolver is not None and resolver.resolve(family) is None:
            rows.append(
                FeatureAuditRow(
                    feature_id=feature_id,
                    allowed=False,
                    reason=f"UNKNOWN_CALCULATOR_FAMILY:{family}",
                    forward_lookahead=definition.forward_lookahead,
                    family=family,
                )
            )
            continue
        rows.append(
            FeatureAuditRow(
                feature_id=feature_id,
                allowed=True,
                reason="causal",
                forward_lookahead=definition.forward_lookahead,
                family=family,
            )
        )
    return CausalityAuditReport(rows=rows)
