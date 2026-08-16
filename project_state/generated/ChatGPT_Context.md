# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-16T10:59:00.959123+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 157
- Test modules: 44

## Current Phase

Phase 28 — Implementation Foundation (Sprint P2: Feature Platform — full 85-feature catalog)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: b5df12b99b2931d9f3733509fb120cf4fdc3fd4c
- Dirty: yes (349 files)
- Recent commits:
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - e9eb8fe Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 â€” Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 â€” Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md
  - ac8c959 Upda
  - 0ddcbe9 Update Docs From Done To No Done

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

Sprint P4 — Trading Platform: strategies, signals, decision and execution abstractions (risk-gated, broker-agnostic).

## Statistics

- Total files: 445
- Source files: 157
- Test files: 44
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 51620
- Modules: 201
- Classes: 192
- Functions: 784
- External dependencies: 9
