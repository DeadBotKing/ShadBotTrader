# PHASE157A — Payoff Target Learnability Result

## Status

```text
COMPLETED — learnability gates failed
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
completed_candidates : 2
learnable_candidates : 0
best_candidate_id    : B2
best_candidate_reason: no gate pass; best diagnostic score only
```

## B4 result

Class balance:

```text
train actionable      : 644 / 16800 = 3.8333%
validation actionable : 158 / 3264  = 4.8407%
test actionable       : 142 / 3264  = 4.3505%
```

Full 3-class baseline:

```text
always_hold_validation_accuracy : 0.9515931373
always_hold_test_accuracy       : 0.9564950980
full3_validation_accuracy       : 0.9515931373
full3_test_accuracy             : 0.9564950980
full3_balanced_accuracy         : 0.3333333333 / 0.3333333333
```

Actionable-vs-HOLD:

```text
binary_validation_base_rate       : 0.0484068627
binary_validation_ap              : 0.1722548759
binary_validation_ap_lift         : +0.1238480131
binary_test_base_rate             : 0.0435049020
binary_test_ap                    : 0.0561184764
binary_test_ap_lift               : +0.0126135744
binary_validation_balanced_acc    : 0.5
binary_test_balanced_acc          : 0.5
binary_validation_f1              : 0.0
binary_test_f1                    : 0.0
```

Candidate-only side:

```text
side_train_rows              : 644
side_validation_rows         : 158
side_test_rows               : 142
side_validation_buy_ap       : 0.8666607330
side_test_buy_ap             : 0.8925912570
side_validation_balanced_acc : 0.5
side_test_balanced_acc       : 0.5
```

Gate:

```text
actionability_learnability_gate : 0
side_learnability_gate          : 0
candidate_learnability_gate     : 0
```

## B2 result

Class balance:

```text
train actionable      : 531 / 16800 = 3.1607%
validation actionable : 137 / 3264  = 4.1973%
test actionable       : 117 / 3264  = 3.5846%
```

Full 3-class baseline:

```text
full3_validation_accuracy       : 0.9580269608
full3_test_accuracy             : 0.9641544118
full3_balanced_accuracy         : 0.3333333333 / 0.3333333333
```

Actionable-vs-HOLD:

```text
binary_validation_ap_lift       : +0.1500396355
binary_test_ap_lift             : +0.0118765579
binary_balanced_accuracy        : 0.5 / 0.5
binary_f1                       : 0.0 / 0.0
```

Candidate-only side:

```text
side_validation_buy_ap          : 0.9235997639
side_test_buy_ap                : 0.9172319370
side_balanced_accuracy          : 0.5 / 0.5
```

Gate:

```text
candidate_learnability_gate = 0
```

## Interpretation

The full-universe 3-class target is too sparse and HOLD-dominant for the current learning path.

```text
A model can score high accuracy by predicting HOLD.
The simple 3-class baseline does exactly that.
The binary actionability signal has validation AP lift but does not transfer meaningfully to test.
```

However, the candidate-only side AP is high:

```text
B4 side BUY AP validation/test = 0.8667 / 0.8926
B2 side BUY AP validation/test = 0.9236 / 0.9172
```

This suggests side ranking may be learnable once a valid candidate universe exists. The weak part is discovering actionable rows from the entire 5M universe.

## Decision

```text
Reject further blind deep training on the current full-universe SELL/HOLD/BUY payoff target.
Keep B4/B2 target work as useful evidence, but reframe the problem around live-known pivot-zone candidates.
```

## Recommended next phase

```text
Phase158A — Pivot Zone Candidate / Actionability Reframe Audit
```

Goal:

```text
Define live-known candidate rows by recent top/bottom pivot-zone geometry.
Inside that candidate universe, audit:
  win/actionability learnability
  side BUY/SELL learnability
  expected payoff score stability
```

Production remains blocked.
