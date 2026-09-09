# ShadBotTrader — Architecture (generated)

> Generated 2026-09-09T05:51:39.113398+00:00
> Architecture version: 1.0

## Layers

- ShadBotTrader: 320 modules

## Dependency rules

- domain depends on nothing else (framework-independent)
- core depends only on core
- application depends on core + domain
- infrastructure depends on core + application
- tests may depend on everything

## Quality gate

```bash
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```