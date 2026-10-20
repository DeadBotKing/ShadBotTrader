# Phase129A Report — Telemetry WaveNet/TCN

Date: 2026-09-09

## Goal

Retry WaveNet/TCN on the new Phase127 causal 3D telemetry tensor instead of the old collapsed raw `trend_signal` problem.

This is not `gold_trend_signal_5m` revived as-is. It is a new meta/score model over:

```text
X = [samples, tensor_window, channels]
```

with Target C:

```text
target_trade_win
target_trade_score_r
target_trade_pnl for analysis/backtest
```

## Implemented files

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
tests/unit/ai/test_hybrid_telemetry_wavenet.py
```

GUI:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

## Training implementation

```text
causal Conv1D / TCN blocks
residual connections
gated tanh/sigmoid activations
skip aggregation
global average pooling
classifier, regressor or multihead outputs
train-only normalization
chronological split with purge_gap
```

Default purge gap:

```text
336 bars = tensor_window 288 + safe_lag 48
```

## Artifact payload

The saved artifact format is `pickle_keras`:

```text
model_bytes
channel_names
scaler_mean
scaler_std
args
task
meta_threshold
score_threshold
```

This lets the backtest and later production path normalize online tensors with the same train-only scaler.

## First train command

```powershell
python -u scripts/train_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_wavenet_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

## First backtest command

```powershell
python -u scripts/backtest_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_wavenet_5m `
  --model-version 0 `
  --decision-mode meta `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Outputs

```text
run_logs/hybrid_telemetry_wavenet/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.html
run_logs/hybrid_telemetry_wavenet_backtest/latest.csv
```

## Quality checks

Targeted tests cover split purging, train-only normalization, candidate filtering, gate modes and chronological skip-while-open behavior.

## Acceptance

A trained WaveNet/TCN is useful only if it beats Phase128 LightGBM and base hybrid chronological replay on out-of-time trading metrics. If not, it remains research-only.

## Operator result — WaveNet/TCN v1 — 2026-09-12

Training configuration:

```text
model_id       : gold_hybrid_telemetry_wavenet_5m
version        : 1
task           : multihead
candidate_only : 1
selected rows  : 13692
input shape    : [13692, 150, 94]
train/val/test : 9584 / 1718 / 1718
purge_gap      : 336
```

Training result summary:

```text
val_meta_ap                      : 0.5189458439202039
test_meta_ap                     : 0.5377916962550442
val_meta_collapse                : 0.0
test_meta_collapse               : 0.0
val_score_mae                    : 0.8421052456884921
test_score_mae                   : 0.8726781023827808
val_score_collapse               : 0.0
test_score_collapse              : 0.0
test_score_selected_rate         : 0.27648428405122233
test_score_selected_target_mean  : +0.1913444548845291
```

Initial score-mode replay:

```text
decision_mode : score
score_threshold : 0
rows          : 52683 / 52683
trades        : 384
coverage      : 0.73%
skipped_nn    : 9520
total_pnl     : +1914.66
profit_factor : 2.604
final_balance : 291.47 with initial=100 and units=0.1
```

Interpretation:

```text
This is the strongest preliminary result so far from the 3D tensor path. It is still preliminary because the replay was full-history/in-sample (`eval_frac=1.0`). The model must pass out-of-time and tensor walk-forward validation before paper/live is considered.
```

## Operator replay details — full and last-15% — 2026-09-12

Full score-mode replay (`eval_frac=1.0`):

```text
samples       : 52683
trades        : 384
buy/sell      : 215 / 169
wins/losses   : 242 / 142
win_rate      : 63.0208%
total_pnl     : +1914.6646151691675
avg_pnl       : +4.986105768669707
profit_factor : 2.603926956615171
max_drawdown  : 192.19346404075623
coverage      : 0.7289%
```

Last-15% score-mode replay (`eval_frac=0.15`):

```text
evaluated_rows: 7902
trades        : 29
buy/sell      : 6 / 23
wins/losses   : 16 / 13
win_rate      : 55.1724%
total_pnl     : +29.590763092041016
avg_pnl       : +1.0203711411048626
profit_factor : 1.316544651614474
max_drawdown  : 52.06632328033447
coverage      : 0.3670%
```

Interpretation:

```text
The last-15% proxy is positive, which is encouraging. It is not enough for acceptance because it has only 29 trades and August remains negative. The full replay is heavily stronger in earlier months, so in-sample contribution is material.
```

## Operator result — WaveNet/TCN v2 long train — 2026-09-13

Version 2 was trained with higher capacity and score-focused monitoring:

```text
filters              : 64
n_layers             : 6
n_blocks             : 2
dense_units          : 96
dropout              : 0.25
learning_rate        : 0.0005
score_loss_weight    : 1.0
monitor_metric       : val_score_r_mae
early_stopping       : 25
```

Important metrics:

```text
val_meta_ap                     : 0.6418573203049249
test_meta_ap                    : 0.4581884952337111
val_score_mae                   : 0.7433294282298605
test_score_mae                  : 0.9537305706318867
val_score_selected_target_mean  : +0.12646526098251343
test_score_selected_target_mean : -0.13298217952251434
test_score_selected_rate        : 0.459837019790454
test_score_collapse             : 0.0
```

Interpretation:

```text
v2 is not collapsed, but it generalizes worse than v1. Validation looked better while test selected-target quality turned negative. v2 should not replace v1 unless backtest/threshold-grid results prove otherwise.
```

## Operator backtest — WaveNet/TCN v2 last-15% — 2026-09-13

Configuration:

```text
model_version  : 2
decision_mode  : score
score_threshold: 0.0
eval_frac      : 0.15
```

Result:

```text
evaluated_rows: 7902
trades        : 89
buy/sell      : 58 / 31
wins/losses   : 29 / 60
win_rate      : 32.5843%
total_pnl     : -178.49363827705383
avg_pnl       : -2.005546497494987
profit_factor : 0.5542918793438448
max_drawdown  : 212.62753653526306
coverage      : 1.1263%
final_balance : 82.15063617229461
```

Monthly:

```text
2026-07:   -3.3839 PF=0.9646 trades=31
2026-08: -168.3904 PF=0.4355 trades=56
2026-09:   -6.7193 PF=0.0000 trades=2
```

Conclusion:

```text
v2 is rejected. The backtest confirms the training-metric warning: it selected too many bad trades out-of-time. v1 remains the better WaveNet candidate.
```

## Phase132A threshold grid — WaveNet v1 on last-15% — 2026-09-13

Base on the same last-15% universe:

```text
trades        : 195
total_pnl     : -247.1424761712551
profit_factor : 0.70282875694799
max_drawdown  : 272.11317190527916
```

Best WaveNet v1 row:

```text
decision_mode   : score
score_threshold : 0.05
trades          : 22
wins/losses     : 14 / 8
win_rate        : 63.6364%
total_pnl       : +42.78727626800537
profit_factor   : 1.6478747062665267
max_drawdown    : 32.968711853027344
```

Interpretation:

```text
v1 has a useful threshold region on the last-15% proxy. score_threshold=0.05 improves total PnL and drawdown relative to threshold=0.00. This strengthens the case for tensor walk-forward validation, but is still not production proof.
```
