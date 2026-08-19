# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-16T12:54:47.690686+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 210
- Test modules: 60

## Current Phase

Phase 28 — Implementation Foundation (Sprint P6: Simulation & Backtesting — deterministic replay)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 22e6743c8c948a0916fc4183319e6b123bd6db72
- Dirty: yes (718 files)
- Recent commits:
  - 22e6743 NewFixSprint02
  - 74c72cf Phase 28 — Implementation Foundation (Sprint P2: Feature Platform — full 85-feature catalog)
  - e9eb8fe Phase 28 — Implementation Foundation (Sprint P2: Feature Platform)
  - 81751ce Phase 28 — Implementation Foundation (Sprint P1: Data Platform)
  - 80cbf5a Phase 28 — Implementation Foundation (Sprint P0: Project Intelligence)
  - e019203 Phase1
  - 28abd28 Delete SHADBOT_ARCHITECTURE_FREEZE_v1.0.md
  - ac8c959 Upda
  - 0ddcbe9 Update Docs From Done To No Done
  - a7c6b62 Docs

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

Sprint P7 — Self-Learning & Optimisation (Phase 17): use backtest results as a feedback signal — parameter search over strategy and risk settings, walk-forward optimisation, and promotion of a candidate configuration only when it beats the incumbent out-of-sample.

## Statistics

- Total files: 517
- Source files: 210
- Test files: 60
- Documentation files: 43
- Legacy files: 175
- Total Python lines: 62392
- Modules: 270
- Classes: 316
- Functions: 1594
- External dependencies: 11
