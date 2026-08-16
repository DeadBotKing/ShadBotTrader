"""Composes scanner output into a single ProjectSnapshot."""

from __future__ import annotations

import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ShadBotTrader.project.builders.statistics_builder import StatisticsBuilder
from ShadBotTrader.project.core.ast_scanner import AstScanner
from ShadBotTrader.project.core.config_scanner import ConfigScanner
from ShadBotTrader.project.core.git_scanner import GitScanner
from ShadBotTrader.project.core.project_scanner import ProjectScanner
from ShadBotTrader.project.models.project_snapshot import (
    DependencyInfo,
    ProjectSnapshot,
)

ARCHITECTURE_VERSION = "1.0"
CURRENT_PHASE = (
    "Phase 28 — Implementation Foundation (Sprint P2: Feature Platform — full 85-feature catalog)"
)


class SnapshotBuilder:
    """Runs all scanners and assembles the canonical ProjectSnapshot."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._project_scanner = ProjectScanner(project_root)
        self._ast_scanner = AstScanner(project_root)
        self._git_scanner = GitScanner(project_root)
        self._config_scanner = ConfigScanner(project_root)
        self._statistics_builder = StatisticsBuilder(project_root)

    def build(self) -> ProjectSnapshot:
        """Run the full scan and build the snapshot."""
        files = self._project_scanner.scan()
        python_files = [
            self._root / file.path
            for file in files
            if file.path.endswith(".py") and file.category in ("source", "test")
        ]
        modules = self._ast_scanner.scan(python_files)
        dependencies = self._build_dependencies(modules)
        statistics = self._statistics_builder.build(files, modules)
        configuration = self._config_scanner.scan()
        git = self._git_scanner.scan()

        project_name = configuration.name or "ShadBotTrader"

        return ProjectSnapshot(
            project_name=project_name,
            architecture_version=ARCHITECTURE_VERSION,
            current_phase=CURRENT_PHASE,
            generated_at=datetime.now(timezone.utc).isoformat(),
            python_version=platform.python_version(),
            git=git,
            files=files,
            modules=modules,
            dependencies=dependencies,
            statistics=statistics,
        )

    @staticmethod
    def _build_dependencies(modules: List) -> List[DependencyInfo]:
        usage: Counter[str] = Counter()
        for module in modules:
            for external in set(module.external_imports):
                usage[external] += 1
        return [
            DependencyInfo(name=name, used_by=count)
            for name, count in sorted(usage.items(), key=lambda item: (-item[1], item[0]))
        ]
