# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-15T16:03:33.379938+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 73
- Test modules: 18

## Current Phase

Phase 28 — Implementation Foundation (Sprint P0: Project Intelligence)

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

Sprint P1 — Data Platform: market-data ingestion, validation, normalisation and dataset storage (L0 → L3).

## Statistics

- Total files: 316
- Source files: 73
- Test files: 18
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 42631
- Modules: 91
- Classes: 74
- Functions: 319
- External dependencies: 3
