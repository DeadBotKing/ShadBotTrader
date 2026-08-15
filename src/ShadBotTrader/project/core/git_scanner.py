"""Extracts git state (branch, commit, dirty state, recent commits)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

from ShadBotTrader.project.models.project_snapshot import GitState


class GitScanner:
    """Reads git state via the ``git`` command line interface."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def scan(self) -> GitState:
        """Return the git state of the project, or an empty state when
        the project is not inside a git repository."""
        if not (self._root / ".git").exists():
            return GitState(is_repo=False)

        branch = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        commit = self._run(["rev-parse", "HEAD"])
        dirty_output = self._run(["status", "--porcelain"])
        dirty_files = len([line for line in dirty_output.splitlines() if line.strip()])
        recent = self._recent_commits(10)

        return GitState(
            is_repo=True,
            branch=branch,
            commit=commit,
            dirty=dirty_files > 0,
            dirty_files=dirty_files,
            recent_commits=recent,
        )

    def _recent_commits(self, limit: int) -> List[str]:
        output = self._run(["log", "--oneline", f"-{limit}"])
        return [line for line in output.splitlines() if line.strip()]

    def _run(self, args: List[str]) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(self._root), *args],
                capture_output=True,
                text=True,
                check=False,
            )
        except (FileNotFoundError, OSError):
            return ""
        return completed.stdout.strip()
