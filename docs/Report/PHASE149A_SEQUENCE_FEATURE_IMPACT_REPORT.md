# Phase149A Report — Sequence Feature Impact Audit

Date: 2026-09-19

## Goal

Build a diagnostic that helps answer:

```text
Which features should be kept?
Which features may hurt validation performance and should become drop candidates?
```

## Implemented

```text
scripts/audit_pivot_sequence_feature_impact.py
```

GUI:

```text
Audit pivot sequence feature impact
```

## What the audit does

```text
- Loads a trained sequence WaveNet model.
- Supports Option A and Option B records.
- Rebuilds chronological validation/test/tail split.
- Predicts baseline metrics.
- Zero-ablates feature groups and individual features.
- Computes metric deltas.
- Writes ranked CSVs for feature pruning research.
```

## Outputs

```text
run_logs\pivot_sequence_feature_impact\latest.json
run_logs\pivot_sequence_feature_impact\latest.html
run_logs\pivot_sequence_feature_impact\latest_features.csv
run_logs\pivot_sequence_feature_impact\latest_groups.csv
```

## First command

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

## Verification

```text
python -m py_compile scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 68 passed
```

## Production status

```text
BLOCKED — diagnostic only.
No Phase134.
No paper shadow.
No live trading.
```
