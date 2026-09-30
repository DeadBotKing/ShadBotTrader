# Phase156A — Payoff-Target Prediction / Threshold Calibration Audit

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

Phase155A trained diagnostic B4/B2 payoff-target Option B models, but fixed thresholds under-selected trades:

```text
B4 validation trades : 1
B4 test trades       : 5
B2 validation trades : 2
B2 test trades       : 22, test PF=0.7425
```

So the next question is:

```text
Does the model contain a usable low-confidence signal that can be extracted with validation-selected thresholds?
Or did it collapse to HOLD/no-trade in a way thresholding cannot rescue?
```

## Implemented executable

```text
scripts/audit_pivot_payoff_prediction_thresholds.py
```

## GUI command

```text
Audit payoff prediction thresholds
```

## Protocol

For each candidate, default B4 and B2:

```text
1. Load the trained payoff Option B model.
2. Predict validation and test splits once.
3. Write probability distribution diagnostics.
4. Scan threshold grid on validation only.
5. Select best validation policy by configured score metric.
6. Confirm exactly that selected policy on test.
```

This keeps test as confirmation-only.

## Candidate format

Default:

```text
B4,B2
```

Which resolves to:

```text
B4 → model_id gold_pivot_payoff_option_b_b4_5m, tensor pivot_payoff_sequence_tensor_b4_latest
B2 → model_id gold_pivot_payoff_option_b_b2_5m, tensor pivot_payoff_sequence_tensor_b2_latest
```

Explicit format is also supported:

```text
ID:model_id:tensor_name
```

## Default threshold grid

```text
buy_thresholds  = 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50
sell_thresholds = 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50
margins         = 0,0.03,0.05,0.10
min_buy_r       = none,0,0.25
min_sell_r      = none,0,0.25
```

`none` maps to the old permissive value:

```text
-999.0
```

This avoids PowerShell negative-argument parsing problems.

## Outputs

```text
run_logs\pivot_payoff_prediction_thresholds\latest.json
run_logs\pivot_payoff_prediction_thresholds\latest.html
run_logs\pivot_payoff_prediction_thresholds\latest_validation_grid.csv
run_logs\pivot_payoff_prediction_thresholds\latest_selection.csv
run_logs\pivot_payoff_prediction_thresholds\latest_probability_summary.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_payoff_prediction_thresholds.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --model-version 0 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 128 `
  --buy-thresholds 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50 `
  --sell-thresholds 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50 `
  --margins 0,0.03,0.05,0.10 `
  --min-buy-r-values none,0,0.25 `
  --min-sell-r-values none,0,0.25 `
  --validation-min-trades 20 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 20 `
  --test-min-profit-factor 1.05 `
  --score-metric drawdown_adjusted `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_prediction_thresholds
```

## Pass/fail logic

Validation policy must pass:

```text
validation_trades >= validation_min_trades
validation_profit_factor >= validation_min_profit_factor
validation_final_balance >= 100
```

Test confirmation must pass:

```text
test_trades >= test_min_trades
test_profit_factor >= test_min_profit_factor
test_final_balance >= 100
```

Final transfer pass requires both.

## Execution result

The owner ran Phase156A on B4/B2.

Result:

```text
selected_candidate_id        : B4
selected_validation_score    : +1.0000
selected_test_profit_factor  : 3.9899
selected_test_final_balance  : 103.0198
selected_transfer_pass_gate  : 0
```

Key probability diagnostics:

```text
B4 validation hold_mean : 0.9814
B4 test hold_mean       : 0.9728
B4 validation buy_p95   : 0.0674
B4 validation sell_p95  : 0.0195
B4 buy_margin_p95       : -0.8387
B4 sell_margin_p95      : -0.8879

B2 validation hold_mean : 0.9850
B2 test hold_mean       : 0.9671
```

Selected validation threshold was already the lowest grid point:

```text
buy_threshold  = 0.05
sell_threshold = 0.05
min_margin     = 0
```

But validation still selected too few trades:

```text
B4 validation trades : 1
B4 test trades       : 5
B2 validation trades : 2
B2 test trades       : 22, test PF=0.7425
```

Decision:

```text
Phase156A failed. Threshold calibration cannot rescue the current B4/B2 trained models.
The action head is HOLD-collapsed / under-selecting.
```

Recommended next phase:

```text
Phase157A — Payoff Target Learnability / Imbalance-Control Diagnostic
```

## Verification

```text
python -m py_compile scripts/audit_pivot_payoff_prediction_thresholds.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_prediction_thresholds.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_prediction_thresholds.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 49 passed
```
