"""Composes scanner output into a single ProjectSnapshot."""

from __future__ import annotations

import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ShadBotTrader.project.builders.statistics_builder import StatisticsBuilder
from ShadBotTrader.project.core.ast_scanner import AstScanner
from ShadBotTrader.project.core.config_scanner import ConfigScanner
from ShadBotTrader.project.core.git_scanner import GitScanner
from ShadBotTrader.project.core.project_scanner import ProjectScanner
from ShadBotTrader.project.models.project_snapshot import (
    DependencyInfo,
    ProjectSnapshot,
)

ARCHITECTURE_VERSION = "1.0"
CURRENT_PHASE = (
    "Phase 28 - Implementation Foundation "
    "+ Phases 29-31 (dual models, 100k dataset, live loop) "
    "+ Phase 24 Deployment + Phases 9/21/22 completed "
    "+ Phase 32 (multi-account profiles, per-broker symbol mapping, "
    "every run driven from the GUI) + Phase 33 (incremental dataset "
    "updates with learned market calendar and gap backfill) "
    "+ Phase 34 (candlestick chart and dataset inspection at /data) "
    "+ Phase 35 (two separate 5M/1H training datasets, rows trimmed only "
    "from the ends, generated candles never stored under a real symbol, "
    "one canonical symbol per instrument) "
    "+ Phase 36 (live training progress in the console and the dashboard, "
    "per-fold metrics reported against a majority-class baseline) "
    "+ Phase 37 (live feature-computation progress, and one feature "
    "store per symbol/timeframe instead of a shared directory) "
    "+ Phase 38 (features reused until the candle fingerprint changes, "
    "then fully recomputed; the training matrix is 14 candle columns "
    "plus all 109 catalogue features) "
    "+ Phase 39 (the training matrix reads stored features and is proven "
    "byte-identical to the computed one; the 1D timeframe has its own "
    "candles, features, dataset and range model; the operator chooses "
    "which model trains on which dataset) "
    "+ Phase 40 (model type, dataset and saved model are dropdowns; "
    "trained models are persisted with the role and dataset that "
    "produced them; retraining adds a version instead of replacing one) "
    "+ Phases 41-48 (streamed training, capped progress lines, batch "
    "count from fold geometry, batch size scaled to the data, a signal "
    "threshold field and a live broker spread, per-epoch checkpoints, "
    "the best epoch kept rather than the last, and buttons to test a "
    "model on a dataset and inspect a dataset) "
    "+ Phase 49 (a signal model records the neutral band it was trained "
    "with, and evaluation rebuilds the labels with that band instead of "
    "a hard-coded 0.08%)"
)


class SnapshotBuilder:
    """Runs all scanners and assembles the canonical ProjectSnapshot."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._project_scanner = ProjectScanner(project_root)
        self._ast_scanner = AstScanner(project_root)
        self._git_scanner = GitScanner(project_root)
        self._config_scanner = ConfigScanner(project_root)
        self._statistics_builder = StatisticsBuilder(project_root)

    def build(self) -> ProjectSnapshot:
        """Run the full scan and build the snapshot."""
        files = self._project_scanner.scan()
        python_files = [
            self._root / file.path
            for file in files
            if file.path.endswith(".py") and file.category in ("source", "test")
        ]
        modules = self._ast_scanner.scan(python_files)
        dependencies = self._build_dependencies(modules)
        statistics = self._statistics_builder.build(files, modules)
        configuration = self._config_scanner.scan()
        git = self._git_scanner.scan()

        project_name = configuration.name or "ShadBotTrader"

        return ProjectSnapshot(
            project_name=project_name,
            architecture_version=ARCHITECTURE_VERSION,
            current_phase=CURRENT_PHASE,
            generated_at=datetime.now(timezone.utc).isoformat(),
            python_version=platform.python_version(),
            git=git,
            files=files,
            modules=modules,
            dependencies=dependencies,
            statistics=statistics,
        )

    @staticmethod
    def _build_dependencies(modules: List) -> List[DependencyInfo]:
        usage: Counter[str] = Counter()
        for module in modules:
            for external in set(module.external_imports):
                usage[external] += 1
        return [
            DependencyInfo(name=name, used_by=count)
            for name, count in sorted(usage.items(), key=lambda item: (-item[1], item[0]))
        ]
