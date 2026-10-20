# Phase175A — Hybrid/regime Walk-forward Failure Attribution Audit

## Status

```text
COMPLETED — owner run confirmed walk-forward failure attribution
research/diagnostic only
```

No production/paper/live/model-training approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model training.
```


## Owner execution result — 2026-10-01

Phase175A was run on the Phase174A output.

Top-level result:

```text
candidate_rows                        : 66
walkforward_rows                      : 396
walkforward_pass_rows                 : 0
walkforward_global_pass_ratio         : 0.0
candidates_with_class_balance_gate    : 53
candidates_with_economic_gate         : 4
candidates_with_static_learnability   : 0
candidates_with_walkforward_gate      : 0
candidates_with_ready_gate            : 0
```

Dominant failures:

```text
static_learnability_gate_failed      : 66/66 candidates
walkforward_learnability_gate_failed : 66/66 candidates
walkforward_pass_ratio_failed        : 66/66 candidates
test_balanced_accuracy_failed        : 63/66 candidates
economic_gate_failed                 : 62/66 candidates
train_negative_expectancy_failed     : 57/66 candidates
```

Walk-forward attribution:

```text
fold_pass_gate_failed               : 396/396 folds
test_balanced_accuracy_failed       : 292/396 folds
validation_balanced_accuracy_failed : 292/396 folds
validation_raw_economics_failed     : 253/396 folds
test_raw_economics_failed           : 241/396 folds
```

Selected near-miss:

```text
CA1_BRK_MID + WIDTH_GE_Q75
ready_gate=0
primary_failure_reason=static_learnability_gate_failed
validation_ap_lift=+0.1417
test_ap_lift=+0.1991
test_balanced_accuracy=0.5000
walkforward_pass=0/6
```

Decision:

```text
Phase175A confirms target/regime instability rather than a model-capacity issue.
Do not train.
Do not relax gates.
No Phase134, no paper shadow, no live trading.
```

Detailed result report:

```text
docs/Report/PHASE175A_HYBRID_REGIME_WALKFORWARD_FAILURE_ATTRIBUTION_RESULT.md
```

## Why this phase exists

Phase174A tested the Phase171A secondary route `HYBRID_REGIME_FIRST_REDESIGN` and failed:

```text
evaluated_regime_candidates    : 66
ready_regime_candidates        : 0
hybrid_regime_first_ready_gate : 0
```

The owner asked for the assistant's recommendation and authorized the preferred next step. The selected recommendation is not model training. It is a diagnostic-only failure attribution phase:

```text
Phase175A — Hybrid/regime Walk-forward Failure Attribution Audit
```

Purpose:

```text
Attribute why Phase174A produced positive-looking pockets but still failed every walk-forward gate.
```

## Implemented executable

```text
scripts/audit_hybrid_regime_walkforward_failure_attribution.py
```

## GUI command

```text
Audit hybrid/regime walk-forward failures
```

Command kind:

```text
AUDIT_HYBRID_REGIME_WALKFORWARD_FAILURES
```

## Inputs

Primary input:

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
```

This is the Phase174A result file.

## What it audits

Phase175A consumes Phase174A output and attributes failure by:

```text
candidate density
positive-rate stability
label PSI
raw train/validation/test economics
validation/test AP lift
validation/test balanced accuracy
walk-forward pass ratio
per-fold failure reasons
```

It does not recompute market features and does not train a model.

## Outputs

```text
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
run_logs\hybrid_regime_walkforward_failure_attribution\latest.html
run_logs\hybrid_regime_walkforward_failure_attribution\latest_candidate_failures.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_failure_reasons.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_fold_failure_summary.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_decision_matrix.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_next_plan.csv
```

## Default thresholds

Defaults match Phase174A gates:

```text
min_train_events                  : 80
min_validation_events             : 20
min_test_events                   : 20
min_positive_rate                 : 0.10
max_positive_rate                 : 0.70
max_label_psi                     : 0.20
min_ap_lift                       : 0.03
min_balanced_accuracy             : 0.53
min_train_independent_pf          : 0.95
min_validation_independent_pf     : 1.00
min_test_independent_pf           : 1.00
min_walkforward_pass_ratio        : 0.50
min_walkforward_folds             : 5
```

## Decision rules

Phase175A can only produce diagnostic recommendations. It always preserves:

```text
no_training_gate = 1
no_paper_live_gate = 1
```

It can recommend a later diagnostic target-definition redesign/root-cause phase, but it cannot approve:

```text
Phase175 model training
Phase134
paper shadow
live trading
```

## Recommended GUI action

Use:

```text
Audit hybrid/regime walk-forward failures
```

Then send:

```text
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_hybrid_regime_walkforward_failure_attribution.py `
  --phase174-path run_logs\hybrid_regime_first_target_redesign\latest.json `
  --min-train-events 80 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-ap-lift 0.03 `
  --min-balanced-accuracy 0.53 `
  --min-train-independent-pf 0.95 `
  --min-validation-independent-pf 1.00 `
  --min-test-independent-pf 1.00 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --output-dir run_logs\hybrid_regime_walkforward_failure_attribution `
  --report-title "Phase175A hybrid/regime walk-forward failure attribution audit"
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_hybrid_regime_walkforward_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
