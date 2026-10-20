"""Data models describing the scanned state of the project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class FileInfo:
    """A single workspace file discovered by the project scanner."""

    path: str
    category: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class GitState:
    """The git state observed at scan time."""

    is_repo: bool
    branch: str = ""
    commit: str = ""
    dirty: bool = False
    dirty_files: int = 0
    recent_commits: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModuleInfo:
    """A Python module and its static dependencies."""

    path: str
    name: str
    classes: int = 0
    functions: int = 0
    internal_imports: List[str] = field(default_factory=list)
    external_imports: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DependencyInfo:
    """A third-party package used by the project."""

    name: str
    used_by: int = 0


@dataclass(frozen=True)
class ProjectStatistics:
    """Aggregated numbers describing the project."""

    total_file_count: int = 0
    source_file_count: int = 0
    test_file_count: int = 0
    documentation_file_count: int = 0
    config_file_count: int = 0
    legacy_file_count: int = 0
    total_lines: int = 0
    source_lines: int = 0
    test_lines: int = 0
    module_count: int = 0
    class_count: int = 0
    function_count: int = 0
    internal_dependency_count: int = 0
    external_dependency_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return the statistics as a JSON-serialisable mapping."""
        return {
            "total_file_count": self.total_file_count,
            "source_file_count": self.source_file_count,
            "test_file_count": self.test_file_count,
            "documentation_file_count": self.documentation_file_count,
            "config_file_count": self.config_file_count,
            "legacy_file_count": self.legacy_file_count,
            "total_lines": self.total_lines,
            "source_lines": self.source_lines,
            "test_lines": self.test_lines,
            "module_count": self.module_count,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "internal_dependency_count": self.internal_dependency_count,
            "external_dependency_count": self.external_dependency_count,
        }


@dataclass(frozen=True)
class ProjectSnapshot:
    """The complete, immutable picture of the project at scan time."""

    project_name: str
    architecture_version: str
    current_phase: str
    generated_at: str
    python_version: str
    git: GitState
    files: List[FileInfo]
    modules: List[ModuleInfo]
    dependencies: List[DependencyInfo]
    statistics: ProjectStatistics

    def to_dict(self) -> Dict[str, Any]:
        """Return the snapshot as a JSON-serialisable mapping."""
        return {
            "project_name": self.project_name,
            "architecture_version": self.architecture_version,
            "current_phase": self.current_phase,
            "generated_at": self.generated_at,
            "python_version": self.python_version,
            "git": {
                "is_repo": self.git.is_repo,
                "branch": self.git.branch,
                "commit": self.git.commit,
                "dirty": self.git.dirty,
                "dirty_files": self.git.dirty_files,
                "recent_commits": list(self.git.recent_commits),
            },
            "source_file_count": self.statistics.source_file_count,
            "test_file_count": self.statistics.test_file_count,
            "statistics": self.statistics.to_dict(),
            "modules": [
                {
                    "path": module.path,
                    "name": module.name,
                    "classes": module.classes,
                    "functions": module.functions,
                    "internal_imports": list(module.internal_imports),
                    "external_imports": list(module.external_imports),
                }
                for module in self.modules
            ],
            "dependencies": [
                {"name": dep.name, "used_by": dep.used_by} for dep in self.dependencies
            ],
            "files": [
                {
                    "path": file.path,
                    "category": file.category,
                    "size_bytes": file.size_bytes,
                    "sha256": file.sha256,
                }
                for file in self.files
            ],
        }
