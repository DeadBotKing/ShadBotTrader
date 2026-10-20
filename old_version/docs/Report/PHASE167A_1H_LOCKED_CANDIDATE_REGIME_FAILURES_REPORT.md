# PHASE167A — 1H Locked Candidate Regime / Failure Attribution Audit Report

## Summary

Phase167A has been implemented to diagnose why Phase166A failed despite 4/6 test folds passing.

It keeps the exact locked 1H fixed-spread candidate and attributes failures by fold, ATR/spread regime, side, month/year and pre-declared diagnostic filters.

No model is trained. No grid search is performed. No paper/live/production approval is granted.

## Implemented files

```text
scripts/audit_pivot_1h_locked_candidate_regime_failures.py
tests/unit/ai/test_pivot_1h_regime_failures.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_1H_LOCKED_CANDIDATE_REGIME_FAILURES
GUI label: Audit 1H locked candidate regime failures
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Diagnostic questions

Phase167A answers:

```text
1. Are failures concentrated in low-ATR / high spread-to-ATR regimes?
2. Are failures concentrated in specific years/months?
3. Are BUY or SELL legs responsible for instability?
4. Are train failures caused by older low-volatility regimes while recent test improves?
5. Does a pre-declared volatility/liquidity filter explain the fold failures without curve-fitting?
6. Should the 1H route be stopped, or reframed as regime-conditional only?
```

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

## Recommended command

Prefer the Dashboard command:

```text
Audit 1H locked candidate regime failures
```

Equivalent PowerShell:

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

## Interpretation guide

Important output fields:

```text
dominant_failure_reason
worst_side
worst_side_total_pnl
worst_atr_regime
worst_atr_regime_total_pnl
best_filter_name
best_filter_fold_pass_ratio
recommendation
```

If `best_filter_fold_pass_ratio` improves over `none`, the next step is a confirmation-only filter replay. If it does not improve, the locked candidate should not be trained.

## Verification

```text
python -m py_compile scripts/audit_pivot_1h_locked_candidate_regime_failures.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_1h_regime_failures.py tests/unit/ai/test_pivot_1h_walk_forward.py tests/unit/ai/test_pivot_1h_candidate_lockdown.py tests/unit/ai/test_pivot_1h_spread_bracket_sensitivity.py tests/unit/ai/test_pivot_1h_entry_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in this sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase167A regime/failure attribution only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase167A on the full local 1H dataset.

```text
dominant_failure_reason     : monthly_stability_failed
baseline_fold_pass_count    : 0/6
baseline_test_pass_count    : 4/6
baseline_aggregate_test_pnl : +38.640147609608306
best_filter_name            : buy_leg_only
best_filter_fold_pass_ratio : 0.16666666666666666
recommendation              : REGIME_FILTER_CONFIRMATION_REQUIRED_NO_TRAINING
```

Key conclusion:

```text
No strong regime filter was found. The best fold-pass filter only reaches 1/6 folds and harms test pass count. If continuing, the next phase must be confirmation-only and must not train a model.
```

Detailed result:

```text
docs/Report/PHASE167A_1H_LOCKED_CANDIDATE_REGIME_FAILURES_RESULT.md
```
