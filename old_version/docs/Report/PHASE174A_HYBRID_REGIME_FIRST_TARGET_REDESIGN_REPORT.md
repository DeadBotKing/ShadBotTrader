# PHASE174A — Hybrid/regime-first Target Redesign Decision Audit Report

## Summary

Phase174A has been implemented after Phase173A failed broker-cost-aware 1H target learnability.

This phase does not train a model. It audits predeclared side/regime/session/cost target subsets for CA1/CA3/CA2 and writes an owner-facing decision matrix before any future training phase can be discussed.

## Implemented files

```text
scripts/audit_hybrid_regime_first_target_redesign.py
tests/unit/ai/test_hybrid_regime_first_target_redesign.py
```

GUI integration:

```text
CommandKind.AUDIT_HYBRID_REGIME_FIRST_TARGET_REDESIGN
GUI label: Audit hybrid/regime-first target redesign
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Why this audit exists

Phase173A result:

```text
learnable_families             : 0
target_learnability_ready_gate : 0
CA1/CA3/CA2 walk-forward pass  : 0/6 each
```

Therefore direct model training on CA1/CA3/CA2 is blocked.

Phase174A tests the Phase171A secondary route:

```text
HYBRID_REGIME_FIRST_REDESIGN
```

## Default target families

```text
CA1_BRK_MID
CA3_BRK_STRICT
CA2_BRK_WIDE
```

## Default regime rules

```text
ALL
BUY_ONLY
SELL_ONLY
TOP_ZONE
BOTTOM_ZONE
SPREAD_ATR_LE_008
SPREAD_ATR_LE_010
ATR_GE_Q50
ATR_GE_Q75
ATR_LE_Q50
WIDTH_GE_Q50
WIDTH_GE_Q75
ACTIVE_UTC_07_17
ASIA_UTC_00_06
RET24_POS
RET24_NEG
MOMENTUM_ALIGNED
MOMENTUM_COUNTER
BUY_MOMENTUM_ALIGNED
SELL_MOMENTUM_ALIGNED
BUY_SPREAD_ATR_LE_010
SELL_SPREAD_ATR_LE_010
```

Quantile thresholds are train-derived per chronological split/fold to avoid leakage.

## Outputs

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
run_logs\hybrid_regime_first_target_redesign\latest.html
run_logs\hybrid_regime_first_target_redesign\latest_regime_candidates.csv
run_logs\hybrid_regime_first_target_redesign\latest_splits.csv
run_logs\hybrid_regime_first_target_redesign\latest_walkforward.csv
run_logs\hybrid_regime_first_target_redesign\latest_decision_matrix.csv
run_logs\hybrid_regime_first_target_redesign\latest_dataset.csv
```

## Recommended command

Dashboard:

```text
Audit hybrid/regime-first target redesign
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_hybrid_regime_first_target_redesign.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48" `
  --regime-rules "ALL;BUY_ONLY;SELL_ONLY;TOP_ZONE;BOTTOM_ZONE;SPREAD_ATR_LE_008;SPREAD_ATR_LE_010;ATR_GE_Q50;ATR_GE_Q75;ATR_LE_Q50;WIDTH_GE_Q50;WIDTH_GE_Q75;ACTIVE_UTC_07_17;ASIA_UTC_00_06;RET24_POS;RET24_NEG;MOMENTUM_ALIGNED;MOMENTUM_COUNTER;BUY_MOMENTUM_ALIGNED;SELL_MOMENTUM_ALIGNED;BUY_SPREAD_ATR_LE_010;SELL_SPREAD_ATR_LE_010" `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --max-folds 0 `
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
  --max-dataset-rows 20000 `
  --storage-root datasets `
  --output-dir run_logs\hybrid_regime_first_target_redesign `
  --report-title "Phase174A hybrid/regime-first target redesign audit"
```

## Verification

```text
python -m py_compile scripts/audit_hybrid_regime_first_target_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_regime_first_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_regime_first_target_redesign.py tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase174A hybrid/regime-first target redesign audit only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase174A on the full 1H XAUUSD dataset. The hybrid/regime-first gates failed:

```text
evaluated_regime_candidates    : 66
ready_regime_candidates        : 0
selected_family_id             : CA2_BRK_WIDE
selected_regime_rule_id        : ASIA_UTC_00_06
selected_regime_ready_gate     : 0
hybrid_regime_first_ready_gate : 0
recommendation                 : STOP_OR_REDESIGN_REQUIRED_NO_MODEL_TRAINING
```

Detailed result report:

```text
docs/Report/PHASE174A_HYBRID_REGIME_FIRST_TARGET_REDESIGN_RESULT.md
```

Decision:

```text
Do not train any CA1/CA3/CA2 regime candidate.
No Phase134.
No paper shadow.
No live trading.
No model training.
```
