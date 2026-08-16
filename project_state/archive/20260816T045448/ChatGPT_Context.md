# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-15T17:21:54.122615+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 130
- Test modules: 35

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

Sprint P3 — AI Platform: model registry, training runs and prediction serving (Wavenet, roll-forward).

## Statistics

- Total files: 392
- Source files: 130
- Test files: 35
- Documentation files: 43
- Legacy files: 176
- Total Python lines: 48375
- Modules: 165
- Classes: 149
- Functions: 631
- External dependencies: 7
