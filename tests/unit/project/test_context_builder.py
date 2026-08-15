"""Tests for the ContextBuilder."""

from datetime import datetime, timezone

from ShadBotTrader.project.builders.context_builder import ContextBuilder
from ShadBotTrader.project.models.project_snapshot import (
    GitState,
    ProjectSnapshot,
    ProjectStatistics,
)


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot(
        project_name="ShadBotTrader",
        architecture_version="1.0",
        current_phase="Phase 28",
        generated_at=datetime.now(timezone.utc).isoformat(),
        python_version="3.13",
        git=GitState(is_repo=True, branch="main", commit="a" * 40),
        files=[],
        modules=[],
        dependencies=[],
        statistics=ProjectStatistics(source_file_count=10, test_file_count=3),
    )


def test_context_contains_all_required_sections():
    context = ContextBuilder().build(_snapshot())
    markdown = context.to_markdown()
    for title in (
        "Project Identity",
        "Current Architecture",
        "Current Phase",
        "Implemented Components",
        "Git Commit",
        "Quality Gate",
        "Known Issues",
        "Next Phase",
        "Statistics",
    ):
        assert f"## {title}" in markdown


def test_context_reports_git_commit():
    markdown = ContextBuilder().build(_snapshot()).to_markdown()
    assert "a" * 40 in markdown
    assert "Branch: main" in markdown


def test_context_reports_quality_gate_commands():
    markdown = ContextBuilder().build(_snapshot()).to_markdown()
    assert "python -m black --check ." in markdown
    assert "python -m pytest" in markdown
