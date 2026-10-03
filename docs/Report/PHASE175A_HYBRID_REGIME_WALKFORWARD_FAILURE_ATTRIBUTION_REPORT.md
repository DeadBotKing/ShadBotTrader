# PHASE175A — Hybrid/regime Walk-forward Failure Attribution Audit Report

## Summary

Phase175A has been implemented as the recommended next diagnostic after Phase174A failed all hybrid/regime-first gates.

It consumes the Phase174A JSON output and attributes failure reasons across candidates and walk-forward folds. It does not train a model and does not approve paper/live trading.

## Implemented files

```text
scripts/audit_hybrid_regime_walkforward_failure_attribution.py
tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py
```

GUI integration:

```text
CommandKind.AUDIT_HYBRID_REGIME_WALKFORWARD_FAILURES
GUI label: Audit hybrid/regime walk-forward failures
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Why this phase was chosen

Phase174A result:

```text
ready_regime_candidates        : 0
hybrid_regime_first_ready_gate : 0
all candidate walk-forward pass ratios failed
```

The selected recommendation is:

```text
Do not train.
Do not relax gates.
Attribute the repeated walk-forward failure before any target redesign or model-design phase.
```

## Inputs

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
```

## Outputs

```text
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
run_logs\hybrid_regime_walkforward_failure_attribution\latest.html
run_logs\hybrid_regime_walkforward_failure_attribution\latest_candidate_failures.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_failure_reasons.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_fold_failure_summary.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_decision_matrix.csv
run_logs\hybrid_regime_walkforward_failure_attribution\latest_next_plan.csv
```

## Recommended command

Dashboard:

```text
Audit hybrid/regime walk-forward failures
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_hybrid_regime_walkforward_failure_attribution.py `
  --phase174-path run_logs\hybrid_regime_first_target_redesign\latest.json `
  --min-train-events 80 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-ap-lift 0.03 `
  --min-balanced-accuracy 0.53 `
  --min-train-independent-pf 0.95 `
  --min-validation-independent-pf 1.00 `
  --min-test-independent-pf 1.00 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --output-dir run_logs\hybrid_regime_walkforward_failure_attribution `
  --report-title "Phase175A hybrid/regime walk-forward failure attribution audit"
```

## Verification

```text
python -m py_compile scripts/audit_hybrid_regime_walkforward_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase175A failure attribution audit only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase175A on the Phase174A output. The failure attribution confirms the route is not trainable:

```text
candidate_rows                        : 66
walkforward_rows                      : 396
walkforward_pass_rows                 : 0
walkforward_global_pass_ratio         : 0.0
candidates_with_static_learnability   : 0
candidates_with_walkforward_gate      : 0
candidates_with_ready_gate            : 0
```

Detailed result report:

```text
docs/Report/PHASE175A_HYBRID_REGIME_WALKFORWARD_FAILURE_ATTRIBUTION_RESULT.md
```

Decision:

```text
Do not train.
Do not relax gates.
No Phase134.
No paper shadow.
No live trading.
```
