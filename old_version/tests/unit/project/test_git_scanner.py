"""Tests for the GitScanner."""

import subprocess
from pathlib import Path

from ShadBotTrader.project.core.git_scanner import GitScanner


def test_not_a_repo_returns_empty_state(tmp_path: Path):
    state = GitScanner(tmp_path).scan()
    assert state.is_repo is False
    assert state.commit == ""


def test_repo_detected_with_branch_and_commit(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)

    state = GitScanner(tmp_path).scan()
    assert state.is_repo is True
    assert state.branch
    assert len(state.commit) == 40
    assert state.dirty is False
    assert any("init" in commit for commit in state.recent_commits)


def test_dirty_state_detected(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    (tmp_path / "f.txt").write_text("changed", encoding="utf-8")

    state = GitScanner(tmp_path).scan()
    assert state.dirty is True
    assert state.dirty_files >= 1
