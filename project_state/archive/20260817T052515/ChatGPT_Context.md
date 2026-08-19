# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-17T05:21:33.545878+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 279
- Test modules: 94

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed (plugin registry, layered config with secret redaction, structured contextual logging)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 8fbd24ede30c3459c660e724766cd16d50e5aa41
- Dirty: yes (382 files)
- Recent commits:
  - 8fbd24e Update Dashboard
  - 98df9b6 Phase 28 - Implementation Foundation (Phase 19: read-only dashboard over persisted state)
  - 715cfce Phase 28 - Implementation Foundation (Sprint P8: Persistence - SQLite-backed state that survives restarts)
  - 4951f42 Real Data
  - 9dbcec3 Phase 28 â€” Implementation Foundation (Sprint P7: Self-Learning â€” walk-forward optimisation with a promotion gate)
  - be2bcf9 Phase 28 â€” Implementation Foundation (Sprint P5: Execution & Portfolio â€” fill-based accounting)
  - 422b7dc Phase 28 â€” Implementation Foundation (Sprint P4: Trading Platform â€” risk-gated decision pipeline)
  - dcd31ce Phase 28 â€” Implementation Foundation (Sprint P2: Feature Platform â€” full 85-feature catalog)
  - b5df12b Create venv.txt
  - 22e6743 NewFixSprint02

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

- Total files: 655
- Source files: 279
- Test files: 94
- Documentation files: 48
- Legacy files: 176
- Total Python lines: 88931
- Modules: 373
- Classes: 565
- Functions: 3283
- External dependencies: 12
