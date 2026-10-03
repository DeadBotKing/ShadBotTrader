# Phase166A — 1H Locked Candidate Walk-Forward / Anti-Overfit Replay

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

Phase165A locked one nonzero-cost 1H breakout candidate and passed a static split:

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
lockdown_gate    : 1
```

But a static train/validation/test split can still be overfit. Phase166A keeps the exact same locked candidate and runs rolling chronological folds. It does not run any grid search and does not change the candidate.

## Implemented executable

```text
scripts/replay_pivot_1h_locked_candidate_walk_forward.py
```

## GUI command

```text
Replay 1H locked candidate walk-forward
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

## Default walk-forward protocol

```text
fold_train_bars      : 18000
fold_validation_bars : 4000
fold_test_bars       : 4000
fold_step_bars       : 4000
purge_gap            : 24
max_folds            : 0/off
```

For each fold:

```text
train segment      -> stability gate
validation segment -> confirmation gate
test segment       -> final fold confirmation
```

No parameter is selected or optimized per fold.

## Aggregate pass gates

```text
min_folds                    : 5
min_fold_pass_ratio          : 0.55
min_test_pass_ratio          : 0.60
min_median_test_profit_factor: 1.05
min_aggregate_test_cash_pnl  : 0.0
max_worst_test_drawdown      : 25.0
```

Each split inside a fold reuses Phase165A style gates:

```text
train_min_trades             : 50
train_min_profit_factor      : 1.00
validation_min_trades        : 20
validation_min_profit_factor : 1.10
test_min_trades              : 20
test_min_profit_factor       : 1.10
min_positive_month_ratio     : 0.50
max_worst_month_loss         : 12.0
```

## Outputs

```text
run_logs\pivot_1h_locked_candidate_walk_forward\latest.json
run_logs\pivot_1h_locked_candidate_walk_forward\latest.html
run_logs\pivot_1h_locked_candidate_walk_forward\latest_folds.csv
run_logs\pivot_1h_locked_candidate_walk_forward\latest_fold_splits.csv
run_logs\pivot_1h_locked_candidate_walk_forward\latest_trades.csv
run_logs\pivot_1h_locked_candidate_walk_forward\latest_monthly.csv
run_logs\pivot_1h_locked_candidate_walk_forward\latest_stress.csv
```

## Recommended GUI action

Use the Dashboard command:

```text
Replay 1H locked candidate walk-forward
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\replay_pivot_1h_locked_candidate_walk_forward.py `
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
  --output-dir run_logs\pivot_1h_locked_candidate_walk_forward `
  --report-title "Phase166A 1H locked candidate walk-forward replay"
```

## Decision after owner run

If `walk_forward_pass_gate=1`, the locked 1H candidate survives the anti-overfit replay and the next phase may design a 1H target/model around the locked rule.

If `walk_forward_pass_gate=0`, do not train a model; inspect which folds failed and whether the locked rule is regime-specific.

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/replay_pivot_1h_locked_candidate_walk_forward.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Owner execution result

The owner ran Phase166A on the full local 1H dataset.

Top-level:

```text
folds                     : 6
fold_pass_count           : 0
fold_pass_ratio           : 0.0
test_pass_count           : 4
test_pass_ratio           : 0.6666666666666666
aggregate_test_cash_pnl   : +38.640147609608306
median_test_profit_factor : 1.383576104732664
worst_test_profit_factor  : 0.7849777518968888
worst_test_cash_pnl       : -5.560744993965023
worst_test_max_drawdown   : 6.86223346129448
walk_forward_pass_gate    : 0
```

Interpretation:

```text
The locked 1H candidate did not pass anti-overfit walk-forward gates.
The test side is encouraging (4/6 tests passed and aggregate test PnL is positive), but no fold passed the full train+validation+test+monthly gates.
```

Main failure sources:

```text
train stability failed in 5/6 folds
monthly_stability_gate = 0 in all folds
stress_transfer_pass_gate = 0 in all folds
validation failed in folds 2,5,6
test failed in folds 1 and 4
```

Decision:

```text
Phase166A failed.
Do not train a 1H model yet.
Do not proceed to paper/live/Phase134.
```

Recommended next diagnostic:

```text
Phase167A — 1H Locked Candidate Regime / Failure Attribution Audit
```

Purpose:

```text
Explain why 4/6 test folds passed but 0/6 full folds passed.
Specifically audit ATR/spread regime, year/month clustering, BUY-vs-SELL legs, and whether failures are regime-specific.
```
