# PHASE154A — Pivot Payoff Target Redesign Result

## Status

```text
COMPLETED — target audit produced two training-ready payoff-stable candidates
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
completed_candidates      : 6
label_stable_candidates   : 6
payoff_stable_candidates  : 2
tensor_ready_candidates   : 2
best_candidate_id         : B4
best_candidate_reason     : ready candidate with best test selected_trade_r_mean diagnostic
```

## Candidate outcomes

### Rejected due to payoff sign flip

```text
B1 balanced_24_rr1
B3 dense_24_half_atr
B5 short_12_rr1
B6 wide_36_rr1
```

These candidates continued the old Phase152/153 issue:

```text
BUY score mean flips sign from validation to test.
SELL score mean flips sign from validation to test.
```

### Training-ready candidates

#### B4 — preferred

```text
candidate_id       : B4
label              : asym_24_tp1_sl05
lookahead_bars     : 24
pivot_zone_atr     : 0.35
tp_atr             : 1.0
sl_atr             : 0.5
min_score_edge     : 0.1
```

Split stability:

```text
train_actionable_rate      : 0.0383333333
validation_actionable_rate : 0.0484068627
test_actionable_rate       : 0.0435049020
validation_psi_vs_train    : 0.0060523732
test_psi_vs_train          : 0.0125569364
```

Payoff stability:

```text
train_buy_score_mean      : -0.0790178571
validation_buy_score_mean : -0.0755208333
test_buy_score_mean       : -0.0503982843

train_sell_score_mean      : -0.0451785714
validation_sell_score_mean : -0.0422794118
test_sell_score_mean       : -0.0847120098

buy_score_sign_flip  : 0
sell_score_sign_flip : 0
```

Gate:

```text
label_stability_pass_gate       : 1
payoff_stability_pass_gate      : 1
candidate_ready_for_tensor_gate : 1
```

#### B2 — conservative backup

```text
candidate_id       : B2
label              : conservative_24_tp1_sl075
lookahead_bars     : 24
pivot_zone_atr     : 0.25
tp_atr             : 1.0
sl_atr             : 0.75
min_score_edge     : 0.1
```

Split stability:

```text
train_actionable_rate      : 0.0316071429
validation_actionable_rate : 0.0419730392
test_actionable_rate       : 0.0358455882
validation_psi_vs_train    : 0.0046029408
test_psi_vs_train          : 0.0121398704
```

Payoff stability:

```text
buy_score_sign_flip  : 0
sell_score_sign_flip : 0
candidate_ready_for_tensor_gate : 1
```

## Interpretation

Phase154A is the first pivot-target audit that produced candidates passing both:

```text
label stability
payoff stability
```

B4 is preferred because it is slightly denser and uses asymmetric geometry:

```text
TP = 1.0 ATR
SL = 0.5 ATR
```

This may force the target to represent cleaner first-hit winners instead of broad top/bottom zones.

## Critical caveat

This result does **not** prove trading edge.

```text
Phase154A audits target definitions only.
It does not train a model and does not backtest model predictions.
selected_trade_r_mean is mechanically positive because selected labels are first-hit winners.
```

## Decision

```text
Proceed to Phase155A with B4 first.
Keep B2 as backup.
Do not train B1/B3/B5/B6 now.
```

## Recommended next phase

```text
Phase155A — Build payoff-target tensor + diagnostic Option B training for B4/B2
```

Minimum Phase155A protocol:

```text
1. Build candidate tensor/meta for B4 payoff target.
2. Run tensor health audit.
3. Train raw Option B diagnostic model with explicit seed.
4. Backtest validation and test with unchanged gates.
5. If B4 fails transfer, repeat with B2.
6. No test tuning.
7. No paper/live/Phase134.
```
