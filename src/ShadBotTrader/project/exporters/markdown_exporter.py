"""Writes generated markdown documents to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


class MarkdownExporter:
    """Writes a mapping of filename -> markdown content into a directory."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def export(self, documents: Dict[str, str]) -> None:
        """Write every document in ``documents`` into the output dir."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in documents.items():
            path = self._output_dir / filename
            path.write_text(content, encoding="utf-8")
