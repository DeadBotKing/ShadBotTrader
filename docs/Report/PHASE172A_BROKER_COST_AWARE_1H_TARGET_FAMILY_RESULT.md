# PHASE172A — Broker-cost-aware 1H Target-family Design Audit Result

## Status

```text
COMPLETED — target-family structural gates passed
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
candidate_families                    : 4
ready_families                        : 3
selected_family_id                    : CA1_BRK_MID
selected_family_ready_gate            : 1
target_family_ready_for_training_gate : 1
primary spread                        : fixed 0.4
stress spread                         : fixed 0.5
```

Important interpretation:

```text
Phase172A passed target-family structural/design gates.
It did not approve a trading strategy.
It did not train a model.
It did not open paper/live.
```

## Selected family: CA1_BRK_MID

```text
family_id              : CA1_BRK_MID
label                  : cost_breakout_mid
side_mapping           : breakout
entry_delay_bars       : 1
recent_window_bars     : 24
pivot_zone_atr         : 0.10
top_position_threshold : 0.85
bottom_position        : 0.15
tp_atr                 : 2.0
sl_atr                 : 1.0
hold_bars              : 24
spread                 : fixed 0.4
stress_spread          : fixed 0.5
```

### Label / target statistics

```text
train_events      : 775
validation_events : 184
test_events       : 202

train_positive_rate      : 0.30838709677419357
validation_positive_rate : 0.3641304347826087
test_positive_rate       : 0.3712871287128713

validation_label_psi : 0.01394638636661747
test_label_psi       : 0.017673124891912508
```

Target-label stability is good:

```text
label_stability_gate = 1
density_gate         = 1
walkforward_gate     = 1
stress_gate          = 1
family_ready_gate    = 1
```

### Economic diagnostics for CA1

```text
train_independent_pf      : 0.8623213243072413
validation_independent_pf : 1.0820911290161364
test_independent_pf       : 1.1811023622047232

train_chrono_pf           : 0.8452504141461508
validation_chrono_pf      : 1.1887086783012621
test_chrono_pf            : 1.102220817710059

stress_test_independent_pf: 1.156249999999999
stress_test_chrono_pf     : 1.090608806221245
```

Caution:

```text
CA1 is target-structure-ready, but its raw train replay economics are negative.
This means it is not a deployable rule. A future model would need to learn to filter/select within this target family.
```

## Other ready families

### CA3_BRK_STRICT

```text
family_ready_gate       : 1
train_events            : 344
validation_events       : 68
test_events             : 82
train_positive_rate     : 0.3314
validation_positive_rate: 0.3971
test_positive_rate      : 0.3659
walkforward_pass_ratio  : 1.0
test_chrono_pf          : 1.3164
stress_test_chrono_pf   : 1.3164
```

Caution:

```text
CA3 is stricter and has fewer events, but it also passed structural gates.
It is a viable backup target family for a later learnability comparison.
```

### CA2_BRK_WIDE

```text
family_ready_gate       : 1
train_events            : 574
validation_events       : 144
test_events             : 141
walkforward_pass_ratio  : 0.8333
test_independent_pf     : 1.4390
test_chrono_pf          : 1.3016
stress_test_chrono_pf   : 1.1766
```

Caution:

```text
CA2 has wider geometry and stronger test economic diagnostics, but train economics are poor.
It can be used as a backup/comparison target family, not a standalone rule.
```

## Rejected family

### CA4_REV_MID

```text
family_ready_gate : 0
stress_gate       : 0
warnings          : ["stress spread gate failed"]
```

Economic diagnostics were weak:

```text
validation_independent_pf : 0.6595
test_independent_pf       : 0.8308
validation_chrono_pf      : 0.5919
test_chrono_pf            : 0.8139
```

Decision:

```text
Do not continue with CA4_REV_MID reversal target now.
```

## Key conclusion

```text
The new broker-cost-aware 1H breakout target-family route is structurally viable.
CA1_BRK_MID is selected as the primary target family.
CA3_BRK_STRICT and CA2_BRK_WIDE are viable backups for comparison.
CA4_REV_MID is rejected.
```

However:

```text
A target family passing structural gates is not the same as a profitable strategy.
Raw train replay for CA1 is negative.
Therefore the next phase must be learnability/model-preflight, not paper/live and not immediate production training.
```

## Decision

```text
Proceed to Phase173A only.
No production.
No paper shadow.
No live trading.
No Phase134.
```

## Recommended next phase

```text
Phase173A — Broker-cost-aware 1H Target Learnability / Dataset Build Audit
```

Purpose:

```text
1. Build a supervised target dataset for CA1_BRK_MID.
2. Include CA3/CA2 as backup comparison targets.
3. Check class balance and time split stability.
4. Run non-neural baseline learnability diagnostics.
5. Confirm whether POSITIVE vs NEGATIVE labels are learnable before any deep model training.
```

Suggested Phase173A gates:

```text
min train/validation/test labeled events
positive/negative class balance
validation/test label PSI
baseline AP lift over base rate
balanced accuracy over naive baseline
walk-forward label learnability
no training of production model yet
```
