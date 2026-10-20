# Phase159A — Pivot Candidate Geometry Tightening Audit

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase158A showed that the current live-known pivot-zone candidates are too broad and negative-expectancy:

```text
B4 zone-event rate ≈ 90%
B2 zone-event rate ≈ 70%
mean R negative in validation and test
side preference flips from validation to test
```

Phase159A searches tighter live-known geometry before any new model training.

## Implemented executable

```text
scripts/audit_pivot_candidate_geometry_tightening.py
```

## GUI command

```text
Audit pivot candidate geometry tightening
```

## What it searches

Grid over:

```text
payoff target specs: B4 / B2
recent_window_bars
pivot_zone_atr
recent-range top position threshold
recent-range bottom position threshold
exclude both-zone rows
min/max recent range width in ATR
zone logic: and/or
```

A top/SELL candidate is live-known:

```text
near recent high by ATR distance
AND/OR position in recent range is high enough
```

A bottom/BUY candidate is live-known:

```text
near recent low by ATR distance
AND/OR position in recent range is low enough
```

## Outputs

```text
run_logs\pivot_candidate_geometry_tightening\latest.json
run_logs\pivot_candidate_geometry_tightening\latest.html
run_logs\pivot_candidate_geometry_tightening\latest_grid.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_candidate_geometry_tightening.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --targets "B4:24:1.0:0.5;B2:24:1.0:0.75" `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --recent-window-bars 24,48,96 `
  --pivot-zone-atrs 0.05,0.10,0.15,0.20,0.25 `
  --top-position-thresholds 0.85,0.90,0.95 `
  --bottom-position-thresholds 0.15,0.10,0.05 `
  --exclude-both-zones 1,0 `
  --min-range-width-atrs 0,0.5,1.0 `
  --max-range-width-atrs 0 `
  --zone-logic and `
  --same-bar-policy stop_first `
  --timeout-score-mode zero `
  --min-validation-events 50 `
  --min-test-events 50 `
  --max-validation-event-rate 0.35 `
  --max-test-event-rate 0.35 `
  --min-validation-mean-r 0 `
  --min-test-mean-r 0 `
  --score-metric mean_r `
  --storage-root datasets `
  --output-dir run_logs\pivot_candidate_geometry_tightening
```

## Pass/fail logic

A policy must pass validation and test gates:

```text
validation/test event count >= minimum
validation/test event rate <= max event rate
validation/test mean R >= minimum
side preference is stable between validation and test
no mean-R sign flip
```

This phase is still diagnostic. A passing policy would justify a later candidate-modeling phase, not production.

## Execution result

The owner ran Phase159A.

Top-level result:

```text
policies                 : 1620
validation_pass_policies : 0
transfer_pass_policies   : 0
selected_policy_id       : B2|rw=48|zone=0.05|top=0.85|bottom=0.15|exclude_both=1|minw=1|maxw=0
selected_validation_mean_r : -0.0050505050
selected_test_mean_r       : -0.0272277221
selected_validation_PF     : 0.9630
selected_test_PF           : 0.7179
```

Geometry tightening worked as a filter:

```text
candidate event rate fell to ~3% validation/test
side preference was stable: BUY in validation and test
```

But expectancy remained negative:

```text
validation_mean_r < 0
test_mean_r < 0
transfer_pass_gate = 0
```

Decision:

```text
Do not train on this geometry.
```

Recommended next phase:

```text
Phase160A — Pivot Candidate Side-Mapping / Counterfactual Direction Audit
```

## Verification

```text
python -m py_compile scripts/audit_pivot_candidate_geometry_tightening.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_candidate_geometry_tightening.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_candidate_geometry_tightening.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 52 passed
```
