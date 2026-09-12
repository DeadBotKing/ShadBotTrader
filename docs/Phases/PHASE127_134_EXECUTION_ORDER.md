# Operator Execution Order — Phase127 to Phase134

Date: 2026-09-09

This is the ordered checklist for tomorrow's operator runs. Every executable phase must have a GUI/Dashboard command as well as CLI.

---

## Current precondition

Run/inspect Phase126A first if not already done:

```text
GUI: Chronological hybrid replay
CLI: scripts/replay_hybrid_chronological_backtest.py
```

Use this result to know whether the base hybrid rule is still bad after one-position chronology.

---

## Phase127 — Build telemetry tensor

Purpose:

```text
Create causal 3D tensor + flat parquet with Target C.
```

GUI:

```text
Build hybrid telemetry tensor
```

Safe first run on existing matrix:

```powershell
python -u scripts/build_hybrid_telemetry_tensor.py `
  --source-mode matrix `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --tensor-window 150 `
  --safe-lag-bars 48 `
  --telemetry-lag-mode fixed `
  --sample-stride 1 `
  --max-samples 0 `
  --candidate-samples-only 0 `
  --dtype float16 `
  --max-tensor-mb 512 `
  --include-htf-context 1 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --storage-root datasets
```

Memory-safe full stream attempt, only after matrix run works:

```powershell
python -u scripts/build_hybrid_telemetry_tensor.py `
  --source-mode stream `
  --stream-scope all `
  --stream-chunk-size 500 `
  --stream-wavenet neutral `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --model-version 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --tensor-window 150 `
  --safe-lag-bars 48 `
  --telemetry-lag-mode fixed `
  --sample-stride 5 `
  --max-samples 12000 `
  --candidate-samples-only 0 `
  --dtype float16 `
  --max-tensor-mb 512 `
  --include-htf-context 1 `
  --max-hold-bars 48 `
  --min-4h-room 2 `
  --min-1d-room 5 `
  --min-tp-distance 2 `
  --min-sl-distance 2 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_telemetry_tensor\latest.json
```

Outputs:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

---

## Phase128 — Train LightGBM/CatBoost meta-labeler

Status: Phase128A implemented. Run only after Phase127A produced the telemetry flat parquet.

GUI:

```text
Train hybrid meta-labeler
Backtest hybrid meta-labeler
```

Input:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

First train command:

```powershell
python -u scripts/train_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --class-weight auto `
  --n-estimators 500 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

Then backtest:

```powershell
python -u scripts/backtest_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --meta-model-id gold_hybrid_meta_lightgbm_5m `
  --meta-model-version 0 `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_meta_labeler\latest.json
run_logs\hybrid_meta_backtest\latest.json
```

---

## Phase129 — Train WaveNet/TCN telemetry model

Status: Phase129A implemented. Run after Phase127A tensor exists. Prefer running Phase128 first as the simpler baseline.

GUI:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

Input:

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

Install first if TensorFlow is missing:

```powershell
python -m pip install -r requirements-ai.txt
```

Train:

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

Backtest:

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

Send back:

```text
run_logs\hybrid_telemetry_wavenet\latest.json
run_logs\hybrid_telemetry_wavenet_backtest\latest.json
```

---

## Phase130 — Train TSMixer benchmark

Status: Phase130A implemented. Run after Phase127A tensor exists. Compare with Phase128/129 results.

GUI:

```text
Train telemetry TSMixer
Backtest telemetry TSMixer
```

Train:

```powershell
python -u scripts/train_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --mixer-layers 4 `
  --time-hidden-units 64 `
  --feature-hidden-units 128 `
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

Backtest:

```powershell
python -u scripts/backtest_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
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

Send back:

```text
run_logs\hybrid_telemetry_tsmixer\latest.json
run_logs\hybrid_telemetry_tsmixer_backtest\latest.json
```

---

## Phase131 — Train PatchTST benchmark

Status: Phase131A implemented. Run after simpler baselines unless you specifically want the heavier Transformer benchmark.

GUI:

```text
Train telemetry PatchTST
Backtest telemetry PatchTST
```

Train:

```powershell
python -u scripts/train_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_patchtst_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --patch-len 16 `
  --stride 8 `
  --d-model 64 `
  --layers 3 `
  --heads 4 `
  --ff-units 128 `
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

Backtest:

```powershell
python -u scripts/backtest_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_patchtst_5m `
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

Send back:

```text
run_logs\hybrid_telemetry_patchtst\latest.json
run_logs\hybrid_telemetry_patchtst_backtest\latest.json
```

---

## Phase132 — Meta-filtered chronological comparison

Status: Phase132A implemented. Run after at least one meta-model exists.

GUI:

```text
Backtest meta-filtered hybrid
```

Purpose:

```text
Compare base hybrid vs meta-filtered variants on identical chronological replay.
```

Command:

```powershell
python -u scripts/backtest_meta_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --candidates base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m `
  --candidate-versions 0 `
  --decision-modes meta,both `
  --meta-thresholds record,0.55,0.60,0.65 `
  --score-thresholds 0,0.05,0.10 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --min-trades 10 `
  --score-metric total_pnl `
  --initial-capital 100 `
  --units 0.1 `
  --skip-missing 1 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_meta_comparison\latest.json
```

Open:

```text
run_logs\hybrid_meta_comparison\latest.html
run_logs\hybrid_meta_comparison\best_replay.html
```

---

## Phase133 — Walk-forward validation

Status: Phase133A implemented for the flat Phase128 booster baseline.

GUI:

```text
Run hybrid walk-forward validation
```

Purpose:

```text
train on past, calibrate on past validation, test next unseen month/block.
```

Command:

```powershell
python -u scripts/run_hybrid_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --meta-thresholds 0.45,0.50,0.55,0.60,0.65,0.70 `
  --min-trades 10 `
  --score-metric total_pnl `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_walk_forward_validation\latest.json
```

Open:

```text
run_logs\hybrid_walk_forward_validation\latest.html
```

---

## Phase134 — Production consolidation

Status: Phase134A implemented as guarded paper-shadow scaffold. Use it only after Phase133 selects a candidate.

GUI:

```text
Validate production hybrid stack
Run hybrid paper shadow
```

Validate/freeze base paper-shadow config:

```powershell
python -u scripts/validate_production_hybrid_stack.py `
  --mode paper_shadow `
  --symbol XAUUSD `
  --timeframe 5M `
  --base-model-id gold_hybrid_lightgbm_head_5m `
  --base-model-version 0 `
  --meta-model-type none `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --position-size-units 0.1 `
  --initial-capital 100 `
  --kill-switch-enabled 1 `
  --write-config 1 `
  --require-models 0 `
  --storage-root datasets
```

Paper shadow:

```powershell
python -u scripts/run_hybrid_paper_shadow.py `
  --config-path configs\hybrid_production_stack.json `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allow-validation-fail 0 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_production_validation\latest.json
run_logs\hybrid_paper_shadow\latest.json
```

No real-money live trading before Phase115 paper/live audit passes.

---

## Latest execution status — 2026-09-12

Completed:

```text
Phase127A full stream telemetry: PASS as data build
Phase128A full-stream LightGBM v2 train: PASS as model training / ranking-signal check
Phase133A full-stream walk-forward: FAIL as production/paper gate
```

Key Phase133A aggregate:

```text
base_total_pnl     : -1288.8456
meta_total_pnl     : -387.9482
meta_profit_factor : 0.7644
meta_trades        : 288
positive_months    : 1
negative_months    : 4
final_balance      : 61.2052 at initial=100, units=0.1
```

Current instruction:

```text
Do NOT run Phase134 paper shadow/live with this candidate.
Next work must stay in research/diagnostic mode: threshold robustness, class-weight/off comparison, regime filtering, or alternative telemetry models.
```
