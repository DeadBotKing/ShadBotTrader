# Phase149 — Sequence Feature Impact / Pruning Diagnostics

**Status:** ✅ Phase149A implemented  
**Type:** Validation-only feature/group ablation audit  
**Production status:** Research-only; no paper/live permission

---

## Goal

The owner asked which features should be kept and which may damage the model. Phase149A provides a validation-only feature impact audit for trained sequence WaveNet models.

This is not a final pruning decision. It identifies candidates for later anti-overfit filtering and retraining.

---

## Implemented

```text
scripts/audit_pivot_sequence_feature_impact.py
```

GUI command:

```text
Audit pivot sequence feature impact
```

Outputs:

```text
run_logs\pivot_sequence_feature_impact\latest.json
run_logs\pivot_sequence_feature_impact\latest.html
run_logs\pivot_sequence_feature_impact\latest_features.csv
run_logs\pivot_sequence_feature_impact\latest_groups.csv
```

---

## Method

The audit:

```text
1. Loads the trained Option A or Option B sequence WaveNet.
2. Rebuilds the same chronological split used in training.
3. Defaults to validation split to avoid selecting filters from the final test split.
4. Computes baseline metrics.
5. Zero-ablates feature groups and/or individual raw features at inference time.
6. Recomputes metrics.
7. Marks features as KEEP_IMPORTANT, NEUTRAL, or DROP_CANDIDATE.
```

Composite score:

```text
composite = action_accuracy
          + 0.5 * top_ap
          + 0.5 * bottom_ap
          - 0.25 * buy_r_mae
          - 0.25 * sell_r_mae
```

Interpretation:

```text
ablated_composite - baseline_composite > harmful_threshold
→ removing the feature improved validation metrics
→ DROP_CANDIDATE

ablated_composite - baseline_composite < -useful_threshold
→ removing the feature hurt validation metrics
→ KEEP_IMPORTANT

otherwise
→ NEUTRAL
```

---

## Recommended first command

Run on the current best raw-branch Option B first, on validation split:

```powershell
python -u scripts\audit_pivot_sequence_feature_impact.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split validation `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 1500 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --check-groups 1 `
  --check-features 1 `
  --feature-group-filter all `
  --max-features-to-check 0 `
  --harmful-threshold 0.005 `
  --useful-threshold 0.005 `
  --storage-root datasets `
  --output-dir run_logs\pivot_sequence_feature_impact `
  --report-title "Phase149A sequence feature impact audit"
```

Use `--max-windows 0` for a slower full validation scan.

---

## Anti-overfit rule

Do not drop features only because they look bad on the final test split. The required workflow is:

```text
1. Discover candidates on train/validation.
2. Retrain or rerun controlled comparisons.
3. Confirm on test/walk-forward.
```

---

## Verification

```text
python -m py_compile scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 68 passed
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```
