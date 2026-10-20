# PHASE155A — Payoff Option B Diagnostic Result

## Status

```text
COMPLETED — no transfer pass
Production — BLOCKED
```

No production/paper/live approval.

```text
No Phase134.
No paper shadow.
No live trading.
```

## Top-level result

```text
completed_candidates         : 2
selected_candidate_id        : B4
selected_model_id            : gold_pivot_payoff_option_b_b4_5m
selected_validation_PF       : 999.0
selected_test_PF             : 3.9898980099
selected_test_final_balance  : 103.01979699
selected_transfer_pass_gate  : 0
```

## B4 result

```text
health_status             : PASS
health_nonfinite_cells    : 0
train_val_action_accuracy : 0.9522058824
train_test_action_accuracy: 0.9525122549
train_val_selected_rate   : 0.0006127451
train_test_selected_rate  : 0.0070465686
validation_trades         : 1
validation_final_balance  : 101.0000
validation_profit_factor  : 999.0
validation_total_cash_pnl : +1.0000
validation_max_drawdown   : 0.0
test_trades               : 5
test_final_balance        : 103.0198
test_profit_factor        : 3.9899
test_total_cash_pnl       : +3.0198
test_max_drawdown         : 1.0100
validation_pass_gate      : 0
test_pass_gate            : 1
transfer_pass_gate        : 0
```

## B2 result

```text
health_status             : PASS
health_nonfinite_cells    : 0
train_val_action_accuracy : 0.9540441176
train_test_action_accuracy: 0.9451593137
train_val_selected_rate   : 0.0039828431
train_test_selected_rate  : 0.0232843137
validation_trades         : 2
validation_final_balance  : 100.2914
validation_profit_factor  : 999.0
validation_total_cash_pnl : +0.2914
test_trades               : 22
test_final_balance        : 97.2088
test_profit_factor        : 0.7425
test_total_cash_pnl       : -2.7912
test_max_drawdown         : 4.1049
transfer_pass_gate        : 0
```

## Interpretation

```text
B4 is positive on the reported test slice, but with only 5 test trades and 1 validation trade.
B2 selects more trades but fails test.
Both candidates fail transfer_pass_gate.
```

The main problem is under-selection:

```text
B4 validation selected rate : 0.0613%
B4 test selected rate       : 0.7047%
B2 validation selected rate : 0.3983%
B2 test selected rate       : 2.3284%
```

High action accuracy is not meaningful here because HOLD is the overwhelming majority class.

## Decision

```text
Reject Phase155A as a valid trading transfer pass.
Keep B4 target as promising but not proven.
Do not train bigger models yet.
```

## Recommended next phase

```text
Phase156A — Payoff-target prediction/threshold calibration audit
```

Required protocol:

```text
1. Load trained B4/B2 models.
2. Archive prediction probability distributions on validation/test.
3. Select thresholds only on validation.
4. Confirm exactly once on test.
5. Reject if trade count remains too low or test fails.
```
