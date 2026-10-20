# PHASE154A — Pivot Payoff / Trade-Outcome Target Redesign Audit Report

## Summary

Phase154A has been implemented to search for a more reliable pivot target after Phase153A showed that C1/C2 label-count redesign did not fix payoff/R sign-flip.

This phase audits first-hit / barrier-based trade-outcome targets before any new training.

## Implemented files

```text
scripts/audit_pivot_payoff_target_redesign.py
tests/unit/ai/test_pivot_payoff_target_redesign.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_PAYOFF_TARGET_REDESIGN
GUI label: Audit pivot payoff target redesign
```

Updated files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Target logic

For each sampled row and candidate:

```text
BUY score:
  +tp_atr if future high hits entry + tp_atr*ATR before future low hits entry - sl_atr*ATR
  -sl_atr if stop hits first
  0 on timeout by default

SELL score:
  +tp_atr if future low hits entry - tp_atr*ATR before future high hits entry + sl_atr*ATR
  -sl_atr if stop hits first
  0 on timeout by default
```

A row becomes BUY only when:

```text
near bottom zone
BUY score is positive
BUY score - SELL score >= min_score_edge
```

A row becomes SELL only when:

```text
near top zone
SELL score is positive
SELL score - BUY score >= min_score_edge
```

Otherwise it stays HOLD.

## Default candidates

```text
B1:balanced_24_rr1:24:0.35:0.75:0.75:0.0
B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1
B3:dense_24_half_atr:24:0.50:0.50:0.50:0.0
B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1
B5:short_12_rr1:12:0.35:0.75:0.75:0.0
B6:wide_36_rr1:36:0.35:0.75:0.75:0.0
```

## Outputs

```text
run_logs\pivot_payoff_target_redesign\latest.json
run_logs\pivot_payoff_target_redesign\latest.html
run_logs\pivot_payoff_target_redesign\latest_candidates.csv
run_logs\pivot_payoff_target_redesign\latest_splits.csv
run_logs\pivot_payoff_target_redesign\latest_monthly.csv
```

## Main gate

A candidate is considered ready only when:

```text
label_stability_pass_gate == 1
payoff_stability_pass_gate == 1
candidate_ready_for_tensor_gate == 1
```

The audit explicitly checks whether hypothetical BUY/SELL trade-outcome score means flip sign between train/validation and test.

## Recommended command

```powershell
python -u scripts\audit_pivot_payoff_target_redesign.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --max-samples 24000 `
  --same-bar-policy stop_first `
  --timeout-score-mode zero `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_target_redesign
```

## Verification

```text
python -m py_compile scripts/audit_pivot_payoff_target_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 48 passed
```

Full ruff/black were unavailable in this sandbox image:

```text
python -m ruff ... → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — research target audit only
No Phase134.
No paper shadow.
No live trading.
```
