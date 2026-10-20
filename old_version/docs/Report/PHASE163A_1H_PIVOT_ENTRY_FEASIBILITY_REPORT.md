# PHASE163A — 1H Pivot Entry Feasibility Audit Report

## Summary

Phase163A implements the owner's proposal to evaluate 1H entries instead of continuing to force a fragile 5M pivot-entry rule.

It is a feasibility audit, not model training. It checks whether 1H data and simple 1H pivot-rule replays are healthy enough to justify a later 1H target/model phase.

## Implemented files

```text
scripts/audit_pivot_1h_entry_feasibility.py
tests/unit/ai/test_pivot_1h_entry_feasibility.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_1H_ENTRY_FEASIBILITY
GUI label: Audit 1H pivot entry feasibility
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Why 1H is being audited

The 5M bottom-buy route failed because:

```text
spread decayed a small event edge
next-open BUY gap was often adverse
single-position replay skipped winners
same-bar policy was not the cause
```

Moving to 1H may improve the ratio of target movement to execution cost, but this must be measured before any training.

## What the script does

### Data health

```text
row count
timestamp range
duplicate timestamps
expected 60-minute gap count
max gap minutes
nonfinite OHLC cells
invalid OHLC rows
ATR nonpositive rows
```

### Spread/ATR audit

For each split and spread value:

```text
ATR mean / median
full spread / ATR mean
full spread / ATR median
full spread / ATR p90
half spread / ATR median
spread_feasible_gate
```

### Candidate/replay audit

Grid defaults:

```text
recent_window_bars        : 24,48
pivot_zone_atrs           : 0.05,0.10,0.15
top_position_thresholds   : 0.85,0.90
bottom_position_thresholds: 0.15,0.10
side_mappings             : reversal,bottom_buy,top_sell,breakout
entry_delays              : 0,1
spread_values             : 0,0.06
```

Replay assumptions:

```text
TP          : 1.5 ATR
SL          : 1.0 ATR
hold_bars   : 24
spread      : selected by grid, realistic selection defaults to 0.06%
risk        : 1% of current balance
capital     : 100
single-position chronological replay
```

## Outputs

```text
run_logs\pivot_1h_entry_feasibility\latest.json
run_logs\pivot_1h_entry_feasibility\latest.html
run_logs\pivot_1h_entry_feasibility\latest_spread_atr.csv
run_logs\pivot_1h_entry_feasibility\latest_candidate_replay.csv
run_logs\pivot_1h_entry_feasibility\latest_selection.csv
run_logs\pivot_1h_entry_feasibility\latest_monthly.csv
```

## Recommended command

Prefer the Dashboard button:

```text
Audit 1H pivot entry feasibility
```

Equivalent PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_pivot_1h_entry_feasibility.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --expected-step-minutes 60 `
  --recent-window-bars 24,48 `
  --pivot-zone-atrs 0.05,0.10,0.15 `
  --top-position-thresholds 0.85,0.90 `
  --bottom-position-thresholds 0.15,0.10 `
  --exclude-both-zones 1 `
  --min-range-width-atrs 1.0 `
  --max-range-width-atrs 0 `
  --side-mappings reversal,bottom_buy,top_sell,breakout `
  --entry-delays 0,1 `
  --spread-mode pct `
  --spread-values 0,0.06 `
  --selection-spread-value 0.06 `
  --max-median-spread-atr 0.12 `
  --tp-atr 1.5 `
  --sl-atr 1.0 `
  --hold-bars 24 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --validation-min-trades 10 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 10 `
  --test-min-profit-factor 1.05 `
  --max-validation-event-rate 0.35 `
  --max-test-event-rate 0.35 `
  --score-metric cash_pnl `
  --max-policies 0 `
  --storage-root datasets `
  --output-dir run_logs\pivot_1h_entry_feasibility `
  --report-title "Phase163A 1H pivot entry feasibility audit"
```

## Selection protocol

Policy selection uses validation metrics only and defaults to the realistic spread rows:

```text
selection_spread_value = 0.06
```

No-spread rows are included only to quantify execution-cost sensitivity.

## Verification

```text
python -m py_compile scripts/audit_pivot_1h_entry_feasibility.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not available in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase163A 1H feasibility diagnostic only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase163A on the full local 1H dataset.

```text
flat_rows                : 50000
validation_pass_configs  : 0
transfer_pass_configs    : 0
spread_feasible_gate     : 0
route_feasible_gate      : 0
```

Selected realistic-spread row:

```text
policy_id      : 1H|breakout|d=1|rw=48|zone=0.05|top=0.85|bottom=0.15|ex=1|minw=1|maxw=0|spread=0.06
validation PF  : 0.9875648654547112
test PF        : 0.9567436757286336
transfer_gate  : 0
```

Key conclusion:

```text
1H raw no-spread structure is promising, but the route is not feasible under spread=0.06%.
No 1H model should be trained until broker spread units and bracket-cost sensitivity are audited.
```

Detailed result:

```text
docs/Report/PHASE163A_1H_PIVOT_ENTRY_FEASIBILITY_RESULT.md
```
