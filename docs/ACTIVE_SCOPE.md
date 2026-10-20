# Active scope — 2026-10-20

The active tree keeps only the path the owner asked to inspect:

```text
MetaTrader ingest     src/ShadBotTrader/infrastructure/data/
                      src/ShadBotTrader/data_cli.py
dataset               src/ShadBotTrader/domain/dataset/
                      src/ShadBotTrader/application/services/data_ingestion_service.py
                      src/ShadBotTrader/application/services/dataset_update_service.py
                      src/ShadBotTrader/application/services/training_data_service.py
features              src/ShadBotTrader/infrastructure/feature/
                      src/ShadBotTrader/feature_cli.py
range model           src/ShadBotTrader/infrastructure/ai/
                      src/ShadBotTrader/application/services/dual_model_service.py
                      scripts/run_dual_models.py
                      scripts/train_range_multistep.py
```

Moved, not deleted:

```text
old_version/
```

Not touched:

```text
legacy/
```

`legacy/` is the owner's original code. `old_version/` is the previous full ShadBotTrader. They were not merged.

Shared files that stayed because the range trainer imports them still contain signal/trend label branches. Those branches were not a separate package. Backtest, live, pivot, hybrid, execution, and the GUI were separate and were moved.
