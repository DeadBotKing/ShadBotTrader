# Phase129 — WaveNet/TCN on 3D Hybrid Telemetry Tensor

**Status:** ✅ Phase129A implemented
**Type:** Neural temporal model / causal Conv1D / roll-forward training
**Priority:** after Phase128 LightGBM baseline

---

## Why this phase exists

The previous WaveNet path on raw `trend_signal` collapsed:

```text
uniform 1/3 probabilities
or always BUY/SELL behavior
loss near random
no stable trade edge
```

That does not mean WaveNet is permanently useless. It means the old input/target pair was weak.

Phase129 retries WaveNet/TCN on a better problem:

```text
input  = causal 3D telemetry tensor from Phase127
target = Target C:
         target_trade_win
         target_trade_score_r
         target_trade_pnl for analysis
```

The model is no longer asked to discover direction from scratch. It learns temporal trade quality and regime behavior around already-built hybrid/range signals.

---

## Model family

Use causal WaveNet/TCN style blocks:

```text
Dilated causal Conv1D
Residual blocks
Skip connections
Dropout
LayerNorm/BatchNorm if stable
```

Input:

```text
X.shape = [samples, tensor_window, channels]
```

Recommended default:

```text
tensor_window = 288
safe_lag = 48
```

---

## Outputs / heads

Recommended multi-head model:

```text
head_win     : sigmoid, predicts target_trade_win
head_score_r : regression, predicts target_trade_score_r
```

Optional analysis only:

```text
head_pnl or no direct PnL head initially
```

The practical decision should use:

```text
meta_win_prob
expected_score_r
```

not raw `target_trade_pnl`.

---

## Loss

Suggested combined loss:

```text
loss = BCE(target_trade_win, pred_win)
     + alpha * Huber(target_trade_score_r, pred_score_r)
```

Start with:

```text
alpha = 0.5
```

If regression destabilizes training, train two separate models first:

```text
classifier WaveNet
score-regression WaveNet
```

---

## Roll-forward protocol

No random split.

Minimum:

```text
expanding roll-forward folds
purge_gap >= tensor_window + safe_lag
```

Monitor metrics:

```text
val_trade_win_ap
val_trade_win_precision_at_threshold
val_score_r_mae
val_expected_trade_pnl_after_filter
val_action_collapse / predicted trade rate sanity
```

Do not monitor only `val_loss`.

---

## Anti-collapse checks

The old WaveNet failed by collapse. This phase must fail fast if:

```text
pred_win_stdev ~= 0
predicted_trade_rate == 0
predicted_trade_rate too high
single-regime output constant
validation PnL worse than LightGBM baseline
```

Acceptance thresholds should be compared to Phase128, not to zero.

---

## Backtest integration

WaveNet/TCN is not the first decision model. It is a filter/scorer:

```text
base hybrid candidate
+ WaveNet meta_win_prob
+ WaveNet expected_score_r
→ execute / skip
```

Then run:

```text
Phase126A chronological replay
Phase133 walk-forward validation
```

---

## Model IDs

Recommended:

```text
gold_hybrid_meta_wavenet_5m
gold_hybrid_score_wavenet_5m
```

If implemented as one multi-head artifact:

```text
gold_hybrid_telemetry_wavenet_5m
```

---

## Acceptance criteria

```text
- Uses Phase127 3D tensor only.
- Enforces chronological/roll-forward split.
- Includes purge gap to prevent target/feature overlap leakage.
- Reports anti-collapse metrics.
- Produces chronological replay after filtering base hybrid trades.
- Must beat Phase128 LightGBM baseline before being considered useful.
```

---

## Important note

This is not a revival of the old `gold_trend_signal_5m` as-is. It is a new WaveNet/TCN experiment with a better target and richer causal telemetry inputs.

---

## Next phase

```text
Phase130 — TSMixer benchmark on the same 3D tensor.
```

---

## GUI/operator execution requirement

WaveNet/TCN جدید نباید فقط با terminal قابل اجرا باشد. این فاز باید Dashboard command داشته باشد تا اپراتور بتواند train و audit را از GUI اجرا کند.

حداقل commandهای لازم:

```text
CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET
Dashboard label: Train telemetry WaveNet/TCN
Handler: runs scripts/train_hybrid_telemetry_wavenet.py

CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET
Dashboard label: Backtest telemetry WaveNet/TCN
Handler: runs scripts/backtest_hybrid_telemetry_wavenet.py
```

فیلدهای مهم GUI:

```text
tensor_path
model_id
tensor_window
n_layers
n_blocks/dilations
batch_size
epochs
learning_rate
monitor_metric
purge_gap
meta_threshold/score_threshold
storage_root
```

تست الزامی: descriptor وجود داشته باشد و handler همهٔ flagهای مهم را پاس کند.

---

## Phase129A implementation status

Implemented files:

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
```

GUI commands:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

Tests:

```text
tests/unit/ai/test_hybrid_telemetry_wavenet.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Training capabilities:

```text
- input: Phase127 NPZ tensor
- task=classifier | regressor | multihead
- causal dilated Conv1D WaveNet/TCN blocks
- train-only channel normalization
- chronological train/validation/test split
- purge_gap default = 336 bars
- anti-collapse metrics: prediction stdev, selected/positive rates
- optional class weights
- TensorFlow/Keras artifact saved as pickle_keras with scaler metadata
```

Backtest capabilities:

```text
- loads saved WaveNet/TCN artifact
- applies saved scaler
- decision_mode=meta|score|both
- meta_threshold / score_threshold gates
- chronological single-position replay using source_index/target_exit_index
- outputs HTML/JSON/CSV
```

Outputs:

```text
run_logs/hybrid_telemetry_wavenet/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.html
run_logs/hybrid_telemetry_wavenet_backtest/latest.csv
```

Precondition:

```text
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
TensorFlow installed via requirements-ai.txt
```

First recommended train command:

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
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

First recommended backtest command:

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
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

---

## Current owner clarification — 2026-09-12

The Phase127A full tensor is now available:

```text
tensor_path : datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
shape       : [52683, 150, 94]
dtype       : float16
```

This is the intended input for Phase129A WaveNet/TCN. It is a new telemetry model, not the old collapsed `gold_trend_signal_5m` WaveNet.

Current recommended target/task:

```text
--task multihead
```

Heads:

```text
meta_win -> target_trade_win
score_r  -> target_trade_score_r
```

Reason:

```text
The classifier-only Phase133A path failed out-of-time. The score_r regressor path was much better and reached near break-even, so target_trade_score_r should be treated as the primary trading-quality target. Multihead keeps target_trade_win as an auxiliary stabilizer while training the score_r head.
```

---

## Important clarification — train command is not monthly walk-forward — 2026-09-12

The current command:

```text
scripts/train_hybrid_telemetry_wavenet.py
```

uses a chronological single train/validation/test split with purge gap:

```text
selected candidate tensor samples -> train_frac / val_frac / test
purge_gap inserted between train and validation, and between validation and test
no random split
```

It is correct for producing the first Phase129A WaveNet/TCN artifact, but it is not a full expanding monthly walk-forward validation.

For the current full tensor run, because `candidate_only=1`, the observed training input shape is expected:

```text
full tensor shape       : [52683, 150, 94]
selected candidate input: [13692, 150, 94]
```

The difference is expected because the model is a meta-filter trained only on candidate windows, not all no-trade windows.

Final acceptance still requires a tensor-model walk-forward validation step if the first WaveNet artifact/backtest is promising.

---

## Operator training and initial backtest result — 2026-09-12

The operator trained Phase129A WaveNet/TCN on the full every-window tensor:

```text
model_id       : gold_hybrid_telemetry_wavenet_5m
version        : 1
task           : multihead
selected rows  : 13692 candidate tensor windows
input shape    : [13692, 150, 94]
train/val/test : 9584 / 1718 / 1718
purge_gap      : 336
```

Important anti-collapse metrics:

```text
val_meta_prob_stdev   : 0.2892801567904343
test_meta_prob_stdev  : 0.2399177476745701
val_score_pred_stdev  : 0.47359669000282073
test_score_pred_stdev : 0.37248512880185
val_meta_collapse     : 0.0
test_meta_collapse    : 0.0
val_score_collapse    : 0.0
test_score_collapse   : 0.0
```

Score-head quality signal:

```text
test_score_target_mean          : -0.05203402787446976
test_score_selected_rate        : 0.27648428405122233
test_score_selected_target_mean : +0.1913444548845291
```

Initial full replay with `decision_mode=score` and `score_threshold=0`:

```text
rows          : 52683 / 52683
trades        : 384
coverage      : 0.73%
skipped_nn    : 9520
total_pnl     : +1914.66
profit_factor : 2.604
final_balance : 291.47 with initial=100 and units=0.1
```

Decision:

```text
PROMISING, but not accepted for production/paper.
```

Reason:

```text
The result includes in-sample training-era windows because eval_frac=1.0. It proves the 3D tensor + WaveNet path has potential and is not collapsed, but it does not replace walk-forward validation.
```

---

## Operator full and last-15% replay details — 2026-09-12

Full score-mode replay:

```text
eval_frac      : 1.0
rows/evaluated : 52683 / 52683
trades         : 384
wins/losses    : 242 / 142
win_rate       : 63.0208%
total_pnl      : +1914.6646151691675
profit_factor  : 2.603926956615171
max_drawdown   : 192.19346404075623
coverage       : 0.7289%
final_balance  : 291.46646151691675 at initial=100, units=0.1
```

Full replay monthly:

```text
2025-12 +205.61, 2026-01 +257.99, 2026-02 +463.73, 2026-03 +668.79,
2026-04 +328.46, 2026-05 -4.30, 2026-06 -49.71, 2026-07 +78.63, 2026-08 -34.54
```

Last-15% score-mode replay:

```text
eval_frac      : 0.15
rows/evaluated : 52683 / 7902
trades         : 29
wins/losses    : 16 / 13
win_rate       : 55.1724%
total_pnl      : +29.590763092041016
profit_factor  : 1.316544651614474
max_drawdown   : 52.06632328033447
coverage       : 0.3670%
final_balance  : 102.95907630920411 at initial=100, units=0.1
```

Last-15% monthly:

```text
2026-07: +64.1343 PF=2.5486 trades=20
2026-08: -34.5435 PF=0.3365 trades=9
```

Decision:

```text
PROMISING BUT FRAGILE. Continue research with threshold robustness and possibly a longer/score-focused v2 training run. Do not deploy.
```

---

## Operator v2 long train result — 2026-09-13

The score-focused long train produced version 2:

```text
model_id          : gold_hybrid_telemetry_wavenet_5m
version           : 2
task              : multihead
filters           : 64
n_layers          : 6
n_blocks          : 2
dense_units       : 96
dropout           : 0.25
learning_rate     : 0.0005
score_loss_weight : 1.0
monitor_metric    : val_score_r_mae
```

Although validation metrics improved, the test split became worse than v1:

```text
v2 val_score_mae                    : 0.7433294282298605
v2 test_score_mae                   : 0.9537305706318867
v2 test_score_selected_rate         : 0.459837019790454
v2 test_score_selected_target_mean  : -0.13298217952251434
v2 test_meta_ap                     : 0.4581884952337111
v2 test_score_collapse              : 0.0
```

Comparison to v1:

```text
v1 test_score_selected_target_mean  : +0.1913444548845291
v2 test_score_selected_target_mean  : -0.13298217952251434
```

Decision:

```text
Do not prefer v2 over v1. The longer/larger score-focused training likely overfit validation or mismatched the test regime. v1 remains the better candidate pending threshold grid and tensor walk-forward validation.
```

Command hygiene note:

```text
Because v2 is now the latest model, --model-version 0 resolves to v2.
Use --model-version 1 when intentionally backtesting the stronger v1 baseline.
Use --model-version 2 when explicitly auditing v2.
```

---

## Operator v2 last-15% backtest — 2026-09-13

After v2 long-train metrics suggested poor test generalization, the operator ran an explicit last-15% backtest:

```text
model_version  : 2
decision_mode  : score
score_threshold: 0.0
eval_frac      : 0.15
rows/evaluated : 52683 / 7902
```

Result:

```text
trades        : 89
buy/sell      : 58 / 31
wins/losses   : 29 / 60
win_rate      : 32.5843%
total_pnl     : -178.49363827705383
avg_pnl       : -2.005546497494987
profit_factor : 0.5542918793438448
max_drawdown  : 212.62753653526306
coverage      : 1.1263%
final_balance : 82.15063617229461 at initial=100, units=0.1
```

Monthly:

```text
2026-07:   -3.3839 PF=0.9646 trades=31
2026-08: -168.3904 PF=0.4355 trades=56
2026-09:   -6.7193 PF=0.0000 trades=2
```

Decision:

```text
REJECT v2. It is materially worse than v1 and should not be used as the preferred WaveNet candidate.
```

Important operational note:

```text
Because v2 is the latest saved version, --model-version 0 now resolves to v2.
Use --model-version 1 for the stronger v1 baseline.
```
