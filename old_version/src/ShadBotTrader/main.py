"""Entrypoint of the ShadBotTrader platform.

Run with: ``python -m ShadBotTrader.main`` (after installing the package
or with ``src`` on ``PYTHONPATH``).
"""

from __future__ import annotations

import sys

from ShadBotTrader.application.bootstrap import Bootstrap
from ShadBotTrader.application.runtime import Runtime


def main() -> int:
    """Boot the application, run it and return the process exit code."""
    application = Bootstrap().build()
    runtime = Runtime(application)
    return runtime.run()


if __name__ == "__main__":
    sys.exit(main())
