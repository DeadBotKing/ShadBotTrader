"""Builds generated architecture documentation from the snapshot."""

from __future__ import annotations

from collections import Counter

from ShadBotTrader.project.models.project_snapshot import ProjectSnapshot


class DocumentationBuilder:
    """Produces the generated ``Architecture.md`` document."""

    def build(self, snapshot: ProjectSnapshot) -> str:
        """Render the architecture document for ``snapshot``."""
        layers = self._layer_summary(snapshot)
        return "\n".join(
            [
                "# ShadBotTrader — Architecture (generated)",
                "",
                f"> Generated {snapshot.generated_at}",
                f"> Architecture version: {snapshot.architecture_version}",
                "",
                "## Layers",
                "",
                layers,
                "",
                "## Dependency rules",
                "",
                "- domain depends on nothing else (framework-independent)",
                "- core depends only on core",
                "- application depends on core + domain",
                "- infrastructure depends on core + application",
                "- tests may depend on everything",
                "",
                "## Quality gate",
                "",
                "```bash",
                "python -m black --check .",
                "python -m ruff check .",
                "python -m mypy src",
                "python -m pytest",
                "```",
            ]
        )

    @staticmethod
    def component_summary(snapshot: ProjectSnapshot) -> str:
        """List the top-level packages of the source tree."""
        packages = sorted(
            {
                module.name.split(".", 1)[0]
                for module in snapshot.modules
                if module.path.startswith("src/")
            }
        )
        if not packages:
            return "- (no source packages detected)"
        return "\n".join(f"- {package}" for package in packages)

    @staticmethod
    def _layer_summary(snapshot: ProjectSnapshot) -> str:
        counts: Counter[str] = Counter()
        for module in snapshot.modules:
            if not module.path.startswith("src/"):
                continue
            layer = module.name.split(".", 1)[0] if "." in module.name else module.name
            counts[layer] += 1
        lines = []
        for layer, count in sorted(counts.items()):
            lines.append(f"- {layer}: {count} modules")
        if not lines:
            lines.append("- (no source modules detected)")
        return "\n".join(lines)
