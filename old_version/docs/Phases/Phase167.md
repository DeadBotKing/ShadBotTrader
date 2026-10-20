# Phase167A — 1H Locked Candidate Regime / Failure Attribution Audit

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

Phase166A failed the walk-forward anti-overfit gate:

```text
folds                     : 6
fold_pass_count           : 0
test_pass_count           : 4
aggregate_test_cash_pnl   : +38.6401
median_test_profit_factor : 1.3836
walk_forward_pass_gate    : 0
```

This means the locked 1H candidate has promising test behavior, but train/validation/monthly stability is not robust enough. Phase167A attributes the failures without changing the locked candidate.

## Implemented executable

```text
scripts/audit_pivot_1h_locked_candidate_regime_failures.py
```

## GUI command

```text
Audit 1H locked candidate regime failures
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

## Diagnostic scope

Phase167A attributes failures by:

```text
1. fold-level failure reasons
2. side: BUY vs SELL
3. ATR regime using train-only fold quantiles
4. spread/ATR regime
5. calendar month/year clustering
6. pre-declared diagnostic filters:
   none
   min_atr_q50
   min_atr_q75
   buy_leg_only
   sell_leg_only
   max_spread_atr_0.05
   max_spread_atr_0.10
```

These filters are diagnostic only. They are not production rules and do not authorize model training.

## Outputs

```text
run_logs\pivot_1h_locked_candidate_regime_failures\latest.json
run_logs\pivot_1h_locked_candidate_regime_failures\latest.html
run_logs\pivot_1h_locked_candidate_regime_failures\latest_fold_failures.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_regime_summary.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_side_summary.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_monthly_summary.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_filter_diagnostics.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_filter_summary.csv
run_logs\pivot_1h_locked_candidate_regime_failures\latest_trades.csv
```

## Recommended GUI action

Use the Dashboard command:

```text
Audit 1H locked candidate regime failures
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_pivot_1h_locked_candidate_regime_failures.py `
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
  --diagnostic-filters none,min_atr_q50,min_atr_q75,buy_leg_only,sell_leg_only,max_spread_atr_0.05,max_spread_atr_0.10 `
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
  --output-dir run_logs\pivot_1h_locked_candidate_regime_failures `
  --report-title "Phase167A 1H locked candidate regime failure attribution"
```

## Decision after owner run

If a pre-declared filter explains the failures, the next phase should be a confirmation-only regime-filter replay with that filter locked before running.

If no filter explains the failures, stop the locked candidate route and do not train a model.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_pivot_1h_locked_candidate_regime_failures.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase167A on the full local 1H dataset.

Top-level:

```text
folds                       : 6
baseline_fold_pass_count    : 0
baseline_test_pass_count    : 4
baseline_aggregate_test_pnl : +38.640147609608306
dominant_failure_reason     : monthly_stability_failed
best_filter_name            : buy_leg_only
best_filter_fold_pass_ratio : 0.16666666666666666
recommendation              : REGIME_FILTER_CONFIRMATION_REQUIRED_NO_TRAINING
```

Filter summary:

```text
buy_leg_only:
  fold_pass_ratio=0.1667, test_pass_ratio=0.3333, aggregate_test_pnl=+31.8855

max_spread_atr_0.10:
  fold_pass_ratio=0.0, test_pass_ratio=0.6667, aggregate_test_pnl=+41.8019

none:
  fold_pass_ratio=0.0, test_pass_ratio=0.6667, aggregate_test_pnl=+38.6401
```

Interpretation:

```text
A simple side filter or ATR/spread filter does not robustly solve fold stability.
BUY-only improves full fold pass from 0/6 to 1/6, but cuts test pass from 4/6 to 2/6.
max_spread_atr_0.10 improves aggregate test PnL but leaves fold pass at 0/6.
```

Decision:

```text
No model training.
No Phase134/paper/live.
Only confirmation-only diagnostics are allowed if continuing.
```

Recommended next diagnostic:

```text
Phase168A — 1H Predeclared Filter Confirmation Replay
```

Allowed filters only:

```text
none
max_spread_atr_0.10
buy_leg_only
buy_leg_only + max_spread_atr_0.10
```
