"""Standard health checks for a ShadBotTrader deployment (Phase 24).

Lives in infrastructure, not the domain: assembling the real checks
means knowing about SQLite, TensorFlow and MetaTrader 5, and the domain
must stay free of all three. ``HealthMonitor`` itself is pure domain —
this module only wires concrete probes into it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ShadBotTrader.domain.deployment.health import DependencyKind, HealthMonitor


def default_monitor(
    version: str = "",
    environment: str = "",
    database_path: Optional[str] = None,
    storage_root: Optional[str] = None,
) -> HealthMonitor:
    """The standard checks for a ShadBotTrader deployment.

    Only things that can genuinely fail are checked. A check that can
    never fail is noise in a health report.
    """

    monitor = HealthMonitor(version=version, environment=environment)

    monitor.register(
        "python_runtime",
        lambda: (True, f"{__import__('sys').version.split()[0]}"),
        DependencyKind.CRITICAL,
    )

    if database_path:

        def database_check() -> tuple[bool, str]:
            path = Path(database_path)
            if not path.exists():
                return False, f"missing: {path}"
            import sqlite3

            connection = sqlite3.connect(str(path))
            try:
                connection.execute("SELECT 1").fetchone()
            finally:
                connection.close()
            return True, f"{path.stat().st_size / 1024:.0f} KB"

        monitor.register("database", database_check, DependencyKind.CRITICAL)

    if storage_root:

        def storage_check() -> tuple[bool, str]:
            path = Path(storage_root)
            if not path.exists():
                return False, f"missing: {path}"
            probe = path / ".write_probe"
            try:
                probe.write_text("ok", encoding="utf-8")
                probe.unlink()
            except OSError as error:
                return False, f"not writable: {error}"
            return True, str(path)

        monitor.register("storage", storage_check, DependencyKind.CRITICAL)

    def tensorflow_check() -> tuple[bool, str]:
        try:
            import tensorflow as tf
        except ImportError:
            return False, "not installed — AI training unavailable"
        return True, tf.__version__

    monitor.register("tensorflow", tensorflow_check, DependencyKind.OPTIONAL)

    def mt5_check() -> tuple[bool, str]:
        from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5

        if not mt5.is_available():
            return False, "not installed — live broker data unavailable"
        return True, "package available"

    monitor.register("metatrader5", mt5_check, DependencyKind.OPTIONAL)

    return monitor
