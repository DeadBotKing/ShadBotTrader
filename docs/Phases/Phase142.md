# Phase142 — 3D Pivot Pattern Tensor + Keras WaveNet

**Status:** ✅ Phase142A/142B implementation added  
**Type:** TensorFlow/Keras sequence model research  
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

The owner clarified that the previous Phase141A flat model was not the intended design. The intended design is a real sequence/pattern-recognition model with a 3D tensor and TensorFlow/Keras WaveNet/TCN.

Important shape clarification:

```text
Stored tensor X shape       : [samples, 288, channels]
Keras runtime batch X shape : [batch, 288, channels]
```

A 4D shape like `[batch, samples, 288, channels]` is not the normal Conv1D/WaveNet input. `samples` is the dataset dimension; `batch` is added by the training loader.

---

## Implemented scripts

```text
scripts/build_pivot_pattern_tensor.py
scripts/train_pivot_pattern_wavenet.py
scripts/backtest_pivot_pattern_wavenet.py
scripts/run_pivot_pattern_wavenet_walk_forward.py
```

GUI commands:

```text
Build pivot pattern tensor
Train pivot WaveNet pattern model
Backtest pivot WaveNet pattern model
Run pivot WaveNet walk-forward
```

Tests:

```text
tests/unit/ai/test_pivot_pattern_tensor.py
tests/unit/ai/test_pivot_wavenet_helpers.py
tests/unit/presentation/test_phase142_pivot_wavenet_gui.py
```

---

## Data input

Default mode reads from project storage:

```text
--source-mode storage
```

Storage layout:

```text
datasets\processed\XAUUSD\5M\v*.parquet
datasets\processed\XAUUSD\1D\v*.parquet
```

For 4H context:

```text
If datasets\processed\XAUUSD\4H\v*.parquet exists, load it directly.
Otherwise read datasets\processed\XAUUSD\1H\v*.parquet and resample to 4H.
```

Project schema is supported:

```text
open_time -> timestamp
```

---

## Tensor builder

Command:

```powershell
python -u scripts/build_pivot_pattern_tensor.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --tensor-window 288 `
  --sample-stride 1 `
  --max-samples 0 `
  --dtype float16 `
  --max-tensor-mb 4096 `
  --output-name pivot_pattern_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_tensor
```

Outputs:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz
datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet
run_logs\pivot_pattern_tensor\latest.json
run_logs\pivot_pattern_tensor\latest.html
```

Tensor channels come from Phase141 causal pivot features:

```text
5M pattern features
4H previous-closed context
1D previous-closed context
session/time features
```

Targets saved in the tensor:

```text
target_action       : SELL/HOLD/BUY = top/no-pivot/bottom
target_top_zone     : binary top-zone label
target_bottom_zone  : binary bottom-zone label
target_buy_r        : clipped future_up_r - future_down_r
target_sell_r       : clipped future_down_r - future_up_r
```

---

## Keras WaveNet trainer

Requires:

```powershell
python -m pip install -r requirements-ai.txt
```

Command:

```powershell
python -u scripts/train_pivot_pattern_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz `
  --model-id gold_pivot_pattern_wavenet_5m `
  --task multihead `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 120 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 6 `
  --n-blocks 2 `
  --dense-units 96 `
  --dropout 0.20 `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.55 `
  --sell-threshold 0.55 `
  --min-margin 0.05 `
  --min-buy-r 0 `
  --min-sell-r 0 `
  --monitor-metric auto `
  --early-stopping-patience 12 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_wavenet
```

Model architecture:

```text
Input [288, channels]
1x1 Conv projection
Residual causal dilated Conv1D blocks
Dilation per block: 1,2,4,8,16,32
GlobalAveragePooling + GlobalMaxPooling
Dense + dropout
Multi-head outputs:
  action softmax: SELL/HOLD/BUY
  top sigmoid
  bottom sigmoid
  buy_r regression
  sell_r regression
```

Outputs:

```text
datasets\models\gold_pivot_pattern_wavenet_5m\v*_model.keras
datasets\models\gold_pivot_pattern_wavenet_5m\v*_training.json
run_logs\pivot_pattern_wavenet\latest.json
run_logs\pivot_pattern_wavenet\latest.html
```

---

## Backtest trained WaveNet

Command:

```powershell
python -u scripts/backtest_pivot_pattern_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet `
  --model-id gold_pivot_pattern_wavenet_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --top-threshold 0.50 `
  --bottom-threshold 0.50 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_wavenet_backtest
```

Outputs:

```text
run_logs\pivot_pattern_wavenet_backtest\latest.json
run_logs\pivot_pattern_wavenet_backtest\latest.html
run_logs\pivot_pattern_wavenet_backtest\latest_trades.csv
```

---

## Walk-forward Keras validation

This is the heavy validation gate. It trains one fresh WaveNet per fold.

Command:

```powershell
python -u scripts/run_pivot_pattern_wavenet_walk_forward.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet `
  --model-id gold_pivot_pattern_wavenet_wf_5m `
  --train-days-min 120 `
  --validation-days 20 `
  --test-days 20 `
  --purge-hours 4 `
  --max-folds 0 `
  --max-train-samples 0 `
  --batch-size 64 `
  --epochs 80 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 6 `
  --n-blocks 2 `
  --dense-units 96 `
  --dropout 0.20 `
  --class-weight auto `
  --early-stopping-patience 10 `
  --buy-thresholds 0.45,0.55,0.65 `
  --sell-thresholds 0.45,0.55,0.65 `
  --margins 0,0.05 `
  --top-thresholds 0.45,0.55,0.65 `
  --bottom-thresholds 0.45,0.55,0.65 `
  --min-r-values=-0.25,0,0.25 `
  --tp-multipliers 0.75,1.0,1.25 `
  --sl-multipliers 0.50,0.75 `
  --hold-bars 24,48 `
  --min-validation-trades 10 `
  --score-metric drawdown_adjusted `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_wavenet_walk_forward
```

Safe note for negative threshold lists in PowerShell:

```text
Use --min-r-values=-0.25,0,0.25 with equals sign.
```

Outputs:

```text
run_logs\pivot_pattern_wavenet_walk_forward\latest.json
run_logs\pivot_pattern_wavenet_walk_forward\latest.html
run_logs\pivot_pattern_wavenet_walk_forward\latest_folds.csv
run_logs\pivot_pattern_wavenet_walk_forward\latest_trades.csv
```

---

## Acceptance

Phase142 implementation acceptance:

```text
3D tensor builder exists
Keras WaveNet trainer exists
WaveNet backtest exists
WaveNet walk-forward exists
All executable actions have GUI commands
Owner Map/docs/tests are updated
```

Trading acceptance is separate and requires real successful walk-forward results. Until then:

```text
No Phase134.
No paper shadow.
No live trading.
```
