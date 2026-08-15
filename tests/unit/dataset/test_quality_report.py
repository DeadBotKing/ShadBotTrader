"""Tests for QualityScore and QualityReport."""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.dataset.quality_report import (
    IssueSeverity,
    QualityIssue,
    QualityReport,
    QualityScore,
)


def test_overall_score_is_mean_of_dimensions():
    score = QualityScore(
        completeness=Decimal(100),
        consistency=Decimal(80),
        validity=Decimal(100),
        timeliness=Decimal(90),
        uniqueness=Decimal(100),
    )
    assert score.overall == Decimal("94.00")


def test_score_rejects_out_of_range():
    with pytest.raises(ValidationError):
        QualityScore(
            completeness=Decimal(150),
            consistency=Decimal(0),
            validity=Decimal(0),
            timeliness=Decimal(0),
            uniqueness=Decimal(0),
        )


def test_report_detects_critical_issue():
    report = QualityReport(
        score=QualityScore(
            completeness=Decimal(100),
            consistency=Decimal(100),
            validity=Decimal(100),
            timeliness=Decimal(100),
            uniqueness=Decimal(100),
        ),
        issues=[QualityIssue("X", IssueSeverity.CRITICAL, "bad")],
    )
    assert report.has_critical is True


def test_issue_to_dict():
    issue = QualityIssue("GAP_DETECTED", IssueSeverity.WARNING, "gap", count=3)
    assert issue.to_dict()["count"] == 3
    assert issue.to_dict()["severity"] == "warning"
