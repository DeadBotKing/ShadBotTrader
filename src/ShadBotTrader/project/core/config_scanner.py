"""Reads project configuration (pyproject.toml and YAML config files)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class ProjectConfiguration:
    """Configuration facts extracted from the project."""

    name: str = ""
    version: str = ""
    python_requirement: str = ""
    dependencies: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)


class ConfigScanner:
    """Scans ``pyproject.toml`` and ``configs/*`` for project facts."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def scan(self) -> ProjectConfiguration:
        """Extract project configuration facts from the workspace."""
        pyproject = self._read_pyproject()
        config_files = self._list_config_files()
        return ProjectConfiguration(
            name=pyproject.get("name", ""),
            version=pyproject.get("version", ""),
            python_requirement=pyproject.get("python_requirement", ""),
            dependencies=pyproject.get("dependencies", []),
            config_files=config_files,
        )

    def _read_pyproject(self) -> Dict[str, Any]:
        path = self._root / "pyproject.toml"
        if not path.exists():
            return {}
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:  # pragma: no cover
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                return {}
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, ValueError):
            return {}
        project = data.get("project", {})
        dependencies = list(project.get("dependencies", []))
        return {
            "name": project.get("name", ""),
            "version": project.get("version", ""),
            "python_requirement": project.get("requires-python", ""),
            "dependencies": dependencies,
        }

    def _list_config_files(self) -> List[str]:
        configs_dir = self._root / "configs"
        if not configs_dir.is_dir():
            return []
        return sorted(
            path.relative_to(self._root).as_posix()
            for path in configs_dir.rglob("*")
            if path.is_file()
        )
