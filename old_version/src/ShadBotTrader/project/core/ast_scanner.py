"""Parses Python source and extracts modules, symbols and imports."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import List

from ShadBotTrader.project.models.project_snapshot import ModuleInfo

_STDLIB = frozenset(getattr(sys, "stdlib_module_names", frozenset()))

_INTERNAL_PREFIXES = ("ShadBotTrader", "src")


class AstScanner:
    """Extracts static structure from the project's Python modules."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root

    def scan(self, python_files: List[Path]) -> List[ModuleInfo]:
        """Parse ``python_files`` and return one ``ModuleInfo`` per file."""
        modules: List[ModuleInfo] = []
        for path in sorted(python_files):
            module = self._inspect(path)
            if module is not None:
                modules.append(module)
        return modules

    def _inspect(self, path: Path) -> ModuleInfo | None:
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

        classes = 0
        functions = 0
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        internal: set[str] = set()
        external: set[str] = set()
        for module_name in imports:
            if self._is_internal(module_name):
                internal.add(module_name)
            else:
                top_level = module_name.split(".", 1)[0]
                if top_level and top_level not in _STDLIB:
                    external.add(top_level)

        relative = path.relative_to(self._root).as_posix()
        module_name = self._derive_module_name(relative)
        return ModuleInfo(
            path=relative,
            name=module_name,
            classes=classes,
            functions=functions,
            internal_imports=sorted(internal),
            external_imports=sorted(external),
        )

    @staticmethod
    def _is_internal(module_name: str) -> bool:
        top_level = module_name.split(".", 1)[0]
        return top_level in _INTERNAL_PREFIXES or module_name.startswith(_INTERNAL_PREFIXES)

    @staticmethod
    def _derive_module_name(relative_path: str) -> str:
        path = relative_path
        for prefix in ("src/", "tests/"):
            if path.startswith(prefix):
                path = path[len(prefix) :]
        if path.endswith(".py"):
            path = path[: -len(".py")]
        if path.endswith("__init__"):
            path = path[: -len("__init__")].rstrip("/.")
        return path.replace("/", ".") or "<root>"
