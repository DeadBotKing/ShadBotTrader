# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T15:04:40.780752+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 227
- Test modules: 64

## Current Phase

Phase 28 — Implementation Foundation (Sprint P7: Self-Learning — walk-forward optimisation with a promotion gate)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: be2bcf9679cfea9b515c3367139b4ce0f8b41aa6
- Dirty: yes (476 files)
- Recent commits:
  - be2bcf9 Phase 28 â€” Implementation Foundation (Sprint P5: Execution & Portfolio â€” fill-based accounting)
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 â€” Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1

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

Sprint P8 — Project Intelligence & Persistence (Phases 18, 20): durable storage for datasets, models, journals and learning experiments (currently in-memory), plus a richer self-describing project state. Alternatively Sprint P9 — real market data: a MetaTrader/broker provider behind the existing MarketDataProvider port, so backtests run on genuine price history.

## Statistics

- Total files: 543
- Source files: 227
- Test files: 64
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 65751
- Modules: 291
- Classes: 365
- Functions: 1868
- External dependencies: 11
