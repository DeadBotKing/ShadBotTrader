# PHASE168A — 1H Predeclared Filter Confirmation Replay Report

## Summary

Phase168A has been implemented as a final confirmation-only replay for the 1H locked candidate route.

It tests only four predeclared filter states from Phase167A:

```text
none
max_spread_atr_0.10
buy_leg_only
buy_leg_only+max_spread_atr_0.10
```

It does not run a new grid search, does not optimize thresholds, does not train a model, and does not approve paper/live trading.

## Implemented files

```text
scripts/replay_pivot_1h_predeclared_filter_confirmation.py
tests/unit/ai/test_pivot_1h_filter_confirmation.py
```

GUI integration:

```text
CommandKind.REPLAY_PIVOT_1H_PREDECLARED_FILTER_CONFIRMATION
GUI label: Replay 1H predeclared filter confirmation
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Locked candidate

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
```

## Outputs

```text
run_logs\pivot_1h_predeclared_filter_confirmation\latest.json
run_logs\pivot_1h_predeclared_filter_confirmation\latest.html
run_logs\pivot_1h_predeclared_filter_confirmation\latest_filter_summary.csv
run_logs\pivot_1h_predeclared_filter_confirmation\latest_filter_folds.csv
run_logs\pivot_1h_predeclared_filter_confirmation\latest_filter_splits.csv
run_logs\pivot_1h_predeclared_filter_confirmation\latest_trades.csv
run_logs\pivot_1h_predeclared_filter_confirmation\latest_monthly.csv
run_logs\pivot_1h_predeclared_filter_confirmation\latest_stress.csv
```

## Recommended command

Prefer the Dashboard command:

```text
Replay 1H predeclared filter confirmation
```

Equivalent PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\replay_pivot_1h_predeclared_filter_confirmation.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
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
  --stress-spreads 0.2,0.5 `
  --same-bar-policy stop_first `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --purge-gap 24 `
  --max-folds 0 `
  --filters none,max_spread_atr_0.10,buy_leg_only,buy_leg_only+max_spread_atr_0.10 `
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
  --min-folds 5 `
  --min-fold-pass-ratio 0.55 `
  --min-test-pass-ratio 0.60 `
  --min-median-test-profit-factor 1.05 `
  --min-aggregate-test-cash-pnl 0 `
  --max-worst-test-drawdown 25 `
  --require-stress-pass 0 `
  --storage-root datasets `
  --output-dir run_logs\pivot_1h_predeclared_filter_confirmation `
  --report-title "Phase168A 1H predeclared filter confirmation replay"
```

## Selection protocol

This is confirmation-only. The script reports the strongest row among the four predeclared filters, but the filter set is fixed before execution.

A filter must pass the same aggregate walk-forward gates:

```text
folds >= 5
fold_pass_ratio >= 0.55
test_pass_ratio >= 0.60
median_test_profit_factor >= 1.05
aggregate_test_cash_pnl > 0
worst_test_max_drawdown <= 25
```

## Verification

```text
python -m py_compile scripts/replay_pivot_1h_predeclared_filter_confirmation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_filter_confirmation.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_filter_confirmation.py tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not available in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase168A predeclared filter confirmation only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase168A on the full local 1H dataset.

```text
selected_filter_name       : buy_leg_only
selected_filter_pass_gate  : 0
selected_fold_pass_ratio   : 0.16666666666666666
selected_test_pass_ratio   : 0.3333333333333333
confirmation_pass_gate     : 0
recommendation             : STOP_1H_LOCKED_FILTER_ROUTE_OR_REDESIGN
```

Key conclusion:

```text
No predeclared filter confirmed the locked 1H candidate.
The current 1H locked-candidate route should stop and no model should be trained around it.
```

Detailed result:

```text
docs/Report/PHASE168A_1H_PREDECLARED_FILTER_CONFIRMATION_RESULT.md
```
