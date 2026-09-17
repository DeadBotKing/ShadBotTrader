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

---

## Owner map and latest regressor status — 2026-09-12

A graphical owner-facing map now exists:

```text
docs/PROJECT_OWNER_MAP.html
```

It shows:

```text
- Clean Architecture tree
- Research pipeline graph
- Model responsibility map
- GUI command tree
- Phase127-134 status
- Latest Phase133 classifier/regressor validation results
- Current decision gates and blocked/allowed next actions
```

Mandatory maintenance rule:

```text
Every meaningful future code/result/phase/decision update must update docs/PROJECT_OWNER_MAP.html in the same commit.
```

Latest Phase133A regressor status:

```text
meta_total_pnl     : +8.1089
meta_profit_factor : 1.0128
positive_months    : 2
negative_months    : 3
meta_trades        : 120
final_balance      : 100.8109 at initial=100, units=0.1
```

Decision:

```text
Near break-even, but not a pass. Phase134 paper/live remains blocked.
```

---

## Phase133B — Tensor-model walk-forward validation

Status: implemented on 2026-09-13 for the WaveNet/TCN tensor model family.

GUI:

```text
Run tensor walk-forward validation
```

Purpose:

```text
Validate the 3D tensor WaveNet path with real expanding monthly walk-forward logic.
Thresholds are selected only on past validation windows and then tested on the next unseen month.
```

Command:

```powershell
python -u scripts/run_hybrid_tensor_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-family wavenet `
  --task multihead `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --decision-modes score,both `
  --meta-thresholds 0.55,0.60,0.65,0.70 `
  --score-thresholds=-0.10,0,0.05,0.10,0.20 `
  --min-trades 10 `
  --score-metric total_pnl `
  --batch-size 64 `
  --epochs 500 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --verbose 2 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

Open:

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

Gate:

```text
Only if Phase133B passes can Phase134 paper-shadow discussion resume.
```

---

## Phase133C — Validation No-Trade / Risk Gate

Status: implemented on 2026-09-13 as a risk-gated extension of Phase133B.

GUI:

```text
Run tensor walk-forward validation
```

Use the new fields:

```text
allow_no_trade = 1
min_validation_score = 0
min_validation_profit_factor = 1.10
max_validation_drawdown = 120
```

Command:

```powershell
python -u scripts/run_hybrid_tensor_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-family wavenet `
  --task multihead `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --decision-modes score,both `
  --meta-thresholds 0.55,0.60,0.65,0.70 `
  --score-thresholds=-0.10,0,0.05,0.10,0.20 `
  --min-trades 10 `
  --allow-no-trade 1 `
  --min-validation-score 0 `
  --min-validation-profit-factor 1.10 `
  --max-validation-drawdown 120 `
  --score-metric total_pnl `
  --batch-size 64 `
  --epochs 500 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --verbose 2 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
```

Interpretation:

```text
If this still fails, the current tensor WaveNet path is not robust enough and the next work should shift to failure/regime analysis rather than larger training runs.
```

---

## Phase136A — Tensor failure/regime diagnostics

Status: implemented on 2026-09-14 after Phase133C failed as a deployable strategy.

GUI:

```text
Analyze tensor failure regimes
```

Purpose:

```text
Analyze where the tensor/WaveNet path fails by month, side, session/hour, range context, candidate quality and validation-to-test transfer.
```

Command:

```powershell
python -u scripts/analyze_tensor_failure_regimes.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --walk-forward-json run_logs\hybrid_tensor_walk_forward_validation\latest.json `
  --candidate-only 1 `
  --min-group-rows 20 `
  --top-n 12 `
  --quantile-bins 5 `
  --storage-root datasets
```

Send back:

```text
run_logs\tensor_failure_regimes\latest.json
```

Open:

```text
run_logs\tensor_failure_regimes\latest.html
```

No paper/live permission is implied by this diagnostic phase.

---

## Phase137A — Regime-filtered hybrid replay

Status: implemented on 2026-09-14 after Phase136A identified BUY-side damage and SELL pockets.

GUI:

```text
Backtest regime-filtered hybrid
```

Purpose:

```text
Test live-safe side/regime hypotheses through chronological replay. BUY is not removed permanently; SELL-only and strict-BUY are diagnostic modes.
```

SELL-only diagnostic command:

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides SELL `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Mixed strict-BUY diagnostic command:

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides BUY,SELL `
  --buy-min-confidence 0.98 `
  --buy-min-side-4h-room 5 `
  --buy-min-side-1d-room 10 `
  --buy-max-sl-distance 20 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\regime_filtered_hybrid\latest.json
```

---

## Phase138A — Trade anatomy / TP-SL failure analysis

Status: implemented on 2026-09-14 after Phase137A manual filters failed recent holdout.

GUI:

```text
Analyze trade anatomy
```

Purpose:

```text
Diagnose whether the main failure is TP/SL construction, bracket geometry, side asymmetry, stop-loss concentration or range context.
```

Command:

```powershell
python -u scripts/analyze_trade_anatomy.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --min-group-rows 20 `
  --quantile-bins 5 `
  --top-n 15 `
  --storage-root datasets
```

Send back:

```text
run_logs\trade_anatomy\latest.json
```

---

## Phase139A — TP/SL bracket recalibration replay

Status: implemented on 2026-09-15 after Phase138A identified bracket/TP-SL anatomy failure.

GUI:

```text
Backtest bracket recalibration
```

Command:

```powershell
python -u scripts/backtest_bracket_recalibration.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides BUY,SELL `
  --max-tp-distances original,12,14,16,18 `
  --max-sl-distances original,20,23.56,30 `
  --max-reward-risks original,1.0,1.5,2.0 `
  --min-trades 10 `
  --score-metric total_pnl `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\bracket_recalibration\latest.json
```

---

## Phase140A — Candidate direction / counterfactual entry audit

Status: implemented on 2026-09-16 after Phase139A showed that global and side-specific TP/SL bracket caps do not rescue the current candidate stream.

GUI:

```text
Audit candidate direction/entry
```

Purpose:

```text
Determine whether existing candidates are wrong because of side direction, entry timing, or no-edge candidate generation.
```

Core tests:

```text
original side replay
flipped side replay: BUY→SELL and SELL→BUY
entry_delay_bars = 0,1,2,3
side × delay matrix
month × original side × flip/delay matrix
session-hour × original side matrix
```

Command:

```powershell
python -u scripts/audit_candidate_direction_entry.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --entry-delays 0,1,2,3 `
  --side-modes original,flipped `
  --execution-modes independent,chronological `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

Interpretation:

```text
If flipped improves materially: candidate direction may be contrarian/inverted.
If delay improves materially: candidate timing may be too early.
If neither helps: current candidate generation likely has no stable edge.
```

Production remains blocked. Phase134/paper/live must not run from this result alone.

Phase140A operator result recorded on 2026-09-16:

```text
best_chronological_scenario      : chronological:original:delay=3
best_chronological_total_pnl     : -3,123.7836
best_chronological_profit_factor : 0.6512

BUY original      : -39,003.7074 PF=0.5106
BUY flipped→SELL  : -15,831.0041 PF=0.7545
SELL original     : -4,306.1039  PF=0.8760
SELL flipped→BUY  : -21,911.8255 PF=0.5157
```

Decision:

```text
Phase140A failed as a strategy but provided useful diagnosis. Global flip is not the fix; BUY has contrarian symptoms but remains negative when flipped; SELL must not be flipped; entry delay helps but remains negative.
```

Recommended next diagnostic:

```text
Phase141A — Side-Transform / Delay Policy Grid
```

---

## Phase141A — Pivot Pattern Recognition Stack

Status: implemented and executed on 2026-09-16 after owner explicitly requested a Pattern Recognition model for approximate top/bottom reversal zones.

GUI:

```text
Train pivot pattern recognition
```

Purpose:

```text
Build a new research candidate-generation model that learns top_zone / bottom_zone / HOLD from causal 5M pattern features plus previous closed 4H and 1D context.
```

Real public-data execution:

```text
source_mode    : yahoo
market_symbol  : GC=F
1D rows        : 1,258
4H rows        : 3,721
5M rows        : 13,509
model_kind     : sklearn_hgb
target_counts  : SELL=1,368 / HOLD=10,764 / BUY=1,376
```

Walk-forward result:

```text
folds             : 6
trades            : 102
initial_balance   : $100.00
final_balance     : $86.7906
return            : -13.2094%
profit_factor     : 0.6738
positive_folds    : 0
negative_folds    : 6
```

Decision:

```text
FAILED as strategy. The model and feature pipeline were built, but the first real public-data walk-forward did not produce an edge.
```

Production remains blocked.

---

## Phase142A/142B — 3D Pivot Tensor + Keras WaveNet

Status: implemented on 2026-09-16 after owner clarified that the pattern-recognition model must be a real 3D TensorFlow/Keras WaveNet model.

Shape:

```text
Stored tensor X shape       : [samples, 288, channels]
Keras runtime batch X shape : [batch, 288, channels]
```

GUI command sequence:

```text
1. Build pivot pattern tensor
2. Train pivot WaveNet pattern model
3. Backtest pivot WaveNet pattern model
4. Run pivot WaveNet walk-forward
```

Core scripts:

```text
scripts/build_pivot_pattern_tensor.py
scripts/train_pivot_pattern_wavenet.py
scripts/backtest_pivot_pattern_wavenet.py
scripts/run_pivot_pattern_wavenet_walk_forward.py
```

Primary output paths:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz
datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet
datasets\models\gold_pivot_pattern_wavenet_5m\v*_model.keras
run_logs\pivot_pattern_wavenet_walk_forward\latest.json
```

Production remains blocked until walk-forward proves a robust edge.

---

## Phase143A — 4D Pivot Image Tensor + Conv2D/Conv3D

Status: implemented on 2026-09-16 after owner clarified the intended tensor should be 4D for Conv2D/Conv3D.

Shape:

```text
Stored X      : [samples, WindowSize, Features_5M, Features_4H_1D]
Conv2D batch  : [batch, WindowSize, Features_5M, Features_4H_1D]
Conv3D batch  : [batch, WindowSize, Features_5M, Features_4H_1D, 1]
```

Default rolling geometry:

```text
WindowSize = 100
sample_stride = 1
```

GUI:

```text
Build pivot image tensor
Train pivot image CNN
```

Scripts:

```text
scripts/build_pivot_pattern_image_tensor.py
scripts/train_pivot_pattern_image_cnn.py
```

Primary outputs:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_model.keras
```

Production remains blocked.

---

## Phase144A — Advanced 4D Pivot Image WaveNet

Status: implemented on 2026-09-17 after owner rejected the simple Conv2D baseline.

GUI:

```text
Train advanced pivot image WaveNet
```

Script:

```text
scripts/train_pivot_pattern_image_wavenet.py
```

Input:

```text
[samples, WindowSize, Features_5M, Features_4H_1D]
```

Architecture includes:

```text
separate 5M/HTF branches
TimeDistributed spatial multi-scale Conv2D
gated tanh-sigmoid dilated temporal WaveNet residual blocks
SE channel attention
temporal self-attention
multi-scale kernels
```

Production remains blocked until validated.
