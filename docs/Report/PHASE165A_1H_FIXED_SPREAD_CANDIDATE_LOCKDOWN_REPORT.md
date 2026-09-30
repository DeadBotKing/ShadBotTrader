# PHASE165A — 1H Fixed-Spread Candidate Lockdown / Stability Replay Report

## Summary

Phase165A has been implemented to lock and replay a single nonzero-cost 1H breakout candidate from Phase164A.

It does not train a model. It evaluates whether one concrete fixed-spread policy is stable enough across train, validation, test, months and optional spread stress before any 1H model-target work.

## Implemented files

```text
scripts/replay_pivot_1h_fixed_spread_candidate_lockdown.py
tests/unit/ai/test_pivot_1h_candidate_lockdown.py
```

GUI integration:

```text
CommandKind.REPLAY_PIVOT_1H_FIXED_SPREAD_CANDIDATE_LOCKDOWN
GUI label: Replay 1H fixed-spread candidate lockdown
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Locked candidate

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
bracket_id                : B15_10
tp_atr                    : 1.5
sl_atr                    : 1.0
hold_bars                 : 24
spread_mode               : fixed
spread_value              : 0.2
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

## Recommended command

Prefer the Dashboard command:

```text
Replay 1H fixed-spread candidate lockdown
```

Equivalent PowerShell:

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

## Gates

```text
train gate:
  trades >= 50
  PF >= 1.00
  final_balance >= 100
  positive_month_ratio >= 0.50
  worst_month_pnl >= -12

validation gate:
  trades >= 20
  PF >= 1.10
  final_balance >= 100
  event_rate <= 0.35
  positive_month_ratio >= 0.50
  worst_month_pnl >= -12

test gate:
  trades >= 20
  PF >= 1.10
  final_balance >= 100
  event_rate <= 0.35
  positive_month_ratio >= 0.50
  worst_month_pnl >= -12
```

## Verification

```text
python -m py_compile scripts/replay_pivot_1h_fixed_spread_candidate_lockdown.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not available in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase165A candidate lockdown diagnostic only
No Phase134.
No paper shadow.
No live trading.
```
