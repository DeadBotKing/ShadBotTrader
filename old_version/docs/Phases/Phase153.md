# Phase153A — Pivot Target Redesign Candidate Build/Audit

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production approval is granted by this phase.

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase151A showed that raw Option B validation edge did not transfer to test across seeds. Phase152A then showed the important cause:

```text
Categorical SELL/HOLD/BUY label counts are fairly stable.
Continuous payoff/R targets flip regime between validation and test.
```

So the next step is **not** another blind training run. Phase153A turns the two most stable label configurations from Phase152A into real tensor artifacts and audits them before any new training.

## Implemented executable

```text
scripts/run_pivot_target_redesign_candidate_audit.py
```

## GUI command

```text
Build/audit pivot target redesign candidates
```

This satisfies the owner rule that every executable phase must be reachable from the Dashboard/GUI.

## Default candidates

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

The GUI/CLI candidate string is:

```text
C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25
```

## What Phase153A does

For each candidate, the script:

1. Builds a candidate sequence tensor through the existing Phase145A builder.
2. Runs the official Phase145A sequence tensor health audit.
3. Runs the Phase152A label/target stability audit on the candidate flat/meta universe.
4. Produces a consolidated candidate report.

## Candidate output names

```text
pivot_pattern_sequence_tensor_c1_stable_latest
pivot_pattern_sequence_tensor_c2_dense_latest
```

Expected candidate artifacts:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c1_stable_latest.parquet

datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c2_dense_latest.parquet
```

## Aggregate outputs

```text
run_logs\pivot_target_redesign_candidates\latest.json
run_logs\pivot_target_redesign_candidates\latest.html
run_logs\pivot_target_redesign_candidates\latest.csv
```

Per-candidate outputs are stored under:

```text
run_logs\pivot_target_redesign_candidates\c1_stable\build\latest.json
run_logs\pivot_target_redesign_candidates\c1_stable\health\latest.json
run_logs\pivot_target_redesign_candidates\c1_stable\stability\latest.json

run_logs\pivot_target_redesign_candidates\c2_dense\build\latest.json
run_logs\pivot_target_redesign_candidates\c2_dense\health\latest.json
run_logs\pivot_target_redesign_candidates\c2_dense\stability\latest.json
```

## Gate logic

Phase153A reports these gates per candidate:

```text
label_stability_pass_gate
  health_status == PASS
  and validation_psi_vs_train <= psi_warning_threshold
  and test_psi_vs_train <= psi_warning_threshold

target_payoff_warning_gate
  1 if target_buy_r or target_sell_r mean flips sign from validation to test

candidate_ready_for_training_gate
  label_stability_pass_gate == 1
  and target_payoff_warning_gate == 0
```

This gate is intentionally stricter than a label-count check. C1/C2 may improve label density/stability, but the continuous payoff targets can still drift. The script reports that explicitly.

## Recommended GUI execution

```text
Dashboard → AI → Build/audit pivot target redesign candidates → Run
```

Recommended field values:

```text
Candidates            : C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25
Build max samples     : 0
Audit max samples     : 24000
Health full scan      : 1
Skip existing tensors : 0
Output dir            : run_logs/pivot_target_redesign_candidates
```

## Equivalent PowerShell command

```powershell
python -u scripts\run_pivot_target_redesign_candidate_audit.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --source-mode storage `
  --candidates "C1:stable:24:0.75:0.25:1.0;C2:dense:24:0.5:0.5:1.25" `
  --recent-window-bars 48 `
  --window-size 100 `
  --sample-stride 1 `
  --build-max-samples 0 `
  --audit-max-samples 24000 `
  --include-source-5m-features 1 `
  --max-features 0 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --chunk-size 512 `
  --max-tensor-mb 8192 `
  --health-full-scan 1 `
  --health-max-scan-samples 0 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --psi-warning-threshold 0.20 `
  --storage-root datasets `
  --output-dir run_logs\pivot_target_redesign_candidates `
  --report-title "Phase153A pivot target redesign candidate build/audit"
```

## Interpretation rules

```text
PASS health + stable label PSI means the candidate tensor is safe to train diagnostically.
It does not mean trading edge exists.
If payoff sign flip remains, train with caution or redesign the R target/loss before training.
If candidate_ready_for_training_gate=0, do not train that candidate blindly.
```

## Execution result

The owner ran Phase153A on C1 and C2.

Result:

```text
completed_candidates      : 2
label_stable_candidates   : 2
training_ready_candidates : 0
```

Both candidate tensors were healthy:

```text
C1 tensor shape : [53098, 100, 140]
C2 tensor shape : [53098, 100, 140]
health_status   : PASS for both
nonfinite_cells : 0 for both
health_max_abs  : 8.0 for both
```

Both candidates were label-stable:

```text
C1 validation/test PSI : 0.0010691657 / 0.0073619577
C2 validation/test PSI : 0.0014521958 / 0.0071221864
```

But both candidates still had payoff/R sign flip:

```text
train_buy_r_mean      = -0.0352140814
validation_buy_r_mean = -0.0586298741
test_buy_r_mean       = +0.0167183634

train_sell_r_mean      = +0.0352140814
validation_sell_r_mean = +0.0586298741
test_sell_r_mean       = -0.0167183634
```

Final gate:

```text
C1 candidate_ready_for_training_gate = 0
C2 candidate_ready_for_training_gate = 0
```

## Decision

```text
Do not train Option B on C1/C2 now.
C1/C2 fixed label-count/density stability, but did not solve payoff/R target regime drift.
```

## Next phase

```text
Phase154A — Pivot Payoff/Trade-Outcome Target Redesign Audit
```

Phase154A must redesign and audit the tradable payoff/first-hit target itself before any new model training.
