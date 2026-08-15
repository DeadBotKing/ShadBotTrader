"""Tests for the AstScanner."""

from pathlib import Path

from ShadBotTrader.project.core.ast_scanner import AstScanner


def _write_module(tmp_path: Path) -> Path:
    source = (
        "import os\n"
        "import pandas as pd\n"
        "from ShadBotTrader.core.events import Event\n"
        "from numpy import array\n"
        "\n"
        "class Thing:\n"
        "    pass\n"
        "\n"
        "def helper():\n"
        "    return Thing()\n"
    )
    path = tmp_path / "src" / "ShadBotTrader" / "sample.py"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_extracts_classes_functions_and_imports(tmp_path: Path):
    path = _write_module(tmp_path)
    modules = AstScanner(tmp_path).scan([path])
    assert len(modules) == 1
    module = modules[0]
    assert module.classes == 1
    assert module.functions == 1
    assert "ShadBotTrader.core.events" in module.internal_imports
    assert "pandas" in module.external_imports
    assert "numpy" in module.external_imports
    assert "os" not in module.external_imports  # stdlib excluded


def test_derives_module_name_from_path(tmp_path: Path):
    path = _write_module(tmp_path)
    modules = AstScanner(tmp_path).scan([path])
    assert modules[0].name == "ShadBotTrader.sample"


def test_syntax_errors_are_skipped(tmp_path: Path):
    path = tmp_path / "src" / "broken.py"
    path.parent.mkdir(parents=True)
    path.write_text("def broken(:\n", encoding="utf-8")
    assert AstScanner(tmp_path).scan([path]) == []
