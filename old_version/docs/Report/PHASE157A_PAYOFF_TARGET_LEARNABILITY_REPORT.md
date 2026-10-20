# PHASE157A — Payoff Target Learnability / Imbalance-Control Diagnostic Report

## Summary

Phase157A has been implemented to diagnose whether B4/B2 payoff targets are learnable from the current sequence tensor features before any additional deep Option B training.

This phase does not train a production model. It uses dependency-free nearest-centroid baselines and imbalance reports.

## Implemented files

```text
scripts/audit_pivot_payoff_target_learnability.py
tests/unit/ai/test_pivot_payoff_target_learnability.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_LEARNABILITY
GUI label: Audit payoff target learnability
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Method

Inputs:

```text
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest_meta.npz

datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest_meta.npz
```

Diagnostics:

```text
- Split class counts and actionable rates.
- Always-HOLD baseline.
- Full SELL/HOLD/BUY centroid baseline.
- Binary actionability-vs-HOLD centroid baseline.
- Candidate-only BUY-vs-SELL centroid baseline.
```

Feature summary:

```text
basic = last timestep + window mean + window std
last  = last timestep only
```

## Outputs

```text
run_logs\pivot_payoff_target_learnability\latest.json
run_logs\pivot_payoff_target_learnability\latest.html
run_logs\pivot_payoff_target_learnability\latest_candidates.csv
run_logs\pivot_payoff_target_learnability\latest_splits.csv
```

## Recommended command

```powershell
python -u scripts\audit_pivot_payoff_target_learnability.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --max-samples 24000 `
  --summary-mode basic `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_target_learnability
```

## Verification

```text
python -m py_compile scripts/audit_pivot_payoff_target_learnability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 51 passed
```

Full ruff/black unavailable in this sandbox image:

```text
No module named ruff
No module named black
```

## Production status

```text
BLOCKED — diagnostic only
No Phase134.
No paper shadow.
No live trading.
```
