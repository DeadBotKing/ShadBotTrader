# Phase172A — Broker-cost-aware 1H Target-family Design Audit

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

Phase171A selected the next research route:

```text
NEW_1H_COST_AWARE_TARGET_FAMILY
```

The previous 1H locked rule was rejected, but Phase170A captured real broker spread and showed that future 1H research should use broker-realistic cost from the start:

```text
Alpari XAUUSD_i spread median ≈ 0.39
p90 ≈ 0.40
p99 ≈ 0.41
```

Phase172A therefore audits new 1H target families under broker-cost assumptions before any model training.

## Implemented executable

```text
scripts/audit_broker_cost_aware_1h_target_family.py
```

## GUI command

```text
Audit broker-cost-aware 1H target family
```

## Default target families

Format:

```text
ID:label:mapping:delay:rw:zone:top:bottom:exclude:minw:maxw:tp:sl:hold
```

Default candidates:

```text
CA1_BRK_MID    : breakout, delay=1, rw=24, zone=0.10, TP/SL=2.0/1.0, hold=24
CA2_BRK_WIDE   : breakout, delay=1, rw=48, zone=0.10, TP/SL=2.5/1.25, hold=48
CA3_BRK_STRICT : breakout, delay=1, rw=24, zone=0.05, top=0.90, bottom=0.10, TP/SL=2.0/1.0, hold=24
CA4_REV_MID    : reversal, delay=1, rw=24, zone=0.10, TP/SL=1.5/1.0, hold=24
```

## Cost assumptions

```text
primary spread : fixed 0.4
stress spread  : fixed 0.5
```

These are based on the Phase170A broker spread sample.

## What it audits

For each target family:

```text
1. live-known candidate geometry
2. broker-cost-aware first-hit/replay labels:
   POSITIVE
   NEGATIVE
   TIMEOUT
3. split label density and positive/negative/timeout rates
4. label PSI validation/test vs train
5. independent score/PF
6. simple chronological replay metrics
7. stress spread behavior
8. rolling walk-forward label stability
```

## Gates

Default gates:

```text
min_train_events             : 100
min_validation_events        : 20
min_test_events              : 20
min_positive_rate            : 0.10
max_positive_rate            : 0.70
max_label_psi                : 0.20
min_walkforward_folds        : 5
min_walkforward_pass_ratio   : 0.50
```

A family is training-ready only if:

```text
density_gate = 1
label_stability_gate = 1
stress_gate = 1
walkforward_gate = 1
```

## Outputs

```text
run_logs\broker_cost_aware_1h_target_family\latest.json
run_logs\broker_cost_aware_1h_target_family\latest.html
run_logs\broker_cost_aware_1h_target_family\latest_candidates.csv
run_logs\broker_cost_aware_1h_target_family\latest_splits.csv
run_logs\broker_cost_aware_1h_target_family\latest_walkforward.csv
run_logs\broker_cost_aware_1h_target_family\latest_events.csv
```

## Recommended GUI action

Use the Dashboard command:

```text
Audit broker-cost-aware 1H target family
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_broker_cost_aware_1h_target_family.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48;CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;CA4_REV_MID:cost_reversal_mid:reversal:1:24:0.10:0.85:0.15:1:1.0:0:1.5:1.0:24" `
  --spread-mode fixed `
  --spread-value 0.4 `
  --stress-spread-value 0.5 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --max-folds 0 `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --min-train-events 100 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --storage-root datasets `
  --output-dir run_logs\broker_cost_aware_1h_target_family `
  --report-title "Phase172A broker-cost-aware 1H target-family design audit"
```

## Decision after owner run

If `target_family_ready_for_training_gate=1`, the next phase may propose a model-training design around the selected target family. It still does not approve paper/live.

If no family passes, do not train a model and move to the secondary research route from Phase171A, likely hybrid/regime-first redesign.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_broker_cost_aware_1h_target_family.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/ai/test_research_route_redesign_decision_matrix.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase172A on the full local 1H dataset.

Top-level:

```text
candidate_families                    : 4
ready_families                        : 3
selected_family_id                    : CA1_BRK_MID
selected_family_ready_gate            : 1
target_family_ready_for_training_gate : 1
spread_value                          : fixed 0.4
stress_spread_value                   : fixed 0.5
```

Ready families:

```text
CA1_BRK_MID    : ready, selected primary
CA3_BRK_STRICT : ready, backup/comparison
CA2_BRK_WIDE   : ready, backup/comparison
```

Rejected family:

```text
CA4_REV_MID : rejected because stress_gate=0 and weak economic diagnostics
```

Important caution:

```text
CA1 is structurally target-ready, not a standalone profitable rule.
CA1 train_chrono_pf=0.8453 and train_independent_pf=0.8623 are negative.
Therefore no production/paper/live and no direct model training yet.
```

Decision:

```text
Proceed only to Phase173A — Broker-cost-aware 1H Target Learnability / Dataset Build Audit.
```
