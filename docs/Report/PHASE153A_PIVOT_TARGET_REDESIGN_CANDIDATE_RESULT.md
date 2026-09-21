# PHASE153A — Pivot Target Redesign Candidate Result

## Status

```text
COMPLETED — candidates built/audited
RESULT — label stability passed, payoff target sign-flip remained
Production — BLOCKED
```

No production/paper/live approval.

```text
No Phase134.
No paper shadow.
No live trading.
```

## Input candidates

```text
C1 stable:
  lookahead_bars     = 24
  pivot_move_atr     = 0.75
  pivot_zone_atr     = 0.25
  min_direction_edge = 1.0

C2 dense:
  lookahead_bars     = 24
  pivot_move_atr     = 0.5
  pivot_zone_atr     = 0.5
  min_direction_edge = 1.25
```

## Output artifacts

```text
run_logs\pivot_target_redesign_candidates\latest.json
run_logs\pivot_target_redesign_candidates\latest.html
run_logs\pivot_target_redesign_candidates\latest.csv
```

Candidate tensors:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c1_stable_latest.parquet

datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c2_dense_latest.parquet
```

## Health result

Both candidates built full-source healthy sequence tensors:

```text
C1 tensor shape : [53098, 100, 140]
C2 tensor shape : [53098, 100, 140]
health_status   : PASS for both
nonfinite_cells : 0 for both
health_max_abs  : 8.0 for both
health_errors   : []
health_warnings : []
```

## Label stability result

Both candidates passed split-level label stability:

```text
C1 validation PSI : 0.0010691657
C1 test PSI       : 0.0073619577
C1 label gate     : PASS

C2 validation PSI : 0.0014521958
C2 test PSI       : 0.0071221864
C2 label gate     : PASS
```

Actionable density:

```text
C1 train / validation / test actionable:
  6.6845% / 6.8627% / 7.6593%

C2 train / validation / test actionable:
  23.7381% / 23.0392% / 26.8689%
```

Interpretation:

```text
C1 gives fewer, conservative labels.
C2 gives denser labels.
Both are split-level label-stable.
```

## Critical payoff-target result

Both candidates kept the same validation-to-test payoff/R sign flip:

```text
C1 and C2:
  train_buy_r_mean      = -0.0352140814
  validation_buy_r_mean = -0.0586298741
  test_buy_r_mean       = +0.0167183634

  train_sell_r_mean      = +0.0352140814
  validation_sell_r_mean = +0.0586298741
  test_sell_r_mean       = -0.0167183634

  buy_r_sign_flip  = 1
  sell_r_sign_flip = 1
```

Gate outcome:

```text
C1 target_payoff_warning_gate       = 1
C1 candidate_ready_for_training_gate = 0

C2 target_payoff_warning_gate       = 1
C2 candidate_ready_for_training_gate = 0
```

## Technical interpretation

Phase153A succeeded as a diagnostic because it prevented blind training on targets that still have payoff-regime instability.

The important distinction is:

```text
Label counts/density were fixed enough.
Payoff/R target sign flip was not fixed.
```

Why C1 and C2 share the same R means:

```text
Both candidates use lookahead_bars=24.
The continuous R targets are driven by future_up_r / future_down_r over that lookahead.
Changing pivot_move_atr / pivot_zone_atr / min_direction_edge changes action-label density, but it does not remove the underlying 24-bar payoff sign flip.
```

## Decision

```text
Do NOT train Option B on C1/C2 as the next step.
Do NOT promote C1/C2 to model training merely because health and label PSI passed.
The current target problem is no longer label-count instability; it is payoff-target regime drift.
```

## Recommended next phase

```text
Phase154A — Pivot Payoff/Trade-Outcome Target Redesign Audit
```

Goal:

```text
Redesign and audit the continuous/tradable target itself, not only the top/bottom action label density.
```

Candidate direction for Phase154A:

```text
1. First-hit / barrier-based trade-outcome labels:
   BUY only if upside barrier is hit before downside barrier within lookahead.
   SELL only if downside barrier is hit before upside barrier within lookahead.
   HOLD if neither side wins or the event is ambiguous.

2. Audit payoff stability by split and month before training.

3. Only if payoff stability passes, build tensors and then train a diagnostic model.
```

## Production status

```text
BLOCKED — Phase153A is research-only.
No Phase134.
No paper shadow.
No live trading.
```
