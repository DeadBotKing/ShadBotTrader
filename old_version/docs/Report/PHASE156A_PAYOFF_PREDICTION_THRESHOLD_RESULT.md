# PHASE156A — Payoff Prediction Threshold Calibration Result

## Status

```text
COMPLETED — threshold calibration failed to produce transfer pass
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Top-level result

```text
completed_candidates          : 2
selected_candidate_id         : B4
selected_model_id             : gold_pivot_payoff_option_b_b4_5m
selected_validation_score     : +1.0000
selected_validation_PF        : 999.0
selected_test_PF              : 3.9898980099
selected_test_final_balance   : 103.01979699
selected_transfer_pass_gate   : 0
```

## B4 probability summary

Validation:

```text
rows              : 3264
sell_mean         : 0.0056987470
sell_p95          : 0.0194561769
sell_p99          : 0.1216436231
hold_mean         : 0.9814271331
hold_p50          : 0.9968348742
hold_p90          : 0.9995517969
buy_mean          : 0.0128741264
buy_p95           : 0.0674442567
buy_p99           : 0.1865325461
buy_margin_p95    : -0.8387111396
sell_margin_p95   : -0.8878526121
buy_r_mean        : -0.0520205647
sell_r_mean       : -0.1033089682
```

Test:

```text
sell_mean         : 0.0161933266
sell_p95          : 0.0723583322
sell_p99          : 0.4180042899
hold_mean         : 0.9727998376
buy_mean          : 0.0110068507
buy_p95           : 0.0557466706
buy_p99           : 0.1540270302
buy_margin_p95    : -0.8041839451
sell_margin_p95   : -0.8133451492
```

Interpretation:

```text
B4 action head is overwhelmingly HOLD-dominant.
Even the 95th percentile of BUY/SELL margin is far below zero, meaning BUY/SELL rarely beat HOLD.
```

## B2 probability summary

```text
Validation hold_mean : 0.9849799871
Test hold_mean       : 0.9670653939
Validation buy_p95   : 0.0365082676
Validation sell_p95  : 0.0130226157
```

B2 is also HOLD-dominant.

## Selected threshold policy

For both B4 and B2, validation selected the lowest grid values:

```text
buy_threshold  : 0.05
sell_threshold : 0.05
min_margin     : 0.0
min_buy_r      : -999.0
min_sell_r     : -999.0
```

## B4 calibration result

```text
validation_trades         : 1
validation_final_balance  : 101.0000
validation_profit_factor  : 999.0
validation_total_cash_pnl : +1.0000
validation_pass_gate      : 0

test_trades               : 5
test_final_balance        : 103.0198
test_profit_factor        : 3.9899
test_total_cash_pnl       : +3.0198
test_pass_gate            : 0
transfer_pass_gate        : 0
```

## B2 calibration result

```text
validation_trades         : 2
validation_final_balance  : 100.2914
validation_total_cash_pnl : +0.2914
validation_pass_gate      : 0

test_trades               : 22
test_final_balance        : 97.2088
test_profit_factor        : 0.7425
test_total_cash_pnl       : -2.7912
test_pass_gate            : 0
transfer_pass_gate        : 0
```

## Decision

```text
Reject current Phase155A trained payoff Option B models.
Threshold calibration cannot rescue them.
The issue is HOLD collapse / under-selection in the action head.
```

B4 target remains structurally promising from Phase154A, but the current training setup cannot extract enough actionable predictions.

## Recommended next phase

```text
Phase157A — Payoff Target Learnability / Imbalance-Control Diagnostic
```

Recommended diagnostics:

```text
1. Split-level class imbalance and majority baselines for B4/B2.
2. Candidate-only BUY-vs-SELL learnability test using only target_action != HOLD rows.
3. Binary actionability vs HOLD learnability test.
4. Compare simple tabular/centroid/LightGBM baseline before another deep Option B training.
5. Only if learnability is proven, redesign the neural loss/sampling path.
```

## Production status

```text
BLOCKED
No Phase134.
No paper shadow.
No live trading.
```
