"""Run the Project Intelligence pipeline without installing the package.

Adds ``src/`` to ``sys.path`` so the command works from a plain checkout:

    python scripts/run_pip.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.intelligence import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--project-root", str(REPO_ROOT)]))
