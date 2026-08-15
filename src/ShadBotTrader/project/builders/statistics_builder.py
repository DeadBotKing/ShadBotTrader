"""Aggregates raw scan data into a ProjectStatistics value."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ShadBotTrader.project.models.project_snapshot import (
    FileInfo,
    ModuleInfo,
    ProjectStatistics,
)


class StatisticsBuilder:
    """Computes project statistics from a file inventory and modules."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def build(self, files: List[FileInfo], modules: List[ModuleInfo]) -> ProjectStatistics:
        """Aggregate ``files`` and ``modules`` into statistics."""
        python_paths = [file.path for file in files if file.path.endswith(".py")]

        source_count = sum(1 for path in python_paths if path.startswith("src/"))
        test_count = sum(1 for path in python_paths if path.startswith("tests/"))
        documentation_count = sum(1 for file in files if file.category == "documentation")
        config_count = sum(1 for file in files if file.category == "config")
        legacy_count = sum(1 for file in files if file.category == "legacy")

        total_lines = self._count_lines(self._resolve(python_paths))
        source_lines = self._count_lines(
            self._resolve([p for p in python_paths if p.startswith("src/")])
        )
        test_lines = self._count_lines(
            self._resolve([p for p in python_paths if p.startswith("tests/")])
        )

        internal_imports: set[str] = set()
        external_imports: set[str] = set()
        for module in modules:
            internal_imports.update(module.internal_imports)
            external_imports.update(module.external_imports)

        return ProjectStatistics(
            total_file_count=len(files),
            source_file_count=source_count,
            test_file_count=test_count,
            documentation_file_count=documentation_count,
            config_file_count=config_count,
            legacy_file_count=legacy_count,
            total_lines=total_lines,
            source_lines=source_lines,
            test_lines=test_lines,
            module_count=len(modules),
            class_count=sum(module.classes for module in modules),
            function_count=sum(module.functions for module in modules),
            internal_dependency_count=len(internal_imports),
            external_dependency_count=len(external_imports),
        )

    def _resolve(self, relative_paths: List[str]) -> List[Path]:
        return [self._root / path for path in relative_paths if (self._root / path).is_file()]

    @staticmethod
    def _count_lines(paths: List[Path]) -> int:
        total = 0
        for path in paths:
            try:
                total += sum(1 for _ in path.open(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
        return total
