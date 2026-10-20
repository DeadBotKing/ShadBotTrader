"""CLI entrypoint for the Project Intelligence Platform.

Run with: ``python -m ShadBotTrader.intelligence``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ShadBotTrader.project.runtime.intelligence_runtime import IntelligenceRuntime


def main(argv: list[str] | None = None) -> int:
    """Run the intelligence pipeline and print a summary."""
    parser = argparse.ArgumentParser(description="ShadBotTrader Project Intelligence")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Root of the project to analyse (default: current directory)",
    )
    args = parser.parse_args(argv)

    snapshot = IntelligenceRuntime(args.project_root).run()

    stats = snapshot.statistics
    print("Project Intelligence scan complete.")
    print(f"  project       : {snapshot.project_name}")
    print(f"  phase         : {snapshot.current_phase}")
    print(f"  git commit    : {snapshot.git.commit or 'n/a'}")
    print(f"  source files  : {stats.source_file_count}")
    print(f"  test files    : {stats.test_file_count}")
    print(f"  modules       : {stats.module_count}")
    print(f"  total lines   : {stats.total_lines}")
    print(f"  dependencies  : {stats.external_dependency_count}")
    print("Generated state written to project_state/generated/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
