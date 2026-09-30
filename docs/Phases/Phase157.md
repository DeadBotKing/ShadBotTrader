# Phase157A — Payoff Target Learnability / Imbalance-Control Diagnostic

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase156A showed that payoff Option B models are strongly HOLD-dominant:

```text
B4 validation hold_mean : 0.9814
B4 test hold_mean       : 0.9728
B4 validation trades    : 1
B4 test trades          : 5
```

Before another expensive deep training run, Phase157A asks whether B4/B2 targets are learnable at all from the current tensor features.

## Implemented executable

```text
scripts/audit_pivot_payoff_target_learnability.py
```

## GUI command

```text
Audit payoff target learnability
```

## Diagnostics

For each candidate, default B4 and B2, Phase157A computes:

```text
1. Split-level class imbalance.
2. Always-HOLD / majority baselines.
3. Full three-class SELL/HOLD/BUY nearest-centroid baseline.
4. Binary ACTIONABLE-vs-HOLD nearest-centroid baseline.
5. Candidate-only BUY-vs-SELL nearest-centroid baseline on target_action != HOLD rows.
```

Feature summary is created from the existing payoff sequence tensor:

```text
summary_mode=basic → last timestep + window mean + window std
summary_mode=last  → last timestep only
```

## Outputs

```text
run_logs\pivot_payoff_target_learnability\latest.json
run_logs\pivot_payoff_target_learnability\latest.html
run_logs\pivot_payoff_target_learnability\latest_candidates.csv
run_logs\pivot_payoff_target_learnability\latest_splits.csv
```

## Recommended PowerShell command

```powershell
python -u scripts\audit_pivot_payoff_target_learnability.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --summary-mode basic `
  --chunk-size 512 `
  --min-action-ap-lift 0.05 `
  --min-binary-balanced-accuracy 0.55 `
  --min-side-balanced-accuracy 0.55 `
  --min-candidate-train-rows 200 `
  --min-candidate-validation-rows 30 `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_target_learnability
```

## Gate interpretation

```text
actionability_learnability_gate
  passes if ACTIONABLE-vs-HOLD validation AP improves enough over base rate
  and binary balanced accuracy is above threshold.

side_learnability_gate
  passes if candidate-only BUY-vs-SELL validation balanced accuracy is above threshold
  and there are enough candidate samples.

candidate_learnability_gate
  passes only if both gates pass.
```

If this phase fails:

```text
Do not train another bigger WaveNet on B4/B2.
Revisit target/feature design or use a different objective/sampling design.
```

If it passes:

```text
The target has learnable signal in simple baselines.
Then neural training should be redesigned around imbalance control/sampling/loss rather than scaling architecture blindly.
```

## Execution result

The owner ran Phase157A on B4/B2.

Top-level result:

```text
completed_candidates : 2
learnable_candidates : 0
best_candidate_id    : B2
best_candidate_reason: no gate pass; best diagnostic score only
```

B4:

```text
train/validation/test actionable : 3.8333% / 4.8407% / 4.3505%
always-HOLD validation/test acc  : 95.1593% / 95.6495%
full3 balanced acc               : 0.3333 / 0.3333
binary validation AP lift        : +0.1238
binary test AP lift              : +0.0126
binary balanced acc              : 0.5 / 0.5
binary F1                        : 0.0 / 0.0
side BUY AP validation/test      : 0.8667 / 0.8926
side balanced acc                : 0.5 / 0.5
candidate_learnability_gate      : 0
```

B2:

```text
train/validation/test actionable : 3.1607% / 4.1973% / 3.5846%
full3 balanced acc               : 0.3333 / 0.3333
binary validation AP lift        : +0.1500
binary test AP lift              : +0.0119
side BUY AP validation/test      : 0.9236 / 0.9172
candidate_learnability_gate      : 0
```

Decision:

```text
Phase157A failed learnability gates.
Do not train bigger Option B/WaveNet models on the current full-universe payoff target.
```

Important nuance:

```text
Candidate-only side AP is high, so side ranking may be learnable after a valid live-known candidate generator exists.
The bottleneck is actionability detection from the full universe.
```

Recommended next phase:

```text
Phase158A — Pivot Zone Candidate / Actionability Reframe Audit
```

## Verification

```text
python -m py_compile scripts/audit_pivot_payoff_target_learnability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```
