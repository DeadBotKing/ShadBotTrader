"""Scans the workspace file tree and categorises every file."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from ShadBotTrader.project.models.project_snapshot import FileInfo

DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        ".idea",
        ".vscode",
        "node_modules",
        "build",
        "dist",
        "project_state",
        "datasets",
    }
)

_CATEGORY_BY_DIR: dict[str, str] = {
    "src": "source",
    "tests": "test",
    "docs": "documentation",
    "architecture": "documentation",
    "configs": "config",
    "legacy": "legacy",
    "scripts": "script",
}


class ProjectScanner:
    """Walks the project tree and returns a categorized file inventory."""

    def __init__(
        self, project_root: Path, excluded_dirs: frozenset[str] = DEFAULT_EXCLUDED_DIRS
    ) -> None:
        self._root = project_root
        self._excluded_dirs = excluded_dirs

    def scan(self) -> List[FileInfo]:
        """Return the file inventory of the project root."""
        files: List[FileInfo] = []
        for path in sorted(self._root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in self._excluded_dirs for part in path.relative_to(self._root).parts):
                continue
            files.append(self._inspect(path))
        return files

    def _inspect(self, path: Path) -> FileInfo:
        relative = path.relative_to(self._root).as_posix()
        category = self._categorise(relative)
        return FileInfo(
            path=relative,
            category=category,
            size_bytes=path.stat().st_size,
            sha256=self._sha256(path),
        )

    @staticmethod
    def _categorise(relative_path: str) -> str:
        top = relative_path.split("/", 1)[0]
        if top in _CATEGORY_BY_DIR:
            return _CATEGORY_BY_DIR[top]
        if relative_path.endswith((".toml", ".yaml", ".yml", ".ini", ".json")):
            return "config"
        return "other"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
