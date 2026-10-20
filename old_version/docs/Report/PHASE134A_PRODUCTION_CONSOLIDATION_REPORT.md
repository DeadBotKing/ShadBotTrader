# Phase134A Report — Production Consolidation / Paper Shadow Scaffold

Date: 2026-09-09

## Goal

Start reducing research complexity into a narrow, guarded production-style path without enabling real-money execution.

The user concern was explicit: code is getting complex, and if the model stack works the online robot must be cleanly assembled.

## Implemented files

```text
src/ShadBotTrader/application/services/hybrid_production_service.py
scripts/validate_production_hybrid_stack.py
scripts/run_hybrid_paper_shadow.py
tests/unit/services/test_hybrid_production_service.py
tests/unit/ai/test_hybrid_production_scripts.py
```

GUI:

```text
Validate production hybrid stack
Run hybrid paper shadow
```

## Production config

The selected stack is frozen in:

```text
configs/hybrid_production_stack.json
```

The config records:

```text
base model id/version
optional meta model id/version/type
range_1d/range_4h model ids/versions
telemetry flat/tensor paths
telemetry schema hash
position sizing
risk limits
paper/live mode
live safety confirmations
```

## Safety gates

Live mode is impossible unless all are true:

```text
paper_shadow_passed
account_profile_confirmed
symbol_mapping_confirmed
kill_switch_enabled
explicit_live_confirm == ENABLE_REAL_HYBRID_TRADING
risk limits present
position size positive
schema hash known/matching
```

The paper shadow script refuses live mode and never sends broker orders.

## Commands

Validate/freeze paper-shadow config:

```powershell
python -u scripts/validate_production_hybrid_stack.py `
  --mode paper_shadow `
  --symbol XAUUSD `
  --timeframe 5M `
  --base-model-id gold_hybrid_lightgbm_head_5m `
  --base-model-version 0 `
  --meta-model-type none `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --position-size-units 0.1 `
  --initial-capital 100 `
  --kill-switch-enabled 1 `
  --write-config 1 `
  --require-models 0 `
  --storage-root datasets
```

Run paper shadow:

```powershell
python -u scripts/run_hybrid_paper_shadow.py `
  --config-path configs\hybrid_production_stack.json `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allow-validation-fail 0 `
  --storage-root datasets
```

## Outputs

```text
run_logs/hybrid_production_validation/latest.json
run_logs/hybrid_paper_shadow/latest.json
run_logs/hybrid_paper_shadow/latest.csv
run_logs/hybrid_paper_shadow/latest.html
```

## Important limitation

Phase134A is not permission to trade live. It is a consolidation scaffold. Real MT5 order submission remains blocked until Phase133 produces an acceptable candidate and Phase115 live decision audit / paper shadow succeeds.
