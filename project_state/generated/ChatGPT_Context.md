# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T15:38:02.526395+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 228
- Test modules: 66

## Current Phase

Phase 28 — Implementation Foundation (Sprint P7: Self-Learning — walk-forward optimisation with a promotion gate)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 9dbcec3364bdee503ad97dace4a2f6e9fe9fdcee
- Dirty: yes (357 files)
- Recent commits:
  - 9dbcec3 Phase 28 â€” Implementation Foundation (Sprint P7: Self-Learning â€” walk-forward optimisation with a promotion gate)
  - be2bcf9 Phase 28 â€” Implementation Foundation (Sprint P5: Execution & Portfolio â€” fill-based accounting)
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 â€” Implementation Foundation (Sprint P0: Project Intelligence)

## Quality Gate

Run from the repository root:
```bash
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```

## Known Issues

- None recorded for the current foundation.

## Next Phase

Sprint P8 — Persistence (Phase 20): datasets are on disk as Parquet, but model registries, journals, learning memory and experiments are still in-memory and vanish between runs. Durable storage is the prerequisite for tracking real results over time.

## Statistics

- Total files: 550
- Source files: 228
- Test files: 66
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 67190
- Modules: 294
- Classes: 376
- Functions: 1943
- External dependencies: 12
