# PHASE153A — Pivot Target Redesign Candidate Build/Audit Report

## Summary

Phase153A has been implemented as a research-only diagnostic phase.

It builds and audits the two candidate pivot target configurations selected by Phase152A before any new model training:

```text
C1 stable = lookahead 24, move 0.75 ATR, zone 0.25 ATR, edge 1.0
C2 dense  = lookahead 24, move 0.5 ATR, zone 0.5 ATR, edge 1.25
```

## Implemented files

```text
scripts/run_pivot_target_redesign_candidate_audit.py
tests/unit/ai/test_pivot_target_redesign_candidate_audit.py
```

GUI integration updated in:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
tests/integration/test_gui_coverage.py
```

## New GUI command

```text
Build/audit pivot target redesign candidates
```

## What the script runs

For each candidate:

```text
1. scripts/build_pivot_pattern_sequence_tensor.py
2. scripts/audit_pivot_pattern_sequence_tensor.py
3. scripts/audit_pivot_label_target_stability.py
```

Then Phase153A aggregates the outputs into one candidate comparison report.

## Main outputs

```text
run_logs\pivot_target_redesign_candidates\latest.json
run_logs\pivot_target_redesign_candidates\latest.html
run_logs\pivot_target_redesign_candidates\latest.csv
```

Candidate tensor artifacts:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c1_stable_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c1_stable_latest.parquet

datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_c2_dense_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_c2_dense_latest.parquet
```

## Important design decision

Phase153A does **not** train models.

Reason:

```text
Phase152A showed that current action labels are stable but payoff/R targets flip sign between validation and test.
Therefore the correct next step is to build and audit redesigned targets first, not to blindly train bigger models.
```

## Gate logic

The aggregate report includes:

```text
label_stability_pass_gate
buy_r_sign_flip
sell_r_sign_flip
target_payoff_warning_gate
candidate_ready_for_training_gate
```

A candidate is training-ready only if:

```text
tensor health passes
split-level label PSI stays below threshold
payoff target means do not flip sign from validation to test
```

## Verification

Executed in sandbox:

```text
python -m py_compile scripts/run_pivot_target_redesign_candidate_audit.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_target_redesign_candidate_audit.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_target_redesign_candidate_audit.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 45 passed
```

Full repository quality debt remains known and pre-existing:

```text
ruff/black/mypy full checks are not clean in this repo from older debt.
This phase ran targeted compile/tests only.
```

## Production status

```text
BLOCKED — research target redesign audit only
No Phase134.
No paper shadow.
No live trading.
No production approval.
```

## Recommended owner action

Run from Dashboard:

```text
AI → Build/audit pivot target redesign candidates
```

Then send:

```text
run_logs\pivot_target_redesign_candidates\latest.json
```

Only after that output is reviewed should C1/C2 diagnostic training be considered.
