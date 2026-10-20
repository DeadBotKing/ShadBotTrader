# Phase168A — 1H Predeclared Filter Confirmation Replay

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

Phase167A attributed the Phase166A walk-forward failure and found:

```text
baseline_fold_pass_count    : 0/6
baseline_test_pass_count    : 4/6
baseline_aggregate_test_pnl : +38.6401
dominant_failure_reason     : monthly_stability_failed
best_filter_name            : buy_leg_only, but only 1/6 fold pass
```

Phase168A is a final confirmation-only replay for a tiny predeclared filter set. It does not introduce new thresholds, new candidates, new optimization, or model training.

## Implemented executable

```text
scripts/replay_pivot_1h_predeclared_filter_confirmation.py
```

## GUI command

```text
Replay 1H predeclared filter confirmation
```

## Locked candidate

```text
policy_key                : BRK_D1_FAST
side_mapping              : breakout
top zone                  : BUY
bottom zone               : SELL
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

## Predeclared filters only

```text
none
max_spread_atr_0.10
buy_leg_only
buy_leg_only+max_spread_atr_0.10
```

No other filter should be added in this phase.

## Default walk-forward protocol

```text
fold_train_bars      : 18000
fold_validation_bars : 4000
fold_test_bars       : 4000
fold_step_bars       : 4000
purge_gap            : 24
```

## Aggregate pass gates

```text
min_folds                    : 5
min_fold_pass_ratio          : 0.55
min_test_pass_ratio          : 0.60
min_median_test_profit_factor: 1.05
min_aggregate_test_cash_pnl  : 0.0
max_worst_test_drawdown      : 25.0
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

## Recommended GUI action

Use the Dashboard command:

```text
Replay 1H predeclared filter confirmation
```

## Equivalent PowerShell command

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

## Decision after owner run

If no filter passes Phase168A, stop the 1H locked-candidate route and do not train a model around it.

If a filter passes, the next step is still not production. It would only allow a new target/model design phase around that locked filter.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/replay_pivot_1h_predeclared_filter_confirmation.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_filter_confirmation.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_filter_confirmation.py tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase168A on the full local 1H dataset.

Top-level:

```text
filters:
  none
  max_spread_atr_0.10
  buy_leg_only
  buy_leg_only+max_spread_atr_0.10

folds                       : 6
selected_filter_name        : buy_leg_only
selected_filter_pass_gate   : 0
selected_fold_pass_ratio    : 0.16666666666666666
selected_test_pass_ratio    : 0.3333333333333333
selected_aggregate_test_pnl : +31.885510318263545
selected_median_test_pf     : 1.3055548257488616
confirmation_pass_gate      : 0
recommendation              : STOP_1H_LOCKED_FILTER_ROUTE_OR_REDESIGN
```

Filter summary:

```text
none:
  fold_pass=0/6
  test_pass=4/6
  aggregate_test_pnl=+38.6401
  pass_gate=0

max_spread_atr_0.10:
  fold_pass=0/6
  test_pass=4/6
  aggregate_test_pnl=+41.8019
  pass_gate=0

buy_leg_only:
  fold_pass=1/6
  test_pass=2/6
  aggregate_test_pnl=+31.8855
  pass_gate=0

buy_leg_only+max_spread_atr_0.10:
  fold_pass=1/6
  test_pass=2/6
  aggregate_test_pnl=+31.8855
  pass_gate=0
```

Decision:

```text
Phase168A failed.
No predeclared filter confirmed the locked 1H candidate.
Stop the current 1H locked-candidate route.
Do not train a model around this rule/filter set.
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```
