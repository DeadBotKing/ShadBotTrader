"""Tests for the ProjectScanner."""

from pathlib import Path

from ShadBotTrader.project.core.project_scanner import ProjectScanner


def _make_fixture(tmp_path: Path) -> Path:
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("# doc\n", encoding="utf-8")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "app.yaml").write_text("app: {}\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()  # excluded directory
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.pyc").write_bytes(b"\x00\x01")
    return tmp_path


def test_scanner_categorises_files(tmp_path: Path):
    root = _make_fixture(tmp_path)
    files = ProjectScanner(root).scan()
    paths = {file.path for file in files}
    assert "src/app/main.py" in paths
    assert "tests/test_a.py" in paths
    assert "docs/readme.md" in paths
    assert "configs/app.yaml" in paths


def test_scanner_excludes_hidden_and_cache_dirs(tmp_path: Path):
    root = _make_fixture(tmp_path)
    files = ProjectScanner(root).scan()
    paths = {file.path for file in files}
    assert ".git/config" not in paths
    assert "__pycache__/junk.pyc" not in paths


def test_scanner_assigns_categories(tmp_path: Path):
    root = _make_fixture(tmp_path)
    files = {file.path: file for file in ProjectScanner(root).scan()}
    assert files["src/app/main.py"].category == "source"
    assert files["tests/test_a.py"].category == "test"
    assert files["docs/readme.md"].category == "documentation"
    assert files["configs/app.yaml"].category == "config"


def test_scanner_computes_sha256(tmp_path: Path):
    root = _make_fixture(tmp_path)
    files = {file.path: file for file in ProjectScanner(root).scan()}
    assert len(files["src/app/main.py"].sha256) == 64
    assert files["src/app/main.py"].size_bytes > 0
