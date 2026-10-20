"""Architecture tests: enforce the frozen dependency direction.

Rules verified here:

* ``core`` must not depend on ``domain`` / ``application`` /
  ``infrastructure``.
* ``domain`` must stay framework-independent: it must not depend on
  ``core`` / ``application`` / ``infrastructure``.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "ShadBotTrader"

FORBIDDEN_BY_LAYER = {
    "core": {
        "ShadBotTrader.domain",
        "ShadBotTrader.application",
        "ShadBotTrader.infrastructure",
    },
    "domain": {
        "ShadBotTrader.core",
        "ShadBotTrader.application",
        "ShadBotTrader.infrastructure",
    },
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _python_files(layer: str) -> list[Path]:
    return sorted((SRC / layer).rglob("*.py"))


def _violations(layer: str) -> list[str]:
    forbidden = FORBIDDEN_BY_LAYER[layer]
    found: list[str] = []
    for path in _python_files(layer):
        for module in _imported_modules(path):
            for prefix in forbidden:
                if module == prefix or module.startswith(prefix + "."):
                    found.append(f"{path.name}: imports {module}")
    return found


def test_core_does_not_depend_on_outer_layers():
    assert _violations("core") == []


def test_domain_is_framework_independent():
    assert _violations("domain") == []
