# PHASE179A — 4H/1D Broker-cost Feasibility and Target Pre-audit Report

## Summary

Phase179A has been implemented after Phase178A selected the higher-timeframe research route.

This phase audits 4H and 1D broker-cost feasibility and target-family pre-audit candidates. It does not train a model and does not approve paper/live trading.

## Implemented files

```text
scripts/audit_higher_timeframe_cost_feasibility.py
tests/unit/ai/test_higher_timeframe_cost_feasibility.py
```

GUI integration:

```text
CommandKind.AUDIT_HIGHER_TIMEFRAME_COST_FEASIBILITY
GUI label: Audit 4H/1D broker-cost feasibility
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Inputs

Default data paths:

```text
datasets\processed\XAUUSD\4H\v1.parquet
datasets\processed\XAUUSD\1D\v1.parquet
```

Default spread:

```text
fixed 0.4
```

## Candidate families

4H:

```text
H4_R1_BK_MID_B15_10_H6
H4_R2_BK_STRICT_B15_10_H6
H4_R3_BK_WIDE_B20_10_H12
H4_R4_REV_MID_B10_075_H6
```

1D:

```text
D1_R1_BK_MID_B20_10_H5
D1_R2_BK_STRICT_B15_10_H5
D1_R3_BK_WIDE_B25_125_H10
D1_R4_REV_MID_B10_075_H5
```

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

## Recommended command

Dashboard:

```text
Audit 4H/1D broker-cost feasibility
```

PowerShell:

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

```text
python -m py_compile scripts/audit_higher_timeframe_cost_feasibility.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase179A 4H/1D feasibility pre-audit only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase179A. Higher-timeframe cost feasibility improved, but no 4H/1D target family passed target-readiness gates:

```text
evaluated_candidates              : 8
ready_candidates                  : 0
selected_family_id                : D1_R1_BK_MID_B20_10_H5
selected_family_ready_gate        : 0
selected_walkforward_pass_ratio   : 0.2
higher_timeframe_feasibility_gate : 0
recommendation                    : NO_HIGHER_TIMEFRAME_TARGET_READY
```

Detailed result report:

```text
docs/Report/PHASE179A_HIGHER_TIMEFRAME_COST_FEASIBILITY_RESULT.md
```

Important note:

```text
The owner run displayed daily timeframe as "1" because PowerShell can pass unquoted 1D as numeric 1.
The script was patched to canonicalize "1"/"D1" to "1D" and future commands quote --timeframes "4H,1D".
```

Decision:

```text
Do not train D1/H4 candidates.
No Phase134.
No paper shadow.
No live trading.
```
