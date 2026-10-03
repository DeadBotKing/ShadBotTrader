# Phase177A — Walk-forward Target-family Redesign Candidate Audit

## Status

```text
COMPLETED — owner run found no ready redesign candidate
research/diagnostic only
```

No production/paper/live/model-training approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model training.
No gate relaxation.
```


## Owner execution result — 2026-10-01

Phase177A was run on the full 1H XAUUSD dataset with fixed spread `0.4`.

Top-level result:

```text
candidate_families                : 8
ready_candidates                  : 0
selected_family_id                : R3_STRICT_B15_10_H12
selected_family_ready_gate        : 0
selected_walkforward_pass_ratio   : 0.0
target_family_redesign_ready_gate : 0
recommendation                    : NO_TARGET_FAMILY_READY_REDESIGN_OR_PAUSE_REQUIRED
```

Best failed candidate:

```text
R3_STRICT_B15_10_H12
TP/SL/hold                      : 1.5 / 1.0 / 12
train PF                        : 0.9735
validation PF                   : 1.4730
test PF                         : 1.3051
validation AP lift              : -0.0081
test AP lift                    : +0.0733
validation/test balanced acc    : 0.5043 / 0.5262
walkforward pass                : 0/6
ready_gate                      : 0
```

Result:

```text
No redesign candidate passed.
Do not train R1/R2/R3/R4/R5/R6/R7/R8.
Keep old CA1/CA3/CA2 targets frozen.
No Phase134, no paper shadow, no live trading.
```

Detailed result report:

```text
docs/Report/PHASE177A_WALKFORWARD_TARGET_FAMILY_REDESIGN_CANDIDATE_AUDIT_RESULT.md
```

## Why this phase exists

Phase176A rejected the current broker-cost-aware 1H target definitions:

```text
CA1_BRK_MID    rejected
CA3_BRK_STRICT rejected
CA2_BRK_WIDE   rejected
```

Supported root-cause hypotheses included:

```text
H1_TARGET_DEFINITION_MISMATCH
H2_TRAIN_EXPECTANCY_INSTABILITY
H3_CLASSIFIER_SIGNAL_NOT_STABLE
H4_RAW_ECONOMICS_DO_NOT_TRANSFER_BY_FOLD
H5_DENSITY_IS_SECONDARY_NOT_PRIMARY
H6_SESSION_FILTERS_NOT_ENOUGH
```

Phase177A is therefore a diagnostic-only audit of new predeclared target-family candidates. It does not train a model.

## Implemented executable

```text
scripts/audit_walkforward_target_family_redesign_candidates.py
```

## GUI command

```text
Audit walk-forward target-family redesign candidates
```

Command kind:

```text
AUDIT_WALKFORWARD_TARGET_FAMILY_REDESIGN_CANDIDATES
```

## Default candidate families

Phase177A audits eight predeclared target-family candidates:

```text
R1_FAST_MID_B15_10_H12
R2_FAST_MID_B12_08_H12
R3_STRICT_B15_10_H12
R4_STRICT_B10_075_H12
R5_WIDE_B20_10_H24
R6_WIDE_B15_10_H24
R7_REV_MID_B10_075_H12
R8_REV_STRICT_B10_075_H12
```

They intentionally vary:

```text
side mapping       : breakout vs reversal
hold horizon       : 12 / 24 bars instead of only prior 24/48
TP/SL geometry     : 1.0/0.75, 1.2/0.8, 1.5/1.0, 2.0/1.0
zone strictness    : mid vs strict vs wide
recent window      : 24 vs 48
```

## Gates

Default gates are train-first and walk-forward-first:

```text
min_train_events                  : 100
min_validation_events             : 25
min_test_events                   : 25
min_positive_rate                 : 0.12
max_positive_rate                 : 0.68
max_label_psi                     : 0.20
min_ap_lift                       : 0.03
min_balanced_accuracy             : 0.53
min_train_independent_pf          : 1.00
min_validation_independent_pf     : 1.00
min_test_independent_pf           : 1.00
min_train_mean_atr_score          : 0.00
min_walkforward_pass_ratio        : 0.50
min_walkforward_folds             : 5
```

A candidate must pass:

```text
density_gate
economic_gate
static_learnability_gate
walkforward_gate
target_family_redesign_ready_gate
```

## Outputs

```text
run_logs\walkforward_target_family_redesign_candidates\latest.json
run_logs\walkforward_target_family_redesign_candidates\latest.html
run_logs\walkforward_target_family_redesign_candidates\latest_candidates.csv
run_logs\walkforward_target_family_redesign_candidates\latest_splits.csv
run_logs\walkforward_target_family_redesign_candidates\latest_walkforward.csv
run_logs\walkforward_target_family_redesign_candidates\latest_events_sample.csv
run_logs\walkforward_target_family_redesign_candidates\latest_decision_matrix.csv
```

## Recommended GUI action

Use:

```text
Audit walk-forward target-family redesign candidates
```

Then send:

```text
run_logs\walkforward_target_family_redesign_candidates\latest.json
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_walkforward_target_family_redesign_candidates.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "R1_FAST_MID_B15_10_H12:fast_breakout_mid_12:breakout:1:24:0.10:0.85:0.15:1:1.0:0:1.5:1.0:12;R2_FAST_MID_B12_08_H12:fast_breakout_mid_compact:breakout:1:24:0.10:0.85:0.15:1:1.0:0:1.2:0.8:12;R3_STRICT_B15_10_H12:fast_breakout_strict_12:breakout:1:24:0.05:0.90:0.10:1:1.0:0:1.5:1.0:12;R4_STRICT_B10_075_H12:strict_asym_12:breakout:1:24:0.05:0.90:0.10:1:1.0:0:1.0:0.75:12;R5_WIDE_B20_10_H24:wide_breakout_shorter_hold:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;R6_WIDE_B15_10_H24:wide_breakout_compact:breakout:1:48:0.10:0.85:0.15:1:1.0:0:1.5:1.0:24;R7_REV_MID_B10_075_H12:reversal_mid_fast:reversal:1:24:0.10:0.85:0.15:1:1.0:0:1.0:0.75:12;R8_REV_STRICT_B10_075_H12:reversal_strict_fast:reversal:1:24:0.05:0.90:0.10:1:1.0:0:1.0:0.75:12" `
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
  --min-validation-events 25 `
  --min-test-events 25 `
  --min-positive-rate 0.12 `
  --max-positive-rate 0.68 `
  --max-label-psi 0.20 `
  --min-ap-lift 0.03 `
  --min-balanced-accuracy 0.53 `
  --min-train-independent-pf 1.00 `
  --min-validation-independent-pf 1.00 `
  --min-test-independent-pf 1.00 `
  --min-train-mean-atr-score 0.00 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --max-events-sample 20000 `
  --storage-root datasets `
  --output-dir run_logs\walkforward_target_family_redesign_candidates `
  --report-title "Phase177A walk-forward target-family redesign candidate audit"
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_walkforward_target_family_redesign_candidates.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_walkforward_target_family_redesign_candidates.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_walkforward_target_family_redesign_candidates.py tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
