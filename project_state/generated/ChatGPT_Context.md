# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T12:13:37.754941+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 178
- Test modules: 50

## Current Phase

Phase 28 — Implementation Foundation (Sprint P4: Trading Platform — risk-gated decision pipeline)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: dcd31ce3c8c0b486bb566c80c7d0316e1e1b8db0
- Dirty: yes (200 files)
- Recent commits:
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 â€” Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md
  - ac8c959 Upda

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

Sprint P5 — Execution Platform: resolve TradingIntent policies into broker orders behind an ExecutionPort (simulated first, broker-agnostic), then Portfolio accounting for realised positions.

## Statistics

- Total files: 474
- Source files: 178
- Test files: 50
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 56047
- Modules: 228
- Classes: 246
- Functions: 1093
- External dependencies: 10
