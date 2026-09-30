# PHASE164A — 1H Spread Unit / Bracket Cost Sensitivity Audit Report

## Summary

Phase164A has been implemented to answer the key question raised by Phase163A:

```text
Is the 1H route truly bad, or did spread=0.06% use the wrong/too-pessimistic cost unit?
```

It does not train a model. It audits fixed spread, percent spread, wider ATR brackets, hold-bars sensitivity and break-even spread thresholds for the 1H no-spread-positive candidate policies.

## Implemented files

```text
scripts/audit_pivot_1h_spread_bracket_sensitivity.py
tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_1H_SPREAD_BRACKET_SENSITIVITY
GUI label: Audit 1H spread/bracket sensitivity
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Inputs

Default dataset:

```text
datasets\processed\XAUUSD\1H\v1.parquet
```

Default candidate policies are focused on Phase163A's no-spread-positive 1H structures:

```text
BRK_D1_FAST:breakout:1:24:0.05:0.85:0.15:1:1.0:0
BRK_D0_MID:breakout:0:24:0.10:0.85:0.15:1:1.0:0
BRK_D0_WIDE:breakout:0:48:0.10:0.85:0.15:1:1.0:0
BB_D1_WIDE:bottom_buy:1:24:0.15:0.85:0.15:1:1.0:0
```

## Audit grid

```text
fixed_spreads = 0,0.2,0.5,1.0,1.5,2.0
pct_spreads   = 0,0.01,0.02,0.03,0.06
brackets      = 1.5/1.0, 2.0/1.0, 2.5/1.25, 3.0/1.5
hold_bars     = 24,48
```

## Outputs

```text
run_logs\pivot_1h_spread_bracket_sensitivity\latest.json
run_logs\pivot_1h_spread_bracket_sensitivity\latest.html
run_logs\pivot_1h_spread_bracket_sensitivity\latest_grid.csv
run_logs\pivot_1h_spread_bracket_sensitivity\latest_split_replay.csv
run_logs\pivot_1h_spread_bracket_sensitivity\latest_break_even.csv
run_logs\pivot_1h_spread_bracket_sensitivity\latest_spread_atr.csv
run_logs\pivot_1h_spread_bracket_sensitivity\latest_monthly.csv
```

## Recommended command

Prefer the Dashboard command:

```text
Audit 1H spread/bracket sensitivity
```

Equivalent PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_pivot_1h_spread_bracket_sensitivity.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --candidate-policies "BRK_D1_FAST:breakout:1:24:0.05:0.85:0.15:1:1.0:0;BRK_D0_MID:breakout:0:24:0.10:0.85:0.15:1:1.0:0;BRK_D0_WIDE:breakout:0:48:0.10:0.85:0.15:1:1.0:0;BB_D1_WIDE:bottom_buy:1:24:0.15:0.85:0.15:1:1.0:0" `
  --brackets "B15_10:1.5:1.0;B20_10:2.0:1.0;B25_125:2.5:1.25;B30_15:3.0:1.5" `
  --hold-bars-grid 24,48 `
  --fixed-spreads 0,0.2,0.5,1.0,1.5,2.0 `
  --pct-spreads 0,0.01,0.02,0.03,0.06 `
  --same-bar-policy stop_first `
  --max-median-spread-atr 0.12 `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --validation-min-trades 10 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 10 `
  --test-min-profit-factor 1.05 `
  --max-validation-event-rate 0.35 `
  --max-test-event-rate 0.35 `
  --score-metric cash_pnl `
  --storage-root datasets `
  --output-dir run_logs\pivot_1h_spread_bracket_sensitivity `
  --report-title "Phase164A 1H spread/bracket cost sensitivity audit"
```

## Selection protocol

Rows are ranked by validation-only score first, with transfer status reported separately:

```text
transfer_pass_gate
validation_pass_gate
validation_score
validation_profit_factor
test_profit_factor
```

Test remains confirmation-only. No paper/live approval follows from this audit.

## Break-even interpretation

`latest_break_even.csv` reports per policy/bracket/hold/spread-mode:

```text
max_validation_nonnegative_spread
max_test_nonnegative_spread
max_both_nonnegative_spread
max_validation_pass_spread
max_test_pass_spread
max_transfer_pass_spread
first_validation_negative_spread
first_test_negative_spread
first_transfer_fail_spread
```

This is the main artifact for deciding whether broker-realistic fixed spread can preserve the 1H raw signal.

## Verification

```text
python -m py_compile scripts/audit_pivot_1h_spread_bracket_sensitivity.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not available in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase164A spread/bracket diagnostic only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase164A on the full local 1H dataset.

```text
evaluated_configs           : 352
validation_pass_configs     : 244
transfer_pass_configs       : 131
fixed_transfer_pass_configs : 69
pct_transfer_pass_configs   : 62
route_feasible_gate         : 1
```

Key result:

```text
1H route has positive cost-sensitive diagnostics.
The Phase163A failure was too narrow: one bracket plus spread=0.06%.
With fixed broker-like spreads and wider brackets, many rows transfer.
```

Detailed result:

```text
docs/Report/PHASE164A_1H_SPREAD_BRACKET_SENSITIVITY_RESULT.md
```

Recommended next phase:

```text
Phase165A — 1H Fixed-Spread Candidate Lockdown / Stability Replay
```
