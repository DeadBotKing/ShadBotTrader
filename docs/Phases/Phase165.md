# Phase165A — 1H Fixed-Spread Candidate Lockdown / Stability Replay

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

Phase164A found cost-sensitive positive diagnostics for the 1H route. The strongest practical takeaway was not the no-spread selected row, but a nonzero fixed-spread candidate:

```text
policy_key       : BRK_D1_FAST
side_mapping     : breakout
entry_delay      : 1
recent_window    : 24
pivot_zone_atr   : 0.05
bracket          : B15_10 = TP 1.5 ATR / SL 1.0 ATR
hold_bars        : 24
spread_mode      : fixed
spread_value     : 0.2
train PF/PnL     : 1.0607 / +11.0742
validation PF/PnL: 1.6360 / +20.3189
test PF/PnL      : 1.3548 / +14.3794
```

Phase165A stops the grid-search behavior and locks one nonzero-cost candidate for stricter replay, train stability, monthly stability and spread-stress reporting.

## Implemented executable

```text
scripts/replay_pivot_1h_fixed_spread_candidate_lockdown.py
```

## GUI command

```text
Replay 1H fixed-spread candidate lockdown
```

## Default locked candidate

```text
policy_key                : BRK_D1_FAST
side_mapping              : breakout
entry_delay_bars          : 1
recent_window_bars        : 24
pivot_zone_atr            : 0.05
top_position_threshold    : 0.85
bottom_position_threshold : 0.15
exclude_both_zones        : 1
min_range_width_atr       : 1.0
max_range_width_atr       : 0.0
bracket_id                : B15_10
tp_atr                    : 1.5
sl_atr                    : 1.0
hold_bars                 : 24
spread_mode               : fixed
spread_value              : 0.2
```

Mapping meaning:

```text
breakout: top zone -> BUY, bottom zone -> SELL
```

## Stability gates

Default gates:

```text
train_min_trades            : 50
train_min_profit_factor     : 1.00
train_min_final_balance     : 100
validation_min_trades       : 20
validation_min_profit_factor: 1.10
validation_min_final_balance: 100
test_min_trades             : 20
test_min_profit_factor      : 1.10
test_min_final_balance      : 100
min_positive_month_ratio    : 0.50
max_worst_month_loss        : 12.0
require_stress_pass         : 0
```

Transfer pass requires:

```text
train_pass_gate = 1
validation_pass_gate = 1
test_pass_gate = 1
```

Lockdown pass additionally requires:

```text
monthly_stability_gate = 1
stress gate if require_stress_pass=1
```

## Outputs

```text
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest.json
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest.html
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest_summary.csv
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest_trades.csv
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest_monthly.csv
run_logs\pivot_1h_fixed_spread_candidate_lockdown\latest_stress.csv
```

## Recommended GUI action

Use the Dashboard command:

```text
Replay 1H fixed-spread candidate lockdown
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\replay_pivot_1h_fixed_spread_candidate_lockdown.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --policy-key BRK_D1_FAST `
  --side-mapping breakout `
  --entry-delay-bars 1 `
  --recent-window-bars 24 `
  --pivot-zone-atr 0.05 `
  --top-position-threshold 0.85 `
  --bottom-position-threshold 0.15 `
  --exclude-both-zones 1 `
  --min-range-width-atr 1.0 `
  --max-range-width-atr 0 `
  --bracket-id B15_10 `
  --tp-atr 1.5 `
  --sl-atr 1.0 `
  --hold-bars 24 `
  --spread-mode fixed `
  --spread-value 0.2 `
  --stress-spreads 0.2,0.5,1.0 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --train-min-trades 50 `
  --train-min-profit-factor 1.00 `
  --validation-min-trades 20 `
  --validation-min-profit-factor 1.10 `
  --test-min-trades 20 `
  --test-min-profit-factor 1.10 `
  --max-validation-event-rate 0.35 `
  --max-test-event-rate 0.35 `
  --min-positive-month-ratio 0.50 `
  --max-worst-month-loss 12 `
  --require-stress-pass 0 `
  --storage-root datasets `
  --output-dir run_logs\pivot_1h_fixed_spread_candidate_lockdown `
  --report-title "Phase165A 1H fixed-spread candidate lockdown replay"
```

## Decision after owner run

If `lockdown_pass_gate=1`, the next phase can be a model-target design around the locked 1H candidate. It still does not authorize paper/live.

If `lockdown_pass_gate=0`, read the split/month/stress diagnostics. If the failure is monthly instability, do not train a model yet; either tighten the candidate or stop the 1H route.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/replay_pivot_1h_fixed_spread_candidate_lockdown.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase165A on the full local 1H dataset.

Top-level:

```text
train_pass_gate        : 1
validation_pass_gate   : 1
test_pass_gate         : 1
transfer_pass_gate     : 1
monthly_stability_gate : 1
lockdown_pass_gate     : 1
```

Train:

```text
trades                 : 305
PF                     : 1.060733745773545
PnL                    : +11.074247798276177
final_balance          : 111.07424779827605
max_drawdown_cash      : 23.520721785388957
positive_month_ratio   : 0.50
worst_month_pnl        : -5.4897689726064005
```

Validation:

```text
trades                 : 61
PF                     : 1.6359758199652334
PnL                    : +20.318939484345947
final_balance          : 120.31893948434596
max_drawdown_cash      : 5.382938511517068
positive_month_ratio   : 0.5714285714285714
worst_month_pnl        : -3.262167302850812
```

Test:

```text
trades                 : 71
PF                     : 1.3548137730296756
PnL                    : +14.379353264011254
final_balance          : 114.37935326401126
max_drawdown_cash      : 4.691881753934851
positive_month_ratio   : 0.50
worst_month_pnl        : -3.5011694037553847
```

Stress:

```text
fixed spread 0.2 : transfer_pass_gate=1
fixed spread 0.5 : transfer_pass_gate=0 because train fails
fixed spread 1.0 : transfer_pass_gate=0 because train/test stability fails
```

Decision:

```text
Phase165A passed as a diagnostic lockdown.
The locked 1H fixed-spread breakout candidate is now the leading research lane.
No production/paper/live approval is granted.
```

Recommended next phase:

```text
Phase166A — 1H Locked Candidate Walk-Forward / Anti-Overfit Replay
```
