# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-15T16:43:09.729258+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 122
- Test modules: 34

## Current Phase

Phase 28 — Implementation Foundation (Sprint P2: Feature Platform)

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

Sprint P3 — AI Platform: model registry, training runs and prediction serving (Wavenet, roll-forward).

## Statistics

- Total files: 383
- Source files: 122
- Test files: 34
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 47291
- Modules: 156
- Classes: 141
- Functions: 596
- External dependencies: 5
