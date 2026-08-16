# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T16:04:21.201987+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 244
- Test modules: 73

## Current Phase

Phase 28 - Implementation Foundation (Phase 19: read-only dashboard over persisted state)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 715cfceb22cad43a52d55148e72f04e3cdea7c7d
- Dirty: yes (241 files)
- Recent commits:
  - 715cfce Phase 28 - Implementation Foundation (Sprint P8: Persistence - SQLite-backed state that survives restarts)
  - 4951f42 Real Data
  - 9dbcec3 Phase 28 â€” Implementation Foundation (Sprint P7: Self-Learning â€” walk-forward optimisation with a promotion gate)
  - be2bcf9 Phase 28 â€” Implementation Foundation (Sprint P5: Execution & Portfolio â€” fill-based accounting)
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)

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

Wire persistence into the remaining demos and CLIs with a --persist flag, so backtests and optimisations land in the database and show up on the dashboard without extra wiring. After that: Phase 24 (deployment) or richer charts once per-bar equity is stored.

## Statistics

- Total files: 579
- Source files: 244
- Test files: 73
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 72531
- Modules: 317
- Classes: 416
- Functions: 2255
- External dependencies: 12
