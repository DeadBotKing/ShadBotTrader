# Phase179A — 4H/1D Broker-cost Feasibility and Target Pre-audit

## Status

```text
COMPLETED — owner run found cost-feasible but target-not-ready
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

Phase179A was run on 4H and daily XAUUSD data with fixed spread `0.4`.

Top-level result:

```text
evaluated_candidates              : 8
ready_candidates                  : 0
selected_family_id                : D1_R1_BK_MID_B20_10_H5
selected_family_ready_gate        : 0
selected_walkforward_pass_ratio   : 0.2
higher_timeframe_feasibility_gate : 0
recommendation                    : NO_HIGHER_TIMEFRAME_TARGET_READY
```

Cost finding:

```text
4H median spread/ATR train/validation/test : 0.06885 / 0.04246 / 0.02725
1D median spread/ATR train/validation/test : 0.02536 / 0.01612 / 0.01033
Cost feasibility passed for all splits.
```

Best failed candidate:

```text
D1_R1_BK_MID_B20_10_H5
train/validation/test PF       : 1.1263 / 1.1464 / 1.4117
validation/test AP lift        : +0.0309 / +0.0112
validation/test balanced acc   : 0.5243 / 0.5000
walk-forward pass              : 1/5
ready gate                     : 0
```

Decision:

```text
Higher timeframe cost feasibility improved, but target readiness still failed.
Do not train D1/H4 candidates.
No Phase134, no paper shadow, no live trading.
```

Implementation note:

```text
The owner run displayed daily timeframe as "1" because PowerShell can pass unquoted 1D as numeric 1.
The script was patched to canonicalize "1"/"D1" to "1D" and future commands quote --timeframes "4H,1D".
```

Detailed result report:

```text
docs/Report/PHASE179A_HIGHER_TIMEFRAME_COST_FEASIBILITY_RESULT.md
```

## Why this phase exists

Phase178A froze the 1H broker-cost-aware pivot target-family lane:

```text
current_1h_pivot_target_lane_status = FROZEN_FAILED_DIAGNOSTIC
selected_next_research_route_id     = HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY
selected_required_phase             = Phase179A — 4H/1D broker-cost feasibility and target pre-audit
```

Phase179A tests whether 4H/1D timeframes have lower broker-cost pressure and more stable target diagnostics than the failed 1H lane.

## Implemented executable

```text
scripts/audit_higher_timeframe_cost_feasibility.py
```

## GUI command

```text
Audit 4H/1D broker-cost feasibility
```

Command kind:

```text
AUDIT_HIGHER_TIMEFRAME_COST_FEASIBILITY
```

## What it audits

For each timeframe:

```text
4H
1D
```

Phase179A audits:

```text
dataset health
spread/ATR under fixed spread=0.4
event density
label stability
raw independent economics
simple centroid learnability
walk-forward target feasibility
```

## Default target families

4H candidates:

```text
H4_R1_BK_MID_B15_10_H6
H4_R2_BK_STRICT_B15_10_H6
H4_R3_BK_WIDE_B20_10_H12
H4_R4_REV_MID_B10_075_H6
```

1D candidates:

```text
D1_R1_BK_MID_B20_10_H5
D1_R2_BK_STRICT_B15_10_H5
D1_R3_BK_WIDE_B25_125_H10
D1_R4_REV_MID_B10_075_H5
```

These are feasibility candidates only. They do not approve a model.

## Outputs

```text
run_logs\higher_timeframe_cost_feasibility\latest.json
run_logs\higher_timeframe_cost_feasibility\latest.html
run_logs\higher_timeframe_cost_feasibility\latest_health.csv
run_logs\higher_timeframe_cost_feasibility\latest_cost.csv
run_logs\higher_timeframe_cost_feasibility\latest_candidates.csv
run_logs\higher_timeframe_cost_feasibility\latest_splits.csv
run_logs\higher_timeframe_cost_feasibility\latest_walkforward.csv
run_logs\higher_timeframe_cost_feasibility\latest_decision_matrix.csv
```

## Gates

Default feasibility gates:

```text
max_median_spread_atr             : 0.08
min_train_events                  : 80
min_validation_events             : 15
min_test_events                   : 15
min_positive_rate                 : 0.10
max_positive_rate                 : 0.70
max_label_psi                     : 0.25
min_ap_lift                       : 0.02
min_balanced_accuracy             : 0.52
min_train_independent_pf          : 1.00
min_validation_independent_pf     : 1.00
min_test_independent_pf           : 1.00
min_train_mean_atr_score          : 0.00
min_walkforward_pass_ratio        : 0.50
min_walkforward_folds             : 4
```

## Recommended GUI action

Use:

```text
Audit 4H/1D broker-cost feasibility
```

Then send:

```text
run_logs\higher_timeframe_cost_feasibility\latest.json
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_higher_timeframe_cost_feasibility.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --max-rows 0 `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 10 `
  --max-folds 6 `
  --min-train-events 80 `
  --min-validation-events 15 `
  --min-test-events 15 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.25 `
  --min-ap-lift 0.02 `
  --min-balanced-accuracy 0.52 `
  --min-train-independent-pf 1.00 `
  --min-validation-independent-pf 1.00 `
  --min-test-independent-pf 1.00 `
  --min-train-mean-atr-score 0.00 `
  --max-median-spread-atr 0.08 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 4 `
  --storage-root datasets `
  --output-dir run_logs\higher_timeframe_cost_feasibility `
  --report-title "Phase179A 4H/1D broker-cost feasibility and target pre-audit"
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_higher_timeframe_cost_feasibility.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
