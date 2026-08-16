# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-16T05:51:29.800791+00:00

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
- Commit: 28abd280926d6219b02019b2a07533dadc36d6ed
- Dirty: yes (185 files)
- Recent commits:
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md
  - ac8c959 Upda
  - 0ddcbe9 Update Docs From Done To No Done
  - a7c6b62 Docs
  - 97d8f00 Update .gitignore
  - 61be191 New
  - 93bf423 gitignore
  - c6816ec Initial commit

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

- Total files: 429
- Source files: 157
- Test files: 44
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 51379
- Modules: 201
- Classes: 192
- Functions: 776
- External dependencies: 8
