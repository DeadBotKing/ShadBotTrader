# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T15:47:28.746224+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 235
- Test modules: 70

## Current Phase

Phase 28 - Implementation Foundation (Sprint P8: Persistence - SQLite-backed state that survives restarts)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 4951f42d521c70ba32091be06ed1040cf47280b6
- Dirty: yes (241 files)
- Recent commits:
  - 4951f42 Real Data
  - 9dbcec3 Phase 28 â€” Implementation Foundation (Sprint P7: Self-Learning â€” walk-forward optimisation with a promotion gate)
  - be2bcf9 Phase 28 â€” Implementation Foundation (Sprint P5: Execution & Portfolio â€” fill-based accounting)
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)

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

Sprint P9 - wire persistence into the demos and CLIs by default, then Phase 19 (GUI/API): a read-only dashboard over the stored positions, equity curve, audit trail and learning history - the data is now durable, so it can finally be displayed.

## Statistics

- Total files: 563
- Source files: 235
- Test files: 70
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 70331
- Modules: 305
- Classes: 396
- Functions: 2145
- External dependencies: 12
