# Phase173A — Broker-cost-aware 1H Target Learnability / Dataset Build Audit

## Status

```text
COMPLETED — owner run failed learnability gates
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```


## Owner execution result — 2026-10-01

Phase173A was run on the full 1H XAUUSD dataset with fixed broker spread `0.4`.

Top-level result:

```text
candidate_families             : 3
learnable_families             : 0
selected_family_id             : CA3_BRK_STRICT
selected_family_ready_gate     : 0
target_learnability_ready_gate : 0
production_status              : BLOCKED — Phase173A target learnability audit only
```

Family outcomes:

```text
CA3_BRK_STRICT: validation_ap_lift=-0.0460, test_ap_lift=+0.1219, balanced_accuracy=0.5000/0.5000, walkforward_pass=0/6
CA1_BRK_MID   : validation_ap_lift=-0.0397, test_ap_lift=+0.0305, balanced_accuracy=0.4448/0.5018, walkforward_pass=0/6
CA2_BRK_WIDE  : validation_ap_lift=-0.0208, test_ap_lift=+0.0191, balanced_accuracy=0.5024/0.5000, walkforward_pass=0/6
```

Interpretation:

```text
Class balance and label PSI were acceptable, but static learnability and walk-forward learnability both failed for every family.
The selected_family_id is only the least-bad diagnostic row; it is not training-ready because selected_family_ready_gate=0.
```

Decision:

```text
Do not train CA1/CA3/CA2.
Do not proceed to Phase174 model training.
No Phase134, no paper shadow, no live trading.
```

Recommended next action requires explicit owner authorization:

```text
Either stop this 1H target-family route for manual review,
or open a new diagnostic-only Phase174A for the Phase171A secondary route: HYBRID_REGIME_FIRST_REDESIGN.
```

Detailed result report:

```text
docs/Report/PHASE173A_BROKER_COST_AWARE_1H_TARGET_LEARNABILITY_RESULT.md
```

## Why this phase exists

Phase172A selected a broker-cost-aware 1H target family:

```text
primary family : CA1_BRK_MID
backup family  : CA3_BRK_STRICT
backup family  : CA2_BRK_WIDE
```

But Phase172A only proved that the target structure was stable enough to inspect. It did not prove the labels are learnable.

Phase173A builds event-level datasets and runs dependency-free baseline learnability diagnostics before any model-training phase.

## Implemented executable

```text
scripts/audit_broker_cost_aware_1h_target_learnability.py
```

## GUI command

```text
Audit broker-cost-aware 1H target learnability
```

## Default target families

```text
CA1_BRK_MID
CA3_BRK_STRICT
CA2_BRK_WIDE
```

CA4 reversal is not included by default because Phase172A rejected it.

## Features

Phase173A builds causal event-level tabular features:

```text
side_buy / side_sell
zone_top / zone_bottom
atr
candle range/body/wicks in ATR
recent range position
recent range width in ATR
distance to top/bottom in ATR
returns over 1/3/6/12/24 bars in ATR
hour/dow sin-cos
spread_to_atr
```

## Labels

```text
POSITIVE -> 1
NEGATIVE/TIMEOUT -> 0
```

The classifier asks:

```text
Can a simple model rank broker-cost-aware positive target events above negative/timeout events?
```

## Baseline model

Dependency-free centroid binary baseline:

```text
standardize train features
positive centroid
negative centroid
score = distance_to_negative - distance_to_positive
threshold selected on train only
```

Metrics:

```text
AP
AP lift over base positive rate
balanced accuracy
F1
BUY-side AP
SELL-side AP
label PSI vs train
walk-forward learnability pass ratio
```

## Gates

Defaults:

```text
min_train_events              : 100
min_validation_events         : 20
min_test_events               : 20
min_positive_rate             : 0.10
max_positive_rate             : 0.70
max_label_psi                 : 0.20
min_ap_lift                   : 0.03
min_balanced_accuracy         : 0.53
min_walkforward_pass_ratio    : 0.50
min_walkforward_folds         : 5
```

Training can only be proposed later if:

```text
class_balance_gate = 1
static_learnability_gate = 1
walkforward_learnability_gate = 1
target_learnability_ready_gate = 1
```

## Outputs

```text
run_logs\broker_cost_aware_1h_target_learnability\latest.json
run_logs\broker_cost_aware_1h_target_learnability\latest.html
run_logs\broker_cost_aware_1h_target_learnability\latest_families.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_splits.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_walkforward.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_dataset.csv
```

## Recommended GUI action

Use:

```text
Audit broker-cost-aware 1H target learnability
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_broker_cost_aware_1h_target_learnability.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48" `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --max-folds 0 `
  --min-train-events 100 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-ap-lift 0.03 `
  --min-balanced-accuracy 0.53 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --max-dataset-rows 20000 `
  --storage-root datasets `
  --output-dir run_logs\broker_cost_aware_1h_target_learnability `
  --report-title "Phase173A broker-cost-aware 1H target learnability audit"
```

## Decision after owner run

If `target_learnability_ready_gate=1`, the next phase may design model training around the selected target family.

If it fails, no model should be trained; move to secondary route from Phase171A or redesign target family.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_broker_cost_aware_1h_target_learnability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```
