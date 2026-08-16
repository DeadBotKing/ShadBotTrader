# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T12:40:06.741861+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 194
- Test modules: 55

## Current Phase

Phase 28 — Implementation Foundation (Sprint P5: Execution & Portfolio — fill-based accounting)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 422b7dcdd01876b113b043c0af35c1917e8fbab6
- Dirty: yes (242 files)
- Recent commits:
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 â€” Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md

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

Sprint P6 — Simulation & Backtesting (Phase 16): drive the data -> feature -> prediction -> decision -> execution chain over historical candles on a deterministic clock, and report performance metrics (equity curve, drawdown, hit rate, profit factor).

## Statistics

- Total files: 497
- Source files: 194
- Test files: 55
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 59433
- Modules: 249
- Classes: 284
- Functions: 1343
- External dependencies: 10
