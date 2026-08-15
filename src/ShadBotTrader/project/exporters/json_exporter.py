"""Writes generated JSON documents to disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JsonExporter:
    """Writes a mapping of filename -> data as pretty-printed JSON."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def export(self, documents: Dict[str, Any]) -> None:
        """Write every document in ``documents`` into the output dir."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        for filename, data in documents.items():
            path = self._output_dir / filename
            path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
