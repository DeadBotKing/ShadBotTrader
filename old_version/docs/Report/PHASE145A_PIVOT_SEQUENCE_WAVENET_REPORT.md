# Phase145A Report — Pivot Sequence Tensor + Advanced Conv1D WaveNet

Date: 2026-09-17

## Goal

Implement Option A proposed by the owner:

```text
X = [samples, WindowSize, Features]
Keras batch = [batch, WindowSize, Features]
```

The model keeps the same pivot targets as the 4D model but concatenates 5M, closed 4H, closed 1D and source 5M feature columns on one channel axis.

## Implemented files

```text
scripts/build_pivot_pattern_sequence_tensor.py
scripts/train_pivot_pattern_sequence_wavenet.py
```

GUI:

```text
Build pivot sequence tensor
Train pivot sequence WaveNet
```

Tests:

```text
tests/unit/ai/test_pivot_sequence_tensor.py
tests/unit/ai/test_pivot_sequence_wavenet_helpers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Why this is different from Phase143/144

Phase143/144 tensor:

```text
[samples, WindowSize, Features_5M, Features_4H_1D]
```

Phase145 tensor:

```text
[samples, WindowSize, Features]
```

Expected benefit:

```text
Can preserve all available features while reducing dimensionality and memory pressure.
Conv1D/WaveNet naturally operates on [time, channels].
```

## Feature handling

The builder includes:

```text
generated 5M pivot features
closed 4H context features
closed 1D context features
session/time features
optional source 5M numeric feature columns from project parquet
```

Source 5M extras are prefixed:

```text
src5m_<column_name>
```

This is intended to preserve the larger historical feature set when present in the operator's stored 5M parquet.

## Targets

Same as Phase143/144:

```text
target_action
target_top_zone
target_bottom_zone
target_buy_r
target_sell_r
```

## Architecture

The trainer mirrors the advanced 4D WaveNet concept, adapted to 1D feature sequences:

```text
Input [WindowSize, Features]
├── 5M branch: generated_5m + source_5m + session features
├── HTF branch: closed_4h + closed_1d features
├── all-feature branch
├── multi-scale causal Conv1D kernels 3,5,9
├── gated tanh-sigmoid dilated WaveNet blocks
├── residual + skip connections
├── SE/channel attention
├── temporal self-attention
├── avg/max/last pooling
└── action/top/bottom/buy_r/sell_r heads
```

## RAM behavior

Default:

```text
--loader-mode stream
```

The tensor remains on disk as a memory-mapped `.npy`; batches are read and normalized on demand.

## Smoke verification

TESTSYM builder smoke:

```text
X shape     : [160, 20, 57]
Keras batch : [batch, 20, 57]
features    : 57 generated=57 source5m=0
```

## Verification

```text
python -m ruff check scripts/build_pivot_pattern_sequence_tensor.py scripts/train_pivot_pattern_sequence_wavenet.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m black --check scripts/build_pivot_pattern_sequence_tensor.py scripts/train_pivot_pattern_sequence_wavenet.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

Targeted Phase145 pytest + GUI coverage
→ passed
```

Full training was not run in the sandbox. It must run on the operator machine with the real XAUUSD sequence tensor and TensorFlow runtime.

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

## Full gate status

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1919 tests collected
```

Known full-repository debt remains unchanged:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## Phase145A operator result — Option A sequence WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet\latest.json` for the first operator-machine run of Phase145A Option A.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 57]
keras_batch_shape : [batch, 100, 57]
feature_count     : 57
m5_feature_count  : 35
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.4604779412
val_top_ap          : 0.2414809241
val_bottom_ap       : 0.1344216114
val_buy_r_mae       : 0.6942731142
val_sell_r_mae      : 0.6847920418
val_selected_rate   : 0.5836397059
```

Test metrics:

```text
test_action_accuracy : 0.4791666667
test_top_ap          : 0.2453369099
test_bottom_ap       : 0.1816515898
test_buy_r_mae       : 0.6652074456
test_sell_r_mae      : 0.6756162643
test_selected_rate   : 0.5719975490
```

Comparison against Phase144A 4D Image WaveNet v1 supplied earlier:

```text
Action accuracy:
  4D Image WaveNet      : val=0.5628, test=0.5970
  Option A Sequence     : val=0.4605, test=0.4792
  Current read          : 4D is stronger on action classification.

Top AP:
  4D Image WaveNet      : val=0.2038, test=0.2328
  Option A Sequence     : val=0.2415, test=0.2453
  Current read          : Option A is slightly stronger on top-zone ranking.

Bottom AP:
  4D Image WaveNet      : val=0.1501, test=0.2357
  Option A Sequence     : val=0.1344, test=0.1817
  Current read          : 4D is stronger on bottom-zone ranking.

Selected rate:
  4D Image WaveNet      : val=0.4187, test=0.4010
  Option A Sequence     : val=0.5836, test=0.5720
  Current read          : Option A is much more aggressive and may over-select.
```

Interpretation:

```text
GOOD:
- Numerically healthy: nonfinite_input_values=0.
- Option A built the intended WaveNet-native tensor: [samples, WindowSize, Features].
- Memory pressure is lower than the 4D interaction tensor.
- Top-zone ranking is slightly better than 4D in this run.

LIMITS:
- Action accuracy is materially lower than the Phase144A 4D Image WaveNet result.
- Bottom-zone AP is lower than 4D.
- selected_rate around 57% is high under the loose diagnostic gate.
- buy_r/sell_r MAE did not improve; R-heads are not yet reliable trading gates.
- The report has no PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation.
- This is not an apples-to-apples comparison because Phase144A used 12000 samples while Phase145A used 24000 samples and a different feature layout/capacity.
- Feature count is 57. If the owner expected the large historical 5M feature set, the Phase145A tensor build report must be checked for `source_5m_feature_count`.
```

Decision:

```text
Phase145A Option A v1 is technically healthy but not better overall than Phase144A 4D v1 on classifier metrics.
It remains useful as a lower-dimensional research lane, especially for top-zone ranking and RAM efficiency.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Phase145A source-feature discovery fix — 2026-09-19

The owner supplied the Phase145A sequence tensor build report. It confirmed:

```text
features                  : 57
generated_feature_count   : 57
source_5m_feature_count   : 0
source_5m_feature_path    : not previously reported
```

Interpretation:

```text
The first Option A tensor was technically valid, but it did not include the larger historical 5M feature set.
It was therefore an Option A generated-feature run, not the intended full-source-feature Option A run.
```

Root cause fixed in the builder:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

New behavior:

```text
--include-source-5m-features 1
```

now auto-probes, in storage mode, before falling back to the plain OHLCV `v*.parquet` file:

```text
datasets\processed\<SYMBOL>\<TF>\hybrid_telemetry_flat_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_latest.parquet
datasets\processed\<SYMBOL>\<TF>\hybrid_xgboost_matrix_all_5m.parquet
hybrid_*flat*.parquet
hybrid_*matrix*.parquet
plain storage OHLCV v*.parquet
```

Added explicit override:

```text
--source-5m-feature-path PATH
```

GUI update:

```text
Build pivot sequence tensor → Optional source 5M feature parquet/csv
```

Leakage/metadata safeguards:

```text
Blocked source columns include OHLCV identifiers, source_index/tensor_index/sample_index/row_id, target_*, future_*, candidate_*, prediction_*, pred_*, prob_*.
```

The build report now records:

```text
source_5m_feature_path
source_5m_total_columns
source_5m_numeric_candidate_count
source_5m_feature_count
```

Required rerun:

```powershell
python -u scripts\build_pivot_pattern_sequence_tensor.py `
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
  --window-size 100 `
  --sample-stride 1 `
  --max-samples 0 `
  --include-source-5m-features 1 `
  --max-features 0 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --chunk-size 512 `
  --max-tensor-mb 8192 `
  --output-name pivot_pattern_sequence_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor
```

If `source_5m_feature_count` remains `0`, then the large 5M feature file is not in the auto-probed project-storage locations and the operator must provide its exact path through the new GUI field or `--source-5m-feature-path`.

Decision:

```text
The previous Phase145A v1 model result should be treated as underfed / generated-feature-only.
Do not compare it as the final full-feature Option A result until the tensor is rebuilt with source_5m_feature_count > 0.
Production remains BLOCKED.
```

Verification in sandbox:

```text
python -m py_compile scripts/build_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 41 passed

python -m pytest -q
→ blocked in sandbox collection because optional dependencies pyarrow/pywt are not installed here.

python -m ruff / python -m black
→ unavailable in this sandbox image.
```

## Phase145A PowerShell empty optional path fix — 2026-09-19

The owner ran the new Phase145A tensor build command in PowerShell with:

```text
--source-5m-feature-path "" `
```

PowerShell/native argv handling dropped the empty string, so `argparse` saw `--source-5m-feature-path` without a value and failed:

```text
build_pivot_pattern_sequence_tensor.py: error: argument --source-5m-feature-path: expected one argument
```

Fix implemented:

```text
scripts/build_pivot_pattern_sequence_tensor.py
```

The argument now uses:

```text
nargs="?"
const=""
default=""
```

So both forms are safe:

```powershell
# recommended: omit the optional path for auto-probe
--include-source-5m-features 1

# also accepted now if a shell drops the empty value
--source-5m-feature-path
```

Documentation command snippets were updated to omit `--source-5m-feature-path ""` unless an explicit path is actually needed.

Recommended rerun is the same tensor build command, but without the empty path line. If auto-probe still reports `source_5m_feature_count=0`, rerun with an actual feature parquet/csv path.

## Phase145A full-source sequence tensor build + health audit command — 2026-09-19

The owner rebuilt the Option A sequence tensor after the source-feature discovery fix. The new build report confirms the intended 3D tensor layout:

```text
stored_x_shape      : [53098, 100, 140]
keras_batch_shape   : [batch, 100, 140]
dtype               : float16
estimated_size_mb   : 1417.8696
samples             : 53098
window_size         : 100
features            : 140
generated_features  : 57
source_5m_features  : 83
source_5m_path      : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_total_cols   : 105
source_numeric_candidates : 83
nonfinite_feature_values  : 0
```

Target counts on the flat target-available frame:

```text
SELL : 5,392
HOLD : 43,342
BUY  : 4,463
```

Interpretation:

```text
- This is the intended Option A tensor: [X, Y, Z] = [samples, WindowSize, Features].
- Source 5M features are now included: source_5m_feature_count=83.
- Total feature count is 140 = 57 generated/context features + 83 source 5M features.
- The tensor is much smaller than the 4D interaction tensor: about 1.42 GB float16 versus about 7.45 GB for [53098,100,32,23].
```

Implemented official health audit for the Option A tensor:

```text
scripts/audit_pivot_pattern_sequence_tensor.py
GUI: Audit pivot sequence tensor health
```

The audit checks:

```text
3D rank/shape: [samples, window, features]
metadata/sample alignment
sample_indices monotonicity
timestamp monotonicity
target array presence/length/finite values
feature_names and feature_groups alignment
source_5m feature count consistency
feature scaler finite checks
full tensor NaN/Inf scan
max_abs <= feature_clip
builder report shape/count consistency
```

Command to run on the operator machine:

```powershell
python -u scripts\audit_pivot_pattern_sequence_tensor.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --builder-report run_logs\pivot_pattern_sequence_tensor\latest.json `
  --chunk-size 512 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --fail-on-reported-feature-nonfinite 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_tensor_health
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_tensor_health\latest.json
run_logs\pivot_pattern_sequence_tensor_health\latest.html
```

Verification in sandbox:

```text
python -m py_compile scripts/audit_pivot_pattern_sequence_tensor.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 45 passed
```

Decision:

```text
The full-source Option A sequence tensor build is structurally correct from the builder report.
Run the new health audit before retraining gold_pivot_pattern_sequence_wavenet_5m.
Previous Sequence WaveNet v1 trained on [24000,100,57] remains underfed and should not be treated as final Option A.
Production remains BLOCKED.
No Phase134. No paper shadow. No live trading.
```

## Phase145A full-source sequence tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_tensor_health\latest.json` after running the official Phase145A Option A sequence tensor health audit.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet
builder_report : run_logs\pivot_pattern_sequence_tensor\latest.json
full_scan      : 1
chunk_size     : 512
```

Result:

```text
status            : PASS
tensor_shape      : [53098, 100, 140]
keras_batch_shape : [batch, 100, 140]
dtype             : float16
samples           : 53098
window_size       : 100
features          : 140
flat_rows         : 53197
sample index      : min=99 max=53196 step=1
first time        : 2025-11-28 17:05:00+00:00
last time         : 2026-09-02 10:25:00+00:00
```

Feature composition:

```text
generated_5m_feature_count : 31
source_5m_feature_count    : 83
session_feature_count      : 4
htf_feature_count          : 22
other_feature_count        : 0
source_5m_feature_path     : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
source_5m_numeric_candidates : 83
```

Full tensor scan:

```text
scanned_cells   : 743,372,000
chunks          : 104
nonfinite_cells : 0
min_value       : -8.0
max_value       : 8.0
max_abs         : 8.0
feature_clip    : 8.0
warnings        : []
errors          : []
```

Target counts on sampled tensor windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- This is the intended Option A tensor layout: [X, Y, Z] = [samples, WindowSize, Features].
- The full-source tensor is healthy: rank=3, shape=[53098,100,140], source_5m=83, no NaN/Inf cells.
- max_abs equals feature_clip, so robust normalization/clipping is active and within configured bounds.
- sample_indices are contiguous with stride=1 from 99 to 53196.
- The previous Sequence WaveNet v1 trained on [24000,100,57] is underfed and should not be treated as the final Option A result.
```

Decision:

```text
Phase145A full-source sequence tensor is accepted as healthy for research training.
Next valid training should use this tensor [samples,100,140], not the old [samples,100,57] tensor.
Production remains BLOCKED until backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```

## Gitignore heavy artifact guard — 2026-09-19

The owner asked to prevent heavy local research artifacts from entering git. `.gitignore` was updated and the malformed `config.inirun_logs/` line was corrected to `config.ini`.

New/confirmed ignore coverage includes:

```text
*.npy
*.keras
*.ckpt
*.weights.h5
*.pkl / *.pickle / *.joblib
*.onnx / *.pb / *.tflite
*.feather / *.arrow / *.orc / *.avro / *.zarr/
*.zip / *.7z / *.rar / *.tar / *.tar.gz / *.tgz / *.xz
datasets/raw/
datasets/external/
datasets/processed/
datasets/models/
run_logs/
logs/
```

Verification examples:

```text
datasets/processed/XAUUSD/5M/pivot_pattern_sequence_tensor_latest.npy → ignored
datasets/models/gold_pivot_pattern_sequence_wavenet_5m/v1_model.keras → ignored
run_logs/pivot_pattern_sequence_wavenet/latest.json → ignored
*.zip project snapshots → ignored
```

Note:

```text
Already-tracked small legacy artifacts are not automatically removed by .gitignore.
New heavy tensors/models/run logs will stay out of git.
```

## Phase145A full-source sequence WaveNet training result — 2026-09-19

The owner supplied the completed `run_logs\pivot_pattern_sequence_wavenet\latest.json`, model summary, and batch/epoch logs for the first full-source Option A training run.

Training input:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [24000, 100, 140]
keras_batch_shape : [batch, 100, 140]
feature_count     : 140
m5_feature_count  : 118
htf_feature_count : 22
other_feature_count : 0
loader_mode       : stream
batch_size        : 16
epochs requested  : 80
early_stopping_patience : 8
nonfinite_input_values  : 0
```

Final report metrics, after Keras restored the best `val_loss` weights:

```text
val_action_accuracy : 0.7239583333
val_top_ap          : 0.3654971900
val_bottom_ap       : 0.3324869559
val_buy_r_mae       : 0.6672694683
val_sell_r_mae      : 0.6664603949
val_selected_rate   : 0.2821691176

test_action_accuracy : 0.6200980392
test_top_ap          : 0.2709324875
test_bottom_ap       : 0.3336111266
test_buy_r_mae       : 0.7359182239
test_sell_r_mae      : 0.7348573208
test_selected_rate   : 0.3609068627
```

Important epoch-end observations from `latest_batch_log.jsonl`:

```text
epoch 1 : val_loss=1.9548627, val_action_acc=0.4316789
epoch 2 : val_loss=1.6995431, val_action_acc=0.5508578
epoch 3 : val_loss=1.8116363, val_action_acc=0.5713848
epoch 4 : val_loss=1.6853775, val_action_acc=0.6583946
epoch 5 : val_loss=1.4642649, val_action_acc=0.7239583  ← best val_loss / restored final weights
epoch 6 : val_loss=1.5603150, val_action_acc=0.7110907
epoch 7 : val_loss=1.8318611, val_action_acc=0.6522672
epoch 8 : val_loss=2.0280118, val_action_acc=0.6197917
epoch 9 : val_loss=1.9110000, val_action_acc=0.6666667
epoch 10: val_loss=1.8384161, val_action_acc=0.6727941
epoch 11: val_loss=1.8083678, val_action_acc=0.7086397
epoch 12: val_loss=1.7787350, val_action_acc=0.7037377
epoch 13: val_loss=1.6534641, val_action_acc=0.7414216
```

Architecture confirmation from the model summary:

```text
Input                  : [batch, 100, 140]
5M branch              : [batch, 100, 118]
HTF branch             : [batch, 100, 22]
All-feature branch     : [batch, 100, 140]
Branch fusion          : [batch, 100, 432]
WaveNet temporal core  : 2 residual blocks × dilations 1,2,4,8,16,32
Attention              : temporal_self_attention
Pooling                : avg + max + last
Heads                  : action/top/bottom/buy_r/sell_r
Trainable params       : 1,256,435
Total params reported  : 3,769,307 including optimizer slots
```

Comparison to the underfed Sequence WaveNet v1 `[24000,100,57]`:

```text
Action accuracy:
  underfed sequence : val=0.4605, test=0.4792
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  underfed sequence : val=0.2415, test=0.2453
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  underfed sequence : val=0.1344, test=0.1817
  full-source seq   : val=0.3325, test=0.3336

Selected rate:
  underfed sequence : val=0.5836, test=0.5720
  full-source seq   : val=0.2822, test=0.3609
```

Comparison to Phase144A 4D Image WaveNet v1 `[12000,100,32,23]`:

```text
Action accuracy:
  4D image WaveNet  : val=0.5628, test=0.5970
  full-source seq   : val=0.7240, test=0.6201

Top AP:
  4D image WaveNet  : val=0.2038, test=0.2328
  full-source seq   : val=0.3655, test=0.2709

Bottom AP:
  4D image WaveNet  : val=0.1501, test=0.2357
  full-source seq   : val=0.3325, test=0.3336
```

Interpretation:

```text
GOOD:
- Full-source Option A is a material improvement over the underfed 57-feature sequence run.
- It also beats the earlier 4D Image WaveNet classification/AP metrics in this non-identical comparison.
- selected_rate is lower and more controlled than the underfed run.
- No NaN/Inf was reported.
- The architecture is the intended advanced Conv1D/WaveNet adaptation of the 4D model.

LIMITS:
- Training loss kept improving while validation loss bottomed at epoch 5; overfitting after epoch 5 is visible.
- R-head test MAE is still weak: buy_r≈0.736, sell_r≈0.735.
- This is still a classifier/pattern report, not a trading proof.
- No PnL, profit factor, drawdown, spread/slippage, or walk-forward trading validation is present.
- 4D and sequence runs used different sample counts and layouts, so comparison is directional, not final proof.
```

Decision:

```text
Phase145A full-source sequence WaveNet is the strongest pivot-pattern research model so far by classification/AP diagnostics.
It is NOT production-approved.
Next required phase: backtest/PnL audit on sequence WaveNet predictions, followed by walk-forward if backtest is promising.
No Phase134. No paper shadow. No live trading.
```

## Phase146A sequence WaveNet PnL audit implemented — 2026-09-19

Implemented the first research-only PnL audit/backtest for the Phase145A full-source sequence WaveNet.

Implemented files:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
docs/Phases/Phase146.md
docs/Report/PHASE146A_SEQUENCE_WAVENET_BACKTEST_REPORT.md
tests/unit/ai/test_pivot_sequence_wavenet_backtest.py
```

GUI command:

```text
Backtest pivot sequence WaveNet PnL
```

Purpose:

```text
Convert action/top/bottom/buy_r/sell_r predictions into BUY/SELL candidates and run a research-only ATR TP/SL replay with spread, same-bar policy, max-hold, initial capital, and risk-per-trade.
```

Recommended first audit command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_backtest `
  --report-title "Phase146A sequence WaveNet PnL audit"
```

Outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.json
run_logs\pivot_pattern_sequence_wavenet_backtest\latest.html
run_logs\pivot_pattern_sequence_wavenet_backtest\latest_trades.csv
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 49 passed
```

Production remains blocked until PnL/walk-forward prove edge.

## Phase147A Option B grouped sequence WaveNet implemented — 2026-09-19

The owner reminded that the agreed roadmap must proceed in this order:

```text
Step 1 — Option B بسازیم
Step 2 — A/B benchmark منصفانه
Step 3 — آموزش بزرگ‌تر / full dataset
Step 4 — ذخیره کامل prediction/backtest archive
Step 5 — فیلترسازی، ولی با قانون ضد overfit
```

Phase147A implements Step 1.

Implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
GUI: Train pivot sequence WaveNet Option B
```

Option B uses the existing healthy Phase145A tensor:

```text
stored X = [53098, 100, 140]
```

but feeds the model as grouped Keras inputs:

```text
m5_context_input  = [batch, 100, 35]   # generated_5m + session
source_5m_input   = [batch, 100, 83]   # source_5m telemetry
htf_context_input = [batch, 100, 22]   # closed 4H + closed 1D
```

Architecture:

```text
separate grouped branches
multi-scale causal Conv1D kernels 3,5,9
late fusion
gated tanh-sigmoid dilated WaveNet
residual/skip connections
SE/channel attention
temporal self-attention
avg/max/last pooling
multi-task heads
```

Command for owner:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --temporal-filters 96 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 8 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 10 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b `
  --report-title "Option B Pivot Sequence WaveNet training"
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_option_b\latest.json
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_summary.txt
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_training_log.csv
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_batch_log.jsonl
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 54 passed
```

Next after owner runs Option B training:

```text
Step 2 — A/B benchmark منصفانه
```

