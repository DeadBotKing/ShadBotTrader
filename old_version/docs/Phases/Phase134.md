# Phase134 — Production Consolidation / Online Bot Assembly

**Status:** ✅ Phase134A implemented
**Type:** Architecture cleanup / live-path simplification
**Priority:** only after Phase133 passes

---

## Goal

If the research path produces a robust model, consolidate the work into a clean online trading path that can run the robot without dragging all research scripts into live execution.

The user concern is valid:

```text
code is getting complex
```

This phase exists to keep complexity out of the final bot.

---

## Rule

Research code may be broad and experimental. Production live code must be narrow:

```text
one selected model stack
one selected config
one decision service
one audit log schema
one MT5 execution adapter path
```

No live system should call threshold-search scripts or training scripts.

---

## Production stack candidate

Only after validation, the selected stack may be:

```text
selected base hybrid head
selected meta-filter / score model
range_1d
range_4h
chronological single-position position manager
risk policy
MT5 execution adapter
```

---

## Expected final runtime flow

```text
new 5M candle / live quote
→ update 5M/4H/1D buffers
→ build online-safe Phase127 feature window
→ score selected model(s)
→ build candidate TP/SL from range_4h/range_1d
→ apply meta-filter and risk policy
→ if approved: create TradingIntent
→ execution adapter submits MT5 order
→ audit every TRADE/NO_TRADE
```

---

## Files likely involved

Do not redesign architecture. Extend existing layers:

```text
Domain:
  strategy value objects / signal context only if necessary

Application:
  live decision / orchestration service

Infrastructure:
  online telemetry feature builder
  selected model predictor adapter
  MT5 execution adapter integration

Presentation:
  GUI command/status/audit view
```

Research scripts remain under:

```text
scripts/
```

but production should use application/infrastructure services, not script glue.

---

## Consolidation tasks

```text
1) Freeze selected model IDs and versions.
2) Freeze selected thresholds/config in one JSON/YAML config.
3) Create one online feature builder matching Phase127 exactly.
4) Create one live decision service path.
5) Create one paper/shadow mode.
6) Create one real-execution switch guarded by safety checks.
7) Write clear logs for every decision.
8) Remove duplicate/obsolete GUI paths from operator workflow if needed.
```

---

## Safety gates

Real-money execution must be impossible unless all are true:

```text
paper_shadow_passed = true
account_profile_confirmed = true
symbol_mapping_confirmed = true
max_daily_loss configured
max_open_positions configured
position_size configured
kill_switch available
```

---

## Acceptance criteria

```text
- One documented production command path.
- No training/backtest script is used in live order submission.
- Online features match training features by schema hash.
- Decision audit contains model inputs, probabilities, thresholds, TP, SL and reason.
- Paper mode runs before live mode.
- Real execution is behind explicit operator confirmation and risk gates.
```

---

## Next phase

After this consolidation, run the already-planned:

```text
Phase115 — Live decision audit / paper shadow
```

Only after that can real MT5 order execution be considered.

---

## GUI/operator execution requirement

Production consolidation هم باید operator-facing باشد. اگر این فاز به اجرای paper/live منتهی شود، همهٔ entry pointها باید command واضح در GUI داشته باشند.

حداقل commandهای لازم:

```text
CommandKind.VALIDATE_PRODUCTION_HYBRID_STACK
Dashboard label: Validate production hybrid stack
Handler: runs scripts/validate_production_hybrid_stack.py

CommandKind.RUN_HYBRID_PAPER_SHADOW
Dashboard label: Run hybrid paper shadow
Handler/application service: runs selected production stack without real orders
```

اگر روزی real execution فعال شود، باید command جداگانه و محافظت‌شده داشته باشد:

```text
CommandKind.RUN_HYBRID_LIVE_TRADING
```

اما فقط بعد از safety gates و تأیید صریح اپراتور.

GUI باید نشان دهد:

```text
selected model ids/versions
schema hash
paper/live mode
symbol mapping
position sizing
max daily loss
kill switch status
last decision audit
```

هیچ مسیر production/live نباید فقط CLI باشد.

---

## Phase134A implementation status

Implemented files:

```text
src/ShadBotTrader/application/services/hybrid_production_service.py
scripts/validate_production_hybrid_stack.py
scripts/run_hybrid_paper_shadow.py
```

GUI commands:

```text
Validate production hybrid stack
Run hybrid paper shadow
```

Tests:

```text
tests/unit/services/test_hybrid_production_service.py
tests/unit/ai/test_hybrid_production_scripts.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
```

Implemented config:

```text
configs/hybrid_production_stack.json
```

The validation script can write/freeze the config with the current telemetry schema hash.

---

## Safety gates implemented

Paper/shadow mode requires:

```text
mode_supported
base_model_selected
range_models_selected
position_size_positive
initial_capital_positive
risk_limits_present
kill_switch_enabled
schema_hash_known
schema_hash_matches_config if an expected hash is set
```

Live mode additionally requires:

```text
paper_shadow_passed
account_profile_confirmed
symbol_mapping_confirmed
explicit_live_confirm == ENABLE_REAL_HYBRID_TRADING
```

`run_hybrid_paper_shadow.py` never runs live mode and never sends real broker orders.

---

## Validation command

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
  --max-daily-loss-percent 5 `
  --max-open-positions 1 `
  --position-size-units 0.1 `
  --initial-capital 100 `
  --kill-switch-enabled 1 `
  --write-config 1 `
  --require-models 0 `
  --storage-root datasets
```

If Phase133 later selects a flat meta model, use:

```powershell
python -u scripts/validate_production_hybrid_stack.py `
  --mode paper_shadow `
  --symbol XAUUSD `
  --timeframe 5M `
  --base-model-id gold_hybrid_lightgbm_head_5m `
  --base-model-version 0 `
  --meta-model-type flat `
  --meta-model-id gold_hybrid_meta_lightgbm_5m `
  --meta-model-version 0 `
  --decision-mode meta `
  --meta-threshold 0.55 `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --position-size-units 0.1 `
  --initial-capital 100 `
  --kill-switch-enabled 1 `
  --write-config 1 `
  --require-models 1 `
  --storage-root datasets
```

Output:

```text
run_logs/hybrid_production_validation/latest.json
```

---

## Paper shadow command

```powershell
python -u scripts/run_hybrid_paper_shadow.py `
  --config-path configs\hybrid_production_stack.json `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allow-validation-fail 0 `
  --storage-root datasets
```

Outputs:

```text
run_logs/hybrid_paper_shadow/latest.json
run_logs/hybrid_paper_shadow/latest.csv
run_logs/hybrid_paper_shadow/latest.html
```

---

## Limitations

```text
- This is consolidation scaffolding, not real execution.
- run_hybrid_paper_shadow.py supports base mode and flat meta models first.
- Tensor meta models remain research candidates until Phase133 validates a selected stack.
- Real MT5 order submission is still blocked until Phase115 paper/live audit succeeds.
```
