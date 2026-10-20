# Phase187A — Protected Range Multistep WaveNet Training

## Status

```text
COMPLETED — owner trained and audited
Result: horizon=5 is emitted, but every step is a near-constant ATR offset
candle_forecast_ready_gate=0
Production — BLOCKED
No paper. No live.
Loss scale was corrected after this run. That correction does not authorize a rerun.
```

Owner accuracy result:

```text
docs/Report/PHASE187A_RANGE_MULTISTEP_ACCURACY_RESULT.md
```

This phase trains a new range model that emits high/low for each of the next 5 candles. It does not overwrite the current production range artifacts.

```text
gold_range_4h : untouched
gold_range_1d : untouched
new 4H id     : gold_range_multistep_4h
new 1D id     : gold_range_multistep_1d
```

## Architecture decision

Option B is not used.

```text
Option B : 5M pivot-sequence model
inputs   : m5 context branch + source 5M branch + HTF branch
target   : pivot action / payoff, not future candle high/low
status   : transfer already failed
```

The current range model is already a causal WaveNet. The missing piece is the output width, not a new backbone.

```text
architecture : existing range WaveNet seq2seq
horizon      : 5
output width : 10
layout       : [high_1, low_1, high_2, low_2, high_3, low_3, high_4, low_4, high_5, low_5]
window       : 150
layers/blocks: 4 x 2
features     : same range causal contract as gold_range_4h / gold_range_1d
```

The 6 causal signal-only features are not added. That would change the input contract and make the horizon comparison unclean.

## Command

GUI:

```text
AI → Train range multistep WaveNet
```

```text
CommandKind.TRAIN_RANGE_MULTISTEP
script: scripts/train_range_multistep.py
```

The command refuses any model id that does not contain `multistep`, and it refuses `gold_range_4h` and `gold_range_1d`.

## CLI

```powershell
python -u scripts\train_range_multistep.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --horizon 5 `
  --window 150 `
  --epochs 50 `
  --folds 3 `
  --n-layers 4 `
  --n-blocks 2 `
  --learning-rate 0.00015 `
  --model-id-prefix gold_range_multistep `
  --storage-root datasets
```

Dry-run, no training:

```powershell
python -u scripts\train_range_multistep.py --dry-run
```

## After training

Run the existing accuracy audit against the new ids. Do not point it back at `gold_range_4h` / `gold_range_1d` if the question is about the new model.

```text
AI → Audit range multistep accuracy
4H range model : gold_range_multistep_4h
1D range model : gold_range_multistep_1d
Requested future candles : 5
```

## Sandbox limit

```text
TensorFlow is not installed here.
The 4H gold dataset and gold_range artifacts are not in this sandbox.
No training result is invented.
```

## Verification

```text
python scripts/train_range_multistep.py --dry-run
→ prints gold_range_multistep_4h and gold_range_multistep_1d, writes nothing

python -m pytest tests/unit/ai/test_range_multistep_training.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 81 passed
```

`ruff` / `black` / `mypy` are unavailable in this sandbox.
