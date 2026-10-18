# PHASE182A — Entry Event Failure Attribution Result

## Status

```text
COMPLETED — failure attributed; no model training approved
Production — BLOCKED
```

No production/paper/live approval:

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Top-level result

```text
source_symbol                         : XAUUSD
source_timeframes                     : 1H, 4H, 1D
source_ready_families                 : 0
source_entry_event_discovery_ready_gate: 0
family_rows                           : 9
near_miss_families                    : 3
selected_focus_timeframe              : 1D
selected_focus_family_id              : E3_CONTINUATION
selected_focus_family_type            : continuation
selected_primary_failure_reason       : mfe_mae_gate_failed
selected_next_route_id                : ENTRY_QUALITY_GEOMETRY_REDESIGN
selected_next_phase                   : Phase183A — entry quality-geometry candidate audit
no_training_gate                      : 1
no_paper_live_gate                    : 1
```

## Root-cause summary

```text
Phase181B did not fail because of data health or broker cost.
Entry events are often stable and feature-separable, but triggered entries fail MFE/MAE quality, replay economics and walk-forward transfer.
```

Dominant failure reasons:

```text
mfe_mae_gate_failed              : 9/9 = 1.0000
walkforward_pass_ratio_failed    : 9/9 = 1.0000
entry_family_ready_gate_failed   : 9/9 = 1.0000
```

Interpretation:

```text
The market states are not random: several families have good density, balance, temporal stability, feature separation and cost feasibility.
But the current trigger/entry/quality geometry is not clean enough after entry.
The move often does not reach the required MFE before MAE, and no family transfers through walk-forward folds.
```

## Selected focus — 1D E3_CONTINUATION

```text
timeframe                  : 1D
family_id                  : E3_CONTINUATION
family_type                : continuation
primary_failure_reason      : mfe_mae_gate_failed
near_miss_gate              : 1
attribution_bucket          : QUALITY_AND_REPLAY_FAILURE
recommendation              : Redesign trigger/entry/quality geometry before considering any model.
```

Metrics:

```text
train/validation/test events       : 301 / 65 / 74
train/validation/test quality pass : 0.3189 / 0.2923 / 0.4459
train/validation/test replay PF    : 0.7631 / 0.6793 / 1.2878
train/validation/test feature SMD  : 1.4523 / 1.5859 / 1.3483
walk-forward pass                  : 0/4
```

Quality geometry:

```text
current_mfe_atr                       : 1.2
current_mae_atr                       : 0.75
triggered_events                      : 442
mfe_p50 / p75 / p90                   : 0.7019 / 1.4035 / 1.8373
mae_p50 / p75 / p90                   : 0.8306 / 1.0864 / 1.4646
pct_mfe_ge_current                    : 0.3643
pct_mae_le_current                    : 0.3484
pct_mfe_ge_current_and_mae_le_current : 0.3394
median_trigger_delay_bars             : 1.0
trigger_delay_p75_bars                : 1.0
quality_geometry_verdict              : MAE_LIMIT_TOO_TIGHT_OR_ENTRY_LATE
```

Interpretation:

```text
1D E3_CONTINUATION is the best diagnostic focus because it has strong feature separation and positive test replay PF.
However, train and validation replay PF are below 1, and walk-forward is 0/4.
The geometry verdict says the current MAE limit is too tight or the entry is too late, not that the family is ready.
```

## Other near-miss families

### 4H E2_PULLBACK_REJECTION

```text
near_miss_gate                  : 1
train/validation/test events    : 428 / 134 / 109
train/validation/test quality   : 0.2827 / 0.2910 / 0.3303
train/validation/test PF        : 0.8003 / 0.8211 / 1.0632
walk-forward pass               : 0/4
bucket                          : QUALITY_AND_REPLAY_FAILURE
```

Quality geometry:

```text
current_mfe_atr                       : 1.5
current_mae_atr                       : 0.75
pct_mfe_ge_current                    : 0.3159
pct_mae_le_current                    : 0.3025
pct_mfe_ge_current_and_mae_le_current : 0.2921
verdict                               : MFE_TOO_FAR_AND_MAE_TOO_TIGHT
```

### 4H E3_CONTINUATION

```text
near_miss_gate                  : 1
train/validation/test events    : 1398 / 313 / 365
train/validation/test quality   : 0.2682 / 0.2556 / 0.3562
train/validation/test PF        : 0.6066 / 0.5658 / 0.9219
walk-forward pass               : 0/4
bucket                          : QUALITY_AND_REPLAY_FAILURE
```

Quality geometry:

```text
current_mfe_atr                       : 1.2
current_mae_atr                       : 0.75
pct_mfe_ge_current                    : 0.3288
pct_mae_le_current                    : 0.3004
pct_mfe_ge_current_and_mae_le_current : 0.2821
verdict                               : MFE_TOO_FAR_AND_MAE_TOO_TIGHT
```

## Side-level observation

The only side-level near-miss was:

```text
1D | E2_PULLBACK_REJECTION | BUY
triggered_events      : 59
quality_pass_rate     : 0.3559
mean_mfe_atr          : 0.9998
mean_mae_atr          : 0.9337
mfe_mae_ratio         : 1.0708
replay_profit_factor  : 1.1053
mean_replay_score_atr : +0.0508
side_verdict          : SIDE_NEAR_MISS
```

Important caveat:

```text
This is side-level evidence only.
The full 1D E2 family failed validation/test replay and walk-forward, so it is not training-ready.
It may be useful only as a diagnostic side-specific candidate in a later geometry audit.
```

## Timeframe attribution

```text
4H:
  family_count               : 3
  near_miss_families         : 2
  best_family                : E2_PULLBACK_REJECTION
  best_test_quality_pass     : 0.3303
  best_test_replay_PF        : 1.0632
  best_walkforward_pass      : 0.0
  verdict                    : NEAR_MISS_ONLY

1D:
  family_count               : 3
  near_miss_families         : 1
  best_family                : E3_CONTINUATION
  best_test_quality_pass     : 0.4459
  best_test_replay_PF        : 1.2878
  best_walkforward_pass      : 0.0
  verdict                    : NEAR_MISS_ONLY

1H:
  family_count               : 3
  near_miss_families         : 0
  best_family                : E2_PULLBACK_REJECTION
  best_test_quality_pass     : 0.2922
  best_test_replay_PF        : 0.9508
  best_walkforward_pass      : 0.0
  verdict                    : NO_USABLE_ENTRY_FAMILY
```

Interpretation:

```text
1H is the weakest route in this Phase182A evidence.
4H and 1D have near-miss pockets, but no walk-forward transfer.
```

## Walk-forward attribution

Every family had:

```text
pass_folds = 0/4
walkforward_verdict = WF_ZERO_TRANSFER
```

For selected focus:

```text
1D E3_CONTINUATION:
  train_gate_failed_folds      : 4/4
  validation_gate_failed_folds : 4/4
  test_gate_failed_folds       : 4/4
  worst_test_quality_pass      : 0.2963
  best_test_quality_pass       : 0.4412
```

Interpretation:

```text
The failure is not one bad split. It is a systematic fold-transfer failure.
```

## Decision matrix

```text
ENTRY_EVENT_MODEL_TRAINING       : BLOCKED
ENTRY_QUALITY_GEOMETRY_REDESIGN  : RECOMMENDED_DIAGNOSTIC, score=82.0
PAPER_OR_LIVE                    : BLOCKED
```

## Decision

```text
Do not train.
Do not open Phase134.
Do not run paper shadow.
Do not run live trading.
Do not relax gates.
```

## Recommended next phase

```text
Phase183A — Entry Quality-Geometry Candidate Audit
```

Purpose:

```text
Test whether trigger placement, MFE target or MAE limit can be redesigned without blindly relaxing gates.
```

Recommended diagnostic focus:

```text
1D | E3_CONTINUATION
4H | E2_PULLBACK_REJECTION
4H | E3_CONTINUATION
```

Optional side-level diagnostic focus:

```text
1D | E2_PULLBACK_REJECTION | BUY-only
```

Phase183A must remain:

```text
Diagnostic only.
No model training.
No paper/live.
No gate relaxation.
```

## Production status

```text
BLOCKED — Phase182A is attribution only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```
