# Phase174A — Hybrid/regime-first Target Redesign Decision Audit

## Status

```text
COMPLETED — owner run failed hybrid/regime-first gates
research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
No deep model training from this phase.
```


## Owner execution result — 2026-10-01

Phase174A was run on the full 1H XAUUSD dataset with fixed broker spread `0.4`.

Top-level result:

```text
evaluated_regime_candidates    : 66
ready_regime_candidates        : 0
selected_family_id             : CA2_BRK_WIDE
selected_regime_rule_id        : ASIA_UTC_00_06
selected_regime_ready_gate     : 0
hybrid_regime_first_ready_gate : 0
recommendation                 : STOP_OR_REDESIGN_REQUIRED_NO_MODEL_TRAINING
```

Best failed candidate:

```text
CA2_BRK_WIDE + ASIA_UTC_00_06
validation_ap_lift=+0.1977
test_ap_lift=+0.0900
validation/test independent PF=1.7000/1.2174
but train independent PF=0.7416 and walk-forward pass=0/6
```

Important near-misses:

```text
CA1_BRK_MID + WIDTH_GE_Q75: economic_gate=1, but test balanced accuracy=0.5000 and walk-forward pass=0/6.
CA3_BRK_STRICT + ACTIVE_UTC_07_17: economic_gate=1, but validation AP lift=0.0119, test balanced accuracy=0.5263, and walk-forward pass=0/6.
```

Decision:

```text
Do not train any CA1/CA3/CA2 regime candidate.
Do not proceed to Phase175 model training.
No Phase134, no paper shadow, no live trading.
```

Detailed result report:

```text
docs/Report/PHASE174A_HYBRID_REGIME_FIRST_TARGET_REDESIGN_RESULT.md
```

## Why this phase exists

Phase173A failed target learnability for the broker-cost-aware 1H target families:

```text
learnable_families             : 0
target_learnability_ready_gate : 0
CA1/CA3/CA2 walk-forward pass  : 0/6 each
```

That blocks direct model training on CA1/CA3/CA2.

Phase174A is the next diagnostic-only step authorized by the owner. It follows the Phase171A secondary route:

```text
HYBRID_REGIME_FIRST_REDESIGN
```

Instead of redesigning the architecture or training a model, it asks:

```text
Can any predeclared side/regime/session/cost subset of CA1/CA3/CA2 become stable and learnable enough to justify a later model-design audit?
```

## Implemented executable

```text
scripts/audit_hybrid_regime_first_target_redesign.py
```

## GUI command

```text
Audit hybrid/regime-first target redesign
```

Command kind:

```text
AUDIT_HYBRID_REGIME_FIRST_TARGET_REDESIGN
```

## Inputs

Default target families:

```text
CA1_BRK_MID
CA3_BRK_STRICT
CA2_BRK_WIDE
```

Default broker cost:

```text
spread_mode  : fixed
spread_value : 0.4
```

Default predeclared regime rules:

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

Train-derived thresholds are used for quantile rules inside each chronological split/fold to avoid validation/test leakage.

## Metrics

For each `family × regime_rule`, Phase174A reports:

```text
train/validation/test events
positive rates
label PSI vs train
AP lift over base rate
balanced accuracy
F1
independent profit factor from filtered target outcomes
mean ATR score
walk-forward pass ratio
```

It also writes a decision matrix that keeps blocked routes visible:

```text
STOP_PHASE173_DIRECT_TRAINING
HYBRID_REGIME_FIRST_REDESIGN
DEEP_MODEL_TRAINING_NOW
PAPER_OR_LIVE
```

## Gates

Default gate values:

```text
min_train_events                  : 80
min_validation_events             : 20
min_test_events                   : 20
min_positive_rate                 : 0.10
max_positive_rate                 : 0.70
max_label_psi                     : 0.20
min_ap_lift                       : 0.03
min_balanced_accuracy             : 0.53
min_train_independent_pf          : 0.95
min_validation_independent_pf     : 1.00
min_test_independent_pf           : 1.00
min_walkforward_pass_ratio        : 0.50
min_walkforward_folds             : 5
```

A regime candidate is ready only if all of these pass:

```text
class_balance_gate = 1
economic_gate = 1
static_learnability_gate = 1
walkforward_learnability_gate = 1
regime_candidate_ready_gate = 1
```

Top-level pass:

```text
hybrid_regime_first_ready_gate = 1
```

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

## Recommended GUI action

Use:

```text
Audit hybrid/regime-first target redesign
```

Then send:

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
```

## Equivalent PowerShell command

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

## Decision after owner run

If `hybrid_regime_first_ready_gate=1`:

```text
Only then discuss an owner-authorized Phase175A model-design audit.
Still no paper/live/Phase134.
```

If it fails:

```text
No model training.
Stop this 1H broker-cost-aware target route or redesign labels/features again with explicit owner approval.
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_hybrid_regime_first_target_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_hybrid_regime_first_target_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_hybrid_regime_first_target_redesign.py tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black/mypy availability in sandbox:

```text
python -m ruff ...  → unavailable in sandbox in recent runs
python -m black ... → unavailable in sandbox in recent runs
python -m mypy ...  → unavailable in sandbox in recent runs
```
