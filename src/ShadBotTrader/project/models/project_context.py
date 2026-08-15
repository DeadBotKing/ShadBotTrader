"""The portable ChatGPT/handoff context assembled from a snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class ProjectContext:
    """The sections of the generated ``ChatGPT_Context.md`` document.

    ``sections`` maps a section title to its markdown body. The order of
    the mapping is preserved because it is built with an ``OrderedDict``.
    """

    sections: Dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render the context as a single markdown document."""
        parts: list[str] = ["# ChatGPT Context — ShadBotTrader\n"]
        for title, body in self.sections.items():
            parts.append(f"\n## {title}\n")
            parts.append(body.strip())
        return "\n".join(parts) + "\n"
