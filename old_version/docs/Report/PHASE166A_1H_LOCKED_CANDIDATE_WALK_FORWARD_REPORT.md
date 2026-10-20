# PHASE166A — 1H Locked Candidate Walk-Forward / Anti-Overfit Replay Report

## Summary

Phase166A implements the next required anti-overfit diagnostic after Phase165A passed a static split lockdown. It keeps the exact same 1H fixed-spread breakout candidate and replays it across rolling chronological folds.

No model is trained. No grid search is performed. No production/paper/live approval is granted.

## Implemented files

```text
scripts/replay_pivot_1h_locked_candidate_walk_forward.py
tests/unit/ai/test_pivot_1h_walk_forward.py
```

GUI integration:

```text
CommandKind.REPLAY_PIVOT_1H_LOCKED_CANDIDATE_WALK_FORWARD
GUI label: Replay 1H locked candidate walk-forward
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

## Walk-forward defaults

```text
fold_train_bars      : 18000
fold_validation_bars : 4000
fold_test_bars       : 4000
fold_step_bars       : 4000
purge_gap            : 24
```

## Pass criteria

Aggregate pass requires:

```text
folds >= 5
fold_pass_ratio >= 0.55
test_pass_ratio >= 0.60
median_test_profit_factor >= 1.05
aggregate_test_cash_pnl > 0
worst_test_max_drawdown_cash <= 25
```

Each fold uses train/validation/test split gates and monthly stability gates. This is stricter than Phase165A's one static split.

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

## Recommended command

Prefer the Dashboard command:

```text
Replay 1H locked candidate walk-forward
```

Equivalent PowerShell:

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

## Verification

```text
python -m py_compile scripts/replay_pivot_1h_locked_candidate_walk_forward.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black were not available in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase166A walk-forward diagnostic only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase166A on the full local 1H dataset.

```text
folds                     : 6
fold_pass_count           : 0
fold_pass_ratio           : 0.0
test_pass_count           : 4
test_pass_ratio           : 0.6666666666666666
aggregate_test_cash_pnl   : +38.640147609608306
median_test_profit_factor : 1.383576104732664
walk_forward_pass_gate    : 0
```

Key conclusion:

```text
The locked candidate has positive out-of-sample test diagnostics in 4/6 folds, but it fails the full anti-overfit walk-forward protocol because train/validation/monthly stability is not reliable.
```

Detailed result:

```text
docs/Report/PHASE166A_1H_LOCKED_CANDIDATE_WALK_FORWARD_RESULT.md
```

Recommended next diagnostic:

```text
Phase167A — 1H Locked Candidate Regime / Failure Attribution Audit
```
