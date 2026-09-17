# Phase133 — Walk-Forward Out-of-Time Hybrid Validation

**Status:** ✅ Phase133A implemented
**Type:** Robustness validation / anti-leakage final research gate
**Priority:** before any live/paper trading

---

## Goal

Determine whether the hybrid/meta system generalizes across time, instead of winning only on one selected holdout.

This phase answers:

```text
If we train only on the past, does the system work on the next unseen block/month?
```

---

## Why not train on all data then backtest all data?

That is leakage:

```text
train on full history
backtest on same full history
```

The model has seen the period being evaluated. It can look good in-sample and fail live.

Production final training on all past data is allowed only after walk-forward passes. Then the only valid test is future paper/live data.

---

## Walk-forward protocol

Recommended monthly version:

```text
for each test_month M:
  train_data      = all data before M, excluding purge gap
  validation_data = last slice before M
  test_data       = month M only

  train Phase128/129/130/131 candidate model
  calibrate thresholds on validation_data only
  run chronological replay on test_data
  record metrics
```

Purge gap:

```text
purge_gap >= tensor_window + safe_lag
```

Default:

```text
tensor_window = 288
safe_lag = 48
purge_gap >= 336 bars
```

---

## What is evaluated

```text
base hybrid head + Phase125 thresholds
LightGBM meta-filter
WaveNet/TCN telemetry model
TSMixer telemetry model
PatchTST telemetry model
```

Only models already built in prior phases are included.

---

## Metrics per fold/month

```text
train rows
validation rows
test rows
trades
coverage
win_rate
label_precision
total_pnl
avg_pnl
profit_factor
max_drawdown
final_balance
would_breach_zero
skipped_while_open
skipped_by_meta_filter
```

Aggregate metrics:

```text
months_positive
months_negative
median_monthly_pnl
mean_monthly_pnl
worst_month
best_month
total_pnl
max_drawdown
profit_factor
```

---

## Acceptance criteria

```text
- No random split.
- No training row overlaps future test labels.
- Thresholds are selected only from validation/past data.
- Monthly report is honest even if negative.
- Proceed to production consolidation only if out-of-time results are stable enough.
```

---

## Pass/fail guideline

A candidate can move forward if it satisfies approximately:

```text
profit_factor > 1.10 out-of-time
max_drawdown acceptable for units/initial_capital
more positive months than negative months
no single month explains all profit
coverage non-zero but not over-trading
```

Exact thresholds can be adjusted after seeing fold counts.

---

## Next phase

```text
Phase134 — Production consolidation / online bot assembly.
```

---

## GUI/operator execution requirement

Walk-forward validation زمان‌بر است، اما باید از Dashboard قابل اجرا باشد تا اپراتور مجبور نباشد دستورهای بلند را دستی بسازد.

حداقل command لازم:

```text
CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION
Dashboard label: Run hybrid walk-forward validation
Handler: runs scripts/run_hybrid_walk_forward_validation.py
```

فیلدهای مهم GUI:

```text
symbol
timeframe
start_month
end_month
tensor_window
safe_lag_bars
purge_gap
candidate_models
train_months_min
validation_months
initial_capital
units
storage_root
```

Dashboard باید log زندهٔ fold/month را نشان دهد. تست GUI و log visibility الزامی است.

---

## Phase133A implementation status

Implemented file:

```text
scripts/run_hybrid_walk_forward_validation.py
```

GUI command:

```text
Run hybrid walk-forward validation
```

Tests:

```text
tests/unit/ai/test_hybrid_walk_forward_validation.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
```

Implemented scope:

```text
Phase133A starts with the Phase128 flat telemetry meta-labeler baseline.
It retrains a fresh booster per test month using only earlier months.
```

Protocol:

```text
for each test_month:
  train_months      = all earlier months before validation block
  validation_months = immediate month(s) before test month
  test_month        = next unseen month

  purge train rows before validation boundary
  purge validation rows before test boundary
  train meta model on train rows
  choose threshold on validation only
  run chronological candidate replay on test month
  record base vs meta metrics
```

Outputs:

```text
run_logs/hybrid_walk_forward_validation/latest.json
run_logs/hybrid_walk_forward_validation/latest.csv
run_logs/hybrid_walk_forward_validation/latest.html
```

First recommended command:

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

Important limitation:

```text
Phase133A validates the flat LightGBM/CatBoost/XGBoost baseline first.
Neural walk-forward for WaveNet/TSMixer/PatchTST can be added later if the flat baseline is promising.
```

---

## Operator walk-forward result on full-stream telemetry — 2026-09-12

Input:

```text
flat_path        : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
model_id         : gold_hybrid_meta_walkforward_5m
task             : classifier
target           : target_trade_win
booster          : lightgbm
candidate_only   : 1
train_months_min : 3
validation_months: 1
purge_gap_bars   : 336
meta_thresholds  : 0.45,0.50,0.55,0.60,0.65,0.70
score_metric     : total_pnl
initial_capital  : 100
units            : 0.1
```

Fold results:

```text
2026-04: base=-228.3295, meta= +25.1883, PF=1.1654, trades=24,  threshold=0.70
2026-05: base=-465.0026, meta=-122.8658, PF=0.4854, trades=35,  threshold=0.60
2026-06: base=-381.2333, meta=-210.3758, PF=0.6922, trades=100, threshold=0.70
2026-07: base=  +3.7473, meta= -59.0373, PF=0.8710, trades=100, threshold=0.70
2026-08: base=-202.4170, meta= -20.8577, PF=0.8181, trades=29,  threshold=0.70
2026-09: base= -15.6105, meta=  +0.0000, PF=0.0000, trades=0,   threshold=0.70
```

Aggregate:

```text
folds                  : 6
positive_months        : 1
negative_months        : 4
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : -387.9482191801071
meta_profit_factor     : 0.764435361497561
meta_trades            : 288
meta_avg_pnl           : -1.3470424277087052
meta_max_drawdown      : 460.49957263469696
meta_final_balance     : 61.20517808198929
meta_return_percent    : -38.79482191801071%
meta_would_breach_zero : false
best_month             : 2026-04
worst_month            : 2026-06
```

Decision:

```text
FAIL for production/paper gate.
```

Reason:

```text
- Out-of-time total PnL is negative: -387.95 raw / -38.79 cash at units=0.1.
- Profit factor is 0.7644, below the required >1.10 guideline.
- Only 1 of 6 test months is positive; 4 are negative and September has zero meta trades.
- The meta-filter reduces base-hybrid damage (-387.95 vs -1288.85), but it does not create a profitable walk-forward edge.
- Validation-selected thresholds do not transfer robustly to the next month.
```

Operational consequence:

```text
Do not proceed to Phase134 paper shadow or any live trading with this flat LightGBM meta-filter configuration.
The current model can be considered a damage-reduction filter, not a deployable alpha filter.
```

---

## Regressor command parsing fix — 2026-09-12

The first regressor walk-forward command failed at argument parsing:

```text
argument --score-thresholds: expected one argument
```

Cause:

```text
argparse treats a separate comma-separated value beginning with a negative number, for example -0.25,-0.10,0, as option-like.
```

Fix:

```text
scripts/run_hybrid_walk_forward_validation.py now normalizes threshold argv before argparse.
Both forms are valid:
  --score-thresholds -0.25,-0.10,0
  --score-thresholds=-0.25,-0.10,0
```

Recommended safe PowerShell syntax remains:

```powershell
--score-thresholds=-0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
```

---

## Operator regressor walk-forward result — 2026-09-12

After the classifier walk-forward failed, the operator ran Phase133A as a regressor on Target C R-score:

```text
task             : regressor
target           : target_trade_score_r
booster          : lightgbm
candidate_only   : 1
score_thresholds : -0.25,-0.10,0,0.05,0.10,0.20,0.35,0.50
score_metric     : total_pnl
```

Fold results:

```text
2026-04: meta= +81.4463, PF=1.8400, trades=20, threshold=0.10, base=-228.3295
2026-05: meta= -37.0843, PF=0.5225, trades=11, threshold=0.10, base=-465.0026
2026-06: meta= -43.2650, PF=0.8105, trades=29, threshold=0.50, base=-381.2333
2026-07: meta= +27.1263, PF=1.1854, trades=39, threshold=0.50, base=  +3.7473
2026-08: meta= -20.1143, PF=0.7675, trades=21, threshold=0.05, base=-202.4170
2026-09: meta=  +0.0000, PF=0.0000, trades=0,  threshold=0.50, base= -15.6105
```

Aggregate:

```text
folds                  : 6
positive_months        : 2
negative_months        : 3
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : +8.10892242193222
meta_gross_profit      : 643.8489658236504
meta_gross_loss        : 635.7400434017181
meta_profit_factor     : 1.0127550914970576
meta_max_drawdown      : 183.82112050056458
meta_trades            : 120
meta_avg_pnl           : +0.06757435351610183
meta_final_balance     : 100.81089224219322
meta_return_percent    : +0.8108922421932221%
meta_would_breach_zero : false
```

Decision:

```text
NOT ACCEPTED for production/paper. This is materially better than the classifier and much better than the base hybrid, but it is only near break-even and does not pass the walk-forward gate.
```

Interpretation:

```text
- Regressing target_trade_score_r is directionally better than classifying target_trade_win.
- The strategy moved from negative classifier WF (-387.95 raw) to slightly positive regressor WF (+8.11 raw).
- However PF=1.0128 is below the >1.10 guideline, and month stability is weak: 2 positive vs 3 negative test months plus one zero-trade incomplete month.
- No Phase134 paper shadow/live trading is allowed from this result.
```

---

## Phase133B implementation — Tensor-model walk-forward validation — 2026-09-13

Phase133B was added because the 3D tensor WaveNet v1 produced a promising diagnostic result, but not a true walk-forward proof.

Implemented file:

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
```

GUI command:

```text
Run tensor walk-forward validation
```

Current implemented model family:

```text
model_family=wavenet
```

Protocol:

```text
for each test_month:
  train_months      = all earlier months before validation block
  validation_months = immediate month(s) before test month
  test_month        = next unseen month

  purge validation rows before test boundary
  purge train rows before validation boundary
  train fresh WaveNet/TCN in memory
  select decision_mode + threshold only on validation replay
  evaluate selected threshold on test replay
```

Outputs:

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
run_logs\hybrid_tensor_walk_forward_validation\latest.csv
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

Recommended first full command uses the v1-like architecture because v2 long-train was rejected:

```powershell
python -u scripts/run_hybrid_tensor_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-family wavenet `
  --model-id gold_hybrid_tensor_walkforward_wavenet_5m `
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

Decision rule:

```text
Phase133B is the required proof step for tensor models. A good Phase132A grid is not enough.
```

---

## Operator Phase133B tensor walk-forward result — 2026-09-13

The tensor WaveNet/TCN walk-forward validation was run with a v1-like architecture and validation-selected score/both thresholds.

Aggregate:

```text
folds                  : 6
positive_months        : 2
negative_months        : 3
base_total_pnl         : -1288.8456037938595
tensor_total_pnl       : -409.51990616321564
tensor_profit_factor   : 0.5978639645181408
tensor_max_drawdown    : 464.1122056245804
tensor_trades          : 200
tensor_avg_pnl         : -2.047599530816078
tensor_final_balance   : 59.04800938367843
tensor_return_percent  : -40.951990616321565%
```

Fold detail:

```text
2026-04: tensor=-144.8683 PF=0.3253 trades=35,  selected score=0.05, validation_score=-102.5548
2026-05: tensor=-270.3103 PF=0.5553 trades=115, selected score=-0.10, validation_score=-42.2108
2026-06: tensor=  +7.8459 PF=1.0769 trades=25,  selected both meta=0.70 score=0.20, validation_score=-107.0676
2026-07: tensor= -23.4140 PF=0.4207 trades=8,   selected both meta=0.65 score=0.05, validation_score=+26.0419
2026-08: tensor= +21.2268 PF=1.3981 trades=17,  selected both meta=0.65 score=-0.10, validation_score=+44.9376
2026-09: tensor=  +0.0000 PF=0.0000 trades=0,   selected score=0.20, validation_score=+44.3921
```

Decision:

```text
FAIL — Phase133B did not pass the tensor production/paper gate.
```

Reason:

```text
The earlier WaveNet v1 last-15% threshold grid was only a diagnostic result. True fold-by-fold retraining and validation-selected thresholds produced negative out-of-time PnL and PF below 1.
```

Next possible research change:

```text
Add a validation no-trade/risk gate so the fold can select NO TRADE when all validation thresholds are weak or negative instead of forcing the least-bad trading threshold.
```

---

## Phase133C implementation — Validation No-Trade / Risk Gate — 2026-09-13

Phase133C was added after Phase133B failed and showed that several folds were forced to trade even when validation was negative.

Implemented by extending:

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
```

GUI command:

```text
Run tensor walk-forward validation
```

New controls:

```text
allow_no_trade
min_validation_score
min_validation_profit_factor
max_validation_drawdown
```

CLI flags:

```text
--allow-no-trade 1
--min-validation-score 0
--min-validation-profit-factor 1.10
--max-validation-drawdown 120
```

Behavior:

```text
If the selected validation threshold fails any enabled validation gate,
selected_decision_mode = no_trade
and the test fold records zero trades / zero PnL.
```

Recommended command:

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

Phase133C is still research-only. It does not permit paper/live unless the resulting walk-forward aggregate passes profitability and stability gates.

---

## Operator Phase133C result — Validation No-Trade Gate — 2026-09-13

Phase133C was run with:

```text
allow_no_trade               : 1
min_validation_score         : 0
min_validation_profit_factor : 1.10
max_validation_drawdown      : 120
```

Aggregate:

```text
folds                    : 6
positive_months          : 0
negative_months          : 1
no_trade_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -32.83297738432884
tensor_profit_factor     : 0.7655299301860462
tensor_max_drawdown      : 86.88896641135216
tensor_trades            : 35
tensor_final_balance     : 96.71670226156712
tensor_return_percent    : -3.283297738432878%
```

Fold decisions:

```text
2026-04: validation OK but test passed no trades -> 0.0000
2026-05: no_trade, validation_score below 0 -> 0.0000
2026-06: no_trade, validation_score below 0 -> 0.0000
2026-07: no_trade, validation PF below 1.10 -> 0.0000
2026-08: traded 35, tensor=-32.8330, PF=0.7655
2026-09: validation OK but test passed no trades -> 0.0000
```

Decision:

```text
FAIL as production/paper gate.
```

What improved:

```text
Phase133B tensor_total_pnl : -409.5199
Phase133C tensor_total_pnl :  -32.8330
```

What still failed:

```text
- Total PnL remains negative.
- Profit factor remains below 1.
- There are no positive trading months.
- The only traded month was 2026-08 and it lost money.
```

Conclusion:

```text
The validation no-trade gate is a useful risk-control component, but current tensor/WaveNet alpha is still not robust. No Phase134 paper/live.
```
