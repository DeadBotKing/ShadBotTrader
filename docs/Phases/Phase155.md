# Phase155A — Payoff-Target Tensor + Diagnostic Option B Training

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

Phase154A found two payoff-stable target candidates:

```text
B4 asym_24_tp1_sl05      — preferred
B2 conservative_24_tp1_sl075 — backup
```

Phase155A turns those payoff target definitions into actual sequence tensors and runs a diagnostic Option B training/backtest chain.

## Implemented executables

```text
scripts/build_pivot_payoff_sequence_tensor.py
scripts/run_pivot_payoff_option_b_diagnostic.py
```

## GUI command

```text
Run payoff-target Option B diagnostic
```

## What the end-to-end script does

For each candidate, by default B4 then B2:

```text
1. Build payoff-target sequence tensor
2. Run official sequence tensor health audit
3. Train raw Option B with explicit random seed
4. Run validation ATR PnL backtest
5. Run test ATR PnL backtest
6. Aggregate transfer result
```

## Default candidate order

```text
B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1
B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1
```

## Tensor outputs

For B4:

```text
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b4_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_flat_b4_latest.parquet
```

For B2:

```text
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest.npy
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_tensor_b2_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_payoff_sequence_flat_b2_latest.parquet
```

## Model IDs

```text
gold_pivot_payoff_option_b_b4_5m
gold_pivot_payoff_option_b_b2_5m
```

## Aggregate outputs

```text
run_logs\pivot_payoff_option_b_diagnostic\latest.json
run_logs\pivot_payoff_option_b_diagnostic\latest.html
run_logs\pivot_payoff_option_b_diagnostic\latest.csv
```

Per candidate directories:

```text
run_logs\pivot_payoff_option_b_diagnostic\b4\build\latest.json
run_logs\pivot_payoff_option_b_diagnostic\b4\health\latest.json
run_logs\pivot_payoff_option_b_diagnostic\b4\train\latest.json
run_logs\pivot_payoff_option_b_diagnostic\b4\validation_backtest\latest.json
run_logs\pivot_payoff_option_b_diagnostic\b4\test_backtest\latest.json
```

and similarly for B2.

## Recommended PowerShell command

```powershell
python -u scripts\run_pivot_payoff_option_b_diagnostic.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --source-mode storage `
  --candidates "B4:asym_24_tp1_sl05:24:0.35:1.0:0.50:0.1;B2:conservative_24_tp1_sl075:24:0.25:1.0:0.75:0.1" `
  --build-max-samples 0 `
  --train-max-samples 24000 `
  --epochs 80 `
  --early-stopping-patience 8 `
  --random-seed 20260921 `
  --learning-rate 0.0005 `
  --batch-size 16 `
  --branch-filters 48 `
  --branch-target-features 0 `
  --feature-augmentation-mode off `
  --class-weight off `
  --same-bar-policy stop_first `
  --timeout-score-mode zero `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_option_b_diagnostic
```

## Pass/fail rule

Phase155A does not approve production. It only reports:

```text
validation_pass_gate
test_pass_gate
transfer_pass_gate
```

A candidate remains research-only unless validation-selected behavior transfers to test.

## Verification

```text
python -m py_compile scripts/build_pivot_payoff_sequence_tensor.py scripts/run_pivot_payoff_option_b_diagnostic.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_sequence_tensor.py tests/unit/ai/test_pivot_payoff_option_b_diagnostic.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_sequence_tensor.py tests/unit/ai/test_pivot_payoff_option_b_diagnostic.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 48 passed
```

## Follow-up fix after owner reruns

The B4 tensor build and health audit passed, but Option B training crashed before epoch 1 with:

```text
IndexError: index 2 is out of bounds for axis 0 with size 1
```

Final root cause:

```text
The payoff tensor metadata includes scalar target metadata:
target_mode = ["first_hit_payoff"]

The trainer was indexing every target_* key by sample rows. This is only valid for per-sample target arrays.
```

Fix:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
  scoped_target_meta() now filters target_* keys and indexes only arrays whose first axis equals the tensor sample count.
```

Recovery command should include:

```text
--skip-existing-tensors 1
--class-weight off
```
