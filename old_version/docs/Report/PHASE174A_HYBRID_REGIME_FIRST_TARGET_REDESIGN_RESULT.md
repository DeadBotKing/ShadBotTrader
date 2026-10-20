# PHASE174A — Hybrid/regime-first Target Redesign Decision Audit Result

## Status

```text
COMPLETED — hybrid/regime-first gates failed
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model-training phase is approved from this result.
```

## Top-level result

```text
symbol                         : XAUUSD
timeframe                      : 1H
flat_path                      : datasets\processed\XAUUSD\1H\v1.parquet
flat_rows                      : 50000
train_rows                     : 35000
validation_rows                : 7476
test_rows                      : 7476
spread_mode                    : fixed
spread_value                   : 0.4
candidate_families             : 3
regime_rules                   : 22
evaluated_regime_candidates    : 66
ready_regime_candidates        : 0
selected_family_id             : CA2_BRK_WIDE
selected_regime_rule_id        : ASIA_UTC_00_06
selected_regime_ready_gate     : 0
hybrid_regime_first_ready_gate : 0
recommendation                 : STOP_OR_REDESIGN_REQUIRED_NO_MODEL_TRAINING
production_status              : BLOCKED — Phase174A hybrid/regime-first target redesign audit only
```

Important interpretation:

```text
Phase174A did not confirm the HYBRID_REGIME_FIRST_REDESIGN route.
No family × regime candidate passed all gates.
The selected candidate is only the best failed diagnostic row, not a training candidate.
```

## Selected diagnostic row — best failed candidate

Selected row:

```text
family_id       : CA2_BRK_WIDE
regime_rule_id  : ASIA_UTC_00_06
regime_label    : asia_utc_00_06
ready_gate      : 0
```

Static split metrics:

```text
train_events      : 154
validation_events : 37
test_events       : 37

train_positive_rate      : 0.2727272727272727
validation_positive_rate : 0.4594594594594595
test_positive_rate       : 0.3783783783783784

validation_label_psi : 0.15280487613528332
test_label_psi       : 0.051176589110582135

train_ap_lift      : 0.1334116970090239
validation_ap_lift : 0.19773694667332936
test_ap_lift       : 0.09002438345309677

validation_balanced_accuracy : 0.5676470588235294
test_balanced_accuracy       : 0.6071428571428571

train_independent_profit_factor      : 0.7415667166416777
validation_independent_profit_factor : 1.6999999999999975
test_independent_profit_factor       : 1.2173913043478277

train_mean_atr_score      : -0.23493934850756568
validation_mean_atr_score : 0.4729729729729707
test_mean_atr_score       : 0.16891891891892002

walkforward_pass_folds : 0 / 6
walkforward_pass_ratio : 0.0
```

Gate diagnosis:

```text
class_balance_gate             : 1
economic_gate                  : 0
static_learnability_gate       : 0
walkforward_learnability_gate  : 0
regime_candidate_ready_gate    : 0
```

Why it failed despite good validation/test diagnostics:

```text
1. Train raw economics are negative: train PF=0.7416 and train mean ATR score=-0.2349.
2. It has only 37 validation events and 37 test events.
3. Walk-forward pass ratio is 0/6.
4. The positive validation/test row therefore looks like a pocket, not a stable target route.
```

## Notable near-misses

### CA1_BRK_MID + WIDTH_GE_Q75

```text
train/validation/test events : 194 / 42 / 54
validation_ap_lift           : 0.1417466843907602
test_ap_lift                 : 0.199135480858877
validation_balanced_accuracy : 0.5588235294117647
test_balanced_accuracy       : 0.5
train/validation/test PF     : 0.9584213251508534 / 1.2922853120600728 / 1.0857142857142843
class_balance_gate           : 1
economic_gate                : 1
static_learnability_gate     : 0
walkforward_pass             : 0/6
```

Interpretation:

```text
Economics were close, but test balanced accuracy stayed at chance and walk-forward failed completely.
```

### CA3_BRK_STRICT + ACTIVE_UTC_07_17

```text
train/validation/test events : 136 / 33 / 29
validation_ap_lift           : 0.011889709111576108
test_ap_lift                 : 0.13920934908003874
validation_balanced_accuracy : 0.6277777777777778
test_balanced_accuracy       : 0.5263157894736842
train/validation/test PF     : 1.0255889926209714 / 1.5726184889723316 / 1.0526315789473657
class_balance_gate           : 1
economic_gate                : 1
static_learnability_gate     : 0
walkforward_pass             : 0/6
```

Interpretation:

```text
This is also not enough: validation AP lift is below the 0.03 gate, test balanced accuracy is below 0.53, and walk-forward is 0/6.
```

### CA3_BRK_STRICT + ALL / MOMENTUM_ALIGNED

```text
class_balance_gate : 1
economic_gate      : 1
static_gate        : 0
walkforward_gate   : 0
```

Reason:

```text
Validation AP lift remained negative and balanced accuracy stayed around chance.
```

## Decision matrix

```text
STOP_PHASE173_DIRECT_TRAINING : MANDATORY, score=100.0
HYBRID_REGIME_FIRST_REDESIGN  : NOT_CONFIRMED, score=35.0
DEEP_MODEL_TRAINING_NOW       : BLOCKED, score=0.0
PAPER_OR_LIVE                 : BLOCKED, score=0.0
```

Decision-matrix evidence:

```text
ready_regime_candidates=0; best=CA2_BRK_WIDE|ASIA_UTC_00_06
```

## Final decision

```text
Phase174A failed.
ready_regime_candidates = 0
hybrid_regime_first_ready_gate = 0
```

Operational decision:

```text
Do not train any CA1/CA3/CA2 regime candidate.
Do not proceed to deep model training.
Do not open Phase134.
Do not paper shadow.
Do not live trade.
```

## Recommended next decision

The current 1H broker-cost-aware target/regime route is not confirmed. The next action requires explicit owner approval.

Recommended options:

```text
Option A — Stop/pause the 1H broker-cost-aware target-family route for manual review.
Option B — Run a new diagnostic-only redesign phase focused on why walk-forward is 0/6 and whether the target definition itself must change.
```

Not allowed:

```text
No Phase175 model training.
No paper/live.
No gate relaxation to force a pass.
```
