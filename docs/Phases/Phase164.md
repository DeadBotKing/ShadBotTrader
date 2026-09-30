# Phase164A — 1H Spread Unit / Bracket Cost Sensitivity Audit

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

Phase163A tested the owner's 1H idea and found:

```text
1H no-spread raw pivot/breakout signal exists.
But under spread=0.06%, no realistic-spread configuration passed validation.
spread_feasible_gate = 0
route_feasible_gate  = 0
```

The critical question is now whether `spread=0.06%` is the right unit/assumption for Alpari XAUUSD. Phase164A audits fixed spread values and percent spread values, plus wider ATR brackets, before any 1H model training.

## Implemented executable

```text
scripts/audit_pivot_1h_spread_bracket_sensitivity.py
```

## GUI command

```text
Audit 1H spread/bracket sensitivity
```

## What it audits

```text
1. fixed spread grid:
   0, 0.2, 0.5, 1.0, 1.5, 2.0

2. percent spread grid:
   0, 0.01, 0.02, 0.03, 0.06

3. wider bracket grid:
   B15_10 : TP=1.5 ATR, SL=1.0 ATR
   B20_10 : TP=2.0 ATR, SL=1.0 ATR
   B25_125: TP=2.5 ATR, SL=1.25 ATR
   B30_15 : TP=3.0 ATR, SL=1.5 ATR

4. hold bars:
   24,48

5. focused candidate policies from Phase163A no-spread signal:
   BRK_D1_FAST
   BRK_D0_MID
   BRK_D0_WIDE
   BB_D1_WIDE
```

## Default candidate policies

Format:

```text
ID:mapping:delay:rw:zone:top:bottom:exclude:minw:maxw
```

Default:

```text
BRK_D1_FAST:breakout:1:24:0.05:0.85:0.15:1:1.0:0
BRK_D0_MID:breakout:0:24:0.10:0.85:0.15:1:1.0:0
BRK_D0_WIDE:breakout:0:48:0.10:0.85:0.15:1:1.0:0
BB_D1_WIDE:bottom_buy:1:24:0.15:0.85:0.15:1:1.0:0
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

## Recommended GUI action

Use the Dashboard command:

```text
Audit 1H spread/bracket sensitivity
```

## Equivalent PowerShell command

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

## Decision after owner run

If fixed broker-like spread values allow validation-selected transfer, then the next phase may build a stricter 1H target/replay confirmation around the selected cost model.

If even fixed realistic spread values fail, the 1H pivot raw-rule route should be stopped before model training.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_pivot_1h_spread_bracket_sensitivity.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase164A on the full local 1H dataset.

Top-level:

```text
evaluated_configs           : 352
validation_pass_configs     : 244
transfer_pass_configs       : 131
fixed_transfer_pass_configs : 69
pct_transfer_pass_configs   : 62
route_feasible_gate         : 1
```

The script-selected top row was no-spread:

```text
selected_config_id : BRK_D0_MID|breakout|d=0|rw=24|zone=0.1|bracket=B25_125|hold=24|spread_mode=fixed|spread=0
validation PF      : 1.4744696009702762
validation PnL     : +38.81352959768986
test PF            : 1.0845370178384561
test PnL           : +7.788579434364673
```

No-spread is not operational by itself, but Phase164A also found nonzero-cost transfer rows.

Important nonzero fixed-spread candidate:

```text
config_id      : BRK_D1_FAST|breakout|d=1|rw=24|zone=0.05|bracket=B15_10|hold=24|spread_mode=fixed|spread=0.2
train PF       : 1.060733745773545
train PnL      : +11.074247798276177
validation PF  : 1.6359758199652334
validation PnL : +20.318939484345947
test PF        : 1.3548137730296756
test PnL       : +14.379353264011254
transfer_gate  : 1
```

Spread/ATR diagnostics:

```text
fixed spread 0.2 median spread/ATR:
  train      : 0.05248
  validation : 0.03098
  test       : 0.01257

pct spread 0.06 median spread/ATR:
  train      : 0.27117
  validation : 0.23577
  test       : 0.15980
```

Decision:

```text
Phase164A is positive diagnostically.
The 1H route should not be rejected.
But there is still no production/paper/live approval and no model training yet.
```

Recommended next phase:

```text
Phase165A — 1H Fixed-Spread Candidate Lockdown / Stability Replay
```

Required gates for Phase165A:

```text
nonzero spread only
train-stability pass
validation pass
test confirmation
monthly stability
single locked candidate
```
