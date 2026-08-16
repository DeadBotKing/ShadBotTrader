"""Builds the portable ChatGPT/handoff context from a snapshot."""

from __future__ import annotations

from collections import OrderedDict
from typing import List

from ShadBotTrader.project.models.project_context import ProjectContext
from ShadBotTrader.project.models.project_snapshot import ProjectSnapshot

NEXT_PHASE = (
    "Sprint P4 — Trading Platform: strategies, signals, decision and "
    "execution abstractions (risk-gated, broker-agnostic)."
)

KNOWN_ISSUES = [
    "None recorded for the current foundation.",
]


class ContextBuilder:
    """Turns a ProjectSnapshot into a self-contained markdown context."""

    def build(self, snapshot: ProjectSnapshot) -> ProjectContext:
        """Assemble the ChatGPT context sections from ``snapshot``."""
        sections: "OrderedDict[str, str]" = OrderedDict()
        sections["Project Identity"] = self._identity(snapshot)
        sections["Current Architecture"] = self._architecture(snapshot)
        sections["Current Phase"] = snapshot.current_phase
        sections["Implemented Components"] = self._components(snapshot)
        sections["Git Commit"] = self._git(snapshot)
        sections["Quality Gate"] = self._quality_gate()
        sections["Known Issues"] = self._bullet_list(KNOWN_ISSUES)
        sections["Next Phase"] = NEXT_PHASE
        sections["Statistics"] = self._statistics(snapshot)
        return ProjectContext(sections=sections)

    @staticmethod
    def _identity(snapshot: ProjectSnapshot) -> str:
        return "\n".join(
            [
                f"- Project name: {snapshot.project_name}",
                f"- Architecture version: {snapshot.architecture_version}",
                f"- Python version: {snapshot.python_version}",
                f"- Snapshot generated at: {snapshot.generated_at}",
            ]
        )

    @staticmethod
    def _architecture(snapshot: ProjectSnapshot) -> str:
        return "\n".join(
            [
                "- Clean Architecture + Domain-Driven Design",
                "- Dependency direction: infrastructure -> application -> domain",
                "- Event-driven + plugin-based core",
                f"- Source modules: {snapshot.statistics.source_file_count}",
                f"- Test modules: {snapshot.statistics.test_file_count}",
            ]
        )

    @staticmethod
    def _components(snapshot: ProjectSnapshot) -> str:
        from ShadBotTrader.project.builders.documentation_builder import DocumentationBuilder

        return DocumentationBuilder.component_summary(snapshot)

    @staticmethod
    def _git(snapshot: ProjectSnapshot) -> str:
        git = snapshot.git
        if not git.is_repo:
            return "- Not a git repository"
        lines = [
            f"- Branch: {git.branch}",
            f"- Commit: {git.commit}",
            (
                f"- Dirty: {'yes' if git.dirty else 'no'}" f" ({git.dirty_files} files)"
                if git.dirty
                else "- Dirty: no"
            ),
        ]
        if git.recent_commits:
            lines.append("- Recent commits:")
            lines.extend(f"  - {commit}" for commit in git.recent_commits)
        return "\n".join(lines)

    @staticmethod
    def _quality_gate() -> str:
        return "\n".join(
            [
                "Run from the repository root:",
                "```bash",
                "python -m black --check .",
                "python -m ruff check .",
                "python -m mypy src",
                "python -m pytest",
                "```",
            ]
        )

    @staticmethod
    def _statistics(snapshot: ProjectSnapshot) -> str:
        stats = snapshot.statistics
        return "\n".join(
            [
                f"- Total files: {stats.total_file_count}",
                f"- Source files: {stats.source_file_count}",
                f"- Test files: {stats.test_file_count}",
                f"- Documentation files: {stats.documentation_file_count}",
                f"- Legacy files: {stats.legacy_file_count}",
                f"- Total Python lines: {stats.total_lines}",
                f"- Modules: {stats.module_count}",
                f"- Classes: {stats.class_count}",
                f"- Functions: {stats.function_count}",
                f"- External dependencies: {stats.external_dependency_count}",
            ]
        )

    @staticmethod
    def _bullet_list(items: List[str]) -> str:
        return "\n".join(f"- {item}" for item in items)
