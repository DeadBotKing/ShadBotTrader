# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-16T14:32:14.575020+00:00

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
- Commit: 22e6743c8c948a0916fc4183319e6b123bd6db72
- Dirty: yes (1516 files)
- Recent commits:
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 — Implementation Foundation (Sprint P2: Feature Platform — full 85-feature catalog)
  - e9eb8fe Phase 28 — Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 — Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 — Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md
  - ac8c959 Upda
  - 0ddcbe9 Update Docs From Done To No Done
  - a7c6b62 Docs

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

- Total files: 547
- Source files: 228
- Test files: 66
- Documentation files: 43
- Legacy files: 175
- Total Python lines: 66915
- Modules: 294
- Classes: 376
- Functions: 1943
- External dependencies: 12
