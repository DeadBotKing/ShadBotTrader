"""End-to-end tests for the IntelligenceRuntime."""

import json
import subprocess
from pathlib import Path

from ShadBotTrader.project.runtime.intelligence_runtime import IntelligenceRuntime


def _make_project(tmp_path: Path) -> Path:
    (tmp_path / "src" / "ShadBotTrader" / "core").mkdir(parents=True)
    (tmp_path / "src" / "ShadBotTrader" / "core" / "m.py").write_text(
        "class A:\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "ShadBotTrader"\nversion = "0.1.0"\n'
        'requires-python = ">=3.10"\ndependencies = ["PyYAML>=6.0"]\n',
        encoding="utf-8",
    )
    (tmp_path / "project_state" / "generated").mkdir(parents=True)
    (tmp_path / "project_state" / "archive").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "a@b.c"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    return tmp_path


def test_runtime_generates_all_five_artifacts(tmp_path: Path):
    root = _make_project(tmp_path)
    snapshot = IntelligenceRuntime(root).run()

    generated = root / "project_state" / "generated"
    for name in (
        "ProjectSnapshot.md",
        "ProjectSnapshot.json",
        "ChatGPT_Context.md",
        "Architecture.md",
        "Statistics.json",
    ):
        assert (generated / name).exists(), f"missing {name}"

    assert snapshot.project_name == "ShadBotTrader"
    assert snapshot.statistics.source_file_count == 1
    assert snapshot.statistics.test_file_count == 1


def test_snapshot_json_has_required_fields(tmp_path: Path):
    root = _make_project(tmp_path)
    IntelligenceRuntime(root).run()
    data = json.loads(
        (root / "project_state" / "generated" / "ProjectSnapshot.json").read_text(encoding="utf-8")
    )
    for field in (
        "project_name",
        "architecture_version",
        "current_phase",
        "python_version",
        "git",
        "source_file_count",
        "test_file_count",
        "modules",
        "dependencies",
        "statistics",
    ):
        assert field in data, f"missing field {field}"


def test_runtime_archives_previous_state(tmp_path: Path):
    root = _make_project(tmp_path)
    runtime = IntelligenceRuntime(root)
    runtime.run()
    runtime.run()  # second run archives the first

    archive = root / "project_state" / "archive"
    archived_dirs = [p for p in archive.iterdir() if p.is_dir()]
    assert len(archived_dirs) == 1
    assert (archived_dirs[0] / "ProjectSnapshot.md").exists()
