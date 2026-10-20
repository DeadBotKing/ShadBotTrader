# Phase163A — 1H Pivot / Entry Feasibility Audit

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

Phase162A closed the strict 5M B2 bottom-buy rescue lane:

```text
Phase160A: event scoring was positive
Phase161A: chronological replay failed
Phase162A: execution-gap audit found no transferable rescue
```

The owner suggested moving entry discovery from 5M to 1H. This is technically reasonable because the 5M rule was too sensitive to spread and micro-entry noise.

Phase163A starts the 1H route safely: it audits 1H data, spread/ATR economics, and simple pivot-rule chronological replay before any model training.

## Implemented executable

```text
scripts/audit_pivot_1h_entry_feasibility.py
```

## GUI command

```text
Audit 1H pivot entry feasibility
```

## What it checks

```text
1. 1H data health:
   rows, timestamp range, duplicate timestamps, expected 60-minute gaps,
   nonfinite OHLC cells, invalid OHLC rows, ATR validity.

2. Spread / ATR burden:
   full_spread_atr_mean
   full_spread_atr_median
   full_spread_atr_p90
   half_spread_atr_median
   spread_feasible_gate

3. Pivot candidate geometry:
   recent_window_bars grid
   pivot_zone_atrs grid
   top/bottom position threshold grid
   range-width filters

4. Simple rule replay before training:
   reversal
   bottom_buy
   top_sell
   breakout
   optional top_buy/bottom_sell/all_buy/all_sell controls

5. Chronological replay:
   spread-aware trade_path
   single-position constraints
   skipped_while_open attribution
   train/validation/test split gates
   monthly breakdown
```

## Default parameters

```text
timeframe                 : 1H
flat_path                 : datasets\processed\XAUUSD\1H\v1.parquet
recent_window_bars        : 24,48
pivot_zone_atrs           : 0.05,0.10,0.15
top_position_thresholds   : 0.85,0.90
bottom_position_thresholds: 0.15,0.10
side_mappings             : reversal,bottom_buy,top_sell,breakout
entry_delays              : 0,1
spread_values             : 0,0.06
selection_spread_value    : 0.06
tp_atr                    : 1.5
sl_atr                    : 1.0
hold_bars                 : 24
validation_min_trades     : 10
test_min_trades           : 10
validation_min_PF         : 1.05
test_min_PF               : 1.05
```

Important: policy selection is made on the realistic spread row by default:

```text
selection_spread_value = 0.06
```

No-spread rows are diagnostic only.

## Outputs

```text
run_logs\pivot_1h_entry_feasibility\latest.json
run_logs\pivot_1h_entry_feasibility\latest.html
run_logs\pivot_1h_entry_feasibility\latest_spread_atr.csv
run_logs\pivot_1h_entry_feasibility\latest_candidate_replay.csv
run_logs\pivot_1h_entry_feasibility\latest_selection.csv
run_logs\pivot_1h_entry_feasibility\latest_monthly.csv
```

## Recommended GUI action

Use the Dashboard command:

```text
Audit 1H pivot entry feasibility
```

## Equivalent PowerShell command

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

## Decision after owner run

If Phase163A returns:

```text
route_feasible_gate = 1
```

then the next phase can be a 1H target/candidate redesign audit.

If it returns:

```text
route_feasible_gate = 0
```

then 1H raw pivot rules are not yet validated, and no 1H model should be trained around them.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_pivot_1h_entry_feasibility.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/ai/test_pivot_bottom_buy_execution_gap.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Owner execution result

The owner ran Phase163A on the full 1H dataset.

Top-level:

```text
flat_rows                : 50000
replay_policy_rows       : 1152
selection_rows           : 384
validation_pass_configs  : 0
transfer_pass_configs    : 0
spread_feasible_gate     : 0
route_feasible_gate      : 0
```

Selected realistic-spread row:

```text
policy_id       : 1H|breakout|d=1|rw=48|zone=0.05|top=0.85|bottom=0.15|ex=1|minw=1|maxw=0|spread=0.06
validation PF   : 0.9875648654547112
validation PnL  : -0.37308487550487257
test PF         : 0.9567436757286336
test PnL        : -1.3693540267499014
transfer_gate   : 0
```

Spread/ATR finding:

```text
spread=0.06% median full spread/ATR:
  train      : 0.27117005195240595
  validation : 0.2357716197367245
  test       : 0.1597977693295558
max_median_spread_atr gate: 0.12
spread_feasible_gate: 0
```

Diagnostic interpretation:

```text
No-spread 1H rows showed raw pivot/breakout signal, including multiple transfer-pass rows.
But under realistic spread=0.06%, no configuration passed validation and no configuration transferred.
The current blocker is spread/cost modeling, not model architecture.
```

Decision:

```text
Do not train a 1H pivot model yet.
Do not approve paper/live.
Phase163A route_feasible_gate=0 under current spread assumption.
```

Recommended next diagnostic:

```text
Phase164A — 1H Spread Unit / Bracket Cost Sensitivity Audit
```

Reason:

```text
If spread=0.06% is too pessimistic or has wrong units for Alpari XAUUSD, the 1H route may still be worth testing with fixed broker-like spreads.
If realistic fixed spread still kills the edge, stop the 1H pivot raw-rule route.
```
