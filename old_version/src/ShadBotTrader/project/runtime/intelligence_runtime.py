"""Orchestrates scan -> build -> export -> archive for project state."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from ShadBotTrader.project.builders.context_builder import ContextBuilder
from ShadBotTrader.project.builders.documentation_builder import DocumentationBuilder
from ShadBotTrader.project.builders.snapshot_builder import SnapshotBuilder
from ShadBotTrader.project.exporters.json_exporter import JsonExporter
from ShadBotTrader.project.exporters.markdown_exporter import MarkdownExporter
from ShadBotTrader.project.models.project_snapshot import ProjectSnapshot


class IntelligenceRuntime:
    """Runs the full Project Intelligence pipeline.

    Pipeline: scan -> snapshot -> context/architecture documents ->
    export to ``project_state/generated/``. Any previously generated
    files are moved into a timestamped directory under
    ``project_state/archive/`` first (evolution model).
    """

    #: How many archived snapshots to keep. Older ones are deleted; they
    #: are regenerable from the code they describe.
    ARCHIVE_KEEP = 5

    GENERATED = (
        "ProjectSnapshot.md",
        "ProjectSnapshot.json",
        "ChatGPT_Context.md",
        "Architecture.md",
        "Statistics.json",
    )

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._generated_dir = project_root / "project_state" / "generated"
        self._archive_dir = project_root / "project_state" / "archive"

    def run(self) -> ProjectSnapshot:
        """Run the pipeline and return the generated snapshot."""
        snapshot = SnapshotBuilder(self._root).build()
        self._archive_previous()
        self._export(snapshot)
        return snapshot

    def _export(self, snapshot: ProjectSnapshot) -> None:
        markdown = self._build_markdown_documents(snapshot)
        json_documents = self._build_json_documents(snapshot)

        MarkdownExporter(self._generated_dir).export(markdown)
        JsonExporter(self._generated_dir).export(json_documents)

    def _build_markdown_documents(self, snapshot: ProjectSnapshot) -> Dict[str, str]:
        return {
            "ProjectSnapshot.md": self._render_snapshot_markdown(snapshot),
            "ChatGPT_Context.md": ContextBuilder().build(snapshot).to_markdown(),
            "Architecture.md": DocumentationBuilder().build(snapshot),
        }

    def _build_json_documents(self, snapshot: ProjectSnapshot) -> Dict[str, object]:
        return {
            "ProjectSnapshot.json": snapshot.to_dict(),
            "Statistics.json": snapshot.statistics.to_dict(),
        }

    @staticmethod
    def _render_snapshot_markdown(snapshot: ProjectSnapshot) -> str:
        git = snapshot.git
        stats = snapshot.statistics
        dependency_lines = "\n".join(
            f"- {dep.name}: used by {dep.used_by} module(s)" for dep in snapshot.dependencies[:20]
        )
        if not dependency_lines:
            dependency_lines = "- (none)"

        git_commit = git.commit if git.is_repo else "n/a"
        git_branch = git.branch if git.is_repo else "n/a"

        return "\n".join(
            [
                "# Project Snapshot",
                "",
                f"- Project name: {snapshot.project_name}",
                f"- Architecture version: {snapshot.architecture_version}",
                f"- Current phase: {snapshot.current_phase}",
                f"- Generated at: {snapshot.generated_at}",
                f"- Python version: {snapshot.python_version}",
                f"- Git branch: {git_branch}",
                f"- Git commit: {git_commit}",
                f"- Dirty: {'yes' if git.dirty else 'no'}",
                "",
                "## Statistics",
                "",
                f"- Source files: {stats.source_file_count}",
                f"- Test files: {stats.test_file_count}",
                f"- Documentation files: {stats.documentation_file_count}",
                f"- Legacy files: {stats.legacy_file_count}",
                f"- Total Python lines: {stats.total_lines}",
                f"- Modules: {stats.module_count}",
                f"- Classes: {stats.class_count}",
                f"- Functions: {stats.function_count}",
                "",
                "## External dependencies (top 20)",
                "",
                dependency_lines,
            ]
        )

    def _archive_previous(self) -> None:
        """Move previously generated files into a timestamped archive dir."""
        if not self._generated_dir.exists():
            return
        previous = [
            path
            for path in self._generated_dir.iterdir()
            if path.is_file() and path.name in self.GENERATED
        ]
        if not previous:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        target_dir = self._archive_dir / stamp
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in previous:
            shutil.move(str(path), str(target_dir / path.name))
        self._prune_archive()

    def _prune_archive(self) -> None:
        """Keep only the most recent snapshots (Phase 48).

        Every run of the intelligence pipeline archived the previous
        output and nothing ever removed it. After 158 runs the archive
        held 48 MB — a third of the whole workspace — of near-identical
        snapshots nobody had read.

        The evolution model wants *some* history, not all of it, so a
        small window is kept and the rest is dropped.
        """
        if not self._archive_dir.is_dir():
            return
        snapshots = sorted(
            (path for path in self._archive_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )
        for stale in snapshots[: -self.ARCHIVE_KEEP] if self.ARCHIVE_KEEP else snapshots:
            shutil.rmtree(stale, ignore_errors=True)
