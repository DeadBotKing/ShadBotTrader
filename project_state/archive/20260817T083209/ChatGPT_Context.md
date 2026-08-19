# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-17T08:28:49.349734+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 288
- Test modules: 101

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 22e6743c8c948a0916fc4183319e6b123bd6db72
- Dirty: yes (2362 files)
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

Model quality: the backtester still uses MomentumPredictionSource, a deliberate baseline — the replay now makes every one of its trades visible, and on random data they all lose. Feeding the trained WaveNet and the 109-feature catalogue into the simulation is the remaining path to a strategy that could be profitable, on real MT5 data rather than noise. Alternatively Phase 24 (deployment) to run continuously.

## Statistics

- Total files: 674
- Source files: 288
- Test files: 101
- Documentation files: 51
- Legacy files: 175
- Total Python lines: 94708
- Modules: 389
- Classes: 618
- Functions: 3623
- External dependencies: 12
